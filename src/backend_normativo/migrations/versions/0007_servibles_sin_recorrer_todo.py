"""No evaluar versión por versión lo que ya se sabe que no se sirve.

`v_hechos_servibles` recorría las 7.888 versiones del registro y llamaba a
`bn_motivos_no_servible` en cada una. Con ocho capacidades eso son 63.104
evaluaciones para responder cuántas versiones puede servir cada capacidad, y el
endpoint de cobertura tardaba 800 ms por eso.

El pre-filtro que se agrega es exactamente un subconjunto de los motivos que la
propia función devuelve: una versión que no está `PUBLISHED`, o cuyo release no
está publicado, ya recibía por esos dos motivos y nunca podía ser servible. Con
lo cual el resultado es el mismo y el trabajo baja de 7.888 evaluaciones a las
que efectivamente pueden pasar.

Es importante que el pre-filtro no sea más estricto que los motivos: si alguna
vez se agrega una condición acá que la función no evalúe, la vista empezaría a
esconder versiones servibles sin decirlo. Por eso la prueba compara el resultado
con el de la versión sin pre-filtro.

Revision ID: 0007_servibles_sin_recorrer_todo
Revises: 0006_indice_de_listado
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_servibles_sin_recorrer_todo"
down_revision = "0006_indice_de_listado"
branch_labels = None
depends_on = None

CON_PREFILTRO = """
CREATE OR REPLACE FUNCTION v_hechos_servibles(
    fecha date,
    known_at timestamptz DEFAULT now(),
    capacidad text DEFAULT 'IDENTIFICACION'
)
RETURNS TABLE(
    registro_version_id uuid, entidad_tipo text, entidad_id uuid, release_id uuid,
    valid_desde date, valid_hasta date, verificado_en timestamptz
)
LANGUAGE sql STABLE AS $$
    SELECT v.id, v.entidad_tipo, v.entidad_id, v.release_id,
           v.valid_desde, v.valid_hasta, v.verificado_en
      FROM registro_versiones v
     -- Estas dos condiciones son motivos que `bn_motivos_no_servible` ya
     -- devuelve. Comprobarlas antes evita evaluar una por una las versiones
     -- que de todos modos iban a quedar afuera.
     WHERE v.estado_revision = 'PUBLISHED'
       AND EXISTS (
           SELECT 1 FROM releases r
            WHERE r.id = v.release_id AND r.estado = 'PUBLICADO'
       )
       AND NOT EXISTS (
           SELECT 1 FROM bn_motivos_no_servible(v.id, fecha, known_at, capacidad)
       );
$$;
"""

SIN_PREFILTRO = """
CREATE OR REPLACE FUNCTION v_hechos_servibles(
    fecha date,
    known_at timestamptz DEFAULT now(),
    capacidad text DEFAULT 'IDENTIFICACION'
)
RETURNS TABLE(
    registro_version_id uuid, entidad_tipo text, entidad_id uuid, release_id uuid,
    valid_desde date, valid_hasta date, verificado_en timestamptz
)
LANGUAGE sql STABLE AS $$
    SELECT v.id, v.entidad_tipo, v.entidad_id, v.release_id,
           v.valid_desde, v.valid_hasta, v.verificado_en
      FROM registro_versiones v
     WHERE NOT EXISTS (
         SELECT 1 FROM bn_motivos_no_servible(v.id, fecha, known_at, capacidad)
     );
$$;
"""


def upgrade() -> None:
    op.execute(CON_PREFILTRO)
    # El índice hace que el pre-filtro sea una búsqueda y no otro recorrido.
    op.create_index(
        "ix_registro_versiones_publicadas",
        "registro_versiones",
        ["release_id"],
        postgresql_where=sa.text("estado_revision = 'PUBLISHED'"),
    )


def downgrade() -> None:
    op.drop_index("ix_registro_versiones_publicadas", table_name="registro_versiones")
    op.execute(SIN_PREFILTRO)
