"""`/v1/sesiones`: el estado mínimo de una conversación (P-025, P-037).

Cuatro operaciones y ninguna más: abrir, leer, corregir y borrar. No hay listado
—nadie tiene que poder recorrer las conversaciones de otros— y el identificador
es lo único que da acceso a una: quien lo tiene es quien la abrió.

Lo que se guarda es la intención, la jurisdicción, la fecha y los hechos que la
persona confirmó, con su procedencia. **Ningún mensaje.** El modelo rechaza
cualquier campo de más y la base rechaza cualquier clave de más; las dos cosas,
porque una sola se olvida.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection

from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.conversacion import sesion as ses
from backend_normativo.db.session import engine_api

router = APIRouter(prefix="/v1/sesiones", tags=["conversación"])


def conexion_sesion() -> Iterator[Connection]:
    """Escritura con el rol de la API, en su propia transacción."""
    with engine_api().begin() as conexion:
        yield conexion


def _vencida() -> HTTPException:
    """404 y no 410: para quien pregunta, una sesión vencida ya no existe."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorRespuesta(
            codigo=CodigoError.UNKNOWN_IDENTITY,
            detalle=(
                "Esa conversación ya no está. Vencen a los 30 minutos sin usarlas y a las "
                "dos horas de empezadas, y lo que habías confirmado se borró. Podés empezar "
                "una nueva."
            ),
        ).model_dump(mode="json"),
    )


class Contexto(BaseModel):
    """Lo que acota la orientación. Todo opcional: se completa de a poco."""

    model_config = ConfigDict(extra="forbid")

    intencion: str | None = Field(None, max_length=120)
    jurisdiccion: str | None = Field(None, max_length=32)
    fecha: str | None = Field(None, max_length=10)


class Hecho(BaseModel):
    """Un dato confirmado, o la decisión de no contestarlo."""

    model_config = ConfigDict(extra="forbid")

    clave: str = Field(min_length=1, max_length=80)
    valor: object | None = None
    origen: str = Field("declarado", pattern="^(declarado|inferido)$")
    # No contestar no es contestar que no, y el motor de reglas los distingue.
    rehusado: bool = False


@router.post("", status_code=201)
def abrir_sesion(conexion: Connection = Depends(conexion_sesion)) -> dict:
    """Empieza una conversación. No pide identidad ni deja rastro de quién."""
    return ses.abrir(conexion).a_dict()


@router.get("/{sesion_id}")
def leer_sesion(sesion_id: uuid.UUID, conexion: Connection = Depends(conexion_sesion)) -> dict:
    sesion = ses.tocar(conexion, sesion_id)
    if sesion is None:
        raise _vencida()
    return sesion.a_dict()


@router.patch("/{sesion_id}/contexto")
def anotar_contexto(
    sesion_id: uuid.UUID,
    contexto: Contexto,
    conexion: Connection = Depends(conexion_sesion),
) -> dict:
    sesion = ses.anotar_contexto(
        conexion,
        sesion_id,
        intencion=contexto.intencion,
        jurisdiccion=contexto.jurisdiccion,
        fecha=contexto.fecha,
    )
    if sesion is None:
        raise _vencida()
    return sesion.a_dict()


@router.put("/{sesion_id}/hechos")
def confirmar_hecho(
    sesion_id: uuid.UUID, hecho: Hecho, conexion: Connection = Depends(conexion_sesion)
) -> dict:
    """Confirma o corrige un hecho. La corrección sube la versión del estado.

    Esa versión es lo que permite marcar como reemplazada una respuesta que se
    calculó con el dato viejo, en lugar de dejar dos conclusiones distintas
    conviviendo en la misma pantalla.
    """
    try:
        sesion = ses.confirmar(
            conexion,
            sesion_id,
            clave=hecho.clave,
            valor=hecho.valor,
            origen=hecho.origen,
            rehusado=hecho.rehusado,
        )
    except ses.SesionInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorRespuesta(codigo=CodigoError.INVALID_REQUEST, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc
    if sesion is None:
        raise _vencida()
    return sesion.a_dict()


@router.delete("/{sesion_id}/hechos/{clave}")
def olvidar_hecho(
    sesion_id: uuid.UUID, clave: str, conexion: Connection = Depends(conexion_sesion)
) -> dict:
    """Saca un hecho: vuelve a desconocido, que no es lo mismo que falso."""
    sesion = ses.olvidar(conexion, sesion_id, clave=clave)
    if sesion is None:
        raise _vencida()
    return sesion.a_dict()


@router.delete("/{sesion_id}", status_code=204)
def borrar_sesion(sesion_id: uuid.UUID, conexion: Connection = Depends(conexion_sesion)) -> None:
    """«Borrar conversación». Borra de verdad, no marca como borrada."""
    ses.borrar(conexion, sesion_id)
