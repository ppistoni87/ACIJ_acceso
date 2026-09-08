"""Entorno de Alembic. La URL viene del entorno (rol `migrador`)."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend_normativo.config import get_settings
from backend_normativo.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", str(get_settings().database_url))

target_metadata = Base.metadata

# Objetos que crea y mantiene SQL a mano (migración 0002): índices de búsqueda
# textual en español, funciones, triggers y vistas. Se excluyen de la
# comparación para que `--autogenerate` no proponga borrarlos en cada corrida.
INDICES_GESTIONADOS_POR_SQL = frozenset(
    {
        "ix_unidades_documentales_fts",
        "ix_chunks_fts",
        "ix_normas_titulo_fts",
        "ix_puntos_atencion_nombre_trgm",
    }
)


def include_object(objeto, nombre, tipo, reflejado, comparado_con):
    if tipo == "index" and nombre in INDICES_GESTIONADOS_POR_SQL:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
