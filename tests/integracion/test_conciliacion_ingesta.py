"""P-005: cerrar una importación exige que las cuentas cierren.

Lo que se fija acá es la aritmética y, sobre todo, lo que la aritmética
descubrió: contadores que parecían rechazos —`literales_sin_dato`,
`sin_clave_canonica`— describen filas que sí entraron. Contarlos como caídas
daba conciliaciones negativas sobre importadores que funcionaban bien.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.ingesta.conciliacion import (
    CONTROL,
    Conciliacion,
    conciliar,
    formatear,
    registrar,
)

pytestmark = pytest.mark.integracion


def test_lo_que_no_se_creo_ni_se_reconocio_se_cayo() -> None:
    c = Conciliacion(importador="x", leidas=100, nuevas=30, repetidas=60)
    assert c.rechazadas == 10
    assert c.de_mas == 0
    assert c.cuadra


def test_una_observacion_no_es_un_rechazo() -> None:
    """El error del primer intento: restar de la suma algo que sí entró."""
    c = Conciliacion(
        importador="x",
        leidas=229,
        nuevas=0,
        repetidas=229,
        observaciones={"literales_sin_dato": 153},
    )
    assert c.rechazadas == 0, "las 229 entraron; 153 de ellas con un campo vacío"
    assert c.cuadra


def test_dar_de_cuenta_de_mas_no_pasa_por_bueno() -> None:
    c = Conciliacion(importador="x", leidas=10, nuevas=8, repetidas=5)
    assert c.de_mas == 3
    assert not c.cuadra


def test_actualizar_lo_que_no_estaba_no_es_posible() -> None:
    c = Conciliacion(importador="x", leidas=10, nuevas=10, repetidas=0, actualizadas=2)
    assert not c.cuadra


def test_una_fila_caida_sin_motivo_es_un_error_sin_causa() -> None:
    c = Conciliacion(importador="x", leidas=10, nuevas=4, repetidas=4)
    assert c.rechazadas == 2
    assert not c.rechazos_con_causa

    con_causa = Conciliacion(
        importador="x", leidas=10, nuevas=4, repetidas=4, motivos={"sin_id": 2}
    )
    assert con_causa.rechazos_con_causa


def _captura_minima(conexion: Connection) -> str:
    import uuid

    source_id = f"P5{uuid.uuid4().hex[:6]}"
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso) VALUES (:s, :n, 'PORTAL_NORMATIVO', 'ACTIVE', "
            "'ACCESIBLE', 'P0', "
            "'PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS')"
        ),
        {"s": source_id, "n": f"Fuente {source_id}"},
    )
    url = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"s": source_id, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES (:s, 1, 'DATASET_ABIERTO') RETURNING id"
        ),
        {"s": source_id},
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES (:s, :c, 'EN_CURSO', 'test-0') RETURNING id"
        ),
        {"s": source_id, "c": cfg},
    ).scalar_one()
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri) "
            "VALUES (:c, :u, :h, :o) RETURNING id"
        ),
        {
            "c": corrida,
            "u": url,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://var/objetos/{uuid.uuid4()}",
        },
    ).scalar_one()
    return captura


def test_la_conciliacion_queda_pegada_a_la_corrida(conexion: Connection) -> None:
    """Guardarla es lo que la hace servir tres días después."""
    captura = _captura_minima(conexion)
    registrar(
        conexion,
        captura,
        Conciliacion(importador="prueba", leidas=10, nuevas=10, source_id="PX"),
    )

    fila = conexion.execute(
        text(
            "SELECT cc.resultado, cc.observado FROM controles_calidad cc "
            " JOIN capturas c ON c.corrida_id = cc.corrida_id "
            " WHERE c.id = :cap AND cc.control_id = :ctrl"
        ),
        {"cap": captura, "ctrl": CONTROL},
    ).one()
    assert fila.resultado == "PASA"
    assert fila.observado["leidas"] == 10

    reporte = conciliar(conexion)
    assert any(f.importador == "prueba" for f in reporte.filas)
    assert "prueba" in formatear(reporte)


def test_una_conciliacion_que_no_cierra_queda_como_falla(conexion: Connection) -> None:
    captura = _captura_minima(conexion)
    registrar(conexion, captura, Conciliacion(importador="rota", leidas=10, nuevas=4, repetidas=4))

    reporte = conciliar(conexion)
    rota = next(f for f in reporte.filas if f.importador == "rota")
    assert rota.resultado == "FALLA"
    assert not reporte.todo_cierra
    assert "sin motivo declarado" in formatear(reporte)


def test_una_corrida_a_medias_impide_dar_la_carga_por_cerrada(conexion: Connection) -> None:
    """Reanudarla es trabajo pendiente, y la conciliación lo dice."""
    captura = _captura_minima(conexion)
    registrar(conexion, captura, Conciliacion(importador="ok", leidas=1, nuevas=1))
    conexion.execute(
        text(
            'UPDATE corridas_ingesta SET checkpoint = \'{"urls_hechas": ["a"]}\'::jsonb '
            " WHERE id = (SELECT corrida_id FROM capturas WHERE id = :cap)"
        ),
        {"cap": captura},
    )

    reporte = conciliar(conexion)

    assert not reporte.con_falla, "la importación cerró bien"
    assert reporte.corridas_abiertas, "pero quedó una corrida sin terminar"
    assert not reporte.todo_cierra
    assert "Corridas a medias" in formatear(reporte)
