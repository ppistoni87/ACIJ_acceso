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
from backend_normativo.api.dependencias import Contexto
from backend_normativo.calidad.cobertura import medir

router = APIRouter(prefix="/v1", tags=["recuperación"])


class SolicitudRecuperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consulta: str
    jurisdiccion: str | None = None
    limite: int = Field(10, ge=1, le=50)


class Fragmento(BaseModel):
    chunk_id: uuid.UUID
    texto: str
    norma: str
    unidad: str | None
    url_fuente: str | None
    relevancia: float


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

    condiciones = ["c.release_id = :r", "c.tsv @@ plainto_tsquery('spanish', :q)"]
    parametros: dict[str, object] = {
        "r": contexto.release_id,
        "q": solicitud.consulta,
        "limite": solicitud.limite,
    }
    if solicitud.jurisdiccion:
        condiciones.append("n.jurisdiccion_id = :j")
        parametros["j"] = solicitud.jurisdiccion

    filas = (
        contexto.conexion.execute(
            text(
                "SELECT c.id, c.texto, u.ruta, f.url, "
                "       n.tipo || ' ' || coalesce(n.numero, '?') || '/' || "
                "       coalesce(n.anio::text, '?') AS norma, "
                "       ts_rank(c.tsv, plainto_tsquery('spanish', :q)) AS relevancia "
                "  FROM chunks c "
                "  JOIN unidades_documentales u ON u.id = c.unidad_id "
                "  JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id "
                "  JOIN normas n ON n.id = nv.norma_id "
                "  JOIN documento_versiones dv ON dv.id = u.doc_version_id "
                "  JOIN capturas cap ON cap.id = dv.captura_id "
                "  JOIN fuente_urls f ON f.id = cap.source_url_id "
                f" WHERE {' AND '.join(condiciones)} "
                " ORDER BY relevancia DESC LIMIT :limite"
            ),
            parametros,
        )
        .mappings()
        .all()
    )

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

    advertencias: list[Advertencia] = []
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
                    chunk_id=fila["id"],
                    texto=fila["texto"],
                    norma=fila["norma"],
                    unidad=fila["ruta"],
                    url_fuente=fila["url"],
                    relevancia=float(fila["relevancia"]),
                )
                for fila in filas
            ],
            conflictos_pertinentes=conflictos,
        ),
        warnings=advertencias,
    )


@router.get("/cobertura", response_model=Respuesta[dict])
def cobertura(contexto: Contexto = Depends()) -> Respuesta[dict]:
    """Denominadores y pendientes, separados de lo validado y publicable."""
    metricas = medir(contexto.conexion)
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
