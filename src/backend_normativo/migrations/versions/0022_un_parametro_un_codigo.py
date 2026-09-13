"""Un parámetro, un código: las reglas citaban unos y los valores vivían en otros.

Las 99 reglas ejecutables citan ocho códigos de parámetro. Los únicos tres
parámetros con valores cargados son otros tres. La intersección es vacía, así que
**ninguna regla podía resolver su umbral en ninguna fecha**, y una condición sin
umbral queda en desconocido: por eso ningún beneficio concluía.

El caso más caro es el salario mínimo. El importador de montos lo escribe como
`SMVM` —está declarado así en `catalogo/derivacion.py`, `COLUMNAS_DE_MONTOS`— y
las lecturas curadas lo citan como `AR.SMVM`, siguiendo la convención con
prefijo de jurisdicción que usan todos los demás (`AR.CBA`, `CABA.SUELDO-MINIMO`,
`INDEC.CBT`). Son la misma magnitud con dos nombres, y ninguno de los dos lados
sabía del otro.

Se unifica en la forma con prefijo, que es la que usan las lecturas y la que
distingue el salario mínimo nacional de uno provincial. Los valores se mueven al
parámetro canónico y el duplicado se borra; `AR.SALARIO-MINIMO-VITAL-Y-MOVIL`,
que una sola lectura usaba, también se pliega a `AR.SMVM`.

Esto no inventa ningún monto. Los valores que se mueven son los tres que ya
estaban capturados del Consejo del Salario, con su evidencia. Lo que cambia es
que ahora una regla puede alcanzarlos.

Revision ID: 0022_un_parametro_un_codigo
Revises: 0021_un_corte_es_la_foto
"""

from __future__ import annotations

from alembic import op

revision = "0022_un_parametro_un_codigo"
down_revision = "0021_un_corte_es_la_foto"
branch_labels = None
depends_on = None


# viejo -> canónico. El canónico puede existir ya (lo crearon las lecturas) o no.
UNIFICAR = {
    "SMVM": "AR.SMVM",
    "AR.SALARIO-MINIMO-VITAL-Y-MOVIL": "AR.SMVM",
    "PRESTACION_DESEMPLEO_MINIMO": "AR.PRESTACION-DESEMPLEO-MINIMO",
    "PRESTACION_DESEMPLEO_MAXIMO": "AR.PRESTACION-DESEMPLEO-MAXIMO",
    "BECA_PROGRESAR": "AR.BECA-PROGRESAR",
}

# Mueve lo que cuelgue del viejo al canónico y borra el viejo. Si el canónico no
# existe, alcanza con renombrar. `ON CONFLICT DO NOTHING` en las tablas puente:
# una regla que ya citaba el canónico no se duplica.
FUNDIR = """
DO $$
DECLARE
    viejo uuid;
    canonico uuid;
BEGIN
    SELECT id INTO viejo FROM parametros WHERE codigo = :viejo;
    IF viejo IS NULL THEN
        RETURN;
    END IF;
    SELECT id INTO canonico FROM parametros WHERE codigo = :canonico;
    IF canonico IS NULL THEN
        UPDATE parametros SET codigo = :canonico WHERE id = viejo;
        RETURN;
    END IF;
    UPDATE parametro_valores SET parametro_id = canonico WHERE parametro_id = viejo;
    UPDATE tramite_versiones SET costo_parametro_id = canonico WHERE costo_parametro_id = viejo;
    INSERT INTO regla_parametros (regla_id, parametro_id, rol)
        SELECT regla_id, canonico, rol FROM regla_parametros WHERE parametro_id = viejo
        ON CONFLICT DO NOTHING;
    DELETE FROM regla_parametros WHERE parametro_id = viejo;
    INSERT INTO cuantia_parametros (cuantia_id, parametro_id, rol)
        SELECT cuantia_id, canonico, rol FROM cuantia_parametros WHERE parametro_id = viejo
        ON CONFLICT DO NOTHING;
    DELETE FROM cuantia_parametros WHERE parametro_id = viejo;
    DELETE FROM parametros WHERE id = viejo;
END $$;
"""


def upgrade() -> None:
    for viejo, canonico in UNIFICAR.items():
        op.execute(FUNDIR.replace(":viejo", f"'{viejo}'").replace(":canonico", f"'{canonico}'"))


def downgrade() -> None:
    """No se deshace: fundir dos parámetros pierde de cuál venía cada valor.

    Volver atrás exigiría saber qué valor había entrado por qué código, y eso no
    se guardó porque nunca debieron ser dos códigos.
    """
    raise NotImplementedError(
        "0022 funde parámetros duplicados: deshacerlo exigiría saber de cuál venía cada valor."
    )
