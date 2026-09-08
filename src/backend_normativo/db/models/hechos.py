"""Afirmaciones, evaluación de completitud y derivaciones.

`afirmaciones` conserva candidatos, estado y respaldo campo por campo. No es una
segunda base editable en paralelo: las tablas tipadas son la proyección
operativa de los hechos aprobados, y la publicación actualiza ambas
representaciones en una transacción identificando la afirmación de origen.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion

CAMPOS_SOLICITADOS_SQL = ", ".join(f"'{c}'" for c in voc.CAMPOS_SOLICITADOS)


class Afirmacion(Base):
    """Un valor observado para un campo de una versión, con su estado y respaldo.

    Reglas de estado (especificación §3.3):

    * `INFORMADO` exige valor y evidencia.
    * `NO_APLICA_JUSTIFICADO` exige motivo y fundamento.
    * `NO_INFORMADO_EN_FUENTES_REVISADAS` exige haber registrado qué fuentes se
      revisaron; nunca significa que el dato no exista.
    """

    __tablename__ = "afirmaciones"

    id: Mapped[uuid.UUID] = pk_uuid()
    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), index=True
    )
    campo_path: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    estado_campo: Mapped[str] = mapped_column(String(40), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text)
    fuentes_revisadas: Mapped[list | None] = mapped_column(JSONB)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), index=True
    )
    estado_revision: Mapped[str] = mapped_column(String(16), nullable=False)
    observado_en: Mapped[dt.datetime] = ts_creacion()
    derivacion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("derivaciones.id", ondelete="RESTRICT")
    )

    __table_args__ = (
        check_vocabulario("estado_campo", voc.EstadoCampo),
        check_vocabulario("estado_revision", voc.EstadoRevision),
        CheckConstraint("length(btrim(campo_path)) > 0", name="campo_path_no_vacio"),
        CheckConstraint(
            "estado_campo <> 'INFORMADO' OR (valor IS NOT NULL AND evidencia_id IS NOT NULL)",
            name="informado_con_valor_y_evidencia",
        ),
        CheckConstraint(
            "estado_campo <> 'NO_APLICA_JUSTIFICADO' OR "
            "(motivo IS NOT NULL AND evidencia_id IS NOT NULL)",
            name="no_aplica_con_motivo_y_fundamento",
        ),
        CheckConstraint(
            "estado_campo <> 'NO_INFORMADO_EN_FUENTES_REVISADAS' OR "
            "(fuentes_revisadas IS NOT NULL AND jsonb_array_length(fuentes_revisadas) > 0)",
            name="no_informado_con_fuentes_revisadas",
        ),
        Index("ix_afirmaciones_version_campo", "registro_version_id", "campo_path"),
        Index("ix_afirmaciones_estado_campo", "estado_campo"),
    )


class EvaluacionCompletitud(Base):
    """Una fila por cada uno de los siete campos pedidos, por ficha evaluada.

    Su existencia prueba que el campo se evaluó; su estado dice con qué
    resultado. Cien por ciento de filas en `NO_INFORMADO...` da cobertura de
    evaluación, nunca "base completa".
    """

    __tablename__ = "evaluaciones_completitud"

    id: Mapped[uuid.UUID] = pk_uuid()
    norma_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("norma_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    beneficio_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("beneficio_versiones.registro_version_id", ondelete="RESTRICT"), index=True
    )
    campo_solicitado: Mapped[str] = mapped_column(String(40), nullable=False)
    estado: Mapped[str] = mapped_column(String(40), nullable=False)
    fuentes_revisadas: Mapped[list | None] = mapped_column(JSONB)
    motivo: Mapped[str | None] = mapped_column(Text)
    revisor_id: Mapped[str | None] = mapped_column(Text)
    evaluado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint(
            f"campo_solicitado IN ({CAMPOS_SOLICITADOS_SQL})", name="campo_solicitado_vocabulario"
        ),
        check_vocabulario("estado", voc.EstadoCampo),
        # Sin duplicar la dimensión dentro de la misma ficha/versión.
        # `NULLS NOT DISTINCT` (PostgreSQL 15+) hace que la evaluación por norma
        # sin beneficio también sea única: con la semántica por defecto, dos
        # filas con `beneficio_version_id` nulo se considerarían distintas.
        Index(
            "uq_evaluaciones_completitud_ficha_campo",
            "norma_version_id",
            "beneficio_version_id",
            "campo_solicitado",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )


class CompletitudAfirmacion(Base):
    """Puente entre una evaluación y las afirmaciones que la respaldan. La FK es
    obligatoria: una evaluación no se justifica con una URL suelta."""

    __tablename__ = "completitud_afirmaciones"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluaciones_completitud.id", ondelete="RESTRICT"), nullable=False
    )
    afirmacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("afirmaciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (PrimaryKeyConstraint("evaluacion_id", "afirmacion_id"),)


class Derivacion(Base):
    """Cálculo reproducible: algoritmo, fórmula, insumos y resultado.

    Los insumos apuntan a la afirmación exacta que se usó, nunca al último valor
    mutable de un parámetro.
    """

    __tablename__ = "derivaciones"

    id: Mapped[uuid.UUID] = pk_uuid()
    algoritmo_version: Mapped[str] = mapped_column(Text, nullable=False)
    formula: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resultado: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ejecutada_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint("length(btrim(algoritmo_version)) > 0", name="algoritmo_version_no_vacia"),
    )


class DerivacionInsumo(Base):
    """Puente obligatorio entre una derivación y sus afirmaciones de entrada."""

    __tablename__ = "derivacion_insumos"

    derivacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("derivaciones.id", ondelete="RESTRICT"), nullable=False
    )
    afirmacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("afirmaciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("derivacion_id", "afirmacion_id", "rol"),)
