"""P-007 criterio 2: recorrer el grafo tiene que terminar.

Los ciclos son legítimos —la Ordenanza 43.478 cita a la Ley 547 y la Ley 547
modifica la Ordenanza 43.478—, así que la protección no puede ser prohibirlos.
Tiene que ser que el recorrido los atraviese una vez y siga.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.calidad.grafo import construir, formatear

pytestmark = pytest.mark.integracion


def _norma(conexion: Connection, numero: str) -> uuid.UUID:
    conexion.execute(
        text(
            "INSERT INTO jurisdicciones (id, nombre, nivel) "
            "VALUES ('AR', 'República Argentina', 'NACIONAL') ON CONFLICT (id) DO NOTHING"
        )
    )
    return conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR', 'LEY', :n, 2000, :t) RETURNING id"
        ),
        {"n": numero, "t": f"Ley {numero}"},
    ).scalar_one()


def _evidencia(conexion: Connection) -> uuid.UUID:
    """Toda relación exige evidencia: no hay relación sin de dónde salió.

    Se arma la cadena mínima —fuente, URL, corrida, captura, documento,
    versión— porque el esquema la exige entera, y exigirla es el punto.
    """
    source_id = f"G{uuid.uuid4().hex[:7]}"
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso) VALUES (:s, :n, 'PORTAL_NORMATIVO', 'ACTIVE', "
            "'ACCESIBLE', 'P0', "
            "'PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS')"
        ),
        {"s": source_id, "n": f"Fuente {source_id}"},
    )
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
    documento = conexion.execute(
        text("INSERT INTO documentos (source_id, tipo) VALUES (:s, 'NORMA') RETURNING id"),
        {"s": source_id},
    ).scalar_one()
    doc_version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            "tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba') RETURNING id"
        ),
        {"d": documento, "c": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, fragmento, hash_fragmento, tipo) "
            "VALUES (:dv, :f, :h, 'FRAGMENTO_TEXTO') RETURNING id"
        ),
        {
            "dv": doc_version,
            "f": "cita de prueba",
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
        },
    ).scalar_one()


def _relacion(conexion: Connection, origen: uuid.UUID, destino: uuid.UUID, tipo: str) -> None:
    conexion.execute(
        text(
            "INSERT INTO relaciones_normativas "
            "(norma_origen_id, norma_destino_id, tipo, evidencia_id, estado_revision) "
            "VALUES (:o, :d, :t, :e, 'CANDIDATE')"
        ),
        {"o": origen, "d": destino, "t": tipo, "e": _evidencia(conexion)},
    )


def _alcanzables(
    conexion: Connection,
    desde: uuid.UUID,
    profundidad: int = 4,
    sentido: str = "SALIENTE",
) -> set[tuple[uuid.UUID, int]]:
    return {
        (fila.norma_id, fila.profundidad)
        for fila in conexion.execute(
            text("SELECT norma_id, profundidad FROM bn_grafo_normativo(:n, :p, :s)"),
            {"n": desde, "p": profundidad, "s": sentido},
        )
    }


def test_un_ciclo_de_dos_normas_no_hace_que_el_recorrido_no_termine(
    conexion: Connection,
) -> None:
    a = _norma(conexion, "1001")
    b = _norma(conexion, "1002")
    _relacion(conexion, a, b, "CITA")
    _relacion(conexion, b, a, "MODIFICA")

    alcanzables = _alcanzables(conexion, a)

    assert alcanzables == {(b, 1)}, "b una vez; volver a `a` sería repetir el nodo de partida"


def test_cada_norma_aparece_una_vez_por_el_camino_mas_corto(conexion: Connection) -> None:
    """Dos caminos hasta el mismo destino no lo devuelven dos veces."""
    a = _norma(conexion, "1003")
    b = _norma(conexion, "1004")
    c = _norma(conexion, "1005")
    _relacion(conexion, a, b, "CITA")
    _relacion(conexion, b, c, "CITA")
    _relacion(conexion, a, c, "CITA")

    alcanzables = _alcanzables(conexion, a)

    assert alcanzables == {(b, 1), (c, 1)}, "c se alcanza en un salto, no en dos"


def test_el_tope_de_profundidad_corta_la_cadena(conexion: Connection) -> None:
    a = _norma(conexion, "1006")
    b = _norma(conexion, "1007")
    c = _norma(conexion, "1008")
    _relacion(conexion, a, b, "CITA")
    _relacion(conexion, b, c, "CITA")

    assert _alcanzables(conexion, a, profundidad=1) == {(b, 1)}
    assert _alcanzables(conexion, a, profundidad=2) == {(b, 1), (c, 2)}


def test_el_sentido_entrante_devuelve_quien_apunta_a_la_norma(conexion: Connection) -> None:
    """«Qué normas afectan a esta» es la pregunta que va a hacer la recuperación."""
    norma = _norma(conexion, "1009")
    modificadora = _norma(conexion, "1010")
    _relacion(conexion, modificadora, norma, "SUSTITUYE")

    assert _alcanzables(conexion, norma, sentido="SALIENTE") == set()
    assert _alcanzables(conexion, norma, sentido="ENTRANTE") == {(modificadora, 1)}


def test_una_norma_no_puede_citarse_a_si_misma(conexion: Connection, viola_restriccion) -> None:
    """El ciclo más corto posible lo cierra el esquema, no el código.

    El resolutor ya omitía las autorreferencias —91 en la última corrida real—
    pero nada impedía escribirlas por otra vía.
    """
    a = _norma(conexion, "1011")
    with viola_restriccion("sin_autorreferencia"):
        _relacion(conexion, a, a, "CITA")


def test_el_informe_cuenta_los_ciclos_en_vez_de_esconderlos(conexion: Connection) -> None:
    a = _norma(conexion, "1012")
    b = _norma(conexion, "1013")
    _relacion(conexion, a, b, "CITA")
    _relacion(conexion, b, a, "MODIFICA")

    reporte = construir(conexion, profundidad=3)

    assert reporte.relaciones == 2
    assert reporte.normas_con_relacion == 2
    assert reporte.autorreferencias == 0
    assert reporte.ciclos_por_largo.get(2) == 2, "el ciclo se cuenta desde cada extremo"
    texto = formatear(reporte)
    assert "no es una lista de errores" in texto
