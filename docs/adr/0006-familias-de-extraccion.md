# ADR 0006 · Familias de extracción y segmentación

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

El inventario tiene 83 fuentes con seis técnicas distintas. La especificación
prohíbe explícitamente resolverlo con un script por fuente: "no crear 67 scripts
aislados con copias divergentes del mismo parser".

## Decisión

1. **Un adaptador por familia técnica**, con un contrato común
   (`CapturaMaterial` → `ResultadoExtraccion`). Los contratos específicos por
   fuente viven en `selector_config`, versionado junto con la configuración.
2. **Los adaptadores no acceden a la red.** Trabajan sobre bytes ya capturados.
   Con la misma captura y la misma versión de extractor, el resultado es el
   mismo, y eso es lo que hace la extracción auditable.
3. **La segmentación es una capa aparte y compartida.** Lo difícil no es partir
   el texto en artículos: es no confundir un artículo dispositivo con el texto
   de otro artículo transcripto dentro de él.
4. **El segmentador informa en vez de adivinar.** Usa tres señales para decidir
   que un marcador no abre una unidad nueva: el artículo en curso nombra
   explícitamente el número que sustituye, la numeración no avanza, o el
   párrafo viene entrecomillado. Cuando las señales se contradicen, marca la
   unidad como ambigua y emite un aviso que abre una incidencia.
5. **La codificación se resuelve al decodificar, no en cada adaptador.** Varios
   boletines siguen sirviendo `cp1252`, y una tilde corrompida en "Artículo"
   hace que el segmentador pierda la unidad entera.
6. **Original, actualizado y consolidado son versiones distintas.** La ruta o el
   marcado dicen cuál es cada una; si la URL y el marcado se contradicen, se
   registra en vez de elegir en silencio.
7. **Las etiquetas de la fuente se conservan como declaradas.** El "Estado:
   No vigente" de NormativaBA es un dato del boletín, no la conclusión del
   sistema. Igual la "Nota Infoleg": lleva información valiosa de vigencia, pero
   es del editor, y se guarda con rol propio.
8. **El texto no clasificado queda visible.** El control DQ06 mide la cobertura
   y abre incidencia por debajo del 60%: publicar sobre una versión con texto
   sin unidad asignada sería publicar sobre un texto incompleto.
9. **Las URLs descubiertas entran como candidatas, no como fuentes.** Que un
   texto enlace a otra norma no prueba que esa norma sea del alcance ni qué
   relación jurídica tienen.

## Consecuencias

- Sumar una fuente de una familia ya cubierta es configuración, no código.
- Sumar una familia nueva es una clase con dos métodos y su archivo de pruebas.
- Los avisos del segmentador generan trabajo de revisión real. Es deliberado:
  el costo de revisar una ambigüedad es mucho menor que el de aplicar una
  reforma sobre el artículo equivocado.
