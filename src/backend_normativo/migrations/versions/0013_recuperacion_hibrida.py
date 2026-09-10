"""Recuperación híbrida: el índice semántico del corte, y un índice léxico que sirva.

P-012 criterio 1. Un corte publicado se indexa por unidad, y cada vector guarda
con qué modelo se calculó, de cuántas dimensiones y sobre qué texto. Sin esas
tres cosas un vector es un número sin procedencia: no se puede saber si quedó
viejo porque cambió el texto, ni si se puede comparar con el de al lado.

Tres cosas que este esquema decide.

**El índice pertenece a un corte.** `indices_semanticos` referencia el release.
Que la recuperación no devuelva contenido fuera del corte no queda entonces
librado a que la consulta se acuerde de filtrar: no hay dónde guardar un vector
que no pertenezca a un corte.

**Un índice, un modelo.** Los vectores cuelgan del índice y no del fragmento, y
el índice declara su modelo y su dimensión. Cambiar de modelo es construir otro
índice, no mezclar vectores nuevos con viejos en la misma tabla —dos modelos
distintos ponen el mismo texto en lugares distintos del espacio, y una distancia
entre dos de esos vectores no significa nada—.

**El índice léxico nunca sirvió a la consulta que la API corre.** `ix_chunks_fts`
estaba sobre la expresión `to_tsvector('spanish', texto)` y la API filtra por la
columna `tsv`, que es otra cosa: PostgreSQL solo usa un índice de expresión
cuando la consulta trae esa misma expresión. Comprobado con `enable_seqscan =
off`, que igual da recorrido secuencial: el índice no podía usarse. Y `tsv` la
escribía el publicador a mano, así que además podía quedar distinta del texto.

Se arregla de una sola forma: `tsv` pasa a ser columna generada a partir de
`texto` —no puede desincronizarse porque no la escribe nadie— y el índice GIN
pasa a estar sobre la columna. Recién ahí la mitad léxica del híbrido tiene un
índice que la sostiene.

Se van también `modelo_embedding` y `embedding_ref`, dos columnas de texto del
esquema inicial que nadie escribió nunca y que ahora dirían, mal, lo que
`indices_semanticos` dice bien.

Revision ID: 0013_recuperacion_hibrida
Revises: 0012_un_ciclo_por_vez
"""

from __future__ import annotations

from alembic import op

revision = "0013_recuperacion_hibrida"
down_revision = "0012_un_ciclo_por_vez"
branch_labels = None
depends_on = None

# El modelo por omisión es multilingüe y chico: entra en el CI sin volverlo
# lento. La dimensión vive en el tipo de la columna porque pgvector la exige
# ahí; cambiar a un modelo de otra dimensión es una migración, y que lo sea
# está bien: es un cambio de esquema, no de configuración.
DIMENSION = 384

LEXICO = """
ALTER TABLE chunks DROP COLUMN modelo_embedding;
ALTER TABLE chunks DROP COLUMN embedding_ref;

DROP INDEX ix_chunks_fts;
ALTER TABLE chunks DROP COLUMN tsv;
ALTER TABLE chunks ADD COLUMN tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED;
CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv);

COMMENT ON COLUMN chunks.tsv IS
    'Generada a partir de texto. No la escribe nadie: antes la escribía el '
    'publicador y podía quedar distinta del texto que decía representar.';
"""

SEMANTICO = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE indices_semanticos (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    release_id    uuid NOT NULL REFERENCES releases(id) ON DELETE RESTRICT,
    modelo        varchar(120) NOT NULL,
    dimension     integer NOT NULL,
    normalizacion varchar(16) NOT NULL,
    construido_en timestamptz NOT NULL DEFAULT now(),
    fragmentos    integer NOT NULL DEFAULT 0,
    CONSTRAINT uq_indice_release_modelo UNIQUE (release_id, modelo),
    CONSTRAINT ck_indice_dimension CHECK (dimension = {DIMENSION}),
    CONSTRAINT ck_indice_normalizacion CHECK (normalizacion IN ('L2', 'NINGUNA')),
    CONSTRAINT ck_indice_fragmentos CHECK (fragmentos >= 0)
);

CREATE TABLE fragmento_vectores (
    indice_id  uuid NOT NULL REFERENCES indices_semanticos(id) ON DELETE CASCADE,
    chunk_id   uuid NOT NULL REFERENCES chunks(id) ON DELETE RESTRICT,
    hash_texto varchar(64) NOT NULL,
    vector     vector({DIMENSION}) NOT NULL,
    PRIMARY KEY (indice_id, chunk_id),
    CONSTRAINT ck_fragmento_vector_hash_hex CHECK (hash_texto ~ '^[0-9a-f]{{64}}$')
);

CREATE INDEX ix_fragmento_vectores_hnsw
    ON fragmento_vectores USING hnsw (vector vector_cosine_ops);

COMMENT ON TABLE indices_semanticos IS
    'Un índice semántico por corte y modelo. Los vectores cuelgan de acá y no '
    'del fragmento para que no convivan dos modelos en la misma tabla: la '
    'distancia entre vectores de modelos distintos no significa nada.';
COMMENT ON COLUMN fragmento_vectores.hash_texto IS
    'SHA-256 del texto que se embebió. Si el fragmento cambia, el vector queda '
    'viejo y se nota comparando, en vez de servir una respuesta desactualizada.';
"""

# La API lee el índice; no lo construye. Construirlo es del publicador, porque
# un índice pertenece a un corte. Se le da DELETE sobre las dos tablas —y solo
# sobre estas dos— porque son datos derivados: se reconstruyen del texto
# publicado y borrarlos no pierde ninguna evidencia.
PERMISOS = """
GRANT SELECT ON indices_semanticos, fragmento_vectores TO bn_lector_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON indices_semanticos, fragmento_vectores TO bn_publicador;
"""


def upgrade() -> None:
    op.execute(LEXICO)
    op.execute(SEMANTICO)
    op.execute(PERMISOS)


def downgrade() -> None:
    op.execute("DROP TABLE fragmento_vectores")
    op.execute("DROP TABLE indices_semanticos")
    op.execute("DROP INDEX ix_chunks_tsv")
    op.execute("ALTER TABLE chunks DROP COLUMN tsv")
    op.execute("ALTER TABLE chunks ADD COLUMN tsv tsvector")
    op.execute("UPDATE chunks SET tsv = to_tsvector('spanish', texto)")
    op.execute("CREATE INDEX ix_chunks_fts ON chunks USING gin (to_tsvector('spanish', texto))")
    op.execute("ALTER TABLE chunks ADD COLUMN modelo_embedding text")
    op.execute("ALTER TABLE chunks ADD COLUMN embedding_ref text")
