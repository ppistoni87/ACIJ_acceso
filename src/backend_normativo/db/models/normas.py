"""Identidad, versiones y relaciones de normas.

`registro_versiones` es el supertipo bitemporal del que cuelgan todos los
subtipos versionados. Distingue dos ejes que no se sustituyen entre sí:

* **aplicación** (`valid_desde`/`valid_hasta`): el período en que el hecho rige.
* **conocimiento** (`known_desde`/`known_hasta`): el período en que el sistema
  lo tuvo por cierto.

`verificado_en` y `reverificar_antes_de` son frescura operativa. Vencer un TTL
no deroga una ley.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    ARRAY,
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
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class RegistroVersion(Base):
    """Supertipo controlado. Cada subtipo referencia una fila de esta tabla y un
    trigger verifica que `entidad_tipo` corresponda al subtipo real: es la forma
    de tener afirmaciones apuntando a "cualquier versión" sin una FK polimórfica
    sin control."""

    __tablename__ = "registro_versiones"

    id: Mapped[uuid.UUID] = pk_uuid()
    entidad_tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    entidad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    estado_revision: Mapped[str] = mapped_column(String(16), nullable=False)

    valid_desde: Mapped[dt.date | None] = mapped_column(Date)
    valid_hasta: Mapped[dt.date | None] = mapped_column(Date)
    valid_tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    condicion_vigencia: Mapped[str | None] = mapped_column(Text)

    known_desde: Mapped[dt.datetime] = ts_creacion()
    known_hasta: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    verificado_en: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    reverificar_antes_de: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("releases.id", ondelete="RESTRICT"), index=True
    )

    __table_args__ = (
        check_vocabulario("entidad_tipo", voc.EntidadVersionada),
        check_vocabulario("estado_revision", voc.EstadoRevision),
        check_vocabulario("valid_tipo", voc.ValidTipo),
        UniqueConstraint(
            "entidad_tipo", "entidad_id", "numero_version", name="uq_registro_versiones_entidad"
        ),
        CheckConstraint("numero_version >= 1", name="numero_version_positivo"),
        CheckConstraint(
            "valid_hasta IS NULL OR valid_desde IS NULL OR valid_hasta >= valid_desde",
            name="valid_ordenado",
        ),
        CheckConstraint("known_hasta IS NULL OR known_hasta >= known_desde", name="known_ordenado"),
        # Un extremo abierto solo se declara cuando la fuente lo respalda.
        # DESCONOCIDO nunca es sinónimo de vigencia abierta.
        CheckConstraint(
            "valid_tipo <> 'CERRADO' OR (valid_desde IS NOT NULL AND valid_hasta IS NOT NULL)",
            name="cerrado_con_ambos_extremos",
        ),
        CheckConstraint(
            "valid_tipo <> 'ABIERTO_FIN' OR valid_hasta IS NULL",
            name="abierto_fin_sin_hasta",
        ),
        CheckConstraint(
            "valid_tipo <> 'PUNTUAL' OR (valid_desde IS NOT NULL AND valid_hasta = valid_desde)",
            name="puntual_un_solo_dia",
        ),
        CheckConstraint(
            "valid_tipo <> 'CONDICIONADO' OR condicion_vigencia IS NOT NULL",
            name="condicionado_con_condicion",
        ),
        # Publicar exige haber verificado y haber declarado hasta cuándo la
        # verificación se considera vigente.
        CheckConstraint(
            "estado_revision <> 'PUBLISHED' OR "
            "(release_id IS NOT NULL AND verificado_en IS NOT NULL)",
            name="publicado_con_release_y_verificacion",
        ),
        Index("ix_registro_versiones_entidad", "entidad_tipo", "entidad_id"),
        Index("ix_registro_versiones_valid", "valid_desde", "valid_hasta"),
        Index("ix_registro_versiones_frescura", "reverificar_antes_de"),
        Index("ix_registro_versiones_estado", "estado_revision"),
        # Sólo las publicadas pueden servirse: el índice parcial deja que
        # `v_hechos_servibles` las busque en vez de recorrer el registro entero.
        Index(
            "ix_registro_versiones_publicadas",
            "release_id",
            postgresql_where=text("estado_revision = 'PUBLISHED'"),
        ),
        # Un solo intervalo de conocimiento abierto por versión lógica.
        Index(
            "uq_registro_versiones_known_abierto",
            "entidad_tipo",
            "entidad_id",
            "numero_version",
            unique=True,
            postgresql_where=text("known_hasta IS NULL"),
        ),
    )


class Norma(Base):
    """Identidad jurídica: jurisdicción + emisor + tipo + número + año.

    Las correcciones de título o de URL no crean otra norma. Una norma cuya
    identidad todavía es incierta se queda sin clave canónica en lugar de
    fusionarse especulativamente con otra.
    """

    __tablename__ = "normas"

    id: Mapped[uuid.UUID] = pk_uuid()
    jurisdiccion_id: Mapped[str] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    emisor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    numero: Mapped[str | None] = mapped_column(Text)
    anio: Mapped[int | None] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    materias: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    sancion: Mapped[dt.date | None] = mapped_column(Date)
    promulgacion: Mapped[dt.date | None] = mapped_column(Date)
    publicacion: Mapped[dt.date | None] = mapped_column(Date)
    identidad_incierta: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoNorma),
        CheckConstraint("anio IS NULL OR (anio BETWEEN 1810 AND 2200)", name="anio_plausible"),
        # Clave canónica solo cuando está completa; dos leyes con mismo
        # número/año pero distinta jurisdicción son normas distintas.
        Index(
            "uq_normas_clave_canonica",
            "jurisdiccion_id",
            "tipo",
            "numero",
            "anio",
            unique=True,
            postgresql_where=text(
                "numero IS NOT NULL AND anio IS NOT NULL AND identidad_incierta = false"
            ),
        ),
        Index("ix_normas_emisor_tipo_numero_anio", "emisor_id", "tipo", "numero", "anio"),
        Index("ix_normas_publicacion", "publicacion"),
        # El orden del listado. Sin él, mostrar las primeras veinte normas
        # recorre la tabla entera para ordenarla.
        Index(
            "ix_normas_orden_listado",
            text("anio DESC NULLS LAST"),
            "numero",
        ),
    )


class NormaIdentificador(Base):
    """Identificadores oficiales alternativos, cada uno con su espacio de
    nombres. El id de InfoLEG no se mezcla con el de NormativaBA."""

    __tablename__ = "norma_identificadores"

    id: Mapped[uuid.UUID] = pk_uuid()
    norma_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    namespace: Mapped[str] = mapped_column(String(64), nullable=False)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    url_oficial: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        UniqueConstraint("namespace", "valor", name="uq_norma_identificadores_namespace_valor"),
        CheckConstraint("length(btrim(namespace)) > 0", name="namespace_no_vacio"),
        CheckConstraint(
            "url_oficial IS NULL OR url_oficial ~ '^https?://'", name="url_http_concreta"
        ),
    )


class NormaVersion(Base):
    """Subtipo de `registro_versiones` para una versión de norma.

    `estado_legal_declarado` es lo que dice la fuente; `estado_legal_validado`
    es la conclusión del equipo con su fundamento. Una etiqueta "abrogada" en un
    encabezado no basta para clasificar la norma entera.
    """

    __tablename__ = "norma_versiones"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    norma_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    doc_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documento_versiones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tipo_version: Mapped[str] = mapped_column(String(32), nullable=False)
    estado_legal_declarado: Mapped[str | None] = mapped_column(String(32))
    estado_legal_validado: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'NO_DETERMINADA'")
    )
    fundamento_estado_evidencia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT")
    )
    fecha_consolidacion: Mapped[dt.date | None] = mapped_column(Date)

    __table_args__ = (
        check_vocabulario("tipo_version", voc.TipoVersionDocumento),
        check_vocabulario("estado_legal_declarado", voc.EstadoLegal, nullable=True),
        check_vocabulario("estado_legal_validado", voc.EstadoLegal),
        # Afirmar un estado legal distinto de "no determinada" exige fundamento.
        CheckConstraint(
            "estado_legal_validado = 'NO_DETERMINADA' "
            "OR fundamento_estado_evidencia_id IS NOT NULL",
            name="estado_validado_con_fundamento",
        ),
        CheckConstraint(
            "tipo_version <> 'CONSOLIDADO' OR fecha_consolidacion IS NOT NULL",
            name="consolidado_con_fecha",
        ),
        Index("ix_norma_versiones_norma_tipo", "norma_id", "tipo_version"),
    )


class EquivalenciaUnidad(Base):
    """Correspondencia entre unidades de versiones distintas: renumeración,
    sustitución, división o fusión. Sin esto, una reforma se "parchea por
    número" y se aplica sobre el artículo equivocado."""

    __tablename__ = "equivalencias_unidades"

    id: Mapped[uuid.UUID] = pk_uuid()
    origen_unidad_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destino_unidad_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text)
    estado_revision: Mapped[str] = mapped_column(String(16), nullable=False)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoEquivalenciaUnidad),
        check_vocabulario("estado_revision", voc.EstadoRevision),
        CheckConstraint("origen_unidad_id <> destino_unidad_id", name="origen_distinto_destino"),
        UniqueConstraint(
            "origen_unidad_id", "destino_unidad_id", "tipo", name="uq_equivalencias_par_tipo"
        ),
    )


class RelacionNormativa(Base):
    """Dirección explícita: origen es la norma modificatoria, destino la
    modificada. Citar no prueba modificar, por eso `CITA` es un tipo propio.

    El alcance puede limitarse a un artículo, un inciso, un colectivo o un
    período; los ciclos entre citas son legítimos y la navegación los recorre
    con conjunto de visitados y presupuesto.
    """

    __tablename__ = "relaciones_normativas"

    id: Mapped[uuid.UUID] = pk_uuid()
    norma_origen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    norma_destino_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    unidad_origen_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT")
    )
    unidad_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("unidades_documentales.id", ondelete="RESTRICT")
    )
    alcance: Mapped[str | None] = mapped_column(Text)
    efecto_desde: Mapped[dt.date | None] = mapped_column(Date)
    efecto_hasta: Mapped[dt.date | None] = mapped_column(Date)
    condicion: Mapped[str | None] = mapped_column(Text)
    estado_revision: Mapped[str] = mapped_column(String(16), nullable=False)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoRelacionNormativa),
        check_vocabulario("estado_revision", voc.EstadoRevision),
        CheckConstraint(
            "efecto_hasta IS NULL OR efecto_desde IS NULL OR efecto_hasta >= efecto_desde",
            name="efecto_ordenado",
        ),
        # `NULLS NOT DISTINCT` (PostgreSQL 15+): una relación cuyo alcance es la
        # norma entera deja las unidades en nulo, y con la semántica por defecto
        # cada reejecución de la curación crearía una arista nueva.
        UniqueConstraint(
            "norma_origen_id",
            "norma_destino_id",
            "tipo",
            "unidad_origen_id",
            "unidad_destino_id",
            name="uq_relaciones_normativas_arista",
            postgresql_nulls_not_distinct=True,
        ),
        # Índice inverso: navegar "qué modifica a esta norma" cuesta lo mismo
        # que "qué modifica esta norma".
        Index("ix_relaciones_normativas_destino_tipo", "norma_destino_id", "tipo"),
        Index("ix_relaciones_normativas_origen_tipo", "norma_origen_id", "tipo"),
    )


class ReferenciaPendiente(Base):
    """Cita cuya norma destino todavía no se pudo identificar. Se conserva el
    texto literal y las identidades candidatas; no se inventa un destino ni se
    la descarta en silencio."""

    __tablename__ = "referencias_pendientes"

    id: Mapped[uuid.UUID] = pk_uuid()
    norma_origen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    texto_cita: Mapped[str] = mapped_column(Text, nullable=False)
    identidad_candidata: Mapped[dict | None] = mapped_column(JSONB)
    motivo: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(16), nullable=False)
    responsable_rol: Mapped[str | None] = mapped_column(Text)
    # Al resolverse se conserva la auditoría: la relación creada queda enlazada.
    relacion_resultante_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("relaciones_normativas.id", ondelete="RESTRICT")
    )
    resuelta_en: Mapped[dt.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("estado", voc.EstadoReferenciaPendiente),
        CheckConstraint(
            "estado <> 'RESUELTA' OR "
            "(relacion_resultante_id IS NOT NULL AND resuelta_en IS NOT NULL)",
            name="resuelta_con_relacion",
        ),
        CheckConstraint("length(btrim(texto_cita)) > 0", name="texto_cita_no_vacio"),
        Index("ix_referencias_pendientes_estado", "estado"),
    )
