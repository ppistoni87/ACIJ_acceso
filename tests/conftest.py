"""Fixtures compartidas.

Las pruebas de integración corren sobre una base real: las reglas que
verificamos son restricciones, triggers y funciones de PostgreSQL, y un doble no
las ejecutaría.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

URL_ADMIN = os.environ.get(
    "BN_TEST_ADMIN_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres"
)
BASE_PRUEBAS = os.environ.get("BN_TEST_DB", "backend_normativo_test")


def _url_pruebas() -> str:
    return URL_ADMIN.rsplit("/", 1)[0] + "/" + BASE_PRUEBAS


@pytest.fixture(scope="session")
def engine_pruebas() -> Iterator[Engine]:
    admin = create_engine(URL_ADMIN, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{BASE_PRUEBAS}" WITH (FORCE)'))
            c.execute(text(f'CREATE DATABASE "{BASE_PRUEBAS}"'))
    except Exception as exc:  # pragma: no cover - entorno sin PostgreSQL
        pytest.skip(f"PostgreSQL no disponible: {exc}")
    finally:
        admin.dispose()

    os.environ["BN_DATABASE_URL"] = _url_pruebas()

    from alembic import command
    from alembic.config import Config

    from backend_normativo.config import get_settings

    get_settings.cache_clear()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    engine = create_engine(_url_pruebas(), future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def conexion(engine_pruebas: Engine) -> Iterator[Connection]:
    """Conexión con transacción externa que siempre se revierte: cada prueba ve
    el esquema limpio sin volver a migrar.

    Los triggers de restricción del esquema son `DEFERRABLE INITIALLY DEFERRED`
    porque la carga real inserta grafos completos y necesita cerrarlos antes de
    validarlos. Como las pruebas nunca confirman, se piden inmediatos para que
    la violación aparezca en la sentencia que la produce. El comportamiento
    diferido tiene su propia prueba.
    """
    with engine_pruebas.connect() as conn:
        trans = conn.begin()
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        try:
            yield conn
        finally:
            trans.rollback()


@pytest.fixture
def sesion(conexion: Connection) -> Iterator[Session]:
    with Session(bind=conexion, join_transaction_mode="create_savepoint") as s:
        yield s


@pytest.fixture
def jurisdiccion_nacion(conexion: Connection) -> str:
    conexion.execute(
        text(
            "INSERT INTO jurisdicciones (id, nombre, nivel) "
            "VALUES ('AR', 'República Argentina', 'NACIONAL')"
        )
    )
    return "AR"


@pytest.fixture
def jurisdiccion_caba(conexion: Connection, jurisdiccion_nacion: str) -> str:
    conexion.execute(
        text(
            "INSERT INTO jurisdicciones (id, parent_id, nombre, nivel) "
            "VALUES ('AR-C', :padre, 'Ciudad Autónoma de Buenos Aires', 'CIUDAD_AUTONOMA')"
        ),
        {"padre": jurisdiccion_nacion},
    )
    return "AR-C"


def nuevo_uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def viola_restriccion(conexion: Connection):
    """Espera que el bloque viole una restricción, dejando la transacción usable.

    PostgreSQL aborta la transacción entera ante un error, así que sin un punto
    de retorno una prueba no puede comprobar el rechazo y después el caso
    válido. Este ayudante abre uno y lo revierte.
    """
    import contextlib

    from sqlalchemy.exc import DBAPIError

    @contextlib.contextmanager
    def _ctx(match: str | None = None):
        punto = conexion.begin_nested()
        with pytest.raises(DBAPIError, match=match):
            try:
                yield
            finally:
                punto.rollback()

    return _ctx
