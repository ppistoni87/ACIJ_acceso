"""HU-009 y HU-010: identidad de normas y relaciones, sobre la base real."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.curacion.relaciones import ConstructorRelaciones

pytestmark = pytest.mark.integracion

POLITICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"


@pytest.fixture
def catalogo(conexion: Connection):
    return cargar_catalogo(conexion)


def _documento_norma(
    conexion: Connection,
    *,
    source_id: str,
    external_id: str,
    tipo_version: str,
    identidad: dict,
    unidades: list[tuple[str, str | None, str, str]] = (),
    sufijo_url: str = "",
) -> uuid.UUID:
    """Crea la cadena captura → documento → versión → unidades para una norma."""
    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"s": source_id, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}{sufijo_url}"},
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
            "INSERT INTO documentos (source_id, tipo, external_id) "
            "VALUES (:s, 'NORMA', :e) RETURNING id"
        ),
        {"s": source_id, "e": external_id},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            " tipo_fecha, hash_texto, modo_extraccion, extractor_version, identidad_candidata) "
            "VALUES (:d, :c, 1, :tv, 'PUBLICACION', :h, 'HTML', 'prueba', :i) RETURNING id"
        ),
        {
            "d": documento,
            "c": captura,
            "tv": tipo_version,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "i": json.dumps(identidad, ensure_ascii=False),
        },
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


# --- Identidad ----------------------------------------------------------------


def test_dos_normas_con_igual_numero_y_distinta_jurisdiccion_no_se_fusionan(
    conexion: Connection, catalogo
) -> None:
    for source_id, jurisdiccion, namespace in (
        ("D01", "AR", "infoleg"),
        ("D03", "AR-C", "normativaba"),
    ):
        _documento_norma(
            conexion,
            source_id=source_id,
            external_id=f"{namespace}:1000:original",
            tipo_version="ORIGINAL",
            identidad={
                "jurisdiccion": jurisdiccion,
                "tipo": "LEY",
                "numero": "1000",
                "anio": 2020,
                "titulo": f"Ley de prueba {jurisdiccion}",
                f"{namespace}_id": "1000",
            },
        )
    resultado = ResolutorIdentidad(conexion).resolver_pendientes()

    assert resultado.normas_creadas == 2
    jurisdicciones = (
        conexion.execute(
            text("SELECT jurisdiccion_id FROM normas WHERE numero = '1000' ORDER BY 1")
        )
        .scalars()
        .all()
    )
    assert jurisdicciones == ["AR", "AR-C"]


def test_una_identidad_incompleta_queda_en_staging_sin_fusionarse(
    conexion: Connection, catalogo
) -> None:
    """El texto de una norma no trae tipo ni número: eso está en la ficha."""
    _documento_norma(
        conexion,
        source_id="D02",
        external_id="infoleg:70499:original",
        tipo_version="ORIGINAL",
        identidad={"jurisdiccion": "AR", "infoleg_id": "70499"},
    )
    resultado = ResolutorIdentidad(conexion).resolver_pendientes()

    assert resultado.inciertas == 1
    fila = conexion.execute(text("SELECT identidad_incierta, tipo, numero FROM normas")).one()
    assert fila.identidad_incierta is True
    assert fila.numero is None

    incidencia = conexion.execute(
        text("SELECT severidad, estado FROM incidencias_revision WHERE tipo = 'IDENTIDAD_AMBIGUA'")
    ).one()
    assert (incidencia.severidad, incidencia.estado) == ("HIGH", "ABIERTA")


def test_la_ficha_completa_la_identidad_sin_crear_otra_norma(
    conexion: Connection, catalogo
) -> None:
    """Corregir un título o completar el número no crea una norma nueva."""
    resolutor = ResolutorIdentidad(conexion)
    _documento_norma(
        conexion,
        source_id="D02",
        external_id="infoleg:70499:original",
        tipo_version="ORIGINAL",
        identidad={"jurisdiccion": "AR", "infoleg_id": "70499"},
        unidades=[("ARTICULO", "1", "Artículo 1° - Restitúyese la vigencia.", "DISPOSITIVO")],
    )
    resolutor.resolver_pendientes()

    _documento_norma(
        conexion,
        source_id="D02",
        external_id="infoleg:70499",
        tipo_version="NO_DETERMINADO",
        identidad={
            "jurisdiccion": "AR",
            "infoleg_id": "70499",
            "tipo": "DECRETO",
            "numero": "1604",
            "anio": 2001,
            "titulo": "ASIGNACIONES FAMILIARES",
        },
        sufijo_url="/ficha",
    )
    resolutor.resolver_pendientes()

    normas = conexion.execute(
        text("SELECT tipo, numero, anio, titulo, identidad_incierta FROM normas")
    ).all()
    assert len(normas) == 1
    assert (normas[0].tipo, normas[0].numero, normas[0].anio) == ("DECRETO", "1604", 2001)
    assert normas[0].identidad_incierta is False

    # La incidencia que abrió la identidad incierta queda resuelta con su rastro.
    incidencia = conexion.execute(
        text(
            "SELECT estado, decidido_por, decision FROM incidencias_revision "
            "WHERE tipo = 'IDENTIDAD_AMBIGUA'"
        )
    ).one()
    assert incidencia.estado == "RESUELTA"
    assert incidencia.decidido_por
    assert "1604" in incidencia.decision


def test_una_identidad_ya_completa_no_se_sobrescribe(conexion: Connection, catalogo) -> None:
    """Si otra vista declara una identidad distinta, es un conflicto para
    revisión, no una corrección automática."""
    resolutor = ResolutorIdentidad(conexion)
    base = {
        "jurisdiccion": "AR",
        "infoleg_id": "99999",
        "tipo": "LEY",
        "numero": "1111",
        "anio": 2020,
    }
    _documento_norma(
        conexion,
        source_id="D01",
        external_id="infoleg:99999:original",
        tipo_version="ORIGINAL",
        identidad=base,
    )
    resolutor.resolver_pendientes()

    _documento_norma(
        conexion,
        source_id="D01",
        external_id="infoleg:99999:actualizado",
        tipo_version="ACTUALIZADO",
        identidad={**base, "numero": "2222"},
        sufijo_url="/act",
    )
    resolutor.resolver_pendientes()

    numeros = conexion.execute(text("SELECT numero FROM normas")).scalars().all()
    assert numeros == ["1111"]
    conflicto = conexion.execute(
        text(
            "SELECT descripcion, candidatos FROM incidencias_revision "
            "WHERE tipo = 'IDENTIDAD_AMBIGUA' AND estado = 'ABIERTA'"
        )
    ).one()
    assert "no se sobrescribe" in conflicto.descripcion.lower()
    assert conflicto.candidatos["registrada"]["numero"] == "1111"
    assert conflicto.candidatos["nueva"]["numero"] == "2222"


def test_una_version_nace_sin_vigencia_resuelta(conexion: Connection, catalogo) -> None:
    """Conocer la publicación no dice hasta cuándo rige. Un límite temporal
    desconocido no puede volverse infinito aplicable por defecto."""
    _documento_norma(
        conexion,
        source_id="D01",
        external_id="infoleg:1:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR",
            "infoleg_id": "1",
            "tipo": "LEY",
            "numero": "1",
            "anio": 2020,
            "fechas": {"PUBLICACION": "2020-05-01"},
        },
    )
    ResolutorIdentidad(conexion).resolver_pendientes()

    version = conexion.execute(
        text(
            "SELECT rv.valid_tipo, rv.valid_desde, rv.valid_hasta, rv.estado_revision, "
            "       nv.estado_legal_validado "
            "FROM registro_versiones rv JOIN norma_versiones nv "
            "  ON nv.registro_version_id = rv.id"
        )
    ).one()
    assert version.valid_tipo == "DESCONOCIDO"
    assert str(version.valid_desde) == "2020-05-01"
    assert version.valid_hasta is None
    assert version.estado_revision == "CANDIDATE"
    assert version.estado_legal_validado == "NO_DETERMINADA"

    # Y por lo tanto no produce rango aplicable ni puede servirse.
    rango = conexion.execute(
        text("SELECT bn_rango_aplicacion('DESCONOCIDO', '2020-05-01'::date, NULL)")
    ).scalar_one()
    assert rango is None


def test_la_ficha_no_es_una_version_del_texto(conexion: Connection, catalogo) -> None:
    """La ficha describe la norma pero no la contiene."""
    _documento_norma(
        conexion,
        source_id="D01",
        external_id="infoleg:2",
        tipo_version="NO_DETERMINADO",
        identidad={
            "jurisdiccion": "AR",
            "infoleg_id": "2",
            "tipo": "LEY",
            "numero": "2",
            "anio": 2020,
        },
    )
    resultado = ResolutorIdentidad(conexion).resolver_pendientes()
    assert resultado.normas_creadas == 1
    assert resultado.versiones_creadas == 0


# --- Relaciones ---------------------------------------------------------------


@pytest.fixture
def corpus_f33(conexion: Connection, catalogo):
    """Ley 24.714 con su nota editorial, y los dos decretos que la afectan."""
    _documento_norma(
        conexion,
        source_id="F33",
        external_id="infoleg:39880:actualizado",
        tipo_version="ACTUALIZADO",
        identidad={
            "jurisdiccion": "AR",
            "infoleg_id": "39880",
            "tipo": "LEY",
            "numero": "24714",
            "anio": 1996,
            "titulo": "REGIMEN DE ASIGNACIONES FAMILIARES",
        },
        unidades=[
            (
                "NO_RECONOCIDO",
                None,
                "( Nota Infoleg : norma abrogada por art. 26 del Decreto N° 1382/01 "
                "y restablecida su vigencia por Decreto N° 1604/2001 )",
                "NOTA",
            ),
            (
                "ARTICULO",
                "1",
                "ARTICULO 1°- Se instituye el régimen. Derógase la Ley N° 18.017.",
                "DISPOSITIVO",
            ),
        ],
    )
    for numero, infoleg, titulo in (
        ("1382", "69649", "SISTEMA INTEGRADO DE PROTECCION A LA FAMILIA"),
        ("1604", "70499", "ASIGNACIONES FAMILIARES"),
    ):
        _documento_norma(
            conexion,
            source_id="D01",
            external_id=f"infoleg:{infoleg}:original",
            tipo_version="ORIGINAL",
            identidad={
                "jurisdiccion": "AR",
                "infoleg_id": infoleg,
                "tipo": "DECRETO",
                "numero": numero,
                "anio": 2001,
                "titulo": titulo,
            },
            sufijo_url=f"/{numero}",
        )
    ResolutorIdentidad(conexion).resolver_pendientes()
    return ConstructorRelaciones(conexion).construir()


def test_la_nota_produce_la_abrogacion_y_la_restitucion(conexion: Connection, corpus_f33) -> None:
    """F33: quedarse con la primera palabra de la nota clasificaría la Ley
    24.714 como abrogada y ocultaría que su vigencia fue restablecida."""
    relaciones = {
        (fila.tipo, fila.origen, fila.destino)
        for fila in conexion.execute(
            text(
                "SELECT r.tipo, o.numero AS origen, d.numero AS destino "
                "FROM relaciones_normativas r "
                "JOIN normas o ON o.id = r.norma_origen_id "
                "JOIN normas d ON d.id = r.norma_destino_id"
            )
        )
    }
    assert ("ABROGA", "1382", "24714") in relaciones
    assert ("RESTABLECE", "1604", "24714") in relaciones


def test_una_relacion_de_una_nota_declara_que_viene_de_una_nota(
    conexion: Connection, corpus_f33
) -> None:
    """La nota es del editor del boletín, no de la norma."""
    alcance = conexion.execute(
        text("SELECT alcance FROM relaciones_normativas WHERE tipo = 'ABROGA'")
    ).scalar_one()
    assert "nota editorial" in alcance


def test_toda_relacion_nace_candidata_y_con_evidencia(conexion: Connection, corpus_f33) -> None:
    filas = conexion.execute(
        text(
            "SELECT r.estado_revision, e.fragmento, e.unidad_id "
            "FROM relaciones_normativas r JOIN evidencias e ON e.id = r.evidencia_id"
        )
    ).all()
    assert filas
    assert all(f.estado_revision == "CANDIDATE" for f in filas)
    # La evidencia apunta a la unidad concreta, no a la norma entera.
    assert all(f.unidad_id is not None and f.fragmento for f in filas)


def test_una_norma_no_registrada_queda_como_referencia_pendiente(
    conexion: Connection, corpus_f33
) -> None:
    """La Ley 18.017 no está en el corpus: no se inventa un destino."""
    pendiente = conexion.execute(
        text(
            "SELECT texto_cita, identidad_candidata, estado, responsable_rol "
            "FROM referencias_pendientes WHERE texto_cita LIKE '%18.017%'"
        )
    ).one()
    assert pendiente.estado == "PENDIENTE"
    assert pendiente.identidad_candidata["numero"] == "18017"
    assert pendiente.identidad_candidata["relacion_sugerida"] == "DEROGA"
    assert pendiente.responsable_rol


def test_construir_relaciones_dos_veces_no_duplica(conexion: Connection, corpus_f33) -> None:
    antes = conexion.execute(text("SELECT count(*) FROM relaciones_normativas")).scalar_one()
    pendientes_antes = conexion.execute(
        text("SELECT count(*) FROM referencias_pendientes")
    ).scalar_one()

    segunda = ConstructorRelaciones(conexion).construir()

    assert segunda.relaciones_creadas == 0
    assert segunda.pendientes_creadas == 0
    assert (
        conexion.execute(text("SELECT count(*) FROM relaciones_normativas")).scalar_one() == antes
    )
    assert (
        conexion.execute(text("SELECT count(*) FROM referencias_pendientes")).scalar_one()
        == pendientes_antes
    )
