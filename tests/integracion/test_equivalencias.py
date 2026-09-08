"""HU-F23 · AT-032: la renumeración del artículo 10 al 9.

Una regla se cita contra el artículo que la dice. Si el texto se consolida y ese
contenido pasa a otro número, responder por número devuelve otra regla —y la
devuelve sin dudar. El caso es el de siempre: alguien pregunta qué dice el
artículo 10 y recibe lo que hoy está en el 10, que ya no es lo que se citó.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.equivalencias import (
    CuradorDeEquivalencias,
    NormaSinDosVersiones,
    aprobar,
    resolver,
)

pytestmark = pytest.mark.integracion

DESAYUNO = "El beneficio cubre desayuno y merienda en el establecimiento escolar."
TRANSPORTE = "El beneficio cubre el transporte escolar."
NUEVO_ART_10 = "Las prestaciones se abonan por mes vencido."


def _version(conexion: Connection, external_id: str, unidades: list[tuple[str, str]]) -> uuid.UUID:
    """Crea captura → documento → versión → unidades. `unidades` son (ruta, texto)."""
    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES ('D01', :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES ('D01', 99, 'HTML_ESTATICO') "
            "ON CONFLICT (source_id, version) DO UPDATE SET adaptador = 'HTML_ESTATICO' "
            "RETURNING id"
        )
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES ('D01', :c, 'EN_CURSO', 'prueba') RETURNING id"
        ),
        {"c": cfg},
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
            "VALUES ('D01', 'NORMA', :e) RETURNING id"
        ),
        {"e": external_id},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            " tipo_fecha, hash_texto, modo_extraccion, extractor_version, identidad_candidata) "
            "VALUES (:d, :c, 1, 'NO_DETERMINADO', 'PUBLICACION', :h, 'HTML', 'prueba', :i) "
            "RETURNING id"
        ),
        {
            "d": documento,
            "c": captura,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "i": json.dumps({"tipo": "DECRETO", "numero": "1382", "anio": 2001}),
        },
    ).scalar_one()
    for orden, (ruta, texto_unidad) in enumerate(unidades, start=1):
        conexion.execute(
            text(
                "INSERT INTO unidades_documentales "
                "(doc_version_id, tipo, numero, ruta, orden, texto, rol_contenido) "
                "VALUES (:dv, 'ARTICULO', :n, :ruta, :o, :texto, 'DISPOSITIVO')"
            ),
            {
                "dv": version,
                "n": ruta.rsplit("-", 1)[-1],
                "ruta": ruta,
                "o": orden,
                "texto": texto_unidad,
            },
        )
    return version


@pytest.fixture
def norma(conexion: Connection):
    """El caso de AT-032: el desayuno estaba en el artículo 10 y pasa al 9.

    Y el artículo 10 nuevo dice otra cosa: es la trampa entera del caso.
    """
    cargar_catalogo(conexion)
    vieja = _version(
        conexion,
        f"decreto:{uuid.uuid4()}:original",
        [("articulo-9", TRANSPORTE), ("articulo-10", DESAYUNO)],
    )
    nueva = _version(
        conexion,
        f"decreto:{uuid.uuid4()}:actualizado",
        [("articulo-9", DESAYUNO), ("articulo-10", NUEVO_ART_10)],
    )
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR', 'DECRETO', :num, 2001, 'Decreto de prueba') RETURNING id"
        ),
        {"num": str(uuid.uuid4())[:8]},
    ).scalar_one()
    for orden, doc_version in enumerate([vieja, nueva], start=1):
        registro = conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo, valid_desde) "
                "VALUES ('norma', :n, :nv, 'CANDIDATE', 'ABIERTO_FIN', '2001-01-01') RETURNING id"
            ),
            {"n": norma_id, "nv": orden},
        ).scalar_one()
        conexion.execute(
            text(
                "INSERT INTO norma_versiones (registro_version_id, norma_id, doc_version_id, "
                " tipo_version) VALUES (:rv, :n, :dv, :tv)"
            ),
            {
                "rv": registro,
                "n": norma_id,
                "dv": doc_version,
                "tv": "ORIGINAL" if orden == 1 else "ACTUALIZADO",
            },
        )
    return norma_id, vieja, nueva


def _unidad(conexion: Connection, version: uuid.UUID, ruta: str) -> uuid.UUID:
    return conexion.execute(
        text("SELECT id FROM unidades_documentales WHERE doc_version_id = :v AND ruta = :r"),
        {"v": version, "r": ruta},
    ).scalar_one()


def _texto(conexion: Connection, unidad_id: uuid.UUID) -> str:
    return conexion.execute(
        text("SELECT texto FROM unidades_documentales WHERE id = :u"), {"u": unidad_id}
    ).scalar_one()


# --- AT-032: la correspondencia 10 → 9 --------------------------------------


def test_at032_la_renumeracion_del_10_al_9_queda_registrada(conexion: Connection, norma) -> None:
    norma_id, _, _ = norma
    resultado = CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)

    assert resultado.renumeraciones == 1
    assert resultado.cambian_de_articulo == 1

    fila = (
        conexion.execute(
            text(
                "SELECT uo.ruta AS origen, ud.ruta AS destino, eq.tipo, eq.estado_revision, "
                "       eq.motivo "
                "  FROM equivalencias_unidades eq "
                "  JOIN unidades_documentales uo ON uo.id = eq.origen_unidad_id "
                "  JOIN unidades_documentales ud ON ud.id = eq.destino_unidad_id "
                " WHERE eq.tipo = 'RENUMERACION'"
            )
        )
        .mappings()
        .one()
    )
    assert (fila["origen"], fila["destino"]) == ("articulo-10", "articulo-9")
    assert "Cambia de artículo" in fila["motivo"]


def test_at032_se_consulta_la_unidad_de_la_version_correcta(conexion: Connection, norma) -> None:
    """La cita al artículo 10 original resuelve al 9 actual, que es el que dice
    lo mismo; no al 10 actual, que dice otra cosa."""
    norma_id, vieja, nueva = norma
    CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)
    equivalencia = conexion.execute(
        text("SELECT id FROM equivalencias_unidades WHERE tipo = 'RENUMERACION'")
    ).scalar_one()
    aprobar(
        conexion,
        equivalencia,
        actor="curador jurídico",
        decision="El desayuno y la merienda pasaron del artículo 10 al 9 sin cambiar de texto.",
    )

    citada = _unidad(conexion, vieja, "articulo-10")
    destino = resolver(conexion, citada, en_version=nueva)

    assert destino == _unidad(conexion, nueva, "articulo-9")
    assert _texto(conexion, destino) == DESAYUNO


def test_at032_no_se_sobrescribe_el_articulo_10_actual(conexion: Connection, norma) -> None:
    """El artículo 10 de la versión nueva conserva su propio texto: una
    equivalencia relaciona unidades, no las pisa."""
    norma_id, vieja, nueva = norma
    CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)

    assert _texto(conexion, _unidad(conexion, nueva, "articulo-10")) == NUEVO_ART_10
    assert _texto(conexion, _unidad(conexion, vieja, "articulo-10")) == DESAYUNO


# --- Una correspondencia sin aprobar no redirige nada ------------------------


def test_una_correspondencia_candidata_no_redirige_la_cita(conexion: Connection, norma) -> None:
    """Dos párrafos con el mismo texto en artículos distintos se emparejan
    solos. Hasta que alguien lo mire, la cita se responde con lo que se citó."""
    norma_id, vieja, nueva = norma
    CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)

    citada = _unidad(conexion, vieja, "articulo-10")
    assert resolver(conexion, citada, en_version=nueva) is None


def test_toda_correspondencia_derivada_nace_candidata(conexion: Connection, norma) -> None:
    norma_id, _, _ = norma
    CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)

    estados = (
        conexion.execute(text("SELECT DISTINCT estado_revision FROM equivalencias_unidades"))
        .scalars()
        .all()
    )
    assert estados == ["CANDIDATE"]


def test_aprobar_exige_actor_y_fundamento(conexion: Connection, norma) -> None:
    norma_id, _, _ = norma
    CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)
    equivalencia = conexion.execute(
        text("SELECT id FROM equivalencias_unidades LIMIT 1")
    ).scalar_one()

    with pytest.raises(ValueError, match="actor y un fundamento"):
        aprobar(conexion, equivalencia, actor="  ", decision="Es lo mismo.")
    with pytest.raises(ValueError, match="actor y un fundamento"):
        aprobar(conexion, equivalencia, actor="curador", decision="ok")


def test_una_unidad_de_la_misma_version_se_resuelve_a_si_misma(conexion: Connection, norma) -> None:
    _, vieja, _ = norma
    citada = _unidad(conexion, vieja, "articulo-10")
    assert resolver(conexion, citada, en_version=vieja) == citada


# --- Lo que no se corresponde no se inventa ----------------------------------


def test_un_texto_que_desaparece_no_recibe_equivalencia(conexion: Connection) -> None:
    """Que un artículo ya no esté no significa que su contenido esté en otro
    lado. Sin correspondencia, la cita queda con su versión."""
    cargar_catalogo(conexion)
    vieja = _version(
        conexion,
        f"decreto:{uuid.uuid4()}:o",
        [("articulo-1", DESAYUNO), ("articulo-2", TRANSPORTE)],
    )
    nueva = _version(conexion, f"decreto:{uuid.uuid4()}:a", [("articulo-1", DESAYUNO)])
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR', 'DECRETO', :n, 2001, 'Decreto de prueba') RETURNING id"
        ),
        {"n": str(uuid.uuid4())[:8]},
    ).scalar_one()

    resultado = CuradorDeEquivalencias(conexion).derivar_entre(norma_id, vieja, nueva)
    assert resultado.sin_destino == 1
    assert resultado.renumeraciones == 0
    assert any("no significa que su contenido esté en otro lado" in a for a in resultado.avisos)


def test_una_norma_con_una_sola_version_no_deriva_nada(conexion: Connection) -> None:
    cargar_catalogo(conexion)
    _version(conexion, f"decreto:{uuid.uuid4()}:o", [("articulo-1", DESAYUNO)])
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR', 'DECRETO', :n, 2001, 'Decreto de prueba') RETURNING id"
        ),
        {"n": str(uuid.uuid4())[:8]},
    ).scalar_one()

    with pytest.raises(NormaSinDosVersiones, match="no se infiere de uno"):
        CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)


def test_derivar_dos_veces_no_duplica(conexion: Connection, norma) -> None:
    norma_id, _, _ = norma
    curador = CuradorDeEquivalencias(conexion)
    primera = curador.derivar_para_norma(norma_id)
    segunda = curador.derivar_para_norma(norma_id)

    assert primera.renumeraciones == 1
    assert segunda.renumeraciones == 0
    assert segunda.ya_registradas == primera.renumeraciones + primera.sustituciones


def test_cada_equivalencia_cita_la_unidad_de_destino_en_su_version(
    conexion: Connection, norma
) -> None:
    """La evidencia de que la correspondencia existe es el texto que está ahí."""
    norma_id, _, nueva = norma
    CuradorDeEquivalencias(conexion).derivar_para_norma(norma_id)

    filas = (
        conexion.execute(
            text(
                "SELECT e.doc_version_id, e.unidad_id, e.fragmento, eq.destino_unidad_id "
                "  FROM equivalencias_unidades eq JOIN evidencias e ON e.id = eq.evidencia_id"
            )
        )
        .mappings()
        .all()
    )
    assert filas
    for fila in filas:
        assert fila["doc_version_id"] == nueva
        assert fila["unidad_id"] == fila["destino_unidad_id"]
        assert fila["fragmento"] == _texto(conexion, fila["destino_unidad_id"])
