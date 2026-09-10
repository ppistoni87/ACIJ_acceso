"""Buscar en el corte combinando texto y significado.

P-012 criterio 2. Dos búsquedas sobre el mismo corte —una léxica y una
vectorial—, fusionadas, sin duplicados, y con los filtros aplicados **antes** de
que salga nada, no después de recortar.

Por qué fusión por rango recíproco (RRF) y no una suma ponderada. `ts_rank`
devuelve un número sin unidad que depende de la longitud del documento; la
distancia coseno va de 0 a 2. Sumarlos exige inventar una normalización, y esa
normalización termina siendo el verdadero criterio de orden sin que nadie la
haya elegido. RRF usa solo el orden en que cada búsqueda dejó a cada fragmento:
`1 / (k + puesto)`, con `k = 60`. Un fragmento que las dos encuentran sube; uno
que solo encuentra una entra igual, que es exactamente el punto de ser híbrido.

Por qué los filtros van adentro de cada búsqueda y no encima del resultado. Si
se filtrara después, las dos búsquedas gastarían sus lugares en fragmentos que
van a descartarse y la respuesta terminaría con menos de los que pidió, o con
ninguno, sin que nada lo explique. Filtrar antes es además lo que el criterio
pide con nombre: los permisos y la temporalidad se aplican antes de entregar
contexto.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid

from sqlalchemy import Connection, text

from backend_normativo.recuperacion.embeddings import Embebedor

# k de la fusión. 60 es el valor del trabajo original de RRF; lo que hace es
# que la diferencia entre el puesto 1 y el 2 no aplaste al resto.
K_RRF = 60

# Cuántos candidatos pide cada mitad antes de fusionar. Con menos que unas
# cuantas veces el límite, un fragmento que una mitad puso décimo y la otra
# primero se pierde antes de que la fusión pueda verlo.
FACTOR_CANDIDATOS = 5


@dataclasses.dataclass(frozen=True)
class FragmentoRecuperado:
    chunk_id: uuid.UUID
    texto: str
    norma: str
    unidad: str | None
    url_fuente: str | None
    jurisdiccion: str
    puntaje: float
    puesto_lexico: int | None
    puesto_semantico: int | None

    @property
    def encontrado_por(self) -> str:
        if self.puesto_lexico is not None and self.puesto_semantico is not None:
            return "ambas"
        return "lexica" if self.puesto_lexico is not None else "semantica"


@dataclasses.dataclass
class ResultadoBusqueda:
    fragmentos: list[FragmentoRecuperado] = dataclasses.field(default_factory=list)
    modelo: str | None = None
    indice_id: uuid.UUID | None = None
    solo_lexica: bool = False
    avisos: list[str] = dataclasses.field(default_factory=list)


# El SQL vive entero acá y no armado por pedazos porque las dos mitades tienen
# que compartir exactamente los mismos filtros: si una se olvida de uno, la
# fusión mete de vuelta lo que la otra descartó.
FILTROS = """
      c.release_id = :release
      AND (cast(:jurisdiccion AS varchar) IS NULL OR n.jurisdiccion_id = :jurisdiccion)
      -- El beneficio se filtra por su código y no por su id: el código es lo
      -- que una consulta trae y lo que una persona reconoce.
      AND (cast(:beneficio AS varchar) IS NULL OR EXISTS (
              SELECT 1 FROM beneficio_normas bn
               JOIN beneficio_versiones bv ON bv.registro_version_id = bn.beneficio_version_id
               JOIN beneficios b ON b.id = bv.beneficio_id
               WHERE bn.norma_version_id = c.registro_version_id
                 AND b.codigo = :beneficio))
      -- Temporalidad: la versión tiene que aplicar a la fecha consultada y
      -- haber sido conocida en ese momento. Una versión de rango desconocido
      -- no se descarta acá: se sirve con su motivo, que es trabajo de la capa
      -- de arriba. Lo que sí se descarta es la que se sabe fuera de rango.
      AND (cast(:as_of AS date) IS NULL
           OR bn_rango_aplicacion(rv.valid_tipo, rv.valid_desde, rv.valid_hasta) IS NULL
           OR bn_rango_aplicacion(rv.valid_tipo, rv.valid_desde, rv.valid_hasta)
              @> cast(:as_of AS date))
      AND (cast(:known_at AS timestamptz) IS NULL
           OR (rv.known_desde <= cast(:known_at AS timestamptz)
               AND (rv.known_hasta IS NULL OR rv.known_hasta > cast(:known_at AS timestamptz))))
"""

CONSULTA = f"""
WITH lexica AS (
    SELECT c.id AS chunk_id,
           row_number() OVER (ORDER BY ts_rank(c.tsv, plainto_tsquery('spanish', :consulta))
                              DESC, c.id) AS puesto
      FROM chunks c
      JOIN registro_versiones rv ON rv.id = c.registro_version_id
      JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id
      JOIN normas n ON n.id = nv.norma_id
     WHERE c.tsv @@ plainto_tsquery('spanish', :consulta)
       AND {FILTROS}
     LIMIT :candidatos
),
semantica AS (
    SELECT c.id AS chunk_id,
           row_number() OVER (ORDER BY v.vector <=> :vector, c.id) AS puesto
      FROM fragmento_vectores v
      JOIN chunks c ON c.id = v.chunk_id
      JOIN registro_versiones rv ON rv.id = c.registro_version_id
      JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id
      JOIN normas n ON n.id = nv.norma_id
     WHERE v.indice_id = :indice
       AND {FILTROS}
     LIMIT :candidatos
),
fusion AS (
    SELECT coalesce(l.chunk_id, s.chunk_id) AS chunk_id,
           l.puesto AS puesto_lexico,
           s.puesto AS puesto_semantico,
           coalesce(1.0 / ({K_RRF} + l.puesto), 0.0)
         + coalesce(1.0 / ({K_RRF} + s.puesto), 0.0) AS puntaje
      FROM lexica l
      FULL OUTER JOIN semantica s ON s.chunk_id = l.chunk_id
),
-- Dos unidades distintas del corte pueden tener el mismo texto —un artículo
-- repetido en un anexo, una fórmula que se transcribe—. Devolver los dos no
-- agrega evidencia: agrega la apariencia de que dos normas dicen lo mismo por
-- separado. Se conserva el mejor puesto de cada texto.
sin_repetidos AS (
    SELECT DISTINCT ON (c.hash)
           f.chunk_id, f.puesto_lexico, f.puesto_semantico, f.puntaje, c.hash
      FROM fusion f
      JOIN chunks c ON c.id = f.chunk_id
     ORDER BY c.hash, f.puntaje DESC, f.chunk_id
)
SELECT r.chunk_id, r.puesto_lexico, r.puesto_semantico, r.puntaje,
       c.texto, u.ruta, fu.url, n.jurisdiccion_id,
       n.tipo || ' ' || coalesce(n.numero, '?') || '/' || coalesce(n.anio::text, '?') AS norma
  FROM sin_repetidos r
  JOIN chunks c ON c.id = r.chunk_id
  JOIN unidades_documentales u ON u.id = c.unidad_id
  JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id
  JOIN normas n ON n.id = nv.norma_id
  JOIN documento_versiones dv ON dv.id = u.doc_version_id
  JOIN capturas cap ON cap.id = dv.captura_id
  JOIN fuente_urls fu ON fu.id = cap.source_url_id
 ORDER BY r.puntaje DESC, r.chunk_id
 LIMIT :limite
"""

# Cuando no hay índice todavía, la mitad léxica se sirve sola. Se dice, no se
# disimula: una respuesta peor que la que el sistema puede dar tiene que
# declararse, porque si no parece la mejor posible.
SOLO_LEXICA = f"""
SELECT c.id AS chunk_id,
       row_number() OVER (ORDER BY ts_rank(c.tsv, plainto_tsquery('spanish', :consulta))
                          DESC, c.id)::int AS puesto_lexico,
       NULL::int AS puesto_semantico,
       ts_rank(c.tsv, plainto_tsquery('spanish', :consulta))::float AS puntaje,
       c.texto, u.ruta, fu.url, n.jurisdiccion_id,
       n.tipo || ' ' || coalesce(n.numero, '?') || '/' || coalesce(n.anio::text, '?') AS norma
  FROM chunks c
  JOIN registro_versiones rv ON rv.id = c.registro_version_id
  JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id
  JOIN normas n ON n.id = nv.norma_id
  JOIN unidades_documentales u ON u.id = c.unidad_id
  JOIN documento_versiones dv ON dv.id = u.doc_version_id
  JOIN capturas cap ON cap.id = dv.captura_id
  JOIN fuente_urls fu ON fu.id = cap.source_url_id
 WHERE c.tsv @@ plainto_tsquery('spanish', :consulta)
   AND {FILTROS}
 ORDER BY puntaje DESC, c.id
 LIMIT :limite
"""


def indice_del_corte(
    conexion: Connection, release_id: uuid.UUID, modelo: str
) -> tuple[uuid.UUID, int] | None:
    fila = conexion.execute(
        text(
            "SELECT id, fragmentos FROM indices_semanticos  WHERE release_id = :r AND modelo = :m"
        ),
        {"r": release_id, "m": modelo},
    ).one_or_none()
    return (fila.id, fila.fragmentos) if fila else None


def buscar(
    conexion: Connection,
    consulta: str,
    *,
    release_id: uuid.UUID,
    embebedor: Embebedor | None = None,
    limite: int = 10,
    jurisdiccion: str | None = None,
    beneficio: str | None = None,
    as_of: dt.date | None = None,
    known_at: dt.datetime | None = None,
) -> ResultadoBusqueda:
    """Busca en el corte y devuelve fragmentos citables, ya fusionados."""
    resultado = ResultadoBusqueda()
    parametros: dict[str, object] = {
        "consulta": consulta,
        "release": release_id,
        "jurisdiccion": jurisdiccion,
        "beneficio": beneficio,
        "as_of": as_of,
        "known_at": known_at,
        "limite": limite,
    }

    indice = None
    if embebedor is not None:
        resultado.modelo = embebedor.modelo
        indice = indice_del_corte(conexion, release_id, embebedor.modelo)

    if indice is None or indice[1] == 0:
        resultado.solo_lexica = True
        resultado.avisos.append(
            "Esta búsqueda fue solo léxica: el corte no tiene índice semántico construido "
            "para el modelo pedido. Se construye con `bn recuperacion indexar`. Mientras "
            "tanto, una consulta que no use las palabras del texto legal puede no encontrar "
            "el artículo que la responde."
            if embebedor is not None
            else "Esta búsqueda fue solo léxica: no se pidió modelo de embeddings."
        )
        filas = conexion.execute(text(SOLO_LEXICA), parametros).mappings().all()
    else:
        resultado.indice_id = indice[0]
        assert embebedor is not None
        parametros["indice"] = indice[0]
        parametros["vector"] = str(embebedor.embeber_consulta(consulta))
        parametros["candidatos"] = limite * FACTOR_CANDIDATOS
        filas = conexion.execute(text(CONSULTA), parametros).mappings().all()

    resultado.fragmentos = [
        FragmentoRecuperado(
            chunk_id=fila["chunk_id"],
            texto=fila["texto"],
            norma=fila["norma"],
            unidad=fila["ruta"],
            url_fuente=fila["url"],
            jurisdiccion=fila["jurisdiccion_id"],
            puntaje=float(fila["puntaje"]),
            puesto_lexico=fila["puesto_lexico"],
            puesto_semantico=fila["puesto_semantico"],
        )
        for fila in filas
    ]
    return resultado
