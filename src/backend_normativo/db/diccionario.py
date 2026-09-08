"""Diccionario de datos generado desde los modelos.

Un diccionario escrito a mano envejece mal: describe el esquema que había el día
que alguien lo escribió. Este se arma leyendo los modelos, así que una columna
nueva aparece sola y una que se fue deja de figurar. El texto explicativo de
cada tabla es su docstring: la razón por la que existe vive junto a su
definición y no en un documento aparte que nadie actualiza.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from backend_normativo.db import models  # noqa: F401  (registra los modelos)
from backend_normativo.db.base import Base


@dataclass
class ColumnaDescrita:
    nombre: str
    tipo: str
    nulo: bool
    defecto: str | None
    referencia: str | None


@dataclass
class TablaDescrita:
    nombre: str
    proposito: str
    columnas: list[ColumnaDescrita] = field(default_factory=list)
    claves_unicas: list[str] = field(default_factory=list)
    verificaciones: list[str] = field(default_factory=list)
    indices: list[str] = field(default_factory=list)


def construir() -> list[TablaDescrita]:
    tablas: list[TablaDescrita] = []
    for mapeador in sorted(Base.registry.mappers, key=lambda m: m.class_.__tablename__):
        tabla = mapeador.local_table
        descrita = TablaDescrita(
            nombre=tabla.name,
            proposito=textwrap.dedent(mapeador.class_.__doc__ or "").strip(),
        )
        for columna in tabla.columns:
            referencia = None
            if columna.foreign_keys:
                referencia = ", ".join(
                    sorted(str(fk.target_fullname) for fk in columna.foreign_keys)
                )
            defecto = None
            if columna.server_default is not None:
                defecto = str(getattr(columna.server_default, "arg", columna.server_default))
            descrita.columnas.append(
                ColumnaDescrita(
                    nombre=columna.name,
                    tipo=str(columna.type),
                    nulo=columna.nullable,
                    defecto=defecto,
                    referencia=referencia,
                )
            )
        for restriccion in tabla.constraints:
            if isinstance(restriccion, UniqueConstraint):
                descrita.claves_unicas.append(
                    f"{restriccion.name or 'sin nombre'}: "
                    f"({', '.join(c.name for c in restriccion.columns)})"
                )
            elif isinstance(restriccion, CheckConstraint):
                descrita.verificaciones.append(
                    f"{restriccion.name or 'sin nombre'}: {restriccion.sqltext}"
                )
            elif isinstance(restriccion, ForeignKeyConstraint):
                continue
        for indice in sorted(tabla.indexes, key=lambda i: i.name or ""):
            marca = "único" if indice.unique else "índice"
            descrita.indices.append(
                f"{indice.name} ({marca}): "
                f"({', '.join(c.name for c in indice.expressions if hasattr(c, 'name'))})"
            )
        tablas.append(descrita)
    return tablas


def formatear(tablas: list[TablaDescrita]) -> str:
    total_columnas = sum(len(t.columnas) for t in tablas)
    lineas = [
        "# Diccionario de datos",
        "",
        f"**{len(tablas)} tablas** y **{total_columnas} columnas**, generadas desde los modelos",
        "con `bn calidad diccionario`. No se edita a mano: si una columna cambia, se regenera.",
        "",
        "El propósito de cada tabla es el docstring de su modelo. Las verificaciones que",
        "aparecen acá son las que viven en el esquema; los disparadores y funciones que",
        "sostienen las reglas que una restricción no puede expresar están en la migración",
        "`0002_reglas_de_integridad.py`.",
        "",
        "## Índice",
        "",
    ]
    lineas += [f"- [`{t.nombre}`](#{t.nombre.replace('_', '-')})" for t in tablas]

    for tabla in tablas:
        lineas += ["", f"## {tabla.nombre}", ""]
        if tabla.proposito:
            lineas += [tabla.proposito, ""]
        lineas += [
            "| Columna | Tipo | Nulo | Defecto | Referencia |",
            "| --- | --- | --- | --- | --- |",
        ]
        for columna in tabla.columnas:
            lineas.append(
                f"| `{columna.nombre}` | {columna.tipo} | {'sí' if columna.nulo else 'no'} "
                f"| {f'`{columna.defecto}`' if columna.defecto else '—'} "
                f"| {f'`{columna.referencia}`' if columna.referencia else '—'} |"
            )
        for titulo, elementos in (
            ("Claves únicas", tabla.claves_unicas),
            ("Verificaciones", tabla.verificaciones),
            ("Índices", tabla.indices),
        ):
            if elementos:
                lineas += ["", f"**{titulo}**", ""]
                lineas += [f"- `{e}`" for e in elementos]
    return "\n".join(lineas)
