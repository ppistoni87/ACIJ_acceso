"""HU-037: el pre-filtro de `v_hechos_servibles` no puede esconder nada.

La función dejó de evaluar versión por versión las 7.888 del registro y ahora
mira primero si están publicadas y con release publicado. El endpoint de
cobertura pasó de 800 ms a 6 ms por eso.

Una optimización así sólo es defendible si el resultado no cambia. El pre-filtro
es un subconjunto de los motivos que `bn_motivos_no_servible` devuelve: si
alguna vez se agrega ahí una condición que la función no evalúe, la vista
empezaría a esconder versiones servibles sin decirlo. Esta prueba compara las
dos formas de calcularlo sobre el mismo corpus.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Connection, text

pytestmark = pytest.mark.integracion

CAPACIDADES = (
    "IDENTIFICACION",
    "DESCRIPCION_GENERAL",
    "REQUISITOS",
    "EVALUACION_PRELIMINAR",
    "MONTO",
    "PLAZO",
    "CANAL",
    "EXPLICACION_HISTORICA",
)

# La forma anterior: evaluar todas las versiones, sin pre-filtrar.
SIN_PREFILTRO = text(
    "SELECT v.id FROM registro_versiones v "
    " WHERE NOT EXISTS ("
    "   SELECT 1 FROM bn_motivos_no_servible(v.id, :fecha, :known_at, :capacidad)"
    " ) ORDER BY v.id"
)
CON_PREFILTRO = text(
    "SELECT registro_version_id FROM v_hechos_servibles(:fecha, :known_at, :capacidad) "
    " ORDER BY registro_version_id"
)


def _servibles(conexion: Connection, consulta, capacidad: str, fecha: dt.date) -> list:
    return list(
        conexion.execute(
            consulta, {"fecha": fecha, "known_at": dt.datetime.now(dt.UTC), "capacidad": capacidad}
        ).scalars()
    )


@pytest.mark.parametrize("capacidad", CAPACIDADES)
def test_el_prefiltro_devuelve_exactamente_lo_mismo(
    conexion: Connection, corpus_publicado, capacidad: str
) -> None:
    hoy = dt.date.today()
    assert _servibles(conexion, CON_PREFILTRO, capacidad, hoy) == _servibles(
        conexion, SIN_PREFILTRO, capacidad, hoy
    )


def test_el_prefiltro_devuelve_lo_mismo_tambien_sin_release(conexion: Connection, corpus) -> None:
    """Sin nada publicado las dos formas tienen que dar vacío, no una vacía y
    otra con algo."""
    hoy = dt.date.today()
    for capacidad in CAPACIDADES:
        con = _servibles(conexion, CON_PREFILTRO, capacidad, hoy)
        sin = _servibles(conexion, SIN_PREFILTRO, capacidad, hoy)
        assert con == sin == []


def test_el_prefiltro_devuelve_lo_mismo_en_una_fecha_fuera_del_periodo(
    conexion: Connection, corpus_publicado
) -> None:
    """La fecha la resuelve la función, no el pre-filtro: tienen que coincidir
    también cuando lo que descarta es el período y no el estado."""
    lejana = dt.date(1990, 1, 1)
    for capacidad in CAPACIDADES:
        assert _servibles(conexion, CON_PREFILTRO, capacidad, lejana) == _servibles(
            conexion, SIN_PREFILTRO, capacidad, lejana
        )


def test_una_version_publicada_cuyo_release_se_revierte_deja_de_servirse(
    conexion: Connection, corpus_publicado
) -> None:
    """El pre-filtro mira el estado del release, no sólo que exista."""
    hoy = dt.date.today()
    assert _servibles(conexion, CON_PREFILTRO, "IDENTIFICACION", hoy)

    conexion.execute(text("UPDATE releases SET estado = 'REVERTIDO'"))
    assert _servibles(conexion, CON_PREFILTRO, "IDENTIFICACION", hoy) == []
    assert _servibles(conexion, SIN_PREFILTRO, "IDENTIFICACION", hoy) == []
