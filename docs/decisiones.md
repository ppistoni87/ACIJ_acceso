# Decisiones de dominio

Las decisiones estructurales están en `docs/adr/` (una por tema, con su
contexto y sus consecuencias). Este documento registra las decisiones **de
dominio**: las que no son de arquitectura sino de qué se puede afirmar sobre una
norma y con qué respaldo. Cada una dice qué se decidió, por qué, y qué se
perdería si se decidiera al revés.

Las políticas que el sistema aplica están versionadas en el repositorio
(`vigencia-declarada@1`) y su versión viaja en el fundamento de cada decisión
automática, para que una respuesta vieja se pueda explicar con la política que
regía cuando se dio.

## D-01 · Frescura no es vigencia

Que una fuente responda `304 Not Modified` prueba que el documento no cambió,
no que su contenido siga rigiendo. Son dos ejes distintos: `valid_desde/hasta`
dice desde cuándo se aplica una norma; `verificado_en` y
`reverificar_antes_de` dicen cuándo la miramos por última vez.

Mezclarlos produce el error más caro del dominio: renovar la vigencia de un
dato porque el servidor devolvió 304. Una convocatoria cerrada sigue publicada
en la misma página durante meses.

**Consecuencia:** vencida la frescura, la versión deja de servirse aunque nadie
la haya derogado. No se deroga: se deja de afirmar.

## D-02 · La ausencia de derogación no prueba vigencia

La política automática resuelve solo lo que la fuente **declara**. Si la fuente
dice "vigente" y hay evidencia de esa declaración, se resuelve automáticamente.
Si no dice nada, va a revisión humana.

No haber encontrado una norma derogatoria no es lo mismo que haber comprobado
que no existe. La diferencia importa cuando la respuesta la lee alguien que
decide si presenta un trámite.

## D-03 · "No vigente" no cierra la vigencia por sí solo

Una norma etiquetada "no vigente" pudo incorporar disposiciones que siguen
aplicándose a través de la norma que modificó. La Ley CABA 547 es el caso: está
marcada no vigente y sus sustituciones siguen en el texto de la Ordenanza
43.478.

**Consecuencia:** la etiqueta no alcanza. Se compara la versión histórica con la
actualizada y la decisión queda con fundamento.

## D-04 · Una abrogación seguida de un restablecimiento no tiene lectura automática

La Ley 24.714 fue abrogada y su vigencia restablecida con excepciones. El grafo
de relaciones conserva ambos eventos con su alcance; ninguna regla los combina
en un estado. `estado_legal_validado` queda `NO_DETERMINADA` hasta que alguien
lo resuelva con fundamento.

Tomar el primer término ("abrogada") daría una respuesta rotundamente falsa
sobre la AUH.

## D-05 · Una clave canónica que no es única no es una clave

La numeración de leyes y decretos es jurisdiccional: "Ley 24.714" identifica.
La de resoluciones y disposiciones es por organismo: "Resolución 1/2023" no
identifica nada —el catálogo nacional trae 123 normas con esa clave—.

**Consecuencia:** esas normas se cargan con `identidad_incierta` y quedan fuera
del índice único parcial. No resuelven citas por número. La alternativa —dejar
que la primera fila importada se quede con la clave— haría que una cita se
resolviera con confianza a la norma equivocada por orden de archivo.

## D-06 · Evaluado no es informado

Que los siete campos estén evaluados no significa que tengan valor. Un campo
puede quedar `NO_INFORMADO_EN_FUENTES_REVISADAS`, y eso es un resultado, no una
falta: dice qué fuentes se revisaron y qué no se encontró.

**Consecuencia:** la cobertura se informa separada —porcentaje evaluado y
porcentaje con valor sustantivo validado— y nunca promediada. Un 100% de
evaluación con 0% sustantivo es un estado posible y honesto; un promedio de 50%
no significa nada.

## D-07 · Falta de dato no es incumplimiento

La evaluación de reglas es ternaria: verdadero, falso y desconocido. Un dato que
falta produce `UNKNOWN` y el resultado pide datos en vez de negar. `not(UNKNOWN)`
es `UNKNOWN`: no saber algo no prueba lo contrario.

**Consecuencia:** nunca se responde "no calificás" por un dato que la persona no
dio. Se responde qué falta.

## D-08 · Las excepciones se evalúan antes de concluir

Un criterio general en falso no alcanza para excluir: puede haber una excepción
aplicable y respaldada. Las salvaguardas de no exclusión nunca excluyen y
siempre se informan.

**Consecuencia:** el evaluador no puede cortar temprano por un criterio general.
Si hay excepciones sin evaluar, el resultado es "requiere datos", no "no".

## D-09 · La evaluación es preliminar y lo dice

El sistema no afirma elegibilidad definitiva, otorgamiento, denegatoria ni
revocación. Devuelve `POTENCIALMENTE_APLICABLE` con sus límites y sus citas, y
el cuerpo de la consulta no se persiste.

Quien decide es el organismo. Decir otra cosa desde un backend sería inventarse
una competencia que no tiene.

## D-10 · El contenido de una fuente es dato, nunca instrucción

Un documento oficial puede contener frases que parecen órdenes. Se guardan como
lo que son: el texto de un artículo. No cambian controles, no cambian permisos y
no se ejecutan. Lo mismo vale para las respuestas de un modelo: la IA puede
proponer una extracción, nunca inventar un dato ni resolver por su cuenta un
conflicto jurídico.

## D-11 · Un tope no es un monto

Un umbral de ingresos y una cuantía son cosas distintas aunque las dos sean
números con signo pesos en la misma tabla. Presentar el tope como "lo que vas a
cobrar" es el error que más rápido se convierte en un reclamo.

**Consecuencia:** las cuantías declaran su tipo y una fórmula reproducible; un
parámetro de umbral no puede servirse como cuantía.

## D-12 · Un acceso bloqueado se registra, no se evade

Un `403`, un `429` o una restricción de `robots.txt` pausan la fuente y quedan
registrados como acceso limitado, con motivo, responsable y capacidad afectada.
No se rotan identidades ni se cambia la huella para volver a entrar, y un error
nunca se convierte en "sin datos".

Un fallo de TLS se registra igual y se busca una fuente oficial equivalente o
una carga manual. La validación no se desactiva.

## D-13 · Quien publica un directorio no es quien atiende

La Defensoría del Pueblo de la Nación publica, en la misma página y con el mismo
formato, sus oficinas regionales, sus receptorías y las defensorías provinciales
y municipales, que son organismos autónomos. Cargarlas todas como oficinas
propias haría que a quien vive en Avellaneda se le respondiera que lo atiende la
Defensoría de la Nación, y quien reclama ante el organismo equivocado pierde
tiempo que a veces es un plazo.

**Consecuencia:** un punto de atención distingue el organismo titular del
organismo operador. Las defensorías de la tercera sección quedan con su propio
titular, en su propia jurisdicción, y con la DPN como quien publica el listado.
La carga abre una incidencia: la competencia y los horarios los fija cada
organismo, no quien lo lista.

## D-14 · Un dato protegido contra la recolección automática no se recolecta

El directorio publica las direcciones de correo ofuscadas con una protección de
Cloudflare. Esa protección existe precisamente para impedir que un proceso
automático las junte.

**Consecuencia:** se registra que el canal de correo existe, con `publico` en
falso y una nota que remite al sitio del organismo, y el valor no se decodifica.
Un dato que se puede obtener no es un dato que corresponda tomar.

## D-15 · Un teléfono publicado se guarda como está

`(11) 4227-7184 / 7110 / 4222-8226` son tres líneas de las que «7110» no se marca
sola, y `(299) 449.1200 int. 4600` lleva interno. Partir esos textos en números
sueltos fabrica líneas que nadie publicó.

**Consecuencia:** se guarda el texto tal como lo publica la fuente y se normaliza
sólo cuando es un único número sin ambigüedad. Un valor normalizado, cuando
existe, se puede marcar sin dudar; cuando no existe, queda el texto.

## D-16 · El recuento que publica la fuente es un control

Cada panel del directorio anuncia cuántas oficinas contiene («Buenos Aires | 16»).
Una primera versión de este importador leía sólo la primera oficina de cada panel
y cargó 39 de 78 sin que nada fallara: los datos entraban, las restricciones se
cumplían y el reporte daba bien.

**Consecuencia:** cuando la fuente declara un recuento, se verifica contra lo
leído y la diferencia se informa. Una lectura incompleta que no avisa es peor que
un error, porque nadie la va a buscar.

## D-17 · Una advertencia de alcance no se compensa con resultados

`GET /v1/beneficios` responde siempre con la advertencia de que el listado no
infiere elegibilidad. La evaluación conversacional contaba primero las filas, así
que mientras el corpus estuvo vacío el caso «¿ya tengo aprobado el beneficio?»
pasaba por no tener nada que devolver; con un beneficio publicado, el mismo
listado pasó a leerse como una respuesta afirmativa.

**Consecuencia:** una envoltura con `UNSUPPORTED_SCOPE` es una abstención,
cualquiera sea la cantidad de filas. Un control que sólo pasa mientras no hay
datos no es un control.

## D-18 · Una correspondencia entre versiones se aprueba antes de redirigir una cita

Cuando un texto se consolida, el contenido de un artículo puede quedar en otro
número. Una regla citada contra el artículo 10 original no se responde con lo
que hoy dice el artículo 10: se responde con la unidad que efectivamente se
citó, y sólo se redirige al artículo nuevo cuando alguien comprobó que son el
mismo contenido.

Emparejar por texto idéntico deriva la correspondencia pero no la comprueba: dos
párrafos iguales en dos artículos distintos se emparejan solos. Por eso toda
equivalencia derivada nace `CANDIDATE` y sólo una `APPROVED` redirige, con actor
y fundamento registrados.

**Consecuencia:** ante la duda no hay redirección, que es lo correcto: devolver
la unidad citada con su versión es siempre defendible; devolver otra por
parecido no lo es. Y una equivalencia relaciona unidades, nunca las pisa: el
artículo 10 de la versión nueva conserva su propio texto.

En el Decreto 1382/2001 la derivación encontró 60 correspondencias reales entre
el texto original y el actualizado: 59 renumeraciones y una sustitución, la del
artículo 3, donde InfoLEG consolidó la corrección del Decreto 1407/2001 —«donde
dice incisos 1) y 5) debe decir incisos 1) a 5)»—. Ese es el caso más silencioso:
la cita sigue apuntando a un artículo que existe, sólo que ya no dice lo mismo.

## D-19 · Un ancla rota se reporta; no se resuelve por parecido

F28 no es una fuente distinta de F31: es la misma página de preguntas
frecuentes citada con `#44` para señalar una pregunta puntual. En la captura
real de F31 hay 129 anclas y ninguna es numérica, así que `#44` no lleva a
ninguna parte. La página carga igual, de modo que el error no se ve.

El alias se conserva —la identidad de la referencia es un dato aunque no
resuelva— y la rotura se registra con responsable. Lo que no se hace es
adivinar: la página tiene un ancla `accordion-2693944`, que contiene «44», y
tiene exactamente 43 preguntas, así que «la 44» está a un lugar de existir. Las
dos coincidencias son falsas y las dos son tentadoras.

**Consecuencia:** los parecidos se reportan como parecidos que no se usaron,
para que quien revise vea por qué no alcanzan. La referencia correcta la
consigue alguien que mire el destino, no una heurística de dígitos.

## D-20 · La fecha de un documento sale de su texto o no sale

La carpeta que aloja un PDF dice dónde lo guardaron, no cuándo lo firmaron. En
el corpus hay tres PDF cuya ruta declara un año —`/files/2021/08/`, `/2025-11/`,
`/2026-08/`— y ninguno lo confirma en su texto.

Adentro del documento tampoco alcanza con encontrar una fecha. El Decreto 690/06
consolidado trae 34, de 2008 a 2025, y ninguna lo fecha: todas están en notas de
consolidación que fechan al decreto que lo modificó. Tomar la primera daría 2011;
la última, 2025. Es un decreto de 2006.

**Consecuencia:** una fecha fecha el documento sólo cuando el texto dice que lo
fecha —un encabezado de lugar y fecha, o una fórmula de sanción—. Las demás se
leen, se clasifican y se reportan sin usarse. Las de las notas, además,
identifican los actos que modificaron: eso no se descarta junto con la fecha.

## D-21 · Un cuerpo que aprueba un anexo no informa lo que el anexo dice

La Resolución 1621/MEDGC/25 no dice cómo se pide una beca. Su artículo 3 aprueba
los «Procedimientos para el otorgamiento, control y evaluación del Régimen de
Becas Estudiantiles de la Ley 2917, identificado como Anexo
(IF-2025-53544032-GCABA-SSGDA) el cual forma parte integrante de la presente».
Las etapas y los plazos están ahí.

Leer sólo el cuerpo y publicar «no informa plazos» es tan falso como publicar
plazos inventados: la resolución sí los fija, en un documento que hay que ir a
buscar.

**Consecuencia:** mientras el anexo no esté capturado y vinculado, los campos
que dependen de él quedan `NO_INFORMADO` **con el motivo puesto** —remite a un
anexo que falta— y no por silencio de la norma. El identificador del anexo se
guarda como referencia pendiente con responsable; que un PDF diga «Anexo» no
prueba que sea el que esta resolución aprobó, así que vincularlo es una decisión
con actor y fundamento, no una coincidencia de nombre.

Dos detalles que sólo aparecen con el texto real: la remisión cruza tres
unidades —empieza en el artículo 3 y termina dos párrafos después—, así que
buscarla unidad por unidad no encuentra ninguna de las dos mitades; y el PDF
parte el identificador en dos renglones (`IF-2025-` / `53544032-GCABA-SSGDA`),
que sigue siendo el mismo documento.

## D-22 · El período de una tabla está adentro de la tabla, no cerca

El PDF de montos de becas tiene tres tablas y tres meses en la misma página.
Asociarlos por cercanía haría que una tabla herede el monto de otro mes, que es
la clase de error que nadie nota hasta que alguien cobra de menos.

Mirando dónde está cada cosa se ve que el epígrafe no está arriba de la tabla:
es su primera fila, adentro del recuadro. Eso convierte la asociación en
contención y no en proximidad: un período que está adentro de una tabla no puede
pertenecer a otra.

**Consecuencia:** una tabla se fecha con el período que declara adentro. Si no
declara ninguno, se fecha con la nota al pie que ella misma llama —la marca
`**` que está en la tabla y encabeza la nota es lo que las une—. Un período que
está suelto en un párrafo de la página no fecha ninguna tabla, y dos períodos
dentro de la misma tabla la dejan en revisión: cuál rige para qué fila es una
lectura, no una deducción.

Sobre el PDF real esto pasó de una tabla fechada a diez de once. La restante
queda en revisión con el motivo puesto.
