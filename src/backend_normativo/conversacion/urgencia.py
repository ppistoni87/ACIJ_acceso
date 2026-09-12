"""Reconocer que un mensaje puede ser una emergencia (análisis del flujo, hallazgo 1).

Alguien escribió «estoy durmiendo en la calle, ¿hay algo urgente?» y el sistema
contestó con el artículo 10 de una ley. En un servicio público eso no es una
respuesta pobre: hay una clase de mensaje donde **el canal va primero y la norma
después**, y este sistema no la tenía.

Tres cosas que este módulo deliberadamente **no** hace:

* **No diagnostica.** No dice «estás en una emergencia»: dice «si esto es
  urgente, mirá acá». Quien sabe si es una emergencia es la persona, no un
  puñado de expresiones regulares.
* **No inventa a quién llamar.** Los canales son dato curado del corpus. Este
  módulo reconoce la clase de mensaje; con qué se la atiende lo define quien
  conoce los servicios de esa jurisdicción, y si no hay ninguno cargado el
  sistema lo dice en vez de improvisar un número.
* **No se activa por una palabra suelta.** «Violencia» aparece en el título de
  media docena de leyes; «calle» está en cualquier dirección. Se exige una
  expresión, y para las clases que dependen del momento —estar en la calle, no
  tener qué comer— se exige además que el mensaje hable del ahora. Un aviso que
  aparece siempre no distingue nada, y éste tiene que distinguir.

El conjunto de casos está congelado en `docs/calidad/urgencia.json`: agregar una
expresión obliga a decir qué casos pasa a reconocer y cuáles no, en el mismo
commit.
"""

from __future__ import annotations

import enum
import json
import pathlib
import re
import unicodedata
from dataclasses import dataclass


class ClaseUrgencia(enum.StrEnum):
    """Qué clase de emergencia parece. El orden es el de atención."""

    VIOLENCIA = "VIOLENCIA"
    SALUD = "SALUD"
    NINEZ = "NINEZ"
    CALLE = "CALLE"
    ALIMENTOS = "ALIMENTOS"


# Expresiones, no palabras, y cada una con lo que exige además de sí misma.
#
# * `None`  — la expresión alcanza sola. «Me pega» sólo lo escribe quien lo vive.
# * `MOMENTO` — hace falta que el mensaje hable del ahora. «Me quedé sin casa»
#   puede ser de hace cinco años; «me quedé sin casa y estoy en la calle» no.
# * `RELATO` — hace falta que la persona esté contando lo suyo y no preguntando
#   por la norma. «Violencia de género» es el nombre de media docena de leyes:
#   sin esto, «¿qué dice la ley sobre violencia de género?» disparaba la alarma.
#   Lo encontró el conjunto congelado.
#
# El requisito va por expresión y no por clase porque dentro de una misma clase
# conviven las dos cosas: «me pega» es un relato por construcción y «violencia
# familiar» es un tema.
MOMENTO = "momento"
RELATO = "relato"

EXPRESIONES: dict[ClaseUrgencia, tuple[tuple[str, str | None], ...]] = {
    ClaseUrgencia.VIOLENCIA: (
        (r"me pega\b", None),
        (r"me golpea", None),
        (r"me lastima", None),
        (r"me amenaza", None),
        (r"me quiere matar", None),
        (r"me viola\b", None),
        (r"tengo miedo de (mi|el|la) (pareja|marido|novio|ex|mujer)", None),
        (r"violencia de genero", RELATO),
        (r"violencia familiar", RELATO),
        (r"violencia domestica", RELATO),
        (r"abuso sexual", RELATO),
    ),
    ClaseUrgencia.SALUD: (
        (r"no puedo respirar", None),
        (r"me estoy descompensando", None),
        (r"emergencia medica", RELATO),
        (r"me estoy muriendo", None),
        (r"se esta muriendo", None),
        (r"perdi el conocimiento", None),
    ),
    ClaseUrgencia.NINEZ: (
        # En los dos órdenes: la gente escribe «con mi bebé en la calle» y
        # también «en la calle con mi bebé». Fijarse en uno solo dejaba la
        # mitad de los casos afuera, y los degradaba a una clase menos urgente.
        (r"con (mi|mis) (hijo|hija|hijos|hijas|bebe|nene|nena)s? en la calle", MOMENTO),
        (r"en la calle con (mi|mis) (hijo|hija|hijos|hijas|bebe|nene|nena)s?", MOMENTO),
        (r"(mi|mis) (hijo|hija|hijos|hijas|bebe)s? no (tiene|tienen) que comer", None),
        (r"(mi|mis) (hijo|hija|hijos|hijas)s? esta(n)? en la calle", MOMENTO),
    ),
    ClaseUrgencia.CALLE: (
        (r"durmiendo en la calle", MOMENTO),
        (r"duermo en la calle", MOMENTO),
        (r"dormi en la calle", MOMENTO),
        (r"estoy en la calle", MOMENTO),
        (r"estamos en la calle", MOMENTO),
        (r"vivo en la calle(?! [a-z])", MOMENTO),
        (r"me estan desalojando", None),
        (r"nos estan desalojando", None),
        (r"me desalojan hoy", None),
        (r"sin techo", MOMENTO),
        (r"a la intemperie", MOMENTO),
        (r"no tengo donde dormir", MOMENTO),
    ),
    ClaseUrgencia.ALIMENTOS: (
        (r"no tengo (nada )?que comer", MOMENTO),
        (r"no tenemos (nada )?que comer", MOMENTO),
        (r"hace dias que no como", None),
        (r"no tengo para comer", MOMENTO),
    ),
}

RE_AHORA = re.compile(
    r"\b(ahora|hoy|anoche|esta noche|en este momento|estoy|estamos|duermo|dormimos|"
    r"durmiendo|dormi|no tengo|no tenemos|hace dias|con mi|con mis)\b"
)
# Que la persona esté contando lo suyo, y no preguntando por la norma.
RE_RELATO = re.compile(r"\b(sufri|sufro|sufrimos|padezco|vivo|estoy|estamos|nos)\b|\bm[ei] ")

_COMPILADAS = {
    clase: tuple((re.compile(patron), exige) for patron, exige in patrones)
    for clase, patrones in EXPRESIONES.items()
}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: la gente escribe sin acentos y con apuro."""
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes)


@dataclass(frozen=True)
class Deteccion:
    clase: ClaseUrgencia | None = None
    expresion: str | None = None

    @property
    def hay(self) -> bool:
        return self.clase is not None

    def a_dict(self) -> dict | None:
        if not self.hay:
            return None
        # La expresión que disparó **no** viaja en la respuesta: es un pedazo de
        # lo que la persona escribió, y eso no sale del servidor. Queda para la
        # prueba y para quien depura, que llaman a `detectar` directamente.
        return {"clase": self.clase.value}


def detectar(consulta: str) -> Deteccion:
    """Qué clase de emergencia parece, si parece alguna."""
    texto = normalizar(consulta)
    if not texto:
        return Deteccion()
    for clase in ClaseUrgencia:  # el orden del enum es el orden de atención
        for patron, exige in _COMPILADAS[clase]:
            if not patron.search(texto):
                continue
            if exige == MOMENTO and not RE_AHORA.search(texto):
                continue
            if exige == RELATO and not RE_RELATO.search(texto):
                continue
            return Deteccion(clase=clase, expresion=patron.pattern)
    return Deteccion()


def casos_congelados(
    ruta: pathlib.Path | None = None,
) -> tuple[list[dict], list[dict]]:
    """Los casos que fijan dónde está la línea. Positivos y negativos."""
    ruta = ruta or pathlib.Path("docs/calidad/urgencia.json")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos["reconoce"], datos["no_reconoce"]
