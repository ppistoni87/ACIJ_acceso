"""Cada fuente contra la historia que declara (P-006).

Lo que se prueba acá no es cuántas sirven —eso cambia con el corpus— sino que el
recuento no llame pendiente a lo que ya está decidido. Un alias, una fuente
retirada y una de referencia no esperan turno: contarlas como «sin correr» infla
el denominador con trabajo que nadie va a hacer porque no hay nada que hacer.
"""

from __future__ import annotations

import dataclasses

import pytest
from sqlalchemy import Connection

pytestmark = pytest.mark.integracion


def test_una_fuente_retirada_no_es_trabajo_pendiente(conexion: Connection, crear_fuente) -> None:
    """El catálogo ya decidió: contarla como «sin correr» inventa una tarea."""
    from backend_normativo.calidad.fuentes import NO_SE_INGESTA, construir

    crear_fuente("Z01", estado="RETIRED", motivo_estado="El portal se dio de baja en 2024.")
    crear_fuente("Z02", clase="ALIAS")
    crear_fuente(
        "Z03", estado="REFERENCE_ONLY", motivo_estado="Se cita en el manual, no se ingesta."
    )

    reporte = construir(conexion)
    veredictos = {f.source_id: f.veredicto for f in reporte.fuentes}
    assert veredictos["Z01"] == NO_SE_INGESTA
    assert veredictos["Z02"] == NO_SE_INGESTA, "un alias no es una fuente: es otro nombre"
    assert veredictos["Z03"] == NO_SE_INGESTA

    porque = {f.source_id: f.por_que_no_se_ingesta for f in reporte.fuentes}
    assert "retirada" in porque["Z01"]
    assert "alias" in porque["Z02"]
    assert "referencia" in porque["Z03"]


def test_una_fuente_de_carga_manual_espera_a_una_persona(
    conexion: Connection, crear_fuente
) -> None:
    """Está pendiente, y lo que falta no es correr un capturador."""
    from backend_normativo.calidad.fuentes import ESPERA_CARGA_MANUAL, construir

    crear_fuente("Z04", estado="MANUAL", motivo_estado="El contenido se sube, no se captura.")
    veredictos = {f.source_id: f.veredicto for f in construir(conexion).fuentes}
    assert veredictos["Z04"] == ESPERA_CARGA_MANUAL


def test_una_fuente_activa_sin_capturas_si_esta_sin_correr(
    conexion: Connection, crear_fuente
) -> None:
    from backend_normativo.calidad.fuentes import SIN_CORRER, construir

    crear_fuente("Z05", estado="ACTIVE")
    veredictos = {f.source_id: f.veredicto for f in construir(conexion).fuentes}
    assert veredictos["Z05"] == SIN_CORRER


def test_el_reporte_declara_sobre_cuantas_tiene_sentido_esperar_filas(
    conexion: Connection, crear_fuente
) -> None:
    """HU-001 pide denominadores y pide no usarlos como sinónimos."""
    from backend_normativo.calidad.fuentes import construir, formatear

    crear_fuente("Z06", estado="RETIRED", motivo_estado="El portal se dio de baja en 2024.")
    crear_fuente("Z07", estado="ACTIVE")
    texto = formatear(construir(conexion))
    assert "Sobre las que se pueden ingestar hoy" in texto
    assert "No se ingestan" in texto


def test_una_fuente_que_declara_que_no_hay_nada_no_es_una_deuda(
    conexion: Connection, crear_fuente
) -> None:
    """«La atención presencial permanecerá cerrada» es la respuesta, no un vacío.

    Contarla como fuente que no llegó a destino inventa una tarea que nadie
    puede completar, porque no hay qué cargar.
    """
    from backend_normativo.calidad.fuentes import DECLARA_AUSENCIA, FuenteVerificada

    fuente = FuenteVerificada(
        source_id="Z08",
        nombre="Sedes presenciales",
        clase="DIRECTORIO",
        prioridad="P1",
        estado="ACTIVE",
        access_status="ACCESIBLE",
        capturas=1,
        doc_versiones=1,
        declaradas=["puntos_atencion"],
        cierre_declarado="la atención presencial permanecerá cerrada",
    )
    assert fuente.veredicto == DECLARA_AUSENCIA

    sin_cierre = dataclasses.replace(fuente, cierre_declarado=None)
    assert sin_cierre.veredicto != DECLARA_AUSENCIA
    del crear_fuente
