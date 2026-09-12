"""`POST /v1/devoluciones`: la mitad de la conversación que faltaba.

Hasta acá el sistema hablaba y nadie le podía contestar. Esta ruta recibe una
señal de un vocabulario cerrado —le sirvió, no le sirvió, quiere hablar con una
persona— y la asocia a la consulta por su `request_id`, que es el mismo que la
respuesta devolvió en la cabecera `X-Request-Id`.

No recibe texto. El modelo tiene `extra="forbid"` y `senal` es un enum, así que
un cliente que mande un comentario recibe 422 en vez de que el comentario entre
sin que nadie lo haya decidido. Eso es a propósito y está explicado en la
migración 0019: la caja de texto libre debajo de una respuesta sobre desalojos
es donde alguien escribe su caso.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection

from backend_normativo.api.devoluciones import Senal, registrar
from backend_normativo.db.session import engine_api

router = APIRouter(prefix="/v1", tags=["conversación"])


def conexion_devolucion() -> Iterator[Connection]:
    """Escritura con el rol de la API, en su propia transacción.

    No se reutiliza `conexion_lectura`: esa se abre sin transacción y confirmar
    sobre ella acoplaría la escritura de la devolución al ciclo de vida de una
    lectura. Es una dependencia aparte por la misma razón que lo es la de
    administración.
    """
    with engine_api().begin() as conexion:
        yield conexion


class Devolucion(BaseModel):
    """Lo único que se acepta. Cualquier campo de más es un 422."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "El identificador que la respuesta devolvió en la cabecera X-Request-Id. "
            "Une la señal con la consulta sin decir qué se preguntó."
        ),
    )
    senal: Senal


@router.post("/devoluciones", status_code=202)
def registrar_devolucion(
    devolucion: Devolucion, conexion: Connection = Depends(conexion_devolucion)
) -> dict:
    """Anota la señal y no devuelve nada más que el acuse.

    202 y no 201: lo que se hace con esto es leerlo después, agregado. No hay
    recurso que después se pueda ir a buscar, y no lo hay a propósito —una
    devolución individual no se consulta ni se corrige—.

    `registrada` en `false` significa que esa señal ya estaba: apretar dos veces
    no cuenta dos veces. No es un error y el frente muestra lo mismo.
    """
    nueva = registrar(conexion, request_id=devolucion.request_id, senal=devolucion.senal)
    return {"registrada": nueva, "senal": devolucion.senal.value}
