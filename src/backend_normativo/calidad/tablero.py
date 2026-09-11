"""Tablero de calidad: cada número se puede abrir (P-016, criterio 3).

Un indicador que no se puede abrir es un número que hay que creer. Este módulo
existe para que no haya ninguno: cada indicador declara **una** consulta que
devuelve sus filas, y el conteo es la cantidad de filas de esa misma consulta.

Que sea la misma y no dos parecidas es la parte importante. Con un `COUNT(*)`
por un lado y un `SELECT` por otro, el día que alguien toque uno y no el otro el
tablero dice doce y la lista muestra nueve, y no hay forma de saber cuál miente.
Acá no puede pasar: son la misma consulta.

Ninguna cifra sale de una constante. El criterio lo pide explícitamente —«no
provienen de constantes de demostración»— y es el mismo principio que el resto
del proyecto: un número escrito a mano envejece en silencio.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text


@dataclass(frozen=True)
class Indicador:
    """Un número del tablero y las filas que lo componen."""

    clave: str
    titulo: str
    # Por qué este número importa, en una línea. Va al lado del número: un
    # tablero de cifras sin sentido obliga a preguntar qué significa cada una.
    porque: str
    consulta: str
    # Cuando es cierto, que el número suba es una mala noticia.
    alarma_si_crece: bool = False


@dataclass
class Medicion:
    indicador: Indicador
    cuantos: int
    filas: list[dict] = field(default_factory=list)


# El orden es el del tablero: primero lo que bloquea, después lo que falta,
# después lo que anda.
INDICADORES: tuple[Indicador, ...] = (
    Indicador(
        clave="reglas_sin_firmar",
        titulo="Reglas esperando firma jurídica",
        porque=(
            "Hasta que alguien con competencia jurídica las firme, la evaluación "
            "contesta REQUIERE_REVISION a todo."
        ),
        alarma_si_crece=True,
        consulta=(
            "SELECT r.id, b.codigo AS beneficio, r.categoria, "
            "       left(replace(r.texto_literal, chr(10), ' '), 160) AS literal "
            "  FROM reglas r "
            "  LEFT JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id "
            "  LEFT JOIN beneficios b ON b.id = bv.beneficio_id "
            " WHERE r.estado_revision IN ('CANDIDATE', 'IN_REVIEW') "
            " ORDER BY b.codigo NULLS LAST, r.id"
        ),
    ),
    Indicador(
        clave="incidencias_abiertas",
        titulo="Incidencias abiertas",
        porque="Lo que el sistema encontró y no resolvió solo.",
        alarma_si_crece=True,
        consulta=(
            "SELECT i.id, i.tipo, i.severidad, i.source_id, "
            "       left(coalesce(i.descripcion, ''), 160) AS descripcion "
            "  FROM incidencias_revision i "
            " WHERE i.estado = 'ABIERTA' "
            " ORDER BY CASE i.severidad WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 "
            "                           WHEN 'MEDIUM' THEN 2 ELSE 3 END, i.tipo"
        ),
    ),
    Indicador(
        clave="fuentes_bloqueadas",
        titulo="Fuentes con acceso bloqueado",
        porque=(
            "No son una deuda de programación: el sistema registró el impedimento y no lo rodeó."
        ),
        consulta=(
            "SELECT f.source_id, f.nombre, f.access_status, "
            "       left(coalesce(f.motivo_estado, ''), 160) AS motivo "
            "  FROM fuentes f "
            " WHERE f.access_status IN ('ACCESO_LIMITADO','BLOQUEADA','ERROR_TLS', "
            "                           'NO_ENCONTRADA','SIN_URL_CONOCIDA') "
            " ORDER BY f.source_id"
        ),
    ),
    Indicador(
        clave="abstenciones_24h",
        titulo="Abstenciones en las últimas 24 horas",
        porque=(
            "Una abstención correcta no es un fallo, pero un salto sí es una señal: "
            "algo dejó de poder contestarse."
        ),
        consulta=(
            "SELECT c.intencion AS ruta, c.resultado_tipo, c.motivo_abstencion, "
            "       c.latencia_ms, c.request_id "
            "  FROM consultas_auditadas c "
            " WHERE c.ocurrido_en >= now() - interval '24 hours' "
            "   AND c.resultado_tipo <> 'RESUELTA' "
            " ORDER BY c.ocurrido_en DESC"
        ),
    ),
    Indicador(
        clave="versiones_publicadas",
        titulo="Versiones normativas publicadas",
        porque="Lo único que el lector puede servir. Si es cero, la API no contesta nada.",
        consulta=(
            "SELECT rv.id, rv.entidad_tipo, rv.numero_version, rv.estado_revision, rv.release_id "
            "  FROM registro_versiones rv "
            " WHERE rv.release_id IS NOT NULL "
            " ORDER BY rv.entidad_tipo, rv.numero_version"
        ),
    ),
)

POR_CLAVE = {i.clave: i for i in INDICADORES}


def medir(conexion: Connection, indicador: Indicador, *, limite: int | None = None) -> Medicion:
    """Cuenta y filas de la **misma** consulta.

    El límite recorta lo que se muestra, nunca lo que se cuenta: un tablero que
    dice «20» porque mostró veinte estaría midiendo su propia paginación.
    """
    filas = [dict(f) for f in conexion.execute(text(indicador.consulta)).mappings()]
    return Medicion(
        indicador=indicador,
        cuantos=len(filas),
        # `limite is not None` y no `if limite`: con cero, lo pedido es «ninguna
        # fila», y un `if` lo confundía con «sin límite».
        filas=filas[:limite] if limite is not None else filas,
    )


def resumen(conexion: Connection) -> list[dict]:
    """Los indicadores con su número, sin las filas."""
    salida = []
    for indicador in INDICADORES:
        medicion = medir(conexion, indicador, limite=0)
        salida.append(
            {
                "clave": indicador.clave,
                "titulo": indicador.titulo,
                "porque": indicador.porque,
                "cuantos": medicion.cuantos,
                "alarma_si_crece": indicador.alarma_si_crece,
            }
        )
    return salida
