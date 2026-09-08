"""Registro y descubrimiento: jurisdicciones, organismos y catálogo de fuentes."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Interval,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class Jurisdiccion(Base):
    """Jerarquía acíclica. `id` es un slug estable (`AR`, `AR-C`, `AR-B`, ...)
    para que Nación, CABA, PBA y municipios homónimos no colisionen."""

    __tablename__ = "jurisdicciones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), index=True
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    nivel: Mapped[str] = mapped_column(String(32), nullable=False)
    codigo_oficial: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("nivel", voc.NivelJurisdiccion),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="sin_autopadre"),
        UniqueConstraint("parent_id", "nombre", name="uq_jurisdicciones_padre_nombre"),
    )


class Organismo(Base):
    """Emisor, autoridad de aplicación, prestador y ONG se distinguen por `tipo`;
    un mismo nombre puede cumplir varios roles en jurisdicciones distintas."""

    __tablename__ = "organismos"

    id: Mapped[uuid.UUID] = pk_uuid()
    jurisdiccion_id: Mapped[str] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    sigla: Mapped[str | None] = mapped_column(Text)
    identificador_oficial: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoOrganismo),
        UniqueConstraint(
            "jurisdiccion_id", "nombre", "tipo", name="uq_organismos_jurisdiccion_nombre_tipo"
        ),
    )


class Fuente(Base):
    """Catálogo del corpus. `source_id` conserva los identificadores del paquete
    (F01–F67, D01–D10, M01–M06): son la clave de trazabilidad con el manual y no
    se renumeran.

    `estado`, `access_status` y `alias_of` son independientes: un alias no está
    necesariamente caído, y una fuente activa puede estar limitada hoy.
    """

    __tablename__ = "fuentes"

    source_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    organismo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT"), index=True
    )
    alias_of: Mapped[str | None] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), index=True
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    clase: Mapped[str] = mapped_column(String(32), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False)
    access_status: Mapped[str] = mapped_column(String(32), nullable=False)
    prioridad: Mapped[str] = mapped_column(String(4), nullable=False)
    motivo_estado: Mapped[str | None] = mapped_column(Text)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    responsable_rol: Mapped[str | None] = mapped_column(Text)
    alcance: Mapped[str | None] = mapped_column(Text)
    # Política de acceso: qué se permite hacer con esta fuente. Es distinta de
    # `access_status`, que describe qué se pudo hacer la última vez.
    politica_acceso: Mapped[str] = mapped_column(String(64), nullable=False)
    # Otros IDs del catálogo con los que hay que contrastar esta fuente. No son
    # alias ni candidatas: son relaciones de revisión que el manual declara.
    relacionadas: Mapped[list | None] = mapped_column(JSONB)
    # Procedencia documental: página del manual, fecha de observación y el
    # estado de URL que el propio manifiesto declaró.
    origen: Mapped[str | None] = mapped_column(Text)
    manual_pagina: Mapped[int | None] = mapped_column(Integer)
    origen_url_status: Mapped[str | None] = mapped_column(Text)
    tarea: Mapped[str | None] = mapped_column(Text)
    aceptacion_especifica: Mapped[list | None] = mapped_column(JSONB)
    tablas_destino: Mapped[list | None] = mapped_column(JSONB)
    # Referencias históricas del manual: son antecedente a revalidar, no contrato.
    referencia_selectores: Mapped[str | None] = mapped_column(Text)
    referencia_campos: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    urls: Mapped[list[FuenteUrl]] = relationship(back_populates="fuente")

    __table_args__ = (
        check_vocabulario("clase", voc.ClaseFuente),
        check_vocabulario("estado", voc.EstadoFuente),
        check_vocabulario("access_status", voc.AccessStatus),
        check_vocabulario("prioridad", voc.Prioridad),
        check_vocabulario("politica_acceso", voc.PoliticaAcceso),
        CheckConstraint("alias_of IS NULL OR alias_of <> source_id", name="sin_autoalias"),
        # Un estado de excepción exige motivo: no se degrada ni se retira una
        # fuente sin dejar por qué.
        CheckConstraint(
            "estado NOT IN ('DEGRADED','QUARANTINED','RETIRED') OR motivo_estado IS NOT NULL",
            name="estado_excepcional_con_motivo",
        ),
        Index("ix_fuentes_estado_prioridad", "estado", "prioridad"),
    )


class FuenteUrl(Base):
    """URL HTTP(S) concreta. Sin plantillas ni secretos, y sin quitar parámetros
    de consulta que cambian el contenido servido."""

    __tablename__ = "fuente_urls"

    id: Mapped[uuid.UUID] = pk_uuid()
    source_id: Mapped[str] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(String(32), nullable=False)
    tipo_acceso: Mapped[str] = mapped_column(String(32), nullable=False)
    es_canonica: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    descubierta_en: Mapped[dt.datetime] = ts_creacion()
    url_padre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fuente_urls.id", ondelete="RESTRICT"), index=True
    )

    fuente: Mapped[Fuente] = relationship(back_populates="urls")

    __table_args__ = (
        check_vocabulario("rol", voc.RolUrl),
        check_vocabulario("tipo_acceso", voc.TipoAcceso),
        UniqueConstraint("source_id", "url", name="uq_fuente_urls_source_url"),
        # `manual://` es para las fuentes que no se pueden recorrer: el archivo
        # entró por una vía legítima fuera de la red y no hay una http que
        # visitar. Inventarle una sería peor que decir que no la hay.
        CheckConstraint("url ~ '^(https?|manual)://'", name="url_concreta"),
        # Una plantilla sin resolver no es una URL descargable.
        CheckConstraint("url !~ '[{}]'", name="url_sin_plantilla"),
        CheckConstraint("url_padre_id IS NULL OR url_padre_id <> id", name="sin_autopadre"),
    )


class FuenteConfigVersion(Base):
    """Configuración de extracción versionada: cada cambio de selector, de
    frecuencia o de presupuesto queda auditable y referenciable desde la corrida
    que lo usó."""

    __tablename__ = "fuente_config_versiones"

    id: Mapped[uuid.UUID] = pk_uuid()
    source_id: Mapped[str] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    adaptador: Mapped[str] = mapped_column(String(32), nullable=False)
    selector_config: Mapped[dict | None] = mapped_column(JSONB)
    frecuencia: Mapped[dt.timedelta | None] = mapped_column(Interval)
    ttl_defecto: Mapped[dt.timedelta | None] = mapped_column(Interval)
    presupuesto: Mapped[dict | None] = mapped_column(JSONB)
    politica_version: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("adaptador", voc.Adaptador),
        UniqueConstraint("source_id", "version", name="uq_fuente_config_versiones_source_version"),
        CheckConstraint("version >= 1", name="version_positiva"),
    )


class FuenteCandidata(Base):
    """Descubrimiento acotado y deduplicado. No es una cola de rastreo
    ilimitada: cada candidata nace de una evidencia concreta."""

    __tablename__ = "fuentes_candidatas"

    id: Mapped[uuid.UUID] = pk_uuid()
    source_id_origen: Mapped[str] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    relacion: Mapped[str | None] = mapped_column(Text)
    tipo_esperado: Mapped[str | None] = mapped_column(String(32))
    estado: Mapped[str] = mapped_column(String(32), nullable=False)
    prioridad: Mapped[str | None] = mapped_column(String(4))
    alias_detectado: Mapped[str | None] = mapped_column(Text)
    descubierta_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("estado", voc.EstadoFuenteCandidata),
        check_vocabulario("prioridad", voc.Prioridad, nullable=True),
        UniqueConstraint("source_id_origen", "url", name="uq_fuentes_candidatas_origen_url"),
        CheckConstraint("url ~ '^https?://'", name="url_http_concreta"),
    )
