"""La URL de una fuente puede ser de carga manual.

Revision ID: 0003_carga_manual
Revises: 0002_reglas_de_integridad

Dieciocho fuentes del corpus no se pueden recorrer: unas devuelven 403, otra
tiene un certificado que no valida, la mayoría no tiene una URL inequívoca.
Cuando alguien consigue su contenido por una vía legítima, la captura necesita
un origen al que colgarse, y ese origen no es una dirección http.

La restricción original exigía `^https?://` para que nadie registrara una
plantilla ni una ruta local disfrazada de URL. Ese propósito se conserva: lo que
se agrega es un esquema propio, `manual://`, que dice exactamente lo que pasó.
Inventarle una http a un archivo que llegó por otra vía sería peor que decir que
no la tiene, porque el monitor la intentaría visitar y el reporte de cobertura
la contaría como recorrible.
"""

from __future__ import annotations

from alembic import op

revision = "0003_carga_manual"
down_revision = "0002_reglas_de_integridad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("url_http_concreta", "fuente_urls", type_="check")
    op.create_check_constraint(
        "url_concreta",
        "fuente_urls",
        "url ~ '^(https?|manual)://'",
    )


def downgrade() -> None:
    # Al volver atrás no puede quedar una URL que la restricción vieja rechace.
    op.execute(
        "DELETE FROM capturas WHERE source_url_id IN (SELECT id FROM fuente_urls WHERE url NOT LIKE 'http%')"
    )
    op.execute("DELETE FROM fuente_urls WHERE url NOT LIKE 'http%'")
    op.drop_constraint("url_concreta", "fuente_urls", type_="check")
    op.create_check_constraint(
        "url_http_concreta",
        "fuente_urls",
        "url ~ '^https?://'",
    )
