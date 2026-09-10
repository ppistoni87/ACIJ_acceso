"""La identidad decide los roles y el actor auditado (P-017 criterio 1).

Lo que se prueba acá no es que el token se firme bien —eso está en las
unitarias— sino lo que pasa del lado de las rutas: que un actor no se pueda
declarar solo, que un revisor no publique, que una credencial revocada deje de
servir en el pedido siguiente y que la bitácora conserve cómo se estableció cada
actor.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Connection, text

from backend_normativo.seguridad.credenciales import (
    IDENTIDAD_AUTODECLARADA,
    IDENTIDAD_CREDENCIAL,
    ROL_PUBLICADOR,
    ROL_REVISOR,
    emitir,
)

pytestmark = pytest.mark.integracion

SECRETO = "secreto-de-prueba-que-no-vive-en-produccion"


@pytest.fixture
def con_secreto(monkeypatch):
    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", SECRETO)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    monkeypatch.delenv("BN_ADMIN_TOKENS", raising=False)
    return SECRETO


def _credencial(roles, actor="curacion_juridica:persona", dias=30):
    token, identidad = emitir(
        actor, roles, duracion=dt.timedelta(days=dias), secreto_bytes=SECRETO.encode()
    )
    return token, identidad


def _incidencia(conexion: Connection, corpus) -> tuple:
    from backend_normativo.curacion.vigencia import ResolutorVigencia

    del corpus
    ResolutorVigencia(conexion).resolver()
    incidencia = conexion.execute(
        text("SELECT id FROM incidencias_revision WHERE tipo = 'VIGENCIA_INDETERMINADA' LIMIT 1")
    ).scalar_one()
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    return incidencia, evidencia


def _resolver(cliente, token, incidencia, evidencia, **cabeceras):
    return cliente.post(
        f"/v1/admin/revisiones/{incidencia}/resolver",
        json={
            "decision": "Publicada, sin norma derogatoria registrada.",
            "fundamento_evidencia_id": str(evidencia),
            "vigencia": {
                "valid_tipo": "ABIERTO_FIN",
                "valid_desde": "2025-12-23",
                "estado_legal": "VIGENTE",
            },
        },
        headers={"Authorization": f"Bearer {token}", **cabeceras},
    )


def test_sin_credencial_no_se_administra(cliente_api, con_secreto, conexion, corpus) -> None:
    incidencia, evidencia = _incidencia(conexion, corpus)
    respuesta = cliente_api.post(
        f"/v1/admin/revisiones/{incidencia}/resolver",
        json={"decision": "x", "fundamento_evidencia_id": str(evidencia)},
    )
    assert respuesta.status_code == 401


def test_el_actor_no_se_declara_solo(cliente_api, con_secreto, conexion, corpus) -> None:
    """Aunque la cabecera diga otra cosa, quien firma es quien dice la credencial."""
    incidencia, evidencia = _incidencia(conexion, corpus)
    token, _ = _credencial({ROL_REVISOR}, actor="curacion_juridica:quien_de_verdad")

    respuesta = _resolver(
        cliente_api, token, incidencia, evidencia, **{"X-Actor": "el_presidente_de_la_nacion"}
    )
    assert respuesta.status_code == 200

    actor = conexion.execute(
        text("SELECT actor, identidad FROM auditoria_eventos ORDER BY ocurrido_en DESC LIMIT 1")
    ).one()
    assert actor.actor == "curacion_juridica:quien_de_verdad"
    assert actor.identidad == IDENTIDAD_CREDENCIAL


def test_un_revisor_no_publica(cliente_api, con_secreto) -> None:
    """Revisar y publicar son decisiones distintas y las toma gente distinta."""
    token, _ = _credencial({ROL_REVISOR})
    respuesta = cliente_api.post(
        "/v1/admin/releases",
        json={"motivo": "un corte que este actor no puede firmar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 403
    assert "no autoriza a publicador" in respuesta.json()["detail"]["detalle"]


def test_un_publicador_no_decide_reglas(cliente_api, con_secreto, conexion, corpus) -> None:
    incidencia, evidencia = _incidencia(conexion, corpus)
    token, _ = _credencial({ROL_PUBLICADOR})
    respuesta = _resolver(cliente_api, token, incidencia, evidencia)
    assert respuesta.status_code == 403
    assert "no autoriza a revisor" in respuesta.json()["detail"]["detalle"]


def test_una_credencial_revocada_deja_de_servir(cliente_api, con_secreto, conexion, corpus) -> None:
    """Revocación de sesión: el criterio la pide con nombre."""
    incidencia, evidencia = _incidencia(conexion, corpus)
    token, identidad = _credencial({ROL_REVISOR})

    conexion.execute(
        text(
            "INSERT INTO credenciales_revocadas (jti, actor, motivo, revocada_por) "
            "VALUES (:j, :a, 'se perdió el equipo', 'operaciones')"
        ),
        {"j": identidad.jti, "a": identidad.actor},
    )

    respuesta = _resolver(cliente_api, token, incidencia, evidencia)
    assert respuesta.status_code == 403
    assert "revocada" in respuesta.json()["detail"]["detalle"]


def test_una_credencial_vencida_no_entra(cliente_api, con_secreto, conexion, corpus) -> None:
    incidencia, evidencia = _incidencia(conexion, corpus)
    token, _ = emitir(
        "alguien",
        {ROL_REVISOR},
        duracion=dt.timedelta(days=1),
        secreto_bytes=SECRETO.encode(),
        ahora=dt.datetime.now(dt.UTC) - dt.timedelta(days=5),
    )
    respuesta = _resolver(cliente_api, token, incidencia, evidencia)
    assert respuesta.status_code == 403
    assert "venció" in respuesta.json()["detail"]["detalle"]


def test_el_token_compartido_no_alcanza_en_produccion(
    cliente_api, conexion, corpus, monkeypatch
) -> None:
    """Identifica al despliegue, no a la persona: quien lo tenga firma como cualquiera."""
    incidencia, evidencia = _incidencia(conexion, corpus)
    monkeypatch.setenv("BN_ADMIN_TOKENS", "token-compartido")
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)

    respuesta = _resolver(
        cliente_api, "token-compartido", incidencia, evidencia, **{"X-Actor": "cualquiera"}
    )
    assert respuesta.status_code == 403
    assert "identifica al despliegue" in respuesta.json()["detail"]["detalle"]


def test_en_desarrollo_se_admite_pero_queda_marcado(
    cliente_api, conexion, corpus, monkeypatch
) -> None:
    """Lo que se firma con identidad autodeclarada se distingue para siempre."""
    incidencia, evidencia = _incidencia(conexion, corpus)
    monkeypatch.setenv("BN_ADMIN_TOKENS", "token-compartido")
    monkeypatch.setenv("BN_IDENTIDAD_MODO", "desarrollo")

    respuesta = _resolver(
        cliente_api, "token-compartido", incidencia, evidencia, **{"X-Actor": "quien_prueba"}
    )
    assert respuesta.status_code == 200

    evento = conexion.execute(
        text("SELECT actor, identidad FROM auditoria_eventos ORDER BY ocurrido_en DESC LIMIT 1")
    ).one()
    assert evento.actor == "quien_prueba"
    assert evento.identidad == IDENTIDAD_AUTODECLARADA


def test_lo_que_escribe_el_cli_queda_como_proceso_local(conexion: Connection) -> None:
    """Sin sesión que lo declare, un evento es lo que efectivamente es."""
    conexion.execute(
        text(
            "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id) "
            "VALUES ('cli:alguien', 'PRUEBA', 'nada', 'nada')"
        )
    )
    identidad = conexion.execute(
        text("SELECT identidad FROM auditoria_eventos ORDER BY ocurrido_en DESC LIMIT 1")
    ).scalar_one()
    assert identidad == "PROCESO_LOCAL"
