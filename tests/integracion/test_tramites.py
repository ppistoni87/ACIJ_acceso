"""HU-019: trámites y pasos citables, con lo ausente a la vista."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.tramites import CargadorTramites

pytestmark = pytest.mark.integracion

FICHA = {
    "titulo": "Iniciar un reclamo ante Defensa del Consumidor",
    "dirigido": "A los consumidores que hayan tenido un problema.",
    "requisitos": [{"texto": "Tu número de DNI.", "detalle": []}],
    "pasos": [
        {"texto": "Ingresá a la Ventanilla Federal Única.", "detalle": []},
        {
            "texto": "Completá el formulario con:",
            "detalle": ["Tus datos personales.", "Los datos del reclamo."],
        },
    ],
    "costo": "Gratuito",
    "duracion": None,
    "cta_url": "https://autogestion.produccion.gob.ar/consumidores",
    "campos_ausentes": ["duracion"],
}


@pytest.fixture
def ficha_extraida(conexion: Connection):
    cargar_catalogo(conexion)

    def crear(ficha: dict, source_id: str = "F45") -> uuid.UUID:
        url_id = conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') "
                "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'DETALLE' RETURNING id"
            ),
            {"s": source_id, "u": f"https://www.argentina.gob.ar/servicio/{source_id}"},
        ).scalar_one()
        config = conexion.execute(
            text(
                "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
                " ORDER BY version DESC LIMIT 1"
            ),
            {"s": source_id},
        ).scalar_one()
        corrida = conexion.execute(
            text(
                "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
                " extractor_version, solicitadas, descargadas, procesadas, fin) "
                "VALUES (:s, :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
            ),
            {"s": source_id, "c": config},
        ).scalar_one()
        sha = uuid.uuid4().hex + uuid.uuid4().hex
        captura = conexion.execute(
            text(
                "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
                " bytes, sha256_raw, objeto_uri) "
                "VALUES (:co, :u, :url, 200, 'text/html', 100, :sha, :uri) RETURNING id"
            ),
            {
                "co": corrida,
                "u": url_id,
                "url": f"https://www.argentina.gob.ar/servicio/{source_id}",
                "sha": sha,
                "uri": f"objeto://sha256/{sha}",
            },
        ).scalar_one()
        documento = conexion.execute(
            text(
                "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
                "VALUES (:s, 'PROCEDIMIENTO', :t, :e) RETURNING id"
            ),
            {"s": source_id, "t": ficha["titulo"], "e": f"tramite:{source_id}"},
        ).scalar_one()
        return conexion.execute(
            text(
                "INSERT INTO documento_versiones (documento_id, captura_id, version, "
                " tipo_version, tipo_fecha, hash_texto, modo_extraccion, extractor_version, "
                " identidad_candidata) "
                "VALUES (:d, :c, 1, 'NO_DETERMINADO', 'DESCONOCIDA', :h, 'HTML', 'prueba', "
                "        CAST(:i AS jsonb)) RETURNING id"
            ),
            {
                "d": documento,
                "c": captura,
                "h": sha,
                "i": json.dumps({"tramite": ficha}, ensure_ascii=False),
            },
        ).scalar_one()

    return crear


def test_el_tramite_se_carga_con_sus_pasos_en_orden(conexion: Connection, ficha_extraida) -> None:
    ficha_extraida(FICHA)
    resultado = CargadorTramites(conexion).cargar()
    assert resultado.tramites_creados == 1
    assert resultado.pasos_creados == 2

    pasos = conexion.execute(
        text("SELECT orden, accion, documentacion FROM tramite_pasos ORDER BY orden")
    ).all()
    assert [p.orden for p in pasos] == [1, 2]
    assert pasos[0].accion.startswith("Ingresá")
    assert "Tus datos personales." in pasos[1].documentacion


def test_cada_paso_es_citable(conexion: Connection, ficha_extraida) -> None:
    """Un paso sin evidencia es una instrucción que el sistema da sin poder
    decir de dónde la sacó."""
    ficha_extraida(FICHA)
    CargadorTramites(conexion).cargar()
    filas = conexion.execute(
        text(
            "SELECT p.orden, e.selector, e.tipo, e.fragmento FROM tramite_pasos p "
            "  JOIN evidencias e ON e.id = p.evidencia_id ORDER BY p.orden"
        )
    ).all()
    assert [f.selector for f in filas] == ["paso:1", "paso:2"]
    assert all(f.tipo == "FRAGMENTO_TEXTO" for f in filas)
    assert filas[0].fragmento.startswith("Ingresá")


def test_una_duracion_ausente_queda_vacia_y_con_incidencia(
    conexion: Connection, ficha_extraida
) -> None:
    ficha_extraida(FICHA)
    resultado = CargadorTramites(conexion).cargar()
    assert resultado.sin_duracion == 1
    assert resultado.sin_costo == 0

    duracion = conexion.execute(text("SELECT duracion_texto FROM tramite_versiones")).scalar_one()
    assert duracion is None

    incidencia = conexion.execute(
        text(
            "SELECT descripcion, responsable_rol FROM incidencias_revision "
            " WHERE tipo = 'DATO_FALTANTE_CRITICO' AND source_id = 'F45'"
        )
    ).one()
    assert "no informa duración" in incidencia.descripcion
    assert incidencia.responsable_rol == "analisis funcional"


def test_el_publico_no_se_deduce_del_texto_de_la_ficha(
    conexion: Connection, ficha_extraida
) -> None:
    """«A los consumidores» no dice si el trámite es ciudadano o institucional:
    son ejes distintos y deducir uno del otro es adivinar."""
    ficha_extraida(FICHA)
    CargadorTramites(conexion).cargar()
    fila = conexion.execute(
        text(
            "SELECT t.publico, tv.descripcion FROM tramites t "
            "  JOIN tramite_versiones tv ON tv.tramite_id = t.id"
        )
    ).one()
    assert fila.publico == "NO_INFORMADO"
    assert "consumidores" in fila.descripcion


def test_el_estado_operativo_no_se_asume_disponible(conexion: Connection, ficha_extraida) -> None:
    """Que la ficha esté publicada no prueba que el trámite esté tomando
    solicitudes hoy."""
    ficha_extraida(FICHA)
    CargadorTramites(conexion).cargar()
    estado = conexion.execute(text("SELECT estado_operativo FROM tramite_versiones")).scalar_one()
    assert estado == "NO_INFORMADO"


def test_cargar_dos_veces_no_duplica(conexion: Connection, ficha_extraida) -> None:
    ficha_extraida(FICHA)
    cargador = CargadorTramites(conexion)
    primera = cargador.cargar()
    segunda = cargador.cargar()
    assert primera.tramites_creados == 1
    assert segunda.tramites_creados == 0
    assert segunda.tramites_conocidos == 1
    assert conexion.execute(text("SELECT count(*) FROM tramite_pasos")).scalar_one() == 2


def test_una_ficha_sin_pasos_se_registra_igual(conexion: Connection, ficha_extraida) -> None:
    """El trámite existe aunque la ficha no explique cómo hacerlo; lo que no se
    puede es publicar la capacidad de procedimiento sobre él."""
    sin_pasos = {**FICHA, "pasos": [], "titulo": "Trámite sin pasos"}
    ficha_extraida(sin_pasos, source_id="F24")
    resultado = CargadorTramites(conexion).cargar()
    assert resultado.tramites_creados == 1
    assert resultado.sin_pasos == 1
    assert any("no se publica sobre él" in a for a in resultado.avisos)
