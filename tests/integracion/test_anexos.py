"""HU-F19 · AT-029: el procedimiento vive en el anexo, no en el cuerpo.

La Resolución 1621/MEDGC/25 no dice cómo se pide una beca. Su artículo 3 aprueba
un anexo —«identificado como Anexo (IF-2025-53544032-GCABA-SSGDA) el cual forma
parte integrante de la presente»— y ahí están las etapas y los plazos.

Publicar «no informa plazos» leyendo sólo el cuerpo es tan falso como publicar
plazos inventados: la resolución sí los fija, en un documento que hay que ir a
buscar.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.anexos import CuradorDeAnexos, remisiones_en

pytestmark = pytest.mark.integracion

# Texto real del artículo 3 de la Resolución 1621/MEDGC/25, partido en unidades
# como lo parte el extractor: la remisión empieza en el artículo y termina dos
# párrafos después.
CUERPO = [
    ("articulo-1", "Artículo 1°.- Dejar sin efecto las Resoluciones 1293-MEGC/09 y 62-SSIECE/13."),
    (
        "articulo-3",
        'Artículo 3°.- Aprobar los "Procedimientos para el otorgamiento, control y evaluación del',
    ),
    ("articulo-3/parrafo-7", 'Régimen de Becas Estudiantiles de la Ley 2917", identificado'),
    (
        "articulo-3/parrafo-8",
        "como Anexo (IF-2025-\n53544032-GCABA-SSGDA) el cual forma parte integrante de la "
        "presente.",
    ),
]

ANEXO = [
    (
        "capitulo-1/articulo-1",
        "Etapa 1. La inscripción se realiza en la plataforma Becas Ciudad dentro de los "
        "treinta (30) días corridos de iniciado el ciclo lectivo.",
    ),
]


def _version(conexion: Connection, source_id: str, unidades, tipo="NORMA") -> uuid.UUID:
    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'ENTRADA', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"s": source_id, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES (:s, 99, 'HTML_ESTATICO') "
            "ON CONFLICT (source_id, version) DO UPDATE SET adaptador = 'HTML_ESTATICO' "
            "RETURNING id"
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
            "u": url_id,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://objetos/{uuid.uuid4()}",
        },
    ).scalar_one()
    documento = conexion.execute(
        text(
            "INSERT INTO documentos (source_id, tipo, external_id) VALUES (:s, :t, :e) RETURNING id"
        ),
        {"s": source_id, "t": tipo, "e": f"res:{uuid.uuid4()}"},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            " tipo_fecha, hash_texto, modo_extraccion, extractor_version, identidad_candidata) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba', :i) RETURNING id"
        ),
        {
            "d": documento,
            "c": captura,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "i": json.dumps({"tipo": "RESOLUCION", "numero": "1621", "anio": 2025}),
        },
    ).scalar_one()
    for orden, (ruta, contenido) in enumerate(unidades, start=1):
        conexion.execute(
            text(
                "INSERT INTO unidades_documentales "
                "(doc_version_id, tipo, numero, ruta, orden, texto, rol_contenido) "
                "VALUES (:dv, 'ARTICULO', :n, :ruta, :o, :texto, 'DISPOSITIVO')"
            ),
            {
                "dv": version,
                "n": str(orden),
                "ruta": ruta,
                "o": orden,
                "texto": contenido,
            },
        )
    return version


def _norma(conexion: Connection, doc_version: uuid.UUID, numero: str) -> uuid.UUID:
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR-C', 'RESOLUCION', :n, 2025, 'Resolución de prueba') RETURNING id"
        ),
        {"n": numero},
    ).scalar_one()
    registro = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde) "
            "VALUES ('norma', :n, 1, 'CANDIDATE', 'ABIERTO_FIN', '2025-01-01') RETURNING id"
        ),
        {"n": norma_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO norma_versiones (registro_version_id, norma_id, doc_version_id, "
            " tipo_version) VALUES (:rv, :n, :dv, 'ORIGINAL')"
        ),
        {"rv": registro, "n": norma_id, "dv": doc_version},
    )
    return norma_id


@pytest.fixture
def resolucion(conexion: Connection):
    cargar_catalogo(conexion)
    cuerpo = _version(conexion, "D04", CUERPO)
    return _norma(conexion, cuerpo, str(uuid.uuid4())[:6]), cuerpo


def _campos(conexion: Connection, norma_id: uuid.UUID) -> dict[str, tuple[str, str]]:
    return {
        f["campo_solicitado"]: (f["estado"], f["motivo"] or "")
        for f in conexion.execute(
            text(
                "SELECT ec.campo_solicitado, ec.estado, ec.motivo "
                "  FROM evaluaciones_completitud ec "
                "  JOIN norma_versiones nv ON nv.registro_version_id = ec.norma_version_id "
                " WHERE nv.norma_id = :n"
            ),
            {"n": norma_id},
        ).mappings()
    }


# --- AT-029: el cuerpo solo no completa el procedimiento ---------------------


def test_at029_la_remision_al_anexo_se_detecta_aunque_cruce_varias_unidades(
    conexion: Connection, resolucion
) -> None:
    """La oración empieza en el artículo 3 y termina dos párrafos después.
    Mirar cada unidad por separado no encuentra ninguna de las dos mitades."""
    norma_id, _ = resolucion
    resultado = CuradorDeAnexos(conexion).revisar(norma_id)

    assert resultado.remisiones == 1
    assert resultado.identificadas == 1


def test_at029_el_cuerpo_solo_no_completa_el_procedimiento(
    conexion: Connection, resolucion
) -> None:
    """Y lo dice con el motivo puesto: no es silencio de la norma."""
    norma_id, _ = resolucion
    CuradorDeAnexos(conexion).revisar(norma_id)

    campos = _campos(conexion, norma_id)
    for campo in ("plazos", "criterios_aplicabilidad"):
        estado, motivo = campos[campo]
        assert estado == "NO_INFORMADO_EN_FUENTES_REVISADAS"
        assert "remite a un anexo" in motivo
        assert "no es silencio de la fuente" in motivo


def test_at029_el_anexo_queda_identificado_por_su_numero(conexion: Connection, resolucion) -> None:
    """`IF-2025-53544032-GCABA-SSGDA` nombra un documento concreto: se guarda
    para que alguien lo consiga, no se resuelve por parecido."""
    norma_id, _ = resolucion
    CuradorDeAnexos(conexion).revisar(norma_id)

    fila = (
        conexion.execute(
            text(
                "SELECT identidad_candidata, estado, responsable_rol, motivo "
                "  FROM referencias_pendientes WHERE norma_origen_id = :n"
            ),
            {"n": norma_id},
        )
        .mappings()
        .one()
    )
    assert fila["identidad_candidata"]["identificador"] == "IF-2025-53544032-GCABA-SSGDA"
    assert fila["identidad_candidata"]["ruta_en_el_cuerpo"] == "articulo-3"
    assert fila["estado"] == "PENDIENTE"
    assert fila["responsable_rol"]


def test_at029_con_el_anexo_vinculado_la_referencia_queda_resuelta(
    conexion: Connection, resolucion
) -> None:
    """La otra mitad del caso: capturado y vinculado antes de publicar."""
    norma_id, _ = resolucion
    CuradorDeAnexos(conexion).revisar(norma_id)
    referencia = conexion.execute(
        text("SELECT id FROM referencias_pendientes WHERE norma_origen_id = :n"),
        {"n": norma_id},
    ).scalar_one()

    version_anexo = _version(conexion, "D07", ANEXO)
    _norma(conexion, version_anexo, str(uuid.uuid4())[:6])

    relacion = CuradorDeAnexos(conexion).resolver(
        referencia,
        doc_version_anexo=version_anexo,
        actor="curador jurídico",
        fundamento="El IF citado corresponde al anexo publicado con la resolución.",
    )

    fila = (
        conexion.execute(
            text(
                "SELECT estado, relacion_resultante_id, resuelta_en "
                "  FROM referencias_pendientes WHERE id = :r"
            ),
            {"r": referencia},
        )
        .mappings()
        .one()
    )
    assert fila["estado"] == "RESUELTA"
    assert fila["relacion_resultante_id"] == relacion

    tipo = conexion.execute(
        text("SELECT tipo FROM relaciones_normativas WHERE id = :r"), {"r": relacion}
    ).scalar_one()
    assert tipo == "COMPLEMENTA"


def test_at029_una_segunda_revision_no_vuelve_a_abrir_la_referencia_resuelta(
    conexion: Connection, resolucion
) -> None:
    norma_id, _ = resolucion
    CuradorDeAnexos(conexion).revisar(norma_id)
    referencia = conexion.execute(
        text("SELECT id FROM referencias_pendientes WHERE norma_origen_id = :n"),
        {"n": norma_id},
    ).scalar_one()
    version_anexo = _version(conexion, "D07", ANEXO)
    _norma(conexion, version_anexo, str(uuid.uuid4())[:6])
    CuradorDeAnexos(conexion).resolver(
        referencia,
        doc_version_anexo=version_anexo,
        actor="curador jurídico",
        fundamento="El IF citado corresponde al anexo publicado con la resolución.",
    )

    segunda = CuradorDeAnexos(conexion).revisar(norma_id)
    assert segunda.pendientes_abiertas == 0
    assert any("están resueltas" in a for a in segunda.avisos)


# --- Vincular es una decisión, no una coincidencia ---------------------------


def test_vincular_exige_actor_y_fundamento(conexion: Connection, resolucion) -> None:
    """De ese vínculo dependen los plazos que se publican."""
    norma_id, _ = resolucion
    CuradorDeAnexos(conexion).revisar(norma_id)
    referencia = conexion.execute(
        text("SELECT id FROM referencias_pendientes WHERE norma_origen_id = :n"),
        {"n": norma_id},
    ).scalar_one()
    version_anexo = _version(conexion, "D07", ANEXO)
    _norma(conexion, version_anexo, str(uuid.uuid4())[:6])

    with pytest.raises(ValueError, match="actor y un fundamento"):
        CuradorDeAnexos(conexion).resolver(
            referencia, doc_version_anexo=version_anexo, actor="", fundamento="Es el anexo."
        )


def test_un_pdf_que_dice_anexo_pero_no_es_una_norma_no_se_vincula(
    conexion: Connection, resolucion
) -> None:
    """Que un archivo diga «Anexo» no prueba que sea el anexo de esta norma."""
    norma_id, _ = resolucion
    CuradorDeAnexos(conexion).revisar(norma_id)
    referencia = conexion.execute(
        text("SELECT id FROM referencias_pendientes WHERE norma_origen_id = :n"),
        {"n": norma_id},
    ).scalar_one()
    suelto = _version(conexion, "D07", ANEXO, tipo="OTRO")

    with pytest.raises(ValueError, match="no está vinculada a ninguna norma"):
        CuradorDeAnexos(conexion).resolver(
            referencia,
            doc_version_anexo=suelto,
            actor="curador jurídico",
            fundamento="Parece el anexo por el nombre del archivo.",
        )


# --- Detección --------------------------------------------------------------


def test_un_identificador_partido_en_dos_renglones_se_junta() -> None:
    """El PDF corta `IF-2025-\\n53544032-GCABA-SSGDA` y sigue siendo el mismo."""
    texto = (
        "Aprobar los Procedimientos, identificado como Anexo (IF-2025-\n"
        "53544032-GCABA-SSGDA) el cual forma parte integrante de la presente."
    )
    [(_, identificador, _posicion)] = remisiones_en(texto)
    assert identificador == "IF-2025-53544032-GCABA-SSGDA"


def test_dejar_sin_efecto_otras_resoluciones_no_es_una_remision_a_anexo() -> None:
    assert remisiones_en("Artículo 1°.- Dejar sin efecto las Resoluciones 1293-MEGC/09.") == []


def test_una_norma_sin_version_vigente_lo_dice(conexion: Connection) -> None:
    cargar_catalogo(conexion)
    resultado = CuradorDeAnexos(conexion).revisar(uuid.uuid4())
    assert resultado.remisiones == 0
    assert any("no tiene una versión vigente" in a for a in resultado.avisos)
