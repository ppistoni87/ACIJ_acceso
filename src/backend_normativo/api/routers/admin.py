"""Rutas de administración: resolver revisiones y publicar releases.

Son las únicas que escriben. Usan los módulos de revisión y publicación, nunca
SQL propio, y exigen credencial y actor declarado: lo que se decide queda en la
bitácora con nombre.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection

from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.api.dependencias import actor_de, conexion_administracion
from backend_normativo.curacion.revision import (
    ConflictoDeVersion,
    DecisionInvalida,
    Revisor,
)
from backend_normativo.publicacion.release import PublicacionRechazada, Publicador

router = APIRouter(prefix="/v1/admin", tags=["administración"])


class Vigencia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_tipo: str
    valid_desde: dt.date | None = None
    valid_hasta: dt.date | None = None
    condicion_vigencia: str | None = None
    estado_legal: str = "NO_DETERMINADA"
    ttl_dias: int = 30


class SolicitudResolucion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., min_length=1)
    fundamento_evidencia_id: uuid.UUID | None = None
    vigencia: Vigencia | None = None
    # Concurrencia optimista: en qué estado se leyó la incidencia.
    estado_esperado: str = "ABIERTA"


class SolicitudRelease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(..., min_length=1)
    candidatos: list[uuid.UUID] | None = None


@router.post("/revisiones/{incidencia_id}/resolver")
def resolver_revision(
    incidencia_id: uuid.UUID,
    solicitud: SolicitudResolucion,
    actor: str = Depends(actor_de),
    conexion: Connection = Depends(conexion_administracion),
) -> dict:
    try:
        resultado = Revisor(conexion).resolver(
            incidencia_id,
            decision=solicitud.decision,
            actor=actor,
            fundamento_evidencia_id=solicitud.fundamento_evidencia_id,
            vigencia=solicitud.vigencia.model_dump(mode="json") if solicitud.vigencia else None,
            estado_esperado=solicitud.estado_esperado,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorRespuesta(codigo=CodigoError.UNKNOWN_IDENTITY, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc
    except ConflictoDeVersion as exc:
        # 409 del contrato: la incidencia cambió desde que se leyó.
        raise HTTPException(
            status_code=409,
            detail=ErrorRespuesta(codigo=CodigoError.VERSION_CONFLICT, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc
    except DecisionInvalida as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorRespuesta(codigo=CodigoError.INVALID_REQUEST, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc

    return {
        "incidencia_id": str(resultado.incidencia_id),
        "version_afectada": str(resultado.version_afectada) if resultado.version_afectada else None,
        "aplico_vigencia": resultado.aplico_vigencia,
        "decidido_por": actor,
    }


@router.post("/releases")
def crear_release(
    solicitud: SolicitudRelease,
    actor: str = Depends(actor_de),
    conexion: Connection = Depends(conexion_administracion),
) -> dict:
    publicador = Publicador(conexion)
    try:
        resultado = publicador.publicar(
            actor=actor, motivo=solicitud.motivo, candidatos=solicitud.candidatos
        )
    except PublicacionRechazada as exc:
        # Los controles de calidad son un estado de dominio, no un fallo del
        # servidor: se devuelve qué falló y con qué observado.
        raise HTTPException(
            status_code=422,
            detail=ErrorRespuesta(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=str(exc),
                missing_fields=[g.id for g in exc.gates.fallidos],
            ).model_dump(mode="json"),
        ) from exc

    return {
        "release_id": str(resultado.release_id),
        "versiones_publicadas": resultado.versiones_publicadas,
        "fragmentos_citables": resultado.chunks_creados,
        "eventos_en_outbox": resultado.eventos_emitidos,
        "en_cuarentena": resultado.en_cuarentena,
        "gates": [
            {"id": g.id, "pasa": g.pasa, "observado": g.observado}
            for g in (resultado.gates.gates if resultado.gates else [])
        ],
        "aprobado_por": actor,
    }
