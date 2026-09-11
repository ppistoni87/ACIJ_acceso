"""El cargador transcribe decisiones ajenas; no toma ninguna.

La firma jurídica ocurre fuera del sistema y después hay que dejarla registrada
sin que el trayecto la deforme. Lo que estas pruebas cuidan es justamente lo que
el cargador **no** hace: completar un fundamento que falta, aplicar medio
archivo, o aceptar una decisión que el vocabulario no admite.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion import transcripcion

pytestmark = pytest.mark.integracion

OTRA = uuid.uuid4()


def _csv(filas: list[tuple[str, str, str]]) -> str:
    cabecera = "regla,decision,fundamento\n"
    return cabecera + "\n".join(f"{r},{d},{f}" for r, d, f in filas)


def test_una_fila_sin_fundamento_no_se_registra() -> None:
    """El fundamento es lo único que distingue una regla revisada de una firmada
    de apuro, y no hay texto genérico que pueda sustituirlo."""
    with pytest.raises(transcripcion.ArchivoInvalido, match="sin fundamento"):
        transcripcion.leer(_csv([(str(uuid.uuid4()), "APROBAR", "")]))


def test_una_fila_mala_impide_aplicar_todo_el_archivo() -> None:
    """Media transcripción es peor que ninguna: nadie sabe dónde quedó."""
    bueno, malo = str(uuid.uuid4()), str(uuid.uuid4())
    with pytest.raises(transcripcion.ArchivoInvalido) as error:
        transcripcion.leer(
            _csv([(bueno, "APROBAR", "Dice lo que la norma dice."), (malo, "APROBAR", "")])
        )
    assert "no se aplica ninguna" in str(error.value)


def test_una_decision_que_no_existe_se_rechaza() -> None:
    with pytest.raises(transcripcion.ArchivoInvalido, match="desconocida"):
        transcripcion.leer(_csv([(str(uuid.uuid4()), "PUBLICAR", "Porque sí.")]))


def test_publicar_no_es_una_decision_de_revision() -> None:
    """Firmar una regla no la pone a contestar: publicar es del corte.

    Si `PUBLICAR` fuera una decisión admitida acá, una firma saltearía el control
    del release, que es donde se verifica que las dependencias estén aprobadas.
    """
    assert "PUBLICAR" not in transcripcion.DECISIONES


def test_la_misma_regla_dos_veces_no_se_resuelve_sola() -> None:
    regla = str(uuid.uuid4())
    with pytest.raises(transcripcion.ArchivoInvalido, match="ya venía decidida"):
        transcripcion.leer(_csv([(regla, "APROBAR", "Sí."), (regla, "RECHAZAR", "No.")]))


def test_sin_actor_no_se_transcribe(conexion: Connection) -> None:
    """La bitácora tiene que decir quién revisó, no quién cargó el archivo."""
    filas = transcripcion.leer(_csv([(str(uuid.uuid4()), "APROBAR", "Coincide.")]))
    with pytest.raises(transcripcion.ArchivoInvalido, match="Falta el actor"):
        transcripcion.aplicar(conexion, filas, actor="   ")


def test_un_archivo_vacio_no_es_una_transcripcion() -> None:
    with pytest.raises(transcripcion.ArchivoInvalido, match="vacío"):
        transcripcion.leer("")


def test_acepta_json_ademas_de_csv() -> None:
    """Quien revisa exporta de donde puede; pedir conversión pierde filas."""
    regla = str(uuid.uuid4())
    filas = transcripcion.leer(
        f'[{{"regla":"{regla}","decision":"aprobar","fundamento":"El art. 2 lo dice."}}]'
    )
    assert len(filas) == 1
    assert filas[0].decision == "APROBAR"


def test_la_decision_transcripta_queda_con_el_actor_de_quien_reviso(
    conexion: Connection, corpus
) -> None:
    """Lo que se registra es la firma de la persona, no la del proceso."""
    regla_id = conexion.execute(
        text("SELECT id FROM reglas WHERE estado_revision = 'CANDIDATE' LIMIT 1")
    ).scalar_one_or_none()
    if regla_id is None:
        pytest.skip("El corpus de prueba no trae reglas candidatas.")

    filas = transcripcion.leer(
        _csv([(str(regla_id), "APROBAR", "Coincide con el artículo citado.")])
    )
    resultado = transcripcion.aplicar(conexion, filas, actor="dra.revisora")
    assert resultado.aplicadas == 1

    actor, motivo = conexion.execute(
        text(
            "SELECT actor, motivo FROM auditoria_eventos "
            " WHERE objeto_id = :r AND accion = 'APROBAR_REGLA' ORDER BY ocurrido_en DESC LIMIT 1"
        ),
        {"r": regla_id},
    ).one()
    assert actor == "dra.revisora"
    assert "artículo citado" in motivo
