"""Aprobar una regla con árbol validado es lo que la vuelve ejecutable.

Estaban separadas y no debían estarlo. El motor decide con
`ast is not None and not requiere_revision`, y ninguna transición bajaba esa
marca: se podían aprobar las 166 reglas del expediente y el evaluador seguía
contestando DESCONOCIDO en todas, con el motivo «la regla está marcada como
pendiente de revisión». Aprobada y pendiente de revisión a la vez.

Ninguna prueba lo veía porque cada mitad estaba bien por su cuenta. Es la
brecha que el plan v1.1 nombra en §02: «hacer coherente aprobar con la marca de
revisión».
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion import revision_reglas

pytestmark = pytest.mark.integracion

AST = {"tipo": "comparacion", "operador": ">=", "campo": "edad", "valor": 18}


def _regla(conexion: Connection, *, con_ast: bool, estado: str = "CANDIDATE") -> uuid.UUID:
    """Una regla mínima colgada de un beneficio, con o sin condición ejecutable."""
    import json

    from backend_normativo.catalogo.carga import cargar_catalogo

    if not conexion.execute(text("SELECT count(*) FROM jurisdicciones")).scalar_one():
        cargar_catalogo(conexion)
    sufijo = uuid.uuid4().hex[:8].upper()
    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'AUTORIDAD_APLICACION') RETURNING id"
        ),
        {"n": f"Organismo {sufijo}"},
    ).scalar_one()
    beneficio = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre, linea) "
            "VALUES (:c, 'Beneficio de prueba', 'PRUEBA') RETURNING id"
        ),
        {"c": f"PRUEBA.{sufijo}"},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            "  estado_revision, valid_tipo, valid_desde) "
            "VALUES ('beneficio', :b, 1, 'CANDIDATE', 'ABIERTO_FIN', DATE '2025-01-01') "
            "RETURNING id"
        ),
        {"b": beneficio},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            "  jurisdiccion_id, autoridad_id, naturaleza, descripcion) "
            "VALUES (:v, :b, 'AR-C', :o, 'PRESTACION_MONETARIA', 'Prueba')"
        ),
        {"v": version, "b": beneficio, "o": organismo},
    )
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one_or_none()
    if evidencia is None:
        pytest.skip("el corpus de prueba no tiene evidencias para colgar una regla")
    return conexion.execute(
        text(
            "INSERT INTO reglas (beneficio_version_id, evidencia_id, categoria, texto_literal, "
            "  ast, ast_schema_version, requiere_revision, estado_revision) "
            "VALUES (:v, :e, 'APLICABILIDAD', 'Texto literal de prueba', "
            "        CAST(:ast AS jsonb), :sv, true, :estado) RETURNING id"
        ),
        {
            "v": version,
            "e": evidencia,
            "ast": json.dumps(AST) if con_ast else None,
            "sv": "1.0" if con_ast else None,
            "estado": estado,
        },
    ).scalar_one()


def _fila(conexion: Connection, regla_id: uuid.UUID):
    return (
        conexion.execute(
            text("SELECT estado_revision, requiere_revision FROM reglas WHERE id = :id"),
            {"id": regla_id},
        )
        .mappings()
        .one()
    )


def test_aprobar_una_regla_con_arbol_la_vuelve_ejecutable(conexion: Connection, corpus) -> None:
    regla = _regla(conexion, con_ast=True)
    revision_reglas.aprobar(
        conexion, regla, actor="Pedro Pistoni", fundamento="Revisada contra el texto."
    )
    fila = _fila(conexion, regla)
    assert fila["estado_revision"] == "APPROVED"
    assert fila["requiere_revision"] is False, (
        "una regla aprobada con árbol validado sigue marcada como pendiente de revisión: "
        "el motor la va a contestar DESCONOCIDO"
    )


def test_una_regla_sin_arbol_queda_aprobada_y_no_ejecutable(conexion: Connection, corpus) -> None:
    """Sin condición ejecutable no hay nada que ejecutar, y la base lo exige."""
    regla = _regla(conexion, con_ast=False)
    revision_reglas.aprobar(conexion, regla, actor="Pedro Pistoni", fundamento="Es informativa.")
    fila = _fila(conexion, regla)
    assert fila["estado_revision"] == "APPROVED"
    assert fila["requiere_revision"] is True


def test_habilitar_conecta_lo_ya_aprobado_y_deja_afuera_lo_que_no_tiene_condicion(
    conexion: Connection, corpus
) -> None:
    """Las 166 del expediente se aprobaron antes del arreglo y quedaron colgadas."""
    con_ast = _regla(conexion, con_ast=True, estado="APPROVED")
    sin_ast = _regla(conexion, con_ast=False, estado="APPROVED")

    resultado = revision_reglas.habilitar_aprobadas(
        conexion,
        actor="Pedro Pistoni",
        fundamento="Decisión de producto: se procede sin firma jurídica.",
    )
    assert resultado.habilitadas >= 1
    assert resultado.sin_condicion >= 1
    assert _fila(conexion, con_ast)["requiere_revision"] is False
    assert _fila(conexion, sin_ast)["requiere_revision"] is True


def test_habilitar_deja_un_evento_por_regla_con_su_fundamento(conexion: Connection, corpus) -> None:
    """Lo que se hace de una vez tiene que poder auditarse una por una."""
    regla = _regla(conexion, con_ast=True, estado="APPROVED")
    revision_reglas.habilitar_aprobadas(
        conexion, actor="Pedro Pistoni", fundamento="Decisión de producto del 12/09."
    )
    evento = (
        conexion.execute(
            text(
                "SELECT actor, accion, motivo FROM auditoria_eventos "
                " WHERE objeto = 'reglas' AND objeto_id = :id AND accion = 'HABILITAR_REGLA'"
            ),
            {"id": str(regla)},
        )
        .mappings()
        .one()
    )
    assert evento["actor"] == "Pedro Pistoni"
    assert "Decisión de producto" in evento["motivo"]


def test_habilitar_sin_fundamento_no_se_acepta(conexion: Connection, corpus) -> None:
    """Es la decisión que hay que poder reconstruir dentro de seis meses."""
    _regla(conexion, con_ast=True, estado="APPROVED")
    with pytest.raises(revision_reglas.RevisionInvalida):
        revision_reglas.habilitar_aprobadas(conexion, actor="Pedro Pistoni", fundamento="   ")


def test_habilitar_dos_veces_no_cuenta_dos_veces(conexion: Connection, corpus) -> None:
    _regla(conexion, con_ast=True, estado="APPROVED")
    primera = revision_reglas.habilitar_aprobadas(
        conexion, actor="Pedro Pistoni", fundamento="Decisión de producto."
    )
    segunda = revision_reglas.habilitar_aprobadas(
        conexion, actor="Pedro Pistoni", fundamento="Decisión de producto."
    )
    assert primera.habilitadas >= 1
    assert segunda.habilitadas == 0
    assert segunda.ya_estaban >= primera.habilitadas
