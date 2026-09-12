"""Dónde está la línea entre pedir el canal primero y contestar la norma.

Alguien escribió «estoy durmiendo en la calle, ¿hay algo urgente?» y el sistema
contestó con el artículo 10 de una ley. Esta es la parte que reconoce esa clase
de mensaje — sin diagnosticar nada y sin inventar a quién llamar.
"""

from __future__ import annotations

import pathlib

import pytest

from backend_normativo.conversacion.urgencia import (
    ClaseUrgencia,
    casos_congelados,
    detectar,
    normalizar,
)

RECONOCE, NO_RECONOCE = casos_congelados(pathlib.Path("docs/calidad/urgencia.json"))


@pytest.mark.parametrize("caso", RECONOCE, ids=[c["consulta"][:40] for c in RECONOCE])
def test_reconoce_lo_que_tiene_que_reconocer(caso: dict) -> None:
    deteccion = detectar(caso["consulta"])
    assert deteccion.hay, f"no reconoció: {caso['consulta']!r}"
    assert deteccion.clase.value == caso["clase"]


@pytest.mark.parametrize("caso", NO_RECONOCE, ids=[c["consulta"][:40] for c in NO_RECONOCE])
def test_no_reconoce_lo_que_no_es(caso: dict) -> None:
    """Un aviso de emergencia que aparece siempre deja de leerse.

    Y deja de leerse justo cuando hace falta, que es el daño de verdad.
    """
    deteccion = detectar(caso["consulta"])
    assert not deteccion.hay, f"{caso['consulta']!r} → {deteccion.clase} · {caso['por_que']}"


def test_la_gente_escribe_sin_tildes() -> None:
    assert detectar("estoy durmiendo en la calle").clase is ClaseUrgencia.CALLE
    assert detectar("ESTOY DURMIENDO EN LA CALLE").clase is ClaseUrgencia.CALLE
    assert normalizar("Violencia de Género") == "violencia de genero"


def test_la_ninez_gana_a_la_calle() -> None:
    """El orden del enum es el orden de atención, y tiene que notarse."""
    assert detectar("estoy en la calle con mis hijos").clase is ClaseUrgencia.NINEZ
    assert detectar("estoy en la calle").clase is ClaseUrgencia.CALLE


def test_lo_que_escribio_la_persona_no_sale_del_servidor() -> None:
    """La expresión que disparó es un pedazo de lo que alguien contó de su vida."""
    deteccion = detectar("mi pareja me pega y me quiero ir de casa")
    assert deteccion.expresion  # está, para quien depura
    assert deteccion.a_dict() == {"clase": "VIOLENCIA"}  # no viaja


def test_sin_texto_no_inventa_nada() -> None:
    for vacio in ("", "   ", None):
        assert not detectar(vacio).hay
