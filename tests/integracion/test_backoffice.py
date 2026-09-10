"""La cola de revisión y la consola que la muestra (P-016 criterio 1).

Lo que se prueba del lado del servidor: que la cola clasifique en pilas, que
filtre, que exija el rol de revisor y que la página se sirva desde la misma
aplicación. El comportamiento del navegador no se prueba acá; lo que sí se
prueba es que el archivo que la consola necesita viaje con el paquete, porque
una consola que existe en el repositorio y no en la imagen es una consola que no
existe.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Connection, text

from backend_normativo.seguridad.credenciales import ROL_PUBLICADOR, ROL_REVISOR, emitir

pytestmark = pytest.mark.integracion

SECRETO = "secreto-de-prueba-que-no-vive-en-produccion"


@pytest.fixture
def revisor(monkeypatch) -> str:
    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", SECRETO)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    token, _ = emitir(
        "curacion_juridica:persona",
        {ROL_REVISOR},
        duracion=dt.timedelta(days=1),
        secreto_bytes=SECRETO.encode(),
    )
    return token


@pytest.fixture
def reglas(conexion: Connection, regla_candidata) -> int:
    """Cuántas candidatas hay para revisar."""
    del regla_candidata
    return conexion.execute(
        text("SELECT count(*) FROM reglas WHERE estado_revision = 'CANDIDATE'")
    ).scalar_one()


def test_la_consola_se_sirve_desde_la_misma_aplicacion(cliente_api) -> None:
    """Un artefacto que viaja aparte se desfasa de la API que consume."""
    respuesta = cliente_api.get("/backoffice/reglas")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "Revisión de reglas" in respuesta.text
    # La credencial la pone quien entra y vive en su pestaña: nada la escribe
    # en el disco del navegador ni en una cookie. Se comprueba que no se use el
    # almacenamiento, no que no se lo nombre —el archivo explica en un
    # comentario por qué no lo usa, y esa explicación no es un uso—.
    assert ".setItem(" not in respuesta.text
    assert "document.cookie" not in respuesta.text


def test_la_cola_exige_el_rol_de_revisor(cliente_api, monkeypatch) -> None:
    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", SECRETO)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    token, _ = emitir(
        "publicacion:persona",
        {ROL_PUBLICADOR},
        duracion=dt.timedelta(days=1),
        secreto_bytes=SECRETO.encode(),
    )
    respuesta = cliente_api.get("/v1/admin/reglas", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403


def test_sin_credencial_no_hay_cola(cliente_api) -> None:
    assert cliente_api.get("/v1/admin/reglas").status_code == 401


def test_la_cola_clasifica_en_pilas(cliente_api, revisor, reglas) -> None:
    """Las pilas no son decoración: no se revisan igual y el riesgo no es el mismo."""
    respuesta = cliente_api.get(
        "/v1/admin/reglas?estado=CANDIDATE", headers={"Authorization": f"Bearer {revisor}"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["total"] == reglas
    assert cuerpo["por_clase"], "cada regla cae en alguna pila"
    assert sum(cuerpo["por_clase"].values()) == reglas
    assert cuerpo["por_estado"]["CANDIDATE"] == reglas

    for regla in cuerpo["reglas"]:
        assert regla["que_hay_que_decidir"], "cada regla trae la pregunta concreta"
        assert regla["texto_literal"]
        assert regla["clase"]


def test_la_cola_filtra_por_pila(cliente_api, revisor, reglas) -> None:
    del reglas
    todas = cliente_api.get(
        "/v1/admin/reglas", headers={"Authorization": f"Bearer {revisor}"}
    ).json()
    clase = next(iter(todas["por_clase"]))

    filtrada = cliente_api.get(
        f"/v1/admin/reglas?clase={clase}", headers={"Authorization": f"Bearer {revisor}"}
    ).json()
    assert filtrada["total"] == todas["por_clase"][clase]
    assert all(r["clase"] == clase for r in filtrada["reglas"])


def test_la_cola_filtra_por_beneficio(cliente_api, revisor, reglas) -> None:
    del reglas
    todas = cliente_api.get(
        "/v1/admin/reglas", headers={"Authorization": f"Bearer {revisor}"}
    ).json()
    beneficio = next(iter(todas["por_beneficio"]))

    filtrada = cliente_api.get(
        f"/v1/admin/reglas?beneficio={beneficio}",
        headers={"Authorization": f"Bearer {revisor}"},
    ).json()
    assert filtrada["total"] == todas["por_beneficio"][beneficio]
    assert all(r["beneficio"] == beneficio for r in filtrada["reglas"])


def test_una_regla_decidida_sale_de_la_cola_de_candidatas(
    cliente_api, revisor, reglas, conexion: Connection
) -> None:
    """El recorrido entero: la cola, el expediente, la firma y la cola de nuevo."""
    cabeceras = {"Authorization": f"Bearer {revisor}"}
    antes = cliente_api.get("/v1/admin/reglas", headers=cabeceras).json()
    regla = antes["reglas"][0]

    ficha = cliente_api.get(f"/v1/admin/reglas/{regla['id']}", headers=cabeceras)
    assert ficha.status_code == 200
    assert ficha.json()["texto_literal"] == regla["texto_literal"]

    decision = cliente_api.post(
        f"/v1/admin/reglas/{regla['id']}/decidir",
        json={
            "decision": "APROBAR",
            "fundamento": "El literal del artículo sostiene la condición tal como está escrita.",
            "estado_esperado": "CANDIDATE",
        },
        headers=cabeceras,
    )
    assert decision.status_code == 200
    assert decision.json()["decidido_por"] == "curacion_juridica:persona"

    despues = cliente_api.get("/v1/admin/reglas", headers=cabeceras).json()
    assert despues["total"] == antes["total"] - 1
    assert regla["id"] not in [r["id"] for r in despues["reglas"]]

    aprobadas = cliente_api.get("/v1/admin/reglas?estado=APPROVED", headers=cabeceras).json()
    assert regla["id"] in [r["id"] for r in aprobadas["reglas"]]

    # Y la firma quedó atada a una identidad verificada, no a una declarada.
    evento = conexion.execute(
        text(
            "SELECT actor, identidad FROM auditoria_eventos "
            " WHERE objeto = 'reglas' ORDER BY ocurrido_en DESC LIMIT 1"
        )
    ).one()
    assert evento.actor == "curacion_juridica:persona"
    assert evento.identidad == "CREDENCIAL_FIRMADA"
