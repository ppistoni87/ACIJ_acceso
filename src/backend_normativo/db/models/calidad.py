"""Controles de calidad e incidencias de revisión."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class ControlCalidad(Base):
    """Resultado de un control (DQ01–DQ18) sobre una versión o una corrida.

    Se guardan lo observado y lo esperado: un control que falla debe poder
    explicarse sin volver a ejecutarlo.
    """

    __tablename__ = "controles_calidad"

    id: Mapped[uuid.UUID] = pk_uuid()
    registro_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), index=True
    )
    corrida_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("corridas_ingesta.id", ondelete="RESTRICT"), index=True
    )
    control_id: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[str] = mapped_column(String(16), nullable=False)
    severidad: Mapped[str] = mapped_column(String(16), nullable=False)
    observado: Mapped[dict | None] = mapped_column(JSONB)
    esperado: Mapped[dict | None] = mapped_column(JSONB)
    ejecutado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("resultado", voc.ResultadoControl),
        check_vocabulario("severidad", voc.Severidad),
        # Un control que falla sin decir qué observó no es evidencia.
        CheckConstraint(
            "resultado <> 'FALLA' OR observado IS NOT NULL", name="falla_con_observado"
        ),
        CheckConstraint(
            "registro_version_id IS NOT NULL OR corrida_id IS NOT NULL",
            name="control_con_objeto",
        ),
        Index("ix_controles_calidad_control_resultado", "control_id", "resultado"),
        Index("ix_controles_calidad_ejecutado", "ejecutado_en"),
    )


class IncidenciaRevision(Base):
    """Conflicto o ambigüedad que necesita decisión humana.

    Resolver una incidencia no borra el conflicto histórico: se conserva quién
    decidió, con qué fundamento y cuándo. "Más reciente" o "más oficial" no es
    un algoritmo universal de desempate.
    """

    __tablename__ = "incidencias_revision"

    id: Mapped[uuid.UUID] = pk_uuid()
    registro_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), index=True
    )
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    severidad: Mapped[str] = mapped_column(String(16), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    # Candidatos en conflicto: se conservan todos, no solo el elegido.
    candidatos: Mapped[list | None] = mapped_column(JSONB)
    estado: Mapped[str] = mapped_column(String(16), nullable=False)
    responsable_rol: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(Text)
    decidido_por: Mapped[str | None] = mapped_column(Text)
    fundamento_evidencia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT")
    )
    resuelta_en: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoIncidencia),
        check_vocabulario("severidad", voc.Severidad),
        check_vocabulario("estado", voc.EstadoIncidencia),
        CheckConstraint(
            "estado <> 'RESUELTA' OR "
            "(decision IS NOT NULL AND decidido_por IS NOT NULL AND resuelta_en IS NOT NULL)",
            name="resuelta_con_decision_y_actor",
        ),
        Index("ix_incidencias_revision_estado_severidad", "estado", "severidad"),
    )
