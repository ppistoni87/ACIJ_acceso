"""Captura y extracción: corridas, bytes originales, documentos y evidencias."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion

HASH_HEX_64 = "~ '^[0-9a-f]{64}$'"


class CorridaIngesta(Base):
    """Una ejecución del pipeline sobre una fuente, con la versión de
    configuración que usó. Los contadores deben reconciliar: una corrida que no
    procesó lo que descargó no puede figurar como completa."""

    __tablename__ = "corridas_ingesta"

    id: Mapped[uuid.UUID] = pk_uuid()
    source_id: Mapped[str] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    config_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fuente_config_versiones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    inicio: Mapped[dt.datetime] = ts_creacion()
    fin: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    estado: Mapped[str] = mapped_column(String(16), nullable=False)
    extractor_version: Mapped[str] = mapped_column(Text, nullable=False)
    solicitadas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    descargadas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    procesadas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rechazadas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    checkpoint: Mapped[dict | None] = mapped_column(JSONB)
    detalle_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        check_vocabulario("estado", voc.EstadoCorrida),
        CheckConstraint(
            "solicitadas >= 0 AND descargadas >= 0 AND procesadas >= 0 AND rechazadas >= 0",
            name="contadores_no_negativos",
        ),
        CheckConstraint("descargadas <= solicitadas", name="descargadas_hasta_solicitadas"),
        CheckConstraint(
            "procesadas + rechazadas <= descargadas", name="procesadas_hasta_descargadas"
        ),
        # Una corrida solo es COMPLETA si cerró y no dejó descargas sin resolver.
        CheckConstraint(
            "estado <> 'COMPLETA' OR (fin IS NOT NULL AND procesadas + rechazadas = descargadas)",
            name="completa_reconciliada",
        ),
        CheckConstraint("fin IS NULL OR fin >= inicio", name="fin_posterior_a_inicio"),
        Index("ix_corridas_ingesta_source_inicio", "source_id", "inicio"),
    )


class Captura(Base):
    """Bytes originales de un recurso público, inmutables.

    `objeto_uri` apunta al almacén direccionado por contenido; la base guarda
    URI y hashes, nunca una ruta local de un agente. Las cabeceras conservadas
    excluyen cookies y tokens de sesión.

    Un `304 Not Modified` exige `captura_previa_id` del mismo recurso y reutiliza
    su objeto y su hash: no inventa un cuerpo descargado.
    """

    __tablename__ = "capturas"

    id: Mapped[uuid.UUID] = pk_uuid()
    corrida_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("corridas_ingesta.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_url_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fuente_urls.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    captura_previa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("capturas.id", ondelete="RESTRICT"), index=True
    )
    url_final: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    capturado_en: Mapped[dt.datetime] = ts_creacion()
    mime: Mapped[str | None] = mapped_column(Text)
    bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256_raw: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256_semantico: Mapped[str | None] = mapped_column(String(64))
    objeto_uri: Mapped[str] = mapped_column(Text, nullable=False)
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    cabeceras: Mapped[dict | None] = mapped_column(JSONB)
    redirecciones: Mapped[list | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint(f"sha256_raw {HASH_HEX_64}", name="sha256_raw_hex"),
        CheckConstraint(
            f"sha256_semantico IS NULL OR sha256_semantico {HASH_HEX_64}",
            name="sha256_semantico_hex",
        ),
        CheckConstraint("bytes IS NULL OR bytes >= 0", name="bytes_no_negativos"),
        CheckConstraint(
            "http_status IS NULL OR (http_status BETWEEN 100 AND 599)", name="http_status_valido"
        ),
        CheckConstraint(
            "http_status <> 304 OR captura_previa_id IS NOT NULL",
            name="revalidacion_304_exige_captura_previa",
        ),
        CheckConstraint("captura_previa_id <> id", name="sin_autoprevia"),
        CheckConstraint("objeto_uri ~ '^[a-z][a-z0-9+.-]*://'", name="objeto_uri_con_esquema"),
        Index("ix_capturas_sha256_raw", "sha256_raw"),
        Index("ix_capturas_url_capturado", "source_url_id", "capturado_en"),
    )


class Documento(Base):
    """No todo documento es norma: una guía, una FAQ, un dataset o un
    procedimiento se registran con su propio tipo."""

    __tablename__ = "documentos"

    id: Mapped[uuid.UUID] = pk_uuid()
    source_id: Mapped[str] = mapped_column(
        ForeignKey("fuentes.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    titulo: Mapped[str | None] = mapped_column(Text)
    idioma: Mapped[str | None] = mapped_column(String(8), server_default=text("'es'"))
    external_id: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoDocumento),
        UniqueConstraint("source_id", "external_id", name="uq_documentos_source_external"),
    )


class DocumentoVersion(Base):
    """Versión textual de un documento, anclada a la captura de la que salió.

    Original, actualizado y consolidado son versiones distintas: no se
    sobrescriben ni se vuelve a aplicar una reforma que el texto ya integra.
    """

    __tablename__ = "documento_versiones"

    id: Mapped[uuid.UUID] = pk_uuid()
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documentos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    captura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("capturas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_version: Mapped[str] = mapped_column(String(32), nullable=False)
    fecha_documento: Mapped[dt.date | None] = mapped_column()
    tipo_fecha: Mapped[str] = mapped_column(String(32), nullable=False)
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    hash_texto: Mapped[str] = mapped_column(String(64), nullable=False)
    modo_extraccion: Mapped[str] = mapped_column(String(16), nullable=False)
    paginas: Mapped[int | None] = mapped_column(Integer)
    chars_por_pagina: Mapped[dict | None] = mapped_column(JSONB)
    # Señal técnica observable de la extracción. No es un juicio de vigencia ni
    # una aprobación: el score de un modelo no valida un registro.
    extraccion_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo_version", voc.TipoVersionDocumento),
        check_vocabulario("tipo_fecha", voc.TipoFecha),
        check_vocabulario("modo_extraccion", voc.ModoExtraccion),
        UniqueConstraint(
            "documento_id", "hash_texto", "tipo_version", name="uq_documento_versiones_contenido"
        ),
        UniqueConstraint("documento_id", "version", name="uq_documento_versiones_numero"),
        CheckConstraint(f"hash_texto {HASH_HEX_64}", name="hash_texto_hex"),
        CheckConstraint("version >= 1", name="version_positiva"),
        CheckConstraint(
            "extraccion_score IS NULL OR (extraccion_score BETWEEN 0 AND 1)",
            name="score_entre_cero_y_uno",
        ),
        # Una fecha sin tipo declarado es ambigua: firma, publicación y cabecera
        # no son equivalentes.
        CheckConstraint(
            "fecha_documento IS NULL OR tipo_fecha <> 'DESCONOCIDA'",
            name="fecha_con_tipo_declarado",
        ),
        Index("ix_documento_versiones_fecha", "fecha_documento"),
    )


class UnidadDocumental(Base):
    """Segmento del texto con su lugar en la jerarquía.

    `ruta` es la ruta jerárquica materializada dentro de la versión y sostiene
    la unicidad: dos artículos raíz no comparten ruta, pero un mismo número
    puede aparecer citado dentro de un bloque de sustitución (`rol_contenido`
    distinto de `DISPOSITIVO`).
    """

    __tablename__ = "unidades_documentales"

    id: Mapped[uuid.UUID] = pk_uuid()
    doc_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documento_versiones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    numero: Mapped[str | None] = mapped_column(Text)
    sufijo: Mapped[str | None] = mapped_column(Text)
    rotulo: Mapped[str | None] = mapped_column(Text)
    ruta: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    inicio: Mapped[int | None] = mapped_column(Integer)
    fin: Mapped[int | None] = mapped_column(Integer)
    pagina_desde: Mapped[int | None] = mapped_column(Integer)
    pagina_hasta: Mapped[int | None] = mapped_column(Integer)
    rol_contenido: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoUnidad),
        check_vocabulario("rol_contenido", voc.RolContenido),
        # Unicidad por ruta jerárquica de la versión, solo entre unidades
        # dispositivas: el texto citado o sustituido puede repetir el número.
        Index(
            "uq_unidades_documentales_ruta_dispositiva",
            "doc_version_id",
            "ruta",
            unique=True,
            postgresql_where=text("rol_contenido = 'DISPOSITIVO'"),
        ),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="sin_autopadre"),
        CheckConstraint("fin IS NULL OR inicio IS NULL OR fin >= inicio", name="offsets_ordenados"),
        CheckConstraint(
            "pagina_hasta IS NULL OR pagina_desde IS NULL OR pagina_hasta >= pagina_desde",
            name="paginas_ordenadas",
        ),
        Index("ix_unidades_documentales_version_orden", "doc_version_id", "orden"),
    )


class Evidencia(Base):
    """Localizador verificable de un fragmento dentro de una versión documental.

    Una URL sola no prueba un valor. La unidad citada debe pertenecer a la misma
    versión que el documento referenciado; el control se aplica por trigger.
    """

    __tablename__ = "evidencias"

    id: Mapped[uuid.UUID] = pk_uuid()
    doc_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documento_versiones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    unidad_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT"), index=True
    )
    fragmento: Mapped[str] = mapped_column(Text, nullable=False)
    selector: Mapped[str | None] = mapped_column(Text)
    pagina: Mapped[int | None] = mapped_column(Integer)
    offset_inicio: Mapped[int | None] = mapped_column(Integer)
    offset_fin: Mapped[int | None] = mapped_column(Integer)
    hash_fragmento: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoEvidencia),
        CheckConstraint(f"hash_fragmento {HASH_HEX_64}", name="hash_fragmento_hex"),
        CheckConstraint("length(btrim(fragmento)) > 0", name="fragmento_no_vacio"),
        CheckConstraint(
            "offset_fin IS NULL OR offset_inicio IS NULL OR offset_fin >= offset_inicio",
            name="offsets_ordenados",
        ),
        Index("ix_evidencias_hash", "hash_fragmento"),
    )
