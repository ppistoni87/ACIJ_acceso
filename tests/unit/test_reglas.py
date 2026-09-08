"""HU-014, HU-015 y HU-030: contrato del AST y evaluación con desconocidos.

El tercer valor de la lógica no es un detalle técnico. Un sistema que colapsa
`UNKNOWN` en `FALSE` excluye personas por falta de información.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

import pytest

from backend_normativo.db.vocabularios import CategoriaRegla
from backend_normativo.reglas.ast import (
    ESQUEMA_VERSION,
    ErrorDeContrato,
    campos_referidos,
    parametros_referidos,
    validar_ast,
)
from backend_normativo.reglas.beneficio import ReglaEvaluable, evaluar_beneficio
from backend_normativo.reglas.evaluacion import (
    Evaluador,
    HechosDeclarados,
    ResultadoBeneficio,
    Ternario,
    conjuncion,
    disyuncion,
    negacion,
)


def _arbol(**extra) -> dict:
    base = {
        "schema_version": ESQUEMA_VERSION,
        "op": "compare",
        "field": "edad",
        "cmp": ">=",
        "value": 18,
        "unit": "anios_cumplidos",
    }
    base.update(extra)
    return base


# --- Contrato ----------------------------------------------------------------


def test_un_operador_fuera_del_contrato_no_se_ejecuta() -> None:
    with pytest.raises(ErrorDeContrato, match="fuera del contrato"):
        validar_ast({"schema_version": ESQUEMA_VERSION, "op": "eval", "args": []})


def test_una_comparacion_sin_unidad_se_rechaza() -> None:
    """Comparar un ingreso contra 150000 sin decir si son pesos mensuales o
    anuales cambia quién accede al derecho."""
    arbol = _arbol()
    del arbol["unit"]
    with pytest.raises(ErrorDeContrato, match="unidad"):
        validar_ast(arbol)


def test_una_comparacion_no_puede_tener_valor_y_parametro_a_la_vez() -> None:
    with pytest.raises(ErrorDeContrato, match="exactamente uno"):
        validar_ast(_arbol(parameter="SMVM"))


def test_una_version_de_esquema_distinta_no_se_ejecuta() -> None:
    with pytest.raises(ErrorDeContrato, match="schema_version"):
        validar_ast(_arbol(schema_version="9.9"))


def test_un_comparador_invalido_se_rechaza() -> None:
    with pytest.raises(ErrorDeContrato, match="comparador"):
        validar_ast(_arbol(cmp="=~"))


def test_el_arbol_declara_sus_parametros_y_campos() -> None:
    """Un tope que se actualiza invalida toda regla que lo use."""
    arbol = {
        "schema_version": ESQUEMA_VERSION,
        "op": "all",
        "args": [
            _arbol(),
            {
                "op": "compare",
                "field": "ingreso_hogar_mensual_bruto",
                "cmp": "<=",
                "parameter": "TOPE_SINTETICO",
                "factor": "1.50",
                "unit": "ARS",
            },
        ],
    }
    validar_ast(arbol)
    assert parametros_referidos(arbol) == {"TOPE_SINTETICO"}
    assert campos_referidos(arbol) == {"edad", "ingreso_hogar_mensual_bruto"}


# --- Lógica ternaria ---------------------------------------------------------


def test_la_tabla_de_verdad_es_la_de_la_especificacion() -> None:
    T, F, U = Ternario.TRUE, Ternario.FALSE, Ternario.UNKNOWN
    assert conjuncion([F, U]) is F
    assert conjuncion([T, U]) is U
    assert disyuncion([T, U]) is T
    assert disyuncion([F, U]) is U
    assert negacion(U) is U
    assert negacion(T) is F
    assert negacion(F) is T


def test_un_dato_que_falta_no_es_un_incumplimiento() -> None:
    resultado = Evaluador().evaluar(_arbol(), HechosDeclarados(valores={}))
    assert resultado.valor is Ternario.UNKNOWN
    assert resultado.faltantes() == ["edad"]


def test_un_dato_declarado_como_nulo_tampoco_lo_es() -> None:
    resultado = Evaluador().evaluar(_arbol(), HechosDeclarados(valores={"edad": None}))
    assert resultado.valor is Ternario.UNKNOWN


def test_una_condicion_falsa_no_arrastra_a_las_desconocidas() -> None:
    """`FALSE AND UNKNOWN = FALSE`: si algo ya no se cumple, no hace falta el
    resto."""
    arbol = {
        "schema_version": ESQUEMA_VERSION,
        "op": "all",
        "args": [
            _arbol(),
            {"op": "is_true", "field": "residencia_acreditada"},
        ],
    }
    resultado = Evaluador().evaluar(arbol, HechosDeclarados(valores={"edad": 15}))
    assert resultado.valor is Ternario.FALSE


def test_una_condicion_cumplida_no_tapa_lo_que_falta() -> None:
    """`TRUE AND UNKNOWN = UNKNOWN`: falta preguntar."""
    arbol = {
        "schema_version": ESQUEMA_VERSION,
        "op": "all",
        "args": [_arbol(), {"op": "is_true", "field": "residencia_acreditada"}],
    }
    resultado = Evaluador().evaluar(arbol, HechosDeclarados(valores={"edad": 22}))
    assert resultado.valor is Ternario.UNKNOWN
    assert resultado.faltantes() == ["residencia_acreditada"]


# --- Precisión y parámetros ---------------------------------------------------


def test_los_importes_se_comparan_como_decimales() -> None:
    """Evaluar un derecho contra un tope con error de redondeo es inaceptable."""
    arbol = {
        "schema_version": ESQUEMA_VERSION,
        "op": "compare",
        "field": "ingreso_hogar_mensual_bruto",
        "cmp": "<=",
        "parameter": "TOPE_SINTETICO",
        "factor": "1.50",
        "unit": "ARS",
    }
    evaluador = Evaluador(resolver_parametro=lambda codigo, fecha: decimal.Decimal("100000.10"))
    hechos = HechosDeclarados(valores={"ingreso_hogar_mensual_bruto": "150000.15"})
    assert evaluador.evaluar(arbol, hechos).valor is Ternario.TRUE

    justo_por_encima = HechosDeclarados(valores={"ingreso_hogar_mensual_bruto": "150000.16"})
    assert evaluador.evaluar(arbol, justo_por_encima).valor is Ternario.FALSE


def test_sin_valor_vigente_del_parametro_la_condicion_es_desconocida() -> None:
    """No es que la persona no cumpla: es que no sabemos contra qué comparar."""
    arbol = {
        "schema_version": ESQUEMA_VERSION,
        "op": "compare",
        "field": "ingreso_hogar_mensual_bruto",
        "cmp": "<=",
        "parameter": "TOPE_SINTETICO",
        "unit": "ARS",
    }
    evaluador = Evaluador(resolver_parametro=lambda codigo, fecha: None)
    resultado = evaluador.evaluar(
        arbol, HechosDeclarados(valores={"ingreso_hogar_mensual_bruto": 1})
    )
    assert resultado.valor is Ternario.UNKNOWN
    assert "no tiene un valor aprobado" in resultado.descripcion


def test_el_parametro_se_resuelve_a_la_fecha_consultada() -> None:
    consultas: list[dt.date] = []

    def resolver(codigo: str, fecha: dt.date):
        consultas.append(fecha)
        return 100

    arbol = {
        "schema_version": ESQUEMA_VERSION,
        "op": "compare",
        "field": "ingreso_hogar_mensual_bruto",
        "cmp": "<=",
        "parameter": "TOPE_SINTETICO",
        "unit": "ARS",
    }
    Evaluador(resolver_parametro=resolver).evaluar(
        arbol,
        HechosDeclarados(valores={"ingreso_hogar_mensual_bruto": 50}, fecha=dt.date(2024, 3, 1)),
    )
    assert consultas == [dt.date(2024, 3, 1)]


def test_menor_que_no_es_menor_o_igual() -> None:
    limite = _arbol(cmp="<", value=18)
    assert (
        Evaluador().evaluar(limite, HechosDeclarados(valores={"edad": 18})).valor is Ternario.FALSE
    )
    assert (
        Evaluador()
        .evaluar(_arbol(cmp="<=", value=18), HechosDeclarados(valores={"edad": 18}))
        .valor
        is Ternario.TRUE
    )


# --- Dictamen por beneficio ---------------------------------------------------


def _regla(categoria: CategoriaRegla, ast: dict | None, **extra) -> ReglaEvaluable:
    return ReglaEvaluable(
        id=extra.pop("id", uuid.uuid4()),
        categoria=categoria,
        texto_literal=extra.pop("texto", "texto literal de la regla"),
        ast=ast,
        requiere_revision=extra.pop("requiere_revision", False),
        **extra,
    )


def test_todo_cumplido_da_un_resultado_preliminar_positivo() -> None:
    reglas = [_regla(CategoriaRegla.APLICABILIDAD, _arbol())]
    dictamen = evaluar_beneficio(reglas, HechosDeclarados(valores={"edad": 20}))
    assert dictamen.resultado is ResultadoBeneficio.POTENCIALMENTE_APLICABLE


def test_falta_un_dato_y_el_resultado_pide_datos_en_vez_de_negar() -> None:
    reglas = [_regla(CategoriaRegla.APLICABILIDAD, _arbol())]
    dictamen = evaluar_beneficio(reglas, HechosDeclarados(valores={}))
    assert dictamen.resultado is ResultadoBeneficio.REQUIERE_DATOS
    assert dictamen.preguntas_faltantes == ["edad"]


def test_una_regla_sin_validar_no_se_ejecuta_y_pide_revision() -> None:
    reglas = [
        _regla(CategoriaRegla.APLICABILIDAD, _arbol()),
        _regla(CategoriaRegla.APLICABILIDAD, _arbol(), requiere_revision=True),
    ]
    dictamen = evaluar_beneficio(reglas, HechosDeclarados(valores={"edad": 20}))
    assert dictamen.resultado is ResultadoBeneficio.REQUIERE_REVISION
    assert dictamen.no_ejecutables


def test_no_se_niega_sin_haber_evaluado_las_excepciones() -> None:
    """La especificación es explícita: `NO_CUMPLE_REGLA_EXPLICITA` exige evaluar
    todas las excepciones aplicables."""
    aplicabilidad = _regla(CategoriaRegla.APLICABILIDAD, _arbol())
    excepcion = _regla(
        CategoriaRegla.EXCEPCION,
        {
            "schema_version": ESQUEMA_VERSION,
            "op": "is_true",
            "field": "excepcion_documentada",
        },
        excepcion_de=(aplicabilidad.id,),
    )
    # La edad no alcanza, pero no se sabe si corresponde la excepción.
    dictamen = evaluar_beneficio([aplicabilidad, excepcion], HechosDeclarados(valores={"edad": 15}))
    assert dictamen.resultado is ResultadoBeneficio.REQUIERE_DATOS
    assert "excepcion_documentada" in dictamen.preguntas_faltantes
    assert any("no se pudo evaluar" in a for a in dictamen.advertencias)


def test_con_la_excepcion_cumplida_el_bloqueo_no_aplica() -> None:
    aplicabilidad = _regla(CategoriaRegla.APLICABILIDAD, _arbol())
    excepcion = _regla(
        CategoriaRegla.EXCEPCION,
        {
            "schema_version": ESQUEMA_VERSION,
            "op": "is_true",
            "field": "excepcion_documentada",
        },
        excepcion_de=(aplicabilidad.id,),
    )
    dictamen = evaluar_beneficio(
        [aplicabilidad, excepcion],
        HechosDeclarados(valores={"edad": 15, "excepcion_documentada": True}),
    )
    assert dictamen.resultado is ResultadoBeneficio.POTENCIALMENTE_APLICABLE


def test_con_todas_las_excepciones_descartadas_si_hay_negativa_explicable() -> None:
    aplicabilidad = _regla(CategoriaRegla.APLICABILIDAD, _arbol())
    excepcion = _regla(
        CategoriaRegla.EXCEPCION,
        {
            "schema_version": ESQUEMA_VERSION,
            "op": "is_true",
            "field": "excepcion_documentada",
        },
        excepcion_de=(aplicabilidad.id,),
    )
    dictamen = evaluar_beneficio(
        [aplicabilidad, excepcion],
        HechosDeclarados(valores={"edad": 15, "excepcion_documentada": False}),
    )
    assert dictamen.resultado is ResultadoBeneficio.NO_CUMPLE_REGLA_EXPLICITA
    assert any("no es una decisión del organismo" in a.lower() for a in dictamen.advertencias)


def test_una_salvaguarda_nunca_excluye_y_siempre_se_informa() -> None:
    salvaguarda = _regla(
        CategoriaRegla.SALVAGUARDA,
        {"schema_version": ESQUEMA_VERSION, "op": "is_true", "field": "documento_alternativo"},
        texto="Se admite documentación alternativa acreditada por autoridad competente.",
    )
    dictamen = evaluar_beneficio(
        [_regla(CategoriaRegla.APLICABILIDAD, _arbol()), salvaguarda],
        HechosDeclarados(valores={"edad": 20}),
    )
    assert dictamen.resultado is ResultadoBeneficio.POTENCIALMENTE_APLICABLE
    assert len(dictamen.salvaguardas) == 1
    assert dictamen.desconocidas == []


def test_una_causal_de_revocacion_no_decide_el_acceso() -> None:
    """Detectar una causal potencial no constituye una decisión administrativa."""
    revocacion = _regla(
        CategoriaRegla.REVOCACION,
        {"schema_version": ESQUEMA_VERSION, "op": "is_true", "field": "dato_falso_declarado"},
    )
    dictamen = evaluar_beneficio(
        [_regla(CategoriaRegla.APLICABILIDAD, _arbol()), revocacion],
        HechosDeclarados(valores={"edad": 20, "dato_falso_declarado": True}),
    )
    assert dictamen.resultado is ResultadoBeneficio.POTENCIALMENTE_APLICABLE
    assert len(dictamen.posteriores) == 1


def test_una_exclusion_cumplida_bloquea_el_acceso() -> None:
    exclusion = _regla(
        CategoriaRegla.EXCLUSION,
        {
            "schema_version": ESQUEMA_VERSION,
            "op": "is_true",
            "field": "percibe_prestacion_incompatible",
        },
    )
    dictamen = evaluar_beneficio(
        [_regla(CategoriaRegla.APLICABILIDAD, _arbol()), exclusion],
        HechosDeclarados(valores={"edad": 20, "percibe_prestacion_incompatible": True}),
    )
    assert dictamen.resultado is ResultadoBeneficio.NO_CUMPLE_REGLA_EXPLICITA
