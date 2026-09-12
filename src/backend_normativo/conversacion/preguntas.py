"""De «falta el dato `edad_del_causante`» a una pregunta que alguien puede contestar.

El motor de reglas deja pendientes **nombres de campo**: `edad_del_causante`,
`titular_reside_en_el_pais`, `percibe_otro_subsidio_habitacional`. Eso es lo que
la regla necesita, y no es una pregunta: es la clave interna con la que se
guarda la respuesta. Mostrarla sería poner el modelo de datos adentro del
recorrido ciudadano, que es justo lo que el plan prohíbe.

Lo que sí se puede mostrar es **el texto de la norma**. La condición que quedó
sin saber tiene sus palabras literales, y esas palabras son la pregunta: «la
norma dice esto; ¿pasa en tu caso?». La persona contesta sobre lo que la norma
exige, no sobre un campo de una tabla, y de paso ve de dónde sale la pregunta.

La **forma** de la respuesta sale del árbol de la regla, no de una lista escrita
a mano: `is_true` se contesta con sí o no, `in` con una de las opciones que la
norma enumera, `compare` con un número en la unidad que la regla usa. Cuando
mañana una regla nueva use otro operador, esto no la inventa: la deja fuera y no
la pregunta.

Y una cosa que no hace: **no vuelve a preguntar lo que la persona rehusó**. No
contestar es una respuesta —el motor la mantiene como desconocida, que no es lo
mismo que un no—, y repetir la pregunta la convertiría en una insistencia.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

# Cómo se contesta cada forma. El frente dibuja el control; acá sólo se dice
# cuál corresponde.
SI_NO = "si_no"
OPCIONES = "opciones"
NUMERO = "numero"
FECHA = "fecha"

# Las unidades que las reglas publicadas usan hoy, dichas en castellano. Una
# unidad que no esté acá viaja tal cual: es preferible una etiqueta fea a una
# traducción inventada.
UNIDADES = {
    "anios_cumplidos": "años cumplidos",
    "meses": "meses",
    "dias": "días",
    "ARS": "pesos",
}


@dataclass(frozen=True)
class Pregunta:
    """Un dato que falta, listo para preguntar.

    `campo` es la clave con la que se guarda la respuesta y **no se muestra**.
    Lo que se muestra es `texto_literal`: las palabras de la norma.
    """

    campo: str
    texto_literal: str
    forma: str
    opciones: tuple[str, ...] = ()
    unidad: str | None = None

    def a_dict(self) -> dict:
        return {
            "campo": self.campo,
            "texto_literal": self.texto_literal,
            "forma": self.forma,
            "opciones": list(self.opciones),
            "unidad": self.unidad,
        }


def _hojas(nodo) -> Iterator[dict]:
    """Recorre el árbol y devuelve las hojas: las que nombran un campo."""
    if not isinstance(nodo, dict):
        return
    if nodo.get("field"):
        yield nodo
    for hijo in nodo.get("args") or []:
        yield from _hojas(hijo)


def _es_fecha(valor) -> bool:
    if isinstance(valor, dt.date):
        return True
    if not isinstance(valor, str):
        return False
    try:
        dt.date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _forma(hoja: dict) -> tuple[str, tuple[str, ...], str | None]:
    operador = hoja.get("op")
    if operador == "is_true":
        return SI_NO, (), None
    if operador == "in":
        return OPCIONES, tuple(str(v) for v in hoja.get("values") or ()), None
    if operador == "compare":
        if _es_fecha(hoja.get("value")):
            return FECHA, (), None
        unidad = hoja.get("unit")
        return NUMERO, (), UNIDADES.get(unidad, unidad)
    # Operador desconocido: no se inventa un control para contestarlo.
    return "", (), None


def _preguntables(reglas) -> dict[str, tuple[dict, str]]:
    """Los campos que se pueden preguntar, con su hoja y el texto de la norma.

    **Sólo los campos cuya regla no nombra ningún otro.** Una regla como
    «acreditar la identidad del titular y de la niña o del niño» tiene dos
    campos adentro de una sola oración: mostrarla dos veces seguidas le pide a
    la persona que conteste dos cosas distintas leyendo el mismo texto, sin
    ninguna forma de saber cuál le están preguntando. Antes que hacer eso, no se
    pregunta: la condición queda como desconocida —que es lo que es— y la
    pantalla dice que hay requisitos que todavía no puede preguntar.

    Lo que falta para poder preguntarlas es un rótulo por hoja tomado de la
    norma, y eso se cura, no se infiere acá. Es una carencia del corpus, no de
    esta pantalla, y se declara como tal.
    """
    preguntables: dict[str, tuple[dict, str]] = {}
    for regla in reglas:
        hojas = list(_hojas(getattr(regla, "ast", None)))
        campos = {h["field"] for h in hojas}
        if len(campos) != 1:
            continue
        texto = getattr(regla, "texto_literal", "") or ""
        if not texto:
            continue
        campo = hojas[0]["field"]
        preguntables.setdefault(campo, (hojas[0], texto))
    return preguntables


def pendientes(reglas, dictamen, *, rehusados: Iterable[str] = ()) -> list[Pregunta]:
    """Las preguntas que faltan, en el orden en que el motor las dejó.

    El orden importa: `faltantes()` conserva el orden de aparición dentro de la
    regla, y la primera es la que conviene hacer primero.
    """
    rehusados = set(rehusados)
    preguntables = _preguntables(reglas)

    preguntas: list[Pregunta] = []
    vistos: set[str] = set()
    for campo in getattr(dictamen, "preguntas_faltantes", []) or []:
        if campo in rehusados or campo in vistos:
            continue
        par = preguntables.get(campo)
        if par is None:
            continue
        hoja, texto = par
        forma, opciones, unidad = _forma(hoja)
        if not forma:
            # Operador para el que no hay forma de contestar. No se inventa un
            # control: se deja sin preguntar.
            continue
        vistos.add(campo)
        preguntas.append(
            Pregunta(
                campo=campo,
                texto_literal=texto,
                forma=forma,
                opciones=opciones,
                unidad=unidad,
            )
        )
    return preguntas


def sin_preguntar(reglas, dictamen, *, rehusados: Iterable[str] = ()) -> int:
    """Cuántos datos siguen faltando y no se pueden preguntar todavía.

    Se cuenta y se dice. Callarlo dejaría a la persona creyendo que contestó
    todo lo que había que contestar.
    """
    rehusados = set(rehusados)
    preguntables = _preguntables(reglas)
    faltantes = getattr(dictamen, "preguntas_faltantes", []) or []
    return len({c for c in faltantes if c not in rehusados and c not in preguntables})
