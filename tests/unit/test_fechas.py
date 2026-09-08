"""AT-053: rangos de fecha sin año.

«Del 20 de diciembre al 10 de enero» es una convocatoria real que no dice de qué
año es. Las dos maneras de arruinarlo son igual de fáciles y las dos producen un
rango exacto y verosímil: ponerle el año en curso, o sumarle uno porque enero es
después de diciembre.
"""

from __future__ import annotations

import datetime as dt

import pytest

from backend_normativo.plazos.fechas import normalizar_rangos

pytestmark = pytest.mark.aceptacion


def _uno(texto: str, **extra):
    rangos = normalizar_rangos(texto, **extra)
    assert len(rangos) == 1, f"Se esperaba un rango y salieron {len(rangos)}"
    return rangos[0]


# --- AT-053: no se completa el año ---------------------------------------------


def test_at053_un_rango_sin_año_queda_pendiente_de_contexto() -> None:
    rango = _uno("La inscripción va del 20 de diciembre al 10 de enero.")
    assert not rango.resuelto
    assert rango.requiere == "anio_de_las_fechas"
    assert "no se completa con el año en curso" in rango.motivo.lower()


def test_at053_el_año_en_curso_no_se_usa_nunca() -> None:
    """El resultado no depende de cuándo se corra: si dependiera, la misma
    convocatoria tendría fechas distintas según el día en que se consulte."""
    rango = _uno("Del 20 de diciembre al 10 de enero.")
    assert rango.inicio is None
    assert str(dt.date.today().year) not in (rango.motivo or "")


def test_at053_un_ciclo_declarado_no_fecha_las_inscripciones() -> None:
    """La inscripción para el ciclo 2026 suele hacerse en 2025. Equiparar el año
    del ciclo con el de los días es la misma suposición silenciosa vista del
    otro lado."""
    rango = _uno("Inscripción para el ciclo lectivo 2026: del 20 de diciembre al 10 de enero.")
    assert not rango.resuelto
    assert rango.ciclo == 2026
    assert "no dice si la inscripción ocurre ese año o el anterior" in rango.motivo


def test_at053_el_ciclo_queda_registrado_para_quien_lo_resuelva() -> None:
    """Dejarlo pendiente sin decir qué se sabe obligaría a volver a la fuente."""
    rango = _uno("Convocatoria 2027. Del 1 de septiembre al 30 de septiembre.")
    assert rango.ciclo == 2027


# --- Lo que sí se resuelve ------------------------------------------------------


def test_dos_extremos_con_año_se_resuelven_sin_derivar() -> None:
    """La contracara: si nunca resolviera, la abstención no probaría nada."""
    rango = _uno("Del 1 de marzo de 2026 al 30 de abril de 2026 se reciben solicitudes.")
    assert rango.inicio == dt.date(2026, 3, 1)
    assert rango.fin == dt.date(2026, 4, 30)
    assert rango.derivado is False


def test_un_rango_que_cruza_el_año_lo_deriva_y_lo_dice() -> None:
    """Derivar no es el problema; derivar en silencio sí."""
    rango = _uno("Del 20 de diciembre de 2025 al 10 de enero.")
    assert rango.inicio == dt.date(2025, 12, 20)
    assert rango.fin == dt.date(2026, 1, 10)
    assert rango.derivado is True
    assert rango.cruza_anio
    assert "cruza el fin de año" in rango.motivo


def test_un_año_aportado_a_sabiendas_fecha_el_rango_y_queda_marcado() -> None:
    """Quien resuelve la incidencia puede aportar el año; queda dicho que no
    salió del texto."""
    rango = _uno(
        "Inscripción para el ciclo lectivo 2026: del 20 de diciembre al 10 de enero.",
        contexto_anio=2025,
    )
    assert rango.inicio == dt.date(2025, 12, 20)
    assert rango.fin == dt.date(2026, 1, 10)
    assert rango.derivado is True
    assert "no el texto" in rango.motivo


def test_un_rango_dentro_del_mismo_año_no_suma_uno() -> None:
    rango = _uno("Del 1 de marzo de 2026 al 30 de abril.")
    assert rango.fin == dt.date(2026, 4, 30)
    assert not rango.cruza_anio


# --- Robustez -------------------------------------------------------------------


def test_una_fecha_que_no_existe_no_se_corrige() -> None:
    """El 31 de febrero no es el 28: corregirlo cambiaría el plazo."""
    rango = _uno("Del 31 de febrero de 2026 al 10 de marzo de 2026.")
    assert not rango.resuelto
    assert rango.requiere == "fecha_valida"


def test_se_reconocen_las_variantes_de_escritura() -> None:
    for texto in (
        "del 20 de diciembre de 2025 al 10 de enero de 2026",
        "Del 20 diciembre 2025 al 10 enero 2026",
        "del 20 de diciembre de 2025 hasta el 10 de enero de 2026",
    ):
        rango = _uno(texto)
        assert rango.inicio == dt.date(2025, 12, 20), texto
        assert rango.fin == dt.date(2026, 1, 10), texto


def test_se_acepta_setiembre_ademas_de_septiembre() -> None:
    rango = _uno("Del 1 de setiembre de 2026 al 30 de setiembre de 2026.")
    assert rango.inicio == dt.date(2026, 9, 1)


def test_varios_rangos_en_un_texto_se_normalizan_por_separado() -> None:
    rangos = normalizar_rangos(
        "Primera etapa: del 1 de marzo de 2026 al 30 de abril de 2026. "
        "Segunda etapa: del 20 de diciembre al 10 de enero."
    )
    assert len(rangos) == 2
    assert rangos[0].resuelto
    assert not rangos[1].resuelto


def test_un_texto_sin_rangos_no_inventa_ninguno() -> None:
    assert normalizar_rangos("La inscripción es por orden de llegada.") == []
