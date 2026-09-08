"""Motores y sesiones. Un motor por rol: la API nunca usa el del ingestor."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend_normativo.config import get_settings


@lru_cache(maxsize=8)
def crear_engine(
    url: str,
    *,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
) -> Engine:
    """El motor con su pool declarado.

    El tamaño no se deja al default de SQLAlchemy —cinco conexiones más diez de
    desborde— porque nadie lo había elegido. Conviene saber que agrandarlo no
    sube el caudal de la API: midiendo por separado, el motor sostiene más de mil
    consultas por segundo con dieciséis hilos mientras la API se queda en unas
    sesenta y seis. El cuello está en el proceso que serializa las respuestas, no
    en las conexiones, así que escalar esto es agregar procesos.
    """
    return create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        future=True,
    )


def engine_migrador() -> Engine:
    s = get_settings()
    return crear_engine(str(s.database_url), echo=s.sql_echo, **_pool(s))


def engine_ingesta() -> Engine:
    s = get_settings()
    return crear_engine(s.url_ingesta, echo=s.sql_echo, **_pool(s))


def engine_api() -> Engine:
    s = get_settings()
    return crear_engine(s.url_api, echo=s.sql_echo, **_pool(s))


def _pool(s) -> dict[str, int]:
    return {
        "pool_size": s.pool_size,
        "max_overflow": s.pool_max_overflow,
        "pool_timeout": s.pool_timeout_s,
    }


@contextmanager
def sesion(engine: Engine | None = None) -> Iterator[Session]:
    """Sesión transaccional: confirma al salir sin error, revierte con error."""
    factory = sessionmaker(bind=engine or engine_migrador(), expire_on_commit=False)
    with factory() as s:
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
