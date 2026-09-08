"""Base declarativa, convenciones de nombres y utilidades de esquema."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, MetaData, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

from backend_normativo.db.vocabularios import valores

# Nombres deterministas: una restricción se puede referenciar desde una
# migración o un mensaje de error sin depender del orden de creación.
CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}

metadata_obj = MetaData(naming_convention=CONVENCION_NOMBRES)


class Base(DeclarativeBase):
    metadata = metadata_obj


def pk_uuid() -> Any:
    """PK interna UUID generada en la base (`gen_random_uuid`, pgcrypto/PG13+)."""
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def ts_creacion() -> Any:
    return mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


def check_vocabulario(
    columna: str, enum_cls: type[StrEnum], *, nullable: bool = False
) -> CheckConstraint:
    """`CHECK` de pertenencia a un vocabulario controlado.

    Se usa `CHECK` en lugar de `ENUM` de PostgreSQL: ampliar un vocabulario debe
    ser una migración revisable y no un `ALTER TYPE` que no admite rollback
    transaccional en versiones soportadas.
    """
    lista = ", ".join(f"'{v}'" for v in valores(enum_cls))
    condicion = f"{columna} IN ({lista})"
    if nullable:
        condicion = f"{columna} IS NULL OR {condicion}"
    return CheckConstraint(condicion, name=f"{columna}_vocabulario")


__all__ = [
    "JSONB",
    "TIMESTAMP",
    "UUID",
    "Base",
    "check_vocabulario",
    "datetime",
    "metadata_obj",
    "pk_uuid",
    "ts_creacion",
]
