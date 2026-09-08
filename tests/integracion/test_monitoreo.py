"""HU-026, HU-027 y HU-028: diferencias, impacto y entrega de eventos."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.monitoreo.diff import comparar_versiones
from backend_normativo.monitoreo.impacto import propagar
from backend_normativo.monitoreo.outbox import INTENTOS_MAXIMOS, entregar_pendientes
from tests.integracion.test_curacion import _documento_norma

pytestmark = pytest.mark.integracion


def _version(conexion: Connection, *, sufijo: str, unidades) -> uuid.UUID:
    _documento_norma(
        conexion,
        source_id="D06",
        external_id="normativaba:830431:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "830431",
            "tipo": "LEY",
            "numero": "6935",
            "anio": 2025,
            "titulo": "PROGRAMA DE APOYO",
        },
        unidades=unidades,
        sufijo_url=sufijo,
    )
    return conexion.execute(
        text("SELECT id FROM documento_versiones ORDER BY creado_en DESC LIMIT 1")
    ).scalar_one()


def _segunda_version(conexion: Connection, documento_id, *, unidades) -> uuid.UUID:
    """Otra versión del mismo documento, como haría una recaptura."""
    captura = conexion.execute(
        text("SELECT captura_id FROM documento_versiones WHERE documento_id = :d LIMIT 1"),
        {"d": documento_id},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            " tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, 2, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba') RETURNING id"
        ),
        {"d": documento_id, "c": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()
    for orden, (tipo, numero, texto_unidad, rol) in enumerate(unidades, start=1):
        conexion.execute(
            text(
                "INSERT INTO unidades_documentales "
                "(doc_version_id, tipo, numero, ruta, orden, texto, rol_contenido) "
                "VALUES (:dv, :t, :n, :ruta, :o, :texto, :rol)"
            ),
            {
                "dv": version,
                "t": tipo,
                "n": numero,
                "ruta": f"{tipo.lower()}-{numero or orden}",
                "o": orden,
                "texto": texto_unidad,
                "rol": rol,
            },
        )
    return version


def _evidencia_de_la_primera_unidad(conexion: Connection) -> uuid.UUID:
    """Evidencia mínima sobre una unidad ya cargada, para respaldar una relación."""
    fila = conexion.execute(
        text("SELECT id, doc_version_id, texto FROM unidades_documentales LIMIT 1")
    ).one()
    return conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, hash_fragmento, "
            " tipo) VALUES (:dv, :u, :f, :h, 'FRAGMENTO_TEXTO') RETURNING id"
        ),
        {
            "dv": fila.doc_version_id,
            "u": fila.id,
            "f": fila.texto,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
        },
    ).scalar_one()


@pytest.fixture
def catalogo(conexion: Connection):
    return cargar_catalogo(conexion)


# --- Diferencias ------------------------------------------------------------


def test_la_primera_version_no_tiene_con_que_compararse(conexion: Connection, catalogo) -> None:
    version = _version(
        conexion,
        sufijo="/v1",
        unidades=[("ARTICULO", "1", "Artículo 1° - Texto original.", "DISPOSITIVO")],
    )
    diferencia = comparar_versiones(conexion, version)
    assert diferencia is not None
    assert diferencia.version_anterior is None
    assert diferencia.hay_cambios is False


def test_el_diff_dice_qué_unidad_cambió_y_cuánto(conexion: Connection, catalogo) -> None:
    primera = _version(
        conexion,
        sufijo="/v1",
        unidades=[
            ("ARTICULO", "1", "Artículo 1° - La prestación será mensual.", "DISPOSITIVO"),
            ("ARTICULO", "2", "Artículo 2° - Comuníquese.", "DISPOSITIVO"),
        ],
    )
    documento = conexion.execute(
        text("SELECT documento_id FROM documento_versiones WHERE id = :v"), {"v": primera}
    ).scalar_one()
    segunda = _segunda_version(
        conexion,
        documento,
        unidades=[
            ("ARTICULO", "1", "Artículo 1° - La prestación será bimestral.", "DISPOSITIVO"),
            ("ARTICULO", "3", "Artículo 3° - Disposición nueva.", "DISPOSITIVO"),
        ],
    )

    diferencia = comparar_versiones(conexion, segunda)
    assert diferencia.hay_cambios
    assert diferencia.resumen == {"MODIFICADA": 1, "ELIMINADA": 1, "AGREGADA": 1}

    modificada = next(c for c in diferencia.cambios if c.clase == "MODIFICADA")
    assert modificada.ruta == "articulo-1"
    assert "bimestral" in modificada.despues
    assert 0.5 < modificada.similitud < 1.0


def test_una_nota_editorial_no_cuenta_como_cambio_de_la_norma(
    conexion: Connection, catalogo
) -> None:
    """Tratar un cambio de nota como cambio normativo llenaría de ruido la cola
    de revisión."""
    primera = _version(
        conexion,
        sufijo="/v1",
        unidades=[
            ("ARTICULO", "1", "Artículo 1° - Texto.", "DISPOSITIVO"),
            ("NO_RECONOCIDO", None, "( Nota Infoleg : ver resoluciones )", "NOTA"),
        ],
    )
    documento = conexion.execute(
        text("SELECT documento_id FROM documento_versiones WHERE id = :v"), {"v": primera}
    ).scalar_one()
    segunda = _segunda_version(
        conexion,
        documento,
        unidades=[
            ("ARTICULO", "1", "Artículo 1° - Texto.", "DISPOSITIVO"),
            ("NO_RECONOCIDO", None, "( Nota Infoleg : otra redacción distinta )", "NOTA"),
        ],
    )
    assert comparar_versiones(conexion, segunda).hay_cambios is False


# --- Impacto ----------------------------------------------------------------


def test_el_impacto_alcanza_a_las_normas_que_la_citan(conexion: Connection, catalogo) -> None:
    _version(
        conexion,
        sufijo="/a",
        unidades=[("ARTICULO", "1", "Artículo 1° - Texto.", "DISPOSITIVO")],
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    norma_id = conexion.execute(text("SELECT id FROM normas LIMIT 1")).scalar_one()

    otra = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR-C', 'DECRETO', '999', 2026, 'Reglamenta') RETURNING id"
        )
    ).scalar_one()
    evidencia = _evidencia_de_la_primera_unidad(conexion)
    conexion.execute(
        text(
            "INSERT INTO relaciones_normativas "
            "(norma_origen_id, norma_destino_id, evidencia_id, tipo, estado_revision) "
            "VALUES (:o, :d, :e, 'REGLAMENTA', 'CANDIDATE')"
        ),
        {"o": otra, "d": norma_id, "e": evidencia},
    )

    impacto = propagar(
        conexion, norma_id, motivo="La fuente publicó un texto distinto.", idempotency_key="x1"
    )
    assert impacto.normas_dependientes == ["DECRETO 999/2026"]
    assert impacto.eventos_emitidos == 1


def test_un_cambio_vence_la_frescura_de_las_versiones_alcanzadas(
    conexion: Connection, catalogo
) -> None:
    """Seguir sirviendo un dato como fresco después de que su norma cambió es
    servir un dato vencido."""
    _version(
        conexion,
        sufijo="/a",
        unidades=[("ARTICULO", "1", "Artículo 1° - Texto.", "DISPOSITIVO")],
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    norma_id = conexion.execute(text("SELECT id FROM normas LIMIT 1")).scalar_one()
    conexion.execute(
        text(
            "UPDATE registro_versiones SET reverificar_antes_de = '2099-01-01' "
            " WHERE entidad_id = :n"
        ),
        {"n": norma_id},
    )

    propagar(conexion, norma_id, motivo="Cambió el texto.", idempotency_key="x2")

    vencidas = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones "
            " WHERE entidad_id = :n AND reverificar_antes_de <= now()"
        ),
        {"n": norma_id},
    ).scalar_one()
    assert vencidas >= 1


def test_propagar_dos_veces_no_duplica_el_evento(conexion: Connection, catalogo) -> None:
    _version(
        conexion,
        sufijo="/a",
        unidades=[("ARTICULO", "1", "Artículo 1° - Texto.", "DISPOSITIVO")],
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    norma_id = conexion.execute(text("SELECT id FROM normas LIMIT 1")).scalar_one()

    propagar(conexion, norma_id, motivo="Cambió.", idempotency_key="misma-clave")
    propagar(conexion, norma_id, motivo="Cambió.", idempotency_key="misma-clave")

    assert conexion.execute(text("SELECT count(*) FROM eventos_outbox")).scalar_one() == 1


# --- Entrega ------------------------------------------------------------------


def _evento(conexion: Connection, clave: str = "evento-1") -> uuid.UUID:
    return conexion.execute(
        text(
            "INSERT INTO eventos_outbox (tipo, aggregate_id, payload, idempotency_key) "
            "VALUES ('NORMA_ACTUALIZADA', :agg, :payload, :clave) RETURNING id"
        ),
        {"agg": str(uuid.uuid4()), "payload": json.dumps({"x": 1}), "clave": clave},
    ).scalar_one()


def test_sin_consumidor_configurado_no_se_declara_ninguna_entrega(
    conexion: Connection, monkeypatch
) -> None:
    """No se afirma haber enviado un mensaje que nadie recibió."""
    monkeypatch.delenv("BN_OUTBOX_WEBHOOK", raising=False)
    _evento(conexion)
    resultado = entregar_pendientes(conexion)

    assert resultado.consumidor is None
    assert resultado.pendientes == 1
    assert resultado.entregados == 0
    assert any("No se declara ninguna entrega" in a for a in resultado.avisos)


def test_una_entrega_exitosa_lleva_la_clave_de_idempotencia(
    conexion: Connection, monkeypatch
) -> None:
    """La entrega es al menos una vez: el consumidor descarta duplicados."""
    monkeypatch.setenv("BN_OUTBOX_WEBHOOK", "https://consumidor.example/eventos")
    _evento(conexion, clave="clave-unica")

    recibidas: list[dict] = []

    def responder(solicitud: httpx.Request) -> httpx.Response:
        recibidas.append(dict(solicitud.headers))
        return httpx.Response(204)

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    resultado = entregar_pendientes(conexion, cliente=cliente)

    assert resultado.entregados == 1
    assert recibidas[0]["idempotency-key"] == "clave-unica"
    entregado = conexion.execute(text("SELECT entregado_en, intentos FROM eventos_outbox")).one()
    assert entregado.entregado_en is not None
    assert entregado.intentos == 1


def test_una_entrega_fallida_no_marca_el_evento_como_entregado(
    conexion: Connection, monkeypatch
) -> None:
    monkeypatch.setenv("BN_OUTBOX_WEBHOOK", "https://consumidor.example/eventos")
    _evento(conexion)

    cliente = httpx.Client(
        transport=httpx.MockTransport(lambda _s: httpx.Response(500, text="caído"))
    )
    resultado = entregar_pendientes(conexion, cliente=cliente)

    assert resultado.entregados == 0
    assert resultado.fallidos == 1
    fila = conexion.execute(
        text("SELECT entregado_en, intentos, ultimo_error FROM eventos_outbox")
    ).one()
    assert fila.entregado_en is None
    assert fila.intentos == 1
    assert "500" in fila.ultimo_error


def test_un_evento_que_agoto_los_intentos_pasa_a_la_cola_de_fallos(
    conexion: Connection, monkeypatch
) -> None:
    """Deja de reintentarse solo: es trabajo de operación, no ruido de cada
    corrida."""
    monkeypatch.setenv("BN_OUTBOX_WEBHOOK", "https://consumidor.example/eventos")
    evento = _evento(conexion)
    conexion.execute(
        text("UPDATE eventos_outbox SET intentos = :n WHERE id = :id"),
        {"n": INTENTOS_MAXIMOS, "id": evento},
    )

    cliente = httpx.Client(transport=httpx.MockTransport(lambda _s: httpx.Response(500)))
    resultado = entregar_pendientes(conexion, cliente=cliente)

    assert resultado.entregados == 0
    assert resultado.fallidos == 0
    assert resultado.en_cola_de_fallos == 1
