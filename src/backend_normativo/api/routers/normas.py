"""`GET /v1/normas` y `GET /v1/normas/{id}`."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from backend_normativo.api import consultas
from backend_normativo.api.contratos import (
    Advertencia,
    CodigoError,
    DataStatus,
    ErrorRespuesta,
    NormaDetalle,
    NormaResumen,
    Pagina,
    Respuesta,
)
from backend_normativo.api.dependencias import Contexto

router = APIRouter(prefix="/v1/normas", tags=["normas"])


@router.get("", response_model=Respuesta[Pagina[NormaResumen]])
def listar_normas(
    contexto: Contexto = Depends(),
    texto: str | None = Query(None, description="Búsqueda textual en el título."),
    jurisdiccion: str | None = Query(None),
    tipo: str | None = Query(None),
    numero: str | None = Query(None),
    anio: int | None = Query(None),
    materia: str | None = Query(None),
    limite: int = Query(25, ge=1, le=100),
    desplazamiento: int = Query(0, ge=0),
) -> Respuesta[Pagina[NormaResumen]]:
    """Normas del corpus con su cobertura de campos.

    Devuelve normas identificadas aunque todavía no tengan versiones publicadas:
    saber que una norma existe y que su ficha está incompleta es información
    útil, y ocultarla haría creer que no existe.
    """
    items, total = consultas.buscar_normas(
        contexto.conexion,
        texto_libre=texto,
        jurisdiccion=jurisdiccion,
        tipo=tipo,
        numero=numero,
        anio=anio,
        materia=materia,
        limite=limite,
        desplazamiento=desplazamiento,
    )

    advertencias: list[Advertencia] = []
    publicadas = sum(1 for i in items if i.versiones_publicadas)
    if not contexto.hay_release:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    "No hay ningún release publicado: se listan las normas identificadas, "
                    "pero ninguna versión puede servirse todavía."
                ),
            )
        )
    inciertas = [i for i in items if i.identidad_incierta]
    if inciertas:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.UNKNOWN_IDENTITY,
                detalle=(
                    f"{len(inciertas)} norma(s) están en identidad incierta y no se fusionan "
                    "con ninguna otra hasta resolverlo."
                ),
            )
        )

    if not items:
        estado = DataStatus.SIN_RESULTADOS
    elif publicadas == len(items):
        estado = DataStatus.PUBLICADO
    elif publicadas:
        estado = DataStatus.PARCIAL
    else:
        estado = DataStatus.NO_PUBLICABLE

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=estado,
        data=Pagina(items=items, total=total, limite=limite, desplazamiento=desplazamiento),
        warnings=advertencias,
    )


@router.get("/{norma_id}", response_model=Respuesta[NormaDetalle])
def obtener_norma(
    norma_id: uuid.UUID,
    contexto: Contexto = Depends(),
    capacidad: str = Query(
        "IDENTIFICACION",
        description="Capacidad para la que se evalúa si cada versión puede servirse.",
    ),
) -> Respuesta[NormaDetalle]:
    """Ficha de una norma: versiones, siete campos, relaciones y pendientes.

    Cada versión declara si puede servirse para la capacidad consultada y, si no,
    por qué. Una abstención explicada es información; una lista vacía no.
    """
    norma = consultas.obtener_norma(contexto.conexion, norma_id)
    if norma is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorRespuesta(
                codigo=CodigoError.UNKNOWN_IDENTITY,
                detalle=f"No hay ninguna norma con el identificador {norma_id}.",
                as_of=contexto.as_of,
                known_at=contexto.known_at,
            ).model_dump(mode="json"),
        )

    versiones = consultas.versiones_de(
        contexto.conexion,
        norma_id,
        fecha=contexto.as_of,
        momento=contexto.known_at,
        capacidad=capacidad,
    )
    campos, faltantes = consultas.campos_de(contexto.conexion, norma_id)
    relaciones = consultas.relaciones_de(contexto.conexion, norma_id)
    pendientes = consultas.referencias_pendientes_de(contexto.conexion, norma_id)
    evidencia = consultas.evidencias_de(contexto.conexion, norma_id)

    advertencias: list[Advertencia] = []
    servibles = [v for v in versiones if v.servible]
    if not servibles:
        motivos = sorted({m for v in versiones for m in v.motivos_no_servible})
        advertencias.append(
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    f"Ninguna versión puede servirse para «{capacidad}» "
                    f"al {contexto.as_of.isoformat()}: {'; '.join(motivos) or 'sin versiones'}."
                ),
            )
        )
    if pendientes:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    f"{len(pendientes)} cita(s) a otras normas todavía no se resolvieron "
                    "contra el corpus."
                ),
            )
        )
    if any(r.estado_revision == "CANDIDATE" for r in relaciones):
        advertencias.append(
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    "Hay relaciones normativas candidatas sin revisión: se informan como "
                    "tales y no como relaciones establecidas."
                ),
            )
        )

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if servibles else DataStatus.NO_PUBLICABLE,
        data=NormaDetalle(
            norma=norma,
            versiones=versiones,
            campos=campos,
            relaciones=relaciones,
            referencias_pendientes=pendientes,
        ),
        evidence=evidencia,
        missing_fields=faltantes,
        warnings=advertencias,
    )
