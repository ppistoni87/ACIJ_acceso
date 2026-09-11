"""HU-029 a HU-033: contrato de la API, abstención explicada y permisos."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion.vigencia import ResolutorVigencia
from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS

pytestmark = pytest.mark.integracion

TOKEN = "credencial-de-prueba"
SECRETO_PRUEBA = "secreto-de-prueba-que-no-vive-en-produccion"
ACTOR = "curacion:persona"


@pytest.fixture
def credencial(monkeypatch) -> str:
    """Una credencial firmada, con todos los roles.

    Las pruebas de administración van por el camino de producción —credencial
    por persona— y no por el token compartido, que desde P-017 solo se admite en
    modo desarrollo. Probar por la puerta que producción no usa dejaría sin
    cubrir la que sí.
    """
    import datetime as dt

    from backend_normativo.seguridad.credenciales import ROLES, emitir

    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", SECRETO_PRUEBA)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    monkeypatch.delenv("BN_ADMIN_TOKENS", raising=False)
    token, _ = emitir(
        ACTOR, set(ROLES), duracion=dt.timedelta(days=1), secreto_bytes=SECRETO_PRUEBA.encode()
    )
    return token


# --- Envoltura de respuesta -----------------------------------------------------


def test_toda_respuesta_lleva_la_envoltura_del_contrato(cliente_api, corpus) -> None:
    cuerpo = cliente_api.get("/v1/normas").json()
    for clave in (
        "schema_version",
        "release_id",
        "as_of",
        "known_at",
        "data_status",
        "data",
        "evidence",
        "missing_fields",
        "warnings",
    ):
        assert clave in cuerpo, clave
    assert cuerpo["schema_version"] == "1.0"


def test_sin_release_publicado_la_respuesta_lo_dice(cliente_api, corpus) -> None:
    """No hay silencio: la respuesta explica por qué no puede servir nada."""
    cuerpo = cliente_api.get("/v1/normas").json()
    assert cuerpo["release_id"] is None
    assert cuerpo["data_status"] == "NO_PUBLICABLE"
    assert any("release publicado" in w["detalle"] for w in cuerpo["warnings"])


def test_una_norma_inexistente_da_un_error_tipado(cliente_api, corpus) -> None:
    respuesta = cliente_api.get(f"/v1/normas/{uuid.uuid4()}")
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "UNKNOWN_IDENTITY"


def test_la_ficha_explica_por_que_una_version_no_se_sirve(cliente_api, corpus) -> None:
    """Una abstención explicada es información; una lista vacía no."""
    cuerpo = cliente_api.get(f"/v1/normas/{corpus.norma_id}").json()
    version = cuerpo["data"]["versiones"][0]
    assert version["servible"] is False
    assert version["motivos_no_servible"]
    assert any("INSUFFICIENT_EVIDENCE" in m for m in version["motivos_no_servible"])


def test_los_siete_campos_viajan_en_la_ficha(cliente_api, corpus) -> None:
    cuerpo = cliente_api.get(f"/v1/normas/{corpus.norma_id}").json()
    assert set(cuerpo["data"]["campos"]) == set(CAMPOS_SOLICITADOS)
    # Sin publicar, ningún campo tiene valores y todos figuran como faltantes.
    assert sorted(cuerpo["missing_fields"]) == sorted(CAMPOS_SOLICITADOS)


def test_un_candidato_en_revision_se_cuenta_pero_no_se_sirve_como_valor(
    cliente_api, corpus
) -> None:
    """Es lo que distingue "lo estamos mirando" de "esto dice la norma"."""
    campos = cliente_api.get(f"/v1/normas/{corpus.norma_id}").json()["data"]["campos"]
    con_candidatos = [c for c in campos.values() if c["candidatos_en_revision"]]
    assert con_candidatos
    assert all(c["valores"] == [] for c in con_candidatos)


# --- Con corpus publicado --------------------------------------------------------


def test_una_norma_publicada_se_sirve_y_trae_evidencia(cliente_api, corpus_publicado) -> None:
    cuerpo = cliente_api.get(f"/v1/normas/{corpus_publicado.norma_id}").json()
    assert cuerpo["release_id"] is not None
    assert cuerpo["data_status"] == "PUBLICADO"
    assert cuerpo["data"]["versiones"][0]["servible"] is True
    assert cuerpo["evidence"]
    assert all(e["fragmento"] for e in cuerpo["evidence"])


def test_la_ficha_se_abstiene_en_las_capacidades_que_no_sustenta(
    cliente_api, corpus_publicado
) -> None:
    """Una norma con plazos desconocidos no responde "hasta cuándo", aunque sí
    pueda explicar de qué se trata."""
    identificacion = cliente_api.get(
        f"/v1/normas/{corpus_publicado.norma_id}?capacidad=IDENTIFICACION"
    ).json()
    plazo = cliente_api.get(f"/v1/normas/{corpus_publicado.norma_id}?capacidad=PLAZO").json()

    assert identificacion["data"]["versiones"][0]["servible"] is True
    assert plazo["data"]["versiones"][0]["servible"] is False
    assert any("plazos" in m for m in plazo["data"]["versiones"][0]["motivos_no_servible"])


def test_una_fecha_anterior_a_la_vigencia_no_se_sirve_como_actual(
    cliente_api, corpus_publicado
) -> None:
    cuerpo = cliente_api.get(f"/v1/normas/{corpus_publicado.norma_id}?as_of=2020-01-01").json()
    assert cuerpo["as_of"] == "2020-01-01"
    assert cuerpo["data"]["versiones"][0]["servible"] is False
    assert any(
        "UNSUPPORTED_SCOPE" in m for m in cuerpo["data"]["versiones"][0]["motivos_no_servible"]
    )


def test_la_recuperacion_devuelve_citas_localizables(cliente_api, corpus_publicado) -> None:
    cuerpo = cliente_api.post(
        "/v1/recuperacion", json={"consulta": "vulnerabilidad habitacional"}
    ).json()
    assert cuerpo["data"]["fragmentos"]
    primero = cuerpo["data"]["fragmentos"][0]
    assert primero["norma"].startswith("LEY 6935")
    assert primero["unidad"]
    assert primero["url_fuente"].startswith("https://")
    assert "no combinando fragmentos" in cuerpo["data"]["aclaracion"]


def test_sin_release_la_recuperacion_no_toca_staging(cliente_api, corpus) -> None:
    """El lector conversacional accede solo a proyecciones publicadas."""
    cuerpo = cliente_api.post("/v1/recuperacion", json={"consulta": "beneficiarios"}).json()
    assert cuerpo["data"]["fragmentos"] == []
    assert cuerpo["data_status"] == "NO_PUBLICABLE"
    assert any("no se recupera de staging" in w["detalle"].lower() for w in cuerpo["warnings"])


def test_un_valor_de_otro_periodo_no_se_devuelve(cliente_api, corpus_publicado) -> None:
    """Servir el monto de otro período es dar una respuesta incorrecta que
    parece correcta."""
    cuerpo = cliente_api.get("/v1/valores?concepto=INEXISTENTE").json()
    assert cuerpo["data"] == []
    assert cuerpo["data_status"] == "SIN_RESULTADOS"
    assert cuerpo["missing_fields"] == ["INEXISTENTE"]
    assert any("otro período" in w["detalle"] for w in cuerpo["warnings"])


def test_el_listado_de_beneficios_no_infiere_elegibilidad(cliente_api, corpus_publicado) -> None:
    cuerpo = cliente_api.get("/v1/beneficios").json()
    assert any("no infiere elegibilidad" in w["detalle"] for w in cuerpo["warnings"])


def test_plazos_exige_decir_de_que_se_pregunta(cliente_api, corpus_publicado) -> None:
    respuesta = cliente_api.get("/v1/plazos")
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["codigo"] == "INVALID_REQUEST"


def test_cobertura_exige_credencial_de_auditoria(cliente_api, corpus_publicado) -> None:
    """La cobertura mide el estado operativo, no una proyección publicada.

    `medir()` lee `fuentes`, `capturas` e `incidencias_revision`. El lector de la
    API no tiene permiso sobre esas tablas —no debe tenerlo: la invariante es que
    el lector accede solo a proyecciones servibles— así que servir esto abierto
    daba 500 en cualquier despliegue con roles de verdad. Las pruebas no lo veían
    porque corren con un rol que puede leer todo; se vio al desplegar.
    """
    assert cliente_api.get("/v1/cobertura").status_code == 401


def test_cobertura_separa_evaluado_de_sustantivo(
    cliente_api, corpus_publicado, credencial: str
) -> None:
    cuerpo = cliente_api.get(
        "/v1/cobertura", headers={"Authorization": f"Bearer {credencial}"}
    ).json()
    campos = cuerpo["data"]["campos"]
    assert campos["porcentaje_evaluado"] == 100.0
    assert "con_valor_sustantivo" in campos
    assert any("no cuenta como completo" in w["detalle"] for w in cuerpo["warnings"])


# --- Evaluación preliminar --------------------------------------------------------


def test_un_beneficio_sin_reglas_publicadas_no_se_evalua_en_silencio(
    cliente_api, corpus_publicado, conexion: Connection
) -> None:
    beneficio_id = conexion.execute(
        text("INSERT INTO beneficios (codigo, nombre) VALUES ('B_API', 'Beneficio') RETURNING id")
    ).scalar_one()
    cuerpo = cliente_api.post(
        "/v1/evaluaciones-preliminares", json={"beneficio_id": str(beneficio_id), "hechos": {}}
    ).json()
    assert cuerpo["data"]["resultado"] == "REQUIERE_REVISION"
    assert any("no tiene reglas publicadas" in w["detalle"] for w in cuerpo["warnings"])


def test_la_evaluacion_aclara_que_no_es_una_decision(
    cliente_api, corpus_publicado, conexion: Connection
) -> None:
    beneficio_id = conexion.execute(
        text("INSERT INTO beneficios (codigo, nombre) VALUES ('B_API2', 'Beneficio') RETURNING id")
    ).scalar_one()
    cuerpo = cliente_api.post(
        "/v1/evaluaciones-preliminares", json={"beneficio_id": str(beneficio_id)}
    ).json()
    assert "no otorga, no rechaza y no revoca" in cuerpo["data"]["aclaracion"].lower()


def test_un_beneficio_inexistente_da_error_tipado(cliente_api, corpus_publicado) -> None:
    respuesta = cliente_api.post(
        "/v1/evaluaciones-preliminares", json={"beneficio_id": str(uuid.uuid4())}
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "UNKNOWN_IDENTITY"


# --- Administración ----------------------------------------------------------------


def test_sin_credencial_configurada_la_administracion_esta_cerrada(
    cliente_api, corpus, monkeypatch
) -> None:
    """Sin secreto de firma no hay credencial que se pueda verificar.

    Y sin credencial no se administra: no hay valor por omisión que abra las
    rutas, porque un secreto por omisión haría que una credencial emitida en
    cualquier máquina valiera acá.
    """
    monkeypatch.delenv("BN_ADMIN_TOKENS", raising=False)
    monkeypatch.delenv("BN_CREDENCIAL_SECRETO", raising=False)

    sin_cabecera = cliente_api.post("/v1/admin/releases", json={"motivo": "intento"})
    assert sin_cabecera.status_code == 401

    con_credencial = cliente_api.post(
        "/v1/admin/releases",
        json={"motivo": "intento"},
        headers={"Authorization": "Bearer bn1.cuerpo.firma"},
    )
    assert con_credencial.status_code == 403
    assert con_credencial.json()["detail"]["codigo"] == "NOT_AUTHORIZED"


def test_una_credencial_invalida_no_autoriza(cliente_api, corpus, monkeypatch) -> None:
    respuesta = cliente_api.post(
        "/v1/admin/releases",
        json={"motivo": "intento"},
        headers={"Authorization": "Bearer otra-cosa", "X-Actor": "alguien"},
    )
    assert respuesta.status_code == 403


def test_toda_operacion_de_administracion_declara_quien_la_hace(
    cliente_api, corpus, credencial
) -> None:
    """Lo que se decide queda en la bitácora con nombre.

    Antes el actor se pedía en una cabecera y faltaba si nadie la mandaba. Ahora
    no puede faltar porque no lo manda quien llama: sale de la credencial. Que
    esta operación falle por los controles de publicación y no por falta de
    actor es justamente la diferencia.
    """
    respuesta = cliente_api.post(
        "/v1/admin/releases",
        json={"motivo": "intento"},
        headers={"Authorization": f"Bearer {credencial}"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "INSUFFICIENT_EVIDENCE"


def test_publicar_sin_pasar_los_gates_no_es_un_error_del_servidor(
    cliente_api, corpus, credencial
) -> None:
    """Información insuficiente es un estado de dominio, no un 500."""
    respuesta = cliente_api.post(
        "/v1/admin/releases",
        json={"motivo": "intento prematuro"},
        headers={"Authorization": f"Bearer {credencial}", "X-Actor": "publicador:persona"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "INSUFFICIENT_EVIDENCE"


def test_resolver_una_incidencia_ya_resuelta_da_409(
    cliente_api, corpus, conexion: Connection, credencial
) -> None:
    ResolutorVigencia(conexion).resolver()
    incidencia = conexion.execute(
        text("SELECT id FROM incidencias_revision WHERE tipo = 'VIGENCIA_INDETERMINADA'")
    ).scalar_one()
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    cuerpo = {
        "decision": "Se aprueba como vigente desde su publicación.",
        "fundamento_evidencia_id": str(evidencia),
        "vigencia": {
            "valid_tipo": "ABIERTO_FIN",
            "valid_desde": "2025-12-23",
            "estado_legal": "VIGENTE",
        },
    }
    cabeceras = {"Authorization": f"Bearer {credencial}", "X-Actor": "curacion:persona"}

    primera = cliente_api.post(
        f"/v1/admin/revisiones/{incidencia}/resolver", json=cuerpo, headers=cabeceras
    )
    assert primera.status_code == 200
    assert primera.json()["decidido_por"] == "curacion:persona"

    segunda = cliente_api.post(
        f"/v1/admin/revisiones/{incidencia}/resolver", json=cuerpo, headers=cabeceras
    )
    assert segunda.status_code == 409
    assert segunda.json()["detail"]["codigo"] == "VERSION_CONFLICT"


def test_afirmar_una_vigencia_sin_evidencia_se_rechaza(
    cliente_api, corpus, conexion: Connection, credencial
) -> None:
    ResolutorVigencia(conexion).resolver()
    incidencia = conexion.execute(
        text("SELECT id FROM incidencias_revision WHERE tipo = 'VIGENCIA_INDETERMINADA'")
    ).scalar_one()
    respuesta = cliente_api.post(
        f"/v1/admin/revisiones/{incidencia}/resolver",
        json={
            "decision": "Se aprueba.",
            "vigencia": {"valid_tipo": "ABIERTO_FIN", "estado_legal": "VIGENTE"},
        },
        headers={"Authorization": f"Bearer {credencial}", "X-Actor": "curacion:persona"},
    )
    assert respuesta.status_code == 400
    assert "evidencia" in respuesta.json()["detail"]["detalle"]


def test_el_cuerpo_de_una_evaluacion_no_se_persiste(
    cliente_api, corpus_publicado, conexion: Connection
) -> None:
    """Los hechos que declara una persona no forman parte del corpus."""
    beneficio_id = conexion.execute(
        text("INSERT INTO beneficios (codigo, nombre) VALUES ('B_PII', 'Beneficio') RETURNING id")
    ).scalar_one()
    cliente_api.post(
        "/v1/evaluaciones-preliminares",
        json={
            "beneficio_id": str(beneficio_id),
            "hechos": {"edad": 34, "ingreso_hogar_mensual_bruto": "250000"},
        },
    )
    almacenado = conexion.execute(text("SELECT count(*) FROM consultas_auditadas")).scalar_one()
    assert almacenado == 0


# --- P-009: el circuito de revisión de reglas ----------------------------------


def _una_regla(conexion: Connection) -> str:
    return str(
        conexion.execute(
            text("SELECT id FROM reglas WHERE estado_revision = 'CANDIDATE' LIMIT 1")
        ).scalar_one()
    )


def test_el_expediente_de_una_regla_trae_todo_junto(
    cliente_api, regla_candidata, conexion: Connection, credencial
) -> None:
    """Una condición se aprueba o no según de qué depende y sobre qué versión
    rige. Pedirle a quien revisa que cruce seis pantallas es pedirle que no las
    cruce."""
    regla = regla_candidata

    respuesta = cliente_api.get(
        f"/v1/admin/reglas/{regla}",
        headers={"Authorization": f"Bearer {credencial}", "X-Actor": "curacion:persona"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in (
        "texto_literal",
        "interpretacion",
        "condicion",
        "dependencias",
        "parametros",
        "vigencia",
        "controles",
        "norma",
        "ruta",
    ):
        assert clave in cuerpo, f"el expediente no trae {clave}"
    assert cuerpo["estado"] == "CANDIDATE"


def test_decidir_una_regla_exige_fundamento(
    cliente_api, regla_candidata, conexion: Connection, credencial
) -> None:
    """El actor ya no puede faltar —sale de la credencial—; el fundamento sí.

    Aprobar una regla sin decir por qué deja en la bitácora una firma sin
    razones, que para una decisión jurídica es casi lo mismo que no tenerla.
    """
    regla = regla_candidata

    sin_fundamento = cliente_api.post(
        f"/v1/admin/reglas/{regla}/decidir",
        json={"decision": "APROBAR", "fundamento": "   "},
        headers={"Authorization": f"Bearer {credencial}"},
    )
    assert sin_fundamento.status_code == 400

    # Y el actor que queda registrado es el de la credencial, no uno que la
    # cabecera pueda proponer.
    aprobada = cliente_api.post(
        f"/v1/admin/reglas/{regla}/decidir",
        json={"decision": "APROBAR", "fundamento": "Se corresponde con el artículo citado."},
        headers={"Authorization": f"Bearer {credencial}", "X-Actor": "otro_cualquiera"},
    )
    assert aprobada.status_code == 200
    assert aprobada.json()["decidido_por"] == ACTOR


def test_aprobar_una_regla_no_la_publica(
    cliente_api, regla_candidata, conexion: Connection, credencial
) -> None:
    """Aprobar y publicar son dos decisiones distintas y las toma gente distinta."""
    regla = regla_candidata

    respuesta = cliente_api.post(
        f"/v1/admin/reglas/{regla}/decidir",
        json={
            "decision": "APROBAR",
            "fundamento": "El literal del artículo 6 sostiene la condición tal como está escrita.",
            "estado_esperado": "CANDIDATE",
        },
        headers={"Authorization": f"Bearer {credencial}", "X-Actor": "curacion:persona"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "APPROVED"
    assert respuesta.json()["publicada"] is False
    assert respuesta.json()["decidido_por"] == "curacion:persona"
    # Y queda en la bitácora, con nombre.
    quien = conexion.execute(
        text(
            "SELECT actor, motivo FROM auditoria_eventos "
            " WHERE accion = 'APROBAR_REGLA' AND objeto_id = :id"
        ),
        {"id": regla},
    ).one()
    assert quien.actor == "curacion:persona"
    assert "artículo 6" in quien.motivo


def test_la_segunda_decision_sobre_una_version_vieja_da_409(
    cliente_api, regla_candidata, conexion: Connection, credencial
) -> None:
    """Dos personas abren la misma regla. La primera decide. La segunda todavía
    mira la pantalla vieja: su decisión no puede pisar a la otra."""
    regla = regla_candidata
    cabeceras = {"Authorization": f"Bearer {credencial}", "X-Actor": "curacion:persona"}

    primera = cliente_api.post(
        f"/v1/admin/reglas/{regla}/decidir",
        json={
            "decision": "APROBAR",
            "fundamento": "El literal sostiene la condición.",
            "estado_esperado": "CANDIDATE",
        },
        headers=cabeceras,
    )
    assert primera.status_code == 200

    segunda = cliente_api.post(
        f"/v1/admin/reglas/{regla}/decidir",
        json={
            "decision": "RECHAZAR",
            "fundamento": "Me parece que el artículo no dice eso.",
            "estado_esperado": "CANDIDATE",
        },
        headers={**cabeceras, "X-Actor": "curacion:otra-persona"},
    )

    assert segunda.status_code == 409
    assert segunda.json()["detail"]["codigo"] == "VERSION_CONFLICT"
    # Y la decisión de la primera sigue en pie.
    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla}
    ).scalar_one()
    assert estado == "APPROVED"


def test_una_decision_desconocida_se_rechaza(
    cliente_api, regla_candidata, conexion: Connection, credencial
) -> None:
    regla = regla_candidata

    respuesta = cliente_api.post(
        f"/v1/admin/reglas/{regla}/decidir",
        json={"decision": "PUBLICAR", "fundamento": "Quiero servirla ya."},
        headers={"Authorization": f"Bearer {credencial}", "X-Actor": "curacion:persona"},
    )

    assert respuesta.status_code == 400
    assert "PUBLICAR" in respuesta.json()["detail"]["detalle"]
