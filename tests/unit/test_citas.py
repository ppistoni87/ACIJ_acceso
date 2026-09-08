"""Reconocimiento de citas a otras normas.

La dirección de la relación depende de la voz del verbo. Invertirla haría que el
corpus afirme lo contrario de lo que dice la fuente.
"""

from __future__ import annotations

from backend_normativo.curacion.citas import detectar_citas
from backend_normativo.db.vocabularios import TipoNorma, TipoRelacionNormativa

NOTA_F33 = (
    "( Nota Infoleg : norma abrogada por art. 26 del Decreto N° 1382/01 - B.O. 2/11/2001 "
    "y restablecida su vigencia por Decreto N° 1604/2001 B.O. 6/12/2001, con excepción de "
    "las normas correspondientes a las prestaciones)"
)


def test_la_voz_pasiva_pone_a_la_norma_citada_como_origen() -> None:
    """F33: "abrogada por el Decreto 1382/01" significa que el decreto abroga a
    la norma en curso, no al revés."""
    citas = {(c.numero, c.relacion, c.citada_es_origen) for c in detectar_citas(NOTA_F33)}
    assert ("1382", TipoRelacionNormativa.ABROGA, True) in citas
    assert ("1604", TipoRelacionNormativa.RESTABLECE, True) in citas


def test_la_nota_conserva_la_abrogacion_y_la_restitucion() -> None:
    """La primera palabra de la nota dice "abrogada" y la segunda parte dice
    "restablecida". Quedarse con la primera clasificaría mal la norma."""
    relaciones = {c.relacion for c in detectar_citas(NOTA_F33)}
    assert TipoRelacionNormativa.ABROGA in relaciones
    assert TipoRelacionNormativa.RESTABLECE in relaciones


def test_la_voz_activa_pone_al_texto_en_curso_como_origen() -> None:
    citas = detectar_citas(
        "Derógase la Ley N° 18.017 y sus modificatorias, y los Decretos Nros. 770/96, 771/96."
    )
    assert all(c.relacion is TipoRelacionNormativa.DEROGA for c in citas)
    assert all(not c.citada_es_origen for c in citas)


def test_una_enumeracion_no_pierde_las_normas_siguientes() -> None:
    """ "Leyes Nros. 22.431, 24.013, 24.241 y 24.714" son cuatro dependencias."""
    citas = detectar_citas(
        "VISTO las Leyes Nros. 22.431, 24.013, 24.241 y 24.714, y el Decreto Nº 2284"
    )
    numeros = [c.numero for c in citas if c.tipo_norma is TipoNorma.LEY]
    assert numeros == ["22431", "24013", "24241", "24714"]
    assert any(c.numero == "2284" and c.tipo_norma is TipoNorma.DECRETO for c in citas)


def test_el_separador_de_miles_no_se_confunde_con_el_numero() -> None:
    """ "Decreto N° 1382/01" es el 1382 de 2001, no el 138."""
    (cita,) = detectar_citas("el Decreto N° 1382/01 dispuso")
    assert (cita.numero, cita.anio) == ("1382", 2001)

    (con_puntos,) = detectar_citas("la Ordenanza N° 43.478 vigente")
    assert (con_puntos.numero, con_puntos.anio) == ("43478", None)


def test_el_ano_de_dos_digitos_se_resuelve_por_ventana() -> None:
    assert detectar_citas("Decreto 770/96")[0].anio == 1996
    assert detectar_citas("Decreto 1382/01")[0].anio == 2001


def test_mencionar_una_norma_no_es_modificarla() -> None:
    """Sin un verbo que lo indique, la relación es una cita y nada más."""
    (cita,) = detectar_citas("conforme lo previsto en la Ley N° 27.260")
    assert cita.relacion is TipoRelacionNormativa.CITA


def test_una_sustitucion_apunta_a_la_norma_sustituida() -> None:
    (cita,) = detectar_citas(
        "Artículo 1° - Sustitúyese el artículo 10 de la Ordenanza N° 43.478 por el siguiente:"
    )
    assert cita.relacion is TipoRelacionNormativa.SUSTITUYE
    assert cita.citada_es_origen is False
    assert cita.numero == "43478"
