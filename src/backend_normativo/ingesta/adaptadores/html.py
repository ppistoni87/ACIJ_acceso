"""Utilidades de extracción de HTML.

Separadas del adaptador concreto porque todos los sitios normativos comparten el
mismo problema: pasar de marcado a párrafos sin perder el orden, los saltos que
separan disposiciones ni la marca de texto entrecomillado.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from backend_normativo.curacion.segmentacion import Parrafo

# Elementos que nunca aportan texto de la norma.
ETIQUETAS_IGNORADAS = frozenset(
    {"script", "style", "noscript", "nav", "header", "footer", "form", "svg", "button"}
)

# Elementos que separan disposiciones.
ETIQUETAS_BLOQUE = frozenset(
    {
        "p",
        "div",
        "li",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "pre",
        "dd",
        "dt",
        "dl",
        "ul",
        "ol",
        "table",
        "tbody",
        "section",
        "article",
        "main",
        "figcaption",
        "caption",
    }
)

RE_ESPACIOS = re.compile(r"[ \t   ]+")
RE_SALTOS = re.compile(r"\n{3,}")
RE_BLANCOS = re.compile(r"\s+")
COMILLAS_APERTURA = "\"“«'‘"
COMILLAS_CIERRE = "\"”»'’"


RE_META_CHARSET = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.IGNORECASE
)


def decodificar_html(contenido: bytes, *, charset_declarado: str | None = None) -> str:
    """Decodifica bytes de HTML sin adivinar.

    Varios boletines siguen sirviendo `windows-1252` o `iso-8859-1`. Decodificar
    todo como UTF-8 con reemplazo corrompe las tildes, y una tilde corrompida en
    "Artículo" hace que el segmentador no reconozca la unidad. El orden es:
    cabecera, `<meta charset>`, UTF-8 estricto y, recién ahí, `cp1252`, que es
    el juego histórico de esos sitios.
    """
    candidatos: list[str] = []
    if charset_declarado:
        candidatos.append(charset_declarado)
    coincidencia = RE_META_CHARSET.search(contenido[:4096])
    if coincidencia:
        candidatos.append(coincidencia.group(1).decode("ascii", "ignore"))
    candidatos.extend(["utf-8", "cp1252"])

    for codificacion in candidatos:
        try:
            return contenido.decode(codificacion)
        except (UnicodeDecodeError, LookupError):
            continue
    return contenido.decode("utf-8", errors="replace")


def normalizar_espacios(texto: str) -> str:
    """Colapsa espacios sin tocar los saltos que separan disposiciones."""
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = RE_ESPACIOS.sub(" ", texto)
    return RE_SALTOS.sub("\n\n", texto).strip()


def _texto_de_bloque(nodo: Node) -> str:
    """Texto de un bloque en una sola línea.

    Dentro de una disposición los saltos son maquetación, no estructura:
    conservarlos partiría un artículo en fragmentos que no significan nada.
    """
    return RE_BLANCOS.sub(" ", unicodedata.normalize("NFC", nodo.text(separator=" "))).strip()


# `css` sobre un nodo devuelve también el nodo si coincide, así que un bloque
# es hoja cuando su propia búsqueda no encuentra nada más que él mismo.
SELECTOR_BLOQUES = ", ".join(sorted(ETIQUETAS_BLOQUE))


def _tiene_bloques_adentro(nodo: Node) -> bool:
    """Si el bloque contiene otros bloques en cualquier profundidad.

    Mirar solo los hijos directos no alcanza: un `div` cuyo único hijo es una
    `dl` con `dt`/`dd` adentro parecería una hoja y duplicaría todo su texto.
    """
    return len(nodo.css(SELECTOR_BLOQUES)) > 1


def _entrecomillado(nodo: Node, texto: str) -> bool:
    """Si el fragmento viene marcado como transcripción.

    Dos señales: comillas que abren el párrafo, o el uso de `blockquote`, que es
    como algunos boletines marcan el texto sustituido.
    """
    if texto[:1] in COMILLAS_APERTURA:
        return True
    padre = nodo.parent
    profundidad = 0
    while padre is not None and profundidad < 4:
        if padre.tag == "blockquote":
            return True
        padre = padre.parent
        profundidad += 1
    return False


def parrafos_de_html(html: str, *, selector: str | None = None) -> list[Parrafo]:
    """Convierte HTML en párrafos con su desplazamiento en el texto plano.

    Los desplazamientos son sobre el texto reconstruido, no sobre el HTML: son
    los que después permiten localizar una evidencia dentro de la versión.
    """
    arbol = HTMLParser(html)
    for etiqueta in ETIQUETAS_IGNORADAS:
        for nodo in arbol.css(etiqueta):
            nodo.decompose()

    raiz = (arbol.css_first(selector) if selector else None) or arbol.body or arbol.root
    if raiz is None:
        return []

    parrafos: list[Parrafo] = []
    cursor = 0

    for nodo in raiz.traverse(include_text=False):
        if nodo.tag not in ETIQUETAS_BLOQUE:
            continue
        # Solo el bloque más profundo aporta el texto: si un div contiene tres
        # párrafos, el texto va tres veces si no se filtra.
        if _tiene_bloques_adentro(nodo):
            continue
        texto = _texto_de_bloque(nodo)
        if not texto:
            continue
        parrafos.append(
            Parrafo(
                texto=texto,
                inicio=cursor,
                fin=cursor + len(texto),
                entrecomillado=_entrecomillado(nodo, texto),
            )
        )
        cursor += len(texto) + 1

    return parrafos


def texto_plano(parrafos: list[Parrafo]) -> str:
    return "\n".join(p.texto for p in parrafos)


def enlaces_de(html: str, base_url: str, *, selector: str | None = None) -> list[tuple[str, str]]:
    """Enlaces absolutos y su texto visible, en orden de aparición."""
    arbol = HTMLParser(html)
    raiz = (arbol.css_first(selector) if selector else None) or arbol.body or arbol.root
    if raiz is None:
        return []
    enlaces: list[tuple[str, str]] = []
    for nodo in raiz.css("a[href]"):
        href = (nodo.attributes.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        enlaces.append((urljoin(base_url, href), normalizar_espacios(nodo.text())))
    return enlaces
