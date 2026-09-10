# Grafo de relaciones normativas

- Relaciones: 527
- Normas con al menos una relación: 125
- Referencias pendientes de resolver: 215
- Autorreferencias: 0

## Ciclos (hasta 4 saltos)

Se encontraron **744** caminos que vuelven a su origen.

| Largo del ciclo | Caminos |
| ---: | ---: |
| 2 | 660 |
| 3 | 36 |
| 4 | 48 |

### Pares que se citan mutuamente

- **DECRETO 1134/2005** —CITA→ **LEY 24714/1996** —CITA→ vuelta
- **DECRETO 1134/2005** —SUSTITUYE→ **LEY 24714/1996** —CITA→ vuelta
- **DECRETO 1282/2013** —CITA→ **LEY 24714/1996** —CITA→ vuelta
- **DECRETO 1382/2001** —ABROGA→ **LEY 24714/1996** —CITA→ vuelta
- **DECRETO 1382/2001** —CITA→ **DECRETO 1407/2001** —CITA→ vuelta
- **DECRETO 1382/2001** —CITA→ **DECRETO 1407/2001** —INCORPORA→ vuelta
- **DECRETO 1382/2001** —CITA→ **LEY 24714/1996** —CITA→ vuelta
- **DECRETO 1382/2001** —DEROGA→ **DECRETO 2284/1991** —CITA→ vuelta
- **DECRETO 1382/2001** —DEROGA→ **LEY 24714/1996** —CITA→ vuelta
- **DECRETO 1388/2010** —CITA→ **LEY 24714/1996** —CITA→ vuelta

## Por qué esto no es una lista de errores

Un ciclo entre dos normas es normal: la que cita y la que después la modifica se nombran mutuamente. Borrar una de las dos relaciones para deshacer el ciclo perdería información real.

Lo que sí importa es que recorrer el grafo termine. `bn_grafo_normativo` lleva la lista de nodos visitados y un tope de profundidad, así que devuelve cada norma una vez, por el camino más corto que la alcanzó. Este informe existe para que el número de ciclos se conozca antes de escribir la primera consulta transitiva y no después.

## Qué no dice

Que las relaciones sean correctas. Dice cuántas hay y cómo se conectan, no que cada `DEROGA` derogue de verdad lo que dice derogar: eso lo sostiene la evidencia de cada relación, que se revisa aparte.

Tampoco dice que no haya ciclos más largos que 4 saltos. Se acota a propósito: en un grafo denso, buscar sin tope es una explosión combinatoria, y los ciclos que la práctica legislativa produce son cortos.
