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

# Marcas con las que una página declara que un bloque no está visible. No es
# una lista de estilos posibles: son las que los portales del corpus usan.
CLASES_OCULTAS = ("d-none", "hidden", "invisible", "sr-only", "visually-hidden")
RE_ESTILO_OCULTO = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)

SELECTOR_OCULTOS = ", ".join(
    [
        *(f"[class~={clase}]" for clase in CLASES_OCULTAS),
        "[hidden]",
        '[aria-hidden="true"]',
        "[style*=none]",
        "[style*=hidden]",
    ]
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


def _una_linea(nodo: Node) -> list[str]:
    """El bloque entero como un párrafo, que es el comportamiento de siempre."""
    texto = _texto_de_bloque(nodo)
    return [texto] if texto else []


def _lineas_de_bloque(nodo: Node) -> list[str]:
    """El bloque partido donde el HTML declara un salto de línea.

    Un salto en el código fuente es maquetación y no significa nada; un `<br>`
    sí, porque alguien lo escribió para cortar ahí. La diferencia importa
    cuando un portal publica una norma entera dentro de un solo `div` separando
    sus artículos con `<br>`: sin partir, la norma es un párrafo de veinte mil
    caracteres y el segmentador no encuentra un solo artículo adentro.

    Partir de más tampoco sirve —un renglón no es un párrafo—, y para eso está
    `unir_renglones`, que vuelve a juntar los que continúan la misma oración.
    Primero hay que tener los renglones.

    No se aplica en todas partes, y eso no es timidez. Partir por `<br>` cambia
    las rutas de las unidades de cualquier documento que use `<br>` para
    maquetar, y las lecturas curadas están ancladas a esas rutas: aplicarlo a
    todo el corpus rompió dieciséis de veinte lecturas en una corrida limpia. Lo
    pide el adaptador que sabe que su página lo necesita.
    """
    lineas: list[str] = []
    actual: list[str] = []
    for hijo in nodo.iter(include_text=True):
        if hijo.tag == "br":
            lineas.append(" ".join(actual))
            actual = []
            continue
        texto = hijo.text(separator=" ") if hijo.tag != "-text" else (hijo.text_content or "")
        if texto:
            actual.append(texto)
    lineas.append(" ".join(actual))
    limpias = [RE_BLANCOS.sub(" ", unicodedata.normalize("NFC", linea)).strip() for linea in lineas]
    return [linea for linea in limpias if linea]


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


def esta_oculto(nodo: Node) -> bool:
    """Si la página declara que este bloque no se ve.

    Una página puede tener el ciclo lectivo viejo y el nuevo en el mismo HTML,
    con el viejo escondido detrás de un `d-none`. Los dos textos son legítimos;
    lo que los distingue es que solo uno está publicado hoy. Extraer el oculto
    como si fuera el vigente es la forma más silenciosa de servir información
    del año pasado.
    """
    clases = (nodo.attributes.get("class") or "").split()
    if any(clase in CLASES_OCULTAS for clase in clases):
        return True
    if "hidden" in nodo.attributes:
        return True
    if (nodo.attributes.get("aria-hidden") or "").lower() == "true":
        return True
    return bool(RE_ESTILO_OCULTO.search(nodo.attributes.get("style") or ""))


def texto_oculto(html: str, *, selector: str | None = None) -> list[str]:
    """Los bloques que la página esconde, para poder decir que existen.

    No se descartan en silencio: que la página tenga un ciclo viejo escondido es
    información, y separarla del visible es lo que permite responder «esa
    inscripción es del ciclo anterior» en vez de no responder.
    """
    arbol = HTMLParser(html)
    for etiqueta in ETIQUETAS_IGNORADAS:
        for nodo in arbol.css(etiqueta):
            nodo.decompose()
    raiz = (arbol.css_first(selector) if selector else None) or arbol.body or arbol.root
    if raiz is None:
        return []

    encontrados: list[str] = []
    for nodo in raiz.css(SELECTOR_OCULTOS):
        if not esta_oculto(nodo):
            continue
        texto = _texto_de_bloque(nodo)
        if texto and not any(texto in visto or visto in texto for visto in encontrados):
            encontrados.append(texto)
    return encontrados


def parrafos_de_html(
    html: str, *, selector: str | None = None, partir_en_br: bool = False
) -> list[Parrafo]:
    """Convierte HTML en párrafos con su desplazamiento en el texto plano.

    Los desplazamientos son sobre el texto reconstruido, no sobre el HTML: son
    los que después permiten localizar una evidencia dentro de la versión.

    Lo que la página esconde no entra: `texto_oculto` lo devuelve aparte.
    """
    arbol = HTMLParser(html)
    for etiqueta in ETIQUETAS_IGNORADAS:
        for nodo in arbol.css(etiqueta):
            nodo.decompose()
    for nodo in arbol.css(SELECTOR_OCULTOS):
        if esta_oculto(nodo):
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
        for texto in _lineas_de_bloque(nodo) if partir_en_br else _una_linea(nodo):
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
