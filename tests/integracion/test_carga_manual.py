"""HU-038: carga manual trazada para fuentes bloqueadas.

Su única razón de ser es que el dato manual no valga menos que el automático
porque nadie sepa de dónde salió. Estas pruebas fijan lo que se exige declarar y
lo que la carga no puede afirmar.
"""

from __future__ import annotations

import datetime as dt
import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.almacen import AlmacenObjetos
from backend_normativo.ingesta.manual import (
    CargaManual,
    ProcedenciaInsuficiente,
    fuentes_bloqueadas,
)

pytestmark = pytest.mark.integracion

PROCEDENCIA = "Copia entregada por la Dirección de Legales el 3 de marzo por expediente 123/26."
ACTOR = "ingesta:persona"


@pytest.fixture
def almacen(tmp_path: pathlib.Path) -> AlmacenObjetos:
    return AlmacenObjetos(base_uri="file://objetos-de-prueba", directorio=tmp_path / "objetos")


@pytest.fixture
def archivo(tmp_path: pathlib.Path) -> pathlib.Path:
    ruta = tmp_path / "resolucion.pdf"
    ruta.write_bytes(b"%PDF-1.4 contenido de la resolucion")
    return ruta


@pytest.fixture
def cargador(conexion: Connection, almacen: AlmacenObjetos) -> CargaManual:
    cargar_catalogo(conexion)
    return CargaManual(conexion, almacen=almacen)


def _cargar(cargador: CargaManual, archivo: pathlib.Path, fuente: str = "F42", **extra):
    parametros = {
        "actor": ACTOR,
        "procedencia": PROCEDENCIA,
        "obtenido_en": dt.date(2026, 3, 3),
    }
    parametros.update(extra)
    return cargador.cargar(fuente, archivo, **parametros)


# --- Lo que se exige declarar --------------------------------------------------


def test_sin_decir_quien_carga_no_se_carga(cargador, archivo) -> None:
    """Una carga sin responsable no se puede repreguntar ni auditar."""
    with pytest.raises(ProcedenciaInsuficiente, match="quién carga"):
        _cargar(cargador, archivo, actor="   ")


def test_sin_decir_de_donde_salio_no_se_carga(cargador, archivo) -> None:
    """Un archivo sin procedencia es indistinguible de uno inventado."""
    with pytest.raises(ProcedenciaInsuficiente, match="de dónde salió"):
        _cargar(cargador, archivo, procedencia="pdf")


def test_un_archivo_que_no_existe_no_se_carga(cargador, tmp_path) -> None:
    with pytest.raises(ProcedenciaInsuficiente, match="No existe"):
        _cargar(cargador, tmp_path / "no-esta.pdf")


def test_una_fuente_fuera_del_catalogo_no_recibe_cargas(cargador, archivo) -> None:
    with pytest.raises(LookupError, match="no está en el catálogo"):
        _cargar(cargador, archivo, fuente="Z99")


# --- Lo que la carga deja --------------------------------------------------------


def test_la_carga_entra_por_la_misma_cadena_que_una_captura(
    cargador, archivo, conexion: Connection
) -> None:
    """Corrida, captura inmutable direccionada por contenido y de ahí el resto:
    lo manual no es un atajo que saltee la trazabilidad."""
    resultado = _cargar(cargador, archivo)
    fila = conexion.execute(
        text(
            "SELECT c.sha256_raw, c.objeto_uri, c.bytes, c.http_status, c.cabeceras, "
            "       c.capturado_en, ci.estado, ci.extractor_version "
            "  FROM capturas c JOIN corridas_ingesta ci ON ci.id = c.corrida_id "
            " WHERE c.id = :id"
        ),
        {"id": resultado.captura_id},
    ).one()
    assert fila.sha256_raw == resultado.sha256
    assert fila.objeto_uri.startswith("file://")
    assert fila.estado == "COMPLETA"
    assert fila.extractor_version == "carga-manual@1"


def test_no_se_finge_una_respuesta_http(cargador, archivo, conexion: Connection) -> None:
    """Poner 200 diría que el servidor contestó, y no contestó nadie."""
    resultado = _cargar(cargador, archivo)
    estado = conexion.execute(
        text("SELECT http_status FROM capturas WHERE id = :id"), {"id": resultado.captura_id}
    ).scalar_one()
    assert estado is None


def test_la_procedencia_viaja_con_la_captura(cargador, archivo, conexion: Connection) -> None:
    resultado = _cargar(cargador, archivo)
    cabeceras = conexion.execute(
        text("SELECT cabeceras FROM capturas WHERE id = :id"), {"id": resultado.captura_id}
    ).scalar_one()
    assert cabeceras["carga"] == "MANUAL"
    assert cabeceras["actor"] == ACTOR
    assert cabeceras["procedencia"] == PROCEDENCIA
    assert cabeceras["obtenido_en"] == "2026-03-03"


def test_la_fecha_de_captura_es_cuando_se_obtuvo_no_cuando_se_cargo(
    cargador, archivo, conexion: Connection
) -> None:
    """Si fuera la de la carga, un documento de marzo figuraría como de hoy y la
    frescura diría que es más nuevo de lo que es."""
    resultado = _cargar(cargador, archivo)
    capturado = conexion.execute(
        text("SELECT capturado_en FROM capturas WHERE id = :id"), {"id": resultado.captura_id}
    ).scalar_one()
    assert capturado.date() == dt.date(2026, 3, 3)


def test_sin_url_de_origen_no_se_inventa_una_http(cargador, archivo, conexion: Connection) -> None:
    """Las fuentes sin URL inequívoca son justamente las que más necesitan esta
    vía; darles una http que nadie puede visitar sería taparlas."""
    resultado = _cargar(cargador, archivo)
    url = conexion.execute(
        text(
            "SELECT u.url, u.tipo_acceso FROM fuente_urls u "
            "  JOIN capturas c ON c.source_url_id = u.id WHERE c.id = :id"
        ),
        {"id": resultado.captura_id},
    ).one()
    assert url.url.startswith("manual://")
    assert url.tipo_acceso == "CARGA_MANUAL"


def test_con_url_declarada_se_conserva_esa(cargador, archivo, conexion: Connection) -> None:
    resultado = _cargar(cargador, archivo, url_declarada="https://www.aysa.com.ar/documento.pdf")
    url = conexion.execute(
        text(
            "SELECT u.url FROM fuente_urls u JOIN capturas c ON c.source_url_id = u.id "
            " WHERE c.id = :id"
        ),
        {"id": resultado.captura_id},
    ).scalar_one()
    assert url == "https://www.aysa.com.ar/documento.pdf"


def test_la_fuente_queda_manual_y_no_activa(cargador, archivo, conexion: Connection) -> None:
    """Que alguien haya conseguido el archivo no significa que el sistema pueda
    recorrerla. Decir lo contrario haría que el monitor la dé por cubierta."""
    _cargar(cargador, archivo)
    fila = conexion.execute(
        text("SELECT estado, access_status, motivo_estado FROM fuentes WHERE source_id = 'F42'")
    ).one()
    assert fila.estado == "MANUAL"
    assert fila.access_status != "ACCESIBLE"
    assert "sigue sin poder recorrerse" in fila.motivo_estado


def test_la_carga_queda_en_la_bitacora(cargador, archivo, conexion: Connection) -> None:
    resultado = _cargar(cargador, archivo)
    fila = conexion.execute(
        text(
            "SELECT actor, accion, motivo FROM auditoria_eventos "
            " WHERE accion = 'CARGA_MANUAL' AND objeto_id = :id"
        ),
        {"id": str(resultado.captura_id)},
    ).one()
    assert fila.actor == ACTOR
    assert PROCEDENCIA in fila.motivo


def test_cargar_el_mismo_archivo_dos_veces_no_duplica_el_objeto(
    cargador, archivo, conexion: Connection
) -> None:
    """El almacén es direccionado por contenido: el mismo archivo es el mismo
    objeto, aunque lo carguen dos personas distintas."""
    primera = _cargar(cargador, archivo)
    segunda = _cargar(cargador, archivo, actor="ingesta:otra-persona")
    assert primera.sha256 == segunda.sha256
    assert primera.ya_existia is False
    assert segunda.ya_existia is True
    assert primera.captura_id != segunda.captura_id


# --- El listado que la justifica --------------------------------------------------


def test_el_listado_de_bloqueadas_dice_por_que_lo_estan(conexion: Connection) -> None:
    cargar_catalogo(conexion)
    filas = fuentes_bloqueadas(conexion)
    assert filas, "El catálogo tiene fuentes sin URL inequívoca."
    assert all(f["access_status"] != "ACCESIBLE" for f in filas)
    assert all(f["responsable_rol"] for f in filas)
