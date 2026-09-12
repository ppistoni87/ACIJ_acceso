# Determinación de vigencia de las normas del alcance

12 de septiembre de 2026 · actor registrado: `curacion_juridica:agente (sin
firma jurídica designada, D-130)`.

Esto **no es una firma jurídica**. Es una determinación hecha sobre los
documentos capturados, bajo la decisión de producto de proceder sin un
responsable jurídico designado (D-130). Cada resolución quedó en
`incidencias_revision` con su fundamento completo y un evento en la bitácora.
Todo lo de acá es corregible y está escrito para que se pueda discutir punto por
punto.

## Regla general aplicada

**Art. 5 del Código Civil y Comercial** (y **art. 2 del Código Civil**, t.o. Ley
16.504, para las normas anteriores a 2015, de idéntico contenido en cuanto al
plazo): la norma rige a los ocho días corridos de su publicación oficial, salvo
que designe otro tiempo. Se revisó el texto capturado de cada norma buscando
cláusulas de entrada en vigencia —«entrará en vigencia», «regirá desde»,
«comenzará a regir»— y ninguna de las resueltas fija fecha propia, así que en
todas rige el plazo supletorio.

Hay una discusión doctrinaria sobre si el plazo se cuenta como ocho o nueve días
corridos. Se tomó **publicación + 8 días** y se deja dicho: para toda consulta
posterior a la semana de publicación la diferencia no cambia ninguna respuesta,
y ninguna de estas normas es de 2026.

## Normas resueltas

| Norma | Publicación | Rige desde | Tipo | Estado legal |
| --- | --- | --- | --- | --- |
| ORDENANZA 43478/1989 | 07/02/1989 | 15/02/1989 | ABIERTO_FIN | VIGENTE |
| LEY 547/2001 | 24/04/2001 | 02/05/2001 | ABIERTO_FIN | VIGENTE |
| DECRETO 690/2006 | 21/06/2006 | 29/06/2006 | **CONDICIONADO** | CONDICIONADA |
| LEY 2917/2008 (×2) | 06/03/2009 | 14/03/2009 | ABIERTO_FIN | VIGENTE |
| DECRETO 75/2015 | 17/03/2015 | 25/03/2015 | ABIERTO_FIN | VIGENTE |
| RESOLUCION 1621/2025 | 19/12/2025 | 27/12/2025 | ABIERTO_FIN | VIGENTE |
| LEY 24714/1996 (×2) | *no capturada* | 16/10/1996 | ABIERTO_FIN | **VIGENCIA_PARCIAL** |

### Los tres casos que no eran mecánicos

**LEY 547/2001 — la fuente la etiqueta «no vigente» y sí rige.** Esa marca del
Digesto corresponde a una norma modificatoria consumida por incorporación, no a
la pérdida de eficacia de su contenido. Sus artículos 1 y 2 sustituyeron los
artículos 10 y 16 de la Ordenanza 43478 —los que fijan los topes de ingreso, el
incremento del 15 % por cada niño que se suma y la deducción de gastos por
enfermedad crónica—, que son el derecho aplicable hoy para la beca de comedor.
Tratarla como no vigente ocultaría los criterios actuales del beneficio.

**DECRETO 690/2006 — no está derogado y no puede declararse abierto.** La Ley
6935/2025, ya publicada y en el corte, dice en su artículo 1 que el programa
nuevo «es continuador del establecido por el Decreto 690/06, y se regirá
exclusivamente por las disposiciones de la presente Ley», y su cláusula
transitoria que «hasta la publicación de reglamentación de la presente Ley,
serán de aplicación las disposiciones del Decreto 690/06». Su aplicación depende
de un hecho externo que el corpus no registra: si esa reglamentación ya salió.
Queda **CONDICIONADO**, que es la forma de decirlo sin mentir en ninguna de las
dos direcciones, y con eso no entra a un corte publicado: el servicio no va a
servir como vigentes los requisitos del decreto viejo. **Para destrabarlo hay
que verificar en el Boletín Oficial de CABA si la reglamentación de la Ley 6935
fue publicada.**

**LEY 24714/1996 — derogada y restituida, con una excepción.** Es la norma de la
que cuelgan 12 de los 16 beneficios, así que vale el detalle:

1. El **Decreto 1382/2001** la derogó en términos totales: «Derógase la Ley Nº
   24.714 sus modificatorias y el artículo 89 del Decreto Nº 2284/91».
2. El **Decreto 1604/2001, artículo 1** restituyó su vigencia de forma
   retroactiva: «Restitúyese, **desde la fecha de su derogación**, la vigencia
   del artículo 89 del Decreto Nº 2284/91 y de la Ley Nº 24.714, con excepción
   de las normas correspondientes a las prestaciones a las que refiere el tercer
   párrafo del artículo 26 del Decreto Nº 1382/01». Al ser desde la fecha de la
   derogación, no hay período sin vigencia.
3. El artículo 26 del Decreto 1382/01, **tal como está capturado**, regula las
   prestaciones del SIPROF y no las asignaciones familiares. El tercer párrafo
   que la excepción menciona no aparece en la captura. Por eso el estado legal
   es VIGENCIA_PARCIAL y no VIGENTE: la excepción existe y no se pudo acotar.
4. Las incorporaciones posteriores registradas —Decreto 1602/2009 con 21
   (Asignación Universal por Hijo), Decreto 446/2011 con 12 y Decreto 504/2015
   con 3— cambian su contenido y no cierran su vigencia.

**Lo que no se pudo verificar de esta norma.** El corpus registra relaciones
DEROGA de la **Ley 27260/2016** y del **Decreto 1039/2024** contra ella, sin el
texto de origen capturado: no consta su alcance. La determinación asume que son
derogaciones de artículos y no de la ley entera. Si alguna fuera total, esta
determinación queda sin efecto y con ella los 12 beneficios nacionales. **Es lo
primero que hay que verificar contra la fuente.**

**Y la fecha de inicio no es exacta.** El documento capturado trae la
promulgación (16/10/1996) y no la publicación oficial. Se tomó la promulgación
dejando dicho que es un piso: la fecha real está entre esa y unos diez días
después. Para cualquier consulta posterior a 1996 no cambia nada, y se corrige
cuando la ingesta capture la fecha de publicación.

## Vigencia de los beneficios: derivada, no inventada

Un beneficio no tiene vigencia propia: existe porque una norma lo crea y
mientras esa norma rija. Las que lo reglamentan o lo modifican cambian su
contenido —requisitos, montos, procedimiento— y no su existencia. La política
`vigencia-derivada-del-beneficio@1` mira sólo las normas con rol CREA y es
conservadora: si la creadora no está resuelta, el beneficio tampoco.

Con las normas de arriba resueltas, los 16 beneficios quedaron con intervalo:
**15 abiertos** y **1 condicionado** (el subsidio de situación de calle, que
hereda la condición del Decreto 690/06).

## Lo que sigue bloqueado, y por qué

**127 versiones sin intervalo de aplicación**, casi todas por lo mismo: **124 de
142 documentos no tienen fecha capturada** (`tipo_fecha = DESCONOCIDA`). No es
una cuestión jurídica —la regla para determinarlas es la de arriba— sino un dato
que la ingesta no extrajo. Es trabajo de desarrollo, y es lo que destraba el
resto del corpus.

Las 67 reglas sin condición ejecutable siguen pendientes de clasificar entre
formalizables, informativas y sin evidencia (P-010, criterio 2).
