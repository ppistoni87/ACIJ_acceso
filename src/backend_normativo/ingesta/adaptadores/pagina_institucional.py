"""HU-006: páginas institucionales que no son normas ni fichas de trámite.

Cronogramas, listados de sedes, directorios y páginas de inscripción. No tienen
articulado, así que no se segmentan como una norma: lo que aportan es contenido
operativo con fecha de vencimiento corta, y por eso lo que más importa acá es lo
que el adaptador **se niega** a dar por bueno.

* **Un contenedor vacío no es contenido.** Estas páginas repiten la misma
  estructura para varios períodos y la del período que todavía no arrancó viene
  en blanco. Tomar el primer contenedor porque es el primero deja una carga
  exitosa sin datos.
* **Lo que la página esconde no es lo que publica.** Un ciclo lectivo viejo
  detrás de un `d-none` sigue en el HTML. Se separa del visible y se informa
  que está: descartarlo en silencio impediría responder «esa inscripción es del
  ciclo anterior».
* **Una tabla que no está no es una tabla vacía.** Cuando la página dice que no
  hay sedes abiertas, eso es el dato. Rescatar el listado de la captura
  anterior lo presentaría como vigente.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser, Node

from backend_normativo.curacion.segmentacion import UnidadSegmentada
from backend_normativo.db.vocabularios import (
    ModoExtraccion,
    RolContenido,
    Severidad,
    TipoDocumento,
    TipoIncidencia,
    TipoUnidad,
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
    decodificar_html,
    parrafos_de_html,
    texto_oculto,
    texto_plano,
)

# Contenedores que estos portales usan para agrupar un período o una sección.
SELECTOR_CONTENEDORES = ".field-item, .panel, .card, .accordion-item, section"

# Debajo de esto un contenedor no aporta contenido: es la estructura sin nada
# adentro, que es como viene el período que todavía no arrancó.
MINIMO_UTIL = 40

# «correspondiente a este mes», «del corriente año»: el período existe y la
# página no dice cuál es. Es la forma más silenciosa de un cronograma sin fecha,
# porque el texto se lee completo y parece que dijera algo.
RE_PERIODO_RELATIVO = re.compile(
    r"\b(?:este|el\s+presente|el\s+corriente|del\s+corriente|el\s+actual)\s+"
    r"(?:mes|a[ñn]o|per[ií]odo|ciclo)\b|\ba\s+la\s+fecha\b",
    re.I,
)
RE_DIA_SIN_ANIO = re.compile(
    r"\b\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|setiembre|octubre|noviembre|diciembre)\b(?!\s+de\s+\d{4})",
    re.I,
)

RE_CIERRE = re.compile(
    r"\b(no hay|sin)\b[^.]{0,60}\b(sedes?|puntos?|turnos?|vacantes?|inscripci[oó]n)\b"
    r"|\b(cerrad[ao]s?|finaliz[oó]|no disponible|pr[oó]ximamente)\b",
    re.I,
)


@dataclass
class LecturaPagina:
    titulo: str | None = None
    texto: str = ""
    contenedores_totales: int = 0
    contenedores_vacios: int = 0
    ocultos: list[str] = field(default_factory=list)
    cierre_declarado: str | None = None
    periodo_relativo: str | None = None
    dias_sin_anio: list[str] = field(default_factory=list)
    secciones: list[UnidadSegmentada] = field(default_factory=list)
    avisos: list[Aviso] = field(default_factory=list)

    @property
    def periodo_determinado(self) -> bool:
        """El cronograma dice a qué período corresponde."""
        return not self.periodo_relativo and not self.dias_sin_anio


def leer(html: str, *, url: str = "") -> LecturaPagina:
    lectura = LecturaPagina()
    arbol = HTMLParser(html)
    principal = arbol.css_first("main") or arbol.body
    if principal is None:
        lectura.avisos.append(Aviso("La respuesta no tiene cuerpo HTML.", severidad=Severidad.HIGH))
        return lectura

    encabezado = principal.css_first("h1")
    lectura.titulo = encabezado.text(strip=True) if encabezado else None

    parrafos = parrafos_de_html(html, selector="main")
    if not parrafos:
        parrafos = parrafos_de_html(html)
    lectura.texto = texto_plano(parrafos)

    lectura.ocultos = texto_oculto(html, selector="main")
    if lectura.ocultos:
        lectura.avisos.append(
            Aviso(
                f"{len(lectura.ocultos)} bloque(s) de la página están ocultos y no se extraen "
                "como contenido vigente. Se informan aparte porque existir es un dato: "
                f"«{lectura.ocultos[0][:120]}»",
                tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                severidad=Severidad.MEDIUM,
            )
        )

    lectura.secciones = _secciones(principal, lectura.texto)
    if lectura.texto.strip() and not lectura.secciones:
        lectura.avisos.append(
            Aviso(
                f"{url or 'La página'} tiene texto pero ninguna sección con título que lo "
                "sostenga como cita. Queda el documento y no hay dónde anclar una evidencia, "
                "así que nada de esta página puede llegar a una tabla de destino.",
                tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                severidad=Severidad.HIGH,
            )
        )

    lectura.contenedores_totales, lectura.contenedores_vacios = _contar_contenedores(principal)
    if lectura.contenedores_vacios:
        lectura.avisos.append(
            Aviso(
                f"{lectura.contenedores_vacios} de {lectura.contenedores_totales} contenedor(es) "
                "vienen sin contenido. Se toma el que lo tiene, no el primero: un contenedor "
                "vacío es la estructura de un período que todavía no arrancó.",
                tipo=TipoIncidencia.COBERTURA_EXTRACCION,
                severidad=Severidad.LOW,
            )
        )

    _revisar_periodo(lectura)

    lectura.cierre_declarado = _cierre(lectura.texto)
    if lectura.cierre_declarado:
        lectura.avisos.append(
            Aviso(
                f"{url or 'La página'} declara un cierre o una ausencia: "
                f"«{lectura.cierre_declarado}». Eso es el dato de hoy; no se completa con el "
                "listado de una captura anterior.",
                tipo=TipoIncidencia.VIGENCIA_INDETERMINADA,
                severidad=Severidad.MEDIUM,
            )
        )
    elif not lectura.texto.strip():
        lectura.avisos.append(
            Aviso(
                f"{url or 'La página'} no trae texto extraíble ni declara un cierre. No se "
                "publica nada sobre ella y queda para revisar.",
                severidad=Severidad.HIGH,
            )
        )
    return lectura


# Qué encabezados abren una sección. Una página institucional no tiene
# articulado, pero sí tiene estructura: sus propios títulos. Cada bloque bajo un
# título es una unidad citable —«el organismo dice X bajo el título Y»— y eso es
# lo que faltaba: toda tabla de destino exige una evidencia, y una evidencia
# apunta a una unidad. Sin unidades, estas fuentes no estaban fallando: estaban
# estructuralmente impedidas de llegar a ningún lado.
SELECTOR_TITULOS = "h1, h2, h3, h4"

# Un bloque más corto que esto no sostiene una cita: es un rótulo suelto, un
# «Ver más» o una miga de pan.
MINIMO_SECCION = 25


def _secciones(principal: Node, texto_completo: str) -> list[UnidadSegmentada]:
    """Parte la página por sus propios títulos.

    El orden y las posiciones se calculan sobre el texto que el documento
    guarda, no sobre el HTML: una evidencia localiza un fragmento por su
    desplazamiento dentro del texto de la versión, y si los dos no coinciden la
    cita apunta a otro lado.
    """
    unidades: list[UnidadSegmentada] = []
    vistos: set[str] = set()
    cursor = 0
    for nodo in principal.css(SELECTOR_TITULOS):
        titulo = " ".join(nodo.text(separator=" ", strip=True).split())
        if not titulo:
            continue
        cuerpo: list[str] = []
        siguiente = nodo.next
        while siguiente is not None and siguiente.tag not in {"h1", "h2", "h3", "h4"}:
            trozo = " ".join(siguiente.text(separator=" ", strip=True).split())
            if trozo:
                cuerpo.append(trozo)
            siguiente = siguiente.next
        contenido = " ".join([titulo, *cuerpo]).strip()
        if len(contenido) < MINIMO_SECCION or contenido in vistos:
            continue
        vistos.add(contenido)

        # Se ancla la sección en el texto de la versión. Si no aparece ahí, la
        # unidad se registra igual pero sin posiciones: una cita sin ancla se
        # puede leer, y un ancla inventada apunta a otro texto.
        inicio = texto_completo.find(titulo, cursor)
        if inicio == -1:
            inicio = texto_completo.find(titulo)
        fin = inicio + len(contenido) if inicio != -1 else None
        if inicio != -1:
            cursor = inicio + len(titulo)

        unidades.append(
            UnidadSegmentada(
                tipo=TipoUnidad.SECCION,
                texto=contenido,
                orden=len(unidades) + 1,
                # No es una parte de una norma: es lo que el organismo publica
                # sobre un derecho. El publicador filtra por DISPOSITIVO, así
                # que esto nunca entra a un corte como texto de la ley.
                rol_contenido=RolContenido.INFORMATIVO,
                rotulo=titulo[:200],
                ruta=f"seccion-{len(unidades) + 1}",
                inicio=inicio if inicio != -1 else None,
                fin=fin,
            )
        )
    return unidades


def _contar_contenedores(principal: Node) -> tuple[int, int]:
    contenedores = principal.css(SELECTOR_CONTENEDORES)
    vacios = sum(
        1
        for c in contenedores
        if len(" ".join(c.text(separator=" ", strip=True).split())) < MINIMO_UTIL
    )
    return len(contenedores), vacios


def _revisar_periodo(lectura: LecturaPagina) -> None:
    """A qué período corresponde lo que la página publica.

    El cronograma de Progresar dice «correspondiente a este mes inicia el 9 de
    febrero». Ni «este mes» ni «9 de febrero» dicen de qué año son, y la fecha
    de captura no lo resuelve: una página que quedó sin actualizar publica el
    cronograma del mes pasado con las mismas palabras.
    """
    relativo = RE_PERIODO_RELATIVO.search(lectura.texto)
    lectura.periodo_relativo = relativo.group(0) if relativo else None
    lectura.dias_sin_anio = [
        " ".join(m.group(0).split()) for m in RE_DIA_SIN_ANIO.finditer(lectura.texto)
    ]
    if lectura.periodo_determinado:
        return

    partes = []
    if lectura.periodo_relativo:
        partes.append(
            f"La página fecha su contenido en términos relativos («{lectura.periodo_relativo}») "
            "y no dice a qué período corresponde."
        )
    if lectura.dias_sin_anio:
        muestra = ", ".join(lectura.dias_sin_anio[:4])
        partes.append(f"{len(lectura.dias_sin_anio)} fecha(s) sin año ({muestra}).")
    partes.append(
        "No se completa con el año de la captura: una página sin actualizar publica el "
        "cronograma del mes pasado con las mismas palabras."
    )
    lectura.avisos.append(
        Aviso(
            " ".join(partes),
            tipo=TipoIncidencia.VIGENCIA_INDETERMINADA,
            severidad=Severidad.HIGH,
        )
    )


def _cierre(texto: str) -> str | None:
    coincidencia = RE_CIERRE.search(texto)
    if coincidencia is None:
        return None
    # Se corta en un límite de palabra: un fragmento que arranca a mitad de
    # una es ilegible justo cuando alguien lo está leyendo para decidir.
    inicio = max(0, coincidencia.start() - 40)
    if inicio:
        espacio = texto.find(" ", inicio)
        inicio = espacio + 1 if 0 <= espacio < coincidencia.start() else inicio
    fin = min(len(texto), coincidencia.end() + 60)
    espacio = texto.rfind(" ", coincidencia.end(), fin)
    if espacio > 0:
        fin = espacio
    return " ".join(texto[inicio:fin].split())


class AdaptadorPaginaInstitucional:
    """Último recurso para páginas de portales oficiales sin articulado.

    Va al final de la cadena a propósito: si una página es una norma o una ficha
    de trámite, la reconoce el adaptador que sabe leerla. Este toma lo que queda
    y lo deja utilizable sin pretender que entiende su estructura.
    """

    nombre = "pagina_institucional"

    DOMINIOS = (
        "argentina.gob.ar",
        "buenosaires.gob.ar",
        "gba.gob.ar",
        "dpn.gob.ar",
        "mptutelar.gob.ar",
        "defensoria.org.ar",
        "mpd.gov.ar",
        "becasprogresar.educacion.gob.ar",
        "buenosaires.edu.ar",
    )

    def acepta(self, captura: CapturaMaterial) -> bool:
        if captura.mime and "html" not in captura.mime.lower():
            return False
        url = captura.url_final.lower()
        return any(dominio in url for dominio in self.DOMINIOS)

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion:
        resultado = ResultadoExtraccion()
        html = decodificar_html(captura.contenido, charset_declarado=captura.charset)
        lectura = leer(html, url=captura.url_final)

        if not lectura.texto.strip():
            resultado.avisos.extend(lectura.avisos)
            return resultado

        documento = DocumentoExtraido(
            tipo=TipoDocumento.GUIA,
            tipo_version=TipoVersionDocumento.NO_DETERMINADO,
            modo_extraccion=ModoExtraccion.HTML,
            texto=lectura.texto,
            titulo=lectura.titulo,
            external_id=f"pagina:{captura.source_id}",
            identidad={
                "pagina": {
                    "titulo": lectura.titulo,
                    "contenedores": lectura.contenedores_totales,
                    "contenedores_vacios": lectura.contenedores_vacios,
                    "ocultos": lectura.ocultos[:10],
                    "cierre_declarado": lectura.cierre_declarado,
                }
            },
            unidades=lectura.secciones,
            # El score mide qué proporción del texto quedó dentro de una sección
            # citable. No hay articulado que clasificar y eso no es un fallo: lo
            # que sí sería un fallo es que el texto no esté en ninguna sección,
            # porque entonces no hay dónde anclar una evidencia.
            extraccion_score=calcular_score(
                caracteres_clasificados=sum(len(u.texto) for u in lectura.secciones),
                caracteres_totales=len(lectura.texto),
                unidades=len(lectura.secciones),
            ),
            avisos=list(lectura.avisos),
        )
        resultado.documentos.append(documento)
        return resultado
