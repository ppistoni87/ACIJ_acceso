"""HU-F54 · AT-022: los pasos de un instructivo en PDF.

Un instructivo numera sus pasos —«Paso 1», «Paso 2»— y entre un rótulo y el
siguiente está lo que hay que hacer. El orden lo fija el número que el documento
declara, no la posición en la que el extractor devuelve el texto: si un rótulo
sale después de su contenido, ordenar por lectura invierte el trámite y manda a
alguien a hacer el paso 4 antes que el 3.

Dos cosas que el documento real obliga a manejar. Los pasos cruzan de página: en
el instructivo de becas alimentarias el paso 4 empieza en la página 3 y su
documentación necesaria está en la 4, sin rótulo propio. Y cada página repite el
encabezado «Becas alimentarias» y termina con el número de folio, que no son
parte de ningún paso.

Un número repetido o un salto en la serie no se corrigen solos: se cargan los
pasos que hay y se dice cuál es el problema.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

RE_ROTULO = re.compile(r"^Paso\s+(?P<numero>\d{1,2})\b\s*[.:)-]?\s*(?P<resto>.*)$", re.IGNORECASE)

# El folio de la página: una línea que es sólo un número.
RE_FOLIO = re.compile(r"^\d{1,3}$")


@dataclass
class PasoLeido:
    numero: int
    titulo: str
    contenido: list[str] = field(default_factory=list)
    paginas: list[int] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return " ".join(self.contenido)


@dataclass
class LecturaDePasos:
    pasos: list[PasoLeido] = field(default_factory=list)
    encabezado_repetido: str | None = None
    avisos: list[str] = field(default_factory=list)

    @property
    def en_orden(self) -> list[PasoLeido]:
        """Ordenados por el número que declaran, no por dónde aparecieron."""
        return sorted(self.pasos, key=lambda p: p.numero)

    @property
    def consistente(self) -> bool:
        return not self.avisos


def encabezado_repetido(paginas: list[list[str]]) -> str | None:
    """La línea que se repite arriba de casi todas las páginas.

    Se detecta en vez de configurarse: cada instructivo tiene el suyo y una
    lista de encabezados conocidos envejece mal.
    """
    primeras = [pagina[0].strip() for pagina in paginas if pagina]
    if len(primeras) < 3:
        return None
    frecuente, veces = Counter(primeras).most_common(1)[0]
    return frecuente if veces >= len(primeras) - 1 and frecuente else None


def leer(paginas: list[list[str]]) -> LecturaDePasos:
    """Los pasos de un instructivo, a partir de las líneas de cada página."""
    lectura = LecturaDePasos()
    lectura.encabezado_repetido = encabezado_repetido(paginas)

    actual: PasoLeido | None = None
    for numero_pagina, lineas in enumerate(paginas, start=1):
        for linea in lineas:
            limpia = " ".join(linea.split())
            if not limpia or _es_furniture(limpia, lectura.encabezado_repetido):
                continue
            rotulo = RE_ROTULO.match(limpia)
            if rotulo:
                actual = PasoLeido(
                    numero=int(rotulo.group("numero")),
                    titulo=limpia,
                    paginas=[numero_pagina],
                )
                resto = rotulo.group("resto").strip()
                if resto:
                    actual.contenido.append(resto)
                lectura.pasos.append(actual)
                continue
            if actual is None:
                # Lo que viene antes del primer rótulo es portada o
                # introducción: no es el paso 1.
                continue
            actual.contenido.append(limpia)
            if numero_pagina not in actual.paginas:
                actual.paginas.append(numero_pagina)

    _revisar(lectura)
    return lectura


def _es_furniture(linea: str, encabezado: str | None) -> bool:
    return linea == encabezado or bool(RE_FOLIO.match(linea))


def _revisar(lectura: LecturaDePasos) -> None:
    numeros = [p.numero for p in lectura.pasos]
    repetidos = sorted({n for n in numeros if numeros.count(n) > 1})
    if repetidos:
        lectura.avisos.append(
            f"El documento numera más de una vez el/los paso(s) {repetidos}. Se cargan todos "
            "y queda la duplicación anotada: renumerar por orden de aparición inventaría una "
            "secuencia que el documento no declara."
        )
    if numeros:
        esperados = set(range(min(numeros), max(numeros) + 1))
        faltantes = sorted(esperados - set(numeros))
        if faltantes:
            lectura.avisos.append(
                f"Falta(n) el/los paso(s) {faltantes} entre los rótulos leídos. Puede estar en "
                "una página que no dejó texto; no se renumeran los que sí están."
            )
    vacios = [p.numero for p in lectura.pasos if not p.contenido]
    if vacios:
        lectura.avisos.append(
            f"El/los paso(s) {vacios} tienen rótulo y no tienen texto. Suelen ser pasos que "
            "sólo muestran una captura de pantalla: el rótulo se conserva y el contenido "
            "queda vacío en vez de heredar el del paso anterior."
        )
