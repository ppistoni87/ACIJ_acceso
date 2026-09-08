"""HU-020 · AT-062: el directorio de la DPN sin atribuir oficinas de más.

La página lista, con el mismo formato y en la misma sección, oficinas propias de
la Defensoría del Pueblo de la Nación y defensorías provinciales y municipales
que son organismos autónomos. Leerlas todas como oficinas de la DPN manda a
reclamar al organismo equivocado, y quien reclama en el lugar equivocado a veces
pierde un plazo.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.importadores.dpn import (
    FormaInesperada,
    ImportadorDpn,
    es_whatsapp,
    leer,
    normalizar_telefono,
)

pytestmark = pytest.mark.integracion

URL_PROPIAS = "https://www.dpn.gob.ar/oficinas.php?idS=2100"
URL_TERCEROS = "https://www.dpn.gob.ar/oficinas.php?idS=2300"


def _panel(jurisdiccion: str, cuerpos: str, declaradas: int) -> str:
    return (
        '<div class="panel panel-default"><div class="panel-heading">'
        f'<h4 class="panel-title"><a href="#x"><icon class="fa fa-ellipsis-v"></icon>'
        f'{jurisdiccion} | {declaradas}<icon class="pull-right fa fa-angle-down"></icon>'
        f"</a></h4></div>{cuerpos}</div>"
    )


def _cuerpo(nombre: str, campos: str) -> str:
    return (
        '<div class="panel-collapse collapse"><div class="panel-body">'
        f"<h4>{nombre}</h4>{campos}</div></div>"
    )


# Recortes reales del directorio publicado, con el correo tal como el sitio lo
# ofusca: el valor no está en el HTML, sólo el rótulo «[email protected]».
CAMPOS_AVELLANEDA = (
    '<p><icon class="fa fa-map-marker fa-fw"></icon> Gral. Levalle 355</p>'
    '<p><icon class="fa fa-location-arrow fa-fw"></icon>(1872) Avellaneda</p>'
    '<p><icon class="fa fa-phone fa-fw"></icon> (11) 4201.5000</p>'
    '<p><icon class="fa fa-envelope"></icon> <a href="/cdn-cgi/l/email-protection" '
    'class="__cf_email__" data-cfemail="0a6f">[email&#160;protected]</a></p>'
)
CAMPOS_TANDIL = (
    '<p><icon class="fa fa-map-marker fa-fw"></icon> Belgrano 485</p>'
    '<p><icon class="fa fa-location-arrow fa-fw"></icon>(7000) Tandil</p>'
)
CAMPOS_CORDOBA = (
    '<p><icon class="fa fa-map-marker fa-fw"></icon> Dean Funes 352</p>'
    '<p><icon class="fa fa-location-arrow fa-fw"></icon>(5000) Córdoba</p>'
    # El sitio rotula este teléfono con el icono de móvil, no con el de teléfono.
    '<p><icon class="fa fa-mobile fa-fw"></icon> (351) 4342040 INT 110</p>'
    '<p><icon class="fa fa-globe"></icon> www.dpn.gob.ar</p>'
)

HTML_TERCEROS = (
    "<html><body><section id='content'>"
    + _panel(
        "Buenos Aires",
        _cuerpo("Defensor del Pueblo de Avellaneda", CAMPOS_AVELLANEDA)
        + _cuerpo("Defensoría del Pueblo de Tandil", CAMPOS_TANDIL),
        2,
    )
    + "</section></body></html>"
)

HTML_PROPIAS = (
    "<html><body><section id='content'>"
    + _panel("Córdoba", _cuerpo("Córdoba", CAMPOS_CORDOBA), 1)
    + "</section></body></html>"
)

# El rótulo anuncia tres oficinas y el panel trae una: la fuente misma dice que
# la lectura quedó incompleta.
HTML_DESCUADRADO = (
    "<html><body><section id='content'>"
    + _panel("Buenos Aires", _cuerpo("Defensor del Pueblo de Avellaneda", CAMPOS_AVELLANEDA), 3)
    + "</section></body></html>"
)


@pytest.fixture
def captura(conexion: Connection):
    cargar_catalogo(conexion)

    def crear(url: str) -> uuid.UUID:
        url_id = conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES ('F44', :u, 'LISTADO', 'HTTP_GET_PUBLICO') "
                "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'LISTADO' RETURNING id"
            ),
            {"u": url},
        ).scalar_one()
        config = conexion.execute(
            text(
                "SELECT id FROM fuente_config_versiones WHERE source_id = 'F44' "
                " ORDER BY version DESC LIMIT 1"
            )
        ).scalar_one()
        corrida = conexion.execute(
            text(
                "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
                " extractor_version, solicitadas, descargadas, procesadas, fin) "
                "VALUES ('F44', :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
            ),
            {"c": config},
        ).scalar_one()
        sha = uuid.uuid4().hex + uuid.uuid4().hex
        return conexion.execute(
            text(
                "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
                " bytes, sha256_raw, objeto_uri) "
                "VALUES (:co, :u, :url, 200, 'text/html', 100, :sha, :uri) RETURNING id"
            ),
            {"co": corrida, "u": url_id, "url": url, "sha": sha, "uri": f"objeto://sha256/{sha}"},
        ).scalar_one()

    return crear


def _importar(conexion: Connection, html: str, url: str, captura_id: uuid.UUID):
    return ImportadorDpn(conexion).importar(
        html,
        captura_id=captura_id,
        url=url,
        capturado_en=dt.datetime(2026, 3, 1, tzinfo=dt.UTC),
    )


def _punto(conexion: Connection, nombre: str):
    return (
        conexion.execute(
            text(
                "SELECT p.nombre, p.tipo, p.jurisdiccion_id, o.nombre AS titular, "
                "       o.jurisdiccion_id AS titular_jurisdiccion, op.nombre AS operador "
                "  FROM puntos_atencion p "
                "  JOIN organismos o ON o.id = p.organismo_id "
                "  LEFT JOIN organismos op ON op.id = p.organismo_operador_id "
                " WHERE p.nombre = :n"
            ),
            {"n": nombre},
        )
        .mappings()
        .one()
    )


# --- AT-062: atribución del directorio ---------------------------------------


def test_at062_una_defensoria_municipal_queda_con_su_propio_organismo(
    conexion: Connection, captura
) -> None:
    """A quien pregunta quién lo atiende en Avellaneda hay que responderle el
    Defensor del Pueblo de Avellaneda, no la Defensoría de la Nación."""
    _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))

    fila = _punto(conexion, "Defensor del Pueblo de Avellaneda")
    assert fila["titular"] == "Defensor del Pueblo de Avellaneda"
    assert fila["operador"] == "Defensoría del Pueblo de la Nación"
    # Es la sede del organismo municipal, no una delegación de la DPN.
    assert fila["tipo"] == "SEDE"


def test_at062_la_defensoria_municipal_pertenece_a_su_jurisdiccion(
    conexion: Connection, captura
) -> None:
    """Un organismo municipal bonaerense no es un organismo nacional."""
    _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))

    fila = _punto(conexion, "Defensor del Pueblo de Avellaneda")
    assert fila["jurisdiccion_id"] == "AR-B"
    assert fila["titular_jurisdiccion"] == "AR-B"


def test_at062_ninguna_defensoria_ajena_figura_como_oficina_de_la_dpn(
    conexion: Connection, captura
) -> None:
    _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))

    propias = conexion.execute(
        text(
            "SELECT count(*) FROM puntos_atencion p JOIN organismos o ON o.id = p.organismo_id "
            " WHERE o.nombre = 'Defensoría del Pueblo de la Nación'"
        )
    ).scalar_one()
    assert propias == 0


def test_at062_la_carga_de_terceros_abre_una_incidencia(conexion: Connection, captura) -> None:
    """La DPN publica el dato, pero la competencia y el horario los fija cada
    organismo: antes de servirlo hay que contrastarlo con su fuente propia."""
    resultado = _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))
    assert resultado.propias_de_la_dpn is False

    descripcion = conexion.execute(
        text("SELECT descripcion FROM incidencias_revision WHERE source_id = 'F44'")
    ).scalar_one()
    assert "no la DPN" in descripcion


def test_una_oficina_propia_queda_como_delegacion_de_la_dpn(conexion: Connection, captura) -> None:
    resultado = _importar(conexion, HTML_PROPIAS, URL_PROPIAS, captura(URL_PROPIAS))
    assert resultado.propias_de_la_dpn is True

    fila = _punto(conexion, "Córdoba")
    assert fila["titular"] == "Defensoría del Pueblo de la Nación"
    assert fila["operador"] is None
    assert fila["tipo"] == "DELEGACION"
    assert fila["jurisdiccion_id"] == "AR-X"


# --- El recuento que la fuente publica es un control -------------------------


def test_se_leen_todas_las_oficinas_del_panel_y_no_solo_la_primera(
    conexion: Connection, captura
) -> None:
    """Cada panel es una jurisdicción con varias oficinas adentro. Quedarse con
    la primera pierde el resto sin que nada falle."""
    resultado = _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))
    assert resultado.oficinas == 2
    assert resultado.puntos_creados == 2


def test_un_recuento_que_no_cuadra_se_avisa_en_vez_de_cargar_de_menos(
    conexion: Connection, captura
) -> None:
    """El rótulo «Buenos Aires | 3» es un control que la fuente regala."""
    resultado = _importar(conexion, HTML_DESCUADRADO, URL_TERCEROS, captura(URL_TERCEROS))
    assert resultado.oficinas == 1
    assert any("anuncia 3 oficina(s) y se leyeron 1" in a for a in resultado.avisos)


def test_un_recuento_que_cuadra_no_genera_aviso(conexion: Connection, captura) -> None:
    resultado = _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))
    assert not any("anuncia" in a for a in resultado.avisos)


# --- Campos ------------------------------------------------------------------


def test_un_telefono_rotulado_como_movil_tambien_es_un_telefono(
    conexion: Connection, captura
) -> None:
    """El sitio usa dos iconos para los teléfonos; mirar sólo uno pierde el otro."""
    _importar(conexion, HTML_PROPIAS, URL_PROPIAS, captura(URL_PROPIAS))

    fila = (
        conexion.execute(
            text(
                "SELECT c.valor_crudo, c.valor_normalizado FROM canales c "
                "  JOIN puntos_atencion p ON p.id = c.punto_id "
                " WHERE p.nombre = 'Córdoba' AND c.tipo = 'TELEFONO'"
            )
        )
        .mappings()
        .one()
    )
    # El texto se guarda entero: el paréntesis del código de área y el interno
    # son parte de cómo se llama a esa oficina.
    assert fila["valor_crudo"] == "(351) 4342040 INT 110"
    # Y no se normaliza, porque con un interno no hay un único número.
    assert fila["valor_normalizado"] is None


def test_el_correo_ofuscado_se_registra_como_canal_pero_no_se_decodifica(
    conexion: Connection, captura
) -> None:
    """La ofuscación es una protección contra la recolección automática. Se
    respeta: el canal existe y el valor no se toma."""
    resultado = _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))
    assert resultado.correos_no_tomados == 1

    fila = (
        conexion.execute(
            text(
                "SELECT c.valor_crudo, c.valor_normalizado, c.publico FROM canales c "
                "  JOIN puntos_atencion p ON p.id = c.punto_id "
                " WHERE c.tipo = 'EMAIL' AND p.nombre = 'Defensor del Pueblo de Avellaneda'"
            )
        )
        .mappings()
        .one()
    )
    assert fila["valor_normalizado"] is None
    assert fila["publico"] == "false"
    assert "@" not in fila["valor_crudo"]


def test_una_oficina_sin_direccion_queda_sin_direccion(conexion: Connection, captura) -> None:
    """No se completa con la de la sede central: mandaría a alguien a otra ciudad."""
    resultado = _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura(URL_TERCEROS))
    assert resultado.sin_direccion == 0

    fila = (
        conexion.execute(
            text(
                "SELECT pv.direccion_cruda, pv.localidad FROM punto_versiones pv "
                "  JOIN puntos_atencion p ON p.id = pv.punto_id "
                " WHERE p.nombre = 'Defensoría del Pueblo de Tandil'"
            )
        )
        .mappings()
        .one()
    )
    assert fila["direccion_cruda"] == "Belgrano 485"
    # Tandil no publica teléfono ni web y no se le inventan.
    canales = (
        conexion.execute(
            text(
                "SELECT c.tipo FROM canales c JOIN puntos_atencion p ON p.id = c.punto_id "
                " WHERE p.nombre = 'Defensoría del Pueblo de Tandil'"
            )
        )
        .scalars()
        .all()
    )
    assert canales == ["PRESENCIAL"]


# --- Idempotencia y forma ----------------------------------------------------


def test_importar_dos_veces_no_duplica_puntos(conexion: Connection, captura) -> None:
    captura_id = captura(URL_TERCEROS)
    _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura_id)
    segunda = _importar(conexion, HTML_TERCEROS, URL_TERCEROS, captura_id)
    assert segunda.puntos_creados == 0
    assert segunda.puntos_conocidos == 2


def test_una_seccion_desconocida_no_se_importa_a_ciegas() -> None:
    """Sin saber a qué sección pertenece no se sabe de quién son las oficinas."""
    with pytest.raises(FormaInesperada, match="no identifica ninguna"):
        leer(HTML_TERCEROS, url="https://www.dpn.gob.ar/oficinas.php?idS=9999")


def test_una_pagina_sin_paneles_no_se_importa_como_directorio_vacio() -> None:
    with pytest.raises(FormaInesperada, match=r"no trae paneles"):
        leer("<html><body><p>Mantenimiento</p></body></html>", url=URL_TERCEROS)


# --- Teléfonos: lo publicado, sin fabricar líneas -----------------------------


@pytest.mark.parametrize(
    ("publicado", "esperado"),
    [
        # Un número solo se normaliza.
        ("(261) 459.6404", "2614596404"),
        ("0810.333.3762", "08103333762"),
        ("(2972) 429 498", "2972429498"),
        # «7110» y «4222-8226» no se marcan solos: partir inventa líneas.
        ("(11) 4227-7184 / 7110 / 4222-8226", None),
        # Un interno no es parte del número al que se llama.
        ("(351) 4342040 INT 110", None),
        # Dos números pegados con un espacio pasan el patrón pero no la cuenta.
        ("(264) 4320333 4322249", None),
    ],
)
def test_un_telefono_se_normaliza_solo_si_no_hay_ambiguedad(
    publicado: str, esperado: str | None
) -> None:
    assert normalizar_telefono(publicado) == esperado


@pytest.mark.parametrize("publicado", ["WhatsApp: (221) 6727760", "wasap 362 4366823"])
def test_un_whatsapp_no_se_ofrece_como_telefono(publicado: str) -> None:
    """El sitio los rotula con el icono del teléfono; sólo el texto los delata.
    Llamar a un número que sólo atiende por WhatsApp da tono y nadie contesta."""
    assert es_whatsapp(publicado) is True
