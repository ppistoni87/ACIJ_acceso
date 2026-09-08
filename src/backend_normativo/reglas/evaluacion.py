"""Evaluación de reglas con lógica ternaria.

El tercer valor no es un detalle técnico: es la diferencia entre "no cumple" y
"todavía no sabemos". Un sistema que colapsa `UNKNOWN` en `FALSE` excluye
personas por falta de información, que es exactamente lo que la especificación
prohíbe.

Tabla de verdad (especificación §4 del modelo):

    FALSE AND UNKNOWN = FALSE      TRUE  AND UNKNOWN = UNKNOWN
    TRUE  OR  UNKNOWN = TRUE       FALSE OR  UNKNOWN = UNKNOWN
    NOT UNKNOWN = UNKNOWN

Un `FALSE` evalúa una condición. No habilita un rechazo administrativo, no dice
que la persona no tenga derecho y no reemplaza la decisión del organismo.
"""

from __future__ import annotations

import datetime as dt
import decimal
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from backend_normativo.reglas.ast import campos_referidos, validar_ast


class Ternario(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class ResultadoBeneficio(StrEnum):
    POTENCIALMENTE_APLICABLE = "POTENCIALMENTE_APLICABLE"
    REQUIERE_DATOS = "REQUIERE_DATOS"
    REQUIERE_REVISION = "REQUIERE_REVISION"
    NO_CUMPLE_REGLA_EXPLICITA = "NO_CUMPLE_REGLA_EXPLICITA"


def conjuncion(valores: list[Ternario]) -> Ternario:
    if Ternario.FALSE in valores:
        return Ternario.FALSE
    if Ternario.UNKNOWN in valores:
        return Ternario.UNKNOWN
    return Ternario.TRUE


def disyuncion(valores: list[Ternario]) -> Ternario:
    if Ternario.TRUE in valores:
        return Ternario.TRUE
    if Ternario.UNKNOWN in valores:
        return Ternario.UNKNOWN
    return Ternario.FALSE


def negacion(valor: Ternario) -> Ternario:
    if valor is Ternario.UNKNOWN:
        return Ternario.UNKNOWN
    return Ternario.FALSE if valor is Ternario.TRUE else Ternario.TRUE


@dataclass(frozen=True)
class HechosDeclarados:
    """Lo que la persona dijo, con lo que dejó sin responder marcado como tal.

    Un campo ausente y un campo respondido "no sé" son lo mismo acá: falta de
    información, no una respuesta negativa.
    """

    valores: Mapping[str, Any] = field(default_factory=dict)
    fecha: dt.date = field(default_factory=dt.date.today)

    def conoce(self, campo: str) -> bool:
        return campo in self.valores and self.valores[campo] is not None

    def obtener(self, campo: str) -> Any:
        return self.valores.get(campo)


@dataclass
class ResultadoCondicion:
    """El resultado de una hoja o de un nodo, con por qué dio eso."""

    valor: Ternario
    descripcion: str
    campo: str | None = None
    faltante: str | None = None
    parametro: str | None = None
    hijos: list[ResultadoCondicion] = field(default_factory=list)

    def faltantes(self) -> list[str]:
        """Campos que hacen falta para dejar de responder `UNKNOWN`."""
        pendientes: list[str] = []
        if self.faltante:
            pendientes.append(self.faltante)
        for hijo in self.hijos:
            pendientes.extend(hijo.faltantes())
        # Se conserva el orden de aparición: la primera pregunta que falta es la
        # que conviene hacer primero.
        vistos: set[str] = set()
        return [p for p in pendientes if not (p in vistos or vistos.add(p))]


class ValorDeParametroDesconocido(LookupError):
    """El catálogo no tiene un valor aprobado para esa fecha."""


class Evaluador:
    """Evalúa un árbol validado contra hechos declarados.

    Los valores de parámetros se resuelven con una función que el llamador
    provee: así la evaluación no depende de la base y se puede probar con
    valores fijos, y en producción esa función consulta la vista servible.
    """

    def __init__(
        self,
        resolver_parametro=None,
    ) -> None:
        self._resolver_parametro = resolver_parametro

    def evaluar(self, ast: dict, hechos: HechosDeclarados) -> ResultadoCondicion:
        validar_ast(ast)
        return self._evaluar(ast, hechos)

    def _evaluar(self, nodo: dict, hechos: HechosDeclarados) -> ResultadoCondicion:
        operador = nodo["op"]
        if operador == "all":
            hijos = [self._evaluar(h, hechos) for h in nodo["args"]]
            return ResultadoCondicion(
                valor=conjuncion([h.valor for h in hijos]),
                descripcion="se cumplen todas las condiciones",
                hijos=hijos,
            )
        if operador == "any":
            hijos = [self._evaluar(h, hechos) for h in nodo["args"]]
            return ResultadoCondicion(
                valor=disyuncion([h.valor for h in hijos]),
                descripcion="se cumple al menos una condición",
                hijos=hijos,
            )
        if operador == "not":
            hijo = self._evaluar(nodo["args"][0], hechos)
            return ResultadoCondicion(
                valor=negacion(hijo.valor),
                descripcion="no se cumple la condición",
                hijos=[hijo],
            )
        if operador == "is_true":
            return self._es_verdadero(nodo, hechos)
        if operador == "in":
            return self._pertenece(nodo, hechos)
        return self._comparar(nodo, hechos)

    # --- Hojas -------------------------------------------------------------

    def _es_verdadero(self, nodo: dict, hechos: HechosDeclarados) -> ResultadoCondicion:
        campo = nodo["field"]
        if not hechos.conoce(campo):
            return ResultadoCondicion(
                valor=Ternario.UNKNOWN,
                descripcion=f"falta saber si «{campo}» corresponde",
                campo=campo,
                faltante=campo,
            )
        valor = bool(hechos.obtener(campo))
        return ResultadoCondicion(
            valor=Ternario.TRUE if valor else Ternario.FALSE,
            descripcion=f"«{campo}» declarado como {'sí' if valor else 'no'}",
            campo=campo,
        )

    def _pertenece(self, nodo: dict, hechos: HechosDeclarados) -> ResultadoCondicion:
        campo = nodo["field"]
        if not hechos.conoce(campo):
            return ResultadoCondicion(
                valor=Ternario.UNKNOWN,
                descripcion=f"falta el dato «{campo}»",
                campo=campo,
                faltante=campo,
            )
        valores = {str(v) for v in nodo["values"]}
        pertenece = str(hechos.obtener(campo)) in valores
        return ResultadoCondicion(
            valor=Ternario.TRUE if pertenece else Ternario.FALSE,
            descripcion=(
                f"«{campo}» {'está' if pertenece else 'no está'} entre los valores previstos"
            ),
            campo=campo,
        )

    def _comparar(self, nodo: dict, hechos: HechosDeclarados) -> ResultadoCondicion:
        campo = nodo["field"]
        if not hechos.conoce(campo):
            return ResultadoCondicion(
                valor=Ternario.UNKNOWN,
                descripcion=f"falta el dato «{campo}»",
                campo=campo,
                faltante=campo,
            )

        try:
            referencia = self._referencia(nodo, hechos.fecha)
        except ValorDeParametroDesconocido as exc:
            # Sin el valor vigente del parámetro no se puede comparar. No es
            # que la persona no cumpla: es que el sistema no sabe contra qué.
            return ResultadoCondicion(
                valor=Ternario.UNKNOWN,
                descripcion=str(exc),
                campo=campo,
                parametro=nodo.get("parameter"),
            )

        declarado = hechos.obtener(campo)
        try:
            izquierda, derecha = _normalizar(declarado, referencia)
        except (TypeError, ValueError, decimal.InvalidOperation):
            return ResultadoCondicion(
                valor=Ternario.UNKNOWN,
                descripcion=(
                    f"«{campo}» y el valor de referencia no son comparables tal como "
                    "fueron declarados"
                ),
                campo=campo,
            )

        comparador = nodo["cmp"]
        cumple = _aplicar(comparador, izquierda, derecha)
        return ResultadoCondicion(
            valor=Ternario.TRUE if cumple else Ternario.FALSE,
            descripcion=(
                f"«{campo}» ({declarado}) {comparador} {referencia} "
                f"[{nodo['unit']}]: {'se cumple' if cumple else 'no se cumple'}"
            ),
            campo=campo,
            parametro=nodo.get("parameter"),
        )

    def _referencia(self, nodo: dict, fecha: dt.date) -> Any:
        if "value" in nodo:
            return nodo["value"]
        codigo = nodo["parameter"]
        if self._resolver_parametro is None:
            raise ValorDeParametroDesconocido(
                f"no hay forma de resolver el parámetro «{codigo}» en esta evaluación"
            )
        valor = self._resolver_parametro(codigo, fecha)
        if valor is None:
            raise ValorDeParametroDesconocido(
                f"el catálogo no tiene un valor aprobado de «{codigo}» para {fecha.isoformat()}"
            )
        factor = nodo.get("factor")
        if factor is None:
            return valor
        return decimal.Decimal(str(valor)) * decimal.Decimal(str(factor))


def _normalizar(izquierda: Any, derecha: Any) -> tuple[Any, Any]:
    """Lleva ambos lados a un tipo comparable sin perder precisión.

    Los importes se comparan como decimales, nunca como coma flotante: evaluar
    un derecho contra un tope con error de redondeo es inaceptable.
    """
    if isinstance(izquierda, bool) or isinstance(derecha, bool):
        return bool(izquierda), bool(derecha)
    if isinstance(izquierda, dt.date) or isinstance(derecha, dt.date):
        return _fecha(izquierda), _fecha(derecha)
    if isinstance(izquierda, (int, float, decimal.Decimal)) or isinstance(
        derecha, (int, float, decimal.Decimal)
    ):
        return decimal.Decimal(str(izquierda)), decimal.Decimal(str(derecha))
    return str(izquierda), str(derecha)


def _fecha(valor: Any) -> dt.date:
    if isinstance(valor, dt.date):
        return valor
    return dt.date.fromisoformat(str(valor))


def _aplicar(comparador: str, izquierda: Any, derecha: Any) -> bool:
    if comparador == "==":
        return izquierda == derecha
    if comparador == "!=":
        return izquierda != derecha
    if comparador == "<":
        return izquierda < derecha
    if comparador == "<=":
        return izquierda <= derecha
    if comparador == ">":
        return izquierda > derecha
    return izquierda >= derecha


def campos_faltantes(ast: dict, hechos: HechosDeclarados) -> list[str]:
    """Campos del árbol que la persona todavía no declaró."""
    return sorted(c for c in campos_referidos(ast) if not hechos.conoce(c))
