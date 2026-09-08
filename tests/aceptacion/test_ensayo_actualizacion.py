"""HU-035: la actualización controlada, ejercida sobre la base de pruebas.

El ensayo corre entero acá para que no se rompa en silencio: si el diff deja de
detectar los artículos que cambiaron, o si propagar dos veces empieza a emitir
dos eventos, esto falla antes de que el reporte diga lo contrario.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import Connection

from backend_normativo.calidad import ensayo

pytestmark = [pytest.mark.integracion, pytest.mark.aceptacion]

RAIZ = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def resultado(conexion: Connection):
    return ensayo.correr(conexion, raiz=RAIZ)


def test_el_diff_encuentra_los_articulos_que_cambiaron(resultado) -> None:
    """El texto actualizado del Decreto 1382/2001 tiene tres unidades más y
    varias reescritas. Ninguna de esas diferencias es inventada: son las que
    InfoLEG publica entre el texto original y el consolidado."""
    assert resultado.diferencia is not None
    assert resultado.diferencia.hay_cambios
    assert resultado.unidades_antes == 105
    assert resultado.unidades_despues == 108
    assert resultado.resumen.get("AGREGADA", 0) >= 1
    assert resultado.resumen.get("MODIFICADA", 0) >= 1


def test_el_cambio_vence_la_frescura_de_la_norma(resultado) -> None:
    """Después de un cambio, la versión deja de poder servirse como actual
    hasta que alguien la verifique. No se deroga: se deja de afirmar."""
    assert resultado.versiones_con_frescura_vencida >= 1


def test_el_cambio_deja_un_evento_con_clave_de_idempotencia(resultado) -> None:
    assert resultado.evento_id is not None
    assert resultado.idempotency_key


def test_propagar_el_mismo_cambio_dos_veces_deja_un_solo_evento(resultado) -> None:
    """Un consumidor no debe recibir dos avisos del mismo cambio."""
    assert resultado.eventos_tras_repetir == 1


def test_el_reporte_dice_que_parte_del_ensayo_es_controlada(resultado) -> None:
    """Un ensayo que se presenta como una actualización real engaña. El reporte
    tiene que decir dónde termina lo real."""
    texto = ensayo.formatear(resultado)
    assert "Qué es real y qué es controlado" in texto
    assert "montaje" in resultado.procedencia["nota"]
    assert resultado.procedencia["sha256_captura_actualizado"]


def test_un_parrafo_insertado_no_produce_ochenta_cambios(resultado) -> None:
    """Las rutas llevan un ordinal para no colisionar, y ese ordinal corre
    cuando se inserta un párrafo. Sin emparejar por contenido, agregar tres
    párrafos produciría 81 cambios de los cuales 78 serían el mismo texto en
    otro lugar: la cola de revisión se llenaría de ruido y el cambio real
    quedaría escondido."""
    assert resultado.diferencia is not None
    assert resultado.resumen.get("DESPLAZADA", 0) >= 1
    sustantivos = resultado.diferencia.sustantivos
    assert len(sustantivos) < len(resultado.diferencia.cambios)
    assert all(c.clase != "DESPLAZADA" for c in sustantivos)
