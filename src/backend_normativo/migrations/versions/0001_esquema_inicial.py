"""Esquema inicial del corpus normativo: las 53 tablas del diccionario.

Crea tablas, claves, vocabularios controlados (`CHECK`), la restricción de
exclusión temporal de los valores de parámetros e índices. Las reglas que
PostgreSQL solo expresa con triggers, funciones, vistas o roles se aplican
en la migración 0002.

Revision ID: 0001_esquema_inicial
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_esquema_inicial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `gen_random_uuid()` para las PK internas y `btree_gist` para la
    # exclusión temporal, que combina igualdad y solapamiento de rangos.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "auditoria_eventos",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=False),
        sa.Column("objeto_id", sa.Text(), nullable=False),
        sa.Column("antes_hash", sa.String(length=64), nullable=True),
        sa.Column("despues_hash", sa.String(length=64), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "ocurrido_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria_eventos")),
    )
    op.create_index(
        "ix_auditoria_eventos_objeto", "auditoria_eventos", ["objeto", "objeto_id"], unique=False
    )
    op.create_index(
        "ix_auditoria_eventos_ocurrido", "auditoria_eventos", ["ocurrido_en"], unique=False
    )
    op.create_table(
        "beneficios",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("linea", sa.Text(), nullable=True),
        sa.Column("familia", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name=op.f("ck_beneficios_codigo_normalizado")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beneficios")),
        sa.UniqueConstraint("codigo", name=op.f("uq_beneficios_codigo")),
    )
    op.create_index("ix_beneficios_familia_linea", "beneficios", ["familia", "linea"], unique=False)
    op.create_table(
        "derivaciones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("algoritmo_version", sa.Text(), nullable=False),
        sa.Column("formula", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resultado", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "ejecutada_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(algoritmo_version)) > 0",
            name=op.f("ck_derivaciones_algoritmo_version_no_vacia"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_derivaciones")),
    )
    op.create_table(
        "jurisdicciones",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("parent_id", sa.String(length=32), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("nivel", sa.String(length=32), nullable=False),
        sa.Column("codigo_oficial", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "nivel IN ('NACIONAL', 'PROVINCIAL', 'CIUDAD_AUTONOMA', 'MUNICIPAL', 'COMUNAL', 'SUPRANACIONAL')",
            name=op.f("ck_jurisdicciones_nivel_vocabulario"),
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name=op.f("ck_jurisdicciones_sin_autopadre")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_jurisdicciones_parent_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jurisdicciones")),
        sa.UniqueConstraint("parent_id", "nombre", name="uq_jurisdicciones_padre_nombre"),
    )
    op.create_index(
        op.f("ix_jurisdicciones_parent_id"), "jurisdicciones", ["parent_id"], unique=False
    )
    op.create_table(
        "parametros",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("concepto", sa.Text(), nullable=False),
        sa.Column("unidad", sa.Text(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=True),
        sa.Column("definicion", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name=op.f("ck_parametros_codigo_normalizado")
        ),
        sa.CheckConstraint(
            "moneda IS NULL OR moneda ~ '^[A-Z]{3}$'", name=op.f("ck_parametros_moneda_iso4217")
        ),
        sa.CheckConstraint(
            "unidad <> 'MONEDA' OR moneda IS NOT NULL",
            name=op.f("ck_parametros_importe_con_moneda"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parametros")),
        sa.UniqueConstraint("codigo", name=op.f("uq_parametros_codigo")),
    )
    op.create_table(
        "poblaciones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("definicion", sa.Text(), nullable=True),
        sa.Column("vocabulario_version", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name=op.f("ck_poblaciones_codigo_normalizado")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_poblaciones")),
        sa.UniqueConstraint("codigo", name=op.f("uq_poblaciones_codigo")),
    )
    op.create_table(
        "releases",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("publicado_en", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=True),
        sa.Column("aprobado_por", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "estado <> 'PUBLICADO' OR (publicado_en IS NOT NULL AND aprobado_por IS NOT NULL  AND manifest_hash IS NOT NULL)",
            name=op.f("ck_releases_publicado_con_acta"),
        ),
        sa.CheckConstraint(
            "estado IN ('BORRADOR', 'PUBLICADO', 'REVERTIDO')",
            name=op.f("ck_releases_estado_vocabulario"),
        ),
        sa.CheckConstraint(
            "manifest_hash IS NULL OR manifest_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_releases_manifest_hash_hex"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_releases")),
    )
    op.create_index(
        "ix_releases_estado_publicado", "releases", ["estado", "publicado_en"], unique=False
    )
    op.create_table(
        "consultas_auditadas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("release_id", sa.UUID(), nullable=False),
        sa.Column("intencion", sa.Text(), nullable=True),
        sa.Column("fecha_consulta", sa.Date(), nullable=True),
        sa.Column("jurisdiccion_id", sa.String(length=32), nullable=True),
        sa.Column("resultado_tipo", sa.Text(), nullable=True),
        sa.Column("evidencias_usadas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reglas_versiones", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column(
            "ocurrido_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "latencia_ms IS NULL OR latencia_ms >= 0",
            name=op.f("ck_consultas_auditadas_latencia_no_negativa"),
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_consultas_auditadas_jurisdiccion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["releases.id"],
            name=op.f("fk_consultas_auditadas_release_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consultas_auditadas")),
    )
    op.create_index(
        "ix_consultas_auditadas_ocurrido", "consultas_auditadas", ["ocurrido_en"], unique=False
    )
    op.create_index(
        op.f("ix_consultas_auditadas_release_id"),
        "consultas_auditadas",
        ["release_id"],
        unique=False,
    )
    op.create_table(
        "eventos_outbox",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("release_id", sa.UUID(), nullable=True),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("aggregate_id", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("entregado_en", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("intentos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ultimo_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('RELEASE_PUBLICADO', 'NORMA_ACTUALIZADA', 'VALOR_ACTUALIZADO', 'PLAZO_ACTUALIZADO', 'CANAL_ACTUALIZADO', 'CONFLICTO_ABIERTO', 'FUENTE_DEGRADADA')",
            name=op.f("ck_eventos_outbox_tipo_vocabulario"),
        ),
        sa.CheckConstraint("intentos >= 0", name=op.f("ck_eventos_outbox_intentos_no_negativos")),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["releases.id"],
            name=op.f("fk_eventos_outbox_release_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eventos_outbox")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_eventos_outbox_idempotency_key")),
    )
    op.create_index(
        "ix_eventos_outbox_pendientes",
        "eventos_outbox",
        ["creado_en"],
        unique=False,
        postgresql_where=sa.text("entregado_en IS NULL"),
    )
    op.create_index(
        op.f("ix_eventos_outbox_release_id"), "eventos_outbox", ["release_id"], unique=False
    )
    op.create_table(
        "organismos",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("jurisdiccion_id", sa.String(length=32), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("sigla", sa.Text(), nullable=True),
        sa.Column("identificador_oficial", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo IN ('EMISOR', 'AUTORIDAD_APLICACION', 'PRESTADOR', 'ORGANISMO_CONTROL', 'ONG', 'OTRO')",
            name=op.f("ck_organismos_tipo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_organismos_jurisdiccion_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organismos")),
        sa.UniqueConstraint(
            "jurisdiccion_id", "nombre", "tipo", name="uq_organismos_jurisdiccion_nombre_tipo"
        ),
    )
    op.create_index(
        op.f("ix_organismos_jurisdiccion_id"), "organismos", ["jurisdiccion_id"], unique=False
    )
    op.create_table(
        "registro_versiones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entidad_tipo", sa.String(length=32), nullable=False),
        sa.Column("entidad_id", sa.UUID(), nullable=False),
        sa.Column("numero_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("estado_revision", sa.String(length=16), nullable=False),
        sa.Column("valid_desde", sa.Date(), nullable=True),
        sa.Column("valid_hasta", sa.Date(), nullable=True),
        sa.Column("valid_tipo", sa.String(length=16), nullable=False),
        sa.Column("condicion_vigencia", sa.Text(), nullable=True),
        sa.Column(
            "known_desde",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("known_hasta", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("verificado_en", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reverificar_antes_de", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("release_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "entidad_tipo IN ('norma', 'beneficio', 'parametro_valor', 'plazo', 'tramite', 'punto_atencion', 'canal', 'barrio_renabap')",
            name=op.f("ck_registro_versiones_entidad_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado_revision <> 'PUBLISHED' OR (release_id IS NOT NULL AND verificado_en IS NOT NULL)",
            name=op.f("ck_registro_versiones_publicado_con_release_y_verificacion"),
        ),
        sa.CheckConstraint(
            "estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')",
            name=op.f("ck_registro_versiones_estado_revision_vocabulario"),
        ),
        sa.CheckConstraint(
            "valid_tipo <> 'ABIERTO_FIN' OR valid_hasta IS NULL",
            name=op.f("ck_registro_versiones_abierto_fin_sin_hasta"),
        ),
        sa.CheckConstraint(
            "valid_tipo <> 'CERRADO' OR (valid_desde IS NOT NULL AND valid_hasta IS NOT NULL)",
            name=op.f("ck_registro_versiones_cerrado_con_ambos_extremos"),
        ),
        sa.CheckConstraint(
            "valid_tipo <> 'CONDICIONADO' OR condicion_vigencia IS NOT NULL",
            name=op.f("ck_registro_versiones_condicionado_con_condicion"),
        ),
        sa.CheckConstraint(
            "valid_tipo <> 'PUNTUAL' OR (valid_desde IS NOT NULL AND valid_hasta = valid_desde)",
            name=op.f("ck_registro_versiones_puntual_un_solo_dia"),
        ),
        sa.CheckConstraint(
            "valid_tipo IN ('CERRADO', 'ABIERTO_FIN', 'ABIERTO_INICIO', 'PUNTUAL', 'CONDICIONADO', 'DESCONOCIDO')",
            name=op.f("ck_registro_versiones_valid_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "known_hasta IS NULL OR known_hasta >= known_desde",
            name=op.f("ck_registro_versiones_known_ordenado"),
        ),
        sa.CheckConstraint(
            "numero_version >= 1", name=op.f("ck_registro_versiones_numero_version_positivo")
        ),
        sa.CheckConstraint(
            "valid_hasta IS NULL OR valid_desde IS NULL OR valid_hasta >= valid_desde",
            name=op.f("ck_registro_versiones_valid_ordenado"),
        ),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["releases.id"],
            name=op.f("fk_registro_versiones_release_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registro_versiones")),
        sa.UniqueConstraint(
            "entidad_tipo", "entidad_id", "numero_version", name="uq_registro_versiones_entidad"
        ),
    )
    op.create_index(
        "ix_registro_versiones_entidad",
        "registro_versiones",
        ["entidad_tipo", "entidad_id"],
        unique=False,
    )
    op.create_index(
        "ix_registro_versiones_estado", "registro_versiones", ["estado_revision"], unique=False
    )
    op.create_index(
        "ix_registro_versiones_frescura",
        "registro_versiones",
        ["reverificar_antes_de"],
        unique=False,
    )
    op.create_index(
        op.f("ix_registro_versiones_release_id"), "registro_versiones", ["release_id"], unique=False
    )
    op.create_index(
        "ix_registro_versiones_valid",
        "registro_versiones",
        ["valid_desde", "valid_hasta"],
        unique=False,
    )
    op.create_index(
        "uq_registro_versiones_known_abierto",
        "registro_versiones",
        ["entidad_tipo", "entidad_id", "numero_version"],
        unique=True,
        postgresql_where=sa.text("known_hasta IS NULL"),
    )
    op.create_table(
        "beneficio_versiones",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("beneficio_id", sa.UUID(), nullable=False),
        sa.Column("jurisdiccion_id", sa.String(length=32), nullable=False),
        sa.Column("autoridad_id", sa.UUID(), nullable=True),
        sa.Column("naturaleza", sa.String(length=32), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("unidad_beneficiaria", sa.Text(), nullable=True),
        sa.Column("modalidad", sa.Text(), nullable=True),
        sa.Column("frecuencia", sa.Text(), nullable=True),
        sa.Column("cupo", sa.Text(), nullable=True),
        sa.Column("requiere_solicitud", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "naturaleza IN ('PRESTACION_MONETARIA', 'PRESTACION_EN_ESPECIE', 'SERVICIO', 'EXENCION', 'PROTECCION', 'ACCESO_A_PROCEDIMIENTO', 'OTRO_EFECTO', 'NO_INFORMADA')",
            name=op.f("ck_beneficio_versiones_naturaleza_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["autoridad_id"],
            ["organismos.id"],
            name=op.f("fk_beneficio_versiones_autoridad_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_id"],
            ["beneficios.id"],
            name=op.f("fk_beneficio_versiones_beneficio_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_beneficio_versiones_jurisdiccion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_beneficio_versiones_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_beneficio_versiones")),
    )
    op.create_index(
        op.f("ix_beneficio_versiones_autoridad_id"),
        "beneficio_versiones",
        ["autoridad_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beneficio_versiones_beneficio_id"),
        "beneficio_versiones",
        ["beneficio_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beneficio_versiones_jurisdiccion_id"),
        "beneficio_versiones",
        ["jurisdiccion_id"],
        unique=False,
    )
    op.create_table(
        "fuentes",
        sa.Column("source_id", sa.String(length=16), nullable=False),
        sa.Column("organismo_id", sa.UUID(), nullable=True),
        sa.Column("alias_of", sa.String(length=16), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("clase", sa.String(length=32), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False),
        sa.Column("access_status", sa.String(length=32), nullable=False),
        sa.Column("prioridad", sa.String(length=4), nullable=False),
        sa.Column("motivo_estado", sa.Text(), nullable=True),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("responsable_rol", sa.Text(), nullable=True),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("politica_acceso", sa.String(length=64), nullable=False),
        sa.Column("relacionadas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("origen", sa.Text(), nullable=True),
        sa.Column("manual_pagina", sa.Integer(), nullable=True),
        sa.Column("origen_url_status", sa.Text(), nullable=True),
        sa.Column("tarea", sa.Text(), nullable=True),
        sa.Column("aceptacion_especifica", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tablas_destino", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("referencia_selectores", sa.Text(), nullable=True),
        sa.Column("referencia_campos", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "access_status IN ('NO_VERIFICADO', 'ACCESIBLE', 'ACCESO_LIMITADO', 'BLOQUEADA', 'ERROR_TLS', 'NO_ENCONTRADA', 'SIN_URL_CONOCIDA')",
            name=op.f("ck_fuentes_access_status_vocabulario"),
        ),
        sa.CheckConstraint(
            "clase IN ('DATASET', 'BOLETIN', 'PORTAL_NORMATIVO', 'FICHA_TRAMITE', 'DIRECTORIO', 'DOCUMENTO', 'PADRON', 'CANAL_ATENCION', 'ALIAS', 'OTRA')",
            name=op.f("ck_fuentes_clase_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado IN ('DISCOVERY', 'ACTIVE', 'DEGRADED', 'QUARANTINED', 'REFERENCE_ONLY', 'MANUAL', 'RETIRED')",
            name=op.f("ck_fuentes_estado_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado NOT IN ('DEGRADED','QUARANTINED','RETIRED') OR motivo_estado IS NOT NULL",
            name=op.f("ck_fuentes_estado_excepcional_con_motivo"),
        ),
        sa.CheckConstraint(
            "politica_acceso IN ('PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS', 'NO_AUTOMATION_UNTIL_IDENTIFIED_AND_PUBLIC', 'MANUAL_ONLY')",
            name=op.f("ck_fuentes_politica_acceso_vocabulario"),
        ),
        sa.CheckConstraint(
            "prioridad IN ('P0', 'P1', 'P2', 'P3')", name=op.f("ck_fuentes_prioridad_vocabulario")
        ),
        sa.CheckConstraint(
            "alias_of IS NULL OR alias_of <> source_id", name=op.f("ck_fuentes_sin_autoalias")
        ),
        sa.ForeignKeyConstraint(
            ["alias_of"],
            ["fuentes.source_id"],
            name=op.f("fk_fuentes_alias_of"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organismo_id"],
            ["organismos.id"],
            name=op.f("fk_fuentes_organismo_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("source_id", name=op.f("pk_fuentes")),
    )
    op.create_index(op.f("ix_fuentes_alias_of"), "fuentes", ["alias_of"], unique=False)
    op.create_index("ix_fuentes_estado_prioridad", "fuentes", ["estado", "prioridad"], unique=False)
    op.create_index(op.f("ix_fuentes_organismo_id"), "fuentes", ["organismo_id"], unique=False)
    op.create_table(
        "normas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("jurisdiccion_id", sa.String(length=32), nullable=False),
        sa.Column("emisor_id", sa.UUID(), nullable=True),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("numero", sa.Text(), nullable=True),
        sa.Column("anio", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("materias", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("sancion", sa.Date(), nullable=True),
        sa.Column("promulgacion", sa.Date(), nullable=True),
        sa.Column("publicacion", sa.Date(), nullable=True),
        sa.Column(
            "identidad_incierta", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo IN ('LEY', 'DECRETO', 'RESOLUCION', 'DISPOSICION', 'ORDENANZA', 'DECRETO_LEY', 'ACORDADA', 'CONVENIO', 'CONSTITUCION', 'TRATADO', 'OTRO')",
            name=op.f("ck_normas_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "anio IS NULL OR (anio BETWEEN 1810 AND 2200)", name=op.f("ck_normas_anio_plausible")
        ),
        sa.ForeignKeyConstraint(
            ["emisor_id"], ["organismos.id"], name=op.f("fk_normas_emisor_id"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_normas_jurisdiccion_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_normas")),
    )
    op.create_index(op.f("ix_normas_emisor_id"), "normas", ["emisor_id"], unique=False)
    op.create_index(
        "ix_normas_emisor_tipo_numero_anio",
        "normas",
        ["emisor_id", "tipo", "numero", "anio"],
        unique=False,
    )
    op.create_index(op.f("ix_normas_jurisdiccion_id"), "normas", ["jurisdiccion_id"], unique=False)
    op.create_index("ix_normas_publicacion", "normas", ["publicacion"], unique=False)
    op.create_index(
        "uq_normas_clave_canonica",
        "normas",
        ["jurisdiccion_id", "tipo", "numero", "anio"],
        unique=True,
        postgresql_where=sa.text(
            "numero IS NOT NULL AND anio IS NOT NULL AND identidad_incierta = false"
        ),
    )
    op.create_table(
        "puntos_atencion",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organismo_id", sa.UUID(), nullable=False),
        sa.Column("jurisdiccion_id", sa.String(length=32), nullable=False),
        sa.Column("organismo_operador_id", sa.UUID(), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo IN ('SEDE', 'DELEGACION', 'OFICINA_MOVIL', 'CENTRO_COMUNITARIO', 'JUZGADO', 'OTRO')",
            name=op.f("ck_puntos_atencion_tipo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_puntos_atencion_jurisdiccion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organismo_id"],
            ["organismos.id"],
            name=op.f("fk_puntos_atencion_organismo_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organismo_operador_id"],
            ["organismos.id"],
            name=op.f("fk_puntos_atencion_organismo_operador_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_puntos_atencion")),
    )
    op.create_index(
        op.f("ix_puntos_atencion_jurisdiccion_id"),
        "puntos_atencion",
        ["jurisdiccion_id"],
        unique=False,
    )
    op.create_index("ix_puntos_atencion_nombre", "puntos_atencion", ["nombre"], unique=False)
    op.create_index(
        op.f("ix_puntos_atencion_organismo_id"), "puntos_atencion", ["organismo_id"], unique=False
    )
    op.create_table(
        "tramites",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organismo_id", sa.UUID(), nullable=False),
        sa.Column("beneficio_id", sa.UUID(), nullable=True),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("publico", sa.String(length=16), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'", name=op.f("ck_tramites_codigo_normalizado")
        ),
        sa.CheckConstraint(
            "publico IN ('CIUDADANO', 'INSTITUCIONAL', 'AMBOS', 'NO_INFORMADO')",
            name=op.f("ck_tramites_publico_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_id"],
            ["beneficios.id"],
            name=op.f("fk_tramites_beneficio_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organismo_id"],
            ["organismos.id"],
            name=op.f("fk_tramites_organismo_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tramites")),
        sa.UniqueConstraint("codigo", name=op.f("uq_tramites_codigo")),
    )
    op.create_index(op.f("ix_tramites_beneficio_id"), "tramites", ["beneficio_id"], unique=False)
    op.create_index(op.f("ix_tramites_organismo_id"), "tramites", ["organismo_id"], unique=False)
    op.create_table(
        "calendarios",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("jurisdiccion_id", sa.String(length=32), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("fecha_desde", sa.Date(), nullable=False),
        sa.Column("fecha_hasta", sa.Date(), nullable=False),
        sa.Column("fuente_id", sa.String(length=16), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "fecha_hasta >= fecha_desde", name=op.f("ck_calendarios_cobertura_ordenada")
        ),
        sa.ForeignKeyConstraint(
            ["fuente_id"],
            ["fuentes.source_id"],
            name=op.f("fk_calendarios_fuente_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_calendarios_jurisdiccion_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendarios")),
        sa.UniqueConstraint("jurisdiccion_id", "nombre", "version", name="uq_calendarios_version"),
    )
    op.create_index(
        op.f("ix_calendarios_jurisdiccion_id"), "calendarios", ["jurisdiccion_id"], unique=False
    )
    op.create_table(
        "documentos",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.String(length=16), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=True),
        sa.Column("idioma", sa.String(length=8), server_default=sa.text("'es'"), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo IN ('NORMA', 'ANEXO', 'GUIA', 'FAQ', 'DATASET', 'PROCEDIMIENTO', 'DIRECTORIO', 'PADRON', 'OTRO')",
            name=op.f("ck_documentos_tipo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["fuentes.source_id"],
            name=op.f("fk_documentos_source_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documentos")),
        sa.UniqueConstraint("source_id", "external_id", name="uq_documentos_source_external"),
    )
    op.create_index(op.f("ix_documentos_source_id"), "documentos", ["source_id"], unique=False)
    op.create_table(
        "fuente_config_versiones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("adaptador", sa.String(length=32), nullable=False),
        sa.Column("selector_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("frecuencia", sa.Interval(), nullable=True),
        sa.Column("ttl_defecto", sa.Interval(), nullable=True),
        sa.Column("presupuesto", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("politica_version", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "adaptador IN ('DATASET_ABIERTO', 'HTML_ESTATICO', 'API_JSON', 'PDF', 'CARGA_MANUAL', 'SIN_ADAPTADOR')",
            name=op.f("ck_fuente_config_versiones_adaptador_vocabulario"),
        ),
        sa.CheckConstraint(
            "version >= 1", name=op.f("ck_fuente_config_versiones_version_positiva")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["fuentes.source_id"],
            name=op.f("fk_fuente_config_versiones_source_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuente_config_versiones")),
        sa.UniqueConstraint(
            "source_id", "version", name="uq_fuente_config_versiones_source_version"
        ),
    )
    op.create_index(
        op.f("ix_fuente_config_versiones_source_id"),
        "fuente_config_versiones",
        ["source_id"],
        unique=False,
    )
    op.create_table(
        "fuente_urls",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.String(length=16), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("rol", sa.String(length=32), nullable=False),
        sa.Column("tipo_acceso", sa.String(length=32), nullable=False),
        sa.Column("es_canonica", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "descubierta_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("url_padre_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "rol IN ('ENTRADA', 'LISTADO', 'DETALLE', 'DESCARGA', 'API', 'ANEXO', 'ALTERNATIVA')",
            name=op.f("ck_fuente_urls_rol_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo_acceso IN ('HTTP_GET_PUBLICO', 'API_PUBLICA', 'DESCARGA_ARCHIVO', 'CARGA_MANUAL')",
            name=op.f("ck_fuente_urls_tipo_acceso_vocabulario"),
        ),
        sa.CheckConstraint("url !~ '[{}]'", name=op.f("ck_fuente_urls_url_sin_plantilla")),
        sa.CheckConstraint("url ~ '^https?://'", name=op.f("ck_fuente_urls_url_http_concreta")),
        sa.CheckConstraint(
            "url_padre_id IS NULL OR url_padre_id <> id", name=op.f("ck_fuente_urls_sin_autopadre")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["fuentes.source_id"],
            name=op.f("fk_fuente_urls_source_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["url_padre_id"],
            ["fuente_urls.id"],
            name=op.f("fk_fuente_urls_url_padre_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuente_urls")),
        sa.UniqueConstraint("source_id", "url", name="uq_fuente_urls_source_url"),
    )
    op.create_index(op.f("ix_fuente_urls_source_id"), "fuente_urls", ["source_id"], unique=False)
    op.create_index(
        op.f("ix_fuente_urls_url_padre_id"), "fuente_urls", ["url_padre_id"], unique=False
    )
    op.create_table(
        "norma_identificadores",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("norma_id", sa.UUID(), nullable=False),
        sa.Column("namespace", sa.String(length=64), nullable=False),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("url_oficial", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "url_oficial IS NULL OR url_oficial ~ '^https?://'",
            name=op.f("ck_norma_identificadores_url_http_concreta"),
        ),
        sa.CheckConstraint(
            "length(btrim(namespace)) > 0", name=op.f("ck_norma_identificadores_namespace_no_vacio")
        ),
        sa.ForeignKeyConstraint(
            ["norma_id"],
            ["normas.id"],
            name=op.f("fk_norma_identificadores_norma_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_norma_identificadores")),
        sa.UniqueConstraint("namespace", "valor", name="uq_norma_identificadores_namespace_valor"),
    )
    op.create_index(
        op.f("ix_norma_identificadores_norma_id"),
        "norma_identificadores",
        ["norma_id"],
        unique=False,
    )
    op.create_table(
        "punto_versiones",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("punto_id", sa.UUID(), nullable=False),
        sa.Column("direccion_cruda", sa.Text(), nullable=True),
        sa.Column("direccion_legible", sa.Text(), nullable=True),
        sa.Column("localidad", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("lng", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("coordenadas_origen", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("crs", sa.Text(), nullable=True),
        sa.Column("es_presencial", sa.Boolean(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(lat IS NULL) = (lng IS NULL)",
            name=op.f("ck_punto_versiones_coordenadas_completas_o_ausentes"),
        ),
        sa.CheckConstraint(
            "lat IS NULL OR (lat BETWEEN -90 AND 90 AND lng BETWEEN -180 AND 180)",
            name=op.f("ck_punto_versiones_coordenadas_en_rango"),
        ),
        sa.CheckConstraint(
            "lat IS NULL OR crs IS NOT NULL", name=op.f("ck_punto_versiones_coordenadas_con_crs")
        ),
        sa.ForeignKeyConstraint(
            ["punto_id"],
            ["puntos_atencion.id"],
            name=op.f("fk_punto_versiones_punto_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_punto_versiones_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_punto_versiones")),
    )
    op.create_index("ix_punto_versiones_localidad", "punto_versiones", ["localidad"], unique=False)
    op.create_index(
        op.f("ix_punto_versiones_punto_id"), "punto_versiones", ["punto_id"], unique=False
    )
    op.create_table(
        "corridas_ingesta",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.String(length=16), nullable=False),
        sa.Column("config_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "inicio",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fin", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False),
        sa.Column("extractor_version", sa.Text(), nullable=False),
        sa.Column("solicitadas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("descargadas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("procesadas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rechazadas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("detalle_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "estado <> 'COMPLETA' OR (fin IS NOT NULL AND procesadas + rechazadas = solicitadas)",
            name=op.f("ck_corridas_ingesta_completa_reconciliada"),
        ),
        sa.CheckConstraint(
            "estado IN ('EN_CURSO', 'COMPLETA', 'PARCIAL', 'FALLIDA', 'CANCELADA')",
            name=op.f("ck_corridas_ingesta_estado_vocabulario"),
        ),
        sa.CheckConstraint(
            "descargadas <= solicitadas",
            name=op.f("ck_corridas_ingesta_descargadas_hasta_solicitadas"),
        ),
        sa.CheckConstraint(
            "fin IS NULL OR fin >= inicio", name=op.f("ck_corridas_ingesta_fin_posterior_a_inicio")
        ),
        sa.CheckConstraint(
            "procesadas + rechazadas <= solicitadas",
            name=op.f("ck_corridas_ingesta_resueltas_hasta_solicitadas"),
        ),
        sa.CheckConstraint(
            "procesadas <= descargadas",
            name=op.f("ck_corridas_ingesta_procesadas_hasta_descargadas"),
        ),
        sa.CheckConstraint(
            "solicitadas >= 0 AND descargadas >= 0 AND procesadas >= 0 AND rechazadas >= 0",
            name=op.f("ck_corridas_ingesta_contadores_no_negativos"),
        ),
        sa.ForeignKeyConstraint(
            ["config_version_id"],
            ["fuente_config_versiones.id"],
            name=op.f("fk_corridas_ingesta_config_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["fuentes.source_id"],
            name=op.f("fk_corridas_ingesta_source_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_corridas_ingesta")),
    )
    op.create_index(
        op.f("ix_corridas_ingesta_config_version_id"),
        "corridas_ingesta",
        ["config_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_corridas_ingesta_source_id"), "corridas_ingesta", ["source_id"], unique=False
    )
    op.create_index(
        "ix_corridas_ingesta_source_inicio",
        "corridas_ingesta",
        ["source_id", "inicio"],
        unique=False,
    )
    op.create_table(
        "capturas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("corrida_id", sa.UUID(), nullable=False),
        sa.Column("source_url_id", sa.UUID(), nullable=False),
        sa.Column("captura_previa_id", sa.UUID(), nullable=True),
        sa.Column("url_final", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column(
            "capturado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("mime", sa.Text(), nullable=True),
        sa.Column("bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256_raw", sa.String(length=64), nullable=False),
        sa.Column("sha256_semantico", sa.String(length=64), nullable=True),
        sa.Column("objeto_uri", sa.Text(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column("cabeceras", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("redirecciones", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "objeto_uri ~ '^[a-z][a-z0-9+.-]*://'", name=op.f("ck_capturas_objeto_uri_con_esquema")
        ),
        sa.CheckConstraint(
            "sha256_raw ~ '^[0-9a-f]{64}$'", name=op.f("ck_capturas_sha256_raw_hex")
        ),
        sa.CheckConstraint(
            "sha256_semantico IS NULL OR sha256_semantico ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_capturas_sha256_semantico_hex"),
        ),
        sa.CheckConstraint(
            "bytes IS NULL OR bytes >= 0", name=op.f("ck_capturas_bytes_no_negativos")
        ),
        sa.CheckConstraint("captura_previa_id <> id", name=op.f("ck_capturas_sin_autoprevia")),
        sa.CheckConstraint(
            "http_status <> 304 OR captura_previa_id IS NOT NULL",
            name=op.f("ck_capturas_revalidacion_304_exige_captura_previa"),
        ),
        sa.CheckConstraint(
            "http_status IS NULL OR (http_status BETWEEN 100 AND 599)",
            name=op.f("ck_capturas_http_status_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["captura_previa_id"],
            ["capturas.id"],
            name=op.f("fk_capturas_captura_previa_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["corrida_id"],
            ["corridas_ingesta.id"],
            name=op.f("fk_capturas_corrida_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_url_id"],
            ["fuente_urls.id"],
            name=op.f("fk_capturas_source_url_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capturas")),
    )
    op.create_index(
        op.f("ix_capturas_captura_previa_id"), "capturas", ["captura_previa_id"], unique=False
    )
    op.create_index(op.f("ix_capturas_corrida_id"), "capturas", ["corrida_id"], unique=False)
    op.create_index("ix_capturas_sha256_raw", "capturas", ["sha256_raw"], unique=False)
    op.create_index(op.f("ix_capturas_source_url_id"), "capturas", ["source_url_id"], unique=False)
    op.create_index(
        "ix_capturas_url_capturado", "capturas", ["source_url_id", "capturado_en"], unique=False
    )
    op.create_table(
        "controles_calidad",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("registro_version_id", sa.UUID(), nullable=True),
        sa.Column("corrida_id", sa.UUID(), nullable=True),
        sa.Column("control_id", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("resultado", sa.String(length=16), nullable=False),
        sa.Column("severidad", sa.String(length=16), nullable=False),
        sa.Column("observado", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("esperado", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "ejecutado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "resultado <> 'FALLA' OR observado IS NOT NULL",
            name=op.f("ck_controles_calidad_falla_con_observado"),
        ),
        sa.CheckConstraint(
            "resultado IN ('PASA', 'FALLA', 'ADVERTENCIA', 'NO_APLICA')",
            name=op.f("ck_controles_calidad_resultado_vocabulario"),
        ),
        sa.CheckConstraint(
            "severidad IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')",
            name=op.f("ck_controles_calidad_severidad_vocabulario"),
        ),
        sa.CheckConstraint(
            "registro_version_id IS NOT NULL OR corrida_id IS NOT NULL",
            name=op.f("ck_controles_calidad_control_con_objeto"),
        ),
        sa.ForeignKeyConstraint(
            ["corrida_id"],
            ["corridas_ingesta.id"],
            name=op.f("fk_controles_calidad_corrida_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_controles_calidad_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_controles_calidad")),
    )
    op.create_index(
        "ix_controles_calidad_control_resultado",
        "controles_calidad",
        ["control_id", "resultado"],
        unique=False,
    )
    op.create_index(
        op.f("ix_controles_calidad_corrida_id"), "controles_calidad", ["corrida_id"], unique=False
    )
    op.create_index(
        "ix_controles_calidad_ejecutado", "controles_calidad", ["ejecutado_en"], unique=False
    )
    op.create_index(
        op.f("ix_controles_calidad_registro_version_id"),
        "controles_calidad",
        ["registro_version_id"],
        unique=False,
    )
    op.create_table(
        "documento_versiones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("documento_id", sa.UUID(), nullable=False),
        sa.Column("captura_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tipo_version", sa.String(length=32), nullable=False),
        sa.Column("fecha_documento", sa.Date(), nullable=True),
        sa.Column("tipo_fecha", sa.String(length=32), nullable=False),
        sa.Column("texto_extraido", sa.Text(), nullable=True),
        sa.Column("hash_texto", sa.String(length=64), nullable=False),
        sa.Column("modo_extraccion", sa.String(length=16), nullable=False),
        sa.Column("extractor_version", sa.Text(), nullable=False),
        sa.Column("paginas", sa.Integer(), nullable=True),
        sa.Column("chars_por_pagina", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extraccion_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("identidad_candidata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "fecha_documento IS NULL OR tipo_fecha <> 'DESCONOCIDA'",
            name=op.f("ck_documento_versiones_fecha_con_tipo_declarado"),
        ),
        sa.CheckConstraint(
            "hash_texto ~ '^[0-9a-f]{64}$'", name=op.f("ck_documento_versiones_hash_texto_hex")
        ),
        sa.CheckConstraint(
            "modo_extraccion IN ('HTML', 'JSON', 'CSV', 'PDF_TEXTO', 'PDF_OCR', 'MANUAL')",
            name=op.f("ck_documento_versiones_modo_extraccion_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo_fecha IN ('SANCION', 'PROMULGACION', 'PUBLICACION', 'FIRMA', 'CABECERA', 'ACTUALIZACION_SITIO', 'DESCONOCIDA')",
            name=op.f("ck_documento_versiones_tipo_fecha_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo_version IN ('ORIGINAL', 'ACTUALIZADO', 'CONSOLIDADO', 'NO_DETERMINADO')",
            name=op.f("ck_documento_versiones_tipo_version_vocabulario"),
        ),
        sa.CheckConstraint(
            "extraccion_score IS NULL OR (extraccion_score BETWEEN 0 AND 1)",
            name=op.f("ck_documento_versiones_score_entre_cero_y_uno"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_documento_versiones_version_positiva")),
        sa.ForeignKeyConstraint(
            ["captura_id"],
            ["capturas.id"],
            name=op.f("fk_documento_versiones_captura_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["documento_id"],
            ["documentos.id"],
            name=op.f("fk_documento_versiones_documento_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documento_versiones")),
        sa.UniqueConstraint(
            "documento_id", "hash_texto", "tipo_version", name="uq_documento_versiones_contenido"
        ),
        sa.UniqueConstraint("documento_id", "version", name="uq_documento_versiones_numero"),
    )
    op.create_index(
        op.f("ix_documento_versiones_captura_id"),
        "documento_versiones",
        ["captura_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documento_versiones_documento_id"),
        "documento_versiones",
        ["documento_id"],
        unique=False,
    )
    op.create_index(
        "ix_documento_versiones_fecha", "documento_versiones", ["fecha_documento"], unique=False
    )
    op.create_table(
        "tramite_versiones",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("tramite_id", sa.UUID(), nullable=False),
        sa.Column("doc_version_id", sa.UUID(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("cta_url", sa.Text(), nullable=True),
        sa.Column("costo_parametro_id", sa.UUID(), nullable=True),
        sa.Column("duracion_texto", sa.Text(), nullable=True),
        sa.Column("estado_operativo", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "cta_url IS NULL OR cta_url ~ '^https?://'",
            name=op.f("ck_tramite_versiones_url_http_concreta"),
        ),
        sa.CheckConstraint(
            "estado_operativo IN ('DISPONIBLE', 'SIN_TURNOS', 'SUSPENDIDO', 'NO_INFORMADO')",
            name=op.f("ck_tramite_versiones_estado_operativo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["costo_parametro_id"],
            ["parametros.id"],
            name=op.f("fk_tramite_versiones_costo_parametro_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doc_version_id"],
            ["documento_versiones.id"],
            name=op.f("fk_tramite_versiones_doc_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_tramite_versiones_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tramite_id"],
            ["tramites.id"],
            name=op.f("fk_tramite_versiones_tramite_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_tramite_versiones")),
    )
    op.create_index(
        op.f("ix_tramite_versiones_doc_version_id"),
        "tramite_versiones",
        ["doc_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tramite_versiones_tramite_id"), "tramite_versiones", ["tramite_id"], unique=False
    )
    op.create_table(
        "unidades_documentales",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("doc_version_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("numero", sa.Text(), nullable=True),
        sa.Column("sufijo", sa.Text(), nullable=True),
        sa.Column("rotulo", sa.Text(), nullable=True),
        sa.Column("ruta", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("inicio", sa.Integer(), nullable=True),
        sa.Column("fin", sa.Integer(), nullable=True),
        sa.Column("pagina_desde", sa.Integer(), nullable=True),
        sa.Column("pagina_hasta", sa.Integer(), nullable=True),
        sa.Column("rol_contenido", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "rol_contenido IN ('DISPOSITIVO', 'CITADO', 'SUSTITUTIVO', 'INCORPORADO', 'HISTORICO', 'NOTA')",
            name=op.f("ck_unidades_documentales_rol_contenido_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo IN ('PREAMBULO', 'VISTO', 'CONSIDERANDO', 'LIBRO', 'TITULO', 'CAPITULO', 'SECCION', 'ARTICULO', 'INCISO', 'PARRAFO', 'ANEXO', 'TRANSITORIA', 'FIRMA', 'TABLA', 'NO_RECONOCIDO')",
            name=op.f("ck_unidades_documentales_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "fin IS NULL OR inicio IS NULL OR fin >= inicio",
            name=op.f("ck_unidades_documentales_offsets_ordenados"),
        ),
        sa.CheckConstraint(
            "pagina_hasta IS NULL OR pagina_desde IS NULL OR pagina_hasta >= pagina_desde",
            name=op.f("ck_unidades_documentales_paginas_ordenadas"),
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name=op.f("ck_unidades_documentales_sin_autopadre"),
        ),
        sa.ForeignKeyConstraint(
            ["doc_version_id"],
            ["documento_versiones.id"],
            name=op.f("fk_unidades_documentales_doc_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_unidades_documentales_parent_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_unidades_documentales")),
    )
    op.create_index(
        op.f("ix_unidades_documentales_doc_version_id"),
        "unidades_documentales",
        ["doc_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_unidades_documentales_parent_id"),
        "unidades_documentales",
        ["parent_id"],
        unique=False,
    )
    op.create_index(
        "ix_unidades_documentales_version_orden",
        "unidades_documentales",
        ["doc_version_id", "orden"],
        unique=False,
    )
    op.create_index(
        "uq_unidades_documentales_ruta_dispositiva",
        "unidades_documentales",
        ["doc_version_id", "ruta"],
        unique=True,
        postgresql_where=sa.text("rol_contenido = 'DISPOSITIVO'"),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("unidad_id", sa.UUID(), nullable=False),
        sa.Column("registro_version_id", sa.UUID(), nullable=True),
        sa.Column("release_id", sa.UUID(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("modelo_embedding", sa.Text(), nullable=True),
        sa.Column("embedding_ref", sa.Text(), nullable=True),
        sa.CheckConstraint("hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_chunks_hash_hex")),
        sa.CheckConstraint(
            "tipo IN ('UNIDAD_NORMATIVA', 'PROCEDIMIENTO', 'FAQ', 'ANEXO')",
            name=op.f("ck_chunks_tipo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_chunks_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["release_id"], ["releases.id"], name=op.f("fk_chunks_release_id"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["unidad_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_chunks_unidad_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks")),
        sa.UniqueConstraint(
            "release_id", "unidad_id", "hash", name="uq_chunks_release_unidad_hash"
        ),
    )
    op.create_index(
        op.f("ix_chunks_registro_version_id"), "chunks", ["registro_version_id"], unique=False
    )
    op.create_index(op.f("ix_chunks_release_id"), "chunks", ["release_id"], unique=False)
    op.create_index(op.f("ix_chunks_unidad_id"), "chunks", ["unidad_id"], unique=False)
    op.create_table(
        "evidencias",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("doc_version_id", sa.UUID(), nullable=False),
        sa.Column("unidad_id", sa.UUID(), nullable=True),
        sa.Column("fragmento", sa.Text(), nullable=False),
        sa.Column("selector", sa.Text(), nullable=True),
        sa.Column("pagina", sa.Integer(), nullable=True),
        sa.Column("offset_inicio", sa.Integer(), nullable=True),
        sa.Column("offset_fin", sa.Integer(), nullable=True),
        sa.Column("hash_fragmento", sa.String(length=64), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "hash_fragmento ~ '^[0-9a-f]{64}$'", name=op.f("ck_evidencias_hash_fragmento_hex")
        ),
        sa.CheckConstraint(
            "tipo IN ('FRAGMENTO_TEXTO', 'CELDA_TABLA', 'CAMPO_JSON', 'CAMPO_CSV', 'REGION_PDF', 'CARGA_MANUAL')",
            name=op.f("ck_evidencias_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "length(btrim(fragmento)) > 0", name=op.f("ck_evidencias_fragmento_no_vacio")
        ),
        sa.CheckConstraint(
            "offset_fin IS NULL OR offset_inicio IS NULL OR offset_fin >= offset_inicio",
            name=op.f("ck_evidencias_offsets_ordenados"),
        ),
        sa.ForeignKeyConstraint(
            ["doc_version_id"],
            ["documento_versiones.id"],
            name=op.f("fk_evidencias_doc_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unidad_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_evidencias_unidad_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidencias")),
    )
    op.create_index(
        op.f("ix_evidencias_doc_version_id"), "evidencias", ["doc_version_id"], unique=False
    )
    op.create_index("ix_evidencias_hash", "evidencias", ["hash_fragmento"], unique=False)
    op.create_index(op.f("ix_evidencias_unidad_id"), "evidencias", ["unidad_id"], unique=False)
    op.create_table(
        "afirmaciones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=True),
        sa.Column("campo_path", sa.Text(), nullable=False),
        sa.Column("valor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado_campo", sa.String(length=40), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("fuentes_revisadas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_id", sa.String(length=16), nullable=True),
        sa.Column("estado_revision", sa.String(length=16), nullable=False),
        sa.Column(
            "observado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("derivacion_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "estado_campo <> 'INFORMADO' OR (valor IS NOT NULL AND evidencia_id IS NOT NULL)",
            name=op.f("ck_afirmaciones_informado_con_valor_y_evidencia"),
        ),
        sa.CheckConstraint(
            "estado_campo <> 'NO_APLICA_JUSTIFICADO' OR (motivo IS NOT NULL AND evidencia_id IS NOT NULL)",
            name=op.f("ck_afirmaciones_no_aplica_con_motivo_y_fundamento"),
        ),
        sa.CheckConstraint(
            "estado_campo <> 'NO_INFORMADO_EN_FUENTES_REVISADAS' OR (fuentes_revisadas IS NOT NULL AND jsonb_array_length(fuentes_revisadas) > 0)",
            name=op.f("ck_afirmaciones_no_informado_con_fuentes_revisadas"),
        ),
        sa.CheckConstraint(
            "estado_campo IN ('PENDIENTE', 'INFORMADO', 'NO_INFORMADO_EN_FUENTES_REVISADAS', 'NO_APLICA_JUSTIFICADO', 'EN_CONFLICTO')",
            name=op.f("ck_afirmaciones_estado_campo_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')",
            name=op.f("ck_afirmaciones_estado_revision_vocabulario"),
        ),
        sa.CheckConstraint(
            "length(btrim(campo_path)) > 0", name=op.f("ck_afirmaciones_campo_path_no_vacio")
        ),
        sa.ForeignKeyConstraint(
            ["derivacion_id"],
            ["derivaciones.id"],
            name=op.f("fk_afirmaciones_derivacion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_afirmaciones_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_afirmaciones_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["fuentes.source_id"],
            name=op.f("fk_afirmaciones_source_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_afirmaciones")),
    )
    op.create_index("ix_afirmaciones_estado_campo", "afirmaciones", ["estado_campo"], unique=False)
    op.create_index(
        op.f("ix_afirmaciones_evidencia_id"), "afirmaciones", ["evidencia_id"], unique=False
    )
    op.create_index(
        op.f("ix_afirmaciones_registro_version_id"),
        "afirmaciones",
        ["registro_version_id"],
        unique=False,
    )
    op.create_index(op.f("ix_afirmaciones_source_id"), "afirmaciones", ["source_id"], unique=False)
    op.create_index(
        "ix_afirmaciones_version_campo",
        "afirmaciones",
        ["registro_version_id", "campo_path"],
        unique=False,
    )
    op.create_table(
        "barrios_renabap",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("barrio_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("id_renabap", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("provincia", sa.Text(), nullable=True),
        sa.Column("departamento", sa.Text(), nullable=True),
        sa.Column("localidad", sa.Text(), nullable=True),
        sa.Column("viviendas", sa.BigInteger(), nullable=True),
        sa.Column("familias", sa.BigInteger(), nullable=True),
        sa.Column("datos_habitacionales", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fecha_corte", sa.Date(), nullable=True),
        sa.Column("padron_version", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "familias IS NULL OR familias >= 0",
            name=op.f("ck_barrios_renabap_familias_no_negativas"),
        ),
        sa.CheckConstraint(
            "viviendas IS NULL OR viviendas >= 0",
            name=op.f("ck_barrios_renabap_viviendas_no_negativas"),
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_barrios_renabap_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_barrios_renabap_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_barrios_renabap")),
        sa.UniqueConstraint("id_renabap", "padron_version", name="uq_barrios_renabap_padron"),
    )
    op.create_index(
        op.f("ix_barrios_renabap_barrio_id"), "barrios_renabap", ["barrio_id"], unique=False
    )
    op.create_index(
        "ix_barrios_renabap_provincia_localidad",
        "barrios_renabap",
        ["provincia", "localidad"],
        unique=False,
    )
    op.create_table(
        "beneficio_cuantias",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("beneficio_version_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=True),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("valor_fijo", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("moneda", sa.String(length=3), nullable=True),
        sa.Column("formula_ast", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("formula_version", sa.Text(), nullable=True),
        sa.Column("redondeo", sa.Text(), nullable=True),
        sa.Column("unidad_beneficiaria", sa.Text(), nullable=True),
        sa.Column("descripcion_especie", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(tipo = 'FIJO' AND valor_fijo IS NOT NULL AND moneda IS NOT NULL   AND formula_ast IS NULL) OR (tipo = 'FORMULA' AND formula_ast IS NOT NULL AND formula_version IS NOT NULL   AND valor_fijo IS NULL) OR (tipo = 'ESPECIE' AND descripcion_especie IS NOT NULL   AND valor_fijo IS NULL AND formula_ast IS NULL) OR (tipo = 'NO_INFORMADO' AND valor_fijo IS NULL AND formula_ast IS NULL)",
            name=op.f("ck_beneficio_cuantias_una_modalidad_respaldada"),
        ),
        sa.CheckConstraint(
            "moneda IS NULL OR moneda ~ '^[A-Z]{3}$'",
            name=op.f("ck_beneficio_cuantias_moneda_iso4217"),
        ),
        sa.CheckConstraint(
            "tipo = 'NO_INFORMADO' OR evidencia_id IS NOT NULL",
            name=op.f("ck_beneficio_cuantias_cuantia_con_evidencia"),
        ),
        sa.CheckConstraint(
            "tipo IN ('FIJO', 'FORMULA', 'ESPECIE', 'NO_INFORMADO')",
            name=op.f("ck_beneficio_cuantias_tipo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_version_id"],
            ["beneficio_versiones.registro_version_id"],
            name=op.f("fk_beneficio_cuantias_beneficio_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_beneficio_cuantias_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beneficio_cuantias")),
    )
    op.create_index(
        op.f("ix_beneficio_cuantias_beneficio_version_id"),
        "beneficio_cuantias",
        ["beneficio_version_id"],
        unique=False,
    )
    op.create_table(
        "calendario_excepciones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("calendario_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("es_habil", sa.Boolean(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["calendario_id"],
            ["calendarios.id"],
            name=op.f("fk_calendario_excepciones_calendario_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_calendario_excepciones_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendario_excepciones")),
        sa.UniqueConstraint("calendario_id", "fecha", name="uq_calendario_excepciones_fecha"),
    )
    op.create_index(
        op.f("ix_calendario_excepciones_calendario_id"),
        "calendario_excepciones",
        ["calendario_id"],
        unique=False,
    )
    op.create_table(
        "canales",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("canal_id", sa.UUID(), nullable=False),
        sa.Column("organismo_id", sa.UUID(), nullable=False),
        sa.Column("punto_id", sa.UUID(), nullable=True),
        sa.Column("tramite_id", sa.UUID(), nullable=True),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("valor_crudo", sa.Text(), nullable=False),
        sa.Column("valor_normalizado", sa.Text(), nullable=True),
        sa.Column("horario", sa.Text(), nullable=True),
        sa.Column("publico", sa.Text(), nullable=True),
        sa.Column("requiere_autenticacion", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "tipo <> 'EMAIL' OR valor_normalizado IS NULL OR valor_normalizado LIKE '%%@%%'",
            name=op.f("ck_canales_email_normalizado_plausible"),
        ),
        sa.CheckConstraint(
            "tipo <> 'PRESENCIAL' OR punto_id IS NOT NULL",
            name=op.f("ck_canales_presencial_con_punto"),
        ),
        sa.CheckConstraint(
            "tipo IN ('PRESENCIAL', 'TELEFONO', 'WHATSAPP', 'EMAIL', 'WEB', 'FORMULARIO_WEB', 'REDES_SOCIALES', 'CORREO_POSTAL')",
            name=op.f("ck_canales_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "length(btrim(valor_crudo)) > 0", name=op.f("ck_canales_valor_crudo_no_vacio")
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_canales_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organismo_id"],
            ["organismos.id"],
            name=op.f("fk_canales_organismo_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["punto_id"],
            ["puntos_atencion.id"],
            name=op.f("fk_canales_punto_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_canales_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tramite_id"], ["tramites.id"], name=op.f("fk_canales_tramite_id"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_canales")),
    )
    op.create_index(op.f("ix_canales_canal_id"), "canales", ["canal_id"], unique=False)
    op.create_index(op.f("ix_canales_organismo_id"), "canales", ["organismo_id"], unique=False)
    op.create_index(op.f("ix_canales_punto_id"), "canales", ["punto_id"], unique=False)
    op.create_index(op.f("ix_canales_tramite_id"), "canales", ["tramite_id"], unique=False)
    op.create_table(
        "equivalencias_unidades",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("origen_unidad_id", sa.UUID(), nullable=False),
        sa.Column("destino_unidad_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado_revision", sa.String(length=16), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')",
            name=op.f("ck_equivalencias_unidades_estado_revision_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo IN ('RENUMERACION', 'SUSTITUCION', 'DIVISION', 'FUSION', 'INCORPORACION')",
            name=op.f("ck_equivalencias_unidades_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "origen_unidad_id <> destino_unidad_id",
            name=op.f("ck_equivalencias_unidades_origen_distinto_destino"),
        ),
        sa.ForeignKeyConstraint(
            ["destino_unidad_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_equivalencias_unidades_destino_unidad_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_equivalencias_unidades_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origen_unidad_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_equivalencias_unidades_origen_unidad_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_equivalencias_unidades")),
        sa.UniqueConstraint(
            "origen_unidad_id", "destino_unidad_id", "tipo", name="uq_equivalencias_par_tipo"
        ),
    )
    op.create_index(
        op.f("ix_equivalencias_unidades_destino_unidad_id"),
        "equivalencias_unidades",
        ["destino_unidad_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_equivalencias_unidades_origen_unidad_id"),
        "equivalencias_unidades",
        ["origen_unidad_id"],
        unique=False,
    )
    op.create_table(
        "fuentes_candidatas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id_origen", sa.String(length=16), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("relacion", sa.Text(), nullable=True),
        sa.Column("tipo_esperado", sa.String(length=32), nullable=True),
        sa.Column("estado", sa.String(length=32), nullable=False),
        sa.Column("prioridad", sa.String(length=4), nullable=True),
        sa.Column("alias_detectado", sa.Text(), nullable=True),
        sa.Column(
            "descubierta_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado IN ('NUEVA', 'EN_EVALUACION', 'PROMOVIDA', 'DESCARTADA', 'DUPLICADA')",
            name=op.f("ck_fuentes_candidatas_estado_vocabulario"),
        ),
        sa.CheckConstraint(
            "prioridad IS NULL OR prioridad IN ('P0', 'P1', 'P2', 'P3')",
            name=op.f("ck_fuentes_candidatas_prioridad_vocabulario"),
        ),
        sa.CheckConstraint(
            "url ~ '^https?://'", name=op.f("ck_fuentes_candidatas_url_http_concreta")
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_fuentes_candidatas_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id_origen"],
            ["fuentes.source_id"],
            name=op.f("fk_fuentes_candidatas_source_id_origen"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuentes_candidatas")),
        sa.UniqueConstraint("source_id_origen", "url", name="uq_fuentes_candidatas_origen_url"),
    )
    op.create_index(
        op.f("ix_fuentes_candidatas_evidencia_id"),
        "fuentes_candidatas",
        ["evidencia_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fuentes_candidatas_source_id_origen"),
        "fuentes_candidatas",
        ["source_id_origen"],
        unique=False,
    )
    op.create_table(
        "incidencias_revision",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("registro_version_id", sa.UUID(), nullable=True),
        sa.Column("source_id", sa.String(length=16), nullable=True),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("severidad", sa.String(length=16), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("candidatos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False),
        sa.Column("responsable_rol", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("decidido_por", sa.Text(), nullable=True),
        sa.Column("fundamento_evidencia_id", sa.UUID(), nullable=True),
        sa.Column("resuelta_en", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado <> 'RESUELTA' OR (decision IS NOT NULL AND decidido_por IS NOT NULL AND resuelta_en IS NOT NULL)",
            name=op.f("ck_incidencias_revision_resuelta_con_decision_y_actor"),
        ),
        sa.CheckConstraint(
            "estado IN ('ABIERTA', 'EN_REVISION', 'RESUELTA', 'DIFERIDA')",
            name=op.f("ck_incidencias_revision_estado_vocabulario"),
        ),
        sa.CheckConstraint(
            "severidad IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')",
            name=op.f("ck_incidencias_revision_severidad_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo IN ('CONFLICTO_DE_FUENTES', 'IDENTIDAD_AMBIGUA', 'DISCREPANCIA_NUMERACION', 'VIGENCIA_INDETERMINADA', 'COBERTURA_EXTRACCION', 'ACCESO_BLOQUEADO', 'CAMBIO_DE_ESQUEMA', 'DATO_FALTANTE_CRITICO')",
            name=op.f("ck_incidencias_revision_tipo_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["fundamento_evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_incidencias_revision_fundamento_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_incidencias_revision_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["fuentes.source_id"],
            name=op.f("fk_incidencias_revision_source_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidencias_revision")),
    )
    op.create_index(
        "ix_incidencias_revision_estado_severidad",
        "incidencias_revision",
        ["estado", "severidad"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incidencias_revision_registro_version_id"),
        "incidencias_revision",
        ["registro_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incidencias_revision_source_id"),
        "incidencias_revision",
        ["source_id"],
        unique=False,
    )
    op.create_table(
        "norma_versiones",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("norma_id", sa.UUID(), nullable=False),
        sa.Column("doc_version_id", sa.UUID(), nullable=False),
        sa.Column("tipo_version", sa.String(length=32), nullable=False),
        sa.Column("estado_legal_declarado", sa.String(length=32), nullable=True),
        sa.Column(
            "estado_legal_validado",
            sa.String(length=32),
            server_default=sa.text("'NO_DETERMINADA'"),
            nullable=False,
        ),
        sa.Column("fundamento_estado_evidencia_id", sa.UUID(), nullable=True),
        sa.Column("fecha_consolidacion", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "estado_legal_declarado IS NULL OR estado_legal_declarado IN ('VIGENTE', 'VIGENCIA_PARCIAL', 'CONDICIONADA', 'NO_VIGENTE', 'NO_DETERMINADA')",
            name=op.f("ck_norma_versiones_estado_legal_declarado_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado_legal_validado = 'NO_DETERMINADA' OR fundamento_estado_evidencia_id IS NOT NULL",
            name=op.f("ck_norma_versiones_estado_validado_con_fundamento"),
        ),
        sa.CheckConstraint(
            "estado_legal_validado IN ('VIGENTE', 'VIGENCIA_PARCIAL', 'CONDICIONADA', 'NO_VIGENTE', 'NO_DETERMINADA')",
            name=op.f("ck_norma_versiones_estado_legal_validado_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo_version <> 'CONSOLIDADO' OR fecha_consolidacion IS NOT NULL",
            name=op.f("ck_norma_versiones_consolidado_con_fecha"),
        ),
        sa.CheckConstraint(
            "tipo_version IN ('ORIGINAL', 'ACTUALIZADO', 'CONSOLIDADO', 'NO_DETERMINADO')",
            name=op.f("ck_norma_versiones_tipo_version_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["doc_version_id"],
            ["documento_versiones.id"],
            name=op.f("fk_norma_versiones_doc_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fundamento_estado_evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_norma_versiones_fundamento_estado_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_id"],
            ["normas.id"],
            name=op.f("fk_norma_versiones_norma_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_norma_versiones_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_norma_versiones")),
    )
    op.create_index(
        op.f("ix_norma_versiones_doc_version_id"),
        "norma_versiones",
        ["doc_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_norma_versiones_norma_id"), "norma_versiones", ["norma_id"], unique=False
    )
    op.create_index(
        "ix_norma_versiones_norma_tipo",
        "norma_versiones",
        ["norma_id", "tipo_version"],
        unique=False,
    )
    op.create_table(
        "parametro_valores",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("hecho_id", sa.UUID(), nullable=False),
        sa.Column("parametro_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("unidad", sa.Text(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=True),
        sa.Column("periodo", sa.Date(), nullable=True),
        sa.Column("territorio_id", sa.String(length=32), nullable=True),
        sa.Column("segmento", sa.Text(), nullable=True),
        sa.Column("dimensiones", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "dimensiones_hash",
            sa.Text(),
            sa.Computed("md5(coalesce(dimensiones, '{}'::jsonb)::text)", persisted=True),
            nullable=False,
        ),
        sa.Column("rango_aplicacion", postgresql.DATERANGE(), nullable=True),
        sa.Column("publicable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        postgresql.ExcludeConstraint(
            (sa.column("parametro_id"), "="),
            (sa.text("coalesce(territorio_id, '')"), "="),
            (sa.text("coalesce(segmento, '')"), "="),
            (sa.column("dimensiones_hash"), "="),
            (sa.column("rango_aplicacion"), "&&"),
            where=sa.text("publicable"),
            using="gist",
            name="parametro_valores_sin_solapamiento",
        ),
        sa.CheckConstraint(
            "moneda IS NULL OR moneda ~ '^[A-Z]{3}$'",
            name=op.f("ck_parametro_valores_moneda_iso4217"),
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_parametro_valores_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parametro_id"],
            ["parametros.id"],
            name=op.f("fk_parametro_valores_parametro_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_parametro_valores_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["territorio_id"],
            ["jurisdicciones.id"],
            name=op.f("fk_parametro_valores_territorio_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_parametro_valores")),
    )
    op.create_index(
        op.f("ix_parametro_valores_hecho_id"), "parametro_valores", ["hecho_id"], unique=False
    )
    op.create_index(
        op.f("ix_parametro_valores_parametro_id"),
        "parametro_valores",
        ["parametro_id"],
        unique=False,
    )
    op.create_index(
        "ix_parametro_valores_parametro_periodo",
        "parametro_valores",
        ["parametro_id", "periodo"],
        unique=False,
    )
    op.create_index(
        op.f("ix_parametro_valores_territorio_id"),
        "parametro_valores",
        ["territorio_id"],
        unique=False,
    )
    op.create_table(
        "reglas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("beneficio_version_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("categoria", sa.String(length=32), nullable=False),
        sa.Column("texto_literal", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("ast", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ast_schema_version", sa.Text(), nullable=True),
        sa.Column(
            "requiere_revision", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("estado_revision", sa.String(length=16), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "categoria IN ('APLICABILIDAD', 'EXCLUSION', 'EXCEPCION', 'PRIORIDAD', 'SALVAGUARDA', 'REVOCACION', 'SUSPENSION', 'CESE', 'SUBSANACION', 'REHABILITACION', 'COMPATIBILIDAD')",
            name=op.f("ck_reglas_categoria_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')",
            name=op.f("ck_reglas_estado_revision_vocabulario"),
        ),
        sa.CheckConstraint(
            "requiere_revision = true OR (ast IS NOT NULL AND estado_revision IN ('APPROVED','PUBLISHED'))",
            name=op.f("ck_reglas_ejecutable_solo_tras_validacion"),
        ),
        sa.CheckConstraint(
            "ast IS NULL OR ast_schema_version IS NOT NULL",
            name=op.f("ck_reglas_ast_con_version_de_esquema"),
        ),
        sa.CheckConstraint(
            "length(btrim(texto_literal)) > 0", name=op.f("ck_reglas_texto_literal_no_vacio")
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_version_id"],
            ["beneficio_versiones.registro_version_id"],
            name=op.f("fk_reglas_beneficio_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_reglas_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reglas")),
    )
    op.create_index(
        "ix_reglas_beneficio_categoria",
        "reglas",
        ["beneficio_version_id", "categoria"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reglas_beneficio_version_id"), "reglas", ["beneficio_version_id"], unique=False
    )
    op.create_table(
        "relaciones_normativas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("norma_origen_id", sa.UUID(), nullable=False),
        sa.Column("norma_destino_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("unidad_origen_id", sa.UUID(), nullable=True),
        sa.Column("unidad_destino_id", sa.UUID(), nullable=True),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("efecto_desde", sa.Date(), nullable=True),
        sa.Column("efecto_hasta", sa.Date(), nullable=True),
        sa.Column("condicion", sa.Text(), nullable=True),
        sa.Column("estado_revision", sa.String(length=16), nullable=False),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')",
            name=op.f("ck_relaciones_normativas_estado_revision_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo IN ('CITA', 'MODIFICA', 'SUSTITUYE', 'INCORPORA', 'DEROGA', 'ABROGA', 'RESTABLECE', 'REGLAMENTA', 'COMPLEMENTA', 'CONSOLIDA', 'PRORROGA', 'SUSPENDE', 'TRANSITORIA')",
            name=op.f("ck_relaciones_normativas_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "efecto_hasta IS NULL OR efecto_desde IS NULL OR efecto_hasta >= efecto_desde",
            name=op.f("ck_relaciones_normativas_efecto_ordenado"),
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_relaciones_normativas_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_destino_id"],
            ["normas.id"],
            name=op.f("fk_relaciones_normativas_norma_destino_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_origen_id"],
            ["normas.id"],
            name=op.f("fk_relaciones_normativas_norma_origen_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unidad_destino_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_relaciones_normativas_unidad_destino_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unidad_origen_id"],
            ["unidades_documentales.id"],
            name=op.f("fk_relaciones_normativas_unidad_origen_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relaciones_normativas")),
        sa.UniqueConstraint(
            "norma_origen_id",
            "norma_destino_id",
            "tipo",
            "unidad_origen_id",
            "unidad_destino_id",
            name="uq_relaciones_normativas_arista",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_relaciones_normativas_destino_tipo",
        "relaciones_normativas",
        ["norma_destino_id", "tipo"],
        unique=False,
    )
    op.create_index(
        op.f("ix_relaciones_normativas_norma_destino_id"),
        "relaciones_normativas",
        ["norma_destino_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_relaciones_normativas_norma_origen_id"),
        "relaciones_normativas",
        ["norma_origen_id"],
        unique=False,
    )
    op.create_index(
        "ix_relaciones_normativas_origen_tipo",
        "relaciones_normativas",
        ["norma_origen_id", "tipo"],
        unique=False,
    )
    op.create_table(
        "beneficio_normas",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("beneficio_version_id", sa.UUID(), nullable=False),
        sa.Column("norma_version_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("rol", sa.String(length=32), nullable=False),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rol IN ('CREA', 'REGLAMENTA', 'FINANCIA', 'MODIFICA', 'INTERPRETA', 'APLICA')",
            name=op.f("ck_beneficio_normas_rol_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_version_id"],
            ["beneficio_versiones.registro_version_id"],
            name=op.f("fk_beneficio_normas_beneficio_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_beneficio_normas_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_version_id"],
            ["norma_versiones.registro_version_id"],
            name=op.f("fk_beneficio_normas_norma_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beneficio_normas")),
        sa.UniqueConstraint(
            "beneficio_version_id", "norma_version_id", "rol", name="uq_beneficio_normas_rol"
        ),
    )
    op.create_index(
        op.f("ix_beneficio_normas_beneficio_version_id"),
        "beneficio_normas",
        ["beneficio_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beneficio_normas_norma_version_id"),
        "beneficio_normas",
        ["norma_version_id"],
        unique=False,
    )
    op.create_table(
        "beneficio_poblaciones",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("beneficio_version_id", sa.UUID(), nullable=False),
        sa.Column("poblacion_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("rol_persona", sa.String(length=32), nullable=False),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("regla_id", sa.UUID(), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rol_persona IN ('TITULAR', 'CAUSANTE', 'SOLICITANTE', 'REPRESENTANTE', 'CONVIVIENTE', 'GRUPO_FAMILIAR')",
            name=op.f("ck_beneficio_poblaciones_rol_persona_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_version_id"],
            ["beneficio_versiones.registro_version_id"],
            name=op.f("fk_beneficio_poblaciones_beneficio_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_beneficio_poblaciones_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["poblacion_id"],
            ["poblaciones.id"],
            name=op.f("fk_beneficio_poblaciones_poblacion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regla_id"],
            ["reglas.id"],
            name=op.f("fk_beneficio_poblaciones_regla_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beneficio_poblaciones")),
        sa.UniqueConstraint(
            "beneficio_version_id",
            "poblacion_id",
            "rol_persona",
            name="uq_beneficio_poblaciones_rol",
        ),
    )
    op.create_index(
        op.f("ix_beneficio_poblaciones_beneficio_version_id"),
        "beneficio_poblaciones",
        ["beneficio_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_beneficio_poblaciones_poblacion_id"),
        "beneficio_poblaciones",
        ["poblacion_id"],
        unique=False,
    )
    op.create_table(
        "cuantia_parametros",
        sa.Column("cuantia_id", sa.UUID(), nullable=False),
        sa.Column("parametro_id", sa.UUID(), nullable=False),
        sa.Column("rol", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["cuantia_id"],
            ["beneficio_cuantias.id"],
            name=op.f("fk_cuantia_parametros_cuantia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parametro_id"],
            ["parametros.id"],
            name=op.f("fk_cuantia_parametros_parametro_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "cuantia_id", "parametro_id", "rol", name=op.f("pk_cuantia_parametros")
        ),
    )
    op.create_index(
        op.f("ix_cuantia_parametros_parametro_id"),
        "cuantia_parametros",
        ["parametro_id"],
        unique=False,
    )
    op.create_table(
        "derivacion_insumos",
        sa.Column("derivacion_id", sa.UUID(), nullable=False),
        sa.Column("afirmacion_id", sa.UUID(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["afirmacion_id"],
            ["afirmaciones.id"],
            name=op.f("fk_derivacion_insumos_afirmacion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["derivacion_id"],
            ["derivaciones.id"],
            name=op.f("fk_derivacion_insumos_derivacion_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "derivacion_id", "afirmacion_id", "rol", name=op.f("pk_derivacion_insumos")
        ),
    )
    op.create_index(
        op.f("ix_derivacion_insumos_afirmacion_id"),
        "derivacion_insumos",
        ["afirmacion_id"],
        unique=False,
    )
    op.create_table(
        "evaluaciones_completitud",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("norma_version_id", sa.UUID(), nullable=False),
        sa.Column("beneficio_version_id", sa.UUID(), nullable=True),
        sa.Column("campo_solicitado", sa.String(length=40), nullable=False),
        sa.Column("estado", sa.String(length=40), nullable=False),
        sa.Column("fuentes_revisadas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("revisor_id", sa.Text(), nullable=True),
        sa.Column(
            "evaluado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "campo_solicitado IN ('poblacion_destinataria', 'criterios_aplicabilidad', 'plazos', 'criterios_revocacion', 'interdependencias', 'beneficio_otorgado', 'no_descartar')",
            name=op.f("ck_evaluaciones_completitud_campo_solicitado_vocabulario"),
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'INFORMADO', 'NO_INFORMADO_EN_FUENTES_REVISADAS', 'NO_APLICA_JUSTIFICADO', 'EN_CONFLICTO')",
            name=op.f("ck_evaluaciones_completitud_estado_vocabulario"),
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_version_id"],
            ["beneficio_versiones.registro_version_id"],
            name=op.f("fk_evaluaciones_completitud_beneficio_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_version_id"],
            ["norma_versiones.registro_version_id"],
            name=op.f("fk_evaluaciones_completitud_norma_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluaciones_completitud")),
    )
    op.create_index(
        op.f("ix_evaluaciones_completitud_beneficio_version_id"),
        "evaluaciones_completitud",
        ["beneficio_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluaciones_completitud_norma_version_id"),
        "evaluaciones_completitud",
        ["norma_version_id"],
        unique=False,
    )
    op.create_index(
        "uq_evaluaciones_completitud_ficha_campo",
        "evaluaciones_completitud",
        ["norma_version_id", "beneficio_version_id", "campo_solicitado"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_table(
        "plazos",
        sa.Column("registro_version_id", sa.UUID(), nullable=False),
        sa.Column("plazo_id", sa.UUID(), nullable=False),
        sa.Column("beneficio_version_id", sa.UUID(), nullable=True),
        sa.Column("tramite_version_id", sa.UUID(), nullable=True),
        sa.Column("norma_version_id", sa.UUID(), nullable=True),
        sa.Column("calendario_id", sa.UUID(), nullable=True),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=True),
        sa.Column("fin", sa.Date(), nullable=True),
        sa.Column("hora_cierre", sa.Time(), nullable=True),
        sa.Column(
            "zona_horaria",
            sa.Text(),
            server_default=sa.text("'America/Argentina/Buenos_Aires'"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Integer(), nullable=True),
        sa.Column("unidad", sa.Text(), nullable=True),
        sa.Column("tipo_dia", sa.String(length=32), nullable=False),
        sa.Column("evento_inicio", sa.Text(), nullable=True),
        sa.Column("regla_computo", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ciclo", sa.Integer(), nullable=True),
        sa.Column("convocatoria", sa.Text(), nullable=True),
        sa.Column("inclusivo_desde", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("inclusivo_hasta", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('VIGENCIA_JURIDICA', 'CONVOCATORIA', 'DURACION_BENEFICIO', 'RENOVACION', 'PRESENTACION_DOCUMENTAL', 'RESPUESTA_ORGANISMO', 'SUBSANACION', 'RECURSO', 'FECHA_PAGO')",
            name=op.f("ck_plazos_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo_dia IN ('CORRIDO', 'HABIL_ADMINISTRATIVO', 'HABIL_JUDICIAL', 'NO_INFORMADO')",
            name=op.f("ck_plazos_tipo_dia_vocabulario"),
        ),
        sa.CheckConstraint(
            "tipo_dia NOT IN ('HABIL_ADMINISTRATIVO','HABIL_JUDICIAL') OR calendario_id IS NOT NULL",
            name=op.f("ck_plazos_habil_exige_calendario"),
        ),
        sa.CheckConstraint(
            "(CASE WHEN beneficio_version_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN tramite_version_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN norma_version_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name=op.f("ck_plazos_un_solo_propietario_principal"),
        ),
        sa.CheckConstraint(
            "(inicio IS NOT NULL OR fin IS NOT NULL) <> (cantidad IS NOT NULL)",
            name=op.f("ck_plazos_fechado_o_relativo_no_ambos"),
        ),
        sa.CheckConstraint(
            "cantidad IS NULL OR (cantidad >= 0 AND unidad IS NOT NULL AND evento_inicio IS NOT NULL)",
            name=op.f("ck_plazos_relativo_con_unidad_y_evento"),
        ),
        sa.CheckConstraint("ciclo IS NULL OR ciclo >= 1", name=op.f("ck_plazos_ciclo_positivo")),
        sa.CheckConstraint(
            "fin IS NULL OR inicio IS NULL OR fin >= inicio", name=op.f("ck_plazos_fin_tras_inicio")
        ),
        sa.ForeignKeyConstraint(
            ["beneficio_version_id"],
            ["beneficio_versiones.registro_version_id"],
            name=op.f("fk_plazos_beneficio_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calendario_id"],
            ["calendarios.id"],
            name=op.f("fk_plazos_calendario_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_plazos_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_version_id"],
            ["norma_versiones.registro_version_id"],
            name=op.f("fk_plazos_norma_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["registro_version_id"],
            ["registro_versiones.id"],
            name=op.f("fk_plazos_registro_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tramite_version_id"],
            ["tramite_versiones.registro_version_id"],
            name=op.f("fk_plazos_tramite_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("registro_version_id", name=op.f("pk_plazos")),
    )
    op.create_index(
        op.f("ix_plazos_beneficio_version_id"), "plazos", ["beneficio_version_id"], unique=False
    )
    op.create_index("ix_plazos_convocatoria", "plazos", ["convocatoria", "ciclo"], unique=False)
    op.create_index(
        op.f("ix_plazos_norma_version_id"), "plazos", ["norma_version_id"], unique=False
    )
    op.create_index(op.f("ix_plazos_plazo_id"), "plazos", ["plazo_id"], unique=False)
    op.create_index("ix_plazos_tipo_inicio_fin", "plazos", ["tipo", "inicio", "fin"], unique=False)
    op.create_index(
        op.f("ix_plazos_tramite_version_id"), "plazos", ["tramite_version_id"], unique=False
    )
    op.create_table(
        "referencias_pendientes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("norma_origen_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("texto_cita", sa.Text(), nullable=False),
        sa.Column("identidad_candidata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False),
        sa.Column("responsable_rol", sa.Text(), nullable=True),
        sa.Column("relacion_resultante_id", sa.UUID(), nullable=True),
        sa.Column("resuelta_en", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "creado_en",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado <> 'RESUELTA' OR (relacion_resultante_id IS NOT NULL AND resuelta_en IS NOT NULL)",
            name=op.f("ck_referencias_pendientes_resuelta_con_relacion"),
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'RESUELTA', 'IRRESOLUBLE')",
            name=op.f("ck_referencias_pendientes_estado_vocabulario"),
        ),
        sa.CheckConstraint(
            "length(btrim(texto_cita)) > 0",
            name=op.f("ck_referencias_pendientes_texto_cita_no_vacio"),
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_referencias_pendientes_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["norma_origen_id"],
            ["normas.id"],
            name=op.f("fk_referencias_pendientes_norma_origen_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["relacion_resultante_id"],
            ["relaciones_normativas.id"],
            name=op.f("fk_referencias_pendientes_relacion_resultante_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referencias_pendientes")),
    )
    op.create_index(
        "ix_referencias_pendientes_estado", "referencias_pendientes", ["estado"], unique=False
    )
    op.create_index(
        op.f("ix_referencias_pendientes_norma_origen_id"),
        "referencias_pendientes",
        ["norma_origen_id"],
        unique=False,
    )
    op.create_table(
        "regla_dependencias",
        sa.Column("regla_id", sa.UUID(), nullable=False),
        sa.Column("regla_referida_id", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('EXCEPCION_DE', 'PRECEDE_A', 'REQUIERE', 'INCOMPATIBLE_CON')",
            name=op.f("ck_regla_dependencias_tipo_vocabulario"),
        ),
        sa.CheckConstraint(
            "regla_id <> regla_referida_id", name=op.f("ck_regla_dependencias_sin_autodependencia")
        ),
        sa.ForeignKeyConstraint(
            ["regla_id"],
            ["reglas.id"],
            name=op.f("fk_regla_dependencias_regla_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regla_referida_id"],
            ["reglas.id"],
            name=op.f("fk_regla_dependencias_regla_referida_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "regla_id", "regla_referida_id", "tipo", name=op.f("pk_regla_dependencias")
        ),
    )
    op.create_index(
        op.f("ix_regla_dependencias_regla_referida_id"),
        "regla_dependencias",
        ["regla_referida_id"],
        unique=False,
    )
    op.create_table(
        "regla_parametros",
        sa.Column("regla_id", sa.UUID(), nullable=False),
        sa.Column("parametro_id", sa.UUID(), nullable=False),
        sa.Column("rol", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["parametro_id"],
            ["parametros.id"],
            name=op.f("fk_regla_parametros_parametro_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regla_id"],
            ["reglas.id"],
            name=op.f("fk_regla_parametros_regla_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "regla_id", "parametro_id", "rol", name=op.f("pk_regla_parametros")
        ),
    )
    op.create_index(
        op.f("ix_regla_parametros_parametro_id"), "regla_parametros", ["parametro_id"], unique=False
    )
    op.create_table(
        "tramite_pasos",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tramite_version_id", sa.UUID(), nullable=False),
        sa.Column("evidencia_id", sa.UUID(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("canal_id", sa.UUID(), nullable=True),
        sa.Column("documentacion", sa.Text(), nullable=True),
        sa.Column("alternativas", sa.Text(), nullable=True),
        sa.CheckConstraint("orden >= 1", name=op.f("ck_tramite_pasos_orden_positivo")),
        sa.ForeignKeyConstraint(
            ["canal_id"],
            ["canales.registro_version_id"],
            name=op.f("fk_tramite_pasos_canal_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_id"],
            ["evidencias.id"],
            name=op.f("fk_tramite_pasos_evidencia_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tramite_version_id"],
            ["tramite_versiones.registro_version_id"],
            name=op.f("fk_tramite_pasos_tramite_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tramite_pasos")),
        sa.UniqueConstraint("tramite_version_id", "orden", name="uq_tramite_pasos_orden"),
    )
    op.create_index(
        op.f("ix_tramite_pasos_tramite_version_id"),
        "tramite_pasos",
        ["tramite_version_id"],
        unique=False,
    )
    op.create_table(
        "completitud_afirmaciones",
        sa.Column("evaluacion_id", sa.UUID(), nullable=False),
        sa.Column("afirmacion_id", sa.UUID(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["afirmacion_id"],
            ["afirmaciones.id"],
            name=op.f("fk_completitud_afirmaciones_afirmacion_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evaluacion_id"],
            ["evaluaciones_completitud.id"],
            name=op.f("fk_completitud_afirmaciones_evaluacion_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "evaluacion_id", "afirmacion_id", name=op.f("pk_completitud_afirmaciones")
        ),
    )
    op.create_index(
        op.f("ix_completitud_afirmaciones_afirmacion_id"),
        "completitud_afirmaciones",
        ["afirmacion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_completitud_afirmaciones_afirmacion_id"), table_name="completitud_afirmaciones"
    )
    op.drop_table("completitud_afirmaciones")
    op.drop_index(op.f("ix_tramite_pasos_tramite_version_id"), table_name="tramite_pasos")
    op.drop_table("tramite_pasos")
    op.drop_index(op.f("ix_regla_parametros_parametro_id"), table_name="regla_parametros")
    op.drop_table("regla_parametros")
    op.drop_index(op.f("ix_regla_dependencias_regla_referida_id"), table_name="regla_dependencias")
    op.drop_table("regla_dependencias")
    op.drop_index(
        op.f("ix_referencias_pendientes_norma_origen_id"), table_name="referencias_pendientes"
    )
    op.drop_index("ix_referencias_pendientes_estado", table_name="referencias_pendientes")
    op.drop_table("referencias_pendientes")
    op.drop_index(op.f("ix_plazos_tramite_version_id"), table_name="plazos")
    op.drop_index("ix_plazos_tipo_inicio_fin", table_name="plazos")
    op.drop_index(op.f("ix_plazos_plazo_id"), table_name="plazos")
    op.drop_index(op.f("ix_plazos_norma_version_id"), table_name="plazos")
    op.drop_index("ix_plazos_convocatoria", table_name="plazos")
    op.drop_index(op.f("ix_plazos_beneficio_version_id"), table_name="plazos")
    op.drop_table("plazos")
    op.drop_index(
        "uq_evaluaciones_completitud_ficha_campo",
        table_name="evaluaciones_completitud",
        postgresql_nulls_not_distinct=True,
    )
    op.drop_index(
        op.f("ix_evaluaciones_completitud_norma_version_id"), table_name="evaluaciones_completitud"
    )
    op.drop_index(
        op.f("ix_evaluaciones_completitud_beneficio_version_id"),
        table_name="evaluaciones_completitud",
    )
    op.drop_table("evaluaciones_completitud")
    op.drop_index(op.f("ix_derivacion_insumos_afirmacion_id"), table_name="derivacion_insumos")
    op.drop_table("derivacion_insumos")
    op.drop_index(op.f("ix_cuantia_parametros_parametro_id"), table_name="cuantia_parametros")
    op.drop_table("cuantia_parametros")
    op.drop_index(op.f("ix_beneficio_poblaciones_poblacion_id"), table_name="beneficio_poblaciones")
    op.drop_index(
        op.f("ix_beneficio_poblaciones_beneficio_version_id"), table_name="beneficio_poblaciones"
    )
    op.drop_table("beneficio_poblaciones")
    op.drop_index(op.f("ix_beneficio_normas_norma_version_id"), table_name="beneficio_normas")
    op.drop_index(op.f("ix_beneficio_normas_beneficio_version_id"), table_name="beneficio_normas")
    op.drop_table("beneficio_normas")
    op.drop_index("ix_relaciones_normativas_origen_tipo", table_name="relaciones_normativas")
    op.drop_index(
        op.f("ix_relaciones_normativas_norma_origen_id"), table_name="relaciones_normativas"
    )
    op.drop_index(
        op.f("ix_relaciones_normativas_norma_destino_id"), table_name="relaciones_normativas"
    )
    op.drop_index("ix_relaciones_normativas_destino_tipo", table_name="relaciones_normativas")
    op.drop_table("relaciones_normativas")
    op.drop_index(op.f("ix_reglas_beneficio_version_id"), table_name="reglas")
    op.drop_index("ix_reglas_beneficio_categoria", table_name="reglas")
    op.drop_table("reglas")
    op.drop_index(op.f("ix_parametro_valores_territorio_id"), table_name="parametro_valores")
    op.drop_index("ix_parametro_valores_parametro_periodo", table_name="parametro_valores")
    op.drop_index(op.f("ix_parametro_valores_parametro_id"), table_name="parametro_valores")
    op.drop_index(op.f("ix_parametro_valores_hecho_id"), table_name="parametro_valores")
    op.drop_table("parametro_valores")
    op.drop_index("ix_norma_versiones_norma_tipo", table_name="norma_versiones")
    op.drop_index(op.f("ix_norma_versiones_norma_id"), table_name="norma_versiones")
    op.drop_index(op.f("ix_norma_versiones_doc_version_id"), table_name="norma_versiones")
    op.drop_table("norma_versiones")
    op.drop_index(op.f("ix_incidencias_revision_source_id"), table_name="incidencias_revision")
    op.drop_index(
        op.f("ix_incidencias_revision_registro_version_id"), table_name="incidencias_revision"
    )
    op.drop_index("ix_incidencias_revision_estado_severidad", table_name="incidencias_revision")
    op.drop_table("incidencias_revision")
    op.drop_index(op.f("ix_fuentes_candidatas_source_id_origen"), table_name="fuentes_candidatas")
    op.drop_index(op.f("ix_fuentes_candidatas_evidencia_id"), table_name="fuentes_candidatas")
    op.drop_table("fuentes_candidatas")
    op.drop_index(
        op.f("ix_equivalencias_unidades_origen_unidad_id"), table_name="equivalencias_unidades"
    )
    op.drop_index(
        op.f("ix_equivalencias_unidades_destino_unidad_id"), table_name="equivalencias_unidades"
    )
    op.drop_table("equivalencias_unidades")
    op.drop_index(op.f("ix_canales_tramite_id"), table_name="canales")
    op.drop_index(op.f("ix_canales_punto_id"), table_name="canales")
    op.drop_index(op.f("ix_canales_organismo_id"), table_name="canales")
    op.drop_index(op.f("ix_canales_canal_id"), table_name="canales")
    op.drop_table("canales")
    op.drop_index(
        op.f("ix_calendario_excepciones_calendario_id"), table_name="calendario_excepciones"
    )
    op.drop_table("calendario_excepciones")
    op.drop_index(
        op.f("ix_beneficio_cuantias_beneficio_version_id"), table_name="beneficio_cuantias"
    )
    op.drop_table("beneficio_cuantias")
    op.drop_index("ix_barrios_renabap_provincia_localidad", table_name="barrios_renabap")
    op.drop_index(op.f("ix_barrios_renabap_barrio_id"), table_name="barrios_renabap")
    op.drop_table("barrios_renabap")
    op.drop_index("ix_afirmaciones_version_campo", table_name="afirmaciones")
    op.drop_index(op.f("ix_afirmaciones_source_id"), table_name="afirmaciones")
    op.drop_index(op.f("ix_afirmaciones_registro_version_id"), table_name="afirmaciones")
    op.drop_index(op.f("ix_afirmaciones_evidencia_id"), table_name="afirmaciones")
    op.drop_index("ix_afirmaciones_estado_campo", table_name="afirmaciones")
    op.drop_table("afirmaciones")
    op.drop_index(op.f("ix_evidencias_unidad_id"), table_name="evidencias")
    op.drop_index("ix_evidencias_hash", table_name="evidencias")
    op.drop_index(op.f("ix_evidencias_doc_version_id"), table_name="evidencias")
    op.drop_table("evidencias")
    op.drop_index(op.f("ix_chunks_unidad_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_release_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_registro_version_id"), table_name="chunks")
    op.drop_table("chunks")
    op.drop_index(
        "uq_unidades_documentales_ruta_dispositiva",
        table_name="unidades_documentales",
        postgresql_where=sa.text("rol_contenido = 'DISPOSITIVO'"),
    )
    op.drop_index("ix_unidades_documentales_version_orden", table_name="unidades_documentales")
    op.drop_index(op.f("ix_unidades_documentales_parent_id"), table_name="unidades_documentales")
    op.drop_index(
        op.f("ix_unidades_documentales_doc_version_id"), table_name="unidades_documentales"
    )
    op.drop_table("unidades_documentales")
    op.drop_index(op.f("ix_tramite_versiones_tramite_id"), table_name="tramite_versiones")
    op.drop_index(op.f("ix_tramite_versiones_doc_version_id"), table_name="tramite_versiones")
    op.drop_table("tramite_versiones")
    op.drop_index("ix_documento_versiones_fecha", table_name="documento_versiones")
    op.drop_index(op.f("ix_documento_versiones_documento_id"), table_name="documento_versiones")
    op.drop_index(op.f("ix_documento_versiones_captura_id"), table_name="documento_versiones")
    op.drop_table("documento_versiones")
    op.drop_index(op.f("ix_controles_calidad_registro_version_id"), table_name="controles_calidad")
    op.drop_index("ix_controles_calidad_ejecutado", table_name="controles_calidad")
    op.drop_index(op.f("ix_controles_calidad_corrida_id"), table_name="controles_calidad")
    op.drop_index("ix_controles_calidad_control_resultado", table_name="controles_calidad")
    op.drop_table("controles_calidad")
    op.drop_index("ix_capturas_url_capturado", table_name="capturas")
    op.drop_index(op.f("ix_capturas_source_url_id"), table_name="capturas")
    op.drop_index("ix_capturas_sha256_raw", table_name="capturas")
    op.drop_index(op.f("ix_capturas_corrida_id"), table_name="capturas")
    op.drop_index(op.f("ix_capturas_captura_previa_id"), table_name="capturas")
    op.drop_table("capturas")
    op.drop_index("ix_corridas_ingesta_source_inicio", table_name="corridas_ingesta")
    op.drop_index(op.f("ix_corridas_ingesta_source_id"), table_name="corridas_ingesta")
    op.drop_index(op.f("ix_corridas_ingesta_config_version_id"), table_name="corridas_ingesta")
    op.drop_table("corridas_ingesta")
    op.drop_index(op.f("ix_punto_versiones_punto_id"), table_name="punto_versiones")
    op.drop_index("ix_punto_versiones_localidad", table_name="punto_versiones")
    op.drop_table("punto_versiones")
    op.drop_index(op.f("ix_norma_identificadores_norma_id"), table_name="norma_identificadores")
    op.drop_table("norma_identificadores")
    op.drop_index(op.f("ix_fuente_urls_url_padre_id"), table_name="fuente_urls")
    op.drop_index(op.f("ix_fuente_urls_source_id"), table_name="fuente_urls")
    op.drop_table("fuente_urls")
    op.drop_index(
        op.f("ix_fuente_config_versiones_source_id"), table_name="fuente_config_versiones"
    )
    op.drop_table("fuente_config_versiones")
    op.drop_index(op.f("ix_documentos_source_id"), table_name="documentos")
    op.drop_table("documentos")
    op.drop_index(op.f("ix_calendarios_jurisdiccion_id"), table_name="calendarios")
    op.drop_table("calendarios")
    op.drop_index(op.f("ix_tramites_organismo_id"), table_name="tramites")
    op.drop_index(op.f("ix_tramites_beneficio_id"), table_name="tramites")
    op.drop_table("tramites")
    op.drop_index(op.f("ix_puntos_atencion_organismo_id"), table_name="puntos_atencion")
    op.drop_index("ix_puntos_atencion_nombre", table_name="puntos_atencion")
    op.drop_index(op.f("ix_puntos_atencion_jurisdiccion_id"), table_name="puntos_atencion")
    op.drop_table("puntos_atencion")
    op.drop_index(
        "uq_normas_clave_canonica",
        table_name="normas",
        postgresql_where=sa.text(
            "numero IS NOT NULL AND anio IS NOT NULL AND identidad_incierta = false"
        ),
    )
    op.drop_index("ix_normas_publicacion", table_name="normas")
    op.drop_index(op.f("ix_normas_jurisdiccion_id"), table_name="normas")
    op.drop_index("ix_normas_emisor_tipo_numero_anio", table_name="normas")
    op.drop_index(op.f("ix_normas_emisor_id"), table_name="normas")
    op.drop_table("normas")
    op.drop_index(op.f("ix_fuentes_organismo_id"), table_name="fuentes")
    op.drop_index("ix_fuentes_estado_prioridad", table_name="fuentes")
    op.drop_index(op.f("ix_fuentes_alias_of"), table_name="fuentes")
    op.drop_table("fuentes")
    op.drop_index(op.f("ix_beneficio_versiones_jurisdiccion_id"), table_name="beneficio_versiones")
    op.drop_index(op.f("ix_beneficio_versiones_beneficio_id"), table_name="beneficio_versiones")
    op.drop_index(op.f("ix_beneficio_versiones_autoridad_id"), table_name="beneficio_versiones")
    op.drop_table("beneficio_versiones")
    op.drop_index(
        "uq_registro_versiones_known_abierto",
        table_name="registro_versiones",
        postgresql_where=sa.text("known_hasta IS NULL"),
    )
    op.drop_index("ix_registro_versiones_valid", table_name="registro_versiones")
    op.drop_index(op.f("ix_registro_versiones_release_id"), table_name="registro_versiones")
    op.drop_index("ix_registro_versiones_frescura", table_name="registro_versiones")
    op.drop_index("ix_registro_versiones_estado", table_name="registro_versiones")
    op.drop_index("ix_registro_versiones_entidad", table_name="registro_versiones")
    op.drop_table("registro_versiones")
    op.drop_index(op.f("ix_organismos_jurisdiccion_id"), table_name="organismos")
    op.drop_table("organismos")
    op.drop_index(op.f("ix_eventos_outbox_release_id"), table_name="eventos_outbox")
    op.drop_index(
        "ix_eventos_outbox_pendientes",
        table_name="eventos_outbox",
        postgresql_where=sa.text("entregado_en IS NULL"),
    )
    op.drop_table("eventos_outbox")
    op.drop_index(op.f("ix_consultas_auditadas_release_id"), table_name="consultas_auditadas")
    op.drop_index("ix_consultas_auditadas_ocurrido", table_name="consultas_auditadas")
    op.drop_table("consultas_auditadas")
    op.drop_index("ix_releases_estado_publicado", table_name="releases")
    op.drop_table("releases")
    op.drop_table("poblaciones")
    op.drop_table("parametros")
    op.drop_index(op.f("ix_jurisdicciones_parent_id"), table_name="jurisdicciones")
    op.drop_table("jurisdicciones")
    op.drop_table("derivaciones")
    op.drop_index("ix_beneficios_familia_linea", table_name="beneficios")
    op.drop_table("beneficios")
    op.drop_index("ix_auditoria_eventos_ocurrido", table_name="auditoria_eventos")
    op.drop_index("ix_auditoria_eventos_objeto", table_name="auditoria_eventos")
    op.drop_table("auditoria_eventos")
