"""Las unidades extraídas antes de `extraccion@15` se quedaron con el marcado.

DQ10 no deja publicar un corte que lo arrastre, y hace bien: son etiquetas que
llegarían a la pantalla de alguien. La limpieza aplica exactamente la misma
función que el extractor, así que el texto queda igual que si el documento se
volviera a extraer, y sólo toca lo que todavía no se publicó.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion.marcado import limpiar

pytestmark = pytest.mark.integracion

CON_MARCADO = "<p>Art. 2°.- Beneficiarios - Son las personas alcanzadas.</p>"
LIMPIO = "Art. 2°.- Beneficiarios - Son las personas alcanzadas."


def _unidad_con_marcado(conexion: Connection, corpus) -> str:
    """Ensucia una unidad del corpus, como quedaron las extraídas con @3 y @4."""
    unidad = conexion.execute(
        text(
            "SELECT u.id FROM unidades_documentales u "
            "  JOIN norma_versiones nv ON nv.doc_version_id = u.doc_version_id "
            " WHERE nv.registro_version_id = :v LIMIT 1"
        ),
        {"v": corpus.registro_version_id},
    ).scalar_one()
    conexion.execute(
        text("UPDATE unidades_documentales SET texto = :t WHERE id = :id"),
        {"t": CON_MARCADO, "id": unidad},
    )
    return str(unidad)


def _texto(conexion: Connection, unidad: str) -> str:
    return conexion.execute(
        text("SELECT texto FROM unidades_documentales WHERE id = :id"), {"id": unidad}
    ).scalar_one()


def test_saca_el_marcado_y_deja_el_texto(conexion: Connection, corpus) -> None:
    unidad = _unidad_con_marcado(conexion, corpus)
    resultado = limpiar(conexion, actor="curacion", fundamento="Marcado de la fuente.")
    assert resultado.limpiadas >= 1
    assert _texto(conexion, unidad) == LIMPIO


def test_no_toca_el_texto_de_un_corte_publicado(conexion: Connection, corpus_publicado) -> None:
    """D-124: el texto que un corte publicado sirve no se cambia."""
    unidad = conexion.execute(
        text(
            "SELECT u.id FROM unidades_documentales u "
            "  JOIN norma_versiones nv ON nv.doc_version_id = u.doc_version_id "
            "  JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
            " WHERE rv.estado_revision = 'PUBLISHED' LIMIT 1"
        )
    ).scalar_one()
    conexion.execute(
        text("UPDATE unidades_documentales SET texto = :t WHERE id = :id"),
        {"t": CON_MARCADO, "id": unidad},
    )
    limpiar(conexion, actor="curacion", fundamento="Marcado de la fuente.")
    assert _texto(conexion, str(unidad)) == CON_MARCADO, (
        "se cambió el texto de una unidad que un corte publicado está sirviendo"
    )


def test_deja_un_evento_por_unidad(conexion: Connection, corpus) -> None:
    unidad = _unidad_con_marcado(conexion, corpus)
    limpiar(conexion, actor="curacion:agente", fundamento="Marcado escapado en la fuente.")
    evento = (
        conexion.execute(
            text(
                "SELECT actor, motivo FROM auditoria_eventos "
                " WHERE accion = 'LIMPIAR_MARCADO' AND objeto_id = :id"
            ),
            {"id": unidad},
        )
        .mappings()
        .one()
    )
    assert evento["actor"] == "curacion:agente"
    assert "Marcado escapado" in evento["motivo"]


def test_simular_no_escribe(conexion: Connection, corpus) -> None:
    unidad = _unidad_con_marcado(conexion, corpus)
    resultado = limpiar(
        conexion, actor="curacion", fundamento="Marcado de la fuente.", simular=True
    )
    assert resultado.limpiadas >= 1
    assert resultado.simulada
    assert _texto(conexion, unidad) == CON_MARCADO


def test_sin_fundamento_no_se_acepta(conexion: Connection, corpus) -> None:
    """Es texto de una norma: cambiarlo tiene que poder explicarse."""
    _unidad_con_marcado(conexion, corpus)
    with pytest.raises(ValueError):
        limpiar(conexion, actor="curacion", fundamento="  ")


def test_la_limpieza_deja_pasar_el_gate(conexion: Connection, corpus) -> None:
    """Es para lo que existe: DQ10 en verde sin tocar lo publicado."""
    from backend_normativo.publicacion.gates import evaluar_gates

    _unidad_con_marcado(conexion, corpus)
    candidatos = [corpus.registro_version_id]
    antes = {g.id: g for g in evaluar_gates(conexion, candidatos).gates if g.id == "DQ10"}
    assert any(not g.pasa for g in antes.values()), "el gate tenía que estar en rojo"

    limpiar(conexion, actor="curacion", fundamento="Marcado de la fuente.")
    despues = [
        g
        for g in evaluar_gates(conexion, candidatos).gates
        if g.id == "DQ10" and "marcado" in g.descripcion
    ]
    assert despues and all(g.pasa for g in despues)
