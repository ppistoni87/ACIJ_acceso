#!/usr/bin/env python3
"""Compara el esquema aplicado en la base gestionada contra el que el código espera.

Por qué existe. El acta de Neon declaraba una cabeza de migraciones escrita a
mano. Se aplicaron tres migraciones más y el número del acta quedó viejo; quien
lo leyó después —incluido un informe de estado— dio por pendiente un trabajo que
ya estaba hecho. Un número que una persona escribe en un documento envejece sin
avisar: el único que no envejece es el que se le pregunta a la base.

Así que el acta ya no declara la cabeza. Declara este comando, y este comando
falla si la base y el código no coinciden.

Uso:
    NEON_DSN='postgresql://usuario:clave@host/base?sslmode=require' \
        python scripts/estado_neon.py

Sale 0 si coinciden, 1 si hay desfase, 2 si falta configuración.
`NEON_DSN` se lee del entorno: ninguna credencial vive en este archivo.
"""

from __future__ import annotations

import os
import sys
import urllib.error

from alembic.config import Config
from alembic.script import ScriptDirectory
from sql_neon import ejecutar

# Objetos que cada migración posterior a la 0002 deja en el esquema. Comprobar
# la fila de `alembic_version` no alcanza: esa fila se escribe aunque el resto
# de la migración haya quedado a medias, y una migración aplicada por HTTP en
# lotes es exactamente donde eso puede pasar.
HUELLAS = {
    "0008_el_ingestor_no_resuelve": (
        "el ingestor ya no puede resolver una incidencia",
        "select count(*) = 0 from information_schema.role_table_grants "
        "where grantee = 'bn_ingestor' and table_name = 'incidencias_revision' "
        "and privilege_type = 'UPDATE'",
    ),
    "0009_evidencia_no_recuperable": (
        "incidencias admite EVIDENCIA_NO_RECUPERABLE",
        "select count(*) = 1 from pg_constraint where conrelid = 'incidencias_revision'::regclass "
        "and pg_get_constraintdef(oid) like '%EVIDENCIA_NO_RECUPERABLE%'",
    ),
    "0010_grafo_sin_recursion": (
        "existe la función bn_grafo_normativo",
        "select count(*) = 1 from pg_proc where proname = 'bn_grafo_normativo'",
    ),
    "0011_plazo_por_evento": (
        "los plazos admiten fechado por evento",
        "select count(*) = 1 from pg_constraint "
        "where conname = 'ck_plazos_fechado_relativo_o_por_evento'",
    ),
    "0013_recuperacion_hibrida": (
        "hay índice semántico y el léxico está sobre la columna generada",
        "select count(*) = 1 from information_schema.tables "
        "where table_name = 'fragmento_vectores' "
        "and exists (select 1 from pg_indexes "
        "            where indexname = 'ix_chunks_tsv') "
        "and exists (select 1 from information_schema.columns "
        "            where table_name = 'chunks' and column_name = 'tsv' "
        "              and is_generated = 'ALWAYS')",
    ),
    "0012_un_ciclo_por_vez": (
        "existe la tabla de turnos y el ingestor no puede borrar constancias",
        "select count(*) = 1 from information_schema.tables "
        "where table_name = 'arrendamientos' "
        "and not exists (select 1 from information_schema.role_table_grants "
        "                where grantee = 'bn_ingestor' and table_name = 'arrendamientos' "
        "                and privilege_type = 'DELETE')",
    ),
}


def _escalar(dsn: str, consulta: str) -> str:
    filas = ejecutar(dsn, consulta).get("rows", [])
    if not filas:
        return ""
    return str(next(iter(filas[0].values())))


def _cabeza_local() -> str:
    return ScriptDirectory.from_config(Config("alembic.ini")).get_current_head() or ""


def main() -> int:
    dsn = os.environ.get("NEON_DSN", "").strip()
    if not dsn:
        print("Falta NEON_DSN en el entorno.", file=sys.stderr)
        return 2

    try:
        remota = _escalar(dsn, "select version_num from alembic_version")
    except urllib.error.HTTPError as error:
        print(f"No se pudo consultar la base: {error}", file=sys.stderr)
        return 2

    local = _cabeza_local()
    print(f"Cabeza que el código espera : {local}")
    print(f"Cabeza aplicada en la base  : {remota or '(ninguna)'}")

    problemas: list[str] = []
    if remota != local:
        problemas.append(
            f"La base está en {remota or 'ninguna migración'} y el código espera {local}. "
            "Aplicá las que faltan antes de desplegar."
        )

    print()
    for revision, (que_prueba, consulta) in HUELLAS.items():
        try:
            presente = _escalar(dsn, consulta) in {"t", "true", "True"}
        except urllib.error.HTTPError as error:
            print(f"  ?  {revision}: no se pudo comprobar ({error})")
            problemas.append(f"{revision}: la comprobación no pudo correr")
            continue
        print(f"  {'ok' if presente else 'NO'}  {revision}: {que_prueba}")
        if not presente:
            problemas.append(
                f"{revision} figura aplicada pero su efecto no está en el esquema: {que_prueba}"
            )

    if problemas:
        print("\nDesfase entre la base y el código:", file=sys.stderr)
        for problema in problemas:
            print(f"  - {problema}", file=sys.stderr)
        return 1

    print("\nLa base gestionada y el código coinciden.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(main())
