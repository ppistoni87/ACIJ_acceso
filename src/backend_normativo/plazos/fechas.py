"""HU-016: normalizar fechas de un texto sin inventar el año.

«Del 20 de diciembre al 10 de enero» es una convocatoria real y no dice de qué
año es. Las dos maneras de arruinarlo son igual de fáciles: ponerle el año en
curso, o ponerle el que viene porque enero es después de diciembre. Las dos
producen un rango exacto, verosímil y posiblemente equivocado, y quien lo lea
va a organizar un trámite alrededor de esa fecha.

Este módulo devuelve tres cosas distintas y no las confunde:

* **Resuelto**: el texto declara los dos años.
* **Derivado**: el texto declara uno solo y el otro sale de que el rango cruza
  el fin de año. Se resuelve y se dice que se derivó, con el motivo. Derivar no
  es el problema; derivar en silencio sí.
* **Pendiente de contexto**: el texto no declara ningún año. No se completa.

Un ciclo lectivo declarado **no** fecha el rango. «Inscripción para el ciclo
lectivo 2026, del 20 de diciembre al 10 de enero» no dice si esos días son de
2025 o de 2026: la inscripción para un ciclo suele hacerse el año anterior, y
equiparar el año del ciclo con el de los días es la misma suposición silenciosa
vista del otro lado. El ciclo se registra —le ahorra el trabajo a quien lo
resuelva— y el rango queda pendiente.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

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

_MESES_ALT = "|".join(MESES)

RE_RANGO = re.compile(
    rf"\bdel?\s+(?P<d1>\d{{1,2}})\s*(?:de\s+)?(?P<m1>{_MESES_ALT})"
    rf"(?:\s+(?:de[l]?\s+)?(?P<a1>(?:19|20)\d{{2}}))?"
    rf"\s+(?:al?|hasta\s+el)\s+(?P<d2>\d{{1,2}})\s*(?:de\s+)?(?P<m2>{_MESES_ALT})"
    rf"(?:\s+(?:de[l]?\s+)?(?P<a2>(?:19|20)\d{{2}}))?",
    re.IGNORECASE,
)

RE_CICLO = re.compile(r"ciclo\s+(?:lectivo\s+)?(?P<anio>(?:19|20)\d{2})", re.IGNORECASE)
RE_CONVOCATORIA = re.compile(r"convocatoria\s+(?P<anio>(?:19|20)\d{2})", re.IGNORECASE)


@dataclass
class RangoNormalizado:
    """Un rango leído del texto, resuelto o explícitamente pendiente."""

    texto: str
    inicio: dt.date | None = None
    fin: dt.date | None = None
    ciclo: int | None = None
    derivado: bool = False
    motivo: str = ""
    requiere: str | None = None

    @property
    def resuelto(self) -> bool:
        return self.inicio is not None and self.fin is not None

    @property
    def cruza_anio(self) -> bool:
        return self.resuelto and self.inicio.year != self.fin.year


def normalizar_rangos(texto: str, *, contexto_anio: int | None = None) -> list[RangoNormalizado]:
    """Todos los rangos de fecha del texto, cada uno con su estado.

    `contexto_anio` es un año que alguien aporta a sabiendas —quien resuelve la
    incidencia, no el reloj—. No sale del texto ni de la fecha de hoy: usar el
    año en curso para fechar un texto es exactamente lo que este módulo evita.
    """
    ciclo = _ciclo_declarado(texto)
    return [_normalizar(c, contexto_anio, ciclo) for c in RE_RANGO.finditer(texto)]


def _ciclo_declarado(texto: str) -> int | None:
    for patron in (RE_CICLO, RE_CONVOCATORIA):
        coincidencia = patron.search(texto)
        if coincidencia:
            return int(coincidencia.group("anio"))
    return None


def _normalizar(
    coincidencia: re.Match, contexto_anio: int | None, ciclo: int | None
) -> RangoNormalizado:
    rango = RangoNormalizado(texto=" ".join(coincidencia.group(0).split()), ciclo=ciclo)
    mes1 = MESES[coincidencia.group("m1").lower()]
    mes2 = MESES[coincidencia.group("m2").lower()]
    dia1 = int(coincidencia.group("d1"))
    dia2 = int(coincidencia.group("d2"))
    anio1 = int(coincidencia.group("a1")) if coincidencia.group("a1") else None
    anio2 = int(coincidencia.group("a2")) if coincidencia.group("a2") else None

    if anio1 is None and anio2 is None:
        if contexto_anio is None:
            rango.motivo = (
                "Ninguno de los dos extremos declara su año. No se completa con el año en "
                "curso: un rango que empieza en diciembre puede ser del año pasado, de este o "
                "del que viene, y las tres lecturas son verosímiles."
            )
            if ciclo is not None:
                rango.motivo += (
                    f" El texto menciona el ciclo {ciclo}, que queda registrado, pero no dice "
                    "si la inscripción ocurre ese año o el anterior."
                )
            rango.requiere = "anio_de_las_fechas"
            return rango
        anio1 = contexto_anio
        rango.derivado = True
        rango.motivo = (
            f"Los días no llevan año; se fecharon con el {contexto_anio} que aportó quien "
            "resolvió la incidencia, no el texto."
        )

    if anio1 is None:
        anio1 = anio2
    inicio = _fecha(anio1, mes1, dia1)
    if inicio is None:
        rango.motivo = f"La fecha de inicio no existe en el calendario: {dia1}/{mes1}."
        rango.requiere = "fecha_valida"
        return rango

    if anio2 is None:
        # Un rango que termina antes de empezar cruza el fin de año. Se deriva y
        # se dice; lo que no se hace es sumar un año sin dejar constancia.
        anio2 = anio1 + 1 if (mes2, dia2) < (mes1, dia1) else anio1
        if anio2 != anio1:
            rango.derivado = True
            rango.motivo = (
                (rango.motivo + " ").strip()
                + f" El fin cae antes que el inicio, así que el rango cruza el fin de año y "
                f"el cierre se fechó en {anio2}."
            ).strip()

    fin = _fecha(anio2, mes2, dia2)
    if fin is None:
        rango.motivo = f"La fecha de cierre no existe en el calendario: {dia2}/{mes2}."
        rango.requiere = "fecha_valida"
        return rango

    rango.inicio = inicio
    rango.fin = fin
    if not rango.motivo:
        rango.motivo = "Los dos extremos declaran su año."
    return rango


def _fecha(anio: int, mes: int, dia: int) -> dt.date | None:
    try:
        return dt.date(anio, mes, dia)
    except ValueError:
        return None
