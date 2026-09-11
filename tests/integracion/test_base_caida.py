"""Con la base caída, el servicio dice «ahora no puedo» y no «salió mal».

La diferencia no es cosmética. Un 500 dice «esta petición salió mal» y un
balanceador la vuelve a mandar a la misma instancia; un 503 con `Retry-After`
dice «esta instancia no puede ahora», que es lo que corresponde cuando lo que
falta es la base y no la consulta.

Acá se prueba el manejador con la base simulada como caída. Apagarla de verdad,
con veinte conversaciones encima y midiendo cuánto tarda en volver, es el ensayo
de carga: `bn calidad carga`.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.exc import OperationalError

pytestmark = pytest.mark.integracion


@pytest.fixture
def cliente_sin_base() -> Iterator:
    import os

    from fastapi.testclient import TestClient

    from backend_normativo.api.app import crear_app
    from backend_normativo.api.dependencias import conexion_lectura
    from backend_normativo.api.limites import VARIABLE_LIMITE, reiniciar_limitadores

    def caida():
        raise OperationalError("SELECT 1", {}, Exception("could not connect to server"))

    anterior = os.environ.get(VARIABLE_LIMITE)
    os.environ[VARIABLE_LIMITE] = "0"
    reiniciar_limitadores()
    app = crear_app()
    app.dependency_overrides[conexion_lectura] = caida
    try:
        with TestClient(app, raise_server_exceptions=False) as cliente:
            yield cliente
    finally:
        if anterior is None:
            os.environ.pop(VARIABLE_LIMITE, None)
        else:
            os.environ[VARIABLE_LIMITE] = anterior
        reiniciar_limitadores()


def test_una_consulta_con_la_base_caida_es_503(cliente_sin_base) -> None:
    respuesta = cliente_sin_base.get("/v1/normas")
    assert respuesta.status_code == 503
    assert respuesta.headers.get("Retry-After")


def test_el_cuerpo_es_tipado_y_no_cuenta_la_cocina(cliente_sin_base) -> None:
    cuerpo = cliente_sin_base.get("/v1/normas").json()
    assert cuerpo["codigo"] == "SOURCE_UNAVAILABLE"
    # Ni el host, ni el usuario, ni el motor, ni la consulta que falló.
    texto = str(cuerpo).lower()
    for filtracion in ("could not connect", "select 1", "psycopg", "sqlalchemy", "postgres"):
        assert filtracion not in texto


def test_lo_dice_como_un_limite_del_servicio_y_no_como_una_respuesta(cliente_sin_base) -> None:
    """«No se pudo averiguar» no es «no te corresponde»."""
    detalle = cliente_sin_base.get("/v1/normas").json()["detalle"]
    assert "no pude fijarme" in detalle.lower()


def test_la_sonda_de_vida_sigue_en_pie(cliente_sin_base) -> None:
    """Si dependiera de la base, una base caída reiniciaría procesos sanos."""
    assert cliente_sin_base.get("/salud").status_code == 200


def test_la_sonda_de_servicio_dice_que_no(monkeypatch) -> None:
    """Es lo que un orquestador lee para dejar de mandarle tráfico.

    Esta se arma aparte porque `/listo` **no** usa la dependencia de lectura:
    abre su propia conexión, a propósito, para poder contestar cuando la base no
    está en vez de caerse con ella. Así que simular la caída sustituyendo la
    dependencia no la toca —se probó, y la sonda seguía diciendo que sí—: hay
    que hacer fallar el motor.
    """
    from fastapi.testclient import TestClient

    from backend_normativo.api import app as modulo_app

    def sin_motor():
        raise OperationalError("connect", {}, Exception("could not connect to server"))

    monkeypatch.setattr(modulo_app, "engine_api", sin_motor)
    with TestClient(modulo_app.crear_app(), raise_server_exceptions=False) as cliente:
        respuesta = cliente.get("/listo")
    assert respuesta.status_code == 503
    assert respuesta.json()["listo"] is False
