# Anclas de las referencias con fragmento

Un alias con `#` promete llevar a un lugar puntual de la página destino. La página
carga igual cuando el ancla no existe, así que el error no se ve: hay que comprobarlo.

- Referencias con fragmento: **1**
- Resueltas: **0** · rotas: **1** · sin captura del destino: **0**

| Fuente | Destino | Ancla | Estado | Anclas en el destino | Detalle |
| --- | --- | --- | --- | --- | --- |
| F28 | F31 | `44` | ROTA | 129 | El ancla «44» no existe entre las 129 de la captura de F31. El alias se conserva; la referencia no lleva a ninguna parte. Parecidos no usados: `accordion-2693944`, `accordion-item-2693944`. |

## Por qué un ancla rota no se arregla sola

Resolver `#44` por el ancla que contiene «44», o por la pregunta que está en el lugar
44, pone una respuesta arbitraria donde había una referencia precisa. El alias se
conserva y la rotura se reporta con responsable: la referencia correcta la consigue
alguien que mire el destino, no una heurística de dígitos.
