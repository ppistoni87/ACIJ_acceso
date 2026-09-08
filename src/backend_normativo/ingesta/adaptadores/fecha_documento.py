"""HU-F67 · AT-075: de qué año es este documento, y de dónde sale ese año.

Un PDF firmado en 2025 puede estar colgado de `/sites/default/files/2021/08/`,
y un anexo llamarse `...-1621-25-ANX.pdf`. La ruta es dónde lo guardaron, no
cuándo lo firmaron: en el corpus hay tres PDF cuya carpeta declara un año y
ninguno de los tres lo confirma en su texto.

Adentro del documento tampoco alcanza con encontrar una fecha. El Decreto 690/06
consolidado trae treinta y cuatro, todas de 2008 a 2025, y ninguna lo fecha:
cada una está en una nota de consolidación que fecha el decreto que lo modificó.
Tomar la primera daría 2008; tomar la última, 2025. Es un decreto de 2006.

Así que una fecha sólo fecha el documento cuando el texto dice que lo fecha: un
encabezado de lugar y fecha, o una fórmula de sanción. Las demás se leen, se
clasifican y se reportan —las de las notas identifican el acto que modificó, que
es un dato aparte y útil— pero no se usan.
"""

from __future__ import annotations

import datetime as dt
import re
import urllib.parse
from dataclasses import dataclass, field

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

_MES = "|".join(MESES)
_ANIO = r"(?:1[89]|20)\d{2}"

RE_FECHA_NUMERICA = re.compile(rf"\b(\d{{1,2}})/(\d{{1,2}})/({_ANIO})\b")
RE_FECHA_LARGA = re.compile(rf"\b(\d{{1,2}})\s+de\s+({_MES})\s+de\s+({_ANIO})\b", re.IGNORECASE)

# «Buenos Aires, 12 de abril de 2006»: el encabezado con el que un acto declara
# dónde y cuándo se dictó.
RE_ENCABEZADO = re.compile(
    rf"(?:^|\n)[^\S\n]*[A-ZÁÉÍÓÚÑ][^\n,]{{2,60}},\s*(\d{{1,2}})\s+de\s+({_MES})\s+de\s+({_ANIO})",
    re.IGNORECASE,
)
# «...a los 12 días del mes de abril de 2006»: la fórmula de sanción.
RE_SALA = re.compile(
    rf"a\s+los\s+(\d{{1,2}})\s+d[ií]as\s+del\s+mes\s+de\s+({_MES})\s+de(?:l\s+a[ñn]o)?\s+({_ANIO})",
    re.IGNORECASE,
)

# Una nota de consolidación fecha el acto que modificó, no éste.
VERBOS_DE_MODIFICACION = (
    "sustituid",
    "incorporad",
    "modificad",
    "derogad",
    "observad",
    "reemplazad",
)
RE_NORMA_CITADA = re.compile(
    r"\b(Decreto|Ley|Resoluci[óo]n|Disposici[óo]n|Ordenanza)\s+N?[°º]?\s*"
    r"(\d[\d.]*)\s*/\s*(\d{2,4})",
    re.IGNORECASE,
)

# Lo que la ruta insinúa: `/files/2021/08/`, `/2026-08/`, `...-1621-25-ANX.pdf`.
RE_ANIO_EN_RUTA = re.compile(rf"(?<!\d)({_ANIO})(?:[-/](\d{{1,2}}))?(?!\d)")

DATA_EL_DOCUMENTO = "DATA_EL_DOCUMENTO"
DATA_OTRO_ACTO = "DATA_OTRO_ACTO"
SIN_CONTEXTO = "SIN_CONTEXTO"


@dataclass
class FechaHallada:
    fecha: dt.date
    texto: str
    clase: str
    contexto: str
    norma_citada: str | None = None


@dataclass
class LecturaDeFecha:
    fecha: dt.date | None = None
    tipo_fecha: str = "DESCONOCIDA"
    anio_en_la_ruta: int | None = None
    halladas: list[FechaHallada] = field(default_factory=list)
    motivo: str = ""

    @property
    def actos_citados(self) -> list[str]:
        """Los actos que las notas de consolidación identifican."""
        vistos: dict[str, None] = {}
        for h in self.halladas:
            if h.clase == DATA_OTRO_ACTO and h.norma_citada:
                vistos.setdefault(h.norma_citada, None)
        return list(vistos)

    @property
    def determinada(self) -> bool:
        return self.fecha is not None


def anio_en_la_ruta(url: str) -> int | None:
    """El año que insinúa la ruta. Se calcula para decir que no se usa."""
    camino = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
    coincidencias = RE_ANIO_EN_RUTA.findall(camino)
    return int(coincidencias[0][0]) if coincidencias else None


def _fecha(dia: str, mes: str, anio: str) -> dt.date | None:
    numero = MESES.get(mes.lower()) if not mes.isdigit() else int(mes)
    if numero is None:
        return None
    try:
        return dt.date(int(anio), numero, int(dia))
    except ValueError:
        # Un 31 de febrero es un error de lectura, no una fecha.
        return None


def _parentesis(texto: str, posicion: int) -> str | None:
    """El paréntesis más externo que envuelve la posición, si hay uno.

    Se busca el externo y no el más cercano porque las notas de consolidación
    llevan paréntesis adentro —«…Decreto 148/2021 (B.O. 6112). Vigencia: a
    partir de (…)»—: quedarse con el interno pierde la nota entera y con ella
    el verbo que dice que esa fecha es de otro acto.
    """
    profundidad = 0
    inicio = -1
    for i, caracter in enumerate(texto):
        if caracter == "(":
            if profundidad == 0:
                inicio = i
            profundidad += 1
        elif caracter == ")" and profundidad > 0:
            profundidad -= 1
            if profundidad == 0:
                if inicio <= posicion < i:
                    return texto[inicio : i + 1]
                if i > posicion:
                    return None
    return None


def _contexto(texto: str, inicio: int, fin: int) -> str:
    return " ".join(texto[max(0, inicio - 120) : fin + 40].split())


def leer(texto: str, *, url: str | None = None) -> LecturaDeFecha:
    """Qué fecha tiene el documento según su propio texto."""
    lectura = LecturaDeFecha(anio_en_la_ruta=anio_en_la_ruta(url) if url else None)
    if not texto.strip():
        lectura.motivo = (
            "El documento no dejó texto extraíble: no hay de dónde leer la fecha. "
            "La ruta no la reemplaza."
        )
        return lectura

    fechan_el_documento = _las_que_fechan(texto)

    for inicio, fin, crudo, partes in _candidatas(texto):
        fecha = _fecha(*partes)
        if fecha is None:
            continue
        citada = _acto_citado(_parentesis(texto, inicio))
        if citada:
            clase, norma = DATA_OTRO_ACTO, citada
        elif fecha in fechan_el_documento:
            clase, norma = DATA_EL_DOCUMENTO, None
        else:
            clase, norma = SIN_CONTEXTO, None
        lectura.halladas.append(
            FechaHallada(
                fecha=fecha,
                texto=crudo,
                clase=clase,
                contexto=_contexto(texto, inicio, fin),
                norma_citada=norma,
            )
        )

    _resolver(lectura)
    return lectura


def _candidatas(texto: str) -> list[tuple[int, int, str, tuple[str, str, str]]]:
    """Cada fecha que aparece en el texto, una sola vez.

    Una fórmula de sanción —«a los 12 días del mes de diciembre de 2019»— no la
    encuentra el patrón de fecha común, y el encabezado sí: hay que mirar los
    tres y después quedarse con el tramo más largo de los que se pisan.
    """
    crudas: list[tuple[int, int, str, tuple[str, str, str]]] = []
    for expresion in (RE_FECHA_NUMERICA, RE_FECHA_LARGA, RE_SALA):
        for m in expresion.finditer(texto):
            crudas.append((m.start(), m.end(), m.group(0), (m.group(1), m.group(2), m.group(3))))
    crudas.sort(key=lambda c: (c[0], -(c[1] - c[0])))

    sin_pisarse: list[tuple[int, int, str, tuple[str, str, str]]] = []
    for candidata in crudas:
        if any(i <= candidata[0] and candidata[1] <= f for i, f, _, _ in sin_pisarse):
            continue
        sin_pisarse.append(candidata)
    return sin_pisarse


def _las_que_fechan(texto: str) -> set[dt.date]:
    """Las fechas que una fórmula declara como fecha del propio acto."""
    encontradas: set[dt.date] = set()
    for expresion in (RE_ENCABEZADO, RE_SALA):
        for m in expresion.finditer(texto):
            fecha = _fecha(m.group(1), m.group(2), m.group(3))
            if fecha is not None:
                encontradas.add(fecha)
    return encontradas


def _acto_citado(envoltura: str | None) -> str | None:
    """El acto que una nota de consolidación nombra, si la envoltura es una."""
    if not envoltura:
        return None
    minuscula = envoltura.lower()
    if not any(v in minuscula for v in VERBOS_DE_MODIFICACION):
        return None
    m = RE_NORMA_CITADA.search(envoltura)
    if m is None:
        return "acto no identificado"
    return f"{m.group(1).capitalize()} {m.group(2)}/{m.group(3)}"


def _plural(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _resolver(lectura: LecturaDeFecha) -> None:
    propias = [h for h in lectura.halladas if h.clase == DATA_EL_DOCUMENTO]
    de_otros = [h for h in lectura.halladas if h.clase == DATA_OTRO_ACTO]
    sueltas = [h for h in lectura.halladas if h.clase == SIN_CONTEXTO]

    if len({h.fecha for h in propias}) == 1:
        lectura.fecha = propias[0].fecha
        lectura.tipo_fecha = "SANCION"
        lectura.motivo = (
            f"El documento declara su fecha: «{propias[0].texto}». "
            f"Contexto: …{propias[0].contexto}…"
        )
        return

    if len({h.fecha for h in propias}) > 1:
        fechas = ", ".join(sorted({h.fecha.isoformat() for h in propias}))
        lectura.motivo = (
            f"El documento declara más de una fecha ({fechas}) y ninguna manda sobre la otra. "
            "Queda pendiente en vez de elegirse una."
        )
        return

    partes = ["El documento no declara su fecha."]
    if de_otros:
        actos = ", ".join(lectura.actos_citados[:6])
        partes.append(
            f"Trae {_plural(len(de_otros), 'fecha', 'fechas')} en notas de consolidación, que "
            f"fechan al acto que modificó y no a éste ({actos}"
            + (", …" if len(lectura.actos_citados) > 6 else "")
            + ")."
        )
    if sueltas:
        partes.append(
            f"Hay {_plural(len(sueltas), 'fecha', 'fechas')} sin nada que diga qué fechan; "
            "una fecha suelta no es la del documento."
        )
    if lectura.anio_en_la_ruta:
        partes.append(
            f"La ruta sugiere {lectura.anio_en_la_ruta} y no se usa: es dónde lo guardaron, no "
            "cuándo lo firmaron."
        )
    partes.append("Queda pendiente hasta leerla del documento o del acto que lo aprueba.")
    lectura.motivo = " ".join(partes)
