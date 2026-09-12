"""La norma no rige el día que se publica, y la sanción no es la publicación.

Dos errores encadenados que no fallaban. La ingesta tomaba
`PUBLICACION or SANCION` y escribía ese valor tal cual como `valid_desde`:
una norma sancionada y no publicada quedaba rigiendo desde su sanción, y una
publicada quedaba rigiendo el mismo día de su publicación. Ninguna de las dos es
cierta y ninguna rompía nada: la fecha simplemente quedaba unos días antes de lo
que corresponde, y con ella cambia qué contesta una consulta con `as_of` en esa
ventana.

Ahora el comienzo lo computa la política, en un solo lugar, con el plazo del
art. 5 del Código Civil y Comercial.
"""

from __future__ import annotations

import datetime as dt

from backend_normativo.db.vocabularios import EstadoLegal, ValidTipo
from backend_normativo.politicas import vigencia as politica


def _dictaminar(**kwargs):
    base = {
        "estado_declarado": EstadoLegal.VIGENTE.value,
        "fecha_publicacion": dt.date(2025, 12, 19),
        "cierres_aprobados": 0,
        "reaperturas_aprobadas": 0,
        "tiene_evidencia_de_estado": True,
    }
    base.update(kwargs)
    return politica.dictaminar(**base)


def test_rige_ocho_dias_despues_de_publicarse() -> None:
    dictamen = _dictaminar()
    assert dictamen.automatica
    assert dictamen.valid_tipo is ValidTipo.ABIERTO_FIN
    assert dictamen.valid_desde == dt.date(2025, 12, 27)


def test_el_fundamento_dice_la_regla_y_las_dos_fechas() -> None:
    """Dentro de seis meses la pregunta va a ser de dónde salió esa fecha."""
    fundamento = _dictaminar().fundamento
    assert "2025-12-19" in fundamento
    assert "2025-12-27" in fundamento
    assert "art. 5" in fundamento


def test_sin_fecha_de_publicacion_no_se_computa_nada() -> None:
    dictamen = _dictaminar(fecha_publicacion=None)
    assert not dictamen.automatica
    assert dictamen.valid_desde is None
    assert "sanción o de firma no la reemplaza" in dictamen.fundamento


def test_una_version_que_va_a_revision_no_trae_fecha_de_comienzo() -> None:
    """Si no se resuelve sola, no deja una fecha a medio computar."""
    for caso in (
        {"cierres_aprobados": 1},
        {"cierres_aprobados": 1, "reaperturas_aprobadas": 1},
        {"estado_declarado": EstadoLegal.NO_VIGENTE.value},
        {"estado_declarado": None},
        {"tiene_evidencia_de_estado": False},
    ):
        dictamen = _dictaminar(**caso)
        assert not dictamen.automatica, caso
        assert dictamen.valid_desde is None, caso
