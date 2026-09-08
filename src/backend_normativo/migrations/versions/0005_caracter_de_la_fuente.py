"""Distinguir una fuente oficial de una secundaria.

Una ONG puede afirmar algo cierto y relevante que el organismo no publica.
Presentarlo como dicho por el organismo le da una autoridad que no tiene;
descartarlo pierde información que a alguien le sirve. Lo que corresponde es
conservarlo con su atribución, y para eso la fuente tiene que declarar con qué
autoridad habla.

Revision ID: 0005_caracter_de_la_fuente
Revises: 0004_alcance_de_los_puntos
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_caracter_de_la_fuente"
down_revision = "0004_alcance_de_los_puntos"
branch_labels = None
depends_on = None

CARACTERES = ("OFICIAL", "SECUNDARIA")


def upgrade() -> None:
    op.add_column(
        "fuentes",
        sa.Column("caracter", sa.String(length=16), nullable=False, server_default="OFICIAL"),
    )
    op.create_check_constraint(
        "caracter_vocabulario", "fuentes", sa.column("caracter").in_(CARACTERES)
    )
    op.create_index("ix_fuentes_caracter", "fuentes", ["caracter"])


def downgrade() -> None:
    op.drop_index("ix_fuentes_caracter", table_name="fuentes")
    op.drop_constraint("caracter_vocabulario", "fuentes", type_="check")
    op.drop_column("fuentes", "caracter")
