"""P-020 criterio 2: dos disparos simultáneos no procesan lo mismo dos veces.

Estas pruebas usan conexiones reales y separadas contra la base, no la
transacción compartida del resto de la suite. Es a propósito: un arrendamiento
tomado dentro de una transacción sin confirmar no es visible para nadie más, así
que probarlo ahí adentro sería probar que dos procesos que no se ven no se
pisan, que es cierto y no dice nada.

Cada prueba arrienda un recurso con nombre propio para que dos pruebas nunca se
disputen el mismo y no haga falta limpiar entre una y otra.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Engine, text

from backend_normativo.operacion.arrendamiento import (
    Arrendador,
    arrendar,
    titular_de_esta_corrida,
)

pytestmark = pytest.mark.integracion


@pytest.fixture
def recurso() -> str:
    return f"prueba:{uuid.uuid4().hex[:12]}"


def _conexion(engine: Engine):
    return engine.connect().execution_options(isolation_level="AUTOCOMMIT")


def test_el_segundo_disparo_no_consigue_el_turno(engine_pruebas: Engine, recurso: str) -> None:
    with _conexion(engine_pruebas) as primera, _conexion(engine_pruebas) as segunda:
        uno = Arrendador(primera, recurso, duracion=dt.timedelta(minutes=5))
        dos = Arrendador(segunda, recurso, duracion=dt.timedelta(minutes=5))

        assert uno.tomar() is not None
        assert dos.tomar() is None, "el segundo disparo no puede correr en paralelo"

        # Y sabe quién lo tiene, que es lo que se pregunta cuando algo no corrió.
        ocupante = dos.quien_lo_tiene()
        assert ocupante is not None
        assert ocupante.titular == uno.titular


def test_al_soltarlo_el_siguiente_lo_toma(engine_pruebas: Engine, recurso: str) -> None:
    with _conexion(engine_pruebas) as primera, _conexion(engine_pruebas) as segunda:
        uno = Arrendador(primera, recurso, duracion=dt.timedelta(minutes=5))
        dos = Arrendador(segunda, recurso, duracion=dt.timedelta(minutes=5))

        assert uno.tomar() is not None
        assert uno.soltar() is True
        tenencia = dos.tomar()
        assert tenencia is not None
        assert tenencia.corridas == 2, "la fila lleva la cuenta de las vueltas"


def test_un_turno_vencido_queda_libre_solo(engine_pruebas: Engine, recurso: str) -> None:
    """Recuperación tras caída: nadie soltó nada y el recurso se libera igual."""
    with _conexion(engine_pruebas) as caida, _conexion(engine_pruebas) as siguiente:
        # Duración cero: es el proceso que muere en el instante en que tomó el
        # turno, sin llegar a soltarlo ni a trabajar.
        muerta = Arrendador(caida, recurso, duracion=dt.timedelta(0))
        assert muerta.tomar() is not None
        assert muerta.quien_lo_tiene() is None, "un turno ya vencido no tiene titular vigente"

        rescate = Arrendador(siguiente, recurso, duracion=dt.timedelta(minutes=5))
        assert rescate.tomar() is not None, "el turno vencido lo toma la vuelta siguiente"


def test_soltar_un_turno_ajeno_no_hace_nada(engine_pruebas: Engine, recurso: str) -> None:
    """Quien se pasó de su turno no puede cerrarle la corrida al que lo tomó después."""
    with _conexion(engine_pruebas) as primera, _conexion(engine_pruebas) as segunda:
        vencida = Arrendador(primera, recurso, duracion=dt.timedelta(0))
        assert vencida.tomar() is not None

        nueva = Arrendador(segunda, recurso, duracion=dt.timedelta(minutes=5))
        assert nueva.tomar() is not None

        assert vencida.soltar() is False, "ya no era suyo"
        assert nueva.quien_lo_tiene() is not None, "el turno de la nueva sigue en pie"


def test_la_corrida_que_se_pasa_de_su_turno_se_entera(engine_pruebas: Engine, recurso: str) -> None:
    """El vencimiento es un tope real: no se renueva mientras se trabaja.

    Si se renovara, un proceso trabado bloquearía el recurso para siempre y el
    «tiempo máximo» del criterio no existiría. Lo que sí se exige es que la
    corrida que se pasó lo sepa, porque otra pudo haber arrancado en paralelo.
    """
    with arrendar(engine_pruebas, recurso, duracion=dt.timedelta(0)) as turno:
        assert turno.tomado
    assert turno.se_paso is True
    assert "en paralelo" in turno.advertencia()

    with arrendar(engine_pruebas, recurso, duracion=dt.timedelta(minutes=5)) as turno:
        assert turno.tomado
    assert turno.se_paso is False
    assert turno.advertencia() == ""


def test_el_turno_no_conseguido_no_es_un_error(engine_pruebas: Engine, recurso: str) -> None:
    """No conseguirlo es la respuesta correcta a dos disparos, no una excepción."""
    with _conexion(engine_pruebas) as ocupante:
        Arrendador(ocupante, recurso, duracion=dt.timedelta(minutes=5)).tomar()

        with arrendar(engine_pruebas, recurso) as turno:
            assert not turno.tomado
        assert "Otra corrida tiene el turno" in turno.por_que_no()


def test_la_constancia_sobrevive_a_la_corrida(engine_pruebas: Engine, recurso: str) -> None:
    """Soltar adelanta el vencimiento; no borra quién corrió."""
    with arrendar(engine_pruebas, recurso, duracion=dt.timedelta(minutes=5)) as turno:
        titular = turno.tenencia.titular

    with engine_pruebas.connect() as conexion:
        fila = conexion.execute(
            text("SELECT titular, corridas FROM arrendamientos WHERE recurso = :r"),
            {"r": recurso},
        ).one()
    assert fila.titular == titular
    assert fila.corridas == 1


def test_el_titular_identifica_maquina_proceso_y_corrida() -> None:
    partes = titular_de_esta_corrida().split("/")
    assert len(partes) == 3, "hace falta saber qué instancia quedó colgada y dónde encontrarla"
    assert all(partes)
    assert titular_de_esta_corrida() != titular_de_esta_corrida()
