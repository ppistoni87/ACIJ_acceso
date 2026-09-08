"""`v_hechos_servibles`: qué puede responderse y por qué a veces no.

Publicar no significa aplicable a cualquier fecha, y frescura no es vigencia.
Estas pruebas fijan esa diferencia.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

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


def _ahora(conexion: Connection) -> dt.datetime:
    """El «ahora» de la consulta, tomado del reloj de la base.

    Estuvo escrito como una constante con la fecha de hoy y a las 12:00 del día
    en que se escribió empezó a fallar: las filas nacen con `known_desde =
    now()`, así que cualquier hora fija de hoy queda antes de que existan y las
    deja fuera del intervalo de conocimiento. El eje de conocimiento se consulta
    con un instante real, no con uno inventado.
    """
    return conexion.execute(text("SELECT now()")).scalar_one()


def _release_publicado(conexion: Connection) -> uuid.UUID:
    return conexion.execute(
        text(
            "INSERT INTO releases (estado, publicado_en, aprobado_por, manifest_hash) "
            "VALUES ('PUBLICADO', now(), 'equipo-de-datos', :h) RETURNING id"
        ),
        {"h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()


def _version_publicada(
    conexion: Connection,
    *,
    release: uuid.UUID,
    desde: str = "2026-01-01",
    hasta: str | None = "2026-12-31",
    valid_tipo: str = "CERRADO",
    reverificar: str | None = "2027-01-01T00:00:00+00:00",
    entidad_tipo: str = "beneficio",
) -> uuid.UUID:
    return conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde, valid_hasta, release_id, verificado_en, "
            "reverificar_antes_de) "
            "VALUES (:et, gen_random_uuid(), 'PUBLISHED', :vt, :vd, :vh, :r, "
            "'2026-09-01T00:00:00+00:00', :rev) RETURNING id"
        ),
        {
            "et": entidad_tipo,
            "vt": valid_tipo,
            "vd": desde,
            "vh": hasta,
            "r": release,
            "rev": reverificar,
        },
    ).scalar_one()


def _motivos(conexion: Connection, version: uuid.UUID, fecha: str, capacidad: str) -> list[str]:
    return [
        fila[0]
        for fila in conexion.execute(
            text("SELECT bn_motivos_no_servible(:v, :f, :k, :c)"),
            {"v": version, "f": fecha, "k": _ahora(conexion), "c": capacidad},
        )
    ]


def test_una_version_publicada_y_vigente_es_servible(conexion: Connection) -> None:
    release = _release_publicado(conexion)
    version = _version_publicada(conexion, release=release)
    assert _motivos(conexion, version, "2026-06-15", "IDENTIFICACION") == []

    servibles = (
        conexion.execute(
            text("SELECT registro_version_id FROM v_hechos_servibles(:f, :k, 'IDENTIFICACION')"),
            {"f": dt.date(2026, 6, 15), "k": _ahora(conexion)},
        )
        .scalars()
        .all()
    )
    assert version in servibles


def test_una_fecha_fuera_del_periodo_no_se_sirve_como_actual(conexion: Connection) -> None:
    """El monto de una campaña anterior no se responde como si rigiera hoy."""
    release = _release_publicado(conexion)
    version = _version_publicada(conexion, release=release, desde="2024-01-01", hasta="2024-12-31")
    motivos = _motivos(conexion, version, "2026-06-15", "IDENTIFICACION")
    assert any("UNSUPPORTED_SCOPE" in m for m in motivos)


def test_vencer_la_frescura_no_deroga_pero_sí_impide_servir(conexion: Connection) -> None:
    """Un TTL vencido no cambia el derecho: cambia lo que podemos afirmar hoy
    sin volver a verificar."""
    release = _release_publicado(conexion)
    version = _version_publicada(conexion, release=release, reverificar="2026-08-01T00:00:00+00:00")
    motivos = _motivos(conexion, version, "2026-06-15", "IDENTIFICACION")
    assert any("STALE_DATA" in m and "frescura" in m for m in motivos)
    # La vigencia jurídica declarada sigue intacta.
    vigencia = conexion.execute(
        text("SELECT valid_desde, valid_hasta FROM registro_versiones WHERE id = :v"),
        {"v": version},
    ).one()
    assert vigencia == (dt.date(2026, 1, 1), dt.date(2026, 12, 31))


def test_vigencia_desconocida_no_se_asume_abierta(conexion: Connection) -> None:
    """Que no sepamos hasta cuándo rige no la vuelve aplicable para siempre."""
    release = _release_publicado(conexion)
    version = _version_publicada(
        conexion, release=release, desde=None, hasta=None, valid_tipo="DESCONOCIDO"
    )
    motivos = _motivos(conexion, version, "2026-06-15", "IDENTIFICACION")
    assert any("DESCONOCIDO" in m for m in motivos)


def test_un_conflicto_abierto_bloquea_la_publicacion_de_ese_hecho(
    conexion: Connection,
) -> None:
    """F66/F67: ante una discrepancia de edad entre la página y el reglamento,
    el sistema se abstiene en vez de elegir un valor en silencio."""
    release = _release_publicado(conexion)
    version = _version_publicada(conexion, release=release)
    conexion.execute(
        text(
            "INSERT INTO incidencias_revision (registro_version_id, tipo, severidad, estado, "
            "descripcion) VALUES (:v, 'CONFLICTO_DE_FUENTES', 'HIGH', 'ABIERTA', "
            "'Discrepancia de edad entre la ficha y el reglamento')"
        ),
        {"v": version},
    )
    motivos = _motivos(conexion, version, "2026-06-15", "IDENTIFICACION")
    assert any("CONFLICT" in m for m in motivos)


def test_una_capacidad_puede_servir_mientras_otra_se_abstiene(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """Una norma con monto desconocido sustenta una explicación general y aun
    así no responde "cuánto cobro"."""
    release = _release_publicado(conexion)
    version = _version_publicada(conexion, release=release, entidad_tipo="norma")

    norma_id, doc_version = _norma_y_documento(conexion, jurisdiccion_nacion)
    conexion.execute(
        text("UPDATE registro_versiones SET entidad_id = :n WHERE id = :v"),
        {"n": norma_id, "v": version},
    )
    conexion.execute(
        text(
            "INSERT INTO norma_versiones (registro_version_id, norma_id, doc_version_id, "
            "tipo_version) VALUES (:rv, :n, :dv, 'ORIGINAL')"
        ),
        {"rv": version, "n": norma_id, "dv": doc_version},
    )
    for campo, estado in (
        ("beneficio_otorgado", "NO_INFORMADO_EN_FUENTES_REVISADAS"),
        ("interdependencias", "INFORMADO"),
    ):
        conexion.execute(
            text(
                "INSERT INTO evaluaciones_completitud (norma_version_id, campo_solicitado, "
                "estado) VALUES (:rv, :c, :e)"
            ),
            {"rv": version, "c": campo, "e": estado},
        )

    assert _motivos(conexion, version, "2026-06-15", "IDENTIFICACION") == []
    assert _motivos(conexion, version, "2026-06-15", "EXPLICACION_HISTORICA") == []
    motivos_monto = _motivos(conexion, version, "2026-06-15", "MONTO")
    assert any("beneficio_otorgado" in m for m in motivos_monto)


def test_una_capacidad_no_declarada_no_se_responde(conexion: Connection) -> None:
    release = _release_publicado(conexion)
    version = _version_publicada(conexion, release=release)
    motivos = _motivos(conexion, version, "2026-06-15", "CUALQUIER_COSA")
    assert any("UNSUPPORTED_SCOPE" in m for m in motivos)


def _norma_y_documento(conexion: Connection, jurisdiccion: str) -> tuple[uuid.UUID, uuid.UUID]:
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, titulo) "
            "VALUES (:j, 'LEY', 'Norma de prueba') RETURNING id"
        ),
        {"j": jurisdiccion},
    ).scalar_one()
    _alta_de_fuente(conexion, "FSRV")
    url = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES ('FSRV', :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES ('FSRV', 1, 'HTML_ESTATICO') RETURNING id"
        )
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES ('FSRV', :c, 'EN_CURSO', 'test-0') RETURNING id"
        ),
        {"c": cfg},
    ).scalar_one()
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri) "
            "VALUES (:c, :u, :h, :o) RETURNING id"
        ),
        {
            "c": corrida,
            "u": url,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://var/objetos/{uuid.uuid4()}",
        },
    ).scalar_one()
    doc = conexion.execute(
        text("INSERT INTO documentos (source_id, tipo) VALUES ('FSRV', 'NORMA') RETURNING id")
    ).scalar_one()
    doc_version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            "tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba') RETURNING id"
        ),
        {"d": doc, "c": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()
    return norma_id, doc_version
