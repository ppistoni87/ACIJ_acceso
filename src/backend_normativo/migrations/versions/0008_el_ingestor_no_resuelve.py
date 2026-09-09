"""El ingestor abre incidencias; no las cierra.

La migración 0002 dice, en el comentario que encabeza sus permisos, que "el
ingestor escribe descubrimiento y candidatos; no publica ni resuelve". El
GRANT no dice lo mismo: otorga `INSERT, UPDATE` sobre `incidencias_revision`,
y con el UPDATE el ingestor puede marcar una incidencia como RESUELTA. La
diferencia no se veía leyendo el SQL —la tabla está en una lista de doce— y
apareció al probar los permisos contra la base real.

Las dos únicas sentencias que resuelven una incidencia viven en `curacion/`
(`revision.py` e `identidad.py`), que es trabajo de revisor. Ninguna ruta de
ingesta actualiza la tabla: solo inserta. Así que se revoca el UPDATE y queda
el INSERT, que es lo que la ingesta necesita para abrir un hallazgo.

Revision ID: 0008_el_ingestor_no_resuelve
Revises: 0007_servibles_sin_recorrer_todo
"""

from __future__ import annotations

from alembic import op

revision = "0008_el_ingestor_no_resuelve"
down_revision = "0007_servibles_sin_recorrer_todo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("REVOKE UPDATE ON incidencias_revision FROM bn_ingestor;")


def downgrade() -> None:
    op.execute("GRANT UPDATE ON incidencias_revision TO bn_ingestor;")
