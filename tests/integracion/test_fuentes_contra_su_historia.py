"""P-006 criterio 1: un HTTP 200 no basta.

El manifiesto declara en qué tablas tiene que terminar lo que cada fuente
aporta. Una fuente podía capturarse bien, extraerse bien y no dejar una sola
fila donde su historia dice que debería, y el catálogo la mostraba igual:
ACTIVE, ACCESIBLE, capturada.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.calidad.fuentes import (
    BLOQUEADA,
    SIN_DESTINO,
    SIN_EXTRAER,
    SIRVE,
    construir,
    formatear,
)

pytestmark = pytest.mark.integracion

POLITICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"


def _fuente(
    conexion: Connection,
    source_id: str,
    *,
    destinos: list[str],
    access_status: str = "ACCESIBLE",
    motivo: str | None = None,
) -> None:
    import json

    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso, tablas_destino, motivo_estado) "
            "VALUES (:s, :n, 'PORTAL_NORMATIVO', 'ACTIVE', :a, 'P0', :p, "
            "CAST(:d AS jsonb), :m)"
        ),
        {
            "s": source_id,
            "n": f"Fuente {source_id}",
            "a": access_status,
            "p": POLITICA,
            "d": json.dumps(destinos),
            "m": motivo,
        },
    )


def _captura(conexion: Connection, source_id: str) -> uuid.UUID:
    url = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"s": source_id, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES (:s, 1, 'HTML_ESTATICO') RETURNING id"
        ),
        {"s": source_id},
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES (:s, :c, 'EN_CURSO', 'prueba') RETURNING id"
        ),
        {"s": source_id, "c": cfg},
    ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri, "
            "http_status) VALUES (:c, :u, :h, :o, 200) RETURNING id"
        ),
        {
            "c": corrida,
            "u": url,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://var/objetos/{uuid.uuid4()}",
        },
    ).scalar_one()


def _documento(conexion: Connection, source_id: str, captura: uuid.UUID) -> uuid.UUID:
    documento = conexion.execute(
        text("INSERT INTO documentos (source_id, tipo) VALUES (:s, 'NORMA') RETURNING id"),
        {"s": source_id},
    ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            "tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba') RETURNING id"
        ),
        {"d": documento, "c": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()


def _de(conexion: Connection, source_id: str):
    return next(f for f in construir(conexion).fuentes if f.source_id == source_id)


def test_capturar_y_extraer_sin_dejar_fila_no_es_haber_cumplido(conexion: Connection) -> None:
    """El caso que el criterio nombra: respondió 200 y no llegó a destino."""
    _fuente(conexion, "T01", destinos=["unidades_documentales"])
    captura = _captura(conexion, "T01")
    _documento(conexion, "T01", captura)

    fuente = _de(conexion, "T01")

    assert fuente.veredicto == SIN_DESTINO
    assert fuente.vacias == ["unidades_documentales"]
    assert "un HTTP 200 no acredita nada" in formatear(construir(conexion))


def test_una_fuente_que_dejo_filas_donde_dijo_sirve(conexion: Connection) -> None:
    _fuente(conexion, "T02", destinos=["unidades_documentales"])
    captura = _captura(conexion, "T02")
    doc_version = _documento(conexion, "T02", captura)
    conexion.execute(
        text(
            "INSERT INTO unidades_documentales "
            "(doc_version_id, tipo, orden, texto, ruta, rol_contenido) "
            "VALUES (:dv, 'ARTICULO', 1, 'Texto del artículo.', 'articulo-1', 'DISPOSITIVO')"
        ),
        {"dv": doc_version},
    )

    fuente = _de(conexion, "T02")

    assert fuente.veredicto == SIRVE
    assert fuente.pobladas["unidades_documentales"] == 1


def test_capturada_y_nunca_extraida_es_otro_problema(conexion: Connection) -> None:
    """No es lo mismo que no llegar a destino: acá falla antes, en el adaptador."""
    _fuente(conexion, "T03", destinos=["unidades_documentales"])
    _captura(conexion, "T03")

    fuente = _de(conexion, "T03")

    assert fuente.veredicto == SIN_EXTRAER
    assert fuente.doc_versiones == 0


def test_una_fuente_bloqueada_no_se_cuenta_como_incumplimiento(conexion: Connection) -> None:
    """El bloqueo se conserva y se informa aparte; no es que la fuente falle."""
    _fuente(
        conexion,
        "T04",
        destinos=["unidades_documentales"],
        access_status="ACCESO_LIMITADO",
        motivo="HTTP 403 registrado",
    )

    fuente = _de(conexion, "T04")

    assert fuente.veredicto == BLOQUEADA
    texto = formatear(construir(conexion))
    assert "HTTP 403 registrado" in texto
    assert "No se convierte en «sin datos»" in texto


def test_las_tablas_que_no_se_pueden_atribuir_se_dicen(conexion: Connection) -> None:
    """Una norma no es «de» una fuente: varias la publican. Contar cero ahí
    diría que la fuente falló, y sería falso."""
    _fuente(conexion, "T05", destinos=["organismos", "unidades_documentales"])
    captura = _captura(conexion, "T05")
    _documento(conexion, "T05", captura)

    fuente = _de(conexion, "T05")

    assert "organismos" in fuente.no_atribuibles
    assert "organismos" not in fuente.vacias
