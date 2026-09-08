# ADR 0007 · Identidad de normas y construcción de relaciones

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

La identidad jurídica es jurisdicción + emisor + tipo + número + año, con los
identificadores oficiales alternativos conservados. El corpus llega en piezas:
la ficha de una norma trae la identidad y las fechas, y las vistas de texto solo
traen el identificador de la fuente. Además, un mismo texto cita otras normas y
esas citas son dependencias que hay que resolver.

## Decisión

1. **No se fusiona por parecido.** La búsqueda por clave canónica solo corre
   cuando la clave está completa. Con la clave incompleta, la norma queda en
   staging con `identidad_incierta` y una incidencia abierta.
2. **Completar no es sobrescribir.** Si una norma incierta recibe después la
   identidad completa desde otra vista de la misma fuente, se completa la que ya
   existe y la incidencia se resuelve con su rastro. Si la identidad ya estaba
   completa y otra vista dice algo distinto, es un conflicto para revisión: se
   registran ambos candidatos y no se toca la registrada.
3. **La versión nace sin vigencia resuelta.** `valid_tipo = DESCONOCIDO` aunque
   se conozca la publicación. Que una norma se haya publicado no dice hasta
   cuándo rige, y `DESCONOCIDO` no produce rango aplicable: la versión no se
   sirve hasta que alguien fundamente su vigencia.
4. **`estado_legal_declarado` y `estado_legal_validado` son campos distintos.**
   Lo que dice la fuente se guarda como declarado; el validado arranca en
   `NO_DETERMINADA` y solo cambia con fundamento.
5. **La dirección de una relación depende de la voz del verbo.** "Abrogada por
   el Decreto 1382/01" pone al decreto como origen; "Deróganse la Ley 18.017"
   pone como origen a la norma que lo dice. Invertirlas haría que el corpus
   afirme lo contrario de lo que dice la fuente.
6. **Citar no es modificar.** Cuando el contexto no permite decidir, la relación
   es `CITA` y nada más.
7. **Toda relación nace candidata y con evidencia localizable**, apuntando a la
   unidad concreta y no a la norma entera.
8. **Una cita sin destino identificado queda pendiente**, con su texto literal,
   la identidad candidata y la relación sugerida. No se inventa un destino ni se
   busca en otra jurisdicción: una ordenanza citada en una norma de CABA es de
   CABA.
9. **Las relaciones derivadas de una nota editorial lo declaran en su alcance.**
   La nota lleva información valiosa de vigencia pero es del editor del boletín,
   no de la norma.

## Consecuencias

- El caso F33 queda representado como es: el grafo tiene a la vez que el Decreto
  1382/01 abroga la Ley 24.714 y que el Decreto 1604/2001 restablece su
  vigencia, y la ley no queda clasificada por la primera palabra de la nota.
- Las referencias pendientes son trabajo real de curación. Es deliberado: son
  las dependencias que faltan para completar el corpus, y esconderlas daría una
  cobertura falsa.
- Reejecutar la curación es idempotente. La unicidad de una arista usa
  `NULLS NOT DISTINCT` porque una relación de alcance general deja las unidades
  en nulo, y con la semántica por defecto cada corrida crearía una arista nueva.
