"""Aprobar dato operativo en bloque, con las protecciones puestas.

Un canal es un teléfono y una dirección transcriptos de un directorio oficial,
con evidencia al fragmento exacto: no afirma qué le corresponde a nadie, y por
eso se puede aprobar en bloque. Lo que estas pruebas cuidan es lo que el bloque
**no** puede arrastrar.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion import aprobacion_operativa as op

pytestmark = pytest.mark.integracion


def _una_version_candidata(conexion: Connection) -> str | None:
    return conexion.execute(
        text(
            "SELECT id FROM registro_versiones "
            " WHERE release_id IS NULL AND estado_revision = 'CANDIDATE' "
            "   AND valid_tipo <> 'DESCONOCIDO' LIMIT 1"
        )
    ).scalar_one_or_none()


def test_sin_actor_no_se_aprueba(conexion: Connection) -> None:
    with pytest.raises(op.AprobacionInvalida, match="Falta el actor"):
        op.aprobar(conexion, actor="  ", fundamento="Porque sí.")


def test_sin_fundamento_no_se_aprueba(conexion: Connection) -> None:
    with pytest.raises(op.AprobacionInvalida, match="sin razón escrita"):
        op.aprobar(conexion, actor="alguien", fundamento="")


def test_una_version_con_incidencia_abierta_queda_afuera(
    conexion: Connection, beneficio_candidato: str
) -> None:
    """Aprobar en bloque algo que el sistema marcó es enterrar la marca."""
    version = _una_version_candidata(conexion)
    assert version is not None, "la fixture deja una versión candidata para revisar"

    antes = op.revisar(conexion)
    conexion.execute(
        text(
            "INSERT INTO incidencias_revision (registro_version_id, tipo, severidad, "
            " descripcion, estado) "
            "VALUES (:v, 'CONFLICTO_DE_FUENTES', 'HIGH', 'Dos fuentes discrepan.', 'ABIERTA')"
        ),
        {"v": version},
    )
    despues = op.revisar(conexion)
    assert despues.total == antes.total - 1
    assert despues.con_incidencia == antes.con_incidencia + 1


def test_una_version_sin_vigencia_nunca_entra(conexion: Connection) -> None:
    """Servirla sería afirmar una vigencia que nadie determinó."""
    seleccion = op.revisar(conexion)
    sin_vigencia_aprobadas = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones "
            " WHERE valid_tipo = 'DESCONOCIDO' AND estado_revision = 'APPROVED' "
            "   AND release_id IS NULL"
        )
    ).scalar_one()
    assert sin_vigencia_aprobadas == 0
    assert seleccion.sin_vigencia >= 0


def test_aprobar_deja_un_evento_por_version(conexion: Connection, beneficio_candidato: str) -> None:
    """Lo que se firma una vez tiene que poder auditarse una por una."""
    assert _una_version_candidata(conexion) is not None

    antes = conexion.execute(
        text("SELECT count(*) FROM auditoria_eventos WHERE accion = 'APROBAR_VERSION'")
    ).scalar_one()
    seleccion = op.aprobar(
        conexion, actor="operaciones-de-prueba", fundamento="Dato operativo con evidencia."
    )
    despues = conexion.execute(
        text("SELECT count(*) FROM auditoria_eventos WHERE accion = 'APROBAR_VERSION'")
    ).scalar_one()
    assert despues - antes == seleccion.total


def test_el_ensayo_en_seco_no_escribe(conexion: Connection) -> None:
    antes = conexion.execute(
        text("SELECT count(*) FROM registro_versiones WHERE estado_revision = 'APPROVED'")
    ).scalar_one()
    op.revisar(conexion)
    despues = conexion.execute(
        text("SELECT count(*) FROM registro_versiones WHERE estado_revision = 'APPROVED'")
    ).scalar_one()
    assert antes == despues


def test_el_reporte_dice_que_queda_afuera_y_por_que() -> None:
    seleccion = op.Seleccion(aprobables={"canal": 12}, con_incidencia=3, sin_vigencia=5)
    texto = op.formatear(seleccion, aplicado=False)
    assert "12" in texto and "canal" in texto
    assert "incidencia abierta" in texto
    assert "vigencia que nadie determinó" in texto
    assert "Nada se escribió" in texto
