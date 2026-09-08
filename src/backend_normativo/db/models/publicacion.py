"""Publicación, recuperación documental, eventos y auditoría."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class Release(Base):
    """Corte publicable de proyecciones. Una consulta nunca mezcla dos releases
    incompatibles; revertir es cambiar de release, no borrar filas."""

    __tablename__ = "releases"

    id: Mapped[uuid.UUID] = pk_uuid()
    creado_en: Mapped[dt.datetime] = ts_creacion()
    publicado_en: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    estado: Mapped[str] = mapped_column(String(16), nullable=False)
    manifest_hash: Mapped[str | None] = mapped_column(String(64))
    aprobado_por: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        check_vocabulario("estado", voc.EstadoRelease),
        CheckConstraint(
            "manifest_hash IS NULL OR manifest_hash ~ '^[0-9a-f]{64}$'", name="manifest_hash_hex"
        ),
        CheckConstraint(
            "estado <> 'PUBLICADO' OR "
            "(publicado_en IS NOT NULL AND aprobado_por IS NOT NULL "
            " AND manifest_hash IS NOT NULL)",
            name="publicado_con_acta",
        ),
        Index("ix_releases_estado_publicado", "estado", "publicado_en"),
    )


class Chunk(Base):
    """Segmento citable del corpus publicado, anclado a una unidad documental.

    Es una proyección reconstruible: ninguna regla depende de que exista, y un
    duplicado no aumenta la autoridad de una afirmación.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = pk_uuid()
    unidad_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    registro_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), index=True
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    tsv: Mapped[str | None] = mapped_column(TSVECTOR)
    modelo_embedding: Mapped[str | None] = mapped_column(Text)
    embedding_ref: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoChunk),
        CheckConstraint("hash ~ '^[0-9a-f]{64}$'", name="hash_hex"),
        UniqueConstraint("release_id", "unidad_id", "hash", name="uq_chunks_release_unidad_hash"),
    )


class EventoOutbox(Base):
    """Evento interno pendiente de entrega a un consumidor configurado.

    Entrega al menos una vez, con consumidores idempotentes. Un evento creado no
    es un mensaje entregado: `entregado_en` solo se completa con entrega
    comprobada. Web Push ciudadano es una integración separada.
    """

    __tablename__ = "eventos_outbox"

    id: Mapped[uuid.UUID] = pk_uuid()
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("releases.id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    creado_en: Mapped[dt.datetime] = ts_creacion()
    entregado_en: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    ultimo_error: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoEventoOutbox),
        CheckConstraint("intentos >= 0", name="intentos_no_negativos"),
        Index(
            "ix_eventos_outbox_pendientes",
            "creado_en",
            postgresql_where=text("entregado_en IS NULL"),
        ),
    )


class AuditoriaEvento(Base):
    """Bitácora append-only de acciones sobre el corpus. RBAC restringe su
    lectura y su escritura; no se actualiza ni se borra desde la aplicación."""

    __tablename__ = "auditoria_eventos"

    id: Mapped[uuid.UUID] = pk_uuid()
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    accion: Mapped[str] = mapped_column(Text, nullable=False)
    objeto: Mapped[str] = mapped_column(Text, nullable=False)
    objeto_id: Mapped[str] = mapped_column(Text, nullable=False)
    antes_hash: Mapped[str | None] = mapped_column(String(64))
    despues_hash: Mapped[str | None] = mapped_column(String(64))
    motivo: Mapped[str | None] = mapped_column(Text)
    ocurrido_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        Index("ix_auditoria_eventos_objeto", "objeto", "objeto_id"),
        Index("ix_auditoria_eventos_ocurrido", "ocurrido_en"),
    )


class ConsultaAuditada(Base):
    """Traza mínima de una consulta servida, para reproducibilidad y métricas.

    Por defecto no guarda la conversación ni datos de la persona: solo la
    intención normalizada, la fecha consultada, el release y qué evidencias y
    versiones de reglas se usaron. Cualquier persistencia adicional exige un
    contrato de consentimiento y retención separado.
    """

    __tablename__ = "consultas_auditadas"

    id: Mapped[uuid.UUID] = pk_uuid()
    release_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("releases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    intencion: Mapped[str | None] = mapped_column(Text)
    fecha_consulta: Mapped[dt.date | None] = mapped_column(Date)
    jurisdiccion_id: Mapped[str | None] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT")
    )
    resultado_tipo: Mapped[str | None] = mapped_column(Text)
    evidencias_usadas: Mapped[list | None] = mapped_column(JSONB)
    reglas_versiones: Mapped[list | None] = mapped_column(JSONB)
    latencia_ms: Mapped[int | None] = mapped_column(Integer)
    ocurrido_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint("latencia_ms IS NULL OR latencia_ms >= 0", name="latencia_no_negativa"),
        Index("ix_consultas_auditadas_ocurrido", "ocurrido_en"),
    )
