"""HU-007: extracción de PDF con control de cobertura.

Un PDF es el formato donde más fácil se afirma de más. Cuatro cosas que el
manual señala y que este adaptador trata explícitamente:

* **Un `Content-Type: application/pdf` no prueba que sea un PDF.** Hay
  endpoints que devuelven 200 con una página HTML de advertencia y el
  encabezado de PDF igual. Se valida el magic; si no está, el documento es
  inválido y la capacidad que dependía de él no se publica. No se hace OCR de
  la página de error: eso convertiría un fallo en contenido.
* **Un prefijo de basura antes del `%PDF-` se repara, y se deja dicho.** Los
  bytes crudos no se tocan —la captura es inmutable—: la reparación produce un
  derivado y queda registrada con el desplazamiento exacto, para que se pueda
  auditar qué se descartó.
* **Una página sin texto no vacía el documento.** Se clasifica página por
  página. Un PDF de treinta páginas con una carátula gráfica tiene veintinueve
  páginas de texto, no cero.
* **Una tabla no hereda su período del nombre del archivo.** Si el epígrafe que
  la fecha aparece después de la tabla en el orden de extracción, o si en el
  mismo documento hay tablas de períodos distintos, la asociación queda en
  revisión en vez de resolverse por cercanía.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from backend_normativo.curacion.segmentacion import Parrafo, Segmentador, unir_renglones
from backend_normativo.db.vocabularios import (
    ModoExtraccion,
    Severidad,
    TipoDocumento,
    TipoFecha,
    TipoIncidencia,
    TipoVersionDocumento,
)
from backend_normativo.ingesta.adaptadores.base import (
    Aviso,
    CapturaMaterial,
    DocumentoExtraido,
    ResultadoExtraccion,
    calcular_score,
)
from backend_normativo.ingesta.adaptadores.fecha_documento import leer as leer_fecha
from backend_normativo.ingesta.adaptadores.pasos_pdf import LecturaDePasos
from backend_normativo.ingesta.adaptadores.pasos_pdf import leer as leer_pasos

MAGIC = b"%PDF-"

# Cuánta basura se tolera antes del magic. Los prefijos que se ven en la
# práctica son avisos de unos pocos cientos de bytes; más que esto ya no es un
# PDF con un prefijo sino otra cosa que contiene un PDF adentro.
LIMITE_PREFIJO = 4096

# Debajo de esto una página no aporta texto utilizable. No es un umbral de
# calidad del contenido: es el piso para distinguir una página con palabras de
# una que solo trae el número de folio.
MINIMO_CHARS_PAGINA = 40

RE_PERIODO = re.compile(
    r"(?:(?P<mes>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)\s+(?:de\s+)?)?(?P<anio>(?:19|20)\d{2})",
    re.IGNORECASE,
)
RE_CICLO = re.compile(r"ciclo\s+lectivo\s+(?P<anio>(?:19|20)\d{2})", re.IGNORECASE)

# «CORRESPONDIENTES A LOS MESES DE DICIEMBRE A MARZO 2026» cubre cuatro meses.
# Quedarse con «marzo 2026» perdería diciembre, enero y febrero.
RE_RANGO_DE_MESES = re.compile(
    r"(?P<desde>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)\s+a\s+"
    r"(?P<hasta>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)\s+(?:de\s+)?(?P<anio>(?:19|20)\d{2})",
    re.IGNORECASE,
)

# Una llamada al pie: «**», «(1)», «(a)». Cuando la misma marca está adentro de
# la tabla y encabeza una línea de abajo, esa línea es su nota, no un párrafo
# suelto que quedó cerca.
RE_MARCA_AL_PIE = re.compile(r"^(?P<marca>\*{1,3}|\(\d{1,2}\)|\(\w\))\s*(?P<resto>\S.*)$")


class PdfInvalido(Exception):
    """Los bytes no son un PDF y no se los va a tratar como si lo fueran."""


@dataclass(frozen=True)
class Reparacion:
    """Qué se descartó para poder abrir el archivo."""

    desplazamiento: int
    prefijo: bytes

    @property
    def descripcion(self) -> str:
        muestra = self.prefijo[:120].decode("utf-8", "replace").replace("\n", " ")
        return (
            f"Se descartaron {self.desplazamiento} byte(s) antes del encabezado PDF "
            f"para poder abrirlo. Los bytes crudos quedan intactos en la captura. "
            f"Prefijo: {muestra!r}"
        )


@dataclass
class PaginaClasificada:
    numero: int
    caracteres: int
    imagenes: int

    @property
    def clase(self) -> str:
        if self.caracteres >= MINIMO_CHARS_PAGINA:
            return "TEXTO"
        if self.imagenes:
            return "GRAFICA"
        return "VACIA"


@dataclass
class TablaUbicada:
    pagina: int
    orden: int
    filas: int
    columnas: int
    periodo: str | None = None
    periodo_ambiguo: bool = False
    motivo_ambiguedad: str | None = None


@dataclass
class LecturaPdf:
    texto: str = ""
    parrafos: list[Parrafo] = field(default_factory=list)
    paginas: list[PaginaClasificada] = field(default_factory=list)
    tablas: list[TablaUbicada] = field(default_factory=list)
    pasos: LecturaDePasos | None = None
    reparacion: Reparacion | None = None
    avisos: list[Aviso] = field(default_factory=list)

    @property
    def paginas_con_texto(self) -> int:
        return sum(1 for p in self.paginas if p.clase == "TEXTO")

    @property
    def cobertura(self) -> float:
        return round(self.paginas_con_texto / len(self.paginas), 4) if self.paginas else 0.0

    @property
    def chars_por_pagina(self) -> dict[str, int]:
        return {str(p.numero): p.caracteres for p in self.paginas}


def validar(datos: bytes) -> tuple[bytes, Reparacion | None]:
    """Devuelve los bytes utilizables y, si hubo que recortar, qué se recortó."""
    if datos.startswith(MAGIC):
        return datos, None
    posicion = datos.find(MAGIC, 0, LIMITE_PREFIJO + len(MAGIC))
    if posicion < 0:
        raise PdfInvalido(
            "La respuesta declara ser un PDF y no tiene el encabezado %PDF- en los "
            f"primeros {LIMITE_PREFIJO} bytes. No se extrae ni se hace OCR: un 200 con "
            "una página de error no es un documento."
        )
    return datos[posicion:], Reparacion(desplazamiento=posicion, prefijo=datos[:posicion])


def leer(datos: bytes) -> LecturaPdf:
    """Abre el PDF y clasifica cada página por separado."""
    import pdfplumber

    utiles, reparacion = validar(datos)
    lectura = LecturaPdf(reparacion=reparacion)
    if reparacion is not None:
        lectura.avisos.append(
            Aviso(
                reparacion.descripcion,
                tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                severidad=Severidad.LOW,
            )
        )

    partes: list[str] = []
    lineas_por_pagina: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(utiles)) as documento:
        for numero, pagina in enumerate(documento.pages, start=1):
            texto = (pagina.extract_text() or "").strip()
            partes.append(texto)
            lineas_por_pagina.append(_lineas_de(pagina))
            lectura.paginas.append(
                PaginaClasificada(
                    numero=numero,
                    caracteres=len(texto),
                    imagenes=len(pagina.images or ()),
                )
            )
            lectura.tablas.extend(_tablas_de(pagina, numero, texto))

    # Un instructivo numera sus pasos. Si los tiene, el orden lo declara él.
    pasos = leer_pasos(lineas_por_pagina)
    if pasos.pasos:
        lectura.pasos = pasos
        lectura.avisos.extend(
            Aviso(a, tipo=TipoIncidencia.COBERTURA_EXTRACCION, severidad=Severidad.MEDIUM)
            for a in pasos.avisos
        )

    # El párrafo conserva de qué página salió: una cita a un PDF sin número de
    # página no es localizable.
    cursor = 0
    for indice, texto in enumerate(partes):
        if not texto:
            continue
        for linea in texto.split("\n"):
            limpia = linea.strip()
            if limpia:
                lectura.parrafos.append(
                    Parrafo(
                        texto=limpia,
                        inicio=cursor,
                        fin=cursor + len(limpia),
                        pagina=indice + 1,
                    )
                )
            cursor += len(linea) + 1
        cursor += 1
    lectura.texto = "\n".join(p.texto for p in lectura.parrafos)

    graficas = [p.numero for p in lectura.paginas if p.clase == "GRAFICA"]
    if graficas:
        lectura.avisos.append(
            Aviso(
                f"Página(s) {', '.join(map(str, graficas))} sin texto extraíble y con "
                "imágenes. Se clasifican como gráficas; el resto del documento se usa "
                "igual. No se hace OCR salvo que esas páginas hagan falta.",
                severidad=Severidad.LOW,
            )
        )
    if lectura.paginas and lectura.paginas_con_texto == 0:
        lectura.avisos.append(
            Aviso(
                "Ninguna página tiene texto extraíble: el documento no sustenta ninguna "
                "capacidad y no se publica sobre él.",
                severidad=Severidad.HIGH,
            )
        )
    lectura.avisos.extend(_avisos_de_tablas(lectura.tablas))
    return lectura


def _lineas_de(pagina) -> list[str]:
    try:
        return [linea["text"] for linea in (pagina.extract_text_lines() or [])]
    except Exception:  # pragma: no cover - depende del PDF
        return []


def _tablas_de(pagina, numero: int, texto: str) -> list[TablaUbicada]:
    """Asocia cada tabla con el período que declara adentro, si declara uno.

    En el PDF de F62 el epígrafe no está arriba de la tabla: es su primera fila.
    «CORRESPONDIENTES AL MES DE OCTUBRE 2025» cae dentro del recuadro de su
    propia tabla, así que la asociación es por contención y no por cercanía: un
    período que está adentro de una tabla no puede pertenecer a otra.

    Un período suelto en el cuerpo de la página no fecha ninguna tabla —en la
    página 7 los dos que hay están cientos de puntos más abajo, en un párrafo—
    y dos períodos dentro de la misma tabla la dejan ambigua.
    """
    try:
        crudas = pagina.extract_tables() or []
        recuadros = pagina.find_tables() or []
    except Exception:  # pragma: no cover - pdfplumber puede fallar en tablas raras
        return []

    dentro = _periodos_por_recuadro(pagina, recuadros)
    al_pie = _periodos_al_pie(pagina, recuadros)
    sueltos = _periodos_en_orden(texto)
    tablas: list[TablaUbicada] = []
    for orden, tabla in enumerate(crudas, start=1):
        ubicada = TablaUbicada(
            pagina=numero,
            orden=orden,
            filas=len(tabla),
            columnas=max((len(f) for f in tabla), default=0),
        )
        propios = dentro.get(orden - 1, []) or al_pie.get(orden - 1, [])
        if len(propios) == 1:
            ubicada.periodo = propios[0]
        elif len(propios) > 1:
            ubicada.periodo_ambiguo = True
            ubicada.motivo_ambiguedad = (
                f"La tabla declara {len(propios)} períodos adentro ({', '.join(propios)}). "
                "Cuál de ellos rige para qué fila es una lectura, no una deducción."
            )
        elif not sueltos:
            ubicada.periodo_ambiguo = True
            ubicada.motivo_ambiguedad = (
                "Ni la tabla ni la página declaran un período. El período no se toma del "
                "nombre del archivo ni de la fecha de subida."
            )
        else:
            ubicada.periodo_ambiguo = True
            ubicada.motivo_ambiguedad = (
                f"La tabla no declara período adentro y la página menciona "
                f"{len(sueltos)} ({', '.join(sueltos)}) fuera de toda tabla. Tomarlos "
                "sería fechar la tabla con el período de un párrafo."
            )
        tablas.append(ubicada)
    return tablas


def _periodos_por_recuadro(pagina, recuadros) -> dict[int, list[str]]:
    """Los períodos que caen dentro del recuadro de cada tabla."""
    if not recuadros:
        return {}
    try:
        lineas = pagina.extract_text_lines() or []
    except Exception:  # pragma: no cover - depende del PDF
        return {}

    por_tabla: dict[int, list[str]] = {}
    for indice, recuadro in enumerate(recuadros):
        _, arriba, _, abajo = recuadro.bbox
        encontrados: list[str] = []
        for linea in lineas:
            if not arriba <= linea["top"] <= abajo:
                continue
            for etiqueta in _periodos_en_orden(linea["text"]):
                if etiqueta not in encontrados:
                    encontrados.append(etiqueta)
        por_tabla[indice] = encontrados
    return por_tabla


def _periodos_al_pie(pagina, recuadros) -> dict[int, list[str]]:
    """Los períodos de una nota al pie que la tabla misma llama.

    En la página 3 de F62 la tabla de topes lleva un «**» adentro y debajo dice
    «**Hasta diciembre 2025». La marca es lo que las une: no es el párrafo que
    quedó más cerca, es la nota que la tabla convoca.
    """
    if not recuadros:
        return {}
    try:
        lineas = pagina.extract_text_lines() or []
    except Exception:  # pragma: no cover - depende del PDF
        return {}

    limites = [r.bbox[3] for r in recuadros]
    por_tabla: dict[int, list[str]] = {}
    for indice, recuadro in enumerate(recuadros):
        abajo = recuadro.bbox[3]
        # La marca se busca en la franja de esta tabla —desde donde terminó la
        # anterior hasta donde termina ésta— y la nota, entre el final de ésta
        # y el de la siguiente. Así una llamada no cruza de tabla.
        desde = limites[indice - 1] if indice else 0.0
        hasta = limites[indice + 1] if indice + 1 < len(limites) else float("inf")
        franja = " ".join(linea["text"] for linea in lineas if desde <= linea["top"] <= abajo)
        encontrados: list[str] = []
        for linea in lineas:
            if not abajo < linea["top"] < hasta:
                continue
            marca = RE_MARCA_AL_PIE.match(" ".join(linea["text"].split()))
            if marca is None or marca.group("marca") not in franja:
                continue
            for etiqueta in _periodos_en_orden(marca.group("resto")):
                if etiqueta not in encontrados:
                    encontrados.append(etiqueta)
        por_tabla[indice] = encontrados
    return por_tabla


def _periodos_en_orden(texto: str) -> list[str]:
    encontrados: list[str] = []
    for coincidencia in RE_RANGO_DE_MESES.finditer(texto):
        etiqueta = (
            f"{coincidencia.group('desde').lower()} a {coincidencia.group('hasta').lower()} "
            f"{coincidencia.group('anio')}"
        )
        if etiqueta not in encontrados:
            encontrados.append(etiqueta)
    for coincidencia in RE_CICLO.finditer(texto):
        etiqueta = f"ciclo lectivo {coincidencia.group('anio')}"
        if etiqueta not in encontrados:
            encontrados.append(etiqueta)
    for coincidencia in RE_PERIODO.finditer(texto):
        mes = coincidencia.group("mes")
        etiqueta = (
            f"{mes.lower()} {coincidencia.group('anio')}" if mes else coincidencia.group("anio")
        )
        if etiqueta not in encontrados and not any(etiqueta in e for e in encontrados):
            encontrados.append(etiqueta)
    return encontrados


def _avisos_de_tablas(tablas: list[TablaUbicada]) -> list[Aviso]:
    ambiguas = [t for t in tablas if t.periodo_ambiguo]
    if not ambiguas:
        return []
    detalle = "; ".join(
        f"página {t.pagina}, tabla {t.orden}: {t.motivo_ambiguedad}" for t in ambiguas[:3]
    )
    return [
        Aviso(
            f"{len(ambiguas)} tabla(s) sin período inequívoco. {detalle}",
            tipo=TipoIncidencia.CONFLICTO_DE_FUENTES,
            severidad=Severidad.HIGH,
        )
    ]


class AdaptadorPdf:
    """Extrae documentos PDF que ya fueron capturados."""

    nombre = "pdf"

    def acepta(self, captura: CapturaMaterial) -> bool:
        declara_pdf = bool(captura.mime and "pdf" in captura.mime.lower())
        parece_pdf = captura.contenido[:LIMITE_PREFIJO].find(MAGIC) >= 0
        termina_en_pdf = captura.url_final.lower().split("?")[0].endswith(".pdf")
        return declara_pdf or parece_pdf or termina_en_pdf

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion:
        resultado = ResultadoExtraccion()
        try:
            lectura = leer(captura.contenido)
        except PdfInvalido as error:
            resultado.avisos.append(
                Aviso(
                    str(error),
                    tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                    severidad=Severidad.HIGH,
                )
            )
            return resultado

        # El PDF llega en renglones: `extract_text_lines` da una línea por vez y una
        # oración cruza varias. Segmentar sin unirlas deja unidades que son media
        # frase, y una evidencia que cita media frase no sostiene lo que afirma.
        segmentacion = Segmentador().segmentar(unir_renglones(lectura.parrafos))
        clasificados = sum(len(u.texto) for u in segmentacion.unidades)
        documento = DocumentoExtraido(
            tipo=self._tipo(captura),
            tipo_version=TipoVersionDocumento.NO_DETERMINADO,
            modo_extraccion=ModoExtraccion.PDF_TEXTO,
            texto=lectura.texto,
            unidades=segmentacion.unidades,
            titulo=self._titulo(lectura.texto),
            external_id=f"{captura.source_id}:{captura.sha256[:16]}",
            paginas=len(lectura.paginas),
            chars_por_pagina=lectura.chars_por_pagina,
            extraccion_score=calcular_score(
                caracteres_clasificados=clasificados,
                caracteres_totales=len(lectura.texto),
                unidades=len(segmentacion.unidades),
            ),
            avisos=[
                *lectura.avisos,
                *(
                    Aviso(
                        a,
                        tipo=TipoIncidencia.DISCREPANCIA_NUMERACION,
                        severidad=Severidad.MEDIUM,
                    )
                    for a in segmentacion.avisos
                ),
            ],
        )
        # La fecha sale del texto del documento o no sale: la carpeta que lo aloja
        # dice dónde lo guardaron, no cuándo lo firmaron.
        fecha = leer_fecha(lectura.texto, url=captura.url_final)
        if fecha.determinada:
            documento.fecha_documento = fecha.fecha
            documento.tipo_fecha = TipoFecha(fecha.tipo_fecha)
        else:
            documento.avisos.append(
                Aviso(
                    fecha.motivo,
                    tipo=TipoIncidencia.VIGENCIA_INDETERMINADA,
                    severidad=Severidad.MEDIUM,
                )
            )
        if fecha.actos_citados:
            # Las notas de consolidación no fechan este documento, pero sí
            # identifican los actos que lo modificaron. Eso se conserva.
            documento.avisos.append(
                Aviso(
                    "El texto cita actos que lo modificaron: "
                    + ", ".join(fecha.actos_citados)
                    + ". Sus fechas son de ellos, no de este documento.",
                    tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                    severidad=Severidad.INFO,
                )
            )
        resultado.documentos.append(documento)
        return resultado

    @staticmethod
    def _tipo(captura: CapturaMaterial) -> TipoDocumento:
        declarado = str(captura.config.get("tipo_documento", "")).upper()
        try:
            return TipoDocumento(declarado)
        except ValueError:
            return TipoDocumento.OTRO

    @staticmethod
    def _titulo(texto: str) -> str | None:
        for linea in texto.splitlines():
            limpia = linea.strip()
            if len(limpia) >= 10:
                return limpia[:300]
        return None
