"""Qué fuentes toca revisar.

La frecuencia es de revisión, no de vencimiento: que una fuente esté vencida en
frescura no dice nada sobre la vigencia de lo que publicó. Este módulo solo
decide a quién le toca, no qué se puede afirmar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Connection, text

from backend_normativo.db import vocabularios as voc

# Estados desde los que tiene sentido volver a pedir. Una fuente retirada o solo
# de referencia no se reintenta sola: sale de acá por una decisión de revisión.
ESTADOS_CAPTURABLES = (
    voc.EstadoFuente.DISCOVERY.value,
    voc.EstadoFuente.ACTIVE.value,
    voc.EstadoFuente.DEGRADED.value,
)


@dataclass(frozen=True)
class FuentePendiente:
    source_id: str
    nombre: str
    prioridad: str
    estado: str
    ultima_corrida: datetime | None
    motivo: str


def fuentes_pendientes(
    conexion: Connection, *, ahora: datetime | None = None, limite: int | None = None
) -> list[FuentePendiente]:
    """Fuentes cuya última corrida exitosa quedó fuera de su frecuencia.

    Quedan fuera las que la política no habilita automatizar y las que no tienen
    ninguna URL: su brecha se resuelve por descubrimiento o carga manual, no
    insistiendo contra una dirección que no existe.
    """
    ahora = ahora or datetime.now(UTC)
    filas = conexion.execute(
        text(
            """
            WITH ultima AS (
                SELECT DISTINCT ON (source_id) source_id, inicio, estado
                  FROM corridas_ingesta
                 WHERE estado IN ('COMPLETA', 'PARCIAL')
                 ORDER BY source_id, inicio DESC
            ),
            config AS (
                SELECT DISTINCT ON (source_id) source_id, frecuencia
                  FROM fuente_config_versiones
                 ORDER BY source_id, version DESC
            )
            SELECT f.source_id, f.nombre, f.prioridad, f.estado,
                   u.inicio AS ultima_corrida,
                   c.frecuencia
              FROM fuentes f
              JOIN config c ON c.source_id = f.source_id
              LEFT JOIN ultima u ON u.source_id = f.source_id
             WHERE f.estado = ANY(:estados)
               AND f.politica_acceso = :politica
               AND EXISTS (SELECT 1 FROM fuente_urls fu WHERE fu.source_id = f.source_id)
               AND (u.inicio IS NULL OR u.inicio + coalesce(c.frecuencia, INTERVAL '30 days')
                    <= :ahora)
             ORDER BY f.prioridad, u.inicio NULLS FIRST, f.source_id
            """
        ),
        {
            "estados": list(ESTADOS_CAPTURABLES),
            "politica": (
                voc.PoliticaAcceso.PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS.value
            ),
            "ahora": ahora,
        },
    ).mappings()

    pendientes = [
        FuentePendiente(
            source_id=fila["source_id"],
            nombre=fila["nombre"],
            prioridad=fila["prioridad"],
            estado=fila["estado"],
            ultima_corrida=fila["ultima_corrida"],
            motivo=(
                "nunca capturada"
                if fila["ultima_corrida"] is None
                else f"venció la frecuencia de {fila['frecuencia']}"
            ),
        )
        for fila in filas
    ]
    return pendientes[:limite] if limite else pendientes
