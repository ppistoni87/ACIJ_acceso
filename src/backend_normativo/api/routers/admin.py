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
from sqlalchemy import text

from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.api.dependencias import (
    Administracion,
    exigir_rol,
)
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
    expediente,
    marcar_en_revision,
    rechazar,
)
from backend_normativo.publicacion.gates import evaluar_gates
from backend_normativo.publicacion.release import PublicacionRechazada, Publicador
from backend_normativo.seguridad.credenciales import ROL_PUBLICADOR, ROL_REVISOR

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
    admin: Administracion = Depends(exigir_rol(ROL_REVISOR)),
) -> dict:
    actor, conexion = admin.actor, admin.conexion
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


@router.get("/reglas")
def listar_reglas(
    estado: str = "CANDIDATE",
    beneficio: str | None = None,
    clase: str | None = None,
    admin: Administracion = Depends(exigir_rol(ROL_REVISOR)),
) -> dict:
    """La cola de revisión: qué falta decidir y en qué pila cae cada una.

    Las pilas no son decoración. Una regla sin condición ejecutable y una con
    condición esperando confirmación no plantean lo mismo, y mandarlas a la
    misma cola hace que la segunda se apruebe sin mirar y la primera se apruebe
    sin poder. Vienen ordenadas por beneficio y por su ubicación en el texto,
    porque revisar un articulado salteado es cómo se aprueban contradicciones.
    """
    resultado = expediente(admin.conexion, estado=estado or None, beneficio=beneficio)
    reglas = [r for r in resultado.reglas if clase is None or r.clase == clase]

    por_clase: dict[str, int] = {}
    por_beneficio: dict[str, int] = {}
    for regla in resultado.reglas:
        por_clase[regla.clase] = por_clase.get(regla.clase, 0) + 1
        por_beneficio[regla.beneficio] = por_beneficio.get(regla.beneficio, 0) + 1

    return {
        "reglas": [
            {
                "id": str(r.id),
                "beneficio": r.beneficio,
                "categoria": r.categoria,
                "estado": r.estado,
                "clase": r.clase,
                "norma": r.norma,
                "ruta": r.ruta,
                "texto_literal": r.texto_literal,
                "interpretacion": r.descripcion,
                "tiene_condicion": r.tiene_condicion,
                "que_hay_que_decidir": r.que_hay_que_decidir,
            }
            for r in reglas
        ],
        "total": len(reglas),
        "por_estado": resultado.por_estado,
        "por_clase": dict(sorted(por_clase.items())),
        "por_beneficio": dict(sorted(por_beneficio.items())),
        "por_categoria": resultado.por_categoria,
        "sin_ubicar": resultado.sin_ubicar,
    }


@router.get("/reglas/{regla_id}")
def ver_regla(
    regla_id: uuid.UUID,
    admin: Administracion = Depends(exigir_rol(ROL_REVISOR)),
) -> dict:
    """El expediente de una regla: todo lo que hace falta para decidirla.

    Literal, interpretación, condición, dependencias, parámetros, vigencia y
    controles, juntos. Una condición se aprueba o no según de qué depende y
    sobre qué versión rige; pedirle a quien revisa que cruce seis pantallas es
    pedirle que no las cruce.
    """
    try:
        ficha = detalle(admin.conexion, regla_id)
    except RevisionInvalida as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorRespuesta(codigo=CodigoError.UNKNOWN_IDENTITY, detalle=str(exc)).model_dump(
                mode="json"
            ),
        ) from exc

    regla = ficha.regla
    return {
        "id": str(regla.id),
        "beneficio": regla.beneficio,
        "categoria": regla.categoria,
        "estado": regla.estado,
        "clase": regla.clase,
        "texto_literal": regla.texto_literal,
        "interpretacion": regla.descripcion,
        "condicion": ficha.ast,
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
            for d in ficha.dependencias
        ],
        "parametros": [
            {
                "codigo": p["codigo"],
                "concepto": p["concepto"],
                "unidad": p["unidad"],
                "rol": p["rol"],
                "tiene_valor": p["tiene_valor"],
            }
            for p in ficha.parametros
        ],
        "vigencia": (
            {
                "estado_revision": ficha.vigencia["estado_revision"],
                "valid_tipo": ficha.vigencia["valid_tipo"],
                "valid_desde": (
                    ficha.vigencia["valid_desde"].isoformat()
                    if ficha.vigencia["valid_desde"]
                    else None
                ),
                "valid_hasta": (
                    ficha.vigencia["valid_hasta"].isoformat()
                    if ficha.vigencia["valid_hasta"]
                    else None
                ),
                "publicada": ficha.vigencia["publicada"],
            }
            if ficha.vigencia
            else None
        ),
        "controles": [
            {
                "control_id": c["control_id"],
                "resultado": c["resultado"],
                "severidad": c["severidad"],
            }
            for c in ficha.controles
        ],
    }


@router.post("/reglas/{regla_id}/decidir")
def decidir_regla(
    regla_id: uuid.UUID,
    solicitud: SolicitudDecisionRegla,
    admin: Administracion = Depends(exigir_rol(ROL_REVISOR)),
) -> dict:
    """Aprueba, rechaza o marca en revisión, con actor y fundamento.

    Aprobar no publica: la regla queda aprobada y recién el corte de release la
    vuelve servible. Son dos decisiones distintas y las toma gente distinta.
    """
    actor, conexion = admin.actor, admin.conexion
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


@router.get("/releases/propuesta")
def propuesta_de_release(
    admin: Administracion = Depends(exigir_rol(ROL_PUBLICADOR)),
) -> dict:
    """Qué publicaría un corte ahora, con sus controles y lo que quedaría afuera.

    P-016 criterio 2. Publicar es irreversible en el sentido que importa —lo
    publicado se sirve, y quien consulta lo lee como el derecho vigente— así que
    quien firma tiene que poder ver antes qué entra, qué controles pasan y qué
    queda en cuarentena. Sin esto, confirmar es firmar a ciegas.

    Es una lectura: no crea nada. La ruta de creación es otra y exige el mismo
    rol.
    """
    publicador = Publicador(admin.conexion)
    candidatos = publicador.candidatos()
    controles = evaluar_gates(admin.conexion, candidatos)
    cuarentena = publicador.cuarentena()

    return {
        "candidatos": len(candidatos),
        "puede_publicar": bool(candidatos) and controles.pasa,
        "por_que_no": (
            ""
            if candidatos
            else "No hay ninguna versión aprobada y con vigencia resuelta esperando corte."
        ),
        "controles": [
            {
                "id": g.id,
                "descripcion": g.descripcion,
                "pasa": g.pasa,
                "observado": g.observado,
                "esperado": g.esperado,
            }
            for g in controles.gates
        ],
        "en_cuarentena": cuarentena,
        "aclaracion": (
            "La cuarentena es tan importante como lo publicable: sin ella, «no aparece "
            "en la respuesta» y «no existe» se vuelven indistinguibles."
        ),
    }


@router.post("/releases")
def crear_release(
    solicitud: SolicitudRelease,
    admin: Administracion = Depends(exigir_rol(ROL_PUBLICADOR)),
) -> dict:
    # Revisar y publicar son dos decisiones distintas y las toma gente
    # distinta: una credencial de revisor no abre esta ruta.
    actor, conexion = admin.actor, admin.conexion
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
