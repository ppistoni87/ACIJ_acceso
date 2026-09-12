"""Quien pregunta puede contestar si le sirvió, y pedir hablar con alguien.

El sistema medía todo de sí mismo —latencia, abstenciones por causa, cuántas
evidencias usó— y nada de lo único que importa: si a la persona que preguntó le
sirvió lo que leyó. Una respuesta puede salir en 40 ms, con seis citas y el
corte correcto, y ser inútil. Con la traza sola eso se cuenta como éxito.

Así que hay una tabla para la devolución. Tres decisiones que la forman:

* **No hay campo de texto libre.** Es la decisión más importante de esta
  migración y es una decisión de privacidad, no de producto. Una caja de
  comentarios debajo de una respuesta sobre desalojos o pensiones por
  discapacidad es el lugar exacto donde alguien escribe su caso: el nombre de su
  hija, la dirección de la que lo echan, el número de expediente. Todo el resto
  del sistema está construido para no guardar eso —`intencion` recibe la ruta y
  no la pregunta— y una caja de texto lo tiraría abajo en un renglón. Las
  señales son un vocabulario cerrado y el CHECK lo hace cumplir en la base, no
  en el cliente.

* **Se une a la traza por `request_id`, no por su contenido.** Con eso quien
  opera puede saber que las respuestas marcadas «no me sirvió» son sobre todo
  abstenciones por falta de evidencia, o que se concentran en una ruta, o en un
  corte. Nunca puede saber qué preguntaron. No hay clave foránea a propósito:
  `request_id` no es único —quien llama puede repetir la cabecera— y una FK
  obligaría a inventarle una unicidad que no tiene.

* **Una señal por consulta, y no más.** El UNIQUE sobre `(request_id, senal)`
  hace que apretar dos veces el mismo botón no cuente dos veces. Una métrica de
  satisfacción que se puede inflar apretando repetido no es una métrica.

La retención es la misma que la de la traza y se aplica en el mismo lugar
(`observabilidad.purgar`): si se borrara la traza y quedaran las devoluciones,
quedaría un registro huérfano que crece para siempre y que ya no se puede
interpretar.

Revision ID: 0019_la_respuesta_se_contesta
Revises: 0018_la_cita_se_puede_abrir
"""

from __future__ import annotations

from alembic import op

revision = "0019_la_respuesta_se_contesta"
down_revision = "0018_la_cita_se_puede_abrir"
branch_labels = None
depends_on = None


TABLA = """
CREATE TABLE devoluciones (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id text NOT NULL,
    senal text NOT NULL,
    ocurrido_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_devoluciones_senal
        CHECK (senal IN ('SIRVIO', 'NO_SIRVIO', 'QUIERE_PERSONA')),
    CONSTRAINT uq_devoluciones_request_senal UNIQUE (request_id, senal)
);
CREATE INDEX ix_devoluciones_ocurrido_en ON devoluciones (ocurrido_en);
CREATE INDEX ix_devoluciones_senal ON devoluciones (senal);

COMMENT ON TABLE devoluciones IS
    'Lo que la persona contesta sobre la respuesta que recibió. No lleva texto '
    'libre y no lleva identidad: solo una señal de un vocabulario cerrado y el '
    'request_id, que la une a la traza de la consulta sin decir qué se preguntó. '
    'Agregar acá una columna de texto libre invierte esa decisión y necesita '
    'discutirse como lo que es: guardar el relato personal de quien consulta.';
COMMENT ON COLUMN devoluciones.senal IS
    'SIRVIO / NO_SIRVIO: la respuesta a «¿te sirvió?». QUIERE_PERSONA: pidió '
    'hablar con alguien, que es la señal más cara de todas y la que menos se mide.';
"""

# La API escribe su propia devolución igual que escribe su traza: `INSERT` y
# nada más. No se le da SELECT —no necesita leer devoluciones de nadie— ni
# UPDATE ni DELETE: una devolución no se corrige, se agrega otra.
PERMISOS = """
GRANT INSERT ON devoluciones TO bn_lector_api;
GRANT SELECT ON devoluciones TO bn_ingestor, bn_revisor, bn_publicador, bn_auditor;
"""


def upgrade() -> None:
    op.execute(TABLA)
    op.execute(PERMISOS)


def downgrade() -> None:
    op.execute("DROP TABLE devoluciones")
