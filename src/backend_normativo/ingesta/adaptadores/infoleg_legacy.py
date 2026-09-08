"""Adaptador del sitio histórico de InfoLEG (`servicios.infoleg.gob.ar`).

Sirve los mismos textos que el portal nuevo, con otro marcado y en `cp1252`. Se
mantiene como familia propia porque varias fuentes del inventario apuntan ahí y
porque su ruta codifica la versión: `texact.htm` es el texto actualizado y
`texorig.htm` el original. Confundirlos aplicaría una reforma dos veces.
"""

from __future__ import annotations

import datetime as dt
import re

from selectolax.parser import HTMLParser

from backend_normativo.curacion.segmentacion import Segmentador, unir_renglones
from backend_normativo.db.vocabularios import (
    ModoExtraccion,
    Severidad,
    TipoDocumento,
    TipoFecha,
    TipoIncidencia,
    TipoNorma,
    TipoVersionDocumento,
)
from backend_normativo.ingesta.adaptadores.base import (
    Aviso,
    CapturaMaterial,
    DocumentoExtraido,
    ResultadoExtraccion,
    calcular_score,
)
from backend_normativo.ingesta.adaptadores.html import (
    normalizar_espacios,
    parrafos_de_html,
    texto_plano,
)

RE_URL = re.compile(
    r"servicios\.infoleg\.gob\.ar/infolegInternet/anexos/[^/]+/(?P<id>\d+)/"
    r"(?P<vista>texact|texord|texorig|norma)\.htm",
    re.IGNORECASE,
)

VISTAS: dict[str, TipoVersionDocumento] = {
    "texact": TipoVersionDocumento.ACTUALIZADO,
    "texord": TipoVersionDocumento.CONSOLIDADO,
    "texorig": TipoVersionDocumento.ORIGINAL,
    "norma": TipoVersionDocumento.ORIGINAL,
}

# "Ley 24.714", "Decreto 1382/2001", "Resolución 1621/2025".
RE_ENCABEZADO = re.compile(
    r"^\s*(?P<tipo>Ley|Decreto(?:\s+Ley)?|Resoluci[oó]n|Disposici[oó]n|Ordenanza|Acordada)\s+"
    r"(?P<numero>[\d.]+)(?:\s*/\s*(?P<anio>\d{2,4}))?\s*$",
    re.IGNORECASE,
)

RE_SANCION = re.compile(r"Sancionada?\s*:\s*(?P<fecha>.+?)\s*$", re.IGNORECASE)
RE_PROMULGACION = re.compile(r"Promulgada?(?:\s+\w+)?\s*:\s*(?P<fecha>.+?)\s*$", re.IGNORECASE)

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
RE_FECHA_LARGA = re.compile(
    r"(?P<mes>[A-Za-zÁÉÍÓÚáéíóú]+)\s+(?P<dia>\d{1,2})\s+de\s+(?P<anio>\d{4})", re.IGNORECASE
)
RE_FECHA_CORTA = re.compile(r"(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<anio>\d{4})")

TIPOS: dict[str, TipoNorma] = {
    "ley": TipoNorma.LEY,
    "decreto": TipoNorma.DECRETO,
    "decreto ley": TipoNorma.DECRETO_LEY,
    "resolucion": TipoNorma.RESOLUCION,
    "resolución": TipoNorma.RESOLUCION,
    "disposicion": TipoNorma.DISPOSICION,
    "disposición": TipoNorma.DISPOSICION,
    "ordenanza": TipoNorma.ORDENANZA,
    "acordada": TipoNorma.ACORDADA,
}


def _fecha(texto: str) -> dt.date | None:
    corta = RE_FECHA_CORTA.search(texto)
    if corta:
        try:
            return dt.date(
                int(corta.group("anio")), int(corta.group("mes")), int(corta.group("dia"))
            )
        except ValueError:
            return None
    larga = RE_FECHA_LARGA.search(texto)
    if larga:
        mes = MESES.get(larga.group("mes").lower())
        if mes:
            try:
                return dt.date(int(larga.group("anio")), mes, int(larga.group("dia")))
            except ValueError:
                return None
    return None


class AdaptadorInfolegLegacy:
    nombre = "infoleg_legacy"

    def acepta(self, captura: CapturaMaterial) -> bool:
        return bool(RE_URL.search(captura.url_final))

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion:
        coincidencia = RE_URL.search(captura.url_final)
        if coincidencia is None:
            return ResultadoExtraccion(avisos=[f"{captura.url_final} no es una ruta de InfoLEG"])

        infoleg_id = coincidencia.group("id")
        tipo_version = VISTAS[coincidencia.group("vista").lower()]

        html = captura.texto()
        parrafos = unir_renglones(parrafos_de_html(html))
        if not parrafos:
            return ResultadoExtraccion(
                avisos=[
                    Aviso(
                        f"{captura.url_final}: la página no tiene texto extraíble",
                        tipo=TipoIncidencia.CAMBIO_DE_ESQUEMA,
                        severidad=Severidad.HIGH,
                    )
                ]
            )

        segmentacion = Segmentador().segmentar(parrafos)
        texto = texto_plano(parrafos)
        identidad, avisos = self._identidad(html, parrafos, infoleg_id)
        avisos.extend(
            Aviso(a, tipo=TipoIncidencia.DISCREPANCIA_NUMERACION) for a in segmentacion.avisos
        )

        if not segmentacion.articulos_dispositivos:
            avisos.append(
                Aviso(
                    f"{captura.url_final}: no se reconoció ningún artículo dispositivo. "
                    "La publicación de esta versión queda bloqueada hasta revisarla.",
                    severidad=Severidad.HIGH,
                )
            )

        clasificados = sum(len(u.texto) for u in segmentacion.unidades)
        documento = DocumentoExtraido(
            tipo=TipoDocumento.NORMA,
            tipo_version=tipo_version,
            modo_extraccion=ModoExtraccion.HTML,
            texto=texto,
            unidades=segmentacion.unidades,
            titulo=identidad.get("titulo"),
            external_id=f"infoleg:{infoleg_id}:{tipo_version.value.lower()}",
            fecha_documento=identidad.get("_fecha_documento"),
            tipo_fecha=identidad.get("_tipo_fecha", TipoFecha.DESCONOCIDA),
            identidad={k: v for k, v in identidad.items() if not k.startswith("_")},
            extraccion_score=calcular_score(
                caracteres_clasificados=clasificados,
                caracteres_totales=len(texto),
                unidades=len(segmentacion.articulos_dispositivos),
            ),
            avisos=avisos,
        )
        return ResultadoExtraccion(documentos=[documento], avisos=avisos)

    def _identidad(
        self, html: str, parrafos, infoleg_id: str
    ) -> tuple[dict[str, object], list[Aviso]]:
        identidad: dict[str, object] = {"infoleg_id": infoleg_id, "jurisdiccion": "AR"}
        avisos: list[Aviso] = []

        arbol = HTMLParser(html)
        titulo = arbol.css_first("title")
        if titulo is not None:
            identidad["titulo"] = normalizar_espacios(titulo.text())

        fechas: dict[TipoFecha, dt.date] = {}
        # El encabezado está en los primeros párrafos, antes del articulado.
        for parrafo in parrafos[:15]:
            texto = parrafo.texto
            encabezado = RE_ENCABEZADO.match(texto)
            if encabezado and "numero" not in identidad:
                grupos = encabezado.groupdict()
                identidad["encabezado"] = texto
                identidad["tipo_declarado"] = grupos["tipo"]
                identidad["tipo"] = TIPOS.get(grupos["tipo"].lower(), TipoNorma.OTRO).value
                identidad["numero"] = grupos["numero"].replace(".", "")
                if grupos.get("anio"):
                    anio = int(grupos["anio"])
                    identidad["anio"] = anio if anio > 100 else 1900 + anio
            for regex, tipo in (
                (RE_SANCION, TipoFecha.SANCION),
                (RE_PROMULGACION, TipoFecha.PROMULGACION),
            ):
                coincidencia = regex.search(texto)
                if coincidencia and tipo not in fechas:
                    fecha = _fecha(coincidencia.group("fecha"))
                    if fecha:
                        fechas[tipo] = fecha

        identidad["fechas"] = {t.value: f.isoformat() for t, f in fechas.items()}
        if "anio" not in identidad and TipoFecha.SANCION in fechas:
            identidad["anio"] = fechas[TipoFecha.SANCION].year
            identidad["anio_derivado_de"] = TipoFecha.SANCION.value
        if "numero" not in identidad:
            avisos.append(
                Aviso(
                    "No se pudo leer tipo y número del encabezado: la identidad queda "
                    "incierta y no se puede fusionar con otra norma sin revisión.",
                    tipo=TipoIncidencia.IDENTIDAD_AMBIGUA,
                    severidad=Severidad.HIGH,
                )
            )

        if fechas:
            tipo_preferido = (
                TipoFecha.PROMULGACION if TipoFecha.PROMULGACION in fechas else TipoFecha.SANCION
            )
            identidad["_fecha_documento"] = fechas[tipo_preferido]
            identidad["_tipo_fecha"] = tipo_preferido
        return identidad, avisos
