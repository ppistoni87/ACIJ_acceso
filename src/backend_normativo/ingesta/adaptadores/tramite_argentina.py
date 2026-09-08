"""HU-019: fichas de trámite de argentina.gob.ar.

El portal publica los trámites con una estructura regular —a quién está
dirigido, qué necesitás, cómo se hace, cuánto tarda, cuánto cuesta— y eso lo
hace extraíble. Lo que no es regular es lo que **falta**: la ficha de Defensa
del Consumidor declara el costo («Gratuito») y deja la duración vacía.

Tres cosas que este adaptador no hace, y son la razón por la que existe:

* **No completa lo ausente.** Una duración vacía no es «inmediato» y un costo
  vacío no es «gratuito». Solo se afirma lo que la ficha dice, con la evidencia
  del fragmento que lo dice.
* **No ordena los pasos por posición en el documento.** Toma los ítems de
  primer nivel de la lista de pasos; los sub-ítems son detalle de su paso, no
  pasos nuevos. Aplanar la lista convertiría un paso con tres aclaraciones en
  cuatro pasos.
* **No trata un formulario como un trámite hecho.** La URL de inicio se
  conserva como el punto de entrada que es. No se completa, no se envía y no se
  declara que el trámite pueda hacerse desde acá.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser, Node

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
)
from backend_normativo.ingesta.adaptadores.html import decodificar_html

DOMINIOS = ("argentina.gob.ar",)
MARCA_SERVICIO = "/servicio/"

# Encabezados de las secciones que el portal usa. Se comparan normalizados
# porque el signo de pregunta y las tildes varían entre fichas.
SECCIONES = {
    "dirigido": ("a quien esta dirigido",),
    "requisitos": ("que necesito", "que necesitas", "requisitos"),
    "pasos": ("como hago", "como lo hago", "como se hace"),
    "duracion": ("cuanto tiempo lleva", "cuanto tarda", "cuanto demora"),
    "costo": ("cual es el costo", "cuanto cuesta", "costo"),
}

RE_ACENTOS = str.maketrans("áéíóúüñ", "aeiouun")

# Señales de que la respuesta es una pantalla de acceso y no la ficha. Un 200
# con un formulario de login no es contenido público del trámite.
MARCAS_LOGIN = (
    "iniciar sesión",
    "iniciá sesión",
    "ingresar con clave",
    "clave fiscal",
    "mi argentina",
    "usuario y contraseña",
)


@dataclass
class Item:
    """Un requisito o un paso, con las aclaraciones que cuelgan de él."""

    texto: str
    detalle: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.texto


@dataclass
class FichaTramite:
    titulo: str | None = None
    resumen: str | None = None
    dirigido: str | None = None
    requisitos: list[Item] = field(default_factory=list)
    pasos: list[Item] = field(default_factory=list)
    costo: str | None = None
    duracion: str | None = None
    cta_url: str | None = None
    avisos: list[Aviso] = field(default_factory=list)

    @property
    def campos_ausentes(self) -> list[str]:
        faltan = []
        for nombre, valor in (
            ("costo", self.costo),
            ("duracion", self.duracion),
            ("requisitos", self.requisitos or None),
            ("pasos", self.pasos or None),
        ):
            if not valor:
                faltan.append(nombre)
        return faltan


def _normalizar(texto: str) -> str:
    return re.sub(r"[^a-z ]", "", texto.lower().translate(RE_ACENTOS)).strip()


def _seccion_de(titulo: str) -> str | None:
    normalizado = _normalizar(titulo)
    for clave, variantes in SECCIONES.items():
        if any(normalizado.startswith(v) for v in variantes):
            return clave
    return None


def _items_de_primer_nivel(contenedor: Node) -> list[Item]:
    """Ítems de la lista, sin aplanar los anidados.

    Un paso que aclara tres cosas es un paso con tres aclaraciones, no cuatro
    pasos. Aplanar la lista es la forma más común de convertir una ficha de
    cinco pasos en una de ocho, y de que el «primer paso» que se le responde a
    alguien sea en realidad un detalle del segundo.

    Las aclaraciones no se descartan: quedan como detalle del paso al que
    pertenecen.
    """
    listas = [n for n in contenedor.css("ol, ul") if _es_raiz(n)]
    if not listas:
        listas = contenedor.css("ol, ul")[:1]
    items: list[Item] = []
    for lista in listas[:1]:
        for li in lista.iter():
            if li.tag != "li":
                continue
            propio, detalle = _partir(li)
            if propio or detalle:
                items.append(Item(texto=propio, detalle=detalle))
    return items


def _es_raiz(nodo: Node) -> bool:
    """La lista no está adentro de otro `li`: es de primer nivel."""
    padre = nodo.parent
    while padre is not None:
        if padre.tag == "li":
            return False
        if padre.tag in ("body", "html"):
            break
        padre = padre.parent
    return True


def _partir(li: Node) -> tuple[str, list[str]]:
    """Separa el texto del ítem del de sus sublistas.

    La sublista puede estar anidada dentro de un `div` o un `p`, así que no
    alcanza con saltear los hijos directos: se resta el texto de cada sublista
    del texto completo.
    """
    completo = _limpio(li)
    detalle: list[str] = []
    for sub in li.css("ol, ul"):
        for hijo in sub.iter():
            if hijo.tag == "li":
                texto = _limpio(hijo)
                if texto:
                    detalle.append(texto)
        texto_sub = _limpio(sub)
        if texto_sub and texto_sub in completo:
            completo = completo.replace(texto_sub, " ")
    return " ".join(completo.split()), detalle


def _limpio(nodo: Node) -> str:
    return " ".join(nodo.text(separator=" ", strip=True).split())


def leer_ficha(html: str, *, url: str = "") -> FichaTramite:
    arbol = HTMLParser(html)
    ficha = FichaTramite()

    principal = arbol.css_first("main") or arbol.body
    if principal is None:
        ficha.avisos.append(Aviso("La respuesta no tiene cuerpo HTML.", severidad=Severidad.HIGH))
        return ficha

    texto_plano = principal.text(separator=" ", strip=True).lower()
    if any(marca in texto_plano for marca in MARCAS_LOGIN) and len(texto_plano) < 2500:
        ficha.avisos.append(
            Aviso(
                f"{url}: la respuesta es una pantalla de acceso, no la ficha del trámite. "
                "Se registra el canal y el estado de acceso; no se autentica ni se publica "
                "como trámite completo.",
                tipo=TipoIncidencia.ACCESO_BLOQUEADO,
                severidad=Severidad.HIGH,
            )
        )
        return ficha

    encabezado = principal.css_first("h1")
    if encabezado is not None:
        ficha.titulo = encabezado.text(strip=True) or None

    for h2 in principal.css("h2"):
        seccion = _seccion_de(h2.text(strip=True))
        if seccion is None:
            continue
        contenedor = h2.parent
        if contenedor is None:
            continue
        if seccion == "requisitos":
            ficha.requisitos = _items_de_primer_nivel(contenedor)
        elif seccion == "pasos":
            ficha.pasos = _items_de_primer_nivel(contenedor)
        elif seccion == "dirigido":
            ficha.dirigido = _sin_encabezado(contenedor, h2)

    # Costo y duración vienen en campos propios del portal. Un campo presente y
    # vacío es la información de que no está informado, no un cero.
    ficha.costo = _campo(principal, "field-costo")
    ficha.duracion = _campo(principal, "field-duracion")

    enlace = _cta(principal)
    if enlace:
        ficha.cta_url = enlace

    for nombre, valor in (("costo", ficha.costo), ("duración", ficha.duracion)):
        if valor is None:
            ficha.avisos.append(
                Aviso(
                    f"La ficha no informa {nombre}. Queda sin valor: no se asigna cero ni "
                    "«gratuito» ni «inmediato» sin evidencia explícita.",
                    tipo=TipoIncidencia.DATO_FALTANTE_CRITICO,
                    severidad=Severidad.MEDIUM,
                )
            )
    return ficha


def _sin_encabezado(contenedor: Node, encabezado: Node) -> str | None:
    texto = contenedor.text(separator=" ", strip=True)
    titulo = encabezado.text(strip=True)
    limpio = " ".join(texto.replace(titulo, "", 1).split())
    return limpio or None


def _campo(principal: Node, clase: str) -> str | None:
    nodo = principal.css_first(f"[class*={clase}]")
    if nodo is None:
        return None
    texto = " ".join(nodo.text(separator=" ", strip=True).split())
    return texto or None


def _cta(principal: Node) -> str | None:
    for enlace in principal.css("a[href^=http]"):
        clases = (enlace.attributes.get("class") or "").lower()
        if "btn" in clases or "cta" in clases:
            return enlace.attributes.get("href")
    return None


class AdaptadorTramiteArgentina:
    """Fichas de trámite del portal nacional."""

    nombre = "tramite_argentina"

    def acepta(self, captura: CapturaMaterial) -> bool:
        url = captura.url_final.lower()
        return any(d in url for d in DOMINIOS) and MARCA_SERVICIO in url

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion:
        resultado = ResultadoExtraccion()
        html = decodificar_html(captura.contenido, charset_declarado=captura.charset)
        ficha = leer_ficha(html, url=captura.url_final)

        if ficha.titulo is None and not ficha.pasos:
            resultado.avisos.extend(ficha.avisos)
            resultado.avisos.append(
                Aviso(
                    f"{captura.url_final}: no se reconoció la estructura de ficha de trámite. "
                    "La captura queda guardada sin extraer.",
                    severidad=Severidad.MEDIUM,
                )
            )
            return resultado

        cuerpo = _texto_de(ficha)
        documento = DocumentoExtraido(
            tipo=TipoDocumento.PROCEDIMIENTO,
            tipo_version=TipoVersionDocumento.NO_DETERMINADO,
            modo_extraccion=ModoExtraccion.HTML,
            texto=cuerpo,
            titulo=ficha.titulo,
            external_id=f"tramite:{captura.source_id}",
            identidad={
                "tramite": {
                    "titulo": ficha.titulo,
                    "dirigido": ficha.dirigido,
                    "requisitos": [
                        {"texto": r.texto, "detalle": r.detalle} for r in ficha.requisitos
                    ],
                    "pasos": [{"texto": p.texto, "detalle": p.detalle} for p in ficha.pasos],
                    "costo": ficha.costo,
                    "duracion": ficha.duracion,
                    "cta_url": ficha.cta_url,
                    "campos_ausentes": ficha.campos_ausentes,
                }
            },
            avisos=list(ficha.avisos),
        )
        resultado.documentos.append(documento)
        return resultado


def _texto_de(ficha: FichaTramite) -> str:
    partes = [ficha.titulo or "", ficha.dirigido or ""]
    for requisito in ficha.requisitos:
        partes.append(f"Requisito: {requisito.texto}")
        partes += [f"  {d}" for d in requisito.detalle]
    for numero, paso in enumerate(ficha.pasos, start=1):
        partes.append(f"Paso {numero}: {paso.texto}")
        partes += [f"  {d}" for d in paso.detalle]
    if ficha.costo:
        partes.append(f"Costo: {ficha.costo}")
    if ficha.duracion:
        partes.append(f"Duración: {ficha.duracion}")
    return "\n".join(p for p in partes if p)
