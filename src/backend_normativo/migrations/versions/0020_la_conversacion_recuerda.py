"""Lo mínimo que una conversación tiene que recordar, y por cuánto tiempo.

Hasta acá cada consulta se resolvía sola. La persona contaba su situación, el
sistema contestaba, y en el mensaje siguiente no quedaba nada: la jurisdicción y
la fecha vivían en el navegador y los hechos no vivían en ningún lado. Con eso
no se puede repreguntar el dato que falta, no se puede corregir lo dicho, y no
se puede evaluar una condición sin que la persona repita todo cada vez.

Esta tabla guarda el estado mínimo (P-025) con la retención que P-037 fija:
**30 minutos de inactividad, dos horas de vida como máximo**, y sin historial
permanente. No se guarda ni un mensaje: el `CHECK` sobre las claves de `estado`
lo hace cumplir en la base, no en el cliente.

Es la primera vez que este sistema guarda algo que la persona dijo. Hasta ahora
la promesa era «nada de lo que escribas se guarda», y con esto pasa a ser «lo
que confirmes se guarda un rato y podés borrarlo cuando quieras». La pantalla
tiene que decirlo con esas palabras; el cambio está en D-134.

Revision ID: 0020_la_conversacion_recuerda
Revises: 0019_la_respuesta_se_contesta
"""

from __future__ import annotations

from alembic import op

revision = "0020_la_conversacion_recuerda"
down_revision = "0019_la_respuesta_se_contesta"
branch_labels = None
depends_on = None


# `version` sube con cada corrección. Sirve para lo que el criterio 1 de P-025
# pide: que el último dato confirmado invalide los resultados que dependían del
# anterior. Una respuesta lleva la versión con la que se calculó, y el frente
# marca como reemplazada cualquiera anterior en vez de dejar dos conclusiones
# distintas conviviendo en la misma pantalla.
CLAVES = "ARRAY['intencion', 'jurisdiccion', 'fecha', 'hechos', 'version']"

TABLA = f"""
CREATE TABLE sesiones_conversacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    creada_en timestamptz NOT NULL DEFAULT now(),
    ultima_actividad_en timestamptz NOT NULL DEFAULT now(),
    estado jsonb NOT NULL DEFAULT '{{}}'::jsonb,
    CONSTRAINT ck_sesiones_solo_estado_estructurado
        CHECK (estado - {CLAVES} = '{{}}'::jsonb)
);
CREATE INDEX ix_sesiones_actividad ON sesiones_conversacion (ultima_actividad_en);
CREATE INDEX ix_sesiones_creada ON sesiones_conversacion (creada_en);

COMMENT ON TABLE sesiones_conversacion IS
    'Estado mínimo de una conversación: intención, jurisdicción, fecha y hechos '
    'confirmados con su procedencia. No guarda mensajes ni identidad, caduca a '
    'los 30 minutos de inactividad y vive dos horas como máximo. El CHECK sobre '
    'las claves impide que alguien agregue el texto de la conversación sin '
    'decidirlo: sería convertir esto en un historial, que es otra cosa y tiene '
    'otra política.';
COMMENT ON COLUMN sesiones_conversacion.estado IS
    'hechos = {{clave: {{valor, origen, en}}}} o {{clave: {{rehusado: true, en}}}}. '
    'La ausencia de una clave es DESCONOCIDO y nunca se lee como falso; '
    'rehusado dice que la persona eligió no contestar, que tampoco es falso.';
"""

# La API abre, lee, corrige y borra sesiones. No necesita ver la de nadie más:
# no hay listado, y el identificador es la única forma de llegar a una.
PERMISOS = """
GRANT SELECT, INSERT, UPDATE, DELETE ON sesiones_conversacion TO bn_lector_api;
GRANT SELECT, DELETE ON sesiones_conversacion TO bn_auditor;
"""


def upgrade() -> None:
    op.execute(TABLA)
    op.execute(PERMISOS)


def downgrade() -> None:
    op.execute("DROP TABLE sesiones_conversacion")
