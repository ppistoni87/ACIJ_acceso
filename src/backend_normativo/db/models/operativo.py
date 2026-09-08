"""Datos operativos: trámites, puntos de atención, canales y padrón RENABAP.

Estos datos se consultan con SQL y tipos, no recuperando fragmentos de texto:
una dirección, un horario o un teléfono salen de la misma entidad o no se
responden.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class Tramite(Base):
    """Procedimiento con identidad propia. Un botón duplicado en dos páginas no
    crea dos trámites; el público destinatario sí los diferencia."""

    __tablename__ = "tramites"

    id: Mapped[uuid.UUID] = pk_uuid()
    organismo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    beneficio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("beneficios.id", ondelete="RESTRICT"), index=True
    )
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    publico: Mapped[str] = mapped_column(String(16), nullable=False)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("publico", voc.PublicoTramite),
        CheckConstraint("codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name="codigo_normalizado"),
    )


class TramiteVersion(Base):
    """Subtipo de `registro_versiones`.

    `estado_operativo` describe la disponibilidad del canal, no el derecho: un
    sistema sin turnos disponibles no elimina el trámite ni revoca el beneficio.
    """

    __tablename__ = "tramite_versiones"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    tramite_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tramites.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    doc_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documento_versiones.id", ondelete="RESTRICT"), index=True
    )
    descripcion: Mapped[str | None] = mapped_column(Text)
    cta_url: Mapped[str | None] = mapped_column(Text)
    costo_parametro_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parametros.id", ondelete="RESTRICT")
    )
    duracion_texto: Mapped[str | None] = mapped_column(Text)
    estado_operativo: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        check_vocabulario("estado_operativo", voc.EstadoOperativo),
        CheckConstraint("cta_url IS NULL OR cta_url ~ '^https?://'", name="url_http_concreta"),
    )


class TramitePaso(Base):
    """Paso del procedimiento. El orden es un dato de la fuente, no el orden de
    lectura de un PDF: si la fuente no lo establece, no se inventa."""

    __tablename__ = "tramite_pasos"

    id: Mapped[uuid.UUID] = pk_uuid()
    tramite_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tramite_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    accion: Mapped[str] = mapped_column(Text, nullable=False)
    canal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("canales.registro_version_id", ondelete="RESTRICT")
    )
    documentacion: Mapped[str | None] = mapped_column(Text)
    # Alternativas documentales: son salvaguardas de no exclusión, no adornos.
    alternativas: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("tramite_version_id", "orden", name="uq_tramite_pasos_orden"),
        CheckConstraint("orden >= 1", name="orden_positivo"),
    )


class PuntoAtencion(Base):
    """Lugar de atención. El organismo que lista y el que atiende pueden diferir.

    Un barrio del padrón RENABAP no es una oficina: vive en `barrios_renabap`.
    """

    __tablename__ = "puntos_atencion"

    id: Mapped[uuid.UUID] = pk_uuid()
    organismo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    jurisdiccion_id: Mapped[str] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organismo_operador_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT")
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    # La jurisdicción dice dónde está el punto; el alcance, a quién sirve. Sin
    # separarlos, una defensoría municipal y la provincial de la misma provincia
    # se responden como si fueran la misma cosa.
    alcance: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=voc.AlcanceTerritorial.NO_DECLARADO.value
    )
    ambito: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoPuntoAtencion),
        check_vocabulario("alcance", voc.AlcanceTerritorial),
        CheckConstraint(
            "alcance <> 'MUNICIPAL' OR ambito IS NOT NULL",
            name="ck_puntos_atencion_municipal_declara_su_ambito",
        ),
        Index("ix_puntos_atencion_nombre", "nombre"),
        Index("ix_puntos_atencion_alcance", "alcance"),
    )


class PuntoVersion(Base):
    """Subtipo de `registro_versiones`. Coordenadas WGS84 válidas o ninguna: sin
    CRS conocido no se reproyecta, y sin coordenadas no se afirma cercanía."""

    __tablename__ = "punto_versiones"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    punto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("puntos_atencion.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    direccion_cruda: Mapped[str | None] = mapped_column(Text)
    direccion_legible: Mapped[str | None] = mapped_column(Text)
    localidad: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[decimal.Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[decimal.Decimal | None] = mapped_column(Numeric(9, 6))
    coordenadas_origen: Mapped[dict | None] = mapped_column(JSONB)
    crs: Mapped[str | None] = mapped_column(Text)
    es_presencial: Mapped[bool | None] = mapped_column(Boolean)
    observaciones: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("(lat IS NULL) = (lng IS NULL)", name="coordenadas_completas_o_ausentes"),
        CheckConstraint(
            "lat IS NULL OR (lat BETWEEN -90 AND 90 AND lng BETWEEN -180 AND 180)",
            name="coordenadas_en_rango",
        ),
        CheckConstraint("lat IS NULL OR crs IS NOT NULL", name="coordenadas_con_crs"),
        Index("ix_punto_versiones_localidad", "localidad"),
    )


class Canal(Base):
    """Subtipo de `registro_versiones`. El horario es por canal: el de la mesa
    presencial no se copia al teléfono ni al WhatsApp.

    Se guarda el valor tal como fue publicado y, si se pudo normalizar, ambos.
    No se desofusca un correo ni se registran datos de personas usuarias.
    """

    __tablename__ = "canales"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    # Identidad lógica del canal a través de sus versiones; es lo que apunta
    # `registro_versiones.entidad_id`. Cambiar el horario publicado versiona el
    # mismo canal en vez de crear uno nuevo.
    canal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organismo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    punto_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("puntos_atencion.id", ondelete="RESTRICT"), index=True
    )
    tramite_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tramites.id", ondelete="RESTRICT"), index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    valor_crudo: Mapped[str] = mapped_column(Text, nullable=False)
    valor_normalizado: Mapped[str | None] = mapped_column(Text)
    horario: Mapped[str | None] = mapped_column(Text)
    publico: Mapped[str | None] = mapped_column(Text)
    requiere_autenticacion: Mapped[bool | None] = mapped_column(Boolean)

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoCanal),
        CheckConstraint("length(btrim(valor_crudo)) > 0", name="valor_crudo_no_vacio"),
        # Una cuenta de red social no es un correo electrónico.
        CheckConstraint(
            "tipo <> 'EMAIL' OR valor_normalizado IS NULL OR valor_normalizado LIKE '%@%'",
            name="email_normalizado_plausible",
        ),
        CheckConstraint(
            "tipo <> 'PRESENCIAL' OR punto_id IS NOT NULL", name="presencial_con_punto"
        ),
    )


class BarrioRenabap(Base):
    """Subtipo de `registro_versiones`: un barrio popular en una versión de
    padrón.

    La ausencia de un barrio en un padrón no es una exclusión jurídica
    definitiva; es un dato de ese corte.
    """

    __tablename__ = "barrios_renabap"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    # Identidad lógica del barrio a través de las versiones de padrón; es lo que
    # apunta `registro_versiones.entidad_id`.
    barrio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    id_renabap: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    provincia: Mapped[str | None] = mapped_column(Text)
    departamento: Mapped[str | None] = mapped_column(Text)
    localidad: Mapped[str | None] = mapped_column(Text)
    viviendas: Mapped[int | None] = mapped_column(BigInteger)
    familias: Mapped[int | None] = mapped_column(BigInteger)
    datos_habitacionales: Mapped[dict | None] = mapped_column(JSONB)
    fecha_corte: Mapped[dt.date | None] = mapped_column(Date)
    padron_version: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_renabap", "padron_version", name="uq_barrios_renabap_padron"),
        CheckConstraint("viviendas IS NULL OR viviendas >= 0", name="viviendas_no_negativas"),
        CheckConstraint("familias IS NULL OR familias >= 0", name="familias_no_negativas"),
        Index("ix_barrios_renabap_provincia_localidad", "provincia", "localidad"),
    )
