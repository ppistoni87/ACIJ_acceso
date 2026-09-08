"""HU-F09 · AT-078: un organismo provincial no es el servicio de un municipio.

Cuando un directorio municipal se cae, la tentación es responder con la lista
provincial que sí está. Las dos cosas comparten provincia y no son
intercambiables: quien reclama ante el organismo equivocado pierde tiempo que a
veces es un plazo, y a veces el plazo era el suyo.

La jurisdicción dice dónde está un punto; el alcance dice a quién sirve. Sin
separarlos, la defensoría de Avellaneda y la de la Provincia de Buenos Aires
viven las dos en `AR-B` y una consulta por provincia las devuelve como si fueran
la misma cosa.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.importadores.dpn import alcance_de

pytestmark = pytest.mark.integracion


# --- Lo que el nombre declara, y sólo eso -----------------------------------


@pytest.mark.parametrize(
    ("nombre", "alcance", "ambito"),
    [
        # Nombres reales del directorio de la DPN.
        ("Defensor del Pueblo de la Provincia de Buenos Aires", "PROVINCIAL", "Buenos Aires"),
        ("Defensor del Pueblo de la Ciudad Autónoma de Buenos Aires", "PROVINCIAL", "Buenos Aires"),
        ("Defensor del Pueblo de la Ciudad de La Plata", "MUNICIPAL", "La Plata"),
        (
            "Defensor del Pueblo de la Municipalidad de Gral. Pueyrredón",
            "MUNICIPAL",
            "Gral. Pueyrredón",
        ),
        ("Defensor de los Vecinos de la Ciudad de Corrientes", "MUNICIPAL", "Corrientes"),
        ("Defensor del Vecino de La Falda", "MUNICIPAL", "La Falda"),
        ("Auditor General de la Municipalidad de Villa María", "MUNICIPAL", "Villa María"),
    ],
)
def test_el_alcance_sale_de_lo_que_el_nombre_declara(
    nombre: str, alcance: str, ambito: str
) -> None:
    assert alcance_de(nombre) == (alcance, ambito)


@pytest.mark.parametrize(
    "nombre",
    [
        # Salta y Córdoba son provincia y capital a la vez: el nombre no alcanza.
        "Defensor del Pueblo de Salta",
        "Defensor del Pueblo de Córdoba",
        "Defensor del Pueblo de Avellaneda",
        "Defensoría del Pueblo de Tandil",
    ],
)
def test_at078_un_nombre_que_no_declara_su_alcance_queda_sin_declarar(nombre: str) -> None:
    """Adivinar manda a alguien a un organismo sin competencia sobre su reclamo."""
    assert alcance_de(nombre) == ("NO_DECLARADO", None)


# --- El esquema no deja declarar municipal sin municipio ---------------------


def _organismo(conexion: Connection, nombre: str) -> uuid.UUID:
    return conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-B', :n, 'ORGANISMO_CONTROL') RETURNING id"
        ),
        {"n": nombre},
    ).scalar_one()


def test_un_punto_municipal_sin_ambito_no_entra(conexion: Connection) -> None:
    """«Municipal» sin municipio no distingue nada."""
    cargar_catalogo(conexion)
    organismo = _organismo(conexion, f"Defensoría {uuid.uuid4().hex[:6]}")

    with pytest.raises(Exception, match="municipal_declara_su_ambito"):
        conexion.execute(
            text(
                "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, "
                " alcance) VALUES (:o, 'AR-B', 'Sede', 'SEDE', 'MUNICIPAL')"
            ),
            {"o": organismo},
        )


def test_un_alcance_fuera_del_vocabulario_no_entra(conexion: Connection) -> None:
    cargar_catalogo(conexion)
    organismo = _organismo(conexion, f"Defensoría {uuid.uuid4().hex[:6]}")

    with pytest.raises(Exception, match="alcance_vocabulario"):
        conexion.execute(
            text(
                "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, "
                " alcance, ambito) VALUES (:o, 'AR-B', 'Sede', 'SEDE', 'COMARCAL', 'X')"
            ),
            {"o": organismo},
        )


# --- La consulta no confunde una cosa con la otra ---------------------------


@pytest.fixture
def dos_defensorias(conexion: Connection):
    """La provincial y la municipal, las dos en Buenos Aires."""
    cargar_catalogo(conexion)
    creados = {}
    for nombre, alcance, ambito in (
        ("Defensor del Pueblo de la Provincia de Buenos Aires", "PROVINCIAL", "Buenos Aires"),
        ("Defensor del Pueblo de Avellaneda", "MUNICIPAL", "Avellaneda"),
    ):
        organismo = _organismo(conexion, nombre)
        creados[alcance] = conexion.execute(
            text(
                "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, "
                " alcance, ambito) VALUES (:o, 'AR-B', :n, 'SEDE', :a, :amb) RETURNING id"
            ),
            {"o": organismo, "n": nombre, "a": alcance, "amb": ambito},
        ).scalar_one()
    return creados


def test_at078_identidad_y_alcance_quedan_separados(conexion: Connection, dos_defensorias) -> None:
    """Las dos comparten jurisdicción y no comparten alcance."""
    filas = (
        conexion.execute(
            text(
                "SELECT jurisdiccion_id, alcance, ambito FROM puntos_atencion "
                " WHERE id = ANY(:ids) ORDER BY alcance"
            ),
            {"ids": list(dos_defensorias.values())},
        )
        .mappings()
        .all()
    )
    assert {f["jurisdiccion_id"] for f in filas} == {"AR-B"}
    assert [f["alcance"] for f in filas] == ["MUNICIPAL", "PROVINCIAL"]
    assert [f["ambito"] for f in filas] == ["Avellaneda", "Buenos Aires"]


def test_at078_pedir_lo_municipal_no_devuelve_lo_provincial(
    conexion: Connection, dos_defensorias
) -> None:
    """Es la consulta que hace quien pregunta por el servicio de su municipio."""
    municipales = (
        conexion.execute(
            text(
                "SELECT nombre FROM puntos_atencion "
                " WHERE jurisdiccion_id = 'AR-B' AND alcance = 'MUNICIPAL'"
            )
        )
        .scalars()
        .all()
    )
    assert municipales == ["Defensor del Pueblo de Avellaneda"]


# --- La API tampoco los ofrece como equivalentes ----------------------------


@pytest.fixture
def defensorias_publicadas(conexion: Connection, corpus_publicado):
    """La provincial publicada y ninguna municipal: el caso de F09."""
    organismo = _organismo(conexion, "Defensor del Pueblo de la Provincia de Buenos Aires")
    punto = conexion.execute(
        text(
            "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, "
            " alcance, ambito) VALUES (:o, 'AR-B', :n, 'SEDE', 'PROVINCIAL', 'Buenos Aires') "
            "RETURNING id"
        ),
        {"o": organismo, "n": "Defensor del Pueblo de la Provincia de Buenos Aires"},
    ).scalar_one()
    release = conexion.execute(
        text("SELECT id FROM releases ORDER BY creado_en DESC LIMIT 1")
    ).scalar_one()
    registro = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde, release_id, verificado_en) "
            "VALUES ('punto_atencion', :p, 1, 'PUBLISHED', 'ABIERTO_FIN', '2025-01-01', "
            " :r, now()) RETURNING id"
        ),
        {"p": punto, "r": release},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_cruda, "
            " localidad, es_presencial) VALUES (:rv, :p, 'Calle 7 849', 'La Plata', true)"
        ),
        {"rv": registro, "p": punto},
    )
    return punto


def test_at078_la_api_no_responde_el_provincial_como_servicio_municipal(
    cliente_api, defensorias_publicadas
) -> None:
    """El directorio municipal está caído y la lista provincial sí está. La
    respuesta dice que no hay municipal, no ofrece el provincial en su lugar."""
    cuerpo = cliente_api.get(
        "/v1/puntos-atencion", params={"jurisdiccion": "AR-B", "alcance": "MUNICIPAL"}
    ).json()

    assert cuerpo["data"] == []
    assert cuerpo["data_status"] == "SIN_RESULTADOS"
    detalle = cuerpo["warnings"][0]["detalle"]
    assert "ningún punto de atención municipal" in detalle
    assert "no se ofrecen como equivalentes" in detalle
    assert "1 provincial" in detalle


def test_at078_el_provincial_si_se_devuelve_cuando_se_lo_pide(
    cliente_api, defensorias_publicadas
) -> None:
    """No se esconde: lo que no se hace es presentarlo como otra cosa."""
    cuerpo = cliente_api.get(
        "/v1/puntos-atencion", params={"jurisdiccion": "AR-B", "alcance": "PROVINCIAL"}
    ).json()

    assert len(cuerpo["data"]) == 1
    punto = cuerpo["data"][0]
    assert punto["alcance"] == "PROVINCIAL"
    assert punto["ambito"] == "Buenos Aires"


def test_un_alcance_inventado_es_un_error_tipado(cliente_api, corpus_publicado) -> None:
    respuesta = cliente_api.get("/v1/puntos-atencion", params={"alcance": "COMARCAL"})
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["codigo"] == "INVALID_REQUEST"
