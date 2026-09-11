"""Una consulta que no deja rastro no se puede medir (P-021, criterio 1).

`consultas_auditadas` existe desde la migración 0001 y `bn_lector_api` tiene
`INSERT` concedido desde la 0002. Nadie escribía nunca en ella: la tabla, el
permiso y el índice estaban, y el código que los usara no. Otra falla que no
falla —no hay error, simplemente no hay datos— y que solo se ve cuando alguien
pregunta cuántas abstenciones hubo y la respuesta es cero filas.

Dos cambios para que sirva:

* **`request_id`**, para poder seguir una consulta entre el registro, el log y
  el reporte de quien la hizo. Sin eso, «tardó mucho» no se puede investigar.
* **`release_id` deja de ser obligatorio.** Tal como estaba, una consulta sin
  corte publicado no se podía registrar, y esa es precisamente la abstención
  más importante: el sistema no puede contestar nada. La única medición que no
  entraba era la del peor caso.

Y una columna para la causa: el criterio 3 pide distinguir una abstención
correcta de una respuesta resuelta, y para eso el estado solo no alcanza —hay
que saber **por qué** no se contestó—.

Revision ID: 0017_la_consulta_deja_rastro
Revises: 0016_lector_ve_su_esquema
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_la_consulta_deja_rastro"
down_revision = "0016_lector_ve_su_esquema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultas_auditadas", sa.Column("request_id", sa.Text(), nullable=True))
    op.add_column("consultas_auditadas", sa.Column("motivo_abstencion", sa.Text(), nullable=True))
    op.alter_column("consultas_auditadas", "release_id", nullable=True)
    op.create_index(
        "ix_consultas_auditadas_request_id", "consultas_auditadas", ["request_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_consultas_auditadas_request_id", table_name="consultas_auditadas")
    # Volver a NOT NULL exige que no queden filas sin corte, que son justamente
    # las que esta migración vino a permitir. Se borran: son registros de
    # medición, no evidencia jurídica, y conservarlos impediría revertir.
    op.execute("DELETE FROM consultas_auditadas WHERE release_id IS NULL")
    op.alter_column("consultas_auditadas", "release_id", nullable=False)
    op.drop_column("consultas_auditadas", "motivo_abstencion")
    op.drop_column("consultas_auditadas", "request_id")
