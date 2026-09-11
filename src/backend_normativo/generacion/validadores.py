"""Lo que una respuesta no puede decir aunque el modelo lo haya dicho.

El criterio 1 de P-013 pide rechazar tres cosas: citas inventadas, enlaces
ajenos al contexto y números sin soporte. Los tres son la misma idea desde
ángulos distintos —una respuesta no puede afirmar nada que sus fragmentos no
sostengan— y los tres se verifican contra el contexto, sin preguntarle al
modelo si está seguro.

Eso último importa. Un modelo que se equivoca no sabe que se equivocó, así que
pedirle que se autoevalúe agrega una opinión, no una verificación. Acá se
compara la respuesta contra los fragmentos recuperados, que es lo único que el
sistema sabe que es cierto porque lo leyó de una norma publicada.

El número es el caso más caro. «Te corresponden $85.000» con un número que no
está en ninguna cita es peor que no contestar: alguien planifica el mes con eso.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Una cita en la respuesta: [[chunk:<uuid>]]. El formato es explícito y feo a
# propósito: si el modelo escribe la cita en prosa —«según el artículo 3»— no
# hay forma de verificar a qué fragmento se refiere, y una cita que no se puede
# verificar no es una cita.
RE_CITA = re.compile(r"\[\[chunk:([0-9a-fA-F-]{36})\]\]")

RE_ENLACE = re.compile(r"https?://[^\s\)\]<>\"']+", re.I)

# Números con sustancia: importes, porcentajes, cantidades, años. Se ignoran los
# que forman parte de una cita y los ordinales sueltos de la redacción —«el
# primero», «los 3 pasos»— porque exigirle respaldo a cada dígito haría que
# ninguna respuesta pase y el validador se termine apagando.
RE_NUMERO = re.compile(r"(?<![\w-])\$?\s?\d[\d.,]{2,}(?:\s?%)?")


@dataclass
class Hallazgo:
    clase: str
    detalle: str


@dataclass
class Veredicto:
    """Si la respuesta se puede servir, y qué la descalifica cuando no."""

    hallazgos: list[Hallazgo] = field(default_factory=list)

    @property
    def sirve(self) -> bool:
        return not self.hallazgos

    def a_dict(self) -> dict:
        return {
            "sirve": self.sirve,
            "hallazgos": [{"clase": h.clase, "detalle": h.detalle} for h in self.hallazgos],
        }


def _normalizar_numero(bruto: str) -> str:
    """Deja el número en dígitos, sin símbolo ni separadores.

    «$ 85.000», «85000» y «85.000» son el mismo número escrito de tres formas, y
    exigir coincidencia literal haría que un importe correcto se rechace por un
    punto de miles.
    """
    return re.sub(r"[^\d]", "", bruto)


def verificar(texto: str, fragmentos: list) -> Veredicto:
    """Compara la respuesta contra los fragmentos que la sostienen.

    `fragmentos` son objetos con `chunk_id`, `texto` y `url_fuente`: lo que
    devuelve la recuperación.
    """
    veredicto = Veredicto()
    permitidos = {str(f.chunk_id) for f in fragmentos}
    contexto = " ".join(f.texto or "" for f in fragmentos)
    enlaces_del_contexto = set(RE_ENLACE.findall(contexto))
    enlaces_del_contexto |= {f.url_fuente for f in fragmentos if getattr(f, "url_fuente", None)}

    citadas = set(RE_CITA.findall(texto))
    for cita in sorted(citadas):
        if cita.lower() not in {p.lower() for p in permitidos}:
            veredicto.hallazgos.append(
                Hallazgo(
                    "cita_inventada",
                    f"La respuesta cita el fragmento {cita}, que no está entre los recuperados. "
                    "Una cita que no se puede abrir es peor que ninguna: parece verificada.",
                )
            )

    if not citadas and texto.strip():
        veredicto.hallazgos.append(
            Hallazgo(
                "sin_cita",
                "La respuesta no cita ningún fragmento. Este sistema no afirma nada sobre "
                "derechos sin señalar de dónde lo sacó.",
            )
        )

    for enlace in sorted(set(RE_ENLACE.findall(texto))):
        if not any(enlace.startswith(p) or p.startswith(enlace) for p in enlaces_del_contexto if p):
            veredicto.hallazgos.append(
                Hallazgo(
                    "enlace_ajeno",
                    f"La respuesta ofrece {enlace}, que no aparece en el contexto. Mandar a "
                    "alguien a una dirección inventada le cuesta un viaje.",
                )
            )

    digitos_del_contexto = {_normalizar_numero(n) for n in RE_NUMERO.findall(contexto)}
    texto_sin_citas = RE_CITA.sub(" ", texto)
    for bruto in sorted(set(RE_NUMERO.findall(texto_sin_citas))):
        normalizado = _normalizar_numero(bruto)
        if normalizado and normalizado not in digitos_del_contexto:
            veredicto.hallazgos.append(
                Hallazgo(
                    "numero_sin_soporte",
                    f"La respuesta dice «{bruto.strip()}» y ese número no está en ninguna cita. "
                    "Alguien planifica el mes con un importe: si no está en la norma, no se dice.",
                )
            )
    return veredicto
