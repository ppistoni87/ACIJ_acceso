"""Casos de aceptación que se juegan en la lógica, sin base de datos.

AT-041 y AT-057 tratan de la misma confusión vista desde dos lados: usar un
número donde corresponde otro. Una edad que no es la de quien pregunta y un
tope que no es lo que se cobra.
"""

from __future__ import annotations

import datetime as dt
import decimal

import pytest

from backend_normativo.reglas.ast import ESQUEMA_VERSION, parametros_referidos
from backend_normativo.reglas.evaluacion import Evaluador, HechosDeclarados, Ternario

pytestmark = pytest.mark.aceptacion


def _compare(field: str, cmp: str, **extra) -> dict:
    return {"schema_version": ESQUEMA_VERSION, "op": "compare", "field": field, "cmp": cmp, **extra}


# --- AT-041: cada edad usa su variable ---------------------------------------

# Una asignación por hijo mira la edad del niño para la elegibilidad y la del
# adulto para saber quién puede pedirla. Son dos variables distintas: si el
# evaluador las mezcla, excluye al niño por la edad del padre.
REGLA_CON_DOS_ROLES = {
    "schema_version": ESQUEMA_VERSION,
    "op": "all",
    "args": [
        _compare("edad_causante", "<=", value=17, unit="anios_cumplidos"),
        _compare("edad_representante", ">=", value=18, unit="anios_cumplidos"),
    ],
}


def test_at041_cada_edad_se_evalua_contra_su_propia_variable() -> None:
    hechos = HechosDeclarados(
        valores={"edad_causante": 10, "edad_representante": 35}, fecha=dt.date(2026, 1, 1)
    )
    resultado = Evaluador().evaluar(REGLA_CON_DOS_ROLES, hechos)
    assert resultado.valor is Ternario.TRUE, (
        "Un niño de 10 con un adulto de 35 cumple: ninguna edad se aplicó al otro rol."
    )


def test_at041_la_edad_del_adulto_no_excluye_por_la_del_nino() -> None:
    """El adulto tiene 35: si el evaluador usara esa edad para la condición del
    causante, daría FALSE y excluiría a un chico que sí califica."""
    hechos = HechosDeclarados(valores={"edad_representante": 35}, fecha=dt.date(2026, 1, 1))
    resultado = Evaluador().evaluar(REGLA_CON_DOS_ROLES, hechos)
    assert resultado.valor is Ternario.UNKNOWN
    assert "edad_causante" in resultado.faltantes()
    assert "edad_representante" not in resultado.faltantes()


def test_at041_falta_la_edad_del_adulto_y_se_pide_esa_y_no_otra() -> None:
    hechos = HechosDeclarados(valores={"edad_causante": 10}, fecha=dt.date(2026, 1, 1))
    resultado = Evaluador().evaluar(REGLA_CON_DOS_ROLES, hechos)
    assert resultado.valor is Ternario.UNKNOWN
    assert resultado.faltantes() == ["edad_representante"]


# --- AT-057: un tope no es un monto ------------------------------------------


def test_at057_un_tope_es_el_limite_de_una_condicion_no_una_cuantia() -> None:
    """La tabla trae un umbral de ingresos y un porcentaje de beca. El umbral
    entra al AST como cota de una condición; nunca sale como el dinero que la
    persona va a cobrar."""
    regla = _compare("ingreso_computable", "<=", parameter="TOPE_INGRESO_BECA", unit="ARS")
    assert parametros_referidos(regla) == {"TOPE_INGRESO_BECA"}

    hechos = HechosDeclarados(
        valores={"ingreso_computable": decimal.Decimal("90000")}, fecha=dt.date(2026, 1, 1)
    )
    resultado = Evaluador(
        resolver_parametro=lambda codigo, fecha: decimal.Decimal("100000")
    ).evaluar(regla, hechos)

    assert resultado.valor is Ternario.TRUE
    # Lo que la condición devuelve es si se cumple, no un importe: el tope queda
    # en la explicación como la cota que se comparó.
    assert resultado.parametro == "TOPE_INGRESO_BECA"
    assert not isinstance(resultado.valor, decimal.Decimal)


def test_at057_estar_bajo_el_tope_no_dice_cuanto_se_cobra() -> None:
    """Cumplir la condición de ingresos habilita a pedir la beca. El monto es
    otro dato, de otra fuente, que puede no existir."""
    regla = _compare("ingreso_computable", "<=", parameter="TOPE_INGRESO_BECA", unit="ARS")
    hechos = HechosDeclarados(
        valores={"ingreso_computable": decimal.Decimal("90000")}, fecha=dt.date(2026, 1, 1)
    )
    resultado = Evaluador(
        resolver_parametro=lambda codigo, fecha: decimal.Decimal("100000")
    ).evaluar(regla, hechos)
    assert resultado.valor is Ternario.TRUE
    assert "100000" in resultado.descripcion or "TOPE_INGRESO_BECA" in resultado.descripcion
