"""HU-028: propagar el impacto de un cambio y emitir el evento.

Un cambio en una norma no afecta solo a esa norma. Afecta a los beneficios que
la citan, a las reglas que dependen de sus artículos y a las cuantías que se
calculan con parámetros que ella fija. Sin propagación, un monto viejo se sigue
sirviendo hasta que alguien lo note a mano.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    Severidad,
    TipoEventoOutbox,
    TipoIncidencia,
)


@dataclass
class Impacto:
    norma_id: uuid.UUID
    normas_dependientes: list[str] = field(default_factory=list)
    beneficios_afectados: list[str] = field(default_factory=list)
    reglas_afectadas: int = 0
    parametros_afectados: list[str] = field(default_factory=list)
    eventos_emitidos: int = 0
    incidencias_creadas: int = 0

    @property
    def hay_impacto(self) -> bool:
        return bool(
            self.normas_dependientes
            or self.beneficios_afectados
            or self.reglas_afectadas
            or self.parametros_afectados
        )


def propagar(
    conexion: Connection,
    norma_id: uuid.UUID,
    *,
    motivo: str,
    idempotency_key: str,
) -> Impacto:
    """Marca lo alcanzado por un cambio y deja el evento en el outbox."""
    impacto = Impacto(norma_id=norma_id)

    # Normas que dependen de esta: las que la citan o la reglamentan.
    impacto.normas_dependientes = [
        fila[0]
        for fila in conexion.execute(
            text(
                "SELECT DISTINCT o.tipo || ' ' || coalesce(o.numero, '?') || '/' || "
                "       coalesce(o.anio::text, '?') "
                "  FROM relaciones_normativas r JOIN normas o ON o.id = r.norma_origen_id "
                " WHERE r.norma_destino_id = :n"
            ),
            {"n": norma_id},
        )
    ]

    impacto.beneficios_afectados = [
        fila[0]
        for fila in conexion.execute(
            text(
                "SELECT DISTINCT b.codigo FROM beneficio_normas bn "
                "  JOIN norma_versiones nv ON nv.registro_version_id = bn.norma_version_id "
                "  JOIN beneficio_versiones bv "
                "    ON bv.registro_version_id = bn.beneficio_version_id "
                "  JOIN beneficios b ON b.id = bv.beneficio_id "
                " WHERE nv.norma_id = :n"
            ),
            {"n": norma_id},
        )
    ]

    impacto.reglas_afectadas = conexion.execute(
        text(
            "SELECT count(*) FROM reglas r "
            "  JOIN beneficio_normas bn "
            "    ON bn.beneficio_version_id = r.beneficio_version_id "
            "  JOIN norma_versiones nv ON nv.registro_version_id = bn.norma_version_id "
            " WHERE nv.norma_id = :n"
        ),
        {"n": norma_id},
    ).scalar_one()

    # Las versiones alcanzadas vuelven a revisión: seguir sirviéndolas como
    # frescas después de un cambio en su norma sería servir un dato vencido.
    conexion.execute(
        text(
            "UPDATE registro_versiones SET reverificar_antes_de = now() "
            " WHERE id IN (SELECT registro_version_id FROM norma_versiones WHERE norma_id = :n)"
        ),
        {"n": norma_id},
    )

    if impacto.hay_impacto:
        conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(registro_version_id, tipo, severidad, estado, descripcion, responsable_rol) "
                "SELECT nv.registro_version_id, CAST(:tipo AS varchar), CAST(:sev AS varchar), "
                "       'ABIERTA', :desc, 'monitoreo' "
                "  FROM norma_versiones nv WHERE nv.norma_id = :n "
                "  AND NOT EXISTS (SELECT 1 FROM incidencias_revision i "
                "                  WHERE i.registro_version_id = nv.registro_version_id "
                "                    AND i.tipo = :tipo AND i.estado <> 'RESUELTA')"
            ),
            {
                "n": norma_id,
                "tipo": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "sev": Severidad.HIGH.value,
                "desc": (
                    f"{motivo} Alcanza a {len(impacto.normas_dependientes)} norma(s) que la "
                    f"citan, {len(impacto.beneficios_afectados)} beneficio(s) y "
                    f"{impacto.reglas_afectadas} regla(s). Hay que revisar antes de volver "
                    "a publicar."
                ),
            },
        )
        impacto.incidencias_creadas = 1

    conexion.execute(
        text(
            "INSERT INTO eventos_outbox (tipo, aggregate_id, payload, idempotency_key) "
            "VALUES (:tipo, :agg, :payload, :clave) "
            "ON CONFLICT (idempotency_key) DO NOTHING"
        ),
        {
            "tipo": TipoEventoOutbox.NORMA_ACTUALIZADA.value,
            "agg": str(norma_id),
            "payload": json.dumps(
                {
                    "norma_id": str(norma_id),
                    "motivo": motivo,
                    "normas_dependientes": impacto.normas_dependientes,
                    "beneficios_afectados": impacto.beneficios_afectados,
                    "reglas_afectadas": impacto.reglas_afectadas,
                },
                ensure_ascii=False,
            ),
            "clave": idempotency_key,
        },
    )
    impacto.eventos_emitidos = 1
    return impacto
