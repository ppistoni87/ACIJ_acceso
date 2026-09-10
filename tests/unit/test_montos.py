"""P-006 criterio 3: leer una tabla de importes sin inventar el período."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from backend_normativo.curacion.montos import leer_tabla, periodos

TABLA = """Fecha Salario Mínimo, Vital y Móvil Prestación por Desempleo monto mínimo
a partir del 1/10/2026 $ 391.200 $ 195.600 $ 391.200
a partir del 1/11/2026 $ 398.800 $ 199.400 $ 398.800
a partir del 1/12/2026 $ 406.400 $ 203.200 $ 406.400
Resoluciones anteriores"""


def test_se_leen_los_renglones_con_su_fecha_y_sus_importes() -> None:
    filas = leer_tabla(TABLA)

    assert [f.desde for f in filas] == [
        dt.date(2026, 10, 1),
        dt.date(2026, 11, 1),
        dt.date(2026, 12, 1),
    ]
    assert filas[0].importes == [Decimal("391200"), Decimal("195600"), Decimal("391200")]


def test_el_encabezado_y_el_pie_no_son_renglones() -> None:
    assert len(leer_tabla(TABLA)) == 3


def test_a_partir_del_rige_hasta_el_dia_anterior_al_siguiente() -> None:
    """El período sale de la tabla. No hay que suponer un mes ni un año."""
    tramos = periodos(leer_tabla(TABLA))

    assert [(desde, hasta) for _, desde, hasta in tramos] == [
        (dt.date(2026, 10, 1), dt.date(2026, 10, 31)),
        (dt.date(2026, 11, 1), dt.date(2026, 11, 30)),
        (dt.date(2026, 12, 1), None),
    ]


def test_los_renglones_se_ordenan_por_fecha_aunque_la_pagina_no_lo_haga() -> None:
    desordenada = """a partir del 1/12/2026 $ 406.400
a partir del 1/10/2026 $ 391.200"""
    tramos = periodos(leer_tabla(desordenada))

    assert tramos[0][1] == dt.date(2026, 10, 1)
    assert tramos[0][2] == dt.date(2026, 11, 30), "cierra el día anterior al siguiente"
    assert tramos[1][2] is None


def test_un_importe_con_centavos_se_lee_entero() -> None:
    filas = leer_tabla("a partir del 1/3/2026 $ 12.345,67")
    assert filas[0].importes == [Decimal("12345.67")]


def test_un_importe_sin_fecha_no_es_un_renglon_de_la_tabla() -> None:
    """«El monto de la beca es de $35.000» no dice desde cuándo rige."""
    assert leer_tabla("El monto de la beca Progresar es de $35.000.-") == []
