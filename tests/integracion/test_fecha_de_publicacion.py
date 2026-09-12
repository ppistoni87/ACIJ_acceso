"""La fecha de publicación que faltaba, y de dónde se la puede sacar.

Cuarenta y seis versiones de norma quedaban fuera de todo corte con la vigencia
en DESCONOCIDO, y no por falta de criterio jurídico: a sus documentos les
faltaba el dato más básico, cuándo se publicaron. Sin eso no hay artículo 5 del
Código Civil y Comercial que aplicar.

Lo que se prueba acá es que la fecha salga de la ficha y no de ningún otro lado,
y que cuando la ficha no la trae, no aparezca igual.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.ingesta import fecha_de_publicacion as fp

pytestmark = pytest.mark.integracion

FICHA_CON_FECHA = (
    '<html><a href="/normativa/buscar-boletin?s=1&amp;fecha_publicacion=30-10-2009">'
    "Boletín</a></html>"
)


class DescargaFalsa:
    """Lo que devolvería el cliente, sin salir a la red."""

    def __init__(self, cuerpo: str, *, status: int = 200, error: str | None = None) -> None:
        self.contenido = cuerpo.encode()
        self.http_status = status
        self.error = error
        self.url_final = "https://www.argentina.gob.ar/normativa/nacional/norma-159466"
        self.mime = "text/html"
        self.cabeceras: dict[str, str] = {}
        self.redirecciones: list = []
        self.capturado_en = dt.datetime.now(dt.UTC)

    @property
    def exitosa(self) -> bool:
        return self.error is None and self.http_status < 400


class ClienteFalso:
    def __init__(self, descarga) -> None:
        self.descarga = descarga
        self.pedidas: list[str] = []

    def descargar(self, url: str, **_):
        self.pedidas.append(url)
        return self.descarga

    def cerrar(self) -> None:
        pass


def test_el_identificador_sale_de_la_url_y_no_se_adivina() -> None:
    """El número de InfoLeg es el mismo que usa el portal: la correspondencia
    es exacta, no un parecido de tipo, número y año."""
    assert (
        fp.identificador(
            "https://servicios.infoleg.gob.ar/infolegInternet/anexos/155000-159999/159466/norma.htm"
        )
        == "159466"
    )
    assert (
        fp.identificador("https://www.argentina.gob.ar/normativa/nacional/norma-70499") == "70499"
    )
    # Las de CABA vienen del Boletín de la Ciudad y no tienen este número.
    assert (
        fp.identificador("https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=1")
        is None
    )


def test_la_fecha_sale_de_la_ficha_y_una_imposible_no_se_corrige() -> None:
    assert fp.fecha_de(FICHA_CON_FECHA) == dt.date(2009, 10, 30)
    assert fp.fecha_de("<html>sin ficha</html>") is None
    assert fp.fecha_de("fecha_publicacion=31-02-2009") is None, (
        "un 31 de febrero en la fuente no se aproxima al 28: se deja sin resolver"
    )


def _norma_sin_fecha(conexion: Connection, corpus) -> str:
    """Deja el documento del corpus sin fecha, como los 46 reales."""
    conexion.execute(
        text("UPDATE documento_versiones SET fecha_documento = NULL, tipo_fecha = 'DESCONOCIDA'")
    )
    conexion.execute(
        text(
            "UPDATE registro_versiones SET valid_tipo = 'DESCONOCIDO' WHERE entidad_tipo = 'norma'"
        )
    )
    # `capturas` es inmutable y un disparador lo hace cumplir, así que la URL de
    # InfoLeg entra en una captura nueva y el documento pasa a apuntar a ella.
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, "
            " capturado_en, sha256_raw, objeto_uri) "
            "SELECT c.corrida_id, c.source_url_id, :url, 200, c.capturado_en, :h, c.objeto_uri "
            "  FROM capturas c LIMIT 1 RETURNING id"
        ),
        {
            "url": (
                "https://servicios.infoleg.gob.ar/infolegInternet/anexos/"
                "155000-159999/159466/norma.htm"
            ),
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
        },
    ).scalar_one()
    conexion.execute(text("UPDATE documento_versiones SET captura_id = :c"), {"c": captura})
    return conexion.execute(text("SELECT id FROM documento_versiones LIMIT 1")).scalar_one()


def test_la_fecha_capturada_queda_con_su_evidencia_y_su_rastro(
    conexion: Connection, corpus
) -> None:
    """Que se pueda comprobar es la mitad del trabajo: la evidencia cita el
    trozo exacto y dice de qué captura salió, porque no salió del texto."""
    doc = _norma_sin_fecha(conexion, corpus)
    cliente = ClienteFalso(DescargaFalsa(FICHA_CON_FECHA))

    resultado = fp.completar(conexion, actor="ingesta:prueba", cliente=cliente)

    assert resultado.resueltas >= 1
    fila = conexion.execute(
        text("SELECT fecha_documento, tipo_fecha FROM documento_versiones WHERE id = :d"),
        {"d": doc},
    ).one()
    assert fila.fecha_documento == dt.date(2009, 10, 30)
    assert fila.tipo_fecha == "PUBLICACION"

    evidencia = conexion.execute(
        text(
            "SELECT fragmento, selector FROM evidencias "
            " WHERE doc_version_id = :d AND fragmento LIKE 'fecha_publicacion=%'"
        ),
        {"d": doc},
    ).one()
    assert evidencia.fragmento == "fecha_publicacion=30-10-2009"
    assert "argentina.gob.ar" in evidencia.selector

    rastro = conexion.execute(
        text(
            "SELECT motivo FROM auditoria_eventos "
            " WHERE accion = 'FECHAR_PUBLICACION' AND objeto_id = CAST(:d AS text)"
        ),
        {"d": doc},
    ).scalar_one()
    assert "403" in rastro, "el rastro dice por qué no se usó InfoLeg"


def test_si_la_ficha_no_declara_la_fecha_no_aparece_una(conexion: Connection, corpus) -> None:
    """No inventar es más importante que resolver."""
    doc = _norma_sin_fecha(conexion, corpus)
    cliente = ClienteFalso(DescargaFalsa("<html>una ficha sin fecha</html>"))

    resultado = fp.completar(conexion, actor="ingesta:prueba", cliente=cliente)

    assert resultado.resueltas == 0
    assert resultado.sin_fecha_en_la_ficha
    assert (
        conexion.execute(
            text("SELECT fecha_documento FROM documento_versiones WHERE id = :d"), {"d": doc}
        ).scalar_one()
        is None
    )


def test_una_ficha_que_no_contesta_se_cuenta_y_no_rompe(conexion: Connection, corpus) -> None:
    _norma_sin_fecha(conexion, corpus)
    cliente = ClienteFalso(DescargaFalsa("", status=403, error="403"))

    resultado = fp.completar(conexion, actor="ingesta:prueba", cliente=cliente)

    assert resultado.resueltas == 0
    assert resultado.no_alcanzadas


def test_simular_no_pide_nada(conexion: Connection, corpus) -> None:
    _norma_sin_fecha(conexion, corpus)
    cliente = ClienteFalso(DescargaFalsa(FICHA_CON_FECHA))

    resultado = fp.completar(conexion, actor="ingesta:prueba", simular=True, cliente=cliente)

    assert resultado.simulado
    assert cliente.pedidas == [], "simular no puede salir a la red"
