"""El parámetro se resuelve contra el corte, y la consulta tiene que ser válida.

`(:r::uuid IS NULL OR rv.release_id = :r)` parece correcto y no lo es: el lector
de `text()` de SQLAlchemy no toma un nombre de parámetro seguido de otro dos
puntos, así que deja `:r::uuid` sin sustituir y PostgreSQL recibe un error de
sintaxis. El segundo `:r` de la misma línea sí se sustituye, que es lo que hace
que leyendo el código no se vea.

No lo agarró ninguna prueba porque la rama sólo corre cuando una regla necesita
el valor de un parámetro, y para eso hace falta un beneficio publicado con
reglas ejecutables. La primera vez que hubo uno, la evaluación contestó 500.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import uuid

import pytest
from sqlalchemy import Connection

pytestmark = pytest.mark.integracion


def test_resolver_un_parametro_no_rompe_la_consulta(conexion: Connection) -> None:
    """Sin corte y con corte: las dos ramas del filtro tienen que ejecutar."""
    from backend_normativo.api.routers.evaluaciones import _resolver_parametro

    for release_id in (None, uuid.uuid4()):
        resolver = _resolver_parametro(conexion, release_id)
        # No hay valores cargados: lo que importa es que la consulta corra.
        assert resolver("CUALQUIER.PARAMETRO", dt.date(2026, 9, 12)) is None


def test_ningun_sql_del_proyecto_pega_un_cast_al_parametro() -> None:
    """El defecto tiene una firma buscable, y buscarla cuesta nada.

    `:nombre::tipo` no se sustituye; `CAST(:nombre AS tipo)` sí. Es la forma que
    usa el resto del proyecto y la única que no depende de dónde caiga el
    parámetro en la consulta.
    """
    raiz = pathlib.Path(__file__).resolve().parents[2] / "src" / "backend_normativo"
    patron = re.compile(r":[a-z_][a-z_0-9]*::")
    culpables = [
        f"{archivo.relative_to(raiz)}:{numero}"
        for archivo in raiz.rglob("*.py")
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1)
        if patron.search(linea) and not linea.lstrip().startswith("#")
    ]
    assert not culpables, (
        "SQLAlchemy deja sin sustituir un parámetro seguido de `::`. "
        f"Usar CAST(:nombre AS tipo) en: {culpables}"
    )
