"""HU-016 y AT-051/AT-052: cómputo de plazos con calendario.

Un vencimiento mal calculado por un día es indistinguible de uno bien calculado
hasta que alguien pierde el plazo. Lo que estas pruebas fijan es que el sistema
prefiera no dar fecha antes que dar una equivocada.
"""

from __future__ import annotations

import datetime as dt

import pytest

from backend_normativo.plazos.computo import (
    Calendario,
    Excepcion,
    calcular_vencimiento,
)

pytestmark = pytest.mark.aceptacion


def _calendario(
    *,
    desde: dt.date = dt.date(2026, 1, 1),
    hasta: dt.date = dt.date(2026, 12, 31),
    excepciones: dict[dt.date, tuple[bool, str]] | None = None,
) -> Calendario:
    return Calendario(
        id="cal",
        jurisdiccion="AR",
        nombre="Feriados nacionales 2026",
        version="2026",
        desde=desde,
        hasta=hasta,
        excepciones={
            fecha: Excepcion(fecha=fecha, es_habil=habil, motivo=motivo)
            for fecha, (habil, motivo) in (excepciones or {}).items()
        },
    )


# --- AT-051: un feriado dentro del plazo se excluye ---------------------------


def test_at051_un_feriado_dentro_del_plazo_se_excluye_y_queda_registrado() -> None:
    """El 24 de marzo de 2026 cae martes. Contar solo sábados y domingos daría
    el 27; el vencimiento real es el 30."""
    calendario = _calendario(
        excepciones={dt.date(2026, 3, 24): (False, "Día Nacional de la Memoria")}
    )
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=5,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=calendario,
    )
    assert resultado.determinado
    assert resultado.vencimiento == dt.date(2026, 3, 30)
    assert dt.date(2026, 3, 24) in [e.fecha for e in resultado.excluidos]
    assert resultado.calendario_usado == "Feriados nacionales 2026@2026"
    assert "Día Nacional de la Memoria" in resultado.fundamento


def test_at051_el_mismo_plazo_sin_el_feriado_vence_antes() -> None:
    """El feriado es lo único que cambia entre los dos cómputos: si no se
    excluyera, esta prueba y la anterior darían la misma fecha."""
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=5,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=_calendario(),
    )
    assert resultado.vencimiento == dt.date(2026, 3, 27)


def test_at051_el_fundamento_dice_con_que_calendario_se_calculo() -> None:
    """Una fecha sin decir contra qué calendario salió no se puede auditar ni
    discutir con el organismo."""
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=3,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=_calendario(),
    )
    assert "Feriados nacionales 2026@2026" in resultado.fundamento


def test_un_dia_habil_excepcional_cuenta_aunque_caiga_sabado() -> None:
    """El calendario puede declarar hábil un día que por regla no lo sería."""
    calendario = _calendario(
        excepciones={dt.date(2026, 3, 21): (True, "Habilitado por resolución")}
    )
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=1,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=calendario,
    )
    assert resultado.vencimiento == dt.date(2026, 3, 21)


# --- AT-052: sin cobertura no hay fecha ---------------------------------------


def test_at052_pasarse_de_la_cobertura_no_produce_una_fecha() -> None:
    """Un calendario que llega hasta diciembre no sabe nada de enero.
    Extrapolar feriados es inventarlos."""
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 12, 20),
        cantidad=15,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=_calendario(),
    )
    assert not resultado.determinado
    assert resultado.vencimiento is None
    assert resultado.requiere == "calendario_que_cubra_el_periodo"
    assert "2026-12-31" in resultado.motivo


def test_un_inicio_fuera_de_la_cobertura_tampoco() -> None:
    resultado = calcular_vencimiento(
        inicio=dt.date(2025, 6, 1),
        cantidad=3,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=_calendario(),
    )
    assert not resultado.determinado
    assert "queda fuera de la cobertura" in resultado.motivo


def test_sin_calendario_un_plazo_habil_no_se_computa() -> None:
    """Saltear solo sábados y domingos cuenta mal cualquier mes con feriado."""
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=5,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=None,
    )
    assert not resultado.determinado
    assert resultado.requiere == "calendario_jurisdiccional"


# --- Lo que el cómputo no supone ----------------------------------------------


def test_sin_saber_si_es_corrido_o_habil_no_se_elige_uno() -> None:
    """La diferencia entre corridos y hábiles es de días: elegir por defecto
    mueve el vencimiento sin que nadie lo haya decidido."""
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=5,
        unidad="dias",
        tipo_dia="NO_INFORMADO",
        calendario=_calendario(),
    )
    assert not resultado.determinado
    assert resultado.requiere == "tipo_de_dia_declarado"


def test_los_dias_corridos_no_necesitan_calendario() -> None:
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=5,
        unidad="dias",
        tipo_dia="CORRIDO",
    )
    assert resultado.vencimiento == dt.date(2026, 3, 25)
    assert resultado.excluidos == []


def test_el_dia_del_evento_cuenta_solo_si_la_norma_lo_dice() -> None:
    """Suponer si el día del evento cuenta mueve el vencimiento un día, que es
    toda la diferencia entre presentar a tiempo y no."""
    comun = {
        "inicio": dt.date(2026, 3, 20),
        "cantidad": 5,
        "unidad": "dias",
        "tipo_dia": "CORRIDO",
    }
    assert calcular_vencimiento(**comun).vencimiento == dt.date(2026, 3, 25)
    assert calcular_vencimiento(**comun, inclusivo_desde=True).vencimiento == dt.date(2026, 3, 24)


def test_una_unidad_fuera_del_contrato_no_se_convierte_por_analogia() -> None:
    """«Meses» no son treinta días: convertirlo produciría un vencimiento que
    ninguna norma dispuso."""
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=2,
        unidad="meses",
        tipo_dia="CORRIDO",
    )
    assert not resultado.determinado
    assert resultado.requiere == "unidad_soportada"


def test_las_semanas_se_convierten_a_dias_habiles() -> None:
    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 2),
        cantidad=2,
        unidad="semanas",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=_calendario(),
    )
    assert resultado.determinado
    assert resultado.dias_contados == 14
