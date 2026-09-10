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
from backend_normativo.seguridad.credenciales import (
    IDENTIDAD_AUTODECLARADA,
    PREFIJO,
    ROLES,
    CredencialInvalida,
    Identidad,
    verificar,
)

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


# Modo de desarrollo. Con esto en `1`, y solo con esto, se admite la puerta
# vieja: un token compartido de `BN_ADMIN_TOKENS` y el actor escrito en
# `X-Actor`. Sirve para probar sin montar credenciales, y todo lo que se firme
# así queda marcado `AUTODECLARADA` en la bitácora para siempre. En producción no
# se pone: el plan dice, con nombre, que no se acepta un X-Actor libre como
# identidad de producción.
VARIABLE_MODO = "BN_IDENTIDAD_MODO"
MODO_DESARROLLO = "desarrollo"


def _modo_desarrollo() -> bool:
    return os.environ.get(VARIABLE_MODO, "").strip().lower() == MODO_DESARROLLO


def _rechazar(codigo: int, detalle: str) -> HTTPException:
    return HTTPException(
        status_code=codigo,
        detail=ErrorRespuesta(codigo=CodigoError.NOT_AUTHORIZED, detalle=detalle).model_dump(
            mode="json"
        ),
    )


def _revocada(conexion: Connection, jti: str) -> bool:
    if not jti:
        return False
    return (
        conexion.execute(
            text("SELECT 1 FROM credenciales_revocadas WHERE jti = :j"), {"j": jti}
        ).scalar_one_or_none()
        is not None
    )


def identidad_admin(
    conexion: Connection = Depends(conexion_administracion),
    autorizacion: str | None = Header(None, alias="Authorization"),
    declarado: str | None = Header(None, alias="X-Actor"),
) -> Identidad:
    """Quién hace la operación, establecido y no declarado.

    El orden importa: primero se intenta la credencial firmada, que es la única
    que identifica a una persona. La puerta vieja —token compartido más
    `X-Actor`— solo se considera si el modo de desarrollo está puesto, y lo que
    entre por ahí queda marcado en la bitácora como autodeclarado.
    """
    if not autorizacion or not autorizacion.startswith("Bearer "):
        raise _rechazar(401, "Falta la credencial de administración.")
    token = autorizacion.removeprefix("Bearer ").strip()

    if token.startswith(f"{PREFIJO}."):
        try:
            identidad = verificar(token)
        except CredencialInvalida as error:
            raise _rechazar(403, str(error)) from error
        if _revocada(conexion, identidad.jti):
            raise _rechazar(
                403,
                "Esta credencial fue revocada. Pedí una nueva a quien administra el "
                "servicio; la revocación no se puede deshacer.",
            )
        return identidad

    compartidos = {
        t.strip() for t in os.environ.get(VARIABLE_TOKENS_ADMIN, "").split(",") if t.strip()
    }
    if not compartidos:
        raise _rechazar(
            403,
            "La credencial no tiene la forma de una credencial firmada y no hay otra "
            "forma de identificarse habilitada.",
        )
    if not _modo_desarrollo():
        raise _rechazar(
            403,
            "Un token compartido no identifica a una persona: identifica al despliegue, "
            "y quien lo tenga podría firmar como cualquiera. Se admite solo con "
            f"{VARIABLE_MODO}={MODO_DESARROLLO}. Emití una credencial firmada con "
            "`bn operacion emitir-credencial`.",
        )
    if token not in compartidos:
        raise _rechazar(403, "La credencial no autoriza operaciones de administración.")
    if not declarado or not declarado.strip():
        raise _rechazar(
            401,
            "En modo desarrollo el actor se declara en la cabecera X-Actor, y queda "
            "registrado en la bitácora como autodeclarado.",
        )
    return Identidad(
        actor=declarado.strip(),
        roles=frozenset(ROLES),
        procedencia=IDENTIDAD_AUTODECLARADA,
    )


class Administracion:
    """Conexión y quién la usa, con la procedencia puesta en la sesión.

    El `SET LOCAL` se hace acá y no en cada sitio que escribe en la bitácora
    —son siete— porque alcanza con que uno se olvide para que un evento quede
    sin decir cómo se estableció su actor.
    """

    def __init__(
        self,
        conexion: Connection = Depends(conexion_administracion),
        identidad: Identidad = Depends(identidad_admin),
    ) -> None:
        self.conexion = conexion
        self.identidad = identidad
        conexion.execute(
            text("SELECT set_config('bn.identidad', :valor, true)"),
            {"valor": identidad.procedencia},
        )

    @property
    def actor(self) -> str:
        return self.identidad.actor

    def exigir(self, rol: str) -> None:
        """Corta la operación si la credencial no lleva ese rol."""
        if not self.identidad.puede(rol):
            raise _rechazar(
                403,
                f"Esta credencial no autoriza a {rol}. Lleva "
                f"{', '.join(sorted(self.identidad.roles)) or 'ningún rol'}.",
            )


def exigir_rol(rol: str):
    """Dependencia que exige un rol y devuelve la administración ya abierta."""

    def _dependencia(admin: Administracion = Depends()) -> Administracion:
        admin.exigir(rol)
        return admin

    return _dependencia


def actor_de(admin: Administracion = Depends()) -> str:
    """Quién realiza la operación, para las rutas que solo necesitan el nombre."""
    return admin.actor
