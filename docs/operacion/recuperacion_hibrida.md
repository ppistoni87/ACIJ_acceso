# Acta de la recuperación híbrida

Evidencia de P-012. Registra lo verificado contra el corpus real, incluido lo
que no cumple.

## Qué quedó construido

- **Índice semántico por corte.** `indices_semanticos` referencia el release y
  declara modelo, dimensión y normalización; `fragmento_vectores` cuelga de él y
  guarda el SHA-256 del texto que embebió. Que la recuperación no devuelva
  contenido fuera del corte no queda librado a que la consulta se acuerde de
  filtrar: no hay dónde guardar un vector que no pertenezca a un corte.
- **Un índice, un modelo.** Los vectores cuelgan del índice y no del fragmento.
  Dos modelos distintos ponen el mismo texto en lugares distintos del espacio, y
  una distancia entre vectores de modelos distintos no significa nada; con esta
  forma no pueden convivir en la misma tabla.
- **Búsqueda híbrida con fusión por rango recíproco.** `ts_rank` no tiene unidad
  y la distancia coseno va de 0 a 2: sumarlas exige inventar una normalización
  que termina siendo el verdadero criterio de orden sin que nadie la haya
  elegido. RRF usa solo el orden, `1/(k+puesto)` con k=60.
- **Los filtros van adentro de cada mitad, no encima del resultado.** Corte,
  jurisdicción, beneficio y temporalidad —`as_of` contra el rango de aplicación,
  `known_at` contra la ventana de conocimiento— se aplican en las dos búsquedas
  antes de fusionar. Filtrar después haría que las dos gastaran sus lugares en
  fragmentos que van a descartarse.
- **Reconstruir es barato.** El hash del texto decide qué se vuelve a embeber: un
  fragmento cuyo texto cambió deja su vector marcado como viejo en vez de servir
  una respuesta desactualizada.
- **El modelo es un extra, no una dependencia.** El backend sirve datos tipados,
  publica cortes y contesta la API sin ningún modelo. `pip install -e '.[rag]'`
  agrega la recuperación semántica; sin él la mitad léxica sirve sola **y la
  respuesta lo declara**, porque una respuesta peor que la que el sistema puede
  dar tiene que decirse o parece la mejor posible.

## El índice léxico nunca sirvió a la consulta que la API corre

`ix_chunks_fts` estaba sobre la expresión `to_tsvector('spanish', texto)` y la
API filtra por la columna `tsv`, que es otra cosa: PostgreSQL solo usa un índice
de expresión cuando la consulta trae esa misma expresión. Comprobado forzando
`enable_seqscan = off`, que igual daba recorrido secuencial: el índice no podía
usarse, con 66 filas o con seis millones.

Y `tsv` la escribía el publicador a mano, así que además podía quedar distinta
del texto que decía representar. Desde la migración 0013 es columna generada y
el índice GIN está sobre la columna. El plan de la misma consulta pasó a
`Bitmap Heap Scan`.

## La medición, con el resultado que dio

Conjunto congelado en `docs/calidad/recuperacion.json`: 27 preguntas escritas
leyendo el texto de los artículos publicados y a propósito con las palabras de
quien consulta, no con las de la norma. El hash cubre id, consulta y respuesta
esperada, y `bn recuperacion evaluar` falla si no coincide: cambiar una pregunta
obliga a volver a congelar en el mismo commit y el cambio queda visible.

| k | Léxica sola | Híbrida | Diferencia |
| ---: | ---: | ---: | ---: |
| 1 | 0,0 % | 33,3 % | +33,3 % |
| 3 | 0,0 % | 51,9 % | +51,9 % |
| 5 | 0,0 % | **74,1 %** | +74,1 % |

**El umbral del plan es Recall@5 ≥ 90 %. No se cumple.**

Dos lecturas sobre ese cero de la mitad léxica. Es real —se verificó que la
búsqueda léxica funciona: «prestación económica mensual» devuelve el Art. 3 en
primer lugar—, y es el resultado de un conjunto escrito para ser adverso a ella.
No dice que la búsqueda de texto sirva para poco en general; dice que de las 27
preguntas que una persona haría con sus palabras, la mitad léxica no contesta
ninguna y la híbrida contesta veinte.

## Por qué no llega a 90: once de los treinta y tres fragmentos no eran la norma

Fallan 7 de 27 preguntas. En 5 de esas 7, los primeros cinco puestos los ocupa
texto que no es de la norma: el panel de **«Relaciones»** que la ficha de
NormativaBA muestra al pie —«Tipo de relación», «Norma relacionada», «Detalle»,
«INTEGRA», «COMPLEMENTA», «PROMULGADA POR DECRETO 495 2025»— más dos resúmenes
que la propia página redacta, con sus etiquetas `<p>` adentro.

Medido: **47 de 135 puestos devueltos (34,8 %)** los ocupaba texto de la página y
no de la ley.

No es ruido inofensivo. Esos fragmentos se publicaron como texto **citable**, así
que una respuesta podía citar «Tipo de relación» o «INTEGRA» como si fuera la
ley. El problema de recuperación es el síntoma; el defecto es que se publicó
como norma algo que no lo es.

La causa: el adaptador sabía dónde **empieza** el articulado y no dónde
**termina**, así que se llevaba todo lo que la ficha muestra debajo. Corregido:
corta por el encabezado del panel, que es una estructura de la ficha y no una
palabra suelta del texto, y **no recorta en silencio** —deja aviso con cuántos
párrafos quedaron afuera, para que un cambio de maquetación que se coma
articulado se vea en vez de aparecer como una norma más corta—.

Al volver a extraer, la Ley 6935 pasó de 33 unidades a 22. Las otras fichas
porteñas descartaron entre 10 y 47 párrafos cada una.

## Lo que este acta no acredita

- **La medición sigue siendo sobre el corte viejo.** La extracción corregida
  existe y está probada, pero el release publicado se construyó con la anterior y
  todavía sirve los once fragmentos del panel. Promoverla no es correr un
  comando: las citas curadas apuntan a las unidades de la versión vieja, y el
  sistema se niega a reprocesarla —«rehacer la segmentación borraría las unidades
  que esas citas localizan, y una cita que apunta a una unidad que ya no existe
  no se puede verificar»—. Volver a curar es trabajo jurídico. **Hasta que eso
  pase, el 74,1 % es el número, y volver a medir sobre un corte limpio es lo
  primero que hay que hacer después.**
- **El denominador es chico.** 33 fragmentos indexados de un solo corte, porque
  es lo único publicado. Con un corpus así, un Recall@5 alto acreditaría poco:
  cinco lugares sobre treinta y tres es el 15 % del corpus. El número se vuelve
  informativo cuando haya más corte publicado, y eso depende de P-010.
- **El modelo por omisión se eligió por tamaño, no por calidad.**
  `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensiones, unos 220 MB: entra en
  el CI. Para producción conviene medir contra uno más grande —`multilingual-e5-large`
  es el candidato— y el esquema lo contempla: cambiar de modelo es construir otro
  índice, y si cambia la dimensión, una migración.
- **pgvector no es la misma versión en los dos lados.** 0.6.0 en el PostgreSQL
  local y del CI, 0.8.6 en Neon. El índice HNSW existe en las dos; las
  diferencias de recorrido de las versiones nuevas no están medidas.
- **No hay generación.** P-012 entrega contexto recuperado y trazado. Redactar
  una respuesta con citas y abstenerse cuando falta evidencia es P-013, y no
  tiene proveedor de modelo configurado.
