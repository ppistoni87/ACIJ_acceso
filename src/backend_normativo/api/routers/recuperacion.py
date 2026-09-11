"""`POST /v1/recuperacion` y `GET /v1/cobertura`.

La recuperación devuelve unidades citables del release autorizado. Sirve para
explicar y citar, nunca para reemplazar una consulta estructurada: un monto, una
fecha o un teléfono se consultan con SQL y tipos, no mezclando fragmentos.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from backend_normativo.api.contratos import (
    Advertencia,
    CodigoError,
    DataStatus,
    Respuesta,
)
from backend_normativo.api.dependencias import Administracion, Contexto, exigir_rol
from backend_normativo.calidad.cobertura import medir
from backend_normativo.recuperacion.busqueda import buscar as buscar_fragmentos
from backend_normativo.recuperacion.embeddings import embebedor_compartido
from backend_normativo.seguridad.credenciales import ROL_AUDITOR

router = APIRouter(prefix="/v1", tags=["recuperación"])


class SolicitudRecuperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consulta: str
    jurisdiccion: str | None = None
    beneficio: str | None = None
    limite: int = Field(10, ge=1, le=50)


class Fragmento(BaseModel):
    chunk_id: uuid.UUID
    texto: str
    norma: str
    unidad: str | None
    url_fuente: str | None
    relevancia: float
    # De qué mitad salió. Sirve para leer el resultado: un fragmento que
    # encontró solo la búsqueda semántica no comparte ninguna palabra con la
    # consulta, y eso conviene saberlo antes de citarlo.
    encontrado_por: str = "lexica"


class ResultadoRecuperacion(BaseModel):
    fragmentos: list[Fragmento] = Field(default_factory=list)
    conflictos_pertinentes: list[dict] = Field(default_factory=list)
    aclaracion: str = (
        "Los fragmentos sirven para explicar y citar. Los montos, las fechas y los datos "
        "de contacto se consultan con las operaciones tipadas, no combinando fragmentos."
    )


@router.post("/recuperacion", response_model=Respuesta[ResultadoRecuperacion])
def recuperar(
    solicitud: SolicitudRecuperacion, contexto: Contexto = Depends()
) -> Respuesta[ResultadoRecuperacion]:
    if not contexto.hay_release:
        return Respuesta(
            release_id=None,
            as_of=contexto.as_of,
            known_at=contexto.known_at,
            data_status=DataStatus.NO_PUBLICABLE,
            data=ResultadoRecuperacion(),
            warnings=[
                Advertencia(
                    codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                    detalle=(
                        "No hay ningún release publicado. No se recupera de staging: "
                        "el corpus servible es solo lo publicado."
                    ),
                )
            ],
        )

    # La búsqueda vive en `recuperacion.busqueda`: la mitad léxica y la
    # vectorial comparten los mismos filtros, y compartirlos importa más que
    # tenerlos cerca. Si una se olvidara de uno, la fusión metería de vuelta lo
    # que la otra descartó.
    # Sin el extra de recuperación instalado, `embebedor_compartido` devuelve
    # `None`, la mitad léxica sirve sola y la respuesta lo declara. No se cae:
    # una consulta contestada peor es mejor que una no contestada, siempre que
    # quien la lee sepa que fue peor.
    hallazgo = buscar_fragmentos(
        contexto.conexion,
        solicitud.consulta,
        release_id=contexto.release_id,
        embebedor=embebedor_compartido(),
        limite=solicitud.limite,
        jurisdiccion=solicitud.jurisdiccion,
        beneficio=solicitud.beneficio,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
    )
    filas = hallazgo.fragmentos

    conflictos = [
        {
            "tipo": fila["tipo"],
            "severidad": fila["severidad"],
            "descripcion": fila["descripcion"],
        }
        for fila in contexto.conexion.execute(
            text(
                "SELECT i.tipo, i.severidad, left(i.descripcion, 300) AS descripcion "
                "  FROM incidencias_revision i "
                " WHERE i.estado IN ('ABIERTA', 'EN_REVISION') "
                "   AND i.severidad IN ('CRITICAL', 'HIGH') LIMIT 10"
            )
        ).mappings()
    ]

    advertencias: list[Advertencia] = [
        Advertencia(codigo=CodigoError.INSUFFICIENT_EVIDENCE, detalle=aviso)
        for aviso in hallazgo.avisos
    ]
    if conflictos:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.CONFLICT,
                detalle=(
                    f"Hay {len(conflictos)} conflicto(s) abiertos de severidad alta en el "
                    "corpus. Se informan junto con los fragmentos."
                ),
            )
        )

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if filas else DataStatus.SIN_RESULTADOS,
        data=ResultadoRecuperacion(
            fragmentos=[
                Fragmento(
                    chunk_id=fragmento.chunk_id,
                    texto=fragmento.texto,
                    norma=fragmento.norma,
                    unidad=fragmento.unidad,
                    url_fuente=fragmento.url_fuente,
                    relevancia=fragmento.puntaje,
                    encontrado_por=fragmento.encontrado_por,
                )
                for fragmento in filas
            ],
            conflictos_pertinentes=conflictos,
        ),
        warnings=advertencias,
    )


@router.get("/cobertura", response_model=Respuesta[dict])
def cobertura(
    contexto: Contexto = Depends(),
    admin: Administracion = Depends(exigir_rol(ROL_AUDITOR)),
) -> Respuesta[dict]:
    """Denominadores y pendientes, separados de lo validado y publicable.

    Va con credencial de auditoría porque `medir()` lee el estado operativo
    —fuentes, capturas, incidencias— y no una proyección publicada. El contrato
    ya lo declaraba de «alcance autorizado»; la implementación lo servía abierto
    y con la conexión del lector, que no tiene permiso sobre `capturas`: en
    cualquier despliegue con roles de verdad esto devolvía 500, y darle el
    permiso al lector hubiera consagrado que el lector lea staging.
    """
    metricas = medir(admin.conexion)
    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO,
        data=metricas.a_dict(),
        warnings=[
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    "Los campos evaluados y los campos con valor sustantivo se informan por "
                    "separado. Un campo revisado sin información no cuenta como completo."
                ),
            )
        ],
    )
