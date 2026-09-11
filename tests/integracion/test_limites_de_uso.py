"""La API aplica los límites, y frenar deja rastro (P-017, criterio 3).

Estas pruebas encienden el límite a propósito: el resto de la suite lo corre
apagado porque todas las pruebas comparten un mismo origen y un mismo proceso.
"""

from __future__ import annotations

import datetime as dt
import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, text

from backend_normativo.api.limites import (
    VARIABLE_LIMITE,
    VARIABLE_LIMITE_AUTENTICACION,
    reiniciar_limitadores,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def cliente_limitado(conexion: Connection) -> Iterator:
    """Un cliente con cupo de 3 consultas por minuto y 2 credenciales fallidas."""
    from fastapi.testclient import TestClient

    from backend_normativo.api.app import crear_app
    from backend_normativo.api.dependencias import conexion_administracion, conexion_lectura

    previos = {
        VARIABLE_LIMITE: os.environ.get(VARIABLE_LIMITE),
        VARIABLE_LIMITE_AUTENTICACION: os.environ.get(VARIABLE_LIMITE_AUTENTICACION),
    }
    os.environ[VARIABLE_LIMITE] = "3"
    os.environ[VARIABLE_LIMITE_AUTENTICACION] = "2"
    reiniciar_limitadores()

    app = crear_app()
    app.dependency_overrides[conexion_lectura] = lambda: conexion
    app.dependency_overrides[conexion_administracion] = lambda: conexion
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        for variable, valor in previos.items():
            if valor is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = valor
        reiniciar_limitadores()


def test_pasado_el_cupo_se_contesta_429_tipado(cliente_limitado) -> None:
    for _ in range(3):
        assert cliente_limitado.get("/v1/normas?limite=1").status_code == 200
    respuesta = cliente_limitado.get("/v1/normas?limite=1")
    assert respuesta.status_code == 429
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "RATE_LIMITED"
    # Dice cuánto esperar: sin eso, un cliente automático reintenta en bucle.
    assert int(respuesta.headers["Retry-After"]) >= 1


def test_el_429_no_revela_nada_del_servicio(cliente_limitado) -> None:
    for _ in range(4):
        respuesta = cliente_limitado.get("/v1/normas?limite=1")
    texto = respuesta.text.lower()
    for filtracion in ("traceback", "select ", "psycopg", "sqlalchemy", "balde"):
        assert filtracion not in texto


def test_frenar_deja_rastro(cliente_limitado, conexion: Connection) -> None:
    """Un límite que frena sin dejar rastro no se puede ajustar.

    No hay forma de saber si está frenando abuso o gente. Por eso los límites
    van **adentro** de la observabilidad y no afuera.
    """
    antes = conexion.execute(
        text("SELECT count(*) FROM consultas_auditadas WHERE resultado_tipo = 'ERROR'")
    ).scalar_one()
    for _ in range(5):
        cliente_limitado.get("/v1/normas?limite=1")
    despues = conexion.execute(
        text(
            "SELECT count(*) FROM consultas_auditadas "
            " WHERE resultado_tipo = 'ERROR' AND motivo_abstencion = 'HTTP 429'"
        )
    ).scalar_one()
    assert despues > 0, "el 429 tiene que quedar medido como cualquier otra respuesta"
    del antes


def test_el_limite_no_alcanza_a_las_sondas(cliente_limitado) -> None:
    """Si el orquestador queda sin cupo, saca de servicio una instancia sana."""
    for _ in range(10):
        assert cliente_limitado.get("/salud").status_code == 200


def test_las_credenciales_fallidas_tienen_su_propio_cupo(cliente_limitado) -> None:
    """Probar mil veces no puede costar lo mismo que probar una vez."""
    cabeceras = {"Authorization": "Bearer no-sirve"}
    primera = cliente_limitado.get("/v1/admin/normas", headers=cabeceras)
    assert primera.status_code in (401, 403)
    segunda = cliente_limitado.get("/v1/admin/normas", headers=cabeceras)
    assert segunda.status_code in (401, 403)
    tercera = cliente_limitado.get("/v1/admin/normas", headers=cabeceras)
    assert tercera.status_code == 429
    assert tercera.json()["codigo"] == "RATE_LIMITED"


def test_una_credencial_valida_no_gasta_el_cupo_de_los_fallos(
    cliente_limitado, monkeypatch
) -> None:
    from backend_normativo.seguridad.credenciales import ROL_REVISOR, emitir

    secreto = "secreto-de-prueba-limites"
    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", secreto)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    token, _ = emitir(
        "revisor-de-prueba",
        {ROL_REVISOR},
        duracion=dt.timedelta(hours=1),
        secreto_bytes=secreto.encode(),
    )
    cabeceras = {"Authorization": f"Bearer {token}"}
    for _ in range(3):
        assert cliente_limitado.get("/v1/admin/normas", headers=cabeceras).status_code == 200
