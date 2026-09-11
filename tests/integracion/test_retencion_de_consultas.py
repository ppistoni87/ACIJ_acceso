"""La traza de consultas caduca, y el lector no la puede borrar (P-017, criterio 2).

Lo que se guarda de una consulta no tiene identidad —ni texto, ni dirección, ni
quién— y aun así se borra: «no identifica a nadie» es una afirmación sobre hoy,
y un conjunto grande de formas de consulta con sus horarios y sus jurisdicciones
se vuelve más identificante cuanto más largo es.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.api.observabilidad import (
    RETENCION_DIAS_DEFECTO,
    VARIABLE_RETENCION,
    Anotacion,
    purgar,
    registrar,
    retencion_configurada,
)

pytestmark = pytest.mark.integracion


def _consulta_de(conexion: Connection, *, hace_dias: int, rid: str) -> None:
    registrar(
        conexion, Anotacion(request_id=rid, ruta="/v1/normas", resultado="RESUELTA", latencia_ms=5)
    )
    conexion.execute(
        text(
            "UPDATE consultas_auditadas SET ocurrido_en = now() - make_interval(days => :d) "
            " WHERE request_id = :r"
        ),
        {"d": hace_dias, "r": rid},
    )


def test_lo_viejo_se_borra_y_lo_reciente_queda(conexion: Connection) -> None:
    _consulta_de(conexion, hace_dias=200, rid="vieja")
    _consulta_de(conexion, hace_dias=1, rid="reciente")
    resultado = purgar(conexion, dias=90)
    assert resultado.borradas >= 1
    quedan = {
        fila[0]
        for fila in conexion.execute(
            text(
                "SELECT request_id FROM consultas_auditadas WHERE request_id IN ('vieja', "
                "'reciente')"
            )
        ).all()
    }
    assert quedan == {"reciente"}


def test_simular_no_borra_nada_y_dice_cuanto_borraria(conexion: Connection) -> None:
    _consulta_de(conexion, hace_dias=200, rid="vieja-simulada")
    resultado = purgar(conexion, dias=90, simular=True)
    assert resultado.simulada
    assert resultado.candidatas >= 1
    assert resultado.borradas == 0
    assert (
        conexion.execute(
            text("SELECT count(*) FROM consultas_auditadas WHERE request_id = 'vieja-simulada'")
        ).scalar_one()
        == 1
    )


def test_una_retencion_mal_escrita_no_borra_todo(monkeypatch) -> None:
    """Cero sería «borrar siempre». No se llega ahí por una variable mal puesta."""
    for valor in ("0", "-5", "no-es-un-numero", ""):
        monkeypatch.setenv(VARIABLE_RETENCION, valor)
        assert retencion_configurada() >= 1
    monkeypatch.delenv(VARIABLE_RETENCION, raising=False)
    assert retencion_configurada() == RETENCION_DIAS_DEFECTO


def test_el_lector_de_la_api_no_puede_borrar_la_traza(conexion: Connection) -> None:
    """Puede insertar la suya y no borrar la de nadie: por eso el registro sirve."""
    conexion.execute(text("SET ROLE bn_lector_api"))
    try:
        conexion.execute(
            text("EXPLAIN INSERT INTO consultas_auditadas (id) VALUES (gen_random_uuid())")
        )
        with pytest.raises(Exception, match=r"(?i)permission|permiso"):
            conexion.execute(text("EXPLAIN DELETE FROM consultas_auditadas"))
    finally:
        conexion.execute(text("ROLLBACK"))
        conexion.execute(text("RESET ROLE"))
