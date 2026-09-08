"""Motores y sesiones. Un motor por rol: la API nunca usa el del ingestor."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend_normativo.config import get_settings


@lru_cache(maxsize=8)
def crear_engine(url: str, *, echo: bool = False) -> Engine:
    return create_engine(url, echo=echo, pool_pre_ping=True, future=True)


def engine_migrador() -> Engine:
    s = get_settings()
    return crear_engine(str(s.database_url), echo=s.sql_echo)


def engine_ingesta() -> Engine:
    s = get_settings()
    return crear_engine(s.url_ingesta, echo=s.sql_echo)


def engine_api() -> Engine:
    s = get_settings()
    return crear_engine(s.url_api, echo=s.sql_echo)


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
