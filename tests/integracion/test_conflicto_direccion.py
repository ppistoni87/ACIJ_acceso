"""HU-F20 · AT-060: dos fuentes oficiales que dicen pisos distintos.

El caso es real y está publicado. El dataset abierto de sedes comunales dice que
la Subsede Comunal 2 está en «Lopez, Vicente 2050, 3 piso»; la ficha de la
Comuna 2, del mismo gobierno, dice «Vicente López 2050, 4° piso». Coinciden en
la calle y en la altura, y difieren en el piso.

Hay tres maneras de arruinarlo y las tres producen una dirección que se lee
bien: elegir la primera fuente, elegir la más reciente, o componer una legible
tomando la calle de una y el piso de la otra.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.conflictos import (
    DetectorDeConflictos,
    contrastar,
    leer_direccion,
)

pytestmark = pytest.mark.integracion

# Las dos cadenas tal como las publican las dos fuentes.
DEL_DATASET = "Lopez, Vicente 2050, 3 piso"
DE_LA_FICHA = "Vicente López 2050, 4° piso"


# --- AT-060: el campo en disputa se retiene ---------------------------------


def test_at060_el_piso_en_disputa_se_reporta_como_conflicto() -> None:
    contraste = contrastar({"dataset abierto": DEL_DATASET, "ficha de la Comuna 2": DE_LA_FICHA})

    assert contraste.hay_conflicto
    assert contraste.campos_en_disputa == ["piso"]
    conflicto = contraste.conflictos[0]
    assert conflicto.valores == {"dataset abierto": "3", "ficha de la Comuna 2": "4"}


def test_at060_no_se_compone_una_direccion_mezclada() -> None:
    """La calle de una fuente con el piso de la otra es una dirección que no
    publicó ninguna de las dos."""
    contraste = contrastar({"dataset abierto": DEL_DATASET, "ficha de la Comuna 2": DE_LA_FICHA})

    publicable = contraste.direccion_publicable
    assert publicable == "Lopez, Vicente 2050"
    assert "3" not in publicable.replace("2050", "")
    assert "4" not in publicable.replace("2050", "")
    assert "piso" not in publicable.lower()


def test_at060_no_se_elige_la_primera_fuente() -> None:
    """Ni la primera ni la segunda: el orden en que llegaron no las ordena."""
    directo = contrastar({"a": DEL_DATASET, "b": DE_LA_FICHA})
    invertido = contrastar({"b": DE_LA_FICHA, "a": DEL_DATASET})

    assert directo.campos_en_disputa == invertido.campos_en_disputa
    assert directo.direccion_publicable == invertido.direccion_publicable
    assert "piso" not in directo.coinciden


def test_at060_lo_que_las_dos_afirman_igual_si_se_conserva() -> None:
    """Que el piso esté en duda no pone en duda la calle."""
    contraste = contrastar({"dataset abierto": DEL_DATASET, "ficha de la Comuna 2": DE_LA_FICHA})

    assert contraste.coinciden["altura"] == "2050"
    assert contraste.coinciden["calle"] == "Lopez, Vicente"


def test_at060_el_apellido_invertido_no_es_un_conflicto_de_calle() -> None:
    """El dataset escribe «Lopez, Vicente» y la ficha «Vicente López». Leerlo
    como dos calles distintas inventaría un conflicto que no existe y taparía
    el que sí existe."""
    contraste = contrastar({"dataset abierto": DEL_DATASET, "ficha de la Comuna 2": DE_LA_FICHA})
    assert "calle" not in contraste.campos_en_disputa


# --- Cómo se lee una dirección ----------------------------------------------


@pytest.mark.parametrize(
    ("cruda", "calle", "altura", "piso"),
    [
        # Todas reales, del corpus cargado.
        (DEL_DATASET, "Lopez, Vicente", "2050", "3"),
        (DE_LA_FICHA, "Vicente López", "2050", "4"),
        ("Cabildo Av. 3067, 1 piso", "Cabildo Av", "3067", "1"),
        ("Av. Directorio 5792, Piso 1.", "Av. Directorio", "5792", "1"),
        ("Sobremonte 549 - Entrepiso", "Sobremonte", "549", "entrepiso"),
        ("Humberto 1° 250", "Humberto 1°", "250", None),
    ],
)
def test_una_direccion_se_separa_en_calle_altura_y_piso(
    cruda: str, calle: str, altura: str | None, piso: str | None
) -> None:
    direccion = leer_direccion(cruda)
    assert (direccion.calle, direccion.altura, direccion.piso) == (calle, altura, piso)


def test_una_fuente_que_no_declara_el_piso_no_contradice_a_la_que_si() -> None:
    """Es una fuente menos completa, no una fuente en desacuerdo."""
    contraste = contrastar({"dataset": "Sarandi 1273", "ficha": "Sarandí 1273, 2° piso"})
    assert not contraste.hay_conflicto
    assert contraste.coinciden["piso"] == "2"
    assert contraste.direccion_publicable == "Sarandi 1273 piso 2"


def test_una_sola_fuente_no_produce_contraste() -> None:
    assert not contrastar({"dataset": DEL_DATASET}).hay_conflicto


# --- La incidencia queda abierta con las dos versiones ----------------------


@pytest.fixture
def subsede(conexion: Connection):
    """La misma subsede con dos versiones candidatas abiertas, una por fuente."""
    cargar_catalogo(conexion)
    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'ORGANISMO_CONTROL') RETURNING id"
        ),
        {"n": f"Comuna 2 {uuid.uuid4().hex[:6]}"},
    ).scalar_one()
    punto = conexion.execute(
        text(
            "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, alcance) "
            "VALUES (:o, 'AR-C', 'Subsede Comunal 2', 'DELEGACION', 'NO_DECLARADO') RETURNING id"
        ),
        {"o": organismo},
    ).scalar_one()
    for numero, direccion in enumerate((DEL_DATASET, DE_LA_FICHA), start=1):
        registro = conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo, valid_desde) "
                "VALUES ('punto_atencion', :p, :nv, 'CANDIDATE', 'ABIERTO_FIN', '2026-01-01') "
                "RETURNING id"
            ),
            {"p": punto, "nv": numero},
        ).scalar_one()
        conexion.execute(
            text(
                "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_cruda, "
                " localidad, es_presencial) VALUES (:rv, :p, :d, 'Recoleta', true)"
            ),
            {"rv": registro, "p": punto, "d": direccion},
        )
    return punto


def test_at060_los_dos_candidatos_coexisten_sin_que_uno_pise_al_otro(
    conexion: Connection, subsede
) -> None:
    contraste = DetectorDeConflictos(conexion).revisar(subsede)

    assert contraste.campos_en_disputa == ["piso"]
    abiertas = conexion.execute(
        text(
            "SELECT count(*) FROM punto_versiones pv "
            "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
            " WHERE pv.punto_id = :p AND rv.known_hasta IS NULL"
        ),
        {"p": subsede},
    ).scalar_one()
    assert abiertas == 2


def test_at060_la_incidencia_nombra_las_dos_versiones_y_su_origen(
    conexion: Connection, subsede
) -> None:
    DetectorDeConflictos(conexion).revisar(subsede)

    fila = (
        conexion.execute(
            text(
                "SELECT tipo, severidad, descripcion FROM incidencias_revision "
                " WHERE tipo = 'CONFLICTO_DE_FUENTES' AND descripcion LIKE '%piso%'"
            )
        )
        .mappings()
        .one()
    )
    assert fila["severidad"] == "HIGH"
    assert "«3»" in fila["descripcion"]
    assert "«4»" in fila["descripcion"]
    assert "no se elige una fuente" in fila["descripcion"]


def test_revisar_dos_veces_no_duplica_la_incidencia(conexion: Connection, subsede) -> None:
    DetectorDeConflictos(conexion).revisar(subsede)
    DetectorDeConflictos(conexion).revisar(subsede)

    assert (
        conexion.execute(
            text(
                "SELECT count(*) FROM incidencias_revision "
                " WHERE tipo = 'CONFLICTO_DE_FUENTES' AND descripcion LIKE '%piso%'"
            )
        ).scalar_one()
        == 1
    )
