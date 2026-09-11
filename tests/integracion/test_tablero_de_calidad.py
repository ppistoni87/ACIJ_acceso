"""P-016 criterio 3: cada indicador se puede abrir, y ninguno es una constante.

Un número que no se puede abrir es un número que hay que creer. Y un tablero que
cuenta por un lado y lista por otro miente el día que alguien toque una de las
dos consultas: el número dice doce, la lista muestra nueve, y no hay forma de
saber cuál está mal.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.calidad import tablero

pytestmark = pytest.mark.integracion

SECRETO = "secreto-de-prueba-tablero"


@pytest.fixture
def credencial(monkeypatch) -> str:
    """Una credencial de auditoría firmada, por el camino de producción."""
    import datetime as dt

    from backend_normativo.seguridad.credenciales import ROL_AUDITOR, emitir

    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", SECRETO)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    monkeypatch.delenv("BN_ADMIN_TOKENS", raising=False)
    token, _ = emitir(
        "auditoria-de-prueba",
        {ROL_AUDITOR},
        duracion=dt.timedelta(hours=1),
        secreto_bytes=SECRETO.encode(),
    )
    return token


def test_todos_los_indicadores_consultan_la_base(conexion: Connection) -> None:
    """Ninguna consulta rota, ninguna cifra escrita a mano.

    El criterio pide con esas palabras que los conteos no vengan de constantes
    de demostración, así que se corren las cinco contra el esquema real.
    """
    for indicador in tablero.INDICADORES:
        medicion = tablero.medir(conexion, indicador, limite=0)
        assert medicion.cuantos >= 0


def test_el_numero_y_las_filas_salen_de_la_misma_consulta(conexion: Connection) -> None:
    """La propiedad que hace confiable al tablero.

    Si el conteo viniera de un `COUNT(*)` y las filas de un `SELECT` parecido,
    podrían discrepar sin que nada avise. Acá abrir un indicador sin límite tiene
    que dar exactamente tantas filas como dice su número.
    """
    for indicador in tablero.INDICADORES:
        medicion = tablero.medir(conexion, indicador)
        assert len(medicion.filas) == medicion.cuantos, indicador.clave


def test_el_limite_recorta_lo_mostrado_y_no_lo_contado(conexion: Connection) -> None:
    """Un tablero que dijera «2» porque mostró dos mediría su propia paginación."""
    indicador = tablero.POR_CLAVE["reglas_sin_firmar"]
    completo = tablero.medir(conexion, indicador)
    if completo.cuantos < 2:
        pytest.skip("El corpus de prueba no tiene suficientes reglas candidatas.")
    recortado = tablero.medir(conexion, indicador, limite=1)
    assert recortado.cuantos == completo.cuantos
    assert len(recortado.filas) == 1


def test_cada_indicador_dice_por_que_importa() -> None:
    """Un tablero de cifras sin sentido obliga a preguntar qué significa cada una."""
    for indicador in tablero.INDICADORES:
        assert indicador.porque.strip(), indicador.clave
        assert indicador.titulo.strip(), indicador.clave


def test_las_claves_no_se_repiten() -> None:
    claves = [i.clave for i in tablero.INDICADORES]
    assert len(claves) == len(set(claves))


def test_el_tablero_exige_credencial(cliente_api) -> None:
    assert cliente_api.get("/v1/admin/calidad").status_code == 401


def test_un_indicador_que_no_existe_dice_cuales_hay(cliente_api, credencial: str) -> None:
    """Un 404 mudo obliga a leer el código para saber qué pedir."""
    respuesta = cliente_api.get(
        "/v1/admin/calidad/no_existe", headers={"Authorization": f"Bearer {credencial}"}
    )
    assert respuesta.status_code == 404
    assert "reglas_sin_firmar" in respuesta.json()["detail"]["detalle"]


def test_abrir_un_indicador_devuelve_sus_registros(
    cliente_api, credencial: str, conexion: Connection
) -> None:
    conexion.execute(text("SELECT 1"))
    cuerpo = cliente_api.get(
        "/v1/admin/calidad/reglas_sin_firmar?limite=3",
        headers={"Authorization": f"Bearer {credencial}"},
    ).json()
    assert cuerpo["cuantos"] >= cuerpo["mostrados"]
    assert len(cuerpo["registros"]) == cuerpo["mostrados"]
