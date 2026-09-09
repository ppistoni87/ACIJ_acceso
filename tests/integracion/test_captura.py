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
            "SELECT http_status, sha256_raw, objeto_uri, bytes, mime, captura_previa_id "
            "FROM capturas WHERE id = :id"
        ),
        {"id": segunda.capturas[0]},
    ).one()
    assert revalidacion.http_status == 304
    assert revalidacion.sha256_raw == sha256_de(contenido)
    assert revalidacion.captura_previa_id == primera.capturas[0]
    # Un 304 no trae Content-Type porque no trae cuerpo, y el tipo es uno de los
    # datos que P-004 pide conservar por captura. Se hereda de la captura cuyos
    # bytes se reutilizan: si no, revalidar borraría el tipo que ya se sabía.
    assert revalidacion.mime == "text/html"
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


def test_una_corrida_fallida_dice_por_que_fallo(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """El motivo vive en la fila de la corrida, no solo en otra tabla.

    Un reporte por fuente lee `corridas_ingesta`. Si ahí dice FALLIDA y nada más,
    el que lo lee tiene que salir a buscar el motivo a mano, y una corrida sin
    motivo es indistinguible de una fuente que no tenía nada para dar.
    """
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url, status=403, error="HTTP 403")]})

    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    detalle = conexion.execute(
        text("SELECT detalle_error FROM corridas_ingesta WHERE id = :id"),
        {"id": resultado.corrida_id},
    ).scalar_one()
    assert detalle is not None
    assert "403" in detalle
    assert detalle == " | ".join(resultado.incidencias)


def test_una_corrida_completa_no_inventa_un_error(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Sin fallo no hay detalle: un campo de error con texto en una corrida que
    anduvo bien haría ruido en cualquier tablero que filtre por él."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url, contenido=b"<html>ok</html>")]})

    resultado = Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    fila = conexion.execute(
        text("SELECT estado, detalle_error FROM corridas_ingesta WHERE id = :id"),
        {"id": resultado.corrida_id},
    ).one()
    assert fila.estado == "COMPLETA"
    assert fila.detalle_error is None


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


def test_un_certificado_que_no_valida_se_reconoce_como_fallo_de_tls() -> None:
    """httpx envuelve el error de TLS en un `ConnectError`. Sin reconocerlo, un
    certificado que no cubre al host se archiva como «no se pudo conectar» y la
    fuente queda como si nadie la hubiera visitado."""
    import httpx

    from backend_normativo.ingesta.cliente import _es_fallo_tls

    assert _es_fallo_tls(
        httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get "
            "local issuer certificate (_ssl.c:1016)"
        )
    )
    assert not _es_fallo_tls(httpx.ConnectError("All connection attempts failed"))


def test_un_404_no_deja_la_fuente_como_sin_visitar(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Un recurso que no está y uno que nadie miró no son lo mismo. Dejar la
    fuente en NO_VERIFICADO después de un 404 es convertir un error en «sin
    datos»: el reporte de cobertura diría que está sin empezar."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba({url: [_descarga(url, status=404, error="HTTP 404")]})
    Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    fila = conexion.execute(
        text("SELECT estado, access_status, motivo_estado FROM fuentes WHERE source_id = 'D01'")
    ).one()
    assert fila.access_status == "NO_ENCONTRADA"
    assert fila.estado == "DEGRADED"
    assert "ya no está en esa dirección" in fila.motivo_estado


# --- AT-007: un 404 que trae una página HTML extensa -------------------------

# El cuerpo que devuelven los portales cuando la URL ya no existe: una página
# completa, con navegación y buscador, que se lee como cualquier otro HTML.
PAGINA_DE_ERROR = (
    b"<html><head><title>Pagina no encontrada</title></head><body><main>"
    b"<h1>La pagina que buscas no existe</h1>"
    b"<p>Es posible que el contenido haya sido movido o dado de baja. "
    b"Te sugerimos volver al inicio o usar el buscador del sitio para encontrar "
    b"lo que necesitas. Tambien podes consultar las secciones destacadas.</p>"
    b"<nav><a href='/'>Inicio</a><a href='/tramites'>Tramites</a></nav>"
    b"</main></body></html>"
)


def test_at007_un_404_con_pagina_extensa_no_produce_ninguna_norma(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """La página de error se lee como cualquier HTML: si se extrajera, el corpus
    tendría un documento que dice «la página que buscás no existe»."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba(
        {url: [_descarga(url, status=404, contenido=PAGINA_DE_ERROR, error="HTTP 404")]}
    )
    Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    from backend_normativo.ingesta.extraccion import Extractor

    Extractor(conexion, almacen=almacen).extraer_pendientes("D01")

    assert (
        conexion.execute(
            text(
                "SELECT count(*) FROM documento_versiones dv "
                "  JOIN documentos d ON d.id = dv.documento_id WHERE d.source_id = 'D01'"
            )
        ).scalar_one()
        == 0
    )
    assert conexion.execute(text("SELECT count(*) FROM normas")).scalar_one() == 0


def test_at007_la_captura_del_error_se_conserva_con_su_status(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Es la prueba de qué contestó esa URL, y permite notar cuándo deja de
    contestar eso."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba(
        {url: [_descarga(url, status=404, contenido=PAGINA_DE_ERROR, error="HTTP 404")]}
    )
    Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    fila = (
        conexion.execute(
            text(
                "SELECT c.http_status, c.bytes, c.sha256_raw FROM capturas c "
                "  JOIN fuente_urls u ON u.id = c.source_url_id WHERE u.source_id = 'D01'"
            )
        )
        .mappings()
        .one()
    )
    assert fila["http_status"] == 404
    assert fila["bytes"] == len(PAGINA_DE_ERROR)
    assert almacen.leer(fila["sha256_raw"]) == PAGINA_DE_ERROR


def test_at007_la_corrida_no_figura_completa_para_contenido(
    conexion: Connection, catalogo, almacen: AlmacenObjetos
) -> None:
    """Descargar la página de error no es haber conseguido el contenido."""
    url = _url_de(conexion, "D01")
    cliente = ClienteDePrueba(
        {url: [_descarga(url, status=404, contenido=PAGINA_DE_ERROR, error="HTTP 404")]}
    )
    Capturador(conexion, cliente=cliente, almacen=almacen).capturar_fuente("D01")

    fila = (
        conexion.execute(
            text(
                "SELECT estado, solicitadas, descargadas, rechazadas FROM corridas_ingesta "
                " WHERE source_id = 'D01' ORDER BY inicio DESC LIMIT 1"
            )
        )
        .mappings()
        .one()
    )
    assert fila["estado"] != "COMPLETA"
    assert fila["rechazadas"] == 1
    assert fila["descargadas"] == 0
