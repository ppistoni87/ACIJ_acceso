# Conciliación de la ingesta

Cada fila que un importador leyó terminó en algún lado: se creó, ya estaba, o se rechazó con motivo. La identidad que se comprueba es
`leidas = nuevas + repetidas + rechazadas`; `actualizadas` es el subconjunto de repetidas que además cambió, y por eso no entra en la suma.

| Fuente | Importador | Leídas | Nuevas | Repetidas | Actualizadas | Rechazadas | Cierra |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| F01 | catalogo_infoleg | 428380 | 0 | 428380 | 8860 | 0 | sí |
| F20 | directorio | 21 | 0 | 21 | 0 | 0 | sí |
| F39 | padron_renabap | 6467 | 0 | 6467 | 0 | 0 | sí |
| F44 | dpn | 57 | 0 | 57 | 0 | 0 | sí |
| F60 | directorio | 229 | 0 | 229 | 0 | 0 | sí |

## Sobre las filas que sí entraron

No son rechazos: describen algo de lo que entró y por eso no restan de la suma.

- **F01** (catalogo_infoleg) — homonimas: 6561, identidad_incierta: 322331, sin_numero: 142, sin_texto: 235489
- **F20** (directorio) — coordenadas_sin_crs: 21
- **F44** (dpn) — alcance_sin_declarar: 38, correos_no_tomados: 55
- **F60** (directorio) — literales_sin_dato: 153

## Qué no dice

Que lo importado sea correcto. Dice que el importador dio cuenta de cada fila que leyó, no que haya interpretado bien lo que leyó.

Tampoco dice que la fuente tuviera esas filas y no más: si la página paginó y el adaptador leyó una sola página, la conciliación cierra igual sobre lo que leyó. Eso lo cubre la historia de cada fuente, no esto.
