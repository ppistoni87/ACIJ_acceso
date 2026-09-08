"""Temporalidad, evidencia y estados: las reglas que evitan afirmar de más."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

pytestmark = pytest.mark.integracion

POLITICA_PUBLICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"


def _alta_de_fuente(conexion: Connection, source_id: str) -> str:
    """Fuente mínima del catálogo para colgar capturas y documentos."""
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso) "
            "VALUES (:sid, :nombre, 'PORTAL_NORMATIVO', 'ACTIVE', 'ACCESIBLE', 'P0', :politica) "
            "ON CONFLICT (source_id) DO NOTHING"
        ),
        {"sid": source_id, "nombre": f"Fuente {source_id}", "politica": POLITICA_PUBLICA},
    )
    return source_id


def _crear_version(
    conexion: Connection,
    *,
    entidad_tipo: str,
    entidad_id: uuid.UUID,
    valid_tipo: str = "ABIERTO_FIN",
    valid_desde: str | None = "2020-01-01",
    valid_hasta: str | None = None,
    estado_revision: str = "CANDIDATE",
    condicion: str | None = None,
    numero_version: int = 1,
) -> uuid.UUID:
    return conexion.execute(
        text(
            "INSERT INTO registro_versiones "
            "(entidad_tipo, entidad_id, numero_version, estado_revision, "
            " valid_tipo, valid_desde, valid_hasta, condicion_vigencia) "
            "VALUES (:tipo, :eid, :nv, :er, :vt, :vd, :vh, :cond) RETURNING id"
        ),
        {
            "tipo": entidad_tipo,
            "eid": entidad_id,
            "nv": numero_version,
            "er": estado_revision,
            "vt": valid_tipo,
            "vd": valid_desde,
            "vh": valid_hasta,
            "cond": condicion,
        },
    ).scalar_one()


# --- Bitemporalidad ----------------------------------------------------------


def test_valid_tipo_cerrado_exige_ambos_extremos(conexion: Connection) -> None:
    with pytest.raises(IntegrityError):
        _crear_version(
            conexion,
            entidad_tipo="norma",
            entidad_id=uuid.uuid4(),
            valid_tipo="CERRADO",
            valid_hasta=None,
        )


def test_abierto_fin_no_admite_fecha_de_cierre(conexion: Connection) -> None:
    """Declarar que no hay fin y a la vez poner uno es una contradicción: el
    extremo abierto solo se declara cuando la fuente lo respalda."""
    with pytest.raises(IntegrityError):
        _crear_version(
            conexion,
            entidad_tipo="norma",
            entidad_id=uuid.uuid4(),
            valid_tipo="ABIERTO_FIN",
            valid_hasta="2025-12-31",
        )


def test_condicionado_exige_declarar_la_condicion(conexion: Connection) -> None:
    with pytest.raises(IntegrityError):
        _crear_version(
            conexion,
            entidad_tipo="norma",
            entidad_id=uuid.uuid4(),
            valid_tipo="CONDICIONADO",
            condicion=None,
        )


def test_desconocido_no_produce_rango_aplicable(conexion: Connection) -> None:
    """Un límite temporal desconocido no se vuelve infinito aplicable: no genera
    rango y por lo tanto no puede servirse como vigente."""
    rango = conexion.execute(
        text("SELECT bn_rango_aplicacion('DESCONOCIDO', '2020-01-01'::date, NULL)")
    ).scalar_one()
    assert rango is None


def test_rango_conserva_ambos_extremos_inclusivos(conexion: Connection) -> None:
    """El último día declarado por la fuente sigue estando dentro del período."""
    contiene = conexion.execute(
        text(
            "SELECT bn_rango_aplicacion('CERRADO', '2026-01-01'::date, '2026-03-31'::date) "
            "@> '2026-03-31'::date"
        )
    ).scalar_one()
    assert contiene is True


def test_solo_un_intervalo_de_conocimiento_abierto_por_version(conexion: Connection) -> None:
    """Dos filas vigentes a la vez para la misma versión lógica harían que una
    consulta histórica devolviera dos verdades simultáneas."""
    eid = uuid.uuid4()
    _crear_version(conexion, entidad_tipo="norma", entidad_id=eid, numero_version=1)
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO registro_versiones "
                "(entidad_tipo, entidad_id, numero_version, estado_revision, valid_tipo) "
                "VALUES ('norma', :eid, 1, 'CANDIDATE', 'ABIERTO_FIN')"
            ),
            {"eid": eid},
        )


def test_publicar_exige_release_y_verificacion(conexion: Connection) -> None:
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO registro_versiones "
                "(entidad_tipo, entidad_id, estado_revision, valid_tipo, valid_desde) "
                "VALUES ('norma', gen_random_uuid(), 'PUBLISHED', 'ABIERTO_FIN', '2020-01-01')"
            )
        )


# --- Supertipo controlado ----------------------------------------------------


def test_subtipo_no_puede_usar_una_version_de_otro_tipo(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """Una versión de beneficio no puede hacerse pasar por versión de norma."""
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, titulo) "
            "VALUES (:jur, 'LEY', 'Norma') RETURNING id"
        ),
        {"jur": jurisdiccion_nacion},
    ).scalar_one()
    beneficio_id = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre) VALUES ('B_PRUEBA', 'Beneficio') RETURNING id"
        )
    ).scalar_one()
    version_de_beneficio = _crear_version(
        conexion, entidad_tipo="beneficio", entidad_id=beneficio_id
    )
    doc_version = _preparar_documento(conexion)

    with pytest.raises(DBAPIError, match='de tipo "beneficio"'):
        conexion.execute(
            text(
                "INSERT INTO norma_versiones "
                "(registro_version_id, norma_id, doc_version_id, tipo_version) "
                "VALUES (:rv, :n, :dv, 'ORIGINAL')"
            ),
            {"rv": version_de_beneficio, "n": norma_id, "dv": doc_version},
        )


def test_subtipo_no_puede_versionar_otra_entidad(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """La versión declara qué norma versiona; la fila del subtipo no puede
    apuntar a otra."""
    normas = [
        conexion.execute(
            text(
                "INSERT INTO normas (jurisdiccion_id, tipo, titulo) "
                "VALUES (:jur, 'LEY', :t) RETURNING id"
            ),
            {"jur": jurisdiccion_nacion, "t": f"Norma {i}"},
        ).scalar_one()
        for i in range(2)
    ]
    version = _crear_version(conexion, entidad_tipo="norma", entidad_id=normas[0])
    doc_version = _preparar_documento(conexion)
    with pytest.raises(DBAPIError, match="versiona la entidad"):
        conexion.execute(
            text(
                "INSERT INTO norma_versiones "
                "(registro_version_id, norma_id, doc_version_id, tipo_version) "
                "VALUES (:rv, :n, :dv, 'ORIGINAL')"
            ),
            {"rv": version, "n": normas[1], "dv": doc_version},
        )


# --- Documentos, unidades y evidencia ---------------------------------------


def _preparar_documento(conexion: Connection, *, sufijo: str = "") -> uuid.UUID:
    """Crea fuente, configuración, corrida, captura, documento y una versión."""
    sid = f"FTEST{sufijo or '0'}"
    _alta_de_fuente(conexion, sid)
    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:sid, :url, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"sid": sid, "url": f"https://ejemplo.gob.ar/norma/{uuid.uuid4()}"},
    ).scalar_one()
    config_id = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES (:sid, 1, 'HTML_ESTATICO') "
            "ON CONFLICT (source_id, version) DO UPDATE SET adaptador = EXCLUDED.adaptador "
            "RETURNING id"
        ),
        {"sid": sid},
    ).scalar_one()
    corrida_id = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta "
            "(source_id, config_version_id, estado, extractor_version) "
            "VALUES (:sid, :cfg, 'EN_CURSO', 'test-0') RETURNING id"
        ),
        {"sid": sid, "cfg": config_id},
    ).scalar_one()
    captura_id = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri, http_status) "
            "VALUES (:c, :u, :h, :o, 200) RETURNING id"
        ),
        {
            "c": corrida_id,
            "u": url_id,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://var/objetos/{uuid.uuid4()}",
        },
    ).scalar_one()
    documento_id = conexion.execute(
        text(
            "INSERT INTO documentos (source_id, tipo, titulo) "
            "VALUES (:sid, 'NORMA', 'Documento') RETURNING id"
        ),
        {"sid": sid},
    ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO documento_versiones "
            "(documento_id, captura_id, version, tipo_version, tipo_fecha, hash_texto, "
            " modo_extraccion) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML') RETURNING id"
        ),
        {"d": documento_id, "c": captura_id, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()


def test_evidencia_no_puede_citar_una_unidad_de_otra_version(conexion: Connection) -> None:
    """Una cita que apunta a otra versión sostendría una afirmación que ese
    texto no dice."""
    version_a = _preparar_documento(conexion, sufijo="A")
    version_b = _preparar_documento(conexion, sufijo="B")
    unidad_de_a = conexion.execute(
        text(
            "INSERT INTO unidades_documentales "
            "(doc_version_id, tipo, ruta, orden, texto, rol_contenido) "
            "VALUES (:dv, 'ARTICULO', 'art-1', 1, 'Texto', 'DISPOSITIVO') RETURNING id"
        ),
        {"dv": version_a},
    ).scalar_one()

    with pytest.raises(DBAPIError, match="cita la unidad"):
        conexion.execute(
            text(
                "INSERT INTO evidencias "
                "(doc_version_id, unidad_id, fragmento, hash_fragmento, tipo) "
                "VALUES (:dv, :u, 'fragmento', :h, 'FRAGMENTO_TEXTO')"
            ),
            {"dv": version_b, "u": unidad_de_a, "h": uuid.uuid4().hex + uuid.uuid4().hex},
        )


def test_articulo_citado_no_colisiona_con_el_articulo_raiz(conexion: Connection) -> None:
    """F23: una ley que sustituye artículos incluye el texto de esos artículos
    dentro del suyo. Ese texto citado comparte número pero no es una raíz."""
    version = _preparar_documento(conexion, sufijo="C")
    raiz = conexion.execute(
        text(
            "INSERT INTO unidades_documentales "
            "(doc_version_id, tipo, numero, ruta, orden, texto, rol_contenido) "
            "VALUES (:dv, 'ARTICULO', '10', 'art-10', 1, 'Sustitúyese...', 'DISPOSITIVO') "
            "RETURNING id"
        ),
        {"dv": version},
    ).scalar_one()
    # El artículo 10 citado dentro del artículo 10 dispositivo.
    conexion.execute(
        text(
            "INSERT INTO unidades_documentales "
            "(doc_version_id, parent_id, tipo, numero, ruta, orden, texto, rol_contenido) "
            "VALUES (:dv, :p, 'ARTICULO', '10', 'art-10', 2, 'Artículo 10: ...', 'SUSTITUTIVO')"
        ),
        {"dv": version, "p": raiz},
    )
    total = conexion.execute(
        text("SELECT count(*) FROM unidades_documentales WHERE doc_version_id = :dv"),
        {"dv": version},
    ).scalar_one()
    assert total == 2

    # Pero dos raíces con la misma ruta sí colisionan.
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO unidades_documentales "
                "(doc_version_id, tipo, numero, ruta, orden, texto, rol_contenido) "
                "VALUES (:dv, 'ARTICULO', '10', 'art-10', 3, 'Otro', 'DISPOSITIVO')"
            ),
            {"dv": version},
        )


def test_un_304_exige_captura_previa(conexion: Connection) -> None:
    """Una revalidación sin cuerpo no puede inventar bytes descargados."""
    version = _preparar_documento(conexion, sufijo="D")
    corrida_id, url_id = conexion.execute(
        text(
            "SELECT c.corrida_id, c.source_url_id FROM capturas c "
            "JOIN documento_versiones dv ON dv.captura_id = c.id WHERE dv.id = :dv"
        ),
        {"dv": version},
    ).one()
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO capturas "
                "(corrida_id, source_url_id, sha256_raw, objeto_uri, http_status) "
                "VALUES (:c, :u, :h, :o, 304)"
            ),
            {
                "c": corrida_id,
                "u": url_id,
                "h": uuid.uuid4().hex + uuid.uuid4().hex,
                "o": "file://var/objetos/x",
            },
        )


def test_los_bytes_capturados_son_inmutables(conexion: Connection) -> None:
    version = _preparar_documento(conexion, sufijo="E")
    captura_id = conexion.execute(
        text("SELECT captura_id FROM documento_versiones WHERE id = :dv"), {"dv": version}
    ).scalar_one()
    with pytest.raises(DBAPIError, match="inmutable"):
        conexion.execute(
            text("UPDATE capturas SET http_status = 200 WHERE id = :c"), {"c": captura_id}
        )


def test_una_corrida_incompleta_no_figura_exitosa(conexion: Connection) -> None:
    """Contadores sin reconciliar y estado COMPLETA es la forma más silenciosa
    de perder cobertura: siete de diez solicitudes resueltas no es una corrida
    completa."""
    _preparar_documento(conexion, sufijo="F")
    config_id = conexion.execute(
        text("SELECT id FROM fuente_config_versiones WHERE source_id = 'FTESTF'")
    ).scalar_one()
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO corridas_ingesta "
                "(source_id, config_version_id, estado, extractor_version, fin, "
                " solicitadas, descargadas, procesadas, rechazadas) "
                "VALUES ('FTESTF', :cfg, 'COMPLETA', 'test-0', now(), 10, 10, 4, 3)"
            ),
            {"cfg": config_id},
        )
