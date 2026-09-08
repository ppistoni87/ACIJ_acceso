# Ensayo de actualización: diff, impacto y evento

Generado con `bn calidad ensayo-actualizacion`, sobre una base descartable.

## Qué es real y qué es controlado

Unidades reales extraídas de las capturas de D01, con la ruta que produjo la segmentación. El texto original y el actualizado del mismo decreto son dos estados verdaderos de la norma; lo controlado del ensayo es presentarlos como dos capturas sucesivas de una misma URL para ejercer diff, impacto y evento. El montaje está en el momento, no en el contenido.

- Norma: **Decreto 1382/2001**
- Fuente: D01 (InfoLEG)
- URL del texto actualizado: `https://www.argentina.gob.ar/normativa/nacional/norma-69649/actualizacion`
- SHA-256 de la captura: `e799f5b7bdbc789f90c4256fdb2c842ebccbccfa1e51a53444ff70caa77a9925`

## 1. Diferencia por unidad

El texto original tiene **105** unidades y el actualizado **108**.

| Clase | Unidades |
| --- | --- |
| AGREGADA | 4 |
| DESPLAZADA | 59 |
| ELIMINADA | 1 |
| MODIFICADA | 1 |

De esas, **59** son la misma unidad en otra ruta: al insertarse párrafos, el ordinal de las unidades sin número corre y todas las posteriores cambian de ruta sin que cambie una palabra. No cuentan como cambio de la norma.

Cambios sustantivos: **6**.

| Unidad | Clase | Similitud |
| --- | --- | --- |
| `titulo-II/articulo-12/parrafo-68` | AGREGADA | 0.0 |
| `titulo-II/articulo-4/parrafo-19` | AGREGADA | 0.0 |
| `titulo-II/articulo-4/parrafo-25` | ELIMINADA | 0.0 |
| `titulo-II/articulo-4/parrafo-26` | AGREGADA | 0.0 |
| `titulo-III/articulo-28/parrafo-106` | AGREGADA | 0.0 |
| `titulo-II/articulo-3` | MODIFICADA | 0.9302 |

La comparación es por unidad y solo sobre texto dispositivo: una nota editorial
o un token de formulario que cambie no produce un cambio de la norma.

## 2. Impacto

- Normas dependientes alcanzadas: **0**
- Beneficios afectados: **0**
- Reglas afectadas: **0**
- Versiones cuya frescura venció por el cambio: **1**

Vencer la frescura no deroga nada: impide seguir sirviendo un dato como actual
hasta que alguien lo verifique.

## 3. Evento

- Evento en el outbox: `6dbb73c1-3974-4844-a954-ef833b3c422f`
- Clave de idempotencia: `ensayo-actualizacion:be67b2bd-c2ea-4cc0-832b-82f9bc8ac947`
- Eventos tras repetir la misma propagación: **1**

Propagar el mismo cambio dos veces deja un solo evento. El evento queda en el
outbox y la API lo expone; sin proveedor de entrega configurado no se afirma que
se haya notificado a nadie.
