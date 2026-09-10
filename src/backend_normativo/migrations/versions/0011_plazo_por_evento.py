"""Un plazo que la norma expresa como evento no necesita inventar un número.

Tres plazos del corpus declaran una cantidad que su propia cita no contiene, y
al mirarlos aparece que no son un error de curaduría: los tres traen
`requiere_revision` y un motivo que explica exactamente el problema.

* «La ayuda escolar se hará efectiva **en el mes de marzo de cada año**»:
  se cargó como «1 día» porque el modelo no admite una fecha recurrente.
* «Se abonará **una (1) vez al año**»: es una frecuencia, no una duración;
  se cargó como «1 día».
* «La solicitud se presentará **en el momento de la inscripción**»: se cargó
  como «0 días», y la lectura lo dice: «un cero acá significa "no hay duración
  declarada", no "vence el mismo día"».

La restricción `ck_plazos_fechado_o_relativo_no_ambos` obligaba a elegir entre
una fecha y una duración, y estos tres plazos no son ninguna de las dos cosas:
son un evento. Con lo cual el modelo forzaba a escribir un número falso y a
explicarlo en una prosa que nada lee. Un cero que significa «no sé» es
indistinguible de un cero que significa «cero».

Se agrega la tercera forma: sin fechas y sin cantidad, con el evento declarado.
Sigue prohibido tener fecha y cantidad a la vez, y sigue exigido que una
cantidad venga con su unidad y su evento.

Revision ID: 0011_plazo_por_evento
Revises: 0010_grafo_sin_recursion
"""

from __future__ import annotations

from alembic import op

revision = "0011_plazo_por_evento"
down_revision = "0010_grafo_sin_recursion"
branch_labels = None
depends_on = None

NUEVA = """
ALTER TABLE plazos ADD CONSTRAINT ck_plazos_fechado_relativo_o_por_evento CHECK (
    CASE
        -- Fechado y relativo a la vez sigue sin tener sentido.
        WHEN (inicio IS NOT NULL OR fin IS NOT NULL) AND cantidad IS NOT NULL THEN false
        -- Ni fecha ni cantidad: es un plazo anclado a un evento, y el evento
        -- tiene que estar. Sin él no se estaría declarando nada.
        WHEN inicio IS NULL AND fin IS NULL AND cantidad IS NULL
            THEN evento_inicio IS NOT NULL
        ELSE true
    END
)
"""


def upgrade() -> None:
    op.execute("ALTER TABLE plazos DROP CONSTRAINT ck_plazos_fechado_o_relativo_no_ambos")
    op.execute(NUEVA)


def downgrade() -> None:
    # Volver atrás con plazos por evento cargados los dejaría fuera de la
    # restricción vieja. Se les repone la cantidad cero que la 0011 vino a
    # sacar, con constancia de que es un valor de compatibilidad y no un dato.
    op.execute(
        "UPDATE plazos SET cantidad = 0, unidad = coalesce(unidad, 'dias') "
        " WHERE inicio IS NULL AND fin IS NULL AND cantidad IS NULL"
    )
    op.execute("ALTER TABLE plazos DROP CONSTRAINT ck_plazos_fechado_relativo_o_por_evento")
    op.execute(
        "ALTER TABLE plazos ADD CONSTRAINT ck_plazos_fechado_o_relativo_no_ambos CHECK ("
        "  ((inicio IS NOT NULL) OR (fin IS NOT NULL)) <> (cantidad IS NOT NULL))"
    )
