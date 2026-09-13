"""Publicación, recuperación documental, eventos y auditoría."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
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
from sqlalchemy.types import UserDefinedType

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class Vector(UserDefinedType):
    """El tipo `vector` de pgvector, declarado sin traer la biblioteca.

    El proyecto no depende del paquete `pgvector` de Python: los vectores se
    escriben y se leen con SQL, y lo único que hace falta acá es que el modelo
    sepa que la columna existe y con qué dimensión. Sin esta declaración,
    `alembic check` ve una tabla que está en la base y no en los modelos, y el
    próximo autogenerado propone borrarla.
    """

    cache_ok = True

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def get_col_spec(self, **_: object) -> str:
        return f"vector({self.dimension})"


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
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('spanish'::regconfig, texto)", persisted=True),
        comment=(
            "Generada a partir de texto. No la escribe nadie: antes la escribía el "
            "publicador y podía quedar distinta del texto que decía representar."
        ),
    )
    url_fuente: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoChunk),
        CheckConstraint("hash ~ '^[0-9a-f]{64}$'", name="hash_hex"),
        UniqueConstraint("release_id", "unidad_id", "hash", name="uq_chunks_release_unidad_hash"),
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
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
    identidad: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text(
            "COALESCE(NULLIF(current_setting('bn.identidad', true), ''), 'PROCESO_LOCAL')"
        ),
        comment=(
            "Cómo se estableció el actor. CREDENCIAL_FIRMADA: credencial por persona, "
            "verificada y no revocada. AUTODECLARADA: token compartido y actor escrito "
            "por quien llamaba, que solo se admite con el modo de desarrollo activado. "
            "PROCESO_LOCAL: CLI o acceso directo a la base. NO_REGISTRADA: anterior a "
            "que esto se registrara."
        ),
    )

    __table_args__ = (
        CheckConstraint(
            "identidad IN ('CREDENCIAL_FIRMADA', 'AUTODECLARADA', 'PROCESO_LOCAL', "
            "'NO_REGISTRADA')",
            name="identidad",
        ),
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
    # Opcional desde 0017: una consulta sin corte publicado es justamente la
    # abstención más importante, y con la columna obligatoria era la única que
    # no se podía registrar.
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("releases.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # `intencion` recibe la ruta pedida —`/v1/respuestas`—, nunca lo que la
    # persona escribió.
    intencion: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(Text, index=True)
    motivo_abstencion: Mapped[str | None] = mapped_column(Text)
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


class Devolucion(Base):
    """Lo que la persona contesta sobre la respuesta que recibió.

    No lleva texto libre y no lleva identidad: sólo una señal de un vocabulario
    cerrado y el `request_id`, que la une a la traza de la consulta sin decir
    qué se preguntó. Agregar acá una columna de comentario invierte esa decisión
    —es donde alguien escribe su caso completo— y hay una prueba que falla si
    aparece.

    No hay clave foránea contra `consultas_auditadas`: `request_id` no es único
    —lo puede mandar quien llama en la cabecera— y una FK le exigiría una
    unicidad que no tiene.
    """

    __tablename__ = "devoluciones"

    id: Mapped[uuid.UUID] = pk_uuid()
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    senal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "SIRVIO / NO_SIRVIO: la respuesta a «¿te sirvió?». QUIERE_PERSONA: pidió "
            "hablar con alguien, que es la señal más cara de todas y la que menos se mide."
        ),
    )
    ocurrido_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint("senal IN ('SIRVIO', 'NO_SIRVIO', 'QUIERE_PERSONA')", name="senal"),
        UniqueConstraint("request_id", "senal", name="uq_devoluciones_request_senal"),
        Index("ix_devoluciones_ocurrido_en", "ocurrido_en"),
        Index("ix_devoluciones_senal", "senal"),
        {
            "comment": (
                "Lo que la persona contesta sobre la respuesta que recibió. No lleva "
                "texto libre y no lleva identidad: solo una señal de un vocabulario "
                "cerrado y el request_id, que la une a la traza de la consulta sin decir "
                "qué se preguntó. Agregar acá una columna de texto libre invierte esa "
                "decisión y necesita discutirse como lo que es: guardar el relato "
                "personal de quien consulta."
            )
        },
    )


class ReleaseVersion(Base):
    """Qué versiones sirve cada corte.

    Existe porque `registro_versiones.release_id` significa *el corte que publicó
    esa versión* y no *los cortes en los que se sirve*. Con un solo corte las dos
    lecturas coincidían; con dos, publicar algo nuevo dejaba de servir todo lo
    viejo sin un solo error (D-142).
    """

    __tablename__ = "release_versiones"

    release_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"), primary_key=True
    )
    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="CASCADE"), primary_key=True
    )
    heredada: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment=(
            "Verdadero si venía del corte anterior. Sirve para que revertir no toque "
            "lo heredado: eso lo publicó otro corte y se sigue sirviendo desde ahí."
        ),
    )

    __table_args__ = (
        Index("ix_release_versiones_version", "registro_version_id"),
        {
            "comment": (
                "Qué versiones sirve cada corte. Un corte es la foto completa de lo "
                "servible, no el delta de su corrida: incluye lo que esa publicación "
                "incorporó y lo que heredó del corte anterior. Sin esto, publicar algo "
                "nuevo dejaba de servir todo lo viejo sin un solo error."
            )
        },
    )


class IndiceSemantico(Base):
    """Un índice vectorial construido para un corte y un modelo concretos.

    El modelo y la dimensión quedan escritos: un vector embebido con otro modelo
    no se compara con estos, y mezclarlos devuelve vecinos que no lo son.
    """

    __tablename__ = "indices_semanticos"

    id: Mapped[uuid.UUID] = pk_uuid()
    release_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("releases.id", ondelete="RESTRICT"), nullable=False
    )
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    normalizacion: Mapped[str] = mapped_column(String(16), nullable=False)
    construido_en: Mapped[dt.datetime] = ts_creacion()
    fragmentos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        UniqueConstraint("release_id", "modelo", name="uq_indice_release_modelo"),
        CheckConstraint("dimension = 384", name="dimension"),
        CheckConstraint("fragmentos >= 0", name="fragmentos"),
        CheckConstraint("normalizacion IN ('L2', 'NINGUNA')", name="normalizacion"),
        {
            "comment": (
                "Un índice semántico por corte y modelo. Los vectores cuelgan de acá y "
                "no del fragmento para que no convivan dos modelos en la misma tabla: la "
                "distancia entre vectores de modelos distintos no significa nada."
            )
        },
    )


class FragmentoVector(Base):
    """El vector de un fragmento dentro de un índice.

    `hash_texto` es lo que permite darse cuenta de que el vector quedó viejo:
    si el fragmento cambió, el hash no coincide y eso se nota comparando, en vez
    de servir una respuesta desactualizada.
    """

    __tablename__ = "fragmento_vectores"

    indice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("indices_semanticos.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="RESTRICT"), primary_key=True
    )
    hash_texto: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment=(
            "SHA-256 del texto que se embebió. Si el fragmento cambia, el vector queda "
            "viejo y se nota comparando, en vez de servir una respuesta desactualizada."
        ),
    )
    vector: Mapped[object] = mapped_column(Vector(384), nullable=False)

    __table_args__ = (
        CheckConstraint("hash_texto ~ '^[0-9a-f]{64}$'", name="hash_hex"),
        Index(
            "ix_fragmento_vectores_hnsw",
            "vector",
            postgresql_using="hnsw",
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
    )
