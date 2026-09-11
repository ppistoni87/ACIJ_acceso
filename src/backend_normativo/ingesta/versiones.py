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

import hashlib
import uuid
from collections.abc import Iterable

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import TipoVersionDocumento


def sha_de_la_captura(conexion: Connection, captura_id: uuid.UUID) -> str:
    """La huella de los bytes descargados.

    Sirve para saber si dos descargas trajeron lo mismo byte a byte, y **no**
    para decidir si hay una versión documental nueva: muchos sitios agregan a
    cada respuesta un token que cambia solo —el ofuscador de correos de
    Cloudflare, sin ir más lejos— así que los bytes difieren en cada descarga
    aunque el contenido sea idéntico. Versionar por esto crea una versión por
    corrida, para siempre. Para eso está `sha_del_contenido`.
    """
    return conexion.execute(
        text("SELECT sha256_raw FROM capturas WHERE id = :c"), {"c": captura_id}
    ).scalar_one()


def sha_del_contenido(partes: Iterable[object]) -> str:
    """La huella de lo que el importador leyó, no de lo que descargó.

    Un importador no guarda texto plano —su aporte son filas: oficinas, puntos
    de atención, feriados— así que la huella se arma con esas filas ya
    normalizadas. Dos lecturas del mismo directorio dan la misma huella aunque
    el servidor haya cambiado un token entre una y otra, que es justo lo que
    tiene que pasar para que reejecutar no invente una versión.

    El orden importa y se respeta: si el directorio reordena sus paneles, eso
    **sí** es contenido distinto y merece una versión nueva.
    """
    crudo = "\u001f".join("" if p is None else str(p) for p in partes)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()


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
