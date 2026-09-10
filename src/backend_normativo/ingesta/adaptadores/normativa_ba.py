"""Adaptador de NormativaBA (`boletinoficial.buenosaires.gob.ar/normativaba`).

La ficha trae metadatos y el texto en la misma página. Dos cuidados propios de
esta fuente:

* El campo **Estado** ("Vigente", "No vigente") es una etiqueta del boletín. Se
  conserva como estado *declarado* y no se convierte en la conclusión del
  sistema: una norma "no vigente" pudo incorporar disposiciones que siguen
  aplicándose a través de la norma que modificó.
* La **síntesis** puede discrepar del título y del documento publicado. Cuando
  eso pasa, la diferencia se registra en vez de elegir una versión en silencio.
"""

from __future__ import annotations

import datetime as dt
import re

from backend_normativo.curacion.segmentacion import Parrafo, Segmentador, unir_renglones
from backend_normativo.db.vocabularios import (
    EstadoLegal,
    ModoExtraccion,
    RolUrl,
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
    UrlDescubierta,
    calcular_score,
)
from backend_normativo.ingesta.adaptadores.html import (
    enlaces_de,
    normalizar_espacios,
    parrafos_de_html,
    texto_plano,
)

RE_URL = re.compile(
    r"boletinoficial\.buenosaires\.gob\.ar/normativaba/norma/(?P<id>\d+)", re.IGNORECASE
)

# "LEY 547 2001", "DECRETO 75 2015", "RESOLUCIÓN 1621 2025 MINISTERIO DE EDUCACION".
# Algunas fichas agregan el organismo emisor después del año.
RE_ENCABEZADO = re.compile(
    r"^\s*(?P<tipo>[A-ZÁÉÍÓÚÑ\s]+?)\s+(?P<numero>[\d.]+)(?:\s*/\s*[\w.]+)*\s+"
    r"(?P<anio>\d{4})(?:\s+(?P<organismo>[A-ZÁÉÍÓÚÑ\s.]+))?\s*$"
)

# Dónde termina la norma y empieza la página.
#
# El adaptador sabía dónde empieza el articulado y no dónde termina, así que
# todo lo que la ficha muestra debajo entraba como si fuera la norma: el panel
# de «Relaciones», sus encabezados de tabla —«Tipo de relación», «Norma
# relacionada», «Detalle»—, los tipos de vínculo —«INTEGRA», «COMPLEMENTA»—, las
# normas listadas y los resúmenes que la propia página redacta sobre ellas.
#
# Once de los treinta y tres fragmentos publicados de la Ley 6935 eran eso. No
# es ruido inofensivo: se publicaron como texto citable, así que una respuesta
# podía citar «Tipo de relación» o «INTEGRA» como si fuera la ley, y en la
# medición de recuperación esos fragmentos ocupaban el 34,8% de los puestos
# devueltos.
#
# El corte se hace por el encabezado del panel, que es una estructura de la
# ficha y no una palabra suelta del texto: se exige coincidencia exacta del
# párrafo entero. Y no se recorta en silencio: se deja aviso con cuántos
# párrafos quedaron afuera, para que un cambio de maquetación que se coma
# articulado se vea en vez de aparecer como una norma más corta.
FIN_DEL_ARTICULADO: frozenset[str] = frozenset({"relaciones"})

TIPOS: tuple[tuple[str, TipoNorma], ...] = (
    ("decreto ley", TipoNorma.DECRETO_LEY),
    ("decreto", TipoNorma.DECRETO),
    ("ley", TipoNorma.LEY),
    ("resolucion", TipoNorma.RESOLUCION),
    ("resolución", TipoNorma.RESOLUCION),
    ("disposicion", TipoNorma.DISPOSICION),
    ("disposición", TipoNorma.DISPOSICION),
    ("ordenanza", TipoNorma.ORDENANZA),
)

ETIQUETAS_FECHA: dict[str, TipoFecha] = {
    "publicación": TipoFecha.PUBLICACION,
    "publicacion": TipoFecha.PUBLICACION,
    "sanción": TipoFecha.SANCION,
    "sancion": TipoFecha.SANCION,
    "promulgación": TipoFecha.PROMULGACION,
    "promulgacion": TipoFecha.PROMULGACION,
}

ESTADOS_DECLARADOS: dict[str, EstadoLegal] = {
    "vigente": EstadoLegal.VIGENTE,
    "no vigente": EstadoLegal.NO_VIGENTE,
    "vigencia parcial": EstadoLegal.VIGENCIA_PARCIAL,
    "derogada": EstadoLegal.NO_VIGENTE,
    "abrogada": EstadoLegal.NO_VIGENTE,
}

# Rótulos que anuncian el comienzo del articulado y qué versión es.
MARCAS_TEXTO: tuple[tuple[str, TipoVersionDocumento], ...] = (
    ("texto original", TipoVersionDocumento.ORIGINAL),
    ("texto actualizado", TipoVersionDocumento.ACTUALIZADO),
    ("texto consolidado", TipoVersionDocumento.CONSOLIDADO),
)

RE_FECHA = re.compile(r"^(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<anio>\d{4})$")


def _tipo_norma(texto: str) -> TipoNorma:
    minusculas = texto.lower().strip()
    for prefijo, tipo in TIPOS:
        if minusculas.startswith(prefijo):
            return tipo
    return TipoNorma.OTRO


def _es_transposicion(candidato: str, numero: str) -> bool:
    """Si dos números tienen los mismos dígitos en distinto orden.

    `1261` frente a `1621` es el caso que reporta el manual para F19: no son dos
    normas, es un dígito fuera de lugar en la síntesis de la fuente.
    """
    if candidato == numero or len(candidato) != len(numero):
        return False
    return sorted(candidato) == sorted(numero)


def _fecha(texto: str) -> dt.date | None:
    coincidencia = RE_FECHA.match(texto.strip())
    if not coincidencia:
        return None
    try:
        return dt.date(
            int(coincidencia.group("anio")),
            int(coincidencia.group("mes")),
            int(coincidencia.group("dia")),
        )
    except ValueError:
        return None


class AdaptadorNormativaBA:
    nombre = "normativa_ba"

    def acepta(self, captura: CapturaMaterial) -> bool:
        return bool(RE_URL.search(captura.url_final))

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion:
        coincidencia = RE_URL.search(captura.url_final)
        if coincidencia is None:
            return ResultadoExtraccion(
                avisos=[
                    Aviso(
                        f"{captura.url_final} no es una ficha de NormativaBA",
                        tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                        severidad=Severidad.HIGH,
                    )
                ]
            )
        norma_ba_id = coincidencia.group("id")

        html = captura.texto()
        # NormativaBA publica el PDF convertido con un `<p>` por renglón: sin
        # unirlos, una cita de una oración no entra en ninguna unidad.
        parrafos = unir_renglones(parrafos_de_html(html))
        if not parrafos:
            return ResultadoExtraccion(
                avisos=[
                    Aviso(
                        f"{captura.url_final}: la ficha no tiene texto extraíble",
                        tipo=TipoIncidencia.CAMBIO_DE_ESQUEMA,
                        severidad=Severidad.HIGH,
                    )
                ]
            )

        identidad, tipo_version, indice_texto, avisos = self._encabezado(parrafos, norma_ba_id)
        articulado, descartados = self._recortar_panel(parrafos[indice_texto:])
        if descartados:
            avisos.append(
                Aviso(
                    f"{captura.url_final}: se descartaron {descartados} párrafo(s) posteriores "
                    "al articulado (el panel de relaciones de la ficha, que no es la norma). "
                    "Si la maquetación cambió, este número cambia y hay que mirarlo.",
                    tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                    severidad=Severidad.LOW,
                )
            )
        cuerpo = self._reindexar(articulado)
        segmentacion = Segmentador().segmentar(cuerpo)
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

        texto = texto_plano(cuerpo)
        clasificados = sum(len(u.texto) for u in segmentacion.unidades)
        fechas = identidad.get("fechas", {})

        documento = DocumentoExtraido(
            tipo=TipoDocumento.NORMA,
            tipo_version=tipo_version,
            modo_extraccion=ModoExtraccion.HTML,
            texto=texto,
            unidades=segmentacion.unidades,
            titulo=identidad.get("titulo"),
            external_id=f"normativaba:{norma_ba_id}:{tipo_version.value.lower()}",
            fecha_documento=(
                dt.date.fromisoformat(fechas["PUBLICACION"]) if "PUBLICACION" in fechas else None
            ),
            tipo_fecha=TipoFecha.PUBLICACION if "PUBLICACION" in fechas else TipoFecha.DESCONOCIDA,
            identidad=identidad,
            extraccion_score=calcular_score(
                caracteres_clasificados=clasificados,
                caracteres_totales=len(texto),
                unidades=len(segmentacion.articulos_dispositivos),
            ),
            avisos=avisos,
        )
        return ResultadoExtraccion(
            documentos=[documento],
            urls_descubiertas=self._anexos(html, captura.url_final),
            avisos=avisos,
        )

    def _encabezado(
        self, parrafos: list[Parrafo], norma_ba_id: str
    ) -> tuple[dict[str, object], TipoVersionDocumento, int, list[Aviso]]:
        """Lee los pares etiqueta/valor de la ficha y ubica dónde empieza el texto.

        Se emparejan por posición y no por selector CSS: el marcado del sitio
        cambia con los rediseños, pero el orden "etiqueta, valor" se mantiene.
        """
        # NormativaBA publica normativa de la Ciudad Autónoma de Buenos
        # Aires: su id no se mezcla con el de InfoLEG.
        identidad: dict[str, object] = {
            "normativaba_id": norma_ba_id,
            "jurisdiccion": "AR-C",
        }
        avisos: list[Aviso] = []
        fechas: dict[str, str] = {}
        tipo_version = TipoVersionDocumento.NO_DETERMINADO
        indice_texto = len(parrafos)

        for indice, parrafo in enumerate(parrafos):
            texto = parrafo.texto.strip()
            minusculas = texto.lower().rstrip(":")

            marca = next((v for rotulo, v in MARCAS_TEXTO if minusculas == rotulo), None)
            if marca is not None:
                tipo_version = marca
                indice_texto = indice + 1
                break

            if indice == 0:
                encabezado = RE_ENCABEZADO.match(texto)
                identidad["encabezado"] = texto
                if encabezado:
                    identidad["tipo_declarado"] = encabezado.group("tipo").strip()
                    identidad["tipo"] = _tipo_norma(encabezado.group("tipo")).value
                    identidad["numero"] = encabezado.group("numero").replace(".", "")
                    identidad["anio"] = int(encabezado.group("anio"))
                    if encabezado.group("organismo"):
                        identidad["emisor_declarado"] = normalizar_espacios(
                            encabezado.group("organismo")
                        )
                else:
                    avisos.append(
                        Aviso(
                            f"No se pudo separar tipo, número y año de {texto!r}: la "
                            "identidad queda incierta.",
                            tipo=TipoIncidencia.IDENTIDAD_AMBIGUA,
                            severidad=Severidad.HIGH,
                        )
                    )
                continue

            siguiente = parrafos[indice + 1].texto.strip() if indice + 1 < len(parrafos) else ""
            if minusculas in ETIQUETAS_FECHA and siguiente:
                fecha = _fecha(siguiente)
                if fecha:
                    fechas[ETIQUETAS_FECHA[minusculas].value] = fecha.isoformat()
            elif minusculas == "síntesis" or minusculas == "sintesis":
                identidad["sintesis"] = siguiente
            elif minusculas == "organismo":
                identidad["emisor_declarado"] = siguiente
            elif minusculas == "estado":
                identidad["estado_legal_declarado"] = ESTADOS_DECLARADOS.get(
                    siguiente.lower(), EstadoLegal.NO_DETERMINADA
                ).value
                identidad["estado_declarado_literal"] = siguiente

        identidad["fechas"] = fechas
        identidad["titulo"] = identidad.get("sintesis") or identidad.get("encabezado")

        if indice_texto == len(parrafos):
            avisos.append(
                Aviso(
                    "No se encontró el rótulo que abre el articulado; no se extrae texto a ciegas.",
                    tipo=TipoIncidencia.CAMBIO_DE_ESQUEMA,
                    severidad=Severidad.HIGH,
                )
            )
        self._controlar_sintesis(identidad, avisos)
        return identidad, tipo_version, indice_texto, avisos

    @staticmethod
    def _controlar_sintesis(identidad: dict[str, object], avisos: list[Aviso]) -> None:
        """F19: la síntesis de una ficha puede nombrar un número distinto del
        título por un error de tipeo de la fuente.

        Que la síntesis mencione otras normas es normal: una norma modificatoria
        nombra a la que modifica. Lo que hay que detectar es otra cosa: un
        número que se parece demasiado al propio, como una transposición de
        dígitos. Ahí no hay dos normas, hay un error a registrar.
        """
        sintesis = str(identidad.get("sintesis") or "")
        numero = str(identidad.get("numero") or "")
        if not sintesis or not numero:
            return
        candidatos = set(re.findall(r"\b(\d{3,6})\b", sintesis.replace(".", ""))) - {numero}
        parecidos = sorted(n for n in candidatos if _es_transposicion(n, numero))
        if parecidos:
            avisos.append(
                Aviso(
                    f"La síntesis menciona {', '.join(parecidos)} y el encabezado declara "
                    f"{numero}: los dígitos coinciden pero en otro orden. Se registra la "
                    "discrepancia; no se duplica la identidad.",
                    tipo=TipoIncidencia.IDENTIDAD_AMBIGUA,
                    severidad=Severidad.HIGH,
                )
            )
            identidad["numeros_discrepantes_en_sintesis"] = parecidos

    @staticmethod
    def _recortar_panel(parrafos: list[Parrafo]) -> tuple[list[Parrafo], int]:
        """Corta donde termina la norma y empieza la ficha que la muestra.

        Devuelve el articulado y cuántos párrafos quedaron afuera. El número
        vuelve como aviso: recortar en silencio convertiría un cambio de
        maquetación en una norma más corta sin que nada lo dijera.
        """
        for indice, parrafo in enumerate(parrafos):
            if parrafo.texto.strip().lower() in FIN_DEL_ARTICULADO:
                return parrafos[:indice], len(parrafos) - indice
        return parrafos, 0

    @staticmethod
    def _reindexar(parrafos: list[Parrafo]) -> list[Parrafo]:
        """Recalcula los desplazamientos para que apunten dentro del articulado."""
        reindexados: list[Parrafo] = []
        cursor = 0
        for parrafo in parrafos:
            reindexados.append(
                Parrafo(
                    texto=parrafo.texto,
                    inicio=cursor,
                    fin=cursor + len(parrafo.texto),
                    pagina=parrafo.pagina,
                    entrecomillado=parrafo.entrecomillado,
                )
            )
            cursor += len(parrafo.texto) + 1
        return reindexados

    @staticmethod
    def _anexos(html: str, base_url: str) -> list[UrlDescubierta]:
        """Anexos publicados como PDF aparte de la ficha."""
        descubiertas: list[UrlDescubierta] = []
        vistas: set[str] = set()
        for url, etiqueta in enlaces_de(html, base_url):
            if not url.lower().endswith(".pdf") or url in vistas:
                continue
            vistas.add(url)
            descubiertas.append(
                UrlDescubierta(
                    url=url,
                    rol=RolUrl.ANEXO,
                    relacion=f"anexo enlazado desde la ficha ({normalizar_espacios(etiqueta)})",
                    tipo_esperado="ANEXO",
                )
            )
        return descubiertas
