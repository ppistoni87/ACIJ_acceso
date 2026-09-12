"""Las vías de subsanación: lo que la norma prevé para levantar un bloqueo.

El motor ya se negaba a informar una negativa sin haber evaluado las
excepciones. Lo que no hacía era **decir cuál** es la excepción, y esa
excepción es muchas veces la única vía que le queda a quien pregunta. Acá se
prueba que ahora la dice, y que distingue las tres cosas que no son lo mismo:
que la excepción alcance, que no alcance, y que no haya ninguna cargada.
"""

from __future__ import annotations

import uuid

from backend_normativo.db.vocabularios import CategoriaRegla
from backend_normativo.reglas.beneficio import ReglaEvaluable, evaluar_beneficio
from backend_normativo.reglas.evaluacion import HechosDeclarados, Ternario

RESIDENCIA = "Deben acreditar dos años de residencia en la Ciudad."
VICTIMA = "Quedan exceptuadas las personas acreditadas como víctimas de violencia de género."


def _regla(categoria, literal, ast, *, excepcion_de=()):
    return ReglaEvaluable(
        id=uuid.uuid4(),
        categoria=CategoriaRegla(categoria),
        texto_literal=literal,
        ast=ast,
        requiere_revision=False,
        excepcion_de=tuple(excepcion_de),
    )


def _con_excepcion():
    principal = _regla(
        "APLICABILIDAD",
        RESIDENCIA,
        {"op": "is_true", "field": "residencia_dos_anios", "schema_version": "1.0"},
    )
    excepcion = _regla(
        "EXCEPCION",
        VICTIMA,
        {"op": "is_true", "field": "victima_violencia_genero", "schema_version": "1.0"},
        excepcion_de=[principal.id],
    )
    return [principal, excepcion]


def test_un_bloqueo_viaja_con_la_excepcion_que_lo_levantaria() -> None:
    """Con el dato de la excepción sin declarar: la vía existe y se nombra."""
    dictamen = evaluar_beneficio(
        _con_excepcion(), HechosDeclarados(valores={"residencia_dos_anios": False})
    )

    [salida] = dictamen.subsanaciones
    assert salida.condicion == RESIDENCIA
    assert salida.categoria is CategoriaRegla.APLICABILIDAD
    assert salida.excepciones == [(VICTIMA, Ternario.UNKNOWN)]
    assert salida.falta_saber
    assert not salida.alcanza_alguna
    # Y mientras la excepción no se resuelva, no se informa una negativa.
    assert not dictamen.es_negativo


def test_cuando_la_excepcion_alcanza_se_dice_que_alcanza() -> None:
    dictamen = evaluar_beneficio(
        _con_excepcion(),
        HechosDeclarados(valores={"residencia_dos_anios": False, "victima_violencia_genero": True}),
    )

    [salida] = dictamen.subsanaciones
    assert salida.excepciones == [(VICTIMA, Ternario.TRUE)]
    assert salida.alcanza_alguna
    assert not dictamen.es_negativo


def test_cuando_la_excepcion_no_alcanza_igual_se_muestra() -> None:
    """Saber que la vía existe y no le sirve es distinto de no saber que existe.

    Quien lee esto puede darse cuenta de que la excepción sí le corresponde y
    que contestó mal, o llevarla al organismo. Esconderla porque el motor la dio
    por no cumplida le saca esa posibilidad.
    """
    dictamen = evaluar_beneficio(
        _con_excepcion(),
        HechosDeclarados(
            valores={"residencia_dos_anios": False, "victima_violencia_genero": False}
        ),
    )

    [salida] = dictamen.subsanaciones
    assert salida.excepciones == [(VICTIMA, Ternario.FALSE)]
    assert not salida.alcanza_alguna and not salida.falta_saber
    assert dictamen.es_negativo


def test_sin_excepciones_cargadas_no_se_afirma_que_la_norma_no_prevea_ninguna() -> None:
    """La lista vacía es una afirmación sobre el corpus, no sobre la ley.

    Es la distinción que evita cerrarle a alguien una puerta que está abierta:
    el motor no sabe si la norma no prevé excepción o si nadie la curó, y la
    estructura lo deja ver en vez de aplanarlo a «no hay salida».
    """
    principal = _regla(
        "APLICABILIDAD",
        RESIDENCIA,
        {"op": "is_true", "field": "residencia_dos_anios", "schema_version": "1.0"},
    )
    dictamen = evaluar_beneficio(
        [principal], HechosDeclarados(valores={"residencia_dos_anios": False})
    )

    [salida] = dictamen.subsanaciones
    assert salida.excepciones == []
    assert not salida.alcanza_alguna and not salida.falta_saber


def test_una_exclusion_que_se_cumple_tambien_es_un_bloqueo_y_se_dice_como_tal() -> None:
    """«No cumplís esto» y «esto que cumplís te deja afuera» no se leen igual."""
    exclusion = _regla(
        "EXCLUSION",
        "No accede quien ya perciba otra prestación equivalente.",
        {"op": "is_true", "field": "percibe_otra_prestacion", "schema_version": "1.0"},
    )
    dictamen = evaluar_beneficio(
        [exclusion], HechosDeclarados(valores={"percibe_otra_prestacion": True})
    )

    [salida] = dictamen.subsanaciones
    assert salida.categoria is CategoriaRegla.EXCLUSION
    assert "otra prestación equivalente" in salida.condicion


def test_sin_bloqueos_no_hay_nada_que_subsanar() -> None:
    dictamen = evaluar_beneficio(
        _con_excepcion(), HechosDeclarados(valores={"residencia_dos_anios": True})
    )
    assert dictamen.subsanaciones == []
