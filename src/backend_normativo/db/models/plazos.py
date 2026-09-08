"""Plazos y calendarios.

Cada tipo de plazo tiene identidad propia: vigencia jurídica, convocatoria,
duración del beneficio, renovación, presentación documental, respuesta del
organismo, subsanación, recurso y fecha de pago no se colapsan en una única
fecha.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class Calendario(Base):
    """Un calendario administrativo no es universal: pertenece a una
    jurisdicción, tiene versión y cubre un rango de fechas conocido."""

    __tablename__ = "calendarios"

    id: Mapped[uuid.UUID] = pk_uuid()
    jurisdiccion_id: Mapped[str] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_desde: Mapped[dt.date] = mapped_column(Date, nullable=False)
    fecha_hasta: Mapped[dt.date] = mapped_column(Date, nullable=False)
    fuente_id: Mapped[str | None] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT")
    )
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        UniqueConstraint("jurisdiccion_id", "nombre", "version", name="uq_calendarios_version"),
        CheckConstraint("fecha_hasta >= fecha_desde", name="cobertura_ordenada"),
    )


class CalendarioExcepcion(Base):
    """Día no laborable o día hábil excepcional, con su motivo y evidencia.

    Fuera de la cobertura confirmada del calendario no se calcula un vencimiento
    hábil: se responde "desconocido".
    """

    __tablename__ = "calendario_excepciones"

    id: Mapped[uuid.UUID] = pk_uuid()
    calendario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calendarios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    fecha: Mapped[dt.date] = mapped_column(Date, nullable=False)
    es_habil: Mapped[bool] = mapped_column(Boolean, nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("calendario_id", "fecha", name="uq_calendario_excepciones_fecha"),
    )


class Plazo(Base):
    """Subtipo de `registro_versiones`.

    Exactamente un propietario principal entre beneficio, trámite y norma; los
    vínculos adicionales se resuelven navegando sus relaciones.

    Un intervalo fechado (`inicio`/`fin`) y uno relativo (`cantidad` + `unidad` +
    `evento_inicio`) son modalidades distintas y no se mezclan. El cómputo en
    días hábiles exige un calendario con cobertura, versión y jurisdicción.
    """

    __tablename__ = "plazos"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    # Identidad lógica del plazo a través de sus versiones; es lo que apunta
    # `registro_versiones.entidad_id`.
    plazo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    beneficio_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("beneficio_versiones.registro_version_id", ondelete="RESTRICT"), index=True
    )
    tramite_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tramite_versiones.registro_version_id", ondelete="RESTRICT"), index=True
    )
    norma_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("norma_versiones.registro_version_id", ondelete="RESTRICT"), index=True
    )
    calendario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("calendarios.id", ondelete="RESTRICT")
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    inicio: Mapped[dt.date | None] = mapped_column(Date)
    fin: Mapped[dt.date | None] = mapped_column(Date)
    hora_cierre: Mapped[dt.time | None] = mapped_column(Time)
    # Los plazos ciudadanos se computan en la zona del país salvo que la
    # fuente establezca otra.
    zona_horaria: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'America/Argentina/Buenos_Aires'")
    )
    cantidad: Mapped[int | None] = mapped_column(Integer)
    unidad: Mapped[str | None] = mapped_column(Text)
    tipo_dia: Mapped[str] = mapped_column(String(32), nullable=False)
    evento_inicio: Mapped[str | None] = mapped_column(Text)
    regla_computo: Mapped[dict | None] = mapped_column(JSONB)
    ciclo: Mapped[int | None] = mapped_column(Integer)
    convocatoria: Mapped[str | None] = mapped_column(Text)
    inclusivo_desde: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    inclusivo_hasta: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoPlazo),
        check_vocabulario("tipo_dia", voc.TipoDia),
        # Exactamente un propietario principal.
        CheckConstraint(
            "(CASE WHEN beneficio_version_id IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN tramite_version_id IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN norma_version_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="un_solo_propietario_principal",
        ),
        CheckConstraint("fin IS NULL OR inicio IS NULL OR fin >= inicio", name="fin_tras_inicio"),
        # Fechado y relativo son modalidades distintas; al menos una debe estar
        # determinada, y no se declaran ambas a la vez.
        CheckConstraint(
            "(inicio IS NOT NULL OR fin IS NOT NULL) <> (cantidad IS NOT NULL)",
            name="fechado_o_relativo_no_ambos",
        ),
        CheckConstraint(
            "cantidad IS NULL OR (cantidad >= 0 AND unidad IS NOT NULL "
            "AND evento_inicio IS NOT NULL)",
            name="relativo_con_unidad_y_evento",
        ),
        # Contar días hábiles sin calendario produce una fecha inventada.
        CheckConstraint(
            "tipo_dia NOT IN ('HABIL_ADMINISTRATIVO','HABIL_JUDICIAL') "
            "OR calendario_id IS NOT NULL",
            name="habil_exige_calendario",
        ),
        CheckConstraint("ciclo IS NULL OR ciclo >= 1", name="ciclo_positivo"),
        Index("ix_plazos_tipo_inicio_fin", "tipo", "inicio", "fin"),
        Index("ix_plazos_convocatoria", "convocatoria", "ciclo"),
    )
