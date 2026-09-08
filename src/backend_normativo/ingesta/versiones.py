"""Reconocer una versión de documento que ya está.

Los importadores que traen datos y no normas —el padrón, los directorios, la
Defensoría, el calendario de feriados— crean una versión de documento por
captura. Reconocían la repetición por la captura, y eso alcanza mientras cada
descarga sea única: reejecutar la población vuelve a pedir el archivo, así que
la captura es otra fila aunque los bytes sean los mismos, y el intento de
insertar una versión con un hash que ya está choca contra la restricción que
justamente impide duplicarla.

Los mismos bytes son la misma versión del documento. Volver a pedirlo no lo
cambia: lo confirma.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import TipoVersionDocumento


def sha_de_la_captura(conexion: Connection, captura_id: uuid.UUID) -> str:
    return conexion.execute(
        text("SELECT sha256_raw FROM capturas WHERE id = :c"), {"c": captura_id}
    ).scalar_one()


def version_ya_existente(
    conexion: Connection,
    documento_id: uuid.UUID,
    captura_id: uuid.UUID,
    sha: str,
    tipo_version: str = TipoVersionDocumento.NO_DETERMINADO.value,
) -> uuid.UUID | None:
    """La versión de este documento para esta captura, o para estos bytes.

    Se busca por las dos cosas: por la captura, porque es lo más preciso cuando
    existe, y por el contenido, porque una descarga nueva de lo mismo no es una
    versión nueva. Si hay más de una se toma la primera por número de versión,
    que es la que se creó antes.
    """
    return conexion.execute(
        text(
            "SELECT id FROM documento_versiones "
            " WHERE documento_id = :d "
            "   AND (captura_id = :c OR (hash_texto = :h AND tipo_version = :tv)) "
            " ORDER BY version LIMIT 1"
        ),
        {"d": documento_id, "c": captura_id, "h": sha, "tv": tipo_version},
    ).scalar_one_or_none()


def proxima_version(conexion: Connection, documento_id: uuid.UUID) -> int:
    return conexion.execute(
        text(
            "SELECT coalesce(max(version), 0) + 1 FROM documento_versiones  WHERE documento_id = :d"
        ),
        {"d": documento_id},
    ).scalar_one()
