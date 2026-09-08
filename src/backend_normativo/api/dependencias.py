"""Dependencias compartidas de la API.

La API lee con el rol `lector_api`, que no tiene escritura ni acceso a staging.
Las rutas de administración usan otro motor y exigen autorización explícita: son
las únicas que escriben, y lo hacen a través de los módulos de revisión y
publicación, nunca con SQL propio.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import Connection, text

from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.db.session import engine_api, engine_migrador

# Variable de entorno con las credenciales de administración, separadas por
# comas. Sin ella, las rutas de administración quedan cerradas: no hay valor por
# defecto que las abra.
VARIABLE_TOKENS_ADMIN = "BN_ADMIN_TOKENS"


def conexion_lectura() -> Iterator[Connection]:
    with engine_api().connect() as conexion:
        yield conexion


def conexion_administracion() -> Iterator[Connection]:
    with engine_migrador().begin() as conexion:
        yield conexion


def as_of(
    fecha: dt.date | None = Query(
        None,
        alias="as_of",
        description="Fecha para la que se consulta. Por omisión, hoy.",
    ),
) -> dt.date:
    return fecha or dt.date.today()


def known_at(
    instante: dt.datetime | None = Query(
        None,
        alias="known_at",
        description=(
            "Instante de conocimiento: qué sabía el sistema en ese momento. "
            "Permite reproducir una respuesta pasada."
        ),
    ),
) -> dt.datetime:
    if instante is None:
        return dt.datetime.now(dt.UTC)
    return instante if instante.tzinfo else instante.replace(tzinfo=dt.UTC)


def release_vigente(conexion: Connection, momento: dt.datetime) -> uuid.UUID | None:
    """Release publicado más reciente a ese instante de conocimiento.

    Una consulta se resuelve entera contra un release: mezclar dos sería servir
    una respuesta que ningún corte del corpus sostiene.
    """
    return conexion.execute(
        text(
            "SELECT id FROM releases WHERE estado = 'PUBLICADO' AND publicado_en <= :m "
            "ORDER BY publicado_en DESC LIMIT 1"
        ),
        {"m": momento},
    ).scalar_one_or_none()


class Contexto:
    """Lo que toda ruta de lectura necesita resolver antes de responder."""

    def __init__(
        self,
        conexion: Connection = Depends(conexion_lectura),
        fecha: dt.date = Depends(as_of),
        momento: dt.datetime = Depends(known_at),
    ) -> None:
        self.conexion = conexion
        self.as_of = fecha
        self.known_at = momento
        self.release_id = release_vigente(conexion, momento)

    @property
    def hay_release(self) -> bool:
        return self.release_id is not None


def exigir_administrador(
    autorizacion: str | None = Header(None, alias="Authorization"),
) -> str:
    """Autoriza una operación de administración.

    Es deliberadamente simple y explícita: sin la variable de entorno
    configurada, las rutas de administración están cerradas. No hay
    credencial por defecto ni modo de desarrollo que las abra.
    """
    tokens = {t.strip() for t in os.environ.get(VARIABLE_TOKENS_ADMIN, "").split(",") if t.strip()}
    if not tokens:
        raise HTTPException(
            status_code=503,
            detail=ErrorRespuesta(
                codigo=CodigoError.NOT_AUTHORIZED,
                detalle=(
                    "Las operaciones de administración están deshabilitadas: no hay "
                    f"credenciales configuradas en {VARIABLE_TOKENS_ADMIN}."
                ),
            ).model_dump(mode="json"),
        )
    if not autorizacion or not autorizacion.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=ErrorRespuesta(
                codigo=CodigoError.NOT_AUTHORIZED,
                detalle="Falta la credencial de administración.",
            ).model_dump(mode="json"),
        )
    token = autorizacion.removeprefix("Bearer ").strip()
    if token not in tokens:
        raise HTTPException(
            status_code=403,
            detail=ErrorRespuesta(
                codigo=CodigoError.NOT_AUTHORIZED,
                detalle="La credencial no autoriza operaciones de administración.",
            ).model_dump(mode="json"),
        )
    return token


def actor_de(
    actor: str | None = Header(None, alias="X-Actor"),
    token: str = Depends(exigir_administrador),
) -> str:
    """Quién realiza la operación. Queda en la bitácora, así que es obligatorio."""
    if not actor or not actor.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorRespuesta(
                codigo=CodigoError.INVALID_REQUEST,
                detalle=(
                    "Toda operación de administración tiene que declarar quién la realiza "
                    "en la cabecera X-Actor: queda registrada en la bitácora."
                ),
            ).model_dump(mode="json"),
        )
    return actor.strip()
