"""Reglas del esquema que sostienen el corpus.

Cada prueba corresponde a una regla explícita de la especificación: si la base
las deja de aplicar, un dato incorrecto puede llegar a una respuesta.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

pytestmark = pytest.mark.integracion


# --- Identidad de normas -----------------------------------------------------


def test_dos_leyes_mismo_numero_distinta_jurisdiccion_no_colisionan(
    conexion: Connection, jurisdiccion_nacion: str, jurisdiccion_caba: str
) -> None:
    """AT-001. La identidad incluye la jurisdicción: una ley nacional y una de
    CABA con el mismo número y año son normas distintas, sin fusión automática."""
    for jur in (jurisdiccion_nacion, jurisdiccion_caba):
        conexion.execute(
            text(
                "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
                "VALUES (:jur, 'LEY', '1234', 2020, 'Ley de prueba')"
            ),
            {"jur": jur},
        )
    total = conexion.execute(
        text("SELECT count(*) FROM normas WHERE numero = '1234' AND anio = 2020")
    ).scalar_one()
    assert total == 2


def test_misma_jurisdiccion_y_numero_no_se_duplica(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """La clave canónica evita crear dos veces la misma norma."""
    for _ in range(2):
        insertar = lambda: conexion.execute(  # noqa: E731
            text(
                "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
                "VALUES (:jur, 'LEY', '9999', 2021, 'Ley')"
            ),
            {"jur": jurisdiccion_nacion},
        )
        if _ == 0:
            insertar()
        else:
            with pytest.raises(IntegrityError):
                insertar()


def test_identidad_incierta_no_ocupa_la_clave_canonica(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """Una norma en identidad incierta queda en staging sin bloquear ni fusionar:
    puede convivir con otra del mismo número mientras se resuelve."""
    conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES (:jur, 'LEY', '555', 2019, 'Canónica')"
        ),
        {"jur": jurisdiccion_nacion},
    )
    conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo, identidad_incierta) "
            "VALUES (:jur, 'LEY', '555', 2019, 'Candidata sin resolver', true)"
        ),
        {"jur": jurisdiccion_nacion},
    )
    total = conexion.execute(
        text("SELECT count(*) FROM normas WHERE numero = '555'")
    ).scalar_one()
    assert total == 2


def test_identificador_oficial_no_se_repite_entre_espacios_de_nombres(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """AT-002. El mismo id de InfoLEG no puede quedar en dos normas, pero un id
    de NormativaBA con el mismo valor sí es otro identificador."""
    normas = [
        conexion.execute(
            text(
                "INSERT INTO normas (jurisdiccion_id, tipo, titulo) "
                "VALUES (:jur, 'LEY', :titulo) RETURNING id"
            ),
            {"jur": jurisdiccion_nacion, "titulo": f"Norma {i}"},
        ).scalar_one()
        for i in range(2)
    ]
    conexion.execute(
        text(
            "INSERT INTO norma_identificadores (norma_id, namespace, valor) "
            "VALUES (:n, 'infoleg', '39880')"
        ),
        {"n": normas[0]},
    )
    # Otro espacio de nombres con el mismo valor es legítimo.
    conexion.execute(
        text(
            "INSERT INTO norma_identificadores (norma_id, namespace, valor) "
            "VALUES (:n, 'normativaba', '39880')"
        ),
        {"n": normas[1]},
    )
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO norma_identificadores (norma_id, namespace, valor) "
                "VALUES (:n, 'infoleg', '39880')"
            ),
            {"n": normas[1]},
        )


# --- Jerarquías --------------------------------------------------------------


def test_jurisdicciones_no_admiten_ciclos(
    conexion: Connection, jurisdiccion_nacion: str, jurisdiccion_caba: str
) -> None:
    with pytest.raises(DBAPIError, match="ciclo"):
        conexion.execute(
            text("UPDATE jurisdicciones SET parent_id = 'AR-C' WHERE id = 'AR'")
        )


def test_alias_de_fuente_no_admite_ciclos(conexion: Connection) -> None:
    """F17/F65 son una fuente canónica y un alias: la cadena no puede cerrarse
    sobre sí misma ni dejar de tener contenido canónico."""
    for sid in ("F17", "F65"):
        conexion.execute(
            text(
                "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, prioridad) "
                "VALUES (:sid, :nombre, 'DOCUMENTO', 'DISCOVERY', 'NO_VERIFICADO', 'P2')"
            ),
            {"sid": sid, "nombre": f"Fuente {sid}"},
        )
    conexion.execute(text("UPDATE fuentes SET alias_of = 'F17' WHERE source_id = 'F65'"))
    with pytest.raises(DBAPIError, match="ciclo"):
        conexion.execute(text("UPDATE fuentes SET alias_of = 'F65' WHERE source_id = 'F17'"))


def test_fuente_no_puede_ser_alias_de_si_misma(conexion: Connection) -> None:
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, prioridad) "
            "VALUES ('F01', 'InfoLEG', 'DATASET', 'DISCOVERY', 'NO_VERIFICADO', 'P0')"
        )
    )
    with pytest.raises(IntegrityError):
        conexion.execute(text("UPDATE fuentes SET alias_of = 'F01' WHERE source_id = 'F01'"))


# --- URLs --------------------------------------------------------------------


def test_url_debe_ser_concreta_y_sin_plantilla(conexion: Connection) -> None:
    """Una plantilla sin resolver no es una dirección descargable."""
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, prioridad) "
            "VALUES ('F02', 'Fuente', 'FICHA_TRAMITE', 'DISCOVERY', 'NO_VERIFICADO', 'P1')"
        )
    )
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES ('F02', 'https://ejemplo.gob.ar/norma/{id}', 'DETALLE', "
                "'HTTP_GET_PUBLICO')"
            )
        )


def test_fuente_degradada_exige_motivo(conexion: Connection) -> None:
    """Una fuente no se degrada ni se retira en silencio."""
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, prioridad) "
                "VALUES ('F03', 'Fuente', 'DIRECTORIO', 'QUARANTINED', 'BLOQUEADA', 'P1')"
            )
        )
