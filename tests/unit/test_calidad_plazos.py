"""Un plazo que dice un número tiene que poder señalarlo en el texto que cita."""

from __future__ import annotations

import pytest

from backend_normativo.calidad.plazos import (
    NO_SOSTENIDO,
    SIN_CANTIDAD,
    SOSTENIDO,
    PlazoVerificado,
    sostiene,
)


def _plazo(cantidad: int | None, cita: str) -> PlazoVerificado:
    return PlazoVerificado(
        tipo="CONVOCATORIA",
        cantidad=cantidad,
        unidad="dias" if cantidad is not None else None,
        evento_inicio="inicio del ciclo lectivo",
        dueño="X",
        source_id="F00",
        cita=cita,
    )


@pytest.mark.parametrize(
    ("cita", "cantidad"),
    [
        ("dentro de los treinta (30) días", 30),
        ("en el plazo de 10 días hábiles", 10),
        # La trampa que hay que esquivar antes de acusar a nadie: los textos
        # legales escriben los números con letras tanto como con cifras.
        ("antes de los tres meses de la finalización", 3),
        ("acreditado entre el tercer y cuarto mes", 4),
        ("el período establecido entre los quince días previos", 15),
    ],
)
def test_el_numero_puede_estar_en_cifras_o_en_letras(cita: str, cantidad: int) -> None:
    assert sostiene(cita, cantidad)


@pytest.mark.parametrize(
    ("cita", "cantidad"),
    [
        ("La solicitud se presentará en el momento de la inscripción", 0),
        ("se hará efectiva en el mes de marzo de cada año", 1),
        ("Los organismos deberán remitir la documentación correspondiente", 30),
    ],
)
def test_un_numero_que_no_esta_no_esta(cita: str, cantidad: int) -> None:
    assert not sostiene(cita, cantidad)


def test_treinta_no_se_confunde_con_treinta_y_cinco() -> None:
    """El límite de palabra evita que «300» respalde un plazo de 30."""
    assert not sostiene("un padrón de 300 familias", 30)
    assert sostiene("un plazo de 30 días", 30)


def test_un_plazo_sin_cantidad_no_tiene_nada_que_comprobar() -> None:
    """La norma lo expresa como evento, y forzarle un número sería inventarlo."""
    assert _plazo(None, "en el momento de la inscripción").veredicto == SIN_CANTIDAD


def test_un_plazo_respaldado_y_uno_que_no() -> None:
    assert _plazo(15, "quince (15) días posteriores").veredicto == SOSTENIDO
    assert _plazo(15, "dentro del período ordinario").veredicto == NO_SOSTENIDO
