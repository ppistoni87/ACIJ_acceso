"""Beneficios, poblaciones, reglas de aplicabilidad, parámetros y cuantías.

Norma y beneficio son entidades diferentes, relacionadas muchos-a-muchos: hay
normas institucionales sin beneficio directo y beneficios sostenidos por varias
normas.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, JSONB, UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db import vocabularios as voc
from backend_normativo.db.base import Base, check_vocabulario, pk_uuid, ts_creacion


class Beneficio(Base):
    """Identidad estable de una prestación. `linea` separa variantes que
    comparten programa (por ejemplo, las líneas de una misma beca) y `familia`
    agrupa regímenes: una asignación no se confunde con otra por pertenecer al
    mismo conjunto."""

    __tablename__ = "beneficios"

    id: Mapped[uuid.UUID] = pk_uuid()
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    linea: Mapped[str | None] = mapped_column(Text)
    familia: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint("codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name="codigo_normalizado"),
        Index("ix_beneficios_familia_linea", "familia", "linea"),
    )


class BeneficioVersion(Base):
    """Subtipo de `registro_versiones`. Un valor desconocido se registra como
    estado en `afirmaciones`, no como un booleano en falso por defecto: por eso
    `requiere_solicitud` admite NULL."""

    __tablename__ = "beneficio_versiones"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    beneficio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beneficios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    jurisdiccion_id: Mapped[str] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    autoridad_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organismos.id", ondelete="RESTRICT"), index=True
    )
    naturaleza: Mapped[str] = mapped_column(String(32), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    unidad_beneficiaria: Mapped[str | None] = mapped_column(Text)
    modalidad: Mapped[str | None] = mapped_column(Text)
    frecuencia: Mapped[str | None] = mapped_column(Text)
    cupo: Mapped[str | None] = mapped_column(Text)
    requiere_solicitud: Mapped[bool | None] = mapped_column(Boolean)

    __table_args__ = (check_vocabulario("naturaleza", voc.NaturalezaBeneficio),)


class BeneficioNorma(Base):
    """Vínculo respaldado entre un beneficio y la versión de norma que lo crea,
    reglamenta, financia, modifica, interpreta o aplica."""

    __tablename__ = "beneficio_normas"

    id: Mapped[uuid.UUID] = pk_uuid()
    beneficio_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beneficio_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    norma_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("norma_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    rol: Mapped[str] = mapped_column(String(32), nullable=False)
    alcance: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("rol", voc.RolBeneficioNorma),
        UniqueConstraint(
            "beneficio_version_id", "norma_version_id", "rol", name="uq_beneficio_normas_rol"
        ),
    )


class Poblacion(Base):
    """Vocabulario curado de grupos destinatarios. Describe categorías de una
    disposición, no clasifica personas reales."""

    __tablename__ = "poblaciones"

    id: Mapped[uuid.UUID] = pk_uuid()
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    definicion: Mapped[str | None] = mapped_column(Text)
    vocabulario_version: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint("codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name="codigo_normalizado"),
    )


class BeneficioPoblacion(Base):
    """Titular, causante, representante y conviviente son roles distintos: un
    mismo grupo puede aparecer en varios con alcances diferentes.

    Pertenecer a una categoría no es, por sí solo, un requisito: cuando la
    condición proviene de una regla, `regla_id` la enlaza.
    """

    __tablename__ = "beneficio_poblaciones"

    id: Mapped[uuid.UUID] = pk_uuid()
    beneficio_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beneficio_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    poblacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("poblaciones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    rol_persona: Mapped[str] = mapped_column(String(32), nullable=False)
    alcance: Mapped[str | None] = mapped_column(Text)
    regla_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reglas.id", ondelete="RESTRICT"))
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("rol_persona", voc.RolPersona),
        UniqueConstraint(
            "beneficio_version_id",
            "poblacion_id",
            "rol_persona",
            name="uq_beneficio_poblaciones_rol",
        ),
    )


class Parametro(Base):
    """Concepto medible con unidad propia. Los catálogos se mantienen separados:
    un salario mínimo, un salario de convenio, el monto de una prestación y un
    tope de ingreso no son el mismo parámetro aunque coincidan en un período."""

    __tablename__ = "parametros"

    id: Mapped[uuid.UUID] = pk_uuid()
    codigo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    concepto: Mapped[str] = mapped_column(Text, nullable=False)
    unidad: Mapped[str] = mapped_column(Text, nullable=False)
    moneda: Mapped[str | None] = mapped_column(String(3))
    definicion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        CheckConstraint("codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name="codigo_normalizado"),
        CheckConstraint("moneda IS NULL OR moneda ~ '^[A-Z]{3}$'", name="moneda_iso4217"),
        # Un importe sin moneda no es comparable.
        CheckConstraint("unidad <> 'MONEDA' OR moneda IS NOT NULL", name="importe_con_moneda"),
    )


class ParametroValor(Base):
    """Subtipo de `registro_versiones`: el valor de un parámetro para un período,
    territorio y segmento.

    La exclusión temporal entre valores aprobados se aplica en la migración con
    un `EXCLUDE` sobre el rango de aplicación; los candidatos en conflicto sí
    pueden coexistir, y quedan fuera de la vista servible.
    """

    __tablename__ = "parametro_valores"

    registro_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registro_versiones.id", ondelete="RESTRICT"), primary_key=True
    )
    # Identidad lógica del hecho: "el valor de este parámetro para este
    # territorio, segmento, dimensiones y período". Es lo que apunta
    # `registro_versiones.entidad_id`; corregir el valor publicado crea una
    # versión nueva del mismo hecho, no un hecho distinto.
    hecho_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    parametro_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parametros.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    valor: Mapped[decimal.Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unidad: Mapped[str] = mapped_column(Text, nullable=False)
    moneda: Mapped[str | None] = mapped_column(String(3))
    periodo: Mapped[dt.date | None] = mapped_column(Date)
    territorio_id: Mapped[str | None] = mapped_column(
        ForeignKey("jurisdicciones.id", ondelete="RESTRICT"), index=True
    )
    segmento: Mapped[str | None] = mapped_column(Text)
    dimensiones: Mapped[dict | None] = mapped_column(JSONB)

    # --- Columnas derivadas que sostienen la exclusión temporal --------------
    # `jsonb` normaliza claves y orden, así que su representación textual es
    # canónica y su hash identifica la combinación de dimensiones.
    dimensiones_hash: Mapped[str] = mapped_column(
        Text,
        Computed("md5(coalesce(dimensiones, '{}'::jsonb)::text)", persisted=True),
        nullable=False,
    )
    # Espejo del intervalo de aplicación y del estado de `registro_versiones`,
    # mantenido por trigger. Existe porque una restricción de exclusión no puede
    # abarcar dos tablas: sin este espejo, "sin solapamientos entre valores
    # aprobados" quedaría en una comprobación de aplicación en vez de en el DDL.
    rango_aplicacion: Mapped[object | None] = mapped_column(DATERANGE)
    publicable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        CheckConstraint("moneda IS NULL OR moneda ~ '^[A-Z]{3}$'", name="moneda_iso4217"),
        Index("ix_parametro_valores_parametro_periodo", "parametro_id", "periodo"),
        # Dos valores aprobados no pueden regir a la vez para la misma
        # combinación semántica. Los candidatos en conflicto sí coexisten:
        # quedan fuera de la vista servible hasta que alguien decida.
        ExcludeConstraint(
            ("parametro_id", "="),
            (text("coalesce(territorio_id, '')"), "="),
            (text("coalesce(segmento, '')"), "="),
            ("dimensiones_hash", "="),
            ("rango_aplicacion", "&&"),
            name="parametro_valores_sin_solapamiento",
            using="gist",
            where=text("publicable"),
        ),
    )


class Regla(Base):
    """Condición jurídica con su texto literal y, cuando fue validada, su AST.

    El literal se conserva siempre: preserva negaciones, cuantificadores,
    excepciones y unidades que una paráfrasis pierde. El AST solo se ejecuta
    tras validación (`estado_revision` aprobado y `requiere_revision` en falso).
    """

    __tablename__ = "reglas"

    id: Mapped[uuid.UUID] = pk_uuid()
    beneficio_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beneficio_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT"), nullable=False
    )
    categoria: Mapped[str] = mapped_column(String(32), nullable=False)
    texto_literal: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    ast: Mapped[dict | None] = mapped_column(JSONB)
    ast_schema_version: Mapped[str | None] = mapped_column(Text)
    requiere_revision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    alcance: Mapped[str | None] = mapped_column(Text)
    estado_revision: Mapped[str] = mapped_column(String(16), nullable=False)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("categoria", voc.CategoriaRegla),
        check_vocabulario("estado_revision", voc.EstadoRevision),
        CheckConstraint("length(btrim(texto_literal)) > 0", name="texto_literal_no_vacio"),
        CheckConstraint(
            "ast IS NULL OR ast_schema_version IS NOT NULL", name="ast_con_version_de_esquema"
        ),
        # Una regla ejecutable exige AST validado y revisión cerrada.
        CheckConstraint(
            "requiere_revision = true OR (ast IS NOT NULL AND "
            "estado_revision IN ('APPROVED','PUBLISHED'))",
            name="ejecutable_solo_tras_validacion",
        ),
        Index("ix_reglas_beneficio_categoria", "beneficio_version_id", "categoria"),
    )


class ReglaDependencia(Base):
    """Excepciones y precedencias explícitas entre reglas. Una colisión no se
    resuelve por orden de carga."""

    __tablename__ = "regla_dependencias"

    regla_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reglas.id", ondelete="RESTRICT"), nullable=False
    )
    regla_referida_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reglas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("regla_id", "regla_referida_id", "tipo"),
        check_vocabulario("tipo", voc.TipoDependenciaRegla),
        CheckConstraint("regla_id <> regla_referida_id", name="sin_autodependencia"),
    )


class ReglaParametro(Base):
    """Parámetros que usa el AST de una regla. Un cambio de valor dispara la
    reevaluación de las reglas afectadas."""

    __tablename__ = "regla_parametros"

    regla_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reglas.id", ondelete="RESTRICT"), nullable=False
    )
    parametro_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parametros.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("regla_id", "parametro_id", "rol"),)


class BeneficioCuantia(Base):
    """Cuánto otorga el beneficio. Exactamente una modalidad respaldada.

    El monto del beneficio no es el tope de ingreso ni el costo del trámite:
    cada uno es un parámetro distinto y se guarda por separado.
    """

    __tablename__ = "beneficio_cuantias"

    id: Mapped[uuid.UUID] = pk_uuid()
    beneficio_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beneficio_versiones.registro_version_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidencias.id", ondelete="RESTRICT")
    )
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    valor_fijo: Mapped[decimal.Decimal | None] = mapped_column(Numeric(20, 4))
    moneda: Mapped[str | None] = mapped_column(String(3))
    formula_ast: Mapped[dict | None] = mapped_column(JSONB)
    formula_version: Mapped[str | None] = mapped_column(Text)
    redondeo: Mapped[str | None] = mapped_column(Text)
    unidad_beneficiaria: Mapped[str | None] = mapped_column(Text)
    descripcion_especie: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        check_vocabulario("tipo", voc.TipoCuantia),
        CheckConstraint("moneda IS NULL OR moneda ~ '^[A-Z]{3}$'", name="moneda_iso4217"),
        # Exactamente una modalidad, y con lo que esa modalidad requiere.
        CheckConstraint(
            "(tipo = 'FIJO' AND valor_fijo IS NOT NULL AND moneda IS NOT NULL "
            "  AND formula_ast IS NULL) "
            "OR (tipo = 'FORMULA' AND formula_ast IS NOT NULL AND formula_version IS NOT NULL "
            "  AND valor_fijo IS NULL) "
            "OR (tipo = 'ESPECIE' AND descripcion_especie IS NOT NULL "
            "  AND valor_fijo IS NULL AND formula_ast IS NULL) "
            "OR (tipo = 'NO_INFORMADO' AND valor_fijo IS NULL AND formula_ast IS NULL)",
            name="una_modalidad_respaldada",
        ),
        # Un valor afirmado exige evidencia; "no informado" no la necesita.
        CheckConstraint(
            "tipo = 'NO_INFORMADO' OR evidencia_id IS NOT NULL", name="cuantia_con_evidencia"
        ),
    )


class CuantiaParametro(Base):
    """Insumos de una cuantía derivada: permite invalidarla cuando cambia el
    parámetro del que depende."""

    __tablename__ = "cuantia_parametros"

    cuantia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("beneficio_cuantias.id", ondelete="RESTRICT"), nullable=False
    )
    parametro_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parametros.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("cuantia_id", "parametro_id", "rol"),)
