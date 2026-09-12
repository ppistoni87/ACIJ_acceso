"""Un corte es la foto completa de lo servible, también en las versiones.

D-127 arregló esto para los fragmentos: un segundo corte armado sólo con sus
candidatos dejaba a la búsqueda sin nada que citar, porque `release_vigente`
devuelve el corte más reciente y los fragmentos se filtran por él. La solución
fue heredar del corte anterior lo que seguía vigente.

El mismo agujero seguía abierto un nivel más arriba y se cobró una publicación:
`registro_versiones.release_id` es **el corte que publicó esa versión**, no «los
cortes en los que se sirve». Publicar el dato operativo creó un corte con 14.390
versiones y sin los 15 beneficios ni las 8 normas del anterior, que se quedaron
apuntando al corte viejo. El informe salió en verde —14.390 versiones, 639
fragmentos heredados, 130 en cuarentena— mientras la orientación y la evaluación
quedaban muertas.

Esta tabla dice qué versiones sirve cada corte. `release_id` conserva su
significado —quién la publicó primero—, y por eso revertir sigue devolviendo a
APPROVED sólo lo que ese corte introdujo: lo heredado vuelve a servirse desde el
corte del que venía, sin tocarlo.

Revision ID: 0021_un_corte_es_la_foto
Revises: 0020_la_conversacion_recuerda
"""

from __future__ import annotations

from alembic import op

revision = "0021_un_corte_es_la_foto"
down_revision = "0020_la_conversacion_recuerda"
branch_labels = None
depends_on = None


TABLA = """
CREATE TABLE release_versiones (
    release_id uuid NOT NULL REFERENCES releases (id) ON DELETE CASCADE,
    registro_version_id uuid NOT NULL REFERENCES registro_versiones (id) ON DELETE CASCADE,
    heredada boolean NOT NULL DEFAULT false,
    PRIMARY KEY (release_id, registro_version_id)
);
CREATE INDEX ix_release_versiones_version ON release_versiones (registro_version_id);

COMMENT ON TABLE release_versiones IS
    'Qué versiones sirve cada corte. Un corte es la foto completa de lo '
    'servible, no el delta de su corrida: incluye lo que esa publicación '
    'incorporó y lo que heredó del corte anterior. Sin esto, publicar algo '
    'nuevo dejaba de servir todo lo viejo sin un solo error.';
COMMENT ON COLUMN release_versiones.heredada IS
    'Verdadero si venía del corte anterior. Sirve para que revertir no toque '
    'lo heredado: eso lo publicó otro corte y se sigue sirviendo desde ahí.';
"""

# El backfill dice la verdad de lo que hay: cada corte sirve lo que publicó.
# No se reconstruye lo que «debería haber heredado» —eso sería reescribir la
# historia de cortes que ya se sirvieron—; la herencia empieza a valer en la
# próxima publicación.
BACKFILL = """
INSERT INTO release_versiones (release_id, registro_version_id, heredada)
SELECT rv.release_id, rv.id, false
  FROM registro_versiones rv
 WHERE rv.release_id IS NOT NULL
ON CONFLICT DO NOTHING;
"""

PERMISOS = """
GRANT SELECT ON release_versiones TO bn_lector_api;
GRANT SELECT ON release_versiones TO bn_auditor;
GRANT SELECT, INSERT, DELETE ON release_versiones TO bn_publicador;
"""


def upgrade() -> None:
    op.execute(TABLA)
    op.execute(BACKFILL)
    op.execute(PERMISOS)


def downgrade() -> None:
    op.execute("DROP TABLE release_versiones")
