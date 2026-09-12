"""La consulta que además orienta: reglas, hechos confirmados y una pregunta.

Hasta acá `/v1/respuestas` devolvía evidencia. Con una conversación abierta
devuelve además cómo va el caso contra las condiciones publicadas, y cuando le
falta un dato **para de contestar y lo pregunta**. Lo que se prueba acá es la
parte que puede mentirle a alguien: que no oriente sin conversación, que no
elija por la persona cuando hay varios programas, que la pregunta no muestre el
nombre de un campo, y que corregir un dato cambie la orientación.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from tests.conftest import version_publicada

pytestmark = pytest.mark.integracion

APLICABILIDAD = "Son beneficiarios las personas en situación de vulnerabilidad habitacional."
DOS_COSAS = "Acreditar la identidad de la persona titular y la del grupo conviviente."


def _beneficio_publicado(conexion: Connection, corpus) -> str:
    """Un beneficio publicado, colgado de la norma del corpus, con dos reglas.

    Una que se puede preguntar —nombra un solo dato— y otra que no, porque pide
    dos cosas en la misma oración. Las dos hacen falta: la segunda es la que
    prueba que el sistema prefiere callarse antes que preguntar mal.
    """
    sufijo = uuid.uuid4().hex[:8].upper()
    beneficio = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre, linea, familia) "
            "VALUES (:c, 'Apoyo habitacional de prueba', 'SUBSIDIO', 'HABITACIONAL') "
            "RETURNING id"
        ),
        {"c": f"AR.ORIENTACION-{sufijo}"},
    ).scalar_one()
    version = version_publicada(conexion, entidad_tipo="beneficio", entidad_id=beneficio)
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            " jurisdiccion_id, naturaleza, descripcion) "
            "VALUES (:rv, :b, 'AR-C', 'PRESTACION_MONETARIA', 'Prestación de prueba.')"
        ),
        {"rv": version, "b": beneficio},
    )
    # Lo que ata el beneficio a los textos que la búsqueda va a recuperar: sin
    # esto los fragmentos no cuelgan de ningún programa y no hay qué evaluar.
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_normas (beneficio_version_id, norma_version_id, rol, "
            " evidencia_id) VALUES (:bv, :nv, 'CREA', :e)"
        ),
        {"bv": version, "nv": corpus.registro_version_id, "e": evidencia},
    )
    for categoria, literal, ast in (
        (
            "APLICABILIDAD",
            APLICABILIDAD,
            {"op": "is_true", "field": "vulnerabilidad_habitacional", "schema_version": "1.0"},
        ),
        (
            "APLICABILIDAD",
            DOS_COSAS,
            {
                "op": "all",
                "schema_version": "1.0",
                "args": [
                    {"op": "is_true", "field": "identidad_titular", "schema_version": "1.0"},
                    {"op": "is_true", "field": "identidad_grupo", "schema_version": "1.0"},
                ],
            },
        ),
    ):
        conexion.execute(
            text(
                "INSERT INTO reglas (beneficio_version_id, evidencia_id, categoria, "
                " texto_literal, descripcion, ast, ast_schema_version, requiere_revision, "
                " estado_revision) "
                "VALUES (:bv, :e, :c, :l, 'Regla de prueba.', CAST(:a AS jsonb), '1.0', false, "
                " 'APPROVED')"
            ),
            {
                "bv": version,
                "e": evidencia,
                "c": categoria,
                "l": literal,
                "a": __import__("json").dumps(ast),
            },
        )
    return beneficio


def _consultar(cliente_api, texto: str, sesion_id: str | None = None) -> dict:
    cuerpo = {"consulta": texto, "limite": 5}
    if sesion_id:
        cuerpo["sesion_id"] = sesion_id
    respuesta = cliente_api.post("/v1/respuestas", json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_sin_conversacion_abierta_no_hay_orientacion(cliente_api, corpus_publicado) -> None:
    """Y no es una limitación: es que no habría dónde guardar lo que conteste.

    Preguntarle algo a alguien sin poder recibir la respuesta es hacerle perder
    el tiempo, y evaluar sin ningún hecho es devolver una lista de desconocidos
    disfrazada de orientación.
    """
    cuerpo = _consultar(cliente_api, "vulnerabilidad habitacional")
    assert cuerpo["orientacion"] is None
    assert cuerpo["sesion_vencida"] is False
    # La respuesta con evidencia sigue estando: no se degrada por no orientar.
    assert cuerpo["modo"] in {"EXTRACTO", "GENERADA", "ABSTENCION"}


def test_con_conversacion_orienta_y_pregunta_con_las_palabras_de_la_norma(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    _beneficio_publicado(conexion, corpus_publicado)
    sesion = cliente_api.post("/v1/sesiones").json()

    cuerpo = _consultar(cliente_api, "vulnerabilidad habitacional", sesion["sesion_id"])
    orientacion = cuerpo["orientacion"]

    assert orientacion is not None
    assert orientacion["beneficio"] == "Apoyo habitacional de prueba"
    pregunta = orientacion["pregunta"]
    assert pregunta is not None
    assert pregunta["texto_literal"] == APLICABILIDAD
    assert pregunta["forma"] == "si_no"
    # La aclaración no promete: dice que no decide.
    assert "no decide" in orientacion["aclaracion"].lower()


def test_lo_que_no_se_puede_preguntar_se_declara_en_vez_de_callarse(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """La regla que pide dos cosas en una oración queda contada, no preguntada."""
    _beneficio_publicado(conexion, corpus_publicado)
    sesion = cliente_api.post("/v1/sesiones").json()

    orientacion = _consultar(cliente_api, "vulnerabilidad habitacional", sesion["sesion_id"])[
        "orientacion"
    ]

    assert orientacion["sin_preguntar"] == 2, (
        "los dos datos de la regla que pide dos cosas juntas tienen que contarse: "
        "callarlos deja a la persona creyendo que contestó todo"
    )


def test_el_hecho_confirmado_cambia_la_orientacion_y_no_se_vuelve_a_preguntar(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    _beneficio_publicado(conexion, corpus_publicado)
    sesion = cliente_api.post("/v1/sesiones").json()
    sid = sesion["sesion_id"]

    primera = _consultar(cliente_api, "vulnerabilidad habitacional", sid)["orientacion"]
    campo = primera["pregunta"]["campo"]
    assert not primera["condiciones_cumplidas"]

    guardado = cliente_api.put(
        f"/v1/sesiones/{sid}/hechos",
        json={"clave": campo, "valor": True, "texto": APLICABILIDAD},
    )
    assert guardado.status_code == 200
    assert guardado.json()["version"] == 1

    segunda = _consultar(cliente_api, "vulnerabilidad habitacional", sid)["orientacion"]
    assert [c["texto_literal"] for c in segunda["condiciones_cumplidas"]] == [APLICABILIDAD]
    assert segunda["pregunta"] is None, "ya lo contestó: preguntarlo otra vez sería insistir"
    assert segunda["version_estado"] == 1


def test_corregir_un_hecho_sube_la_version_y_da_vuelta_la_orientacion(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """La versión es lo que le permite a la pantalla marcar como reemplazada la
    respuesta que se calculó con el dato viejo, en vez de dejar dos
    conclusiones distintas conviviendo."""
    _beneficio_publicado(conexion, corpus_publicado)
    sid = cliente_api.post("/v1/sesiones").json()["sesion_id"]
    campo = _consultar(cliente_api, "vulnerabilidad habitacional", sid)["orientacion"]["pregunta"][
        "campo"
    ]

    cliente_api.put(f"/v1/sesiones/{sid}/hechos", json={"clave": campo, "valor": True})
    cliente_api.put(f"/v1/sesiones/{sid}/hechos", json={"clave": campo, "valor": False})

    orientacion = _consultar(cliente_api, "vulnerabilidad habitacional", sid)["orientacion"]
    assert orientacion["version_estado"] == 2
    assert [c["texto_literal"] for c in orientacion["condiciones_no_cumplidas"]] == [APLICABILIDAD]
    # Y sin embargo el resultado **no** es la negativa firme, porque queda otra
    # condición sin saber. El motor pone lo desconocido por encima de lo
    # negativo a propósito: decirle «no» a alguien es lo más dañino que este
    # sistema puede hacer, y no lo dice mientras le falte algo por saber.
    assert orientacion["resultado"] == "REQUIERE_DATOS"


def test_rehusar_deja_la_condicion_desconocida_y_no_la_vuelve_a_preguntar(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """No contestar no es contestar que no. La diferencia decide un derecho."""
    _beneficio_publicado(conexion, corpus_publicado)
    sid = cliente_api.post("/v1/sesiones").json()["sesion_id"]
    campo = _consultar(cliente_api, "vulnerabilidad habitacional", sid)["orientacion"]["pregunta"][
        "campo"
    ]

    cliente_api.put(f"/v1/sesiones/{sid}/hechos", json={"clave": campo, "rehusado": True})

    orientacion = _consultar(cliente_api, "vulnerabilidad habitacional", sid)["orientacion"]
    assert orientacion["pregunta"] is None
    assert APLICABILIDAD in [c["texto_literal"] for c in orientacion["condiciones_desconocidas"]]
    assert orientacion["resultado"] != "NO_CUMPLE_REGLA_EXPLICITA", (
        "rehusar no puede leerse como una negativa"
    )


def test_una_sesion_que_vencio_se_dice_y_no_se_resucita(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    sid = cliente_api.post("/v1/sesiones").json()["sesion_id"]
    conexion.execute(
        text("DELETE FROM sesiones_conversacion WHERE id = CAST(:s AS uuid)"), {"s": sid}
    )

    cuerpo = _consultar(cliente_api, "vulnerabilidad habitacional", sid)
    assert cuerpo["sesion_vencida"] is True
    assert cuerpo["orientacion"] is None
    # Y la consulta se contesta igual: perder la conversación no puede dejar a
    # alguien sin la evidencia que pidió.
    assert cuerpo["modo"] in {"EXTRACTO", "GENERADA", "ABSTENCION"}


def test_deshacer_la_eleccion_de_programa_deja_de_acotar_de_verdad(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """Sacarlo de la pantalla no alcanza: tiene que dejar de actuar.

    `PATCH .../contexto` con `null` significa «no lo toques», así que la
    pantalla podía dejar de mostrar el programa elegido mientras el servidor
    seguía acotando cada consulta a ese programa. Un supuesto que sigue
    actuando después de que la persona lo quitó es peor que uno que nunca se
    mostró, y por eso deshacerlo tiene ruta propia.
    """
    _beneficio_publicado(conexion, corpus_publicado)
    sid = cliente_api.post("/v1/sesiones").json()["sesion_id"]

    puesto = cliente_api.patch(f"/v1/sesiones/{sid}/contexto", json={"intencion": "AR.LO-QUE-SEA"})
    assert puesto.json()["intencion"] == "AR.LO-QUE-SEA"

    # Mandar `null` no lo saca: es lo que hace falta poder decir de otra forma.
    nulo = cliente_api.patch(f"/v1/sesiones/{sid}/contexto", json={"intencion": None})
    assert nulo.json()["intencion"] == "AR.LO-QUE-SEA"

    sacado = cliente_api.delete(f"/v1/sesiones/{sid}/contexto/intencion")
    assert sacado.status_code == 200
    assert sacado.json()["intencion"] is None


def test_no_se_puede_inventar_un_campo_de_contexto(cliente_api, corpus_publicado) -> None:
    """La conversación tiene tres cosas en cuenta y ninguna más."""
    sid = cliente_api.post("/v1/sesiones").json()["sesion_id"]
    respuesta = cliente_api.delete(f"/v1/sesiones/{sid}/contexto/lo_que_sea")
    assert respuesta.status_code == 422
