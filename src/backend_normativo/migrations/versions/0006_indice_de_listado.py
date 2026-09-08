"""Índice para el orden del listado de normas.

Sobre el catálogo nacional completo —423.718 normas— listar las primeras veinte
hacía un recorrido secuencial de la tabla entera para ordenarla. El listado es
la primera pantalla de cualquier consulta, así que ese costo lo paga todo el
mundo en cada pregunta.

Revision ID: 0006_indice_de_listado
Revises: 0005_caracter_de_la_fuente
"""

from __future__ import annotations

from alembic import op

revision = "0006_indice_de_listado"
down_revision = "0005_caracter_de_la_fuente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_normas_orden_listado",
        "normas",
        ["anio", "numero"],
        postgresql_ops={"anio": "DESC NULLS LAST"},
    )


def downgrade() -> None:
    op.drop_index("ix_normas_orden_listado", table_name="normas")
