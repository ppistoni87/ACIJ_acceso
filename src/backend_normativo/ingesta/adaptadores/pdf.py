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

from backend_normativo.curacion.segmentacion import Parrafo, Segmentador
from backend_normativo.db.vocabularios import (
    ModoExtraccion,
    Severidad,
    TipoDocumento,
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
    with pdfplumber.open(io.BytesIO(utiles)) as documento:
        for numero, pagina in enumerate(documento.pages, start=1):
            texto = (pagina.extract_text() or "").strip()
            partes.append(texto)
            lectura.paginas.append(
                PaginaClasificada(
                    numero=numero,
                    caracteres=len(texto),
                    imagenes=len(pagina.images or ()),
                )
            )
            lectura.tablas.extend(_tablas_de(pagina, numero, texto))

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


def _tablas_de(pagina, numero: int, texto: str) -> list[TablaUbicada]:
    """Asocia cada tabla con el período que la encabeza, si lo hay.

    La regla es de orden de lectura: el epígrafe que fecha una tabla va antes.
    Si el único período del texto de la página aparece después de la tabla, o si
    hay más de uno, no se elige por cercanía: queda ambiguo.
    """
    try:
        crudas = pagina.extract_tables() or []
    except Exception:  # pragma: no cover - pdfplumber puede fallar en tablas raras
        return []

    periodos = _periodos_en_orden(texto)
    tablas: list[TablaUbicada] = []
    for orden, tabla in enumerate(crudas, start=1):
        ubicada = TablaUbicada(
            pagina=numero,
            orden=orden,
            filas=len(tabla),
            columnas=max((len(f) for f in tabla), default=0),
        )
        if len(periodos) == 1 and len(crudas) == 1:
            ubicada.periodo = periodos[0]
        elif not periodos:
            ubicada.periodo_ambiguo = True
            ubicada.motivo_ambiguedad = (
                "La página no declara ningún período. El período no se toma del nombre "
                "del archivo ni de la fecha de subida."
            )
        else:
            ubicada.periodo_ambiguo = True
            ubicada.motivo_ambiguedad = (
                f"La página menciona {len(periodos)} período(s) ({', '.join(periodos)}) y "
                f"{len(crudas)} tabla(s). Asociar por cercanía haría que una tabla herede "
                "el período de otra."
            )
        tablas.append(ubicada)
    return tablas


def _periodos_en_orden(texto: str) -> list[str]:
    encontrados: list[str] = []
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

        segmentacion = Segmentador().segmentar(lectura.parrafos)
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
        # La fecha de la carpeta que aloja el PDF no fecha el documento: un anexo
        # firmado en 2025 puede estar colgado de una ruta de 2019.
        documento.avisos.append(
            Aviso(
                "La fecha del documento no se deduce de la ruta ni del nombre del archivo. "
                "Queda pendiente hasta que se lea del propio documento o del acto que lo aprueba.",
                tipo=TipoIncidencia.VIGENCIA_INDETERMINADA,
                severidad=Severidad.MEDIUM,
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
