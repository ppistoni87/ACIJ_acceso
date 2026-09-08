"""HU-037 · AT-074: el volcado y la restauración de verdad.

Las otras pruebas de respaldo verifican que la comprobación de integridad
encuentre lo que falta. Ésta verifica lo anterior: que `pg_dump` produzca un
volcado y que `pg_restore` lo deje servible en una base que empieza vacía.

Corre sobre bases propias, creadas y borradas acá, porque un volcado sólo ve lo
que está confirmado y las pruebas de integración trabajan dentro de una
transacción que siempre se revierte. Restaurar sobre una base que ya tiene el
esquema no probaría nada: el caso que importa es el del servidor nuevo.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text

from backend_normativo.operacion import respaldo

pytestmark = [pytest.mark.integracion, pytest.mark.aceptacion, pytest.mark.lento]

URL_ADMIN = os.environ.get(
    "BN_TEST_ADMIN_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres"
)


def _url(base: str) -> str:
    return URL_ADMIN.rsplit("/", 1)[0] + "/" + base


def _crear(base: str) -> None:
    admin = create_engine(URL_ADMIN, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{base}"'))
    admin.dispose()


def _borrar(base: str) -> None:
    admin = create_engine(URL_ADMIN, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)'))
    admin.dispose()


def _migrar(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    from backend_normativo.config import get_settings

    previo = os.environ.get("BN_DATABASE_URL")
    os.environ["BN_DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previo is None:
            os.environ.pop("BN_DATABASE_URL", None)
        else:
            os.environ["BN_DATABASE_URL"] = previo
        get_settings.cache_clear()


@pytest.fixture(scope="module")
def sufijo() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture(scope="module")
def origen(sufijo: str) -> Iterator[tuple[Engine, str, pathlib.Path]]:
    """Una base con catálogo cargado y una captura con sus bytes, confirmada."""
    base = f"bn_respaldo_origen_{sufijo}"
    try:
        _crear(base)
    except Exception as exc:  # pragma: no cover - entorno sin PostgreSQL
        pytest.skip(f"PostgreSQL no disponible: {exc}")
    _migrar(_url(base))

    directorio = pathlib.Path(f"/tmp/bn-objetos-{sufijo}")
    directorio.mkdir(parents=True, exist_ok=True)

    motor = create_engine(_url(base), future=True)
    with motor.begin() as conexion:
        from backend_normativo.catalogo.carga import cargar_catalogo

        cargar_catalogo(conexion)
        _sembrar(conexion, directorio)

    yield motor, base, directorio
    motor.dispose()
    _borrar(base)


def _sembrar(conexion, directorio: pathlib.Path) -> None:
    """Una captura real con su objeto en disco: es lo que hay que poder restaurar."""
    contenido = b"<html><body>Texto capturado que tiene que sobrevivir al volcado.</body></html>"
    sha = hashlib.sha256(contenido).hexdigest()
    ruta = directorio / sha[:2] / sha[2:4] / sha
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)

    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES ('D01', :u, 'ENTRADA', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "SELECT id FROM fuente_config_versiones WHERE source_id = 'D01' "
            " ORDER BY version DESC LIMIT 1"
        )
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            " extractor_version, solicitadas, descargadas, procesadas, fin) "
            "VALUES ('D01', :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
        ),
        {"c": cfg},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
            " bytes, sha256_raw, objeto_uri) "
            "VALUES (:co, :u, 'https://ejemplo.gob.ar/x', 200, 'text/html', :b, :s, :o)"
        ),
        {
            "co": corrida,
            "u": url_id,
            "b": len(contenido),
            "s": sha,
            "o": f"objeto://sha256/{sha}",
        },
    )


# --- AT-074: el volcado se restaura en una base que empieza vacía ------------


@pytest.fixture(scope="module")
def restaurada(origen, sufijo: str, tmp_path_factory) -> Iterator[tuple[Engine, pathlib.Path]]:
    motor, base, directorio = origen
    respaldo_dir = tmp_path_factory.mktemp("respaldo")
    with motor.connect() as conexion:
        respaldo.respaldar(
            conexion,
            respaldo_dir,
            url_base=_url(base),
            directorio_objetos=directorio,
        )

    destino = f"bn_respaldo_destino_{sufijo}"
    _crear(destino)
    respaldo.restaurar(respaldo_dir, url_destino=_url(destino))

    motor_destino = create_engine(_url(destino), future=True)
    yield motor_destino, respaldo_dir
    motor_destino.dispose()
    _borrar(destino)


def test_at074_el_volcado_se_escribe_con_su_manifiesto(origen, restaurada) -> None:
    _, respaldo_dir = restaurada
    assert (respaldo_dir / respaldo.ARCHIVO_BASE).stat().st_size > 0

    manifiesto = respaldo.leer_manifiesto(respaldo_dir)
    assert manifiesto.formato == respaldo.FORMATO
    assert manifiesto.capturas == 1
    assert manifiesto.hash


def test_at074_la_base_restaurada_conserva_las_83_fuentes(restaurada) -> None:
    """Restaurar el esquema sin el catálogo dejaría una base que arranca y no
    sabe qué tiene que mirar."""
    motor_destino, _ = restaurada
    with motor_destino.connect() as conexion:
        assert conexion.execute(text("SELECT count(*) FROM fuentes")).scalar_one() == 83


def test_at074_la_captura_restaurada_conserva_su_hash(restaurada) -> None:
    """Una captura es inmutable: si el volcado la cambia, deja de sostener lo
    que se publicó sobre ella."""
    motor_destino, _ = restaurada
    with motor_destino.connect() as conexion:
        fila = (
            conexion.execute(text("SELECT sha256_raw, bytes, http_status FROM capturas"))
            .mappings()
            .one()
        )
    assert fila["http_status"] == 200
    assert len(fila["sha256_raw"]) == 64
    assert fila["bytes"] > 0


def test_at074_la_verificacion_pasa_sobre_la_base_restaurada(origen, restaurada) -> None:
    """El punto del caso: no que `pg_restore` termine, sino que lo restaurado
    sirva y se pueda demostrar."""
    _, _, directorio = origen
    motor_destino, respaldo_dir = restaurada
    manifiesto = respaldo.leer_manifiesto(respaldo_dir)

    with motor_destino.connect() as conexion:
        verificacion = respaldo.verificar(conexion, manifiesto, directorio)

    assert verificacion.integra, verificacion.problemas
    assert verificacion.objetos_presentes == verificacion.objetos_esperados
    assert verificacion.objetos_esperados == len(manifiesto.objetos)


def test_at074_el_esquema_restaurado_conserva_sus_restricciones(restaurada) -> None:
    """Un volcado que pierde los triggers deja una base que acepta lo que la
    original rechazaba, y eso no se nota hasta que alguien escribe."""
    motor_destino, _ = restaurada
    with motor_destino.connect() as conexion:
        inmutables = conexion.execute(
            text(
                "SELECT count(*) FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
                " WHERE p.proname = 'bn_rechazar_modificacion' AND NOT t.tgisinternal"
            )
        ).scalar_one()
        assert inmutables >= 3

    with motor_destino.begin() as escritura, pytest.raises(Exception, match="inmutable"):
        escritura.execute(text("DELETE FROM capturas"))
