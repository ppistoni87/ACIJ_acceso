"""Separar el alcance territorial de un punto de su jurisdicción.

La jurisdicción dice dónde está el punto; el alcance dice a quién sirve. Sin
separarlos, la defensoría de Avellaneda y la de la Provincia de Buenos Aires
comparten `AR-B` y se responden como intercambiables: quien pregunta por el
servicio de su municipio recibe un organismo que no tiene competencia sobre su
reclamo.

Revision ID: 0004_alcance_de_los_puntos
Revises: 0003_carga_manual
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_alcance_de_los_puntos"
down_revision = "0003_carga_manual"
branch_labels = None
depends_on = None

ALCANCES = ("NACIONAL", "PROVINCIAL", "MUNICIPAL", "NO_DECLARADO")


def upgrade() -> None:
    op.add_column(
        "puntos_atencion",
        sa.Column(
            "alcance",
            sa.String(length=16),
            nullable=False,
            server_default="NO_DECLARADO",
        ),
    )
    op.add_column("puntos_atencion", sa.Column("ambito", sa.Text(), nullable=True))
    op.create_check_constraint(
        "alcance_vocabulario",
        "puntos_atencion",
        sa.column("alcance").in_(ALCANCES),
    )
    # Un punto municipal tiene que decir de qué municipio: «municipal» sin
    # municipio no distingue nada.
    op.create_check_constraint(
        "municipal_declara_su_ambito",
        "puntos_atencion",
        "alcance <> 'MUNICIPAL' OR ambito IS NOT NULL",
    )
    op.create_index("ix_puntos_atencion_alcance", "puntos_atencion", ["alcance"])


def downgrade() -> None:
    op.drop_index("ix_puntos_atencion_alcance", table_name="puntos_atencion")
    op.drop_constraint("municipal_declara_su_ambito", "puntos_atencion", type_="check")
    op.drop_constraint("alcance_vocabulario", "puntos_atencion", type_="check")
    op.drop_column("puntos_atencion", "ambito")
    op.drop_column("puntos_atencion", "alcance")
