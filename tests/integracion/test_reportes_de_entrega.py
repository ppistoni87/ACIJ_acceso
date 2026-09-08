"""HU-035 y HU-039: los reportes de entrega se verifican, no se declaran.

Estas pruebas existen porque un mapa de trazabilidad y un estado de backlog
envejecen en silencio: alguien renombra una prueba o mueve un módulo y el
documento sigue diciendo que todo está cubierto. Acá se rompen en ese momento.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import Connection

from backend_normativo.calidad import backlog, trazabilidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def test_el_mapa_de_trazabilidad_cubre_los_ochenta_casos() -> None:
    """El mapa no puede citar casos que el paquete no tiene ni pruebas que no
    existen: `construir` falla en cualquiera de los dos casos."""
    reporte = trazabilidad.construir(raiz=RAIZ)
    assert reporte.total == 80
    assert reporte.cubiertos + reporte.parciales + reporte.no_ejecutados == 80


def test_ningun_caso_no_ejecutado_queda_sin_motivo() -> None:
    """Un caso sin pruebas tiene que decir qué capacidad falta. «Pendiente» no
    es un motivo: no le dice a nadie qué habría que construir."""
    reporte = trazabilidad.construir(raiz=RAIZ)
    sin_motivo = [c.id for c in reporte.casos if c.estado == "NO_EJECUTADO" and not c.motivo]
    assert sin_motivo == []


def test_ningun_caso_parcial_queda_sin_decir_que_le_falta() -> None:
    reporte = trazabilidad.construir(raiz=RAIZ)
    sin_falta = [c.id for c in reporte.casos if c.estado == "CUBIERTO_PARCIAL" and not c.falta]
    assert sin_falta == []


def test_el_backlog_cubre_las_ciento_veintitres_historias(conexion: Connection) -> None:
    """Cada historia transversal declara estado y cada evidencia que declara
    existe; las de fuente salen de la base."""
    reporte = backlog.construir(conexion, raiz=RAIZ)
    assert reporte.total == 123
    assert len(reporte.transversales) == 40
    assert len(reporte.fuentes) == 83


def test_toda_historia_no_cerrada_dice_que_le_falta(conexion: Connection) -> None:
    reporte = backlog.construir(conexion, raiz=RAIZ)
    sin_explicacion = [h.id for h in reporte.transversales if h.estado != "CERRADA" and not h.falta]
    assert sin_explicacion == []


def test_toda_fuente_detenida_dice_por_que(conexion: Connection) -> None:
    """Una fuente bloqueada sin motivo es indistinguible de una que nadie miró."""
    reporte = backlog.construir(conexion, raiz=RAIZ)
    mudas = [h.id for h in reporte.fuentes if h.estado == "BLOQUEADA" and not h.detencion]
    assert mudas == []


def test_los_estados_declarados_son_del_vocabulario() -> None:
    declarado = json.loads((RAIZ / backlog.RUTA_ESTADO).read_text())["transversales"]
    fuera = {
        hu: entrada["estado"]
        for hu, entrada in declarado.items()
        if entrada["estado"] not in backlog.ESTADOS
    }
    assert fuera == {}
