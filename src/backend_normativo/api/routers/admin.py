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
from sqlalchemy import Connection, text

from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.api.dependencias import actor_de, conexion_administracion
from backend_normativo.curacion.revision import (
    ConflictoDeVersion,
    DecisionInvalida,
    Revisor,
)
from backend_normativo.curacion.revision_reglas import (
    ConflictoDeRevision,
    RevisionInvalida,
    aprobar,
    detalle,
    marcar_en_revision,
    rechazar,
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


# Qué se puede decidir sobre una regla. No hay «publicar»: publicar es el corte
# de release y pasa por otra puerta, con su propio control.
DECISIONES = {
    "APROBAR": aprobar,
    "RECHAZAR": rechazar,
    "EN_REVISION": marcar_en_revision,
}


class SolicitudDecisionRegla(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., min_length=1)
    # Sin fundamento no se decide: dentro de seis meses nadie puede saber si se
    # revisó o se aprobó de apuro.
    fundamento: str = Field(..., min_length=1)
    # Concurrencia optimista: en qué estado la leyó quien decide.
    estado_esperado: str | None = None


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


@router.get("/reglas/{regla_id}")
def ver_regla(
    regla_id: uuid.UUID,
    conexion: Connection = Depends(conexion_administracion),
) -> dict:
    """El expediente de una regla: todo lo que hace falta para decidirla.

    Literal, interpretación, condición, dependencias, parámetros, vigencia y
    controles, juntos. Una condición se aprueba o no según de qué depende y
    sobre qué versión rige; pedirle a quien revisa que cruce seis pantallas es
    pedirle que no las cruce.
    """
    try:
        expediente = detalle(conexion, regla_id)
    except RevisionInvalida as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorRespuesta(codigo=CodigoError.UNKNOWN_IDENTITY, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc

    regla = expediente.regla
    return {
        "id": str(regla.id),
        "beneficio": regla.beneficio,
        "categoria": regla.categoria,
        "estado": regla.estado,
        "clase": regla.clase,
        "texto_literal": regla.texto_literal,
        "interpretacion": regla.descripcion,
        "condicion": expediente.ast,
        "tiene_condicion": regla.tiene_condicion,
        "requiere_revision": regla.requiere_revision,
        "motivo_revision": regla.motivo_revision,
        "norma": regla.norma,
        "ruta": regla.ruta,
        "dependencias": [
            {
                "tipo": d["tipo"],
                "regla_id": str(d["regla_referida_id"]),
                "categoria": d["categoria"],
                "estado": d["estado_revision"],
                "texto_literal": d["texto_literal"],
            }
            for d in expediente.dependencias
        ],
        "parametros": [
            {
                "codigo": p["codigo"],
                "concepto": p["concepto"],
                "unidad": p["unidad"],
                "rol": p["rol"],
                "tiene_valor": p["tiene_valor"],
            }
            for p in expediente.parametros
        ],
        "vigencia": (
            {
                "estado_revision": expediente.vigencia["estado_revision"],
                "valid_tipo": expediente.vigencia["valid_tipo"],
                "valid_desde": (
                    expediente.vigencia["valid_desde"].isoformat()
                    if expediente.vigencia["valid_desde"]
                    else None
                ),
                "valid_hasta": (
                    expediente.vigencia["valid_hasta"].isoformat()
                    if expediente.vigencia["valid_hasta"]
                    else None
                ),
                "publicada": expediente.vigencia["publicada"],
            }
            if expediente.vigencia
            else None
        ),
        "controles": [
            {
                "control_id": c["control_id"],
                "resultado": c["resultado"],
                "severidad": c["severidad"],
            }
            for c in expediente.controles
        ],
    }


@router.post("/reglas/{regla_id}/decidir")
def decidir_regla(
    regla_id: uuid.UUID,
    solicitud: SolicitudDecisionRegla,
    actor: str = Depends(actor_de),
    conexion: Connection = Depends(conexion_administracion),
) -> dict:
    """Aprueba, rechaza o marca en revisión, con actor y fundamento.

    Aprobar no publica: la regla queda aprobada y recién el corte de release la
    vuelve servible. Son dos decisiones distintas y las toma gente distinta.
    """
    transicion = DECISIONES.get(solicitud.decision.upper())
    if transicion is None:
        raise HTTPException(
            status_code=400,
            detail=ErrorRespuesta(
                codigo=CodigoError.INVALID_REQUEST,
                detalle=(
                    f"Decisión {solicitud.decision!r} desconocida. "
                    f"Las que hay: {', '.join(sorted(DECISIONES))}."
                ),
            ).model_dump(mode="json"),
        )
    try:
        transicion(
            conexion,
            regla_id,
            actor=actor,
            fundamento=solicitud.fundamento,
            estado_esperado=solicitud.estado_esperado,
        )
    except ConflictoDeRevision as exc:
        # 409: alguien decidió antes. No se sobrescribe.
        raise HTTPException(
            status_code=409,
            detail=ErrorRespuesta(codigo=CodigoError.VERSION_CONFLICT, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc
    except RevisionInvalida as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorRespuesta(codigo=CodigoError.INVALID_REQUEST, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc

    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla_id}
    ).scalar_one()
    return {
        "id": str(regla_id),
        "estado": estado,
        "decidido_por": actor,
        # Aprobada no es servible: falta el corte de publicación.
        "publicada": False,
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
