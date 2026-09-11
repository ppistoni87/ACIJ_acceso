"""El lector tiene que poder comprobar contra qué esquema está sirviendo.

La sonda de readiness (P-019, criterio 2) verifica que el esquema aplicado sea
el que el código espera. Para que esa verificación signifique algo tiene que
hacerla **la conexión que sirve**: con una conexión de administración, la sonda
pasaría mientras el lector está roto, que es exactamente el caso que hay que
detectar.

`bn_lector_api` no podía leer `alembic_version`, así que la sonda informaba «la
base está en ninguna migración» cuando lo que pasaba era que no podía mirar.

Esto no contradice la invariante de que el lector accede sólo a proyecciones
servibles. `alembic_version` es una fila con un identificador de migración: es
metadato del esquema que el lector ya está usando, no contenido del corpus. La
diferencia con `capturas` —que el lector no puede leer y no debe— es que
aquello es material de staging: qué se descargó, de dónde y cuándo.

Se concede sólo `SELECT`, y sólo sobre esa tabla.

Revision ID: 0016_lector_ve_su_esquema
Revises: 0015_lo_que_el_organismo_publica
"""

from __future__ import annotations

from alembic import op

revision = "0016_lector_ve_su_esquema"
down_revision = "0015_lo_que_el_organismo_publica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT SELECT ON TABLE alembic_version TO bn_lector_api")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON TABLE alembic_version FROM bn_lector_api")
