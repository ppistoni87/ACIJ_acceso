"""Lo que un organismo publica sobre un derecho no es la norma, y hasta ahora no era nada.

Diecisiete fuentes del manifiesto respondían 200, se extraían y no dejaban una
sola fila donde su historia dice que deberían: sedes, canales de atención,
cronogramas, pasos de trámite. El recuento las mostraba como «capturadas,
extraídas y sin destino», que sonaba a diecisiete problemas distintos.

Era uno solo. El adaptador de páginas institucionales producía el texto de la
página y **cero unidades**, con el argumento —correcto— de que una página de
sedes no tiene articulado. Pero toda tabla de destino exige `evidencia_id`, y
una evidencia apunta a una unidad. Sin unidades no hay evidencia, y sin
evidencia no se puede curar nada: esas diecisiete fuentes no estaban fallando,
estaban estructuralmente impedidas de llegar.

Se agrega el rol `INFORMATIVO` para las secciones de esas páginas. No es una
parte de una norma y no puede confundirse con una: el publicador arma los
fragmentos citables filtrando por `DISPOSITIVO`, así que una sección
informativa nunca entra a un corte como texto de la ley. Se cita como «el
organismo dice X en su página», que es lo que efectivamente es.

Revision ID: 0015_lo_que_el_organismo_publica
Revises: 0014_identidad_en_la_bitacora
"""

from __future__ import annotations

from alembic import op

revision = "0015_lo_que_el_organismo_publica"
down_revision = "0014_identidad_en_la_bitacora"
branch_labels = None
depends_on = None

ROLES = (
    "DISPOSITIVO",
    "CITADO",
    "SUSTITUTIVO",
    "INCORPORADO",
    "HISTORICO",
    "NOTA",
    "INFORMATIVO",
)

RESTRICCION = "ck_unidades_documentales_rol_contenido_vocabulario"


def _check(roles: tuple[str, ...]) -> str:
    valores = ", ".join(f"'{r}'" for r in roles)
    return (
        f"ALTER TABLE unidades_documentales ADD CONSTRAINT {RESTRICCION} "
        f"CHECK (rol_contenido IN ({valores}))"
    )


def upgrade() -> None:
    op.execute(f"ALTER TABLE unidades_documentales DROP CONSTRAINT {RESTRICCION}")
    op.execute(_check(ROLES))
    op.execute(
        "COMMENT ON COLUMN unidades_documentales.rol_contenido IS "
        "'Qué es esta unidad dentro de su documento. INFORMATIVO es lo que un "
        "organismo publica sobre un derecho —sedes, canales, cronogramas—: se "
        "cita como dicho del organismo y nunca entra a un corte como texto de "
        "la norma, porque el publicador filtra por DISPOSITIVO.'"
    )


def downgrade() -> None:
    # Las unidades informativas no tienen equivalente en el vocabulario viejo.
    # Se borran en vez de reetiquetarlas: llamarlas NOTA las volvería parte de
    # una norma, que es exactamente lo que este rol vino a evitar.
    op.execute(
        "DELETE FROM evidencias WHERE unidad_id IN "
        " (SELECT id FROM unidades_documentales WHERE rol_contenido = 'INFORMATIVO')"
    )
    op.execute("DELETE FROM unidades_documentales WHERE rol_contenido = 'INFORMATIVO'")
    op.execute(f"ALTER TABLE unidades_documentales DROP CONSTRAINT {RESTRICCION}")
    op.execute(_check(ROLES[:-1]))
