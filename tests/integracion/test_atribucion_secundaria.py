"""HU-022 · AT-066: una ONG afirma algo que la fuente oficial no dice.

En el corpus hay 83 fuentes oficiales y una secundaria: ACIJ, que publica un
análisis del Proyecto de Presupuesto 2026 de la Ciudad y afirma que las partidas
de vivienda son las más bajas en catorce años. El GCBA publica el proyecto de
presupuesto; no publica esa lectura.

Descartarla pierde información sostenida en un documento público. Presentarla
sin decir quién la hace le da una autoridad que no tiene: quien la lea va a
creer que el Gobierno de la Ciudad dijo que su propio presupuesto de vivienda es
el más bajo en catorce años.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.publicacion.atribucion import explicar

pytestmark = pytest.mark.integracion

# Titular real de la publicación capturada.
AFIRMACION_ACIJ = (
    "El presupuesto previsto para los organismos de vivienda es el más bajo de los "
    "últimos catorce años."
)
CAMPO = "presupuesto_vivienda_2026"


def _fuente_secundaria(conexion: Connection, source_id: str) -> None:
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, caracter, estado, access_status, "
            " prioridad, politica_acceso) "
            "VALUES (:s, :n, 'DOCUMENTO', 'SECUNDARIA', 'ACTIVE', 'NO_VERIFICADO', 'P2', "
            " 'PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS')"
        ),
        {
            "s": source_id,
            "n": "ACIJ — Asociación Civil por la Igualdad y la Justicia (fuente secundaria)",
        },
    )


def _afirmar(
    conexion: Connection, registro_version_id: uuid.UUID, source_id: str, valor: str
) -> None:
    """Una afirmación informada exige evidencia: el esquema no deja afirmar sin
    poder mostrar dónde lo dice."""
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO afirmaciones (registro_version_id, campo_path, valor, estado_campo, "
            " source_id, evidencia_id, estado_revision) "
            "VALUES (:v, :c, :val, 'INFORMADO', :s, :e, 'CANDIDATE')"
        ),
        {
            "v": registro_version_id,
            "c": CAMPO,
            "val": json.dumps({"texto": valor}, ensure_ascii=False),
            "s": source_id,
            "e": evidencia,
        },
    )


@pytest.fixture
def version(conexion: Connection, corpus):
    cargar_catalogo(conexion)
    return corpus.registro_version_id


# --- AT-066: la atribución se conserva --------------------------------------


def test_at066_una_afirmacion_de_ong_no_se_adjudica_al_organismo_oficial(
    conexion: Connection, version
) -> None:
    """Es la mitad del caso que más daño hace: presentarla como oficial."""
    _fuente_secundaria(conexion, "S90")
    _afirmar(conexion, version, "S90", AFIRMACION_ACIJ)

    explicacion = explicar(conexion, version, CAMPO)
    assert explicacion.solo_secundaria
    atribucion = explicacion.secundarias[0]
    assert atribucion.atribuible_al_organismo is False
    assert atribucion.organismo is None


def test_at066_la_afirmacion_se_conserva_con_quien_la_hace(conexion: Connection, version) -> None:
    """La otra mitad: descartarla pierde información que a alguien le sirve."""
    _fuente_secundaria(conexion, "S91")
    _afirmar(conexion, version, "S91", AFIRMACION_ACIJ)

    explicacion = explicar(conexion, version, CAMPO)
    assert not explicacion.se_abstiene
    assert len(explicacion.secundarias) == 1
    assert "ACIJ" in explicacion.secundarias[0].fuente


def test_at066_la_explicacion_dice_que_la_oficial_no_lo_afirma(
    conexion: Connection, version
) -> None:
    _fuente_secundaria(conexion, "S92")
    _afirmar(conexion, version, "S92", AFIRMACION_ACIJ)

    texto = explicar(conexion, version, CAMPO).texto()
    assert "fuente secundaria" in texto
    assert "La fuente oficial revisada no lo dice" in texto
    assert "no se presenta como afirmación del organismo" in texto


def test_una_afirmacion_oficial_si_se_atribuye_a_su_organismo(
    conexion: Connection, version
) -> None:
    """La regla no es esconder la fuente: es no confundir una con la otra."""
    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'AUTORIDAD_APLICACION') RETURNING id"
        ),
        {"n": f"Autoridad de prueba {uuid.uuid4().hex[:6]}"},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, organismo_id, nombre, clase, caracter, estado, "
            " access_status, prioridad, politica_acceso) "
            "VALUES ('S93', :o, 'Portal oficial', 'PORTAL_NORMATIVO', 'OFICIAL', 'ACTIVE', "
            " 'ACCESIBLE', 'P1', 'PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS')"
        ),
        {"o": organismo},
    )
    _afirmar(conexion, version, "S93", "El presupuesto asignado es de $725.000 millones.")

    explicacion = explicar(conexion, version, CAMPO)
    assert not explicacion.solo_secundaria
    assert explicacion.oficiales[0].atribuible_al_organismo
    assert "Autoridad de prueba" in explicacion.oficiales[0].leyenda


def test_cuando_las_dos_afirman_no_es_solo_secundaria(conexion: Connection, version) -> None:
    _fuente_secundaria(conexion, "S94")
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, caracter, estado, access_status, "
            " prioridad, politica_acceso) "
            "VALUES ('S95', 'Portal oficial', 'PORTAL_NORMATIVO', 'OFICIAL', 'ACTIVE', "
            " 'ACCESIBLE', 'P1', 'PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS')"
        )
    )
    _afirmar(conexion, version, "S94", AFIRMACION_ACIJ)
    _afirmar(conexion, version, "S95", AFIRMACION_ACIJ)

    explicacion = explicar(conexion, version, CAMPO)
    assert len(explicacion.secundarias) == 1
    assert len(explicacion.oficiales) == 1
    assert not explicacion.solo_secundaria


def test_sin_ninguna_afirmacion_se_abstiene(conexion: Connection, version) -> None:
    explicacion = explicar(conexion, version, "campo_que_nadie_afirma")
    assert explicacion.se_abstiene
    assert "La ausencia no es una negación" in explicacion.texto()


# --- El catálogo distingue el carácter --------------------------------------


def test_el_catalogo_registra_a_acij_como_fuente_secundaria(conexion: Connection) -> None:
    """Las 83 del manifiesto son oficiales; la secundaria se agregó aparte y se
    declara como tal."""
    cargar_catalogo(conexion)
    oficiales = conexion.execute(
        text("SELECT count(*) FROM fuentes WHERE caracter = 'OFICIAL'")
    ).scalar_one()
    assert oficiales == 83

    _fuente_secundaria(conexion, "S96")
    assert (
        conexion.execute(
            text("SELECT count(*) FROM fuentes WHERE caracter = 'SECUNDARIA'")
        ).scalar_one()
        == 1
    )


def test_un_caracter_fuera_del_vocabulario_no_entra(conexion: Connection) -> None:
    with pytest.raises(Exception, match="caracter_vocabulario"):
        conexion.execute(
            text(
                "INSERT INTO fuentes (source_id, nombre, clase, caracter, estado, "
                " access_status, prioridad, politica_acceso) "
                "VALUES ('S97', 'X', 'DOCUMENTO', 'SEMIOFICIAL', 'ACTIVE', 'NO_VERIFICADO', "
                " 'P2', 'PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS')"
            )
        )
