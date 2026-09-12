"""La fecha de verificación sale de la captura, o no sale.

Es la pieza que faltaba para que el dato operativo pudiera publicarse: estaba
aprobado desde hacía tiempo y sin fecha, y la base se negaba —con razón— a
servir algo cuyo respaldo nadie fechó. Lo que se prueba acá es que la fecha
diga la verdad: que salga del snapshot y nunca del reloj de la corrida.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion.verificacion import DIAS_DE_FRESCURA, fechar_desde_la_captura

pytestmark = pytest.mark.integracion

HACE_DOS_ANIOS = dt.datetime(2024, 9, 8, 12, 0, tzinfo=dt.UTC)


def _canal_sin_fecha(conexion: Connection, corpus, *, capturado_en=None) -> str:
    """Un canal aprobado, sin fecha de verificación, con o sin captura detrás."""
    evidencia = None
    if capturado_en is not None:
        # Una captura propia con la fecha que la prueba quiere.
        captura = conexion.execute(
            text(
                "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, "
                " capturado_en, sha256_raw, sha256_semantico, objeto_uri) "
                "SELECT c.corrida_id, c.source_url_id, c.url_final, 200, :cuando, :h, :h, "
                "       c.objeto_uri FROM capturas c LIMIT 1 RETURNING id"
            ),
            {"cuando": capturado_en, "h": uuid.uuid4().hex + uuid.uuid4().hex},
        ).scalar_one()
        doc_version = conexion.execute(
            text(
                "INSERT INTO documento_versiones (documento_id, captura_id, version, "
                " tipo_version, texto_extraido, hash_texto, modo_extraccion, extractor_version, "
                " fecha_documento, tipo_fecha) "
                "SELECT dv.documento_id, :cap, dv.version + 100, 'ORIGINAL', 'texto', :h, "
                "       dv.modo_extraccion, dv.extractor_version, DATE '2024-09-08', "
                "       'PUBLICACION' FROM documento_versiones dv LIMIT 1 RETURNING id"
            ),
            {"cap": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
        ).scalar_one()
        evidencia = conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, fragmento, hash_fragmento, tipo) "
                "VALUES (:dv, 'Teléfono 4000-0000', :h, 'FRAGMENTO_TEXTO') RETURNING id"
            ),
            {"dv": doc_version, "h": uuid.uuid4().hex + uuid.uuid4().hex},
        ).scalar_one()

    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'PRESTADOR') RETURNING id"
        ),
        {"n": f"Organismo {uuid.uuid4().hex[:6]}"},
    ).scalar_one()
    # Un disparador exige que `entidad_id` sea el identificador del subtipo, no
    # otro cualquiera: la versión y la fila del canal tienen que hablar del mismo.
    canal_id = uuid.uuid4()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde) "
            "VALUES ('canal', :e, 1, 'APPROVED', 'ABIERTO_FIN', DATE '2025-01-01') RETURNING id"
        ),
        {"e": canal_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO canales (registro_version_id, canal_id, organismo_id, evidencia_id, "
            " tipo, valor_crudo, publico) "
            "VALUES (:rv, :c, :o, :e, 'TELEFONO', '4000-0000', true)"
        ),
        {"rv": version, "c": canal_id, "o": organismo, "e": evidencia},
    )
    return version


def _fecha(conexion: Connection, version_id):
    return conexion.execute(
        text("SELECT verificado_en, reverificar_antes_de FROM registro_versiones WHERE id = :v"),
        {"v": version_id},
    ).one()


def test_la_fecha_sale_de_la_captura_y_no_del_reloj_de_la_corrida(
    conexion: Connection, corpus
) -> None:
    """El fallo que no falla: sellar con `now()` convertiría un dato de hace dos
    años en uno de hoy con una sola ejecución, y quedaría todo en verde."""
    version = _canal_sin_fecha(conexion, corpus, capturado_en=HACE_DOS_ANIOS)

    fechar_desde_la_captura(conexion, actor="prueba", tipos=["canal"])

    verificado, _ = _fecha(conexion, version)
    assert verificado == HACE_DOS_ANIOS


def test_una_captura_vieja_nace_vencida_en_vez_de_estrenarse_fresca(
    conexion: Connection, corpus
) -> None:
    """El horizonte también sale de la captura: captura más treinta días, no hoy
    más treinta."""
    version = _canal_sin_fecha(conexion, corpus, capturado_en=HACE_DOS_ANIOS)

    fechar_desde_la_captura(conexion, actor="prueba", tipos=["canal"])

    _, refrescar = _fecha(conexion, version)
    assert refrescar == HACE_DOS_ANIOS + dt.timedelta(days=DIAS_DE_FRESCURA)
    assert refrescar < dt.datetime.now(dt.UTC), "una captura de hace dos años ya venció"


def test_lo_que_no_llega_a_una_captura_no_se_sella_y_se_cuenta(
    conexion: Connection, corpus
) -> None:
    """Ponerle una fecha a algo sin snapshot detrás sería inventarla.

    Un canal no puede quedar huérfano —el esquema le exige evidencia—, pero un
    punto de atención sí: llega a la captura por sus canales, y puede no tener
    ninguno. Ese es el caso que este módulo tiene que dejar sin sellar.
    """
    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'PRESTADOR') RETURNING id"
        ),
        {"n": f"Organismo {uuid.uuid4().hex[:6]}"},
    ).scalar_one()
    punto = conexion.execute(
        text(
            "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, alcance) "
            "VALUES (:o, 'AR-C', 'Sede sin ningún canal', 'SEDE', 'PROVINCIAL') RETURNING id"
        ),
        {"o": organismo},
    ).scalar_one()
    huerfano = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde) "
            "VALUES ('punto_atencion', :p, 1, 'APPROVED', 'ABIERTO_FIN', DATE '2025-01-01') "
            "RETURNING id"
        ),
        {"p": punto},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_legible, "
            " es_presencial) VALUES (:v, :p, 'Una dirección', true)"
        ),
        {"v": huerfano, "p": punto},
    )

    resultado = fechar_desde_la_captura(conexion, actor="prueba", tipos=["punto_atencion"])

    verificado, _ = _fecha(conexion, huerfano)
    assert verificado is None, "sin canales no hay captura, y sin captura no hay fecha"
    assert resultado.sin_captura["punto_atencion"] >= 1


def test_simular_no_escribe_nada_y_dice_cuanto_haria(conexion: Connection, corpus) -> None:
    version = _canal_sin_fecha(conexion, corpus, capturado_en=HACE_DOS_ANIOS)

    resultado = fechar_desde_la_captura(conexion, actor="prueba", tipos=["canal"], simular=True)

    assert resultado.simulado
    assert resultado.sellados["canal"] >= 1
    assert _fecha(conexion, version)[0] is None


def test_cada_version_sellada_deja_su_rastro(conexion: Connection, corpus) -> None:
    """Lo que se sella de a miles tiene que poder auditarse de a una."""
    version = _canal_sin_fecha(conexion, corpus, capturado_en=HACE_DOS_ANIOS)

    fechar_desde_la_captura(conexion, actor="curacion:quien-sea", tipos=["canal"])

    fila = conexion.execute(
        text(
            "SELECT actor, accion, motivo FROM auditoria_eventos "
            " WHERE objeto = 'registro_version' AND objeto_id = CAST(:v AS text)"
        ),
        {"v": version},
    ).one()
    assert fila.actor == "curacion:quien-sea"
    assert fila.accion == "FECHAR_VERIFICACION"
    # El rastro dice qué significa la fecha, no sólo que se puso.
    assert "no que el lugar esté abierto" in fila.motivo


def test_no_se_vuelve_a_sellar_lo_que_ya_tiene_fecha(conexion: Connection, corpus) -> None:
    """Correrlo dos veces no puede rejuvenecer nada."""
    version = _canal_sin_fecha(conexion, corpus, capturado_en=HACE_DOS_ANIOS)
    fechar_desde_la_captura(conexion, actor="prueba", tipos=["canal"])

    segunda = fechar_desde_la_captura(conexion, actor="prueba", tipos=["canal"])

    assert segunda.sellados["canal"] == 0
    assert _fecha(conexion, version)[0] == HACE_DOS_ANIOS
