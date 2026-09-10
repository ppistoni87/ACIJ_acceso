"""Recorrer el grafo de relaciones sin quedarse dando vueltas.

El criterio 2 de P-007 pide que resolver referencias evite la recursión
infinita. Hoy se cumple por omisión: ninguna consulta recorre el grafo más de
un salto. Eso alcanza mientras nadie escriba la primera consulta transitiva
—«qué normas afectan a esta»—, que es justo lo que la recuperación va a
necesitar. Y el grafo real tiene ciclos: en este corpus, 744 caminos de a lo
sumo seis saltos vuelven a su origen.

Los ciclos no son un error de los datos. La Ordenanza 43.478 cita a la Ley 547,
y la Ley 547 modifica la Ordenanza 43.478: ninguna de las dos relaciones sobra.
Lo que no puede pasar es que recorrerlas no termine.

Se agregan dos cosas:

* `bn_grafo_normativo`, que recorre con una lista de visitados y un tope de
  profundidad. Cada norma aparece una vez, por el camino más corto con el que
  se la alcanzó.
* Un `CHECK` contra la autorreferencia. El resolutor ya las omite —91 en la
  última corrida— pero el esquema las admitía, y una norma que se cita a sí
  misma es el ciclo más corto posible. Hoy no hay ninguna en la base, así que
  la restricción entra sin migrar datos.

Revision ID: 0010_grafo_sin_recursion
Revises: 0009_evidencia_no_recuperable
"""

from __future__ import annotations

from alembic import op

revision = "0010_grafo_sin_recursion"
down_revision = "0009_evidencia_no_recuperable"
branch_labels = None
depends_on = None

FUNCION = """
CREATE OR REPLACE FUNCTION bn_grafo_normativo(
    p_norma_id uuid,
    p_profundidad_max int DEFAULT 4,
    p_sentido text DEFAULT 'SALIENTE'
)
RETURNS TABLE (
    norma_id uuid,
    profundidad int,
    camino uuid[],
    tipos text[]
)
LANGUAGE sql
STABLE
AS $$
    WITH RECURSIVE aristas AS (
        -- Un solo lugar donde se decide la dirección: repetir el recorrido una
        -- vez por sentido invita a que los dos se separen con el tiempo.
        SELECT norma_origen_id AS desde, norma_destino_id AS hasta, tipo
          FROM relaciones_normativas
         WHERE p_sentido IN ('SALIENTE', 'AMBOS')
        UNION ALL
        SELECT norma_destino_id AS desde, norma_origen_id AS hasta, tipo
          FROM relaciones_normativas
         WHERE p_sentido IN ('ENTRANTE', 'AMBOS')
    ),
    recorrido AS (
        SELECT a.hasta AS norma_id,
               1 AS profundidad,
               ARRAY[p_norma_id, a.hasta] AS camino,
               ARRAY[a.tipo::text] AS tipos
          FROM aristas a
         WHERE a.desde = p_norma_id
           AND a.hasta <> p_norma_id
        UNION ALL
        SELECT a.hasta,
               r.profundidad + 1,
               r.camino || a.hasta,
               r.tipos || a.tipo::text
          FROM recorrido r
          JOIN aristas a ON a.desde = r.norma_id
         WHERE r.profundidad < p_profundidad_max
           -- Lo que hace que termine: no se vuelve a un nodo ya visitado en
           -- este camino. Sin esto, la Ordenanza 43.478 y la Ley 547 se
           -- devuelven la pelota hasta agotar la memoria.
           AND NOT a.hasta = ANY(r.camino)
    )
    SELECT DISTINCT ON (norma_id) norma_id, profundidad, camino, tipos
      FROM recorrido
     ORDER BY norma_id, profundidad, camino;
$$;

COMMENT ON FUNCTION bn_grafo_normativo(uuid, int, text) IS
    'Normas alcanzables desde una, sin repetir nodos y con tope de profundidad. '
    'Cada norma aparece una vez, por el camino más corto que la alcanzó. Los '
    'ciclos del grafo son legítimos: lo que no puede es no terminar.';
"""


def upgrade() -> None:
    op.execute(
        "ALTER TABLE relaciones_normativas "
        "ADD CONSTRAINT ck_relaciones_normativas_sin_autorreferencia "
        "CHECK (norma_origen_id <> norma_destino_id)"
    )
    op.execute(FUNCION)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS bn_grafo_normativo(uuid, int, text)")
    op.execute(
        "ALTER TABLE relaciones_normativas "
        "DROP CONSTRAINT IF EXISTS ck_relaciones_normativas_sin_autorreferencia"
    )
