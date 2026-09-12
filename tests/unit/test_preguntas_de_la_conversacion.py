"""De un campo pendiente a una pregunta que alguien puede contestar.

Lo que se prueba acá no es que el motor sepa qué falta —eso ya está probado—
sino que lo que falta se pueda **preguntar sin mostrar el modelo de datos** y
sin pedirle a la persona que adivine cuál de dos cosas le están preguntando.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend_normativo.conversacion.preguntas import (
    FECHA,
    NUMERO,
    OPCIONES,
    SI_NO,
    pendientes,
    sin_preguntar,
)


@dataclass
class ReglaFalsa:
    texto_literal: str
    ast: dict
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class DictamenFalso:
    preguntas_faltantes: list[str]


def test_la_pregunta_muestra_la_norma_y_nunca_el_nombre_del_campo() -> None:
    regla = ReglaFalsa(
        texto_literal="Los titulares deben residir en el país.",
        ast={"op": "is_true", "field": "titular_reside_en_el_pais"},
    )
    [pregunta] = pendientes([regla], DictamenFalso(["titular_reside_en_el_pais"]))

    assert pregunta.texto_literal == "Los titulares deben residir en el país."
    assert pregunta.forma == SI_NO
    # El campo viaja porque es con lo que se guarda la respuesta, y la pantalla
    # lo usa sin mostrarlo. Que viaje es distinto de que se lea.
    assert pregunta.campo == "titular_reside_en_el_pais"


def test_la_forma_de_contestar_sale_del_arbol_de_la_regla() -> None:
    reglas = [
        ReglaFalsa(
            "Menor de dieciocho años.",
            {"op": "compare", "cmp": "<", "field": "edad", "value": 18, "unit": "anios_cumplidos"},
        ),
        ReglaFalsa(
            "El vínculo debe ser alguno de los previstos.",
            {"op": "in", "field": "vinculo", "values": ["PADRE", "MADRE"]},
        ),
        ReglaFalsa(
            "Debe haberse presentado antes de la fecha.",
            {"op": "compare", "cmp": "<", "field": "presentado_el", "value": "2026-01-01"},
        ),
    ]
    por_campo = {
        p.campo: p for p in pendientes(reglas, DictamenFalso(["edad", "vinculo", "presentado_el"]))
    }

    assert por_campo["edad"].forma == NUMERO
    assert por_campo["edad"].unidad == "años cumplidos"
    assert por_campo["vinculo"].forma == OPCIONES
    assert por_campo["vinculo"].opciones == ("PADRE", "MADRE")
    assert por_campo["presentado_el"].forma == FECHA


def test_una_regla_que_pide_dos_cosas_en_una_oracion_no_se_pregunta() -> None:
    """El caso que rompe la pantalla si no se lo trata.

    «Acreditar la identidad del titular y de la niña o del niño» son dos datos
    adentro de una sola oración. Preguntar esa oración dos veces seguidas le
    pide a la persona que conteste cosas distintas leyendo lo mismo, sin ninguna
    forma de saber cuál. Antes que preguntar mal, no se pregunta: la condición
    queda desconocida y se cuenta para poder decirlo.
    """
    regla = ReglaFalsa(
        "Acreditar la identidad del titular y de la niña o del niño.",
        {
            "op": "all",
            "args": [
                {"op": "is_true", "field": "identidad_titular"},
                {"op": "is_true", "field": "identidad_causante"},
            ],
        },
    )
    dictamen = DictamenFalso(["identidad_titular", "identidad_causante"])

    assert pendientes([regla], dictamen) == []
    assert sin_preguntar([regla], dictamen) == 2


def test_lo_rehusado_no_se_vuelve_a_preguntar_ni_se_cuenta_como_pendiente() -> None:
    """No contestar es una respuesta. Repetir la pregunta sería insistir."""
    regla = ReglaFalsa("Debe residir en el país.", {"op": "is_true", "field": "reside"})
    dictamen = DictamenFalso(["reside"])

    assert pendientes([regla], dictamen, rehusados=["reside"]) == []
    assert sin_preguntar([regla], dictamen, rehusados=["reside"]) == 0


def test_un_operador_sin_forma_de_contestar_no_inventa_un_control() -> None:
    regla = ReglaFalsa("Algo raro.", {"op": "operador_del_futuro", "field": "x"})
    assert pendientes([regla], DictamenFalso(["x"])) == []


def test_una_regla_sin_texto_de_la_norma_no_se_pregunta() -> None:
    """Sin las palabras de la norma la pregunta sería el nombre del campo."""
    regla = ReglaFalsa("", {"op": "is_true", "field": "x"})
    assert pendientes([regla], DictamenFalso(["x"])) == []
    assert sin_preguntar([regla], DictamenFalso(["x"])) == 1


def test_el_orden_es_el_que_dejo_el_motor() -> None:
    reglas = [
        ReglaFalsa("Primera.", {"op": "is_true", "field": "a"}),
        ReglaFalsa("Segunda.", {"op": "is_true", "field": "b"}),
    ]
    assert [p.campo for p in pendientes(reglas, DictamenFalso(["b", "a"]))] == ["b", "a"]
