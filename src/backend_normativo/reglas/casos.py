"""Los casos que una regla ejecutable tiene que declarar, y que se corren al cargarla.

Doce de las catorce reglas de exclusión del corpus estaban al revés. El árbol
expresaba la condición de **inclusión** —«la remuneración está entre el piso y el
techo»— y la categoría decía `EXCLUSION`, que el motor lee como «si esto es
verdadero, la persona queda afuera». El resultado era que a quien cobraba dentro
de la banda, que es exactamente quien accede, el sistema le iba a contestar que
una regla explícita lo excluía.

Ninguna prueba lo detectó, y no por descuido: las pruebas del motor comprueban
que `all`, `any` y `not` se evalúen bien, y se evaluaban bien. El error no estaba
en el motor sino en la traducción del texto legal al árbol, que es justo lo que
ninguna prueba de unidad puede mirar. Un árbol no se puede revisar contra una
ley leyéndolo: hay que preguntarle por un caso donde el texto no deje dudas.

Por eso cada regla ejecutable de acceso declara sus casos junto al árbol, en la
misma lectura curada, en castellano y con el veredicto esperado. Es la parte de
la interpretación que se puede comprobar sola, y el cargador se niega a entrar
una regla cuyos casos no den lo que dicen.

Para una `EXCLUSION`, `espera: "TRUE"` significa **queda excluida**. Para una
`APLICABILIDAD`, significa **cumple la condición**. Es la misma convención que
usa el resolvedor, escrita donde se escribe el caso.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backend_normativo.db.vocabularios import CategoriaRegla
from backend_normativo.reglas.evaluacion import Evaluador, HechosDeclarados, Ternario

# Dónde los casos son obligatorios **hoy**. Es `EXCLUSION` porque es donde
# apareció el error y donde una polaridad invertida hace el daño más directo:
# el sistema le dice a alguien que una regla explícita lo excluye.
#
# `APLICABILIDAD` todavía no los exige, y no por criterio sino por cantidad: 66
# reglas de acceso no los tienen, y escribir 66 lecturas legales a las apuradas
# para que el cargador deje de quejarse sería meter interpretaciones sin revisar
# en el único lugar que existe para revisarlas. Lo que sí hay es un trinquete
# —`tests/unit/test_casos_de_reglas.py`— que fija cuántas faltan y falla si
# alguien agrega una más. El número solo puede bajar.
CATEGORIAS_QUE_EXIGEN_CASOS = frozenset({CategoriaRegla.EXCLUSION})

# Dónde los casos se corren si están, aunque no sean obligatorios. Una regla que
# declara un caso lo tiene que cumplir; declararlo mal es peor que no declararlo.
CATEGORIAS_DE_ACCESO = frozenset({CategoriaRegla.APLICABILIDAD, CategoriaRegla.EXCLUSION})

VEREDICTOS = {"TRUE": Ternario.TRUE, "FALSE": Ternario.FALSE, "UNKNOWN": Ternario.UNKNOWN}


class CasoInvalido(Exception):
    """Un caso declarado no da lo que la lectura dice que da."""


@dataclass(frozen=True)
class Desvio:
    caso: str
    esperado: Ternario
    obtenido: Ternario

    def __str__(self) -> str:
        return (
            f"«{self.caso}»: se esperaba {self.esperado.value} y el árbol dio {self.obtenido.value}"
        )


def _tabla(parametros: dict):
    """Los valores de parámetro que el caso declara, y ninguno más."""

    def resolver(clave: str, *_: object, **__: object):
        return parametros.get(clave)

    return resolver


def correr(ast: dict, casos: list[dict], *, fecha: dt.date | None = None) -> list[Desvio]:
    """Evalúa el árbol contra cada caso y devuelve los que no coinciden.

    Los valores de parámetro los pone el propio caso. No se leen de la base a
    propósito: un caso que dependiera del corte publicado dejaría de comprobar
    la regla el día que cambie un monto, que es justo cuando hace falta.
    """
    fecha = fecha or dt.date(2026, 1, 1)
    desvios: list[Desvio] = []
    for caso in casos:
        esperado = VEREDICTOS.get(str(caso.get("espera", "")).upper())
        if esperado is None:
            raise CasoInvalido(
                f"El caso «{caso.get('nombre', '(sin nombre)')}» no declara un veredicto "
                f"válido: {sorted(VEREDICTOS)}."
            )
        evaluador = Evaluador(resolver_parametro=_tabla(caso.get("parametros") or {}))
        obtenido = evaluador.evaluar(
            ast, HechosDeclarados(valores=caso.get("hechos") or {}, fecha=fecha)
        ).valor
        if obtenido is not esperado:
            desvios.append(
                Desvio(caso.get("nombre", "(sin nombre)"), esperado=esperado, obtenido=obtenido)
            )
    return desvios


def exigir(clave: str, categoria: str, ast: dict | None, casos: list[dict] | None) -> None:
    """Se niega a dejar pasar una regla de acceso ejecutable sin casos que den bien.

    Sin árbol no hay nada que comprobar: una regla que la norma remite a la
    reglamentación entra con su texto y sin casos, como siempre.
    """
    if ast is None:
        return
    try:
        cat = CategoriaRegla(categoria)
    except ValueError as exc:  # pragma: no cover - el vocabulario lo valida antes
        raise CasoInvalido(f"La regla {clave!r} declara una categoría desconocida.") from exc
    if cat not in CATEGORIAS_DE_ACCESO:
        return
    if not casos:
        if cat not in CATEGORIAS_QUE_EXIGEN_CASOS:
            return
        raise CasoInvalido(
            f"La regla {clave!r} es de categoría {cat.value} y tiene árbol, así que tiene que "
            "declarar al menos un caso en «casos». Un árbol no se revisa contra una ley "
            "leyéndolo: se le pregunta por un caso donde el texto no deje dudas."
        )
    desvios = correr(ast, casos)
    if desvios:
        detalle = "; ".join(str(d) for d in desvios)
        raise CasoInvalido(
            f"Los casos de la regla {clave!r} no dan lo que la lectura dice: {detalle}. "
            f"En una {cat.value}, «TRUE» significa "
            + ("«queda excluida»." if cat is CategoriaRegla.EXCLUSION else "«cumple la condición».")
        )
