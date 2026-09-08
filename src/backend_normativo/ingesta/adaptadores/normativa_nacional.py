"""Adaptador del portal de normativa nacional (`argentina.gob.ar/normativa`).

El portal expone tres vistas de la misma norma y son documentos distintos:

* la **ficha** (`/norma-N`), con la identidad y las fechas;
* el **texto original** (`/norma-N/texto`);
* el **texto actualizado** (`/norma-N/actualizacion`), que integra las reformas.

No se mezclan. Aplicar una reforma sobre un texto que ya la integra es
exactamente el error que la especificación pide evitar, y solo se puede evitar
si original y actualizado son versiones identificadas por separado.

Las notas editoriales del boletín llevan información de vigencia valiosa, pero
son del editor y no de la norma: se conservan con su propio rol y alimentan
candidatos de relación, nunca una conclusión automática de vigencia.
"""

from __future__ import annotations

import datetime as dt
import re

from selectolax.parser import HTMLParser

from backend_normativo.curacion.segmentacion import Segmentador
from backend_normativo.db.vocabularios import (
    ModoExtraccion,
    RolUrl,
    TipoDocumento,
    TipoFecha,
    TipoNorma,
    TipoVersionDocumento,
)
from backend_normativo.ingesta.adaptadores.base import (
    CapturaMaterial,
    DocumentoExtraido,
    ResultadoExtraccion,
    UrlDescubierta,
    calcular_score,
)
from backend_normativo.ingesta.adaptadores.html import (
    enlaces_de,
    normalizar_espacios,
    parrafos_de_html,
    texto_plano,
)

SELECTOR_CUERPO = ".infoleg-norma-body"
SELECTOR_FICHA = "article"

RE_URL_NORMA = re.compile(r"/normativa/(?P<ambito>[^/]+)/norma-(?P<id>\d+)(?P<vista>/\w+)?")

# "Decreto DNU 1382 / 2001", "Ley 24.714", "Resolución 1621/2025".
RE_ENCABEZADO = re.compile(
    r"^\s*(?P<tipo>[A-Za-zÁÉÍÓÚÑáéíóúñ\s.]+?)\s*"
    r"(?P<numero>[\d.]+)\s*/\s*(?P<anio>\d{4})\s*$"
)
RE_ENCABEZADO_SIN_ANIO = re.compile(
    r"^\s*(?P<tipo>[A-Za-zÁÉÍÓÚÑáéíóúñ\s.]+?)\s+(?P<numero>[\d.]+)\s*$"
)

TIPOS_NORMA: tuple[tuple[str, TipoNorma], ...] = (
    ("decreto ley", TipoNorma.DECRETO_LEY),
    ("decreto", TipoNorma.DECRETO),
    ("ley", TipoNorma.LEY),
    ("resolución", TipoNorma.RESOLUCION),
    ("resolucion", TipoNorma.RESOLUCION),
    ("disposición", TipoNorma.DISPOSICION),
    ("disposicion", TipoNorma.DISPOSICION),
    ("ordenanza", TipoNorma.ORDENANZA),
    ("acordada", TipoNorma.ACORDADA),
    ("convenio", TipoNorma.CONVENIO),
    ("constitución", TipoNorma.CONSTITUCION),
)

# Etiquetas de la ficha y qué fecha significan. Firma, publicación y cabecera no
# son equivalentes, así que cada una conserva su tipo.
ETIQUETAS_FECHA: tuple[tuple[str, TipoFecha], ...] = (
    ("sanción", TipoFecha.SANCION),
    ("sancion", TipoFecha.SANCION),
    ("promulgación", TipoFecha.PROMULGACION),
    ("promulgacion", TipoFecha.PROMULGACION),
    ("publicada en el boletín oficial", TipoFecha.PUBLICACION),
    ("publicada en el boletin oficial", TipoFecha.PUBLICACION),
    ("publicación", TipoFecha.PUBLICACION),
)


def _tipo_norma(texto: str) -> TipoNorma:
    minusculas = texto.lower()
    for prefijo, tipo in TIPOS_NORMA:
        if prefijo in minusculas:
            return tipo
    return TipoNorma.OTRO


def _numero_normalizado(numero: str) -> str:
    """`24.714` y `24714` son la misma norma: el separador de miles es
    tipográfico y no forma parte del número."""
    return numero.replace(".", "").strip()


class AdaptadorNormativaNacional:
    """HTML del portal de normativa nacional."""

    nombre = "normativa_nacional"

    def acepta(self, captura: CapturaMaterial) -> bool:
        return bool(RE_URL_NORMA.search(captura.url_final)) and (
            captura.mime is None or "html" in captura.mime
        )

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion:
        coincidencia = RE_URL_NORMA.search(captura.url_final)
        if coincidencia is None:
            return ResultadoExtraccion(
                avisos=[f"{captura.url_final} no es una URL de norma del portal nacional"]
            )
        vista = (coincidencia.group("vista") or "").strip("/")
        infoleg_id = coincidencia.group("id")

        if vista == "texto":
            return self._extraer_texto(
                captura, infoleg_id, TipoVersionDocumento.ORIGINAL, "infoleg-mode-original"
            )
        if vista == "actualizacion":
            return self._extraer_texto(
                captura,
                infoleg_id,
                TipoVersionDocumento.ACTUALIZADO,
                "infoleg-mode-actualizado",
            )
        return self._extraer_ficha(captura, infoleg_id)

    # --- Ficha -------------------------------------------------------------

    def _extraer_ficha(self, captura: CapturaMaterial, infoleg_id: str) -> ResultadoExtraccion:
        html = captura.texto()
        arbol = HTMLParser(html)
        ficha = arbol.css_first(SELECTOR_FICHA)
        if ficha is None:
            return ResultadoExtraccion(avisos=["La ficha no tiene el bloque esperado"])

        identidad: dict[str, object] = {"infoleg_id": infoleg_id}
        avisos: list[str] = []

        encabezado = ficha.css_first("h1")
        titulo_tematico = ficha.css_first("h2")
        emisor = ficha.css_first("p.lead")

        if encabezado is not None:
            texto = normalizar_espacios(encabezado.text())
            identidad["encabezado"] = texto
            partes = RE_ENCABEZADO.match(texto) or RE_ENCABEZADO_SIN_ANIO.match(texto)
            if partes:
                grupos = partes.groupdict()
                identidad["tipo"] = _tipo_norma(grupos["tipo"]).value
                identidad["tipo_declarado"] = normalizar_espacios(grupos["tipo"])
                identidad["numero"] = _numero_normalizado(grupos["numero"])
                if grupos.get("anio"):
                    identidad["anio"] = int(grupos["anio"])
            else:
                avisos.append(
                    f"No se pudo separar tipo, número y año de {texto!r}: "
                    "la identidad queda incierta."
                )

        if emisor is not None:
            identidad["emisor_declarado"] = normalizar_espacios(emisor.text())
        if titulo_tematico is not None:
            identidad["titulo"] = normalizar_espacios(titulo_tematico.text())

        fechas = self._fechas_de_ficha(ficha)
        identidad["fechas"] = {tipo.value: fecha.isoformat() for tipo, fecha in fechas.items()}

        # El año puede faltar en el encabezado pero deducirse de la sanción.
        if "anio" not in identidad and TipoFecha.SANCION in fechas:
            identidad["anio"] = fechas[TipoFecha.SANCION].year
            identidad["anio_derivado_de"] = TipoFecha.SANCION.value

        parrafos = parrafos_de_html(html, selector=SELECTOR_FICHA)
        documento = DocumentoExtraido(
            tipo=TipoDocumento.NORMA,
            tipo_version=TipoVersionDocumento.NO_DETERMINADO,
            modo_extraccion=ModoExtraccion.HTML,
            texto=texto_plano(parrafos),
            titulo=identidad.get("titulo") or identidad.get("encabezado"),
            external_id=f"infoleg:{infoleg_id}",
            fecha_documento=fechas.get(TipoFecha.PUBLICACION) or fechas.get(TipoFecha.SANCION),
            tipo_fecha=(
                TipoFecha.PUBLICACION
                if TipoFecha.PUBLICACION in fechas
                else (TipoFecha.SANCION if TipoFecha.SANCION in fechas else TipoFecha.DESCONOCIDA)
            ),
            identidad=identidad,
            avisos=avisos,
        )
        # La ficha no es el texto de la norma: no se le pide cobertura de
        # articulado ni se la segmenta como si lo fuera.
        documento.extraccion_score = calcular_score(
            caracteres_clasificados=len(documento.texto),
            caracteres_totales=len(documento.texto),
            unidades=1 if identidad.get("numero") else 0,
        )

        return ResultadoExtraccion(
            documentos=[documento],
            urls_descubiertas=self._urls_de_ficha(html, captura.url_final),
            avisos=avisos,
        )

    def _fechas_de_ficha(self, ficha) -> dict[TipoFecha, dt.date]:
        """Lee los pares etiqueta/valor de la ficha.

        La fecha se toma del atributo `datetime` del elemento `time`, que es
        inequívoco, y no del texto visible, que usa formato local.
        """
        fechas: dict[TipoFecha, dt.date] = {}
        for bloque in ficha.css("dl.normativa > div"):
            etiqueta_nodo = bloque.css_first("dt")
            if etiqueta_nodo is None:
                continue
            etiqueta = normalizar_espacios(etiqueta_nodo.text()).lower().rstrip(":")
            tipo = next((t for clave, t in ETIQUETAS_FECHA if etiqueta.startswith(clave)), None)
            if tipo is None:
                continue
            nodo_tiempo = bloque.css_first("time[datetime]")
            if nodo_tiempo is None:
                continue
            try:
                fechas[tipo] = dt.date.fromisoformat(nodo_tiempo.attributes["datetime"])
            except (ValueError, KeyError, TypeError):
                continue
        return fechas

    def _urls_de_ficha(self, html: str, base_url: str) -> list[UrlDescubierta]:
        """Descubre las vistas de texto de la misma norma.

        Los enlaces del buscador del boletín no se siguen: son consultas, no
        documentos, y abrirlas convertiría el descubrimiento en un rastreo
        indiscriminado.
        """
        descubiertas: list[UrlDescubierta] = []
        for url, etiqueta in enlaces_de(html, base_url, selector=SELECTOR_FICHA):
            coincidencia = RE_URL_NORMA.search(url)
            if not coincidencia:
                continue
            vista = (coincidencia.group("vista") or "").strip("/")
            if vista == "texto":
                relacion = "texto original de la misma norma"
            elif vista == "actualizacion":
                relacion = "texto actualizado de la misma norma"
            else:
                continue
            descubiertas.append(
                UrlDescubierta(
                    url=url,
                    rol=RolUrl.DETALLE,
                    relacion=f"{relacion} ({etiqueta})",
                    tipo_esperado="NORMA",
                )
            )
        return descubiertas

    # --- Texto -------------------------------------------------------------

    def _extraer_texto(
        self,
        captura: CapturaMaterial,
        infoleg_id: str,
        tipo_version: TipoVersionDocumento,
        clase_esperada: str,
    ) -> ResultadoExtraccion:
        html = captura.texto()
        arbol = HTMLParser(html)
        cuerpo = arbol.css_first(SELECTOR_CUERPO)
        avisos: list[str] = []
        if cuerpo is None:
            return ResultadoExtraccion(
                avisos=[
                    f"{captura.url_final}: no se encontró {SELECTOR_CUERPO}. "
                    "El sitio pudo cambiar de estructura; no se extrae a ciegas."
                ]
            )

        clases = cuerpo.attributes.get("class") or ""
        if clase_esperada not in clases:
            # La URL dice una vista y el marcado dice otra: se registra en vez
            # de elegir una en silencio.
            avisos.append(
                f"{captura.url_final} corresponde a {tipo_version.value} pero el cuerpo "
                f"declara {clases!r}. Hay que confirmar qué versión es."
            )

        parrafos = parrafos_de_html(html, selector=SELECTOR_CUERPO)
        segmentacion = Segmentador().segmentar(parrafos)
        avisos.extend(segmentacion.avisos)

        texto = texto_plano(parrafos)
        clasificados = sum(len(u.texto) for u in segmentacion.unidades)

        if not segmentacion.articulos_dispositivos:
            avisos.append(
                f"{captura.url_final}: no se reconoció ningún artículo dispositivo. "
                "La publicación de esta versión queda bloqueada hasta revisarla."
            )

        documento = DocumentoExtraido(
            tipo=TipoDocumento.NORMA,
            tipo_version=tipo_version,
            modo_extraccion=ModoExtraccion.HTML,
            texto=texto,
            unidades=segmentacion.unidades,
            external_id=f"infoleg:{infoleg_id}:{tipo_version.value.lower()}",
            tipo_fecha=TipoFecha.DESCONOCIDA,
            identidad={"infoleg_id": infoleg_id},
            extraccion_score=calcular_score(
                caracteres_clasificados=clasificados,
                caracteres_totales=len(texto),
                unidades=len(segmentacion.articulos_dispositivos),
            ),
            avisos=avisos,
        )

        return ResultadoExtraccion(
            documentos=[documento],
            urls_descubiertas=self._normas_citadas(html, captura.url_final),
            avisos=avisos,
        )

    def _normas_citadas(self, html: str, base_url: str) -> list[UrlDescubierta]:
        """Normas enlazadas desde el texto: son dependencias a resolver.

        Se registran como candidatas, no como relaciones: que una norma enlace a
        otra no prueba qué relación jurídica tienen.
        """
        vistas: set[str] = set()
        descubiertas: list[UrlDescubierta] = []
        for url, etiqueta in enlaces_de(html, base_url, selector=SELECTOR_CUERPO):
            coincidencia = RE_URL_NORMA.search(url)
            if not coincidencia or url in vistas:
                continue
            vistas.add(url)
            descubiertas.append(
                UrlDescubierta(
                    url=url,
                    rol=RolUrl.DETALLE,
                    relacion=f"norma citada en el texto ({etiqueta or 'sin rótulo'})",
                    tipo_esperado="NORMA",
                )
            )
        return descubiertas
