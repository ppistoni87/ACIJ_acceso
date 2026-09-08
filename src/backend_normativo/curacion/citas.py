"""Reconocimiento de citas a otras normas dentro de un texto.

Separado de la construcción de relaciones porque son dos problemas distintos:
encontrar que un texto menciona la Ley 24.714 es reconocimiento de patrones;
decidir qué relación jurídica hay entre ambas normas es interpretación.

La dirección importa y depende de la voz. "Norma abrogada por el Decreto
1382/01" pone al decreto como origen; "Deróganse la Ley 18.017 y sus
modificatorias" pone a la norma que lo dice como origen. Confundirlas invierte
la relación y hace que el corpus afirme lo contrario de lo que dice la fuente.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend_normativo.db.vocabularios import TipoNorma, TipoRelacionNormativa

TIPOS_CITABLES: dict[str, TipoNorma] = {
    "ley": TipoNorma.LEY,
    "leyes": TipoNorma.LEY,
    "decreto": TipoNorma.DECRETO,
    "decretos": TipoNorma.DECRETO,
    "resolución": TipoNorma.RESOLUCION,
    "resolucion": TipoNorma.RESOLUCION,
    "resoluciones": TipoNorma.RESOLUCION,
    "disposición": TipoNorma.DISPOSICION,
    "disposicion": TipoNorma.DISPOSICION,
    "ordenanza": TipoNorma.ORDENANZA,
    "ordenanzas": TipoNorma.ORDENANZA,
    "acordada": TipoNorma.ACORDADA,
}

# El número puede venir con separador de miles tipográfico. La forma con
# puntos va primero: si se probara `\d{1,3}` antes, "1382/01" se leería como
# número 138 y el año se perdería.
NUMERO = r"\d{1,3}(?:\.\d{3})+|\d+"

# "Ley N° 24.714", "Decreto Nº 1382/01", "Ordenanza 43.478", "Leyes Nros. 22.431, 24.013".
RE_CITA = re.compile(
    r"\b(?P<tipo>Ley(?:es)?|Decretos?|Resoluci[oó]n(?:es)?|Disposici[oó]n(?:es)?|"
    r"Ordenanzas?|Acordadas?)\s+"
    r"(?:N(?:ros?)?[°º.]?\s*)?"
    r"(?P<numero>" + NUMERO + r")"
    r"(?:\s*/\s*(?P<anio>\d{2,4}))?",
    re.IGNORECASE,
)

# Continuación de una enumeración: "Leyes Nros. 22.431, 24.013, 24.241 y 24.714".
# Sin esto se perderían todas las dependencias menos la primera.
RE_CONTINUACION = re.compile(
    r"\s*(?:,|;|\s+y\s+|\s+e\s+)\s*(?:N(?:ros?)?[°º.]?\s*)?"
    r"(?P<numero>" + NUMERO + r")"
    r"(?:\s*/\s*(?P<anio>\d{2,4}))?"
)

# Cuando la cita es la que actúa sobre el texto en curso.
MARCAS_PASIVAS: tuple[tuple[str, TipoRelacionNormativa], ...] = (
    ("restablecida su vigencia por", TipoRelacionNormativa.RESTABLECE),
    ("restablecido su vigencia por", TipoRelacionNormativa.RESTABLECE),
    ("abrogada por", TipoRelacionNormativa.ABROGA),
    ("abrogado por", TipoRelacionNormativa.ABROGA),
    ("derogada por", TipoRelacionNormativa.DEROGA),
    ("derogado por", TipoRelacionNormativa.DEROGA),
    ("sustituida por", TipoRelacionNormativa.SUSTITUYE),
    ("sustituido por", TipoRelacionNormativa.SUSTITUYE),
    ("modificada por", TipoRelacionNormativa.MODIFICA),
    ("modificado por", TipoRelacionNormativa.MODIFICA),
    ("incorporado por", TipoRelacionNormativa.INCORPORA),
    ("incorporada por", TipoRelacionNormativa.INCORPORA),
    ("reglamentada por", TipoRelacionNormativa.REGLAMENTA),
    ("reglamentado por", TipoRelacionNormativa.REGLAMENTA),
    ("prorrogada por", TipoRelacionNormativa.PRORROGA),
    ("prorrogado por", TipoRelacionNormativa.PRORROGA),
    ("suspendida por", TipoRelacionNormativa.SUSPENDE),
    ("suspendido por", TipoRelacionNormativa.SUSPENDE),
)

# Cuando el texto en curso actúa sobre la cita.
MARCAS_ACTIVAS: tuple[tuple[str, TipoRelacionNormativa], ...] = (
    ("der[oó]g[ae]n?se", TipoRelacionNormativa.DEROGA),
    ("abr[oó]g[ae]n?se", TipoRelacionNormativa.ABROGA),
    ("sust[ií]t[uú]y[ae]n?se", TipoRelacionNormativa.SUSTITUYE),
    ("modif[ií]c[ae]n?se", TipoRelacionNormativa.MODIFICA),
    ("incorp[oó]r[ae]n?se", TipoRelacionNormativa.INCORPORA),
    ("reglam[eé]nt[ae]n?se", TipoRelacionNormativa.REGLAMENTA),
    ("prorr[oó]g[ae]n?se", TipoRelacionNormativa.PRORROGA),
    ("susp[eé]nd[ae]n?se", TipoRelacionNormativa.SUSPENDE),
    ("restabl[eé]c[ae]n?se", TipoRelacionNormativa.RESTABLECE),
    ("restit[uú]y[ae]n?se", TipoRelacionNormativa.RESTABLECE),
)

RE_MARCAS_ACTIVAS = {
    tipo: re.compile(rf"\b{patron}\b", re.IGNORECASE) for patron, tipo in MARCAS_ACTIVAS
}

# Ventana de texto anterior a la cita donde se busca el verbo que la gobierna.
VENTANA = 140


@dataclass(frozen=True)
class CitaDetectada:
    tipo_norma: TipoNorma
    numero: str
    anio: int | None
    texto_cita: str
    posicion: int
    relacion: TipoRelacionNormativa
    # `True` si la norma citada es la que actúa sobre el texto en curso.
    citada_es_origen: bool
    contexto: str


def _normalizar_anio(anio: str | None) -> int | None:
    """`01` en "Decreto 1382/01" es 2001, no el año 1.

    Se resuelve con la ventana habitual de dos dígitos: por encima de 40 el
    siglo es el XX. No hay normas argentinas citadas con año de dos dígitos que
    caigan fuera de ese rango.
    """
    if not anio:
        return None
    valor = int(anio)
    if valor >= 1000:
        return valor
    return 1900 + valor if valor > 40 else 2000 + valor


def detectar_citas(texto: str) -> list[CitaDetectada]:
    """Citas a otras normas con la relación que sugiere su contexto.

    Cuando el contexto no permite decidir, la relación es `CITA`: mencionar una
    norma no prueba que se la modifique.
    """
    citas: list[CitaDetectada] = []
    for coincidencia in RE_CITA.finditer(texto):
        tipo = TIPOS_CITABLES.get(coincidencia.group("tipo").lower())
        if tipo is None:
            continue
        inicio = coincidencia.start()
        contexto = texto[max(0, inicio - VENTANA) : inicio].lower()

        relacion = TipoRelacionNormativa.CITA
        citada_es_origen = False

        for marca, tipo_relacion in MARCAS_PASIVAS:
            if marca in contexto:
                relacion = tipo_relacion
                citada_es_origen = True
                break
        else:
            for tipo_relacion, patron in RE_MARCAS_ACTIVAS.items():
                if patron.search(contexto):
                    relacion = tipo_relacion
                    citada_es_origen = False
                    break

        contexto_completo = texto[max(0, inicio - VENTANA) : coincidencia.end() + 60].strip()
        citas.append(
            CitaDetectada(
                tipo_norma=tipo,
                numero=coincidencia.group("numero").replace(".", ""),
                anio=_normalizar_anio(coincidencia.group("anio")),
                texto_cita=coincidencia.group(0),
                posicion=inicio,
                relacion=relacion,
                citada_es_origen=citada_es_origen,
                contexto=contexto_completo,
            )
        )
        citas.extend(
            _continuaciones(
                texto, coincidencia.end(), tipo, relacion, citada_es_origen, contexto_completo
            )
        )
    return citas


def _continuaciones(
    texto: str,
    desde: int,
    tipo: TipoNorma,
    relacion: TipoRelacionNormativa,
    citada_es_origen: bool,
    contexto: str,
) -> list[CitaDetectada]:
    """Números que continúan una enumeración del mismo tipo de norma."""
    encontradas: list[CitaDetectada] = []
    cursor = desde
    while True:
        siguiente = RE_CONTINUACION.match(texto, cursor)
        if siguiente is None:
            return encontradas
        encontradas.append(
            CitaDetectada(
                tipo_norma=tipo,
                numero=siguiente.group("numero").replace(".", ""),
                anio=_normalizar_anio(siguiente.group("anio")),
                texto_cita=siguiente.group(0).strip(" ,;"),
                posicion=siguiente.start(),
                relacion=relacion,
                citada_es_origen=citada_es_origen,
                contexto=contexto,
            )
        )
        cursor = siguiente.end()
