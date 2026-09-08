"""HU-003 y HU-004: configuración versionada y capturas inmutables.

Se usa un cliente de prueba en lugar de la red: lo que se verifica es cómo el
capturador trata cada respuesta, no si un sitio está en pie hoy.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.almacen import AlmacenObjetos, sha256_de
from backend_normativo.ingesta.capturador import Capturador, PermisoDePoliticaDenegado
from backend_normativo.ingesta.cliente import Descarga
from backend_normativo.ingesta.planificador import fuentes_pendientes

pytestmark = pytest.mark.integracion


class ClienteDePrueba:
    """Devuelve respuestas preparadas y registra qué se le pidió."""

    def __init__(self, respuestas: dict[str, list[Descarga]]) -> None:
        self.respuestas = {url: list(rs) for url, rs in respuestas.items()}
        self.pedidos: list[tuple[str, str | None, str | None]] = []

    def descargar(self, url: str, *, etag=None, last_modified=None, presupuesto=None) -> Descarga:
        self.pedidos.append((url, etag, last_modified))
        cola = self.respuestas.get(url)
        if not cola:
            return _descarga(url, status=404, error="HTTP 404")
        return cola.pop(0) if len(cola) > 1 else cola[0]


def _descarga(
    url: str,
    *,
    status: int | None = 200,
    contenido: bytes = b"<html>contenido</html>",
    mime: str | None = "text/html",
    etag: str | None = None,
    last_modified: str | None = None,
    error: str | None = None,
    acceso_limitado: bool = False,
    error_tls: bool = False,
) -> Descarga:
    return Descarga(
        url_solicitada=url,
        url_final=url,
        http_status=status,
        contenido=contenido,
        mime=mime,
        etag=etag,
        last_modified=last_modified,
        cabeceras={"content-type": mime} if mime else {},
        capturado_en=datetime.now(UTC),
        error=error,
        acceso_limitado=acceso_limitado,
        error_tls=error_tls,
    )


@pytest.fixture
def almacen(tmp_path) -> AlmacenObjetos:
    return AlmacenObjetos(base_uri="file://objetos-de-prueba", directorio=tmp_path / "objetos")


@pytest.fixture
def catalogo(conexion: Connection):
    return cargar_catalogo(conexion)


def _url_de(conexion: Connection, source_id: str) -> str:
    return conexion.execute(
        text("SELECT url FROM fuente_urls WHERE source_id = :s ORDER BY es_canonica DESC LIMIT 1"),
        {"s": source_id},
    ).scalar_one()


# --- Almacén ------------------------------------------------------------------


def test_el_almacen_direcciona_por_contenido(almacen: AlmacenObjetos) -> None:
    """Dos capturas idénticas comparten objeto: guardar de nuevo no duplica."""
    datos = b"texto de una norma"
    primero = almacen.guardar(datos)
    segundo = almacen.guardar(datos)

    assert primero.sha256 == sha256_de(datos)
    assert primero.uri == segundo.uri
    assert primero.ya_existia is False
    assert segundo.ya_existia is True
    assert almacen.leer(primero.sha256) == datos


def test_el_uri_no_es_una_ruta_local(almacen: AlmacenObjetos) -> None:
    """La base guarda un URI con esquema, no una ruta que solo exista en la
    máquina de un agente."""
    objeto = almacen.guardar(b"x")
    assert objeto.uri.startswith("file://")
    assert str(almacen.directorio) not in objeto.uri


# --- Capturas -----------------------------------------------------------------


def test_una_captura_guarda_bytes_hash_y_procedencia(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    url = _url_de(conexion, "D01")
    contenido = b"<html>Decreto 1382/2001</html>"
    cliente = ClienteDePrueba({url: [_descarga(url, contenido=contenido, etag='"v1"')]})

    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    assert resultado.estado.value == "COMPLETA"
    fila = conexion.execute(
        text(
            "SELECT sha256_raw, bytes, mime, http_status, objeto_uri, etag "
            "FROM capturas WHERE id = :id"
        ),
        {"id": resultado.capturas[0]},
    ).one()
    assert fila.sha256_raw == sha256_de(contenido)
    assert fila.bytes == len(contenido)
    assert fila.mime == "text/html"
    assert fila.etag == '"v1"'
    assert almacen.leer(fila.sha256_raw) == contenido


def test_la_revalidacion_reutiliza_el_objeto_previo(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """AT: un 304 no inventa un cuerpo descargado. Reutiliza el objeto y el hash
    de la captura anterior y deja constancia de cuál."""
    url = _url_de(conexion, "D01")
    contenido = b"<html>original</html>"
    cliente = ClienteDePrueba(
        {
            url: [
                _descarga(url, contenido=contenido, etag='"v1"'),
                _descarga(url, status=304, contenido=b"", mime=None, etag='"v1"'),
            ]
        }
    )
    capturador = Capturador(conexion, cliente=cliente, almacen=almacen)

    primera = capturador.capturar_fuente("D01")
    segunda = capturador.capturar_fuente("D01")

    assert segunda.no_modificadas == 1
    # La segunda solicitud llevó el validador de la primera.
    assert cliente.pedidos[1][1] == '"v1"'

    revalidacion = conexion.execute(
        text(
            "SELECT http_status, sha256_raw, objeto_uri, bytes, captura_previa_id "
            "FROM capturas WHERE id = :id"
        ),
        {"id": segunda.capturas[0]},
    ).one()
    assert revalidacion.http_status == 304
    assert revalidacion.sha256_raw == sha256_de(contenido)
    assert revalidacion.captura_previa_id == primera.capturas[0]
    # Un solo objeto en el almacén: la revalidación no transfirió nada.
    assert len(list(almacen.directorio.rglob("*"))) >= 1


def test_los_bytes_de_una_captura_no_se_editan(
    conexion: Connection, catalogo, almacen: AlmacenObjetos, viola_restriccion
) -> None:
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url)]})
    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    with viola_restriccion("inmutable"):
        conexion.execute(
            text("UPDATE capturas SET bytes = 0 WHERE id = :id"), {"id": resultado.capturas[0]}
        )


def test_no_se_guardan_cookies_ni_credenciales(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Las cabeceras conservadas describen el recurso, no la sesión."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url, etag='"v1"')]})
    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    cabeceras = conexion.execute(
        text("SELECT cabeceras FROM capturas WHERE id = :id"), {"id": resultado.capturas[0]}
    ).scalar_one()
    claves = {k.lower() for k in (cabeceras or {})}
    assert not (claves & {"set-cookie", "cookie", "authorization"})


# --- Política -----------------------------------------------------------------


def test_un_403_pausa_la_fuente_y_no_la_deja_como_sin_datos(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Un rechazo no se convierte en "no hay datos": degrada la fuente y abre
    una incidencia con responsable."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba(
        {url: [_descarga(url, status=403, error="HTTP 403", acceso_limitado=True)]}
    )

    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    assert resultado.estado.value == "FALLIDA"
    assert resultado.rechazadas == 1
    fuente = conexion.execute(
        text("SELECT estado, access_status, motivo_estado FROM fuentes WHERE source_id = 'D01'")
    ).one()
    assert fuente.estado == "DEGRADED"
    assert fuente.access_status == "ACCESO_LIMITADO"
    assert "no se rotan identidades" in fuente.motivo_estado

    incidencia = conexion.execute(
        text(
            "SELECT tipo, severidad, estado, responsable_rol FROM incidencias_revision "
            "WHERE source_id = 'D01' AND tipo = 'ACCESO_BLOQUEADO'"
        )
    ).one()
    assert (incidencia.estado, incidencia.severidad) == ("ABIERTA", "HIGH")
    assert incidencia.responsable_rol == "ingesta"


def test_un_fallo_de_tls_no_relaja_la_validacion(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba(
        {
            url: [
                _descarga(
                    url,
                    status=None,
                    contenido=b"",
                    mime=None,
                    error="Fallo de validación TLS: certificado no cubre el host",
                    error_tls=True,
                )
            ]
        }
    )

    Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    fuente = conexion.execute(
        text("SELECT access_status, motivo_estado FROM fuentes WHERE source_id = 'D01'")
    ).one()
    assert fuente.access_status == "ERROR_TLS"
    assert "no se relaja la validación de tls" in fuente.motivo_estado.lower()
    # No quedó ninguna captura: no hay bytes que acreditar.
    assert conexion.execute(text("SELECT count(*) FROM capturas")).scalar_one() == 0


def test_una_fuente_sin_url_no_se_automatiza(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """F13 no tiene dirección conocida: su política lo dice y el capturador la
    respeta en vez de inventar una."""
    cliente = ClienteDePrueba({})
    with pytest.raises(PermisoDePoliticaDenegado, match="no se automatiza"):
        Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("F13")


def test_una_corrida_con_rechazos_no_figura_completa(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Los contadores reconcilian y el estado dice la verdad."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url, status=500, error="HTTP 500")]})

    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    fila = conexion.execute(
        text(
            "SELECT estado, solicitadas, descargadas, procesadas, rechazadas, fin "
            "FROM corridas_ingesta WHERE id = :id"
        ),
        {"id": resultado.corrida_id},
    ).one()
    assert fila.estado == "FALLIDA"
    assert (fila.solicitadas, fila.descargadas, fila.procesadas, fila.rechazadas) == (1, 0, 0, 1)
    assert fila.fin is not None


# --- Planificación ------------------------------------------------------------


def test_el_planificador_ignora_lo_que_no_se_puede_pedir(conexion: Connection, catalogo) -> None:
    """Sin URL no hay a quién pedirle, y una fuente retirada o de referencia no
    se reintenta sola."""
    pendientes = {f.source_id for f in fuentes_pendientes(conexion)}

    sin_url = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT source_id FROM fuentes WHERE access_status = 'SIN_URL_CONOCIDA'")
        )
    }
    no_capturables = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT source_id FROM fuentes WHERE estado IN ('RETIRED', 'REFERENCE_ONLY')")
        )
    }
    assert pendientes & sin_url == set()
    assert pendientes & no_capturables == set()
    assert "D01" in pendientes


def test_una_fuente_recien_capturada_deja_de_estar_pendiente(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url)]})
    Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    pendientes = {f.source_id for f in fuentes_pendientes(conexion)}
    assert "D01" not in pendientes

    # Pasada la frecuencia, vuelve a la cola: revisar de nuevo no es opcional.
    futuro = datetime(2027, 1, 1, tzinfo=UTC)
    assert "D01" in {f.source_id for f in fuentes_pendientes(conexion, ahora=futuro)}
