"""Contrato del árbol de reglas.

Operadores cerrados y versionados. No hay `eval`, ni SQL, ni código generado
dentro de una regla: un árbol es un dato que se valida antes de ejecutarse, y lo
que no está en este contrato no se ejecuta.

Cada hoja de comparación referencia un campo del diccionario de hechos y, cuando
compara contra un valor de la realidad, un parámetro del catálogo. Un literal
suelto sin unidad no se acepta: comparar un ingreso contra "150000" sin decir si
son pesos mensuales o anuales es la clase de error que cambia quién accede a un
derecho.
"""

from __future__ import annotations

import decimal
import re
from typing import Any

ESQUEMA_VERSION = "1.0"

OPERADORES = frozenset({"all", "any", "not", "compare", "in", "is_true"})
COMPARADORES = frozenset({"==", "!=", "<", "<=", ">", ">="})

# Unidades que el diccionario reconoce. La lista es cerrada a propósito: una
# unidad nueva es una decisión de dominio, no un texto libre.
UNIDADES = frozenset(
    {
        "anios_cumplidos",
        "meses",
        "dias",
        "ARS",
        "USD",
        "cantidad",
        "porcentaje",
        "booleano",
        "texto",
        "fecha",
    }
)

RE_CODIGO_PARAMETRO = re.compile(r"^[A-Z0-9][A-Z0-9_.-]*$")
RE_CAMPO = re.compile(r"^[a-z][a-z0-9_.]*$")


class ErrorDeContrato(ValueError):
    """El árbol no cumple el contrato y por lo tanto no se ejecuta."""

    def __init__(self, mensaje: str, ruta: str = "$") -> None:
        super().__init__(f"{ruta}: {mensaje}")
        self.ruta = ruta
        self.mensaje = mensaje


def validar_ast(ast: Any, *, ruta: str = "$", raiz: bool = True) -> None:
    """Valida un árbol completo. Lanza `ErrorDeContrato` en la primera falla.

    Validar es barato y ejecutar un árbol mal formado es caro: una comparación
    con el operador equivocado no falla, devuelve la respuesta contraria.
    """
    if raiz:
        if not isinstance(ast, dict):
            raise ErrorDeContrato("el árbol tiene que ser un objeto", ruta)
        version = ast.get("schema_version")
        if version != ESQUEMA_VERSION:
            raise ErrorDeContrato(
                f"schema_version esperado {ESQUEMA_VERSION!r} y se recibió {version!r}", ruta
            )

    if not isinstance(ast, dict):
        raise ErrorDeContrato("cada nodo tiene que ser un objeto", ruta)

    operador = ast.get("op")
    if operador not in OPERADORES:
        raise ErrorDeContrato(
            f"operador {operador!r} fuera del contrato; permitidos: "
            f"{', '.join(sorted(OPERADORES))}",
            ruta,
        )

    if operador in ("all", "any"):
        _validar_argumentos(ast, ruta, minimo=1)
    elif operador == "not":
        _validar_argumentos(ast, ruta, minimo=1, maximo=1)
    elif operador == "compare":
        _validar_compare(ast, ruta)
    elif operador == "in":
        _validar_in(ast, ruta)
    elif operador == "is_true":
        _validar_campo(ast, ruta)


def _validar_argumentos(nodo: dict, ruta: str, *, minimo: int, maximo: int | None = None) -> None:
    argumentos = nodo.get("args")
    if not isinstance(argumentos, list):
        raise ErrorDeContrato(f"{nodo['op']} necesita una lista en 'args'", ruta)
    if len(argumentos) < minimo:
        raise ErrorDeContrato(f"{nodo['op']} necesita al menos {minimo} argumento(s)", ruta)
    if maximo is not None and len(argumentos) > maximo:
        raise ErrorDeContrato(f"{nodo['op']} admite a lo sumo {maximo} argumento(s)", ruta)
    for indice, hijo in enumerate(argumentos):
        validar_ast(hijo, ruta=f"{ruta}.args[{indice}]", raiz=False)


def _validar_campo(nodo: dict, ruta: str) -> str:
    campo = nodo.get("field")
    if not isinstance(campo, str) or not RE_CAMPO.match(campo):
        raise ErrorDeContrato(
            f"'field' tiene que ser un identificador del diccionario y llegó {campo!r}", ruta
        )
    return campo


def _validar_compare(nodo: dict, ruta: str) -> None:
    _validar_campo(nodo, ruta)

    comparador = nodo.get("cmp")
    if comparador not in COMPARADORES:
        raise ErrorDeContrato(
            f"comparador {comparador!r} fuera del contrato; permitidos: "
            f"{', '.join(sorted(COMPARADORES))}",
            ruta,
        )

    tiene_valor = "value" in nodo
    tiene_parametro = "parameter" in nodo
    if tiene_valor == tiene_parametro:
        raise ErrorDeContrato("una comparación usa exactamente uno de 'value' o 'parameter'", ruta)

    if tiene_parametro:
        parametro = nodo["parameter"]
        if not isinstance(parametro, str) or not RE_CODIGO_PARAMETRO.match(parametro):
            raise ErrorDeContrato(
                f"'parameter' tiene que ser un código del catálogo y llegó {parametro!r}", ruta
            )
        factor = nodo.get("factor")
        if factor is not None:
            try:
                # El factor viaja como texto para no perder precisión: 1.50 en
                # coma flotante no es exactamente 1,5.
                decimal.Decimal(str(factor))
            except (decimal.InvalidOperation, TypeError) as exc:
                raise ErrorDeContrato(f"'factor' no es un decimal: {factor!r}", ruta) from exc

    unidad = nodo.get("unit")
    if unidad is None:
        raise ErrorDeContrato(
            "una comparación declara su unidad: sin ella no se sabe si se comparan "
            "pesos mensuales o anuales",
            ruta,
        )
    if unidad not in UNIDADES:
        raise ErrorDeContrato(
            f"unidad {unidad!r} fuera del diccionario; permitidas: {', '.join(sorted(UNIDADES))}",
            ruta,
        )


def _validar_in(nodo: dict, ruta: str) -> None:
    _validar_campo(nodo, ruta)
    valores = nodo.get("values")
    if not isinstance(valores, list) or not valores:
        raise ErrorDeContrato("'in' necesita una lista no vacía en 'values'", ruta)
    if len(valores) != len({str(v) for v in valores}):
        raise ErrorDeContrato("'in' tiene valores repetidos", ruta)


def parametros_referidos(ast: Any) -> set[str]:
    """Códigos de parámetro que usa el árbol.

    Sirve para saber qué reglas hay que reevaluar cuando cambia un valor: un
    tope que se actualiza invalida toda regla que lo use.
    """
    referidos: set[str] = set()
    _recolectar(ast, referidos)
    return referidos


def _recolectar(nodo: Any, acumulador: set[str]) -> None:
    if not isinstance(nodo, dict):
        return
    if nodo.get("op") == "compare" and isinstance(nodo.get("parameter"), str):
        acumulador.add(nodo["parameter"])
    for hijo in nodo.get("args", []) or []:
        _recolectar(hijo, acumulador)


def campos_referidos(ast: Any) -> set[str]:
    """Hechos que el árbol necesita para poder evaluarse."""
    campos: set[str] = set()
    _recolectar_campos(ast, campos)
    return campos


def _recolectar_campos(nodo: Any, acumulador: set[str]) -> None:
    if not isinstance(nodo, dict):
        return
    if isinstance(nodo.get("field"), str):
        acumulador.add(nodo["field"])
    for hijo in nodo.get("args", []) or []:
        _recolectar_campos(hijo, acumulador)
