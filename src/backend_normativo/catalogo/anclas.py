"""HU-F28 · AT-006: un alias que apunta a un fragmento que no está.

F28 no es una fuente distinta de F31: es la misma página de preguntas
frecuentes, citada con el ancla `#44` para señalar una pregunta puntual. El
alias se conserva —la identidad de la referencia es un dato— pero el ancla hay
que verificarla: si `#44` no existe en el destino, la referencia no lleva a
ninguna parte y nadie se entera, porque la página carga igual.

En la captura real de F31 hay 129 anclas y ninguna es numérica: son
`accordion-2691962` y parecidas. El `#44` no está.

Y no se resuelve por parecido. La página tiene un ancla `accordion-2693944`,
que contiene «44», y tiene exactamente 43 preguntas, así que «la 44» está a un
lugar de existir. Las dos coincidencias son tentadoras y las dos son falsas:
elegir cualquiera pondría una pregunta arbitraria en lugar de la que se citó.
Se reportan como lo que son —parecidos que no se usaron— para que quien revise
vea por qué no alcanzan.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser
from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import Severidad, TipoIncidencia
from backend_normativo.ingesta.adaptadores.html import decodificar_html
from backend_normativo.ingesta.almacen import AlmacenObjetos

RESPONSABLE = "curador de datos"


@dataclass
class Ancla:
    source_id: str
    url: str
    fragmento: str
    destino_source_id: str
    estado: str
    anclas_en_destino: int = 0
    parecidos: list[str] = field(default_factory=list)
    detalle: str = ""

    @property
    def rota(self) -> bool:
        return self.estado == "ROTA"


@dataclass
class ReporteAnclas:
    anclas: list[Ancla] = field(default_factory=list)

    @property
    def rotas(self) -> list[Ancla]:
        return [a for a in self.anclas if a.rota]

    @property
    def resueltas(self) -> list[Ancla]:
        return [a for a in self.anclas if a.estado == "RESUELTA"]

    @property
    def sin_captura(self) -> list[Ancla]:
        return [a for a in self.anclas if a.estado == "SIN_CAPTURA"]


def fragmento_de(url: str) -> str | None:
    """El fragmento de una URL, sin el `#` y con el escapado resuelto."""
    partes = urllib.parse.urlsplit(url)
    if not partes.fragment:
        return None
    return urllib.parse.unquote(partes.fragment) or None


def anclas_de(html: str) -> set[str]:
    """Los destinos a los que un `#` puede llegar en esta página.

    Un ancla es un `id` o el `name` de un enlace. Nada más: si el destino se
    arma con JavaScript, la captura no lo prueba y no se declara existente.
    """
    arbol = HTMLParser(html)
    encontradas = {
        nodo.attributes.get("id") for nodo in arbol.css("[id]") if nodo.attributes.get("id")
    }
    encontradas |= {
        nodo.attributes.get("name") for nodo in arbol.css("a[name]") if nodo.attributes.get("name")
    }
    return {a for a in encontradas if a}


def parecidos_a(fragmento: str, anclas: set[str]) -> list[str]:
    """Las anclas que se parecen al fragmento y que igual no se van a usar.

    Existen para reportarse, no para resolverse. Un ancla que contiene el mismo
    número no es la misma ancla, y la enésima pregunta de una lista no es la
    pregunta número ene.
    """
    if not fragmento.isdigit():
        return []
    return sorted(a for a in anclas if fragmento in a and a != fragmento)


def verificar(conexion: Connection, almacen: AlmacenObjetos | None = None) -> ReporteAnclas:
    """Comprueba, para cada URL con fragmento, que el fragmento exista."""
    almacen = almacen or AlmacenObjetos()
    reporte = ReporteAnclas()

    for fila in conexion.execute(
        text(
            "SELECT u.source_id, u.url, coalesce(f.alias_of, u.source_id) AS destino "
            "  FROM fuente_urls u JOIN fuentes f ON f.source_id = u.source_id "
            " WHERE u.url LIKE '%#%' ORDER BY u.source_id, u.url"
        )
    ).mappings():
        fragmento = fragmento_de(fila["url"])
        if fragmento is None:
            continue
        ancla = Ancla(
            source_id=fila["source_id"],
            url=fila["url"],
            fragmento=fragmento,
            destino_source_id=fila["destino"],
            estado="SIN_CAPTURA",
        )
        html = _html_del_destino(conexion, almacen, fila["destino"])
        if html is None:
            ancla.detalle = (
                f"La fuente de destino {fila['destino']} no tiene una captura HTML con la que "
                "comprobar el ancla. No se declara rota ni válida: no se miró."
            )
            reporte.anclas.append(ancla)
            continue

        disponibles = anclas_de(html)
        ancla.anclas_en_destino = len(disponibles)
        if fragmento in disponibles:
            ancla.estado = "RESUELTA"
            ancla.detalle = f"El ancla «{fragmento}» existe en la captura de {fila['destino']}."
        else:
            ancla.estado = "ROTA"
            ancla.parecidos = parecidos_a(fragmento, disponibles)
            ancla.detalle = (
                f"El ancla «{fragmento}» no existe entre las {len(disponibles)} de la captura "
                f"de {fila['destino']}. El alias se conserva; la referencia no lleva a ninguna "
                "parte."
            )
        reporte.anclas.append(ancla)

    _abrir_incidencias(conexion, reporte)
    return reporte


def _html_del_destino(conexion: Connection, almacen: AlmacenObjetos, destino: str) -> str | None:
    fila = (
        conexion.execute(
            text(
                "SELECT c.sha256_raw FROM capturas c "
                "  JOIN fuente_urls u ON u.id = c.source_url_id "
                " WHERE u.source_id = :s AND c.http_status = 200 AND c.mime LIKE 'text/html%' "
                " ORDER BY c.capturado_en DESC LIMIT 1"
            ),
            {"s": destino},
        )
        .mappings()
        .first()
    )
    if fila is None:
        return None
    return decodificar_html(almacen.leer(fila["sha256_raw"]), charset_declarado=None)


def _abrir_incidencias(conexion: Connection, reporte: ReporteAnclas) -> None:
    for ancla in reporte.rotas:
        descripcion = _descripcion(ancla)
        ya = conexion.execute(
            text(
                "SELECT id FROM incidencias_revision "
                " WHERE source_id = :s AND tipo = :t AND descripcion = :d"
            ),
            {
                "s": ancla.source_id,
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "d": descripcion,
            },
        ).scalar_one_or_none()
        if ya is not None:
            continue
        conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, source_id, "
                " descripcion, responsable_rol) VALUES (:t, :s, 'ABIERTA', :src, :d, :r)"
            ),
            {
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "s": Severidad.HIGH.value,
                "src": ancla.source_id,
                "d": descripcion,
                "r": RESPONSABLE,
            },
        )


def _descripcion(ancla: Ancla) -> str:
    partes = [
        f"{ancla.source_id} cita {ancla.destino_source_id} con el ancla «{ancla.fragmento}», "
        f"que no existe entre las {ancla.anclas_en_destino} de la captura del destino. "
        "El alias se conserva: la referencia es un dato aunque no resuelva."
    ]
    if ancla.parecidos:
        partes.append(
            "No se resolvió por parecido. Contienen el mismo número y no se usaron: "
            + ", ".join(f"«{p}»" for p in ancla.parecidos)
            + ". Un ancla que comparte dígitos no es la misma ancla."
        )
    partes.append(
        "Hay que conseguir el ancla correcta del destino o registrar que la pregunta citada "
        "ya no está publicada."
    )
    return " ".join(partes)


def formatear(reporte: ReporteAnclas) -> str:
    lineas = [
        "# Anclas de las referencias con fragmento",
        "",
        "Un alias con `#` promete llevar a un lugar puntual de la página destino. La página",
        "carga igual cuando el ancla no existe, así que el error no se ve: hay que comprobarlo.",
        "",
        f"- Referencias con fragmento: **{len(reporte.anclas)}**",
        f"- Resueltas: **{len(reporte.resueltas)}** · rotas: **{len(reporte.rotas)}** · "
        f"sin captura del destino: **{len(reporte.sin_captura)}**",
        "",
        "| Fuente | Destino | Ancla | Estado | Anclas en el destino | Detalle |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for a in reporte.anclas:
        detalle = a.detalle
        if a.parecidos:
            detalle += " Parecidos no usados: " + ", ".join(f"`{p}`" for p in a.parecidos) + "."
        lineas.append(
            f"| {a.source_id} | {a.destino_source_id} | `{a.fragmento}` | {a.estado} "
            f"| {a.anclas_en_destino or '—'} | {detalle} |"
        )
    lineas += [
        "",
        "## Por qué un ancla rota no se arregla sola",
        "",
        "Resolver `#44` por el ancla que contiene «44», o por la pregunta que está en el lugar",
        "44, pone una respuesta arbitraria donde había una referencia precisa. El alias se",
        "conserva y la rotura se reporta con responsable: la referencia correcta la consigue",
        "alguien que mire el destino, no una heurística de dígitos.",
    ]
    return "\n".join(lineas)
