"""Dos disparos simultáneos del ciclo no pueden procesar lo mismo dos veces.

El ciclo de monitoreo está pensado para que un planificador lo llame cada hora.
Un planificador que reintenta —y todos reintentan— puede disparar dos veces la
misma vuelta, y hoy las dos correrían: capturarían la misma fuente, crearían la
misma versión documental y emitirían el mismo evento. Nada en el esquema lo
impedía.

Un arrendamiento es un derecho de uso con vencimiento, y eso es exactamente lo
que hace falta: quien lo toma es el único que puede correr, y si se cae sin
soltarlo el derecho caduca solo y la vuelta siguiente puede tomarlo. Sin el
vencimiento, un proceso que muere dejando el candado puesto bloquea el ciclo
para siempre y hace falta que alguien lo destrabe a mano.

La toma es una sola sentencia —`INSERT … ON CONFLICT DO UPDATE … WHERE ya
venció`— y no dos, porque «fijarse si está libre» y «tomarlo» en sentencias
separadas es la carrera que este arrendamiento viene a evitar: los dos procesos
se fijan, los dos ven libre, los dos toman.

La fila no se borra al soltar: se le adelanta el vencimiento. Así queda como
constancia de quién corrió la última vuelta, cuándo y cuántas van, que es lo
primero que se pregunta cuando algo no corrió.

Revision ID: 0012_un_ciclo_por_vez
Revises: 0011_plazo_por_evento
"""

from __future__ import annotations

from alembic import op

revision = "0012_un_ciclo_por_vez"
down_revision = "0011_plazo_por_evento"
branch_labels = None
depends_on = None

TABLA = """
CREATE TABLE arrendamientos (
    recurso     varchar(64) PRIMARY KEY,
    titular     varchar(200) NOT NULL,
    tomado_en   timestamptz NOT NULL,
    vence_en    timestamptz NOT NULL,
    corridas    integer NOT NULL DEFAULT 1,
    CONSTRAINT ck_arrendamiento_vence_despues_de_tomarse CHECK (vence_en >= tomado_en),
    CONSTRAINT ck_arrendamiento_corridas_positivas CHECK (corridas > 0)
)
"""

COMENTARIOS = [
    "COMMENT ON TABLE arrendamientos IS "
    "'Derecho de uso exclusivo con vencimiento sobre un recurso que no admite dos "
    "procesos a la vez. La fila sobrevive al fin de la corrida como constancia.'",
    "COMMENT ON COLUMN arrendamientos.titular IS "
    "'Quién lo tomó: máquina, proceso y un identificador de corrida. Sirve para "
    "saber qué instancia quedó colgada cuando un arrendamiento no se soltó.'",
    "COMMENT ON COLUMN arrendamientos.vence_en IS "
    "'Tope máximo de la corrida. Pasado esto el recurso queda libre aunque el "
    "titular siga vivo: una corrida que se pasa de su arrendamiento se entera al "
    "soltarlo y lo declara, porque otra pudo haber empezado en paralelo.'",
]

# El ciclo corre con el rol de ingesta. No se le da DELETE: soltar es adelantar
# el vencimiento, no borrar la constancia.
PERMISOS = "GRANT SELECT, INSERT, UPDATE ON arrendamientos TO bn_ingestor"


def upgrade() -> None:
    op.execute(TABLA)
    for comentario in COMENTARIOS:
        op.execute(comentario)
    op.execute(PERMISOS)


def downgrade() -> None:
    op.execute("DROP TABLE arrendamientos")
