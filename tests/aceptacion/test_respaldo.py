"""HU-037 y AT-074: restaurar y comprobar que lo restaurado sirve.

Un backup que nadie restauró no es un backup, y una restauración que nadie
verificó tampoco. Lo que estas pruebas fijan no es que `pg_restore` termine sino
que la verificación encuentre los tres modos en que una restauración parece
exitosa y no lo es: capturas sin sus bytes, un release sin lo que lo sostiene, y
eventos que se enviarían dos veces.
"""

from __future__ import annotations

import hashlib
import pathlib
import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.operacion import respaldo

pytestmark = [pytest.mark.integracion, pytest.mark.aceptacion]


@pytest.fixture
def almacen(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "objetos"


def _guardar(directorio: pathlib.Path, datos: bytes) -> str:
    sha = hashlib.sha256(datos).hexdigest()
    ruta = directorio / sha[:2] / sha[2:4] / sha
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return sha


def _manifiesto_de(conexion: Connection, almacen: pathlib.Path) -> respaldo.Manifiesto:
    return respaldo.inventariar(conexion, almacen)


def test_el_inventario_recoge_lo_que_hay_que_poder_restaurar(
    conexion: Connection, almacen, corpus_publicado
) -> None:
    for sha in conexion.execute(text("SELECT DISTINCT sha256_raw FROM capturas")).scalars():
        _guardar(almacen, sha.encode())  # contenido cualquiera: acá importa el inventario

    manifiesto = _manifiesto_de(conexion, almacen)
    assert manifiesto.capturas >= 1
    assert manifiesto.releases == 1
    assert manifiesto.evidencias >= 1
    assert manifiesto.hash


def test_una_restauracion_completa_se_declara_integra(
    conexion: Connection, almacen, corpus_publicado
) -> None:
    """El caso feliz tiene que dar íntegro; si no, los casos que fallan no
    prueban nada."""
    manifiesto = respaldo.Manifiesto()
    for sha in conexion.execute(text("SELECT DISTINCT sha256_raw FROM capturas")).scalars():
        datos = f"contenido de {sha}".encode()
        real = _guardar(almacen, datos)
        manifiesto.objetos[real] = len(datos)
    manifiesto.releases = 1
    manifiesto.evidencias = conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one()

    verificacion = respaldo.verificar(conexion, manifiesto, almacen)
    assert verificacion.integra, verificacion.problemas
    assert verificacion.objetos_presentes == len(manifiesto.objetos)
    assert verificacion.chunks > 0


def test_una_captura_sin_sus_bytes_no_pasa(conexion: Connection, almacen, corpus_publicado) -> None:
    """La base restaurada dice que hay una captura; el almacén no la tiene. Esa
    afirmación ya no se puede verificar contra nada."""
    manifiesto = respaldo.Manifiesto(
        objetos={"a" * 64: 10},
        releases=1,
        evidencias=conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one(),
    )
    verificacion = respaldo.verificar(conexion, manifiesto, almacen)
    assert not verificacion.integra
    assert verificacion.capturas_sin_objeto == ["a" * 64]
    assert any("quedaron sin bytes" in p for p in verificacion.problemas)


def test_un_objeto_alterado_se_detecta(conexion: Connection, almacen, corpus_publicado) -> None:
    """Un objeto content-addressed cuyo contenido cambió es indistinguible de
    uno correcto salvo verificándolo. Por eso se verifica."""
    sha = _guardar(almacen, b"contenido original")
    ruta = almacen / sha[:2] / sha[2:4] / sha
    ruta.write_bytes(b"otra cosa")

    manifiesto = respaldo.Manifiesto(
        objetos={sha: 18},
        releases=1,
        evidencias=conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one(),
    )
    verificacion = respaldo.verificar(conexion, manifiesto, almacen)
    assert not verificacion.integra
    assert verificacion.objetos_corruptos == [sha]
    assert any("no hashean a lo que declaran" in p for p in verificacion.problemas)


def test_un_release_sin_evidencia_no_pasa(conexion: Connection, almacen, corpus_publicado) -> None:
    """Se restauró el release pero se perdieron las evidencias: lo publicado
    dejó de poder sostenerse y seguiría sirviéndose igual."""
    manifiesto = respaldo.Manifiesto(releases=1, evidencias=9999)
    verificacion = respaldo.verificar(conexion, manifiesto, almacen)
    assert not verificacion.integra
    assert any("deja de poder sostenerse" in p for p in verificacion.problemas)


def test_un_evento_ya_entregado_no_se_puede_duplicar(
    conexion: Connection, almacen, corpus_publicado
) -> None:
    """Que un aviso no se envíe dos veces no depende de que la verificación lo
    note: lo impide un índice único sobre la clave de idempotencia. Restaurar no
    puede introducir un duplicado porque la base no lo acepta."""
    release = conexion.execute(text("SELECT id FROM releases LIMIT 1")).scalar_one()
    clave = f"prueba:{uuid.uuid4()}"
    conexion.execute(
        text(
            "INSERT INTO eventos_outbox (release_id, tipo, aggregate_id, payload, "
            " idempotency_key, entregado_en) "
            "VALUES (:r, 'RELEASE_PUBLICADO', :a, '{}'::jsonb, :k, now())"
        ),
        {"r": release, "a": uuid.uuid4(), "k": clave},
    )
    punto = conexion.begin_nested()
    with pytest.raises(IntegrityError, match="idempotency_key"):
        conexion.execute(
            text(
                "INSERT INTO eventos_outbox (release_id, tipo, aggregate_id, payload, "
                " idempotency_key) VALUES (:r, 'RELEASE_PUBLICADO', :a, '{}'::jsonb, :k)"
            ),
            {"r": release, "a": uuid.uuid4(), "k": clave},
        )
    punto.rollback()


def test_perder_un_evento_entregado_no_pasa_desapercibido(
    conexion: Connection, almacen, corpus_publicado
) -> None:
    """Si un evento entregado no llega a la restauración, el consumidor lo
    recibiría de nuevo la próxima corrida."""
    manifiesto = respaldo.Manifiesto(
        releases=1,
        evidencias=conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one(),
        eventos_entregados=3,
    )
    verificacion = respaldo.verificar(conexion, manifiesto, almacen)
    assert not verificacion.integra
    assert any("ya recibió" in p for p in verificacion.problemas)


def test_perder_los_checkpoints_no_pasa_desapercibido(
    conexion: Connection, almacen, corpus_publicado
) -> None:
    """Sin checkpoints la ingesta reanuda desde el principio: vuelve a
    descargar todo y a pedirle a la fuente lo que ya tenía."""
    manifiesto = respaldo.Manifiesto(
        releases=1,
        evidencias=conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one(),
        checkpoints={"corrida": "pagina-4"},
    )
    verificacion = respaldo.verificar(conexion, manifiesto, almacen)
    assert not verificacion.integra
    assert any("reanudaría desde el principio" in p for p in verificacion.problemas)


def test_un_respaldo_sin_manifiesto_no_se_restaura(tmp_path: pathlib.Path) -> None:
    """Restaurar solo el volcado deja una base que afirma cosas sobre bytes que
    nadie sabe si están."""
    with pytest.raises(respaldo.RespaldoInvalido, match="No hay manifiesto"):
        respaldo.leer_manifiesto(tmp_path)


def test_un_manifiesto_de_otro_formato_no_se_lee(tmp_path: pathlib.Path) -> None:
    (tmp_path / respaldo.ARCHIVO_MANIFIESTO).write_text('{"formato": "0.9"}')
    with pytest.raises(respaldo.RespaldoInvalido, match="formato"):
        respaldo.leer_manifiesto(tmp_path)


def test_el_catalogo_restaurado_conserva_las_83_fuentes(conexion: Connection) -> None:
    """La verificación mira releases y evidencia; el catálogo es lo que da
    sentido a todo lo demás y también tiene que llegar entero."""
    cargar_catalogo(conexion)
    assert conexion.execute(text("SELECT count(*) FROM fuentes")).scalar_one() == 83
