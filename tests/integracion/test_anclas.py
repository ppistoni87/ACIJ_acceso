"""HU-F28 · AT-006: el alias con fragmento que no resuelve.

F28 es la misma página que F31, citada con `#44` para señalar una pregunta. El
alias vale como identidad de la referencia; el ancla hay que comprobarla. Una
página carga igual cuando el fragmento no existe, así que el error no se nota:
alguien sigue el enlace y aterriza arriba de todo.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.anclas import (
    anclas_de,
    fragmento_de,
    parecidos_a,
    verificar,
)
from backend_normativo.catalogo.carga import cargar_catalogo

pytestmark = pytest.mark.integracion

# La página real de F31 usa anclas `accordion-<id>`, ninguna numérica, y una de
# ellas contiene «44». Es la coincidencia que hay que no tomar.
FAQ = """
<html><body>
  <div id="page-wrapper">
    <div id="accordion-2691962"><h3>¿Cuándo abre la inscripción?</h3></div>
    <div id="accordion-item-2691962">En noviembre.</div>
    <div id="accordion-2693944"><h3>¿Qué documentación llevo?</h3></div>
    <div id="accordion-item-2693944">DNI del estudiante.</div>
    <a name="contacto">Contacto</a>
  </div>
</body></html>
"""


class AlmacenFalso:
    def __init__(self, contenido: bytes) -> None:
        self.contenido = contenido

    def leer(self, sha256: str) -> bytes:
        return self.contenido


@pytest.fixture
def catalogo_con_captura(conexion: Connection):
    """Deja F28 aliasando a F31 con `#44`, y una captura real de F31."""
    cargar_catalogo(conexion)

    def crear(url_destino: str = "https://ejemplo.gob.ar/preguntas-frecuentes") -> None:
        url_id = conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES ('F31', :u, 'ENTRADA', 'HTTP_GET_PUBLICO') "
                "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'ENTRADA' RETURNING id"
            ),
            {"u": url_destino},
        ).scalar_one()
        cfg = conexion.execute(
            text(
                "SELECT id FROM fuente_config_versiones WHERE source_id = 'F31' "
                " ORDER BY version DESC LIMIT 1"
            )
        ).scalar_one()
        corrida = conexion.execute(
            text(
                "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
                " extractor_version, solicitadas, descargadas, procesadas, fin) "
                "VALUES ('F31', :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
            ),
            {"c": cfg},
        ).scalar_one()
        conexion.execute(
            text(
                "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
                " bytes, sha256_raw, objeto_uri) "
                "VALUES (:co, :u, :url, 200, 'text/html; charset=utf-8', 100, :sha, :uri)"
            ),
            {
                "co": corrida,
                "u": url_id,
                "url": url_destino,
                "sha": uuid.uuid4().hex + uuid.uuid4().hex,
                "uri": "objeto://sha256/prueba",
            },
        )

    return crear


def _verificar(conexion: Connection, html: str = FAQ):
    return verificar(conexion, AlmacenFalso(html.encode("utf-8")))


# --- AT-006: alias conservado, ancla rota reportada -------------------------


def test_at006_el_ancla_inexistente_se_reporta_como_rota(
    conexion: Connection, catalogo_con_captura
) -> None:
    catalogo_con_captura()
    reporte = _verificar(conexion)

    rotas = {a.source_id: a for a in reporte.rotas}
    assert "F28" in rotas
    assert rotas["F28"].fragmento == "44"
    assert rotas["F28"].destino_source_id == "F31"


def test_at006_el_alias_se_conserva_aunque_el_ancla_no_resuelva(
    conexion: Connection, catalogo_con_captura
) -> None:
    """La referencia es un dato: que no lleve a la pregunta citada no la borra."""
    catalogo_con_captura()
    _verificar(conexion)

    fila = (
        conexion.execute(text("SELECT alias_of, estado FROM fuentes WHERE source_id = 'F28'"))
        .mappings()
        .one()
    )
    assert fila["alias_of"] == "F31"
    assert fila["estado"] == "REFERENCE_ONLY"


def test_at006_ningun_mapeo_por_semejanza_numerica(
    conexion: Connection, catalogo_con_captura
) -> None:
    """`accordion-2693944` contiene «44» y no es la pregunta 44. Que la página
    tenga un ancla parecida no la convierte en la citada."""
    catalogo_con_captura()
    reporte = _verificar(conexion)

    ancla = next(a for a in reporte.rotas if a.source_id == "F28")
    assert ancla.estado == "ROTA"
    assert "accordion-2693944" in ancla.parecidos
    # El parecido se reporta, nunca se resuelve.
    assert not reporte.resueltas


def test_at006_la_incidencia_dice_que_no_se_resolvio_por_parecido(
    conexion: Connection, catalogo_con_captura
) -> None:
    catalogo_con_captura()
    _verificar(conexion)

    fila = (
        conexion.execute(
            text(
                "SELECT tipo, severidad, responsable_rol, descripcion "
                "  FROM incidencias_revision WHERE source_id = 'F28'"
            )
        )
        .mappings()
        .one()
    )
    assert fila["tipo"] == "DATO_FALTANTE_CRITICO"
    assert fila["severidad"] == "HIGH"
    assert fila["responsable_rol"]
    assert "No se resolvió por parecido" in fila["descripcion"]
    assert "accordion-2693944" in fila["descripcion"]


def test_verificar_dos_veces_no_duplica_la_incidencia(
    conexion: Connection, catalogo_con_captura
) -> None:
    catalogo_con_captura()
    _verificar(conexion)
    _verificar(conexion)

    assert (
        conexion.execute(
            text("SELECT count(*) FROM incidencias_revision WHERE source_id = 'F28'")
        ).scalar_one()
        == 1
    )


def test_un_ancla_que_existe_se_declara_resuelta(
    conexion: Connection, catalogo_con_captura
) -> None:
    catalogo_con_captura()
    html = FAQ.replace('id="accordion-2691962"', 'id="44"')
    reporte = _verificar(conexion, html)

    assert not reporte.rotas
    ancla = next(a for a in reporte.resueltas if a.source_id == "F28")
    assert ancla.fragmento == "44"
    assert (
        conexion.execute(
            text("SELECT count(*) FROM incidencias_revision WHERE source_id = 'F28'")
        ).scalar_one()
        == 0
    )


def test_sin_captura_del_destino_no_se_declara_rota_ni_valida(conexion: Connection) -> None:
    """No haberla mirado no es lo mismo que haberla mirado y no encontrarla."""
    cargar_catalogo(conexion)
    reporte = _verificar(conexion)

    ancla = next(a for a in reporte.sin_captura if a.source_id == "F28")
    assert ancla.estado == "SIN_CAPTURA"
    assert "no se miró" in ancla.detalle
    assert not reporte.rotas


# --- Piezas ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("https://x.gob.ar/preguntas#44", "44"),
        ("https://x.gob.ar/preguntas", None),
        ("https://x.gob.ar/preguntas#", None),
        ("https://x.gob.ar/p#secci%C3%B3n-2", "sección-2"),
    ],
)
def test_el_fragmento_se_lee_de_la_url(url: str, esperado: str | None) -> None:
    assert fragmento_de(url) == esperado


def test_un_ancla_es_un_id_o_el_name_de_un_enlace() -> None:
    assert anclas_de(FAQ) == {
        "page-wrapper",
        "accordion-2691962",
        "accordion-item-2691962",
        "accordion-2693944",
        "accordion-item-2693944",
        "contacto",
    }


def test_los_parecidos_solo_se_buscan_para_fragmentos_numericos() -> None:
    """«contacto» no tiene parecidos por dígitos; el ruido no ayuda a revisar."""
    assert parecidos_a("contacto", anclas_de(FAQ)) == []
    assert parecidos_a("44", anclas_de(FAQ)) == [
        "accordion-2693944",
        "accordion-item-2693944",
    ]
