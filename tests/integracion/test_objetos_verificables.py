"""P-004: el original detrás de cada afirmación tiene que seguir estando.

Un objeto que falta no se nota. La fila de la captura sigue ahí, con su hash y
su URI, y todo lo que cuelga de ella se sigue sirviendo igual; lo único que se
perdió es la posibilidad de comprobarlo. Estas pruebas fijan que eso deje de
ser silencioso: que se detecte, que abra incidencia y que la incidencia saque
de circulación lo que dependía del objeto.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from backend_normativo.ingesta.almacen import AlmacenObjetos, sha256_de
from backend_normativo.operacion.objetos import (
    DIFIERE,
    FALTA,
    sincronizar,
    verificar_almacen,
)

pytestmark = pytest.mark.integracion

POLITICA_PUBLICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"
CONTENIDO = b"<html><body>Texto original de la norma</body></html>"


@pytest.fixture
def almacen(tmp_path: Path) -> AlmacenObjetos:
    return AlmacenObjetos(base_uri=f"file://{tmp_path}", directorio=tmp_path)


def _capturado(
    conexion: Connection, almacen: AlmacenObjetos, contenido: bytes = CONTENIDO
) -> tuple[str, uuid.UUID]:
    """Una captura real con su objeto guardado, y la versión que depende de ella."""
    objeto = almacen.guardar(contenido)
    source_id = f"P4{uuid.uuid4().hex[:6]}"
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso) "
            "VALUES (:sid, :nombre, 'PORTAL_NORMATIVO', 'ACTIVE', 'ACCESIBLE', 'P0', :pol)"
        ),
        {"sid": source_id, "nombre": f"Fuente {source_id}", "pol": POLITICA_PUBLICA},
    )
    url = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:sid, :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"sid": source_id, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES (:sid, 1, 'HTML_ESTATICO') RETURNING id"
        ),
        {"sid": source_id},
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES (:sid, :c, 'EN_CURSO', 'test-0') RETURNING id"
        ),
        {"sid": source_id, "c": cfg},
    ).scalar_one()
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri, "
            "mime, bytes, http_status, url_final) "
            "VALUES (:c, :u, :h, :o, 'text/html', :b, 200, :uf) RETURNING id"
        ),
        {
            "c": corrida,
            "u": url,
            "h": objeto.sha256,
            "o": objeto.uri,
            "b": objeto.bytes,
            "uf": f"https://ejemplo.gob.ar/{uuid.uuid4()}",
        },
    ).scalar_one()
    documento = conexion.execute(
        text("INSERT INTO documentos (source_id, tipo) VALUES (:sid, 'NORMA') RETURNING id"),
        {"sid": source_id},
    ).scalar_one()
    doc_version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            "tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba') RETURNING id"
        ),
        {"d": documento, "c": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO jurisdicciones (id, nombre, nivel) "
            "VALUES ('AR', 'República Argentina', 'NACIONAL') ON CONFLICT (id) DO NOTHING"
        )
    )
    norma = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, titulo) "
            "VALUES ('AR', 'LEY', 'Norma de prueba') RETURNING id"
        )
    ).scalar_one()
    release = conexion.execute(
        text(
            "INSERT INTO releases (estado, publicado_en, aprobado_por, manifest_hash) "
            "VALUES ('PUBLICADO', now(), 'equipo-de-datos', :h) RETURNING id"
        ),
        {"h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde, valid_hasta, release_id, verificado_en, "
            "reverificar_antes_de) "
            "VALUES ('norma', :n, 'PUBLISHED', 'CERRADO', '2026-01-01', '2026-12-31', :r, "
            "'2026-09-01T00:00:00+00:00', '2027-01-01T00:00:00+00:00') RETURNING id"
        ),
        {"n": norma, "r": release},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO norma_versiones (registro_version_id, norma_id, doc_version_id, "
            "tipo_version) VALUES (:rv, :n, :dv, 'ORIGINAL')"
        ),
        {"rv": version, "n": norma, "dv": doc_version},
    )
    return objeto.sha256, version


def _incidencias(conexion: Connection, version: uuid.UUID) -> list[tuple[str, str]]:
    return [
        (fila.tipo, fila.severidad)
        for fila in conexion.execute(
            text(
                "SELECT tipo, severidad FROM incidencias_revision "
                " WHERE registro_version_id = :v AND estado = 'ABIERTA'"
            ),
            {"v": version},
        )
    ]


def _motivos(conexion: Connection, version: uuid.UUID) -> list[str]:
    ahora = conexion.execute(text("SELECT now()")).scalar_one()
    return [
        fila[0]
        for fila in conexion.execute(
            text("SELECT bn_motivos_no_servible(:v, '2026-06-15', :k, 'NORMA_TEXTO')"),
            {"v": version, "k": ahora},
        )
    ]


def test_un_objeto_presente_e_intacto_no_abre_nada(
    conexion: Connection, almacen: AlmacenObjetos
) -> None:
    _capturado(conexion, almacen)
    reporte = verificar_almacen(conexion, almacen)
    assert reporte.referencias == 1
    assert reporte.intactos == 1
    assert reporte.hallazgos == []
    assert not reporte.hay_problemas


def test_un_objeto_que_falta_bloquea_la_version_que_depende_de_el(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    sha, version = _capturado(conexion, almacen)
    assert not any("CONFLICT" in m for m in _motivos(conexion, version)), (
        "antes de romper nada, la versión se sirve"
    )

    (tmp_path / sha[:2] / sha[2:4] / sha).unlink()
    reporte = verificar_almacen(conexion, almacen)

    assert [h.motivo for h in reporte.hallazgos] == [FALTA]
    assert reporte.versiones_bloqueadas == 1
    assert _incidencias(conexion, version) == [("EVIDENCIA_NO_RECUPERABLE", "CRITICAL")]
    # Lo que importa no es la incidencia sino su efecto: la versión deja de
    # poder servirse mientras el original no se recupere.
    assert any("CONFLICT" in m for m in _motivos(conexion, version))


def test_un_objeto_alterado_no_se_confunde_con_uno_que_falta(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    sha, version = _capturado(conexion, almacen)
    (tmp_path / sha[:2] / sha[2:4] / sha).write_bytes(b"otra cosa")

    reporte = verificar_almacen(conexion, almacen)

    assert [h.motivo for h in reporte.hallazgos] == [DIFIERE]
    assert "cambió" in reporte.hallazgos[0].explicacion
    assert any("CONFLICT" in m for m in _motivos(conexion, version))


def test_verificar_dos_veces_no_duplica_la_incidencia(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    sha, version = _capturado(conexion, almacen)
    (tmp_path / sha[:2] / sha[2:4] / sha).unlink()

    primera = verificar_almacen(conexion, almacen)
    segunda = verificar_almacen(conexion, almacen)

    assert primera.incidencias_abiertas == 1
    assert segunda.incidencias_abiertas == 0
    assert segunda.hallazgos[0].incidencias_ya_abiertas == 1
    assert len(_incidencias(conexion, version)) == 1


def test_informar_sin_abrir_incidencias_no_bloquea(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    """Para inspeccionar hace falta poder mirar sin decidir."""
    sha, version = _capturado(conexion, almacen)
    (tmp_path / sha[:2] / sha[2:4] / sha).unlink()

    reporte = verificar_almacen(conexion, almacen, abrir_incidencias=False)

    assert reporte.hay_problemas
    assert reporte.incidencias_abiertas == 0
    assert _incidencias(conexion, version) == []
    assert not any("CONFLICT" in m for m in _motivos(conexion, version))


def test_el_mismo_contenido_dos_veces_es_un_solo_objeto(almacen: AlmacenObjetos) -> None:
    """Deduplicación: reingestar lo mismo no duplica bytes ni pisa nada."""
    primero = almacen.guardar(CONTENIDO)
    segundo = almacen.guardar(CONTENIDO)
    distinto = almacen.guardar(CONTENIDO + "<!-- cambió -->".encode())

    assert primero.sha256 == segundo.sha256
    assert not primero.ya_existia
    assert segundo.ya_existia
    assert distinto.sha256 != primero.sha256
    assert almacen.leer(primero.sha256) == CONTENIDO, "la versión nueva no pisó a la anterior"
    archivos = [r for r in almacen.directorio.rglob("*") if r.is_file()]
    assert len(archivos) == 2, "tres escrituras, dos contenidos, dos archivos"


def test_el_hash_viaja_con_el_objeto_a_otro_almacen(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    """El criterio de P-004: recuperarlo desde otra instancia y que coincida."""
    import shutil

    _capturado(conexion, almacen)
    otra = tmp_path / "otra_instancia"
    shutil.copytree(almacen.directorio, otra)
    otro_almacen = AlmacenObjetos(base_uri=f"file://{otra}", directorio=otra)

    reporte = verificar_almacen(conexion, otro_almacen)

    assert reporte.intactos == 1
    assert not reporte.hay_problemas
    # Y el objeto leído desde la otra instancia es byte por byte el mismo.
    sha = conexion.execute(text("SELECT sha256_raw FROM capturas")).scalar_one()
    assert sha256_de(otro_almacen.leer(sha)) == sha


def test_sincronizar_lleva_los_originales_y_los_relee_en_el_destino(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    """P-004: que sobrevivan al contenedor exige copiarlos y comprobarlos allá."""
    sha, _ = _capturado(conexion, almacen)
    afuera = tmp_path / "persistente"
    destino = AlmacenObjetos(base_uri=f"file://{afuera}", directorio=afuera)

    reporte = sincronizar(conexion, destino, almacen)

    assert reporte.referenciados == 1
    assert reporte.copiados == 1
    assert reporte.ya_estaban == 0
    assert reporte.completa
    assert sha256_de(destino.leer(sha)) == sha


def test_sincronizar_dos_veces_no_vuelve_a_copiar(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    _capturado(conexion, almacen)
    afuera = tmp_path / "persistente"
    destino = AlmacenObjetos(base_uri=f"file://{afuera}", directorio=afuera)

    sincronizar(conexion, destino, almacen)
    segunda = sincronizar(conexion, destino, almacen)

    assert segunda.copiados == 0
    assert segunda.ya_estaban == 1
    assert segunda.completa


def test_sincronizar_no_puede_copiar_lo_que_ya_se_perdio(
    conexion: Connection, almacen: AlmacenObjetos, tmp_path: Path
) -> None:
    """Una copia no repone lo que ya no está: lo dice en vez de dar por completo."""
    sha, _ = _capturado(conexion, almacen)
    (almacen.directorio / sha[:2] / sha[2:4] / sha).unlink()
    afuera = tmp_path / "persistente"
    destino = AlmacenObjetos(base_uri=f"file://{afuera}", directorio=afuera)

    reporte = sincronizar(conexion, destino, almacen)

    assert reporte.copiados == 0
    assert reporte.sin_origen == [sha]
    assert not reporte.completa
