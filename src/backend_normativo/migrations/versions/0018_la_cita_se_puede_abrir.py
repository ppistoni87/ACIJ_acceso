"""El fragmento publicado lleva su URL, para que la cita se pueda abrir.

La recuperación traía la URL de la fuente con un `JOIN` a `capturas` y
`fuente_urls`. Las dos son staging, y el lector de la API no las puede leer —ni
debe: la invariante es que accede únicamente a proyecciones servibles—. El
resultado era que `POST /v1/recuperacion` devolvía 500 en cualquier despliegue
con roles de verdad, y nadie lo veía porque las pruebas corren con un rol que
lee todo.

Quitar la URL arreglaba el permiso y rompía algo peor: una cita que no se puede
abrir. Este proyecto entero se apoya en que quien lee una respuesta pueda ir al
texto y verificarlo.

Así que la URL viaja con el fragmento. Es lo que tiene que pasar con todo lo que
el lector necesita: el corte lleva su propia evidencia, y no va a buscarla al
otro lado de la frontera.

Revision ID: 0018_la_cita_se_puede_abrir
Revises: 0017_la_consulta_deja_rastro
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_la_cita_se_puede_abrir"
down_revision = "0017_la_consulta_deja_rastro"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("url_fuente", sa.Text(), nullable=True))
    # Los cortes ya publicados se completan desde staging **una vez**, acá, que
    # es donde corre el migrador y tiene permiso. Después nadie vuelve a cruzar.
    op.execute(
        """
        UPDATE chunks c SET url_fuente = fu.url
          FROM unidades_documentales u
          JOIN documento_versiones dv ON dv.id = u.doc_version_id
          JOIN capturas cap ON cap.id = dv.captura_id
          JOIN fuente_urls fu ON fu.id = cap.source_url_id
         WHERE c.unidad_id = u.id AND c.url_fuente IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("chunks", "url_fuente")
