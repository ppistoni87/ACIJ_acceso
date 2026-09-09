"""Un original que ya no se puede recuperar tiene nombre propio.

P-004 pide que, si el objeto detrás de una captura falta o su hash difiere, se
abra una incidencia y se bloquee la publicación de lo que dependa de él. El
bloqueo ya existe: `bn_motivos_no_servible` devuelve CONFLICT cuando hay una
incidencia abierta de severidad alta sobre la versión. Lo que faltaba era el
tipo, porque los ocho del vocabulario describen problemas de la norma o de la
fuente, y este es un problema del almacén: el texto se leyó bien en su momento
y hoy no hay con qué comprobarlo.

Meterlo en COBERTURA_EXTRACCION o ACCESO_BLOQUEADO habría ahorrado esta
migración y mezclado dos cosas que se atienden distinto: una se resuelve
volviendo a extraer, la otra recuperando el objeto de un respaldo o
recapturando la fuente.

Revision ID: 0009_evidencia_no_recuperable
Revises: 0008_el_ingestor_no_resuelve
"""

from __future__ import annotations

from alembic import op

revision = "0009_evidencia_no_recuperable"
down_revision = "0008_el_ingestor_no_resuelve"
branch_labels = None
depends_on = None

ANTERIORES = (
    "CONFLICTO_DE_FUENTES",
    "IDENTIDAD_AMBIGUA",
    "DISCREPANCIA_NUMERACION",
    "VIGENCIA_INDETERMINADA",
    "COBERTURA_EXTRACCION",
    "ACCESO_BLOQUEADO",
    "CAMBIO_DE_ESQUEMA",
    "DATO_FALTANTE_CRITICO",
)
NUEVOS = (*ANTERIORES, "EVIDENCIA_NO_RECUPERABLE")


def _rehacer(valores: tuple[str, ...]) -> None:
    lista = ", ".join(f"'{v}'" for v in valores)
    op.execute(
        "ALTER TABLE incidencias_revision DROP CONSTRAINT ck_incidencias_revision_tipo_vocabulario"
    )
    op.execute(
        "ALTER TABLE incidencias_revision ADD CONSTRAINT "
        f"ck_incidencias_revision_tipo_vocabulario CHECK (tipo IN ({lista}))"
    )


def upgrade() -> None:
    _rehacer(NUEVOS)


def downgrade() -> None:
    # Bajar el vocabulario con filas que lo usan dejaría la tabla en un estado
    # que la restricción rechaza; se cierran primero, con constancia del motivo.
    op.execute(
        "UPDATE incidencias_revision "
        "   SET estado = 'RESUELTA', "
        "       decision = 'cerrada por revertir el vocabulario de tipos', "
        "       decidido_por = 'migracion 0009 (downgrade)', "
        "       resuelta_en = now(), "
        "       tipo = 'COBERTURA_EXTRACCION' "
        " WHERE tipo = 'EVIDENCIA_NO_RECUPERABLE'"
    )
    _rehacer(ANTERIORES)
