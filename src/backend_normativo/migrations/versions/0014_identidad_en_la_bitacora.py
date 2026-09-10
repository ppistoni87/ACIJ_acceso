"""La bitácora dice quién firmó y también cómo se supo que era esa persona.

P-017 criterio 1. Las rutas de administración pedían un token de una lista en
`BN_ADMIN_TOKENS` y tomaban al actor de la cabecera `X-Actor`. El token está bien
como puerta, pero identifica al despliegue y no a la persona: quien lo tiene
puede firmar como cualquiera. Y lo que se firma en este sistema es que una regla
dice lo que dice el derecho.

Con credenciales firmadas el actor sale de la credencial. Pero eso deja una
pregunta que la bitácora no podía contestar: de los eventos que ya están y de
los que vengan, ¿cuáles llevan un actor verificado y cuáles uno que quien
llamaba escribió a mano? Sin esa columna las dos cosas son la misma fila, y
dentro de dos años nadie va a poder distinguirlas.

Cómo se llena. No la pasa cada sitio que escribe en la bitácora —son siete y
alcanza con que uno se olvide—: sale de `bn.identidad`, un ajuste de sesión que
la API pone al abrir la transacción, y la columna la toma por omisión. Si nadie
lo puso, queda `PROCESO_LOCAL`, que es lo que efectivamente es: alguien con
acceso directo a la base o al CLI.

Las filas anteriores a esta migración quedan en `NO_REGISTRADA`. No se les
adivina la procedencia: decir de un evento viejo que fue `PROCESO_LOCAL` sería
inventar una constancia, que es justo lo que esta columna viene a evitar.

Revision ID: 0014_identidad_en_la_bitacora
Revises: 0013_recuperacion_hibrida
"""

from __future__ import annotations

from alembic import op

revision = "0014_identidad_en_la_bitacora"
down_revision = "0013_recuperacion_hibrida"
branch_labels = None
depends_on = None

# Dos pasos a propósito: primero la columna con un valor constante, que es lo
# que las filas viejas merecen, y después el valor por omisión para las nuevas.
# Un solo paso con la expresión les pondría `PROCESO_LOCAL` a todas.
COLUMNA = """
ALTER TABLE auditoria_eventos
    ADD COLUMN identidad varchar(24) NOT NULL DEFAULT 'NO_REGISTRADA';

ALTER TABLE auditoria_eventos
    ALTER COLUMN identidad SET DEFAULT
        coalesce(nullif(current_setting('bn.identidad', true), ''), 'PROCESO_LOCAL');

ALTER TABLE auditoria_eventos ADD CONSTRAINT ck_auditoria_identidad_vocabulario
    CHECK (identidad IN (
        'CREDENCIAL_FIRMADA', 'AUTODECLARADA', 'PROCESO_LOCAL', 'NO_REGISTRADA'));

COMMENT ON COLUMN auditoria_eventos.identidad IS
    'Cómo se estableció el actor. CREDENCIAL_FIRMADA: credencial por persona, '
    'verificada y no revocada. AUTODECLARADA: token compartido y actor escrito '
    'por quien llamaba, que solo se admite con el modo de desarrollo activado. '
    'PROCESO_LOCAL: CLI o acceso directo a la base. NO_REGISTRADA: anterior a '
    'que esto se registrara.';
"""

# Revocar es lo que hace que una credencial robada deje de servir antes de
# vencer. La fila queda: saber que una credencial fue revocada, cuándo y por
# qué es parte de la historia de quién pudo hacer qué.
REVOCACION = """
CREATE TABLE credenciales_revocadas (
    jti          varchar(32) PRIMARY KEY,
    actor        text NOT NULL,
    motivo       text NOT NULL,
    revocada_por text NOT NULL,
    revocada_en  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE credenciales_revocadas IS
    'Credenciales que dejaron de valer antes de su vencimiento. No se borran: '
    'que una credencial haya sido revocada es parte de la historia de quién '
    'pudo hacer qué y cuándo dejó de poder.';

-- La API de lectura no ve esta tabla: los nombres de quienes administran no
-- son parte del corpus servible, y la revocación se comprueba en la conexión de
-- administración, que es la única que la necesita.
GRANT SELECT, INSERT ON credenciales_revocadas TO bn_revisor, bn_publicador;
"""

INMUTABLE = """
CREATE TRIGGER trg_credenciales_revocadas_inmutable
    BEFORE DELETE OR UPDATE ON credenciales_revocadas
    FOR EACH ROW EXECUTE FUNCTION bn_rechazar_modificacion();
"""


def upgrade() -> None:
    op.execute(COLUMNA)
    op.execute(REVOCACION)
    op.execute(INMUTABLE)


def downgrade() -> None:
    op.execute("DROP TABLE credenciales_revocadas")
    op.execute("ALTER TABLE auditoria_eventos DROP CONSTRAINT ck_auditoria_identidad_vocabulario")
    op.execute("ALTER TABLE auditoria_eventos DROP COLUMN identidad")
