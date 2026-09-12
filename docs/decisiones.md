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

## D-23 · El orden de los pasos lo declara el documento, no el extractor

Un instructivo numera sus pasos. Ese número es la secuencia; la posición en la
que el extractor devuelve el texto no lo es. Si un rótulo sale después de su
contenido y se ordena por lectura, el trámite queda invertido y alguien hace el
paso 4 antes que el 3.

**Consecuencia:** los pasos se ordenan por el número que declaran. Un paso que
cruza de página sigue siendo el mismo paso —en el instructivo de becas el 4
empieza en una página y su documentación necesaria está en la siguiente, sin
rótulo propio—, y el encabezado que se repite arriba de cada página se detecta
por repetición en vez de configurarse.

Un número repetido, un salto en la serie o un paso que sólo trae una captura de
pantalla se cargan como están y se reportan. Renumerar por orden de aparición
inventaría una secuencia que el documento no declara.

## D-24 · Una página de error se guarda y no se extrae

Un `404` de un portal suele traer una página completa, con navegación y
buscador, que se lee como cualquier otro HTML. Extraerla mete en el corpus un
documento cuyo texto dice «la página que buscás no existe».

**Consecuencia:** la respuesta se captura con su status real —es la prueba de
qué contestó esa URL, y permite notar cuándo deja de contestar eso— y la
extracción sólo toma capturas `2xx`. La corrida no figura completa: haber
descargado la página de error no es haber conseguido el contenido.

## D-25 · «Este mes» no es un período

El cronograma de pagos de Progresar dice «correspondiente a este mes inicia el 9
de febrero», y las fechas de la tabla no llevan año. El texto se lee entero y
parece que dijera algo.

Completar el año con la fecha de captura es el mismo error que fechar un PDF por
su carpeta, con un agravante: una página que quedó sin actualizar publica el
cronograma del mes pasado con exactamente las mismas palabras, así que la
suposición no sólo es silenciosa, además es probable.

**Consecuencia:** una página que fecha su contenido en términos relativos, o que
trae días sin año, queda con su período indeterminado y lo declara. El contenido
se conserva —el monto y el orden por terminación de DNI son datos— y lo que no
se afirma es a qué mes corresponden.

## D-26 · La jurisdicción dice dónde está; el alcance, a quién sirve

La defensoría de Avellaneda y la de la Provincia de Buenos Aires comparten
`AR-B`. Con sólo la jurisdicción, una consulta las devuelve como si fueran la
misma cosa, y quien pregunta por el servicio de su municipio recibe un organismo
que no tiene competencia sobre su reclamo.

**Consecuencia:** un punto de atención declara su alcance —nacional, provincial,
municipal— aparte de su jurisdicción, y un punto municipal tiene que decir de
qué municipio. Pedir alcance municipal no devuelve el provincial de la misma
provincia; cuando no hay ninguno municipal, la respuesta lo dice y nombra los de
otro alcance que sí hay, sin ofrecerlos como equivalentes.

El alcance sale de lo que el nombre declara y de nada más. «Defensor del Pueblo
de Salta» puede ser el provincial o el de la capital: de los 57 organismos del
directorio de la DPN, 13 se declaran municipales, 6 provinciales y 38 quedan sin
declarar. Adivinar los 38 habría dado un resultado completo y a veces falso.

## D-27 · Un campo en disputa se retiene; lo coincidente se publica

El dataset abierto de sedes comunales dice que la Subsede Comunal 2 está en
«Lopez, Vicente 2050, 3 piso». La ficha de la Comuna 2, del mismo gobierno, dice
«Vicente López 2050, 4° piso». Las dos son oficiales y las dos están publicadas
hoy.

Elegir la primera fuente, elegir la más reciente o componer una legible con la
calle de una y el piso de la otra producen las tres una dirección que se lee
bien y manda a alguien a una puerta equivocada en un edificio correcto.

**Consecuencia:** los dos candidatos coexisten, el piso queda en disputa con una
incidencia que nombra qué dice cada fuente, y se publica lo que las dos afirman
igual: «Lopez, Vicente 2050». El valor coincidente se elige de forma
determinista y no por orden de llegada, porque quedarse con el primero también
es elegir una fuente.

Y «Lopez, Vicente» y «Vicente López» no son un conflicto de calle: el dataset
invierte apellido y nombre. Leerlo como dos calles distintas habría inventado un
conflicto y tapado el que sí existe.

## D-28 · Lo que afirma una ONG se conserva con su atribución

ACIJ publica un análisis del Proyecto de Presupuesto 2026 de la Ciudad y afirma
que las partidas de los organismos de vivienda caen 22,9% en términos reales y
son las más bajas en catorce años. El GCBA publica el proyecto; no publica esa
lectura.

Descartarla pierde información sostenida en un documento público. Presentarla
sin decir quién la hace le da una autoridad que no tiene: quien la lea va a
creer que el Gobierno de la Ciudad dijo que su propio presupuesto de vivienda es
el más bajo en catorce años.

**Consecuencia:** una fuente declara con qué autoridad habla. Las 83 del
manifiesto son oficiales; ACIJ se incorporó como secundaria. Una afirmación
sostenida sólo por una fuente secundaria se sirve diciendo quién la afirma, y el
organismo de la fuente oficial no viaja con ella.

## D-29 · Un respaldo se prueba restaurándolo

Las pruebas de respaldo verificaban que la comprobación de integridad encontrara
lo que falta, no que el volcado existiera. Un backup que nadie restauró no es un
backup.

**Consecuencia:** el ciclo completo se ejerce sobre bases propias, creadas y
borradas en la prueba: `pg_dump` de una base con datos confirmados, `pg_restore`
en otra que empieza vacía, y sobre la restaurada se comprueban las 83 fuentes,
el hash de la captura, la verificación de integridad y que los triggers de
inmutabilidad sigan ahí. Un volcado que pierde los triggers deja una base que
acepta lo que la original rechazaba, y eso no se nota hasta que alguien escribe.

## D-30 · Una latencia sin el tamaño del corpus al lado no dice nada

La misma consulta que responde en 8 ms sobre veinte normas puede tardar
segundos sobre cuatrocientas mil. Por eso la medición corre sobre la base real
—423.718 normas, 364 MB— y el reporte lleva el recuento de cada tabla arriba de
los números.

Medir encontró tres cosas que ninguna prueba funcional podía encontrar, porque
todas daban el resultado correcto:

- El listado de normas pedía los identificadores y la cobertura de campos **de a
  una fila**: veinte normas eran cuarenta idas y vueltas más. Pedirlos por página
  bajó el listado de 207 ms a 21 ms.
- Ordenar por año y número recorría la tabla entera. Con índice, la primera
  consulta en frío pasó de 6,9 segundos a 33 ms.
- `v_hechos_servibles` evaluaba las 7.888 versiones del registro una por una, y
  7.887 eran candidatas que nunca podían servirse. Pre-filtrar por las dos
  condiciones que la propia función ya devolvía como motivo bajó el endpoint de
  cobertura de 800 ms a 27 ms.

**Consecuencia:** el pre-filtro sólo es defendible si el resultado no cambia, así
que hay una prueba que calcula las dos formas —con y sin pre-filtro, en ocho
capacidades, con release y sin release, dentro y fuera del período— y compara.
Si alguien agrega ahí una condición que la función no evalúe, la vista empezaría
a esconder versiones servibles sin decirlo, y la prueba lo ve.

Y el reporte dice qué no mide: las consultas van una después de otra, sobre la
misma conexión y sin red. No afirma un número de concurrencia, porque para eso
hace falta el despliegue real.

## D-31 · Un calendario de otra jurisdicción no computa un plazo local

El artículo 14 de la Ley 2917 da diez días **hábiles** para pedir la
reconsideración de una beca. El esquema exige un calendario para computar un
plazo hábil, y el único cargado era el nacional.

Los feriados nacionales rigen en todo el país, así que un calendario local que
los repita es cierto en lo que dice. Lo que no tiene son las ferias
administrativas que cada jurisdicción fija por su cuenta, y ésas **alargan** el
plazo: contarlas de menos adelanta el vencimiento, que es exactamente el error
que hace perder un plazo.

**Consecuencia:** el cómputo rechaza calcular con un calendario de otra
jurisdicción, que hasta ahora nada impedía. El calendario de CABA se derivó del
nacional con el nombre diciendo qué le falta —«sin ferias administrativas
locales», que viaja en el fundamento de cada cómputo— y una incidencia abierta
con responsable. Un calendario incompleto que dice qué le falta es mejor que
ninguno; uno que no lo dice es peor que ninguno.

## D-32 · Una regla con condición escrita no es una regla sin condición

El aviso de la curación decía, de todas las reglas pendientes de revisión, que
«se conserva su texto literal y nada más». Era falso para la mitad de ellas: el
árbol estaba guardado y validado, esperando aprobación. El mensaje hacía parecer
perdido un trabajo que estaba hecho.

**Consecuencia:** el aviso separa las dos situaciones. Una regla sin AST no tiene
condición que ejecutar porque la ley la remite a la reglamentación; una regla con
AST y `requiere_revision` tiene su condición escrita y validada, y espera una
firma. Confundirlas hacia un lado esconde trabajo; hacia el otro haría creer que
hay una condición ejecutable donde no la hay.

Y que a una lectura le falte la norma que cita ya no aborta el lote: se reporta
con su motivo y las demás entran. Es la misma regla que rige para las fuentes.

## D-33 · Medir antes de optimizar, y corregir lo que la medición desmiente

La medición de concurrencia mostró que entre cuatro y dieciséis consultas
simultáneas la latencia se multiplicaba por seis mientras el caudal se quedaba
quieto en unas setenta consultas por segundo. La explicación obvia era el pool
de conexiones, que estaba en el default de SQLAlchemy —cinco más diez de
desborde— y que nadie había elegido.

Se declaró el pool y **el caudal no cambió**. Así que la explicación obvia era
falsa, y el comentario que la afirmaba en el código tuvo que corregirse antes de
quedar como documentación de algo que no pasa.

Corriendo el mismo trabajo contra el motor, sin la API en el medio, el resultado
fue claro: **1.270 consultas por segundo contra 76**. El límite no está en la
base ni en las conexiones sino en el proceso que arma y serializa cada
respuesta.

**Consecuencia:** el reporte de rendimiento incluye las dos cifras juntas,
porque la diferencia es la que dice qué hacer. Agrandar el pool o agregar
índices no mueve ese número; agregar procesos sí. Y el pool declarado se
conserva —elegir el número es mejor que heredarlo— pero sin atribuirle una
mejora que no produjo.

## D-34 · Una corrida sin trabajo no es una corrida fallida

El ciclo de monitoreo planifica según la frecuencia declarada de cada fuente y
revalida sólo a las vencidas. Cuando no le toca a ninguna, la corrida termina
sin hacer nada, y eso está bien: es la frecuencia haciendo lo suyo. Un reporte
que no distinga ese caso del de un fallo hace que alguien reinicie un servicio
que estaba funcionando, o peor, que deje de mirar los reportes.

**Consecuencia:** el ciclo dice explícitamente cuándo no le tocaba a nadie, y el
paso de planificación informa cuántas fuentes entraron aunque sean cero. Revisar
de más también tiene costo: gasta la cuota de la fuente y no aporta nada.

El ciclo planifica y delega en el monitor, que ya encadenaba captura, extracción
y comparación. Repetir esos pasos desde el ciclo habría hecho el trabajo dos
veces sobre las mismas capturas.

Lo que el ciclo no hace es dispararse solo, y el reporte lo dice con esas
palabras. Es una decisión de despliegue —un planificador del sistema llamando
`bn monitoreo ciclo` cada hora— y no código que falte; dejarlo implícito haría
creer que el corpus se actualiza sin que nadie lo pida.

## D-35 · Un renglón no es un párrafo

Varios boletines publican el PDF convertido con un `<p>` por línea visual, y el
adaptador de PDF armaba un párrafo por cada línea que devuelve la biblioteca. En
las dos vías, una oración quedaba repartida en cuatro unidades documentales.

Eso rompe la promesa de la evidencia. Una afirmación apunta a una unidad; si la
unidad es media oración, la cita no cabe adentro y la afirmación queda colgada
de un fragmento que no dice lo que se afirma. De las nueve reglas de la primera
lectura curada, las nueve citaban texto que no estaba en la unidad citada.

Los renglones se unen con una señal local y sin dos lecturas: el bloque anterior
no cerró oración y este empieza a mitad de frase —con minúscula, con un
paréntesis corto que cierra enseguida, o porque el anterior cortó en una palabra
que ninguna oración puede terminar—. Nunca se une si el bloque abre estructura,
ni si es un correo o una dirección web.

Se probó antes decidirlo por documento, midiendo qué proporción de bloques
termina en punto. Eso confundía una guía telefónica con una norma cortada en
renglones: en las dos casi ningún bloque termina en punto, y unía el mail de una
defensoría con el interno de la de al lado.

**Consecuencia:** una unidad puede cruzar el corte de página, así que el párrafo
lleva también dónde termina. Una cita que dice «página 4» cuando la frase sigue
en la 5 manda a buscar donde no está.

## D-36 · Una cita que no está en la unidad que dice citar no es una cita

Que la lectura jurídica de una norma sea correcta lo decide una persona. Que el
texto citado exista donde se dice que existe, no: es lo único que una máquina
puede verificar sola de una lectura curada, y por eso se verifica siempre.

El cargador compara el texto literal de cada regla y de cada plazo contra la
unidad que su evidencia señala, con los espacios normalizados —el boletín corta
las líneas donde le queda y eso no cambia lo que dice— y falla si no está.
Cualquier otra diferencia sí importa: una cita que resume, que elide con puntos
suspensivos o que le agrega un punto final a una oración que seguía deja de ser
una cita del texto capturado.

Con el control puesto aparecieron cuatro citas que no eran citas. Una de ellas
reproduce ahora «Una vezentregado» sin el espacio, porque así lo publica la
fuente: corregir la errata haría que la cita dejara de coincidir con el texto
capturado, que es lo único contra lo que se puede verificar.

**Consecuencia:** cambiar la segmentación rompe las lecturas curadas, a propósito.
El error dice en qué unidad sí está el texto, que distingue los dos casos —la
cita se movió porque cambió la segmentación, o no está en ninguna parte—.

## D-37 · Aprobar los campos después de publicar no sirve de nada

La publicación es lo que promueve las afirmaciones a `PUBLISHED`, y la API sirve
sólo las publicadas. Publicar antes de aprobar deja la versión publicada y sus
afirmaciones aprobadas para siempre fuera de ese release: la ficha se sirve con
versiones servibles y sin una sola cita, que es indistinguible de una norma sin
respaldo.

No se prohíbe: una versión puede no tener nada informado que aprobar, y
bloquearla obligaría a aprobar algo para poder publicar. Lo que no se hace es en
silencio.

**Consecuencia:** publicar avisa cuando una versión sale con todas sus
afirmaciones sin aprobar, y dice cómo se arregla. Revertir el release devuelve
las versiones a aprobadas sin borrar nada: borrarlo dejaría a los consumidores
citando fragmentos que ya no se pueden explicar.

## D-38 · Lo que se recibe no siempre es dinero

La beca de comedor no paga un importe: da de comer. La ordenanza que la crea no
fija el valor de la ración —sale de la licitación de cada distrito— y lo único
que fija es que la ración del alumno no becado no puede costar más que la del
becado, que es una relación entre dos precios y no la cuantía del beneficio.

Guardarla como fórmula habría obligado a inventar un número, y el número es
justamente lo que la norma no da.

**Consecuencia:** la cuantía se guarda como prestación en especie, con la
descripción de lo que se recibe. Un monto fijo, en cambio, se rechaza con su
motivo hasta que haya un caso real: escribir ese camino a ciegas sería adivinar
cómo se guarda un número que después se sirve como «lo que vas a cobrar».

## D-39 · Un beneficio puede estar leído desde más de una norma

La beca de comedor la crea la Ordenanza 43.478 de 1989 y la Ley 547 de 2001 le
sustituye los artículos que dicen quién accede y con qué umbral. Es la misma
beca. Partirla en dos códigos de beneficio habría dicho que hay dos becas donde
hay una, y descartar la ley habría dejado la lectura anclada a un texto que
otro texto reemplazó.

Que las dos lecturas compartan la versión del beneficio rompía algo que no se
veía: la carga marca `SUPERSEDED` las reglas del beneficio que la lectura ya no
contiene —así se retira una cita corregida— y ninguna regla de la ordenanza
figura en el archivo de la ley. Cargar la segunda retiraba a la primera, y cuál
sobrevivía dependía del orden alfabético de los archivos.

**Consecuencia:** una lectura solo retira lo que ella misma escribió: el barrido
se acota al texto que esa lectura cita. Dos lecturas del mismo beneficio tienen
que leer normas distintas y solo una puede decir que lo crea, y eso se verifica
sobre los archivos antes de tocar la base.

## D-40 · Un conflicto entre dos textos del corpus se escribe, no se resuelve

NormativaBA publica como texto consolidado de la Ordenanza 43.478 un artículo 16
anterior al que la Ley 547 puso en su lugar. Los dos están en el corpus y dan
resultados distintos para la misma familia: uno mide en «sueldos mínimos» sin
definirlos, beca total hasta dos; el otro mide contra el sueldo del convenio de
empleados de comercio, beca total hasta 2,5 y con más tope por cada hijo en la
escuela pública.

Elegir uno al cargar habría sido resolver una cuestión jurídica en silencio y
con la apariencia de un dato. Cargar solo uno de los dos habría sido lo mismo
sin dejar rastro. Descartar los dos habría borrado del corpus la única beca
alimentaria escolar que tiene texto.

**Consecuencia:** una lectura curada puede declarar un conflicto con otro texto
del corpus. La carga verifica la cita propia como cualquier otra —un conflicto
que apunta a un texto que no lo dice es un error de lectura y detiene la
carga—, guarda las dos reglas con su evidencia y abre una incidencia
`CONFLICTO_DE_FUENTES` que localiza las dos redacciones. Quién decide cuál rige
tiene nombre: `curacion juridica`.

## D-41 · Un vacío declarado con un nombre inventado no declara nada

Trece lecturas curadas decían que la norma no informa los canales de atención, y
dos que no informa la cuantía. Ninguna de las quince hacía nada: la carga
actualiza la evaluación de completitud del campo por su nombre, «canales» y
«cuantias» no están entre los siete campos que la completitud evalúa, y una
sentencia que no encuentra fila termina sin error. Quince motivos escritos con
cuidado, y ninguno llegaba a ninguna parte.

Lo que se perdía no era un dato de más: es la diferencia entre «no figura dónde
presentarlo» y «no hay dónde presentarlo». Un canal ausente sin explicación se
lee como que el trámite no existe.

**Consecuencia:** los siete campos son los siete. Declarar cualquier otro como
campo no informado detiene la carga y dice dónde va, y declarar uno de los siete
como vacío también, porque los dos lugares no son intercambiables: la
completitud es lo que la API sirve cuando alguien pregunta si le pueden quitar
el beneficio. Lo que la norma no da y no es uno de los siete va en
`vacios_declarados` y abre una incidencia con el motivo y con el rol que puede
cerrarla. Y la carga verifica que la fila exista: declarar no informado un campo
sin evaluación tampoco pasa desapercibido.

## D-42 · Una prestación con la vigencia en duda se dice, no se decide

En noviembre de 2001 el Decreto 1382/01 derogó la Ley 24.714 y mantuvo cinco de
sus prestaciones —asignación por hijo, por hijo discapacitado, por maternidad,
ayuda escolar primaria y por cónyuge del beneficiario del SIJP— hasta que
empezaran a pagarse las equivalentes del sistema que creaba. Tres días después el
Decreto 1604/01 restituyó la vigencia de la ley desde la fecha de su derogación,
«con excepción de las normas correspondientes a las prestaciones a las que
refiere el tercer párrafo del artículo 26» del primero: exactamente esas cinco.

Leído al pie, lo restituido excluye a las cinco. Leído por su finalidad, las
cinco nunca se derogaron y por eso no necesitaban restitución. Los dos textos
están en el corpus y no alcanzan para elegir: no consta que las prestaciones
equivalentes se hayan empezado a pagar nunca. Y el decreto dice «ayuda escolar
primaria» donde la ley dice «ayuda escolar anual», así que ni siquiera es seguro
que la cuarta esté en la lista.

Servir cualquiera de las dos lecturas sería afirmar sobre la vigencia de un
derecho a partir de una elección del sistema. Callarlo sería peor: las cinco
prestaciones quedarían indistinguibles de las otras siete, que no tienen esta
duda.

**Consecuencia:** cada una de las cinco lecturas declara el conflicto por
separado, citando el artículo que crea su prestación y el párrafo del decreto que
la nombra, y cada una abre su propia incidencia. Se ve cuáles son las cinco y
cuáles son las siete que no están alcanzadas, sin que el sistema diga que
ninguna de las doce está vigente ni que todas lo están.

## D-43 · Un documento generado que cambia por regenerarlo no sirve de referencia

El diccionario de datos se arma leyendo los modelos, y volver a correrlo daba un
archivo distinto sin que hubiera cambiado una línea del esquema. Dos causas: las
restricciones de cada tabla se leen de un conjunto, que no tiene orden, y una
columna calculada traía el `repr` de su `Computed`, que incluye la dirección de
memoria del objeto.

El costo no es estético. El diccionario existe para que un cambio de esquema se
vea en el diff; si cada regeneración mueve sesenta líneas y cambia un número
hexadecimal, el cambio real queda escondido entre el ruido y nadie regenera.

**Consecuencia:** las restricciones salen ordenadas por nombre y la columna
calculada muestra la expresión que la calcula en lugar de su `repr`. Dos
corridas dan el mismo texto, y eso se prueba: si vuelve a haber una dirección de
memoria en el documento, falla.

## D-44 · Una lectura curada entra entera o no entra

Una corrida limpia decía «16 beneficios curados» y en la base había cuatro
lecturas cargadas de diecinueve. Las otras quince se rechazaban a mitad de
camino y nadie se enteraba, por tres razones que se tapaban entre sí.

La primera: la población evalúa los siete campos *después* de cargar los
beneficios, porque varios de ellos salen de la lectura curada. Así que cuando la
curación quería declarar un campo como no informado, la fila de evaluación
todavía no existía y el `UPDATE` no encontraba nada. En una base de desarrollo,
donde alguien ya había corrido los campos alguna vez, funcionaba; desde cero, no.

La segunda: el cargador escribe el beneficio, sus poblaciones y sus reglas antes
de llegar a los campos, las dependencias y los conflictos. Una lectura que se
rechazaba tarde dejaba escrita la primera mitad, y el beneficio quedaba en la
base sin las dependencias ni los conflictos que la lectura declaraba.

La tercera: el reporte contaba `beneficios`, y esa fila la escribe el cargador
en su primer paso. Los quince beneficios a medio cargar entraban en el total y
el total decía que estaba todo.

**Consecuencia:** declarar un campo no informado crea la evaluación si no está,
que es lo que corresponde —la lectura curada es la fuente de esa afirmación—.
Cada lectura se carga dentro de un punto de retorno, así que la que falla no
deja nada. Y el reporte cuenta los beneficios que tienen al menos una regla: uno
sin ninguna condición no es un beneficio curado, y contarlo era lo que hacía que
el total tapara el problema.

## D-45 · Idempotente es una propiedad que hay que ejercitar, no declarar

El procedimiento de población dice de sí mismo que es idempotente: reejecutarlo
revalida las capturas, no duplica versiones y solo reprocesa lo que cambió. Y lo
era para casi todo, porque casi todo se corría dos veces seguidas mientras se
construía. El padrón RENABAP no: se importaba una vez por base y nadie lo volvía
a correr sobre una base que ya lo tenía.

Reejecutar la población sobre la base de desarrollo lo mostró en una línea: la
planilla se vuelve a descargar, así que la captura es otra fila, pero los bytes
son los mismos. El importador reconocía la repetición por la captura y no por el
contenido, intentaba insertar una versión de documento con un hash que ya
estaba, y la restricción que impide duplicarla detenía la población entera.

**Consecuencia:** los mismos bytes son la misma versión del documento, y así se
busca. Y la idempotencia se prueba: una segunda captura de la misma planilla no
crea una versión más.

Vale la pena decir por qué no se había visto. La corrida limpia empieza de cero
y por eso nunca ejercita la segunda pasada; la base de desarrollo se reejecuta y
por eso nunca ejercita la primera. Las dos hacen falta, y ninguna de las dos
sola alcanza.

## D-46 · El corpus se amplía con lo que el corpus pide, no con lo que parece útil

Las 83 fuentes del manual son el inventario y no se tocan. Pero las normas que
sí están citan otras, y cada cita que no resuelve queda escrita como referencia
pendiente: «esta norma dice que depende de aquella y aquella no está». Eran
ciento sesenta y ocho preguntas escritas y sin contestar.

El catálogo nacional que ya se había importado tenía la respuesta para buena
parte: trae, por cada norma, la URL de su texto en InfoLEG. Así que ampliar no
fue salir a buscar, fue capturar el texto que el propio corpus ya había
identificado como necesario. Entraron veintiséis decretos nacionales, entre
ellos el que crea la AUH y el que crea la Asignación por Embarazo.

Lo que no se hace es adivinar. Una referencia se amplía solo si resuelve a una y
una sola norma, esa norma no está marcada de identidad incierta, y hay texto. Lo
demás se informa con su motivo, incluido el error más fácil de cometer y el más
difícil de ver después: resolver contra el catálogo nacional una «Ley 3706» que
citó una norma porteña traería un texto de otra jurisdicción, ya segmentado y
curable, sin que nada dijera que es el equivocado.

**Consecuencia:** la fuente derivada tiene `origen` propio y no entra al
inventario de las 83; cada norma que llega es trazable a la cita que la pidió; y
el criterio de corte está probado por su lado negativo —sin año, ambigua,
incierta, de otra jurisdicción, sin texto—, que es donde una ampliación se
vuelve una afirmación falsa.

## D-47 · Un `<br>` es un salto de línea, y una norma no es un párrafo

InfoLEG publica las normas recientes dentro de un solo `div`, con los artículos
separados por `<br>`. El extractor tomaba el bloque entero como un párrafo, así
que una norma de veintitrés mil caracteres llegaba al segmentador como una sola
unidad y no se reconocía un artículo adentro. Nueve de las veintiséis normas
nuevas entraron sin una sola unidad.

Un salto en el código fuente es maquetación y no significa nada —eso sigue
igual—, pero un `<br>` lo escribió alguien para cortar ahí. Partir por `<br>`
puede partir de más, y para eso ya estaba `unir_renglones`, que vuelve a juntar
los renglones que continúan la misma oración: primero hay que tener los
renglones.

**Consecuencia:** el extractor parte los bloques donde el HTML declara el salto.
Es un cambio que alcanza a todo lo ya extraído, así que sube la versión del
extractor, y eso destapó dos cosas más: que nada volvía a extraer lo ya
extraído, y que rehacer la segmentación de una versión citada borra las unidades
que esas citas localizan.

## D-48 · Una versión que alguien citó ya no se resegmenta

Numerar el extractor solo sirve si algo vuelve a pasar por lo ya extraído. No lo
hacía: solo entraban las capturas sin versión, así que mejorar la segmentación
no alcanzaba nada, y una fuente que ya no responde se quedaba con la
segmentación vieja para siempre sin que nada lo dijera. Ahora también entran las
versiones producidas por un extractor anterior.

Eso destapó lo otro. Rehacer la segmentación borra las unidades de la versión, y
una evidencia localiza una unidad: la cita quedaría apuntando a algo que ya no
existe, que es exactamente lo que una evidencia está para impedir. La base lo
rechazó por integridad referencial antes de que nadie lo notara.

**Consecuencia:** una versión con evidencias sobre sus unidades no se
resegmenta, y el aviso dice cuántas citas dependen de ella. Mejorarle la
segmentación deja de ser un reproceso y pasa a ser una decisión: hay que volver
a curar lo que la citaba. Cuando la fuente vuelve a entregar y el texto cambia,
la versión nueva se segmenta con el extractor nuevo y la vieja queda intacta con
sus citas —que fue lo que pasó con la Ley 24.714, cuyo inciso c) del artículo 1
se movió de ruta y obligó a reanclar tres lecturas curadas—.

## D-49 · Faltaba con qué aprobar, no a quién

Las reglas curadas nacen candidatas y la evaluación no las usa «hasta que
alguien con competencia jurídica las apruebe». Esa frase estaba en el código, en
los avisos de la carga y en el backlog. Lo que no estaba era el comando: no
había forma de aprobar una regla. `bn revision aprobar-campos` mueve
afirmaciones, que son otra tabla.

Así que las ciento cincuenta y cuatro reglas estaban en CANDIDATE por ausencia
de una función y no por falta de revisión, y la historia figuraba bloqueada
esperando a una persona que, aunque hubiera aparecido, no habría tenido con qué
firmar.

**Consecuencia:** el circuito existe —aprobar, rechazar, marcar en revisión, y
aprobar por beneficio— y cada transición exige actor y fundamento y deja un
evento por regla en la bitácora. Aprobar de a un beneficio no es un atajo: sus
reglas se leen juntas porque se aplican juntas, y obligar a ciento cincuenta
invocaciones no hace la revisión más cuidadosa, hace que se resuelva con un
bucle que nadie mira.

## D-50 · Una revisión que no tiene forma de tarea no se hace

«Revisar 154 reglas» no es una tarea: es una intención. El expediente que genera
`bn revision reglas` la convierte en una lista de preguntas concretas, cada una
con el texto literal de la norma al lado, la unidad a la que mirar, lo que la
lectura afirma y qué hay que decidir.

Armarlo mostró que dos de cada tres reglas no decían a qué artículo mirar: la
evidencia localiza una unidad, pero el `selector` lo escribe quien crea la
evidencia, y una reusada por otro curador no lo traía. Quien revisara habría
tenido que buscar el artículo a mano ciento seis veces.

**Consecuencia:** el expediente localiza por unidad y no por selector, y separa
las reglas en las dos pilas que no se revisan igual: las que tienen condición
ejecutable, que se confirman contra el texto, y las que no, donde hay que
decidir si la condición se puede escribir o si la regla es informativa.

Lo que el expediente no hace es firmar. Esa parte no es una tarea pendiente de
automatizar: aprobar una regla es afirmar que lo que el backend contesta es lo
que dice el derecho, y ponerle a esa afirmación un actor que no revisó nada
convertiría la bitácora —que existe para poder explicar cada respuesta— en el
lugar donde se esconde que nadie la revisó.

## D-51 · Ampliar el corpus no es un paso de rutina

`bn ingesta ampliar` trae el texto de las normas que el corpus cita. Ponerlo
dentro del procedimiento de población parecía natural —es ingesta, va con la
ingesta— y la corrida limpia mostró que no.

Cada pasada descubre citas nuevas en las normas que trajo la pasada anterior.
Con la ampliación adentro, la segunda pasada pasó de 53 a 85 versiones de
documento, y el propio reporte lo dijo con todas las letras: el procedimiento
había dejado de ser idempotente, que es lo que promete de sí mismo. No era una
duplicación, era crecimiento; pero un procedimiento que crece cada vez que se
corre no se puede correr todos los días.

Peor: traer un anillo nuevo puede resegmentar normas ya curadas, porque una
captura nueva es una versión nueva y las rutas de las unidades se corren. En esa
corrida, dieciséis de veinte lecturas curadas dejaron de cargar. El reporte lo
detectó por dos caminos distintos —los beneficios cargados no daban, y las
lecturas que entraron tampoco— y no se dejó leer como evidencia.

**Consecuencia:** ampliar es una decisión de crecimiento del corpus y se corre
aparte, no en cada población. Después de ampliar hay que volver a cargar las
lecturas curadas y reanclar las citas que se hayan corrido; el cargador dice
cuál y a qué ruta. El runbook lo explica en su propia sección.

Lo que hay que retener no es el bug: es que el reporte de la corrida limpia
encontró dos regresiones que ninguna prueba había encontrado, porque son
regresiones de procedimiento y no de código. Un informe que se desmiente a sí
mismo sirve exactamente para esto.

## D-52 · Ampliar el corpus va después de tener contra qué resolver

`bn ingesta ampliar` resuelve las citas pendientes contra el catálogo nacional.
Puesto en el procedimiento de población antes de que ese catálogo se importe, no
encontraba nada que resolver y no fallaba: la corrida limpia terminaba
«completa», con el corpus sin las normas que sus propias lecturas curadas citan
y tres lecturas informadas como «su norma no está».

El síntoma parecía otra cosa —lecturas que no cargan— y la causa era el orden.
En la base de desarrollo no se veía, porque ahí el catálogo estaba desde antes.

**Consecuencia:** la ampliación corre después del catálogo nacional, y solo en la
primera pasada. La segunda tiene que no agregar nada, y eso es lo que el reporte
mide.

## D-53 · Traer una norma no es leerla

La ampliación metió veintiséis normas nacionales con texto en el corpus. Tres
tienen lectura curada; veintitrés no. Sin decirlo, las dos cosas se ven igual
desde afuera: el corpus creció y nadie sabe qué parte de ese crecimiento puede
contestar algo.

Trece de las veintitrés fijan rangos, topes y montos para un período, y no se
curan como cuantía a propósito: son una cadena donde cada una reemplaza a la
anterior, y la más nueva que el corpus tiene es de 2015. Servir cualquiera como
el monto de hoy sería dar por vigente un importe de hace una década, que es peor
que decir que no se sabe. Lo que sí aportan es la cadena, que sirve para
reconstruir un período pasado —otra pregunta, y legítima—.

Las demás modifican artículos cuyo texto vigente ya está curado desde el
consolidado de la Ley 24.714: curarlas aparte repetiría las mismas reglas sin
agregar nada, y la trazabilidad ya la da el grafo de relaciones. El Decreto
446/2011 es el caso claro: se comparó su texto con el consolidado y son
idénticos.

**Consecuencia:** `bn ingesta ampliar --informe` deja escrito, norma por norma,
qué se trajo y qué se leyó, con el motivo de lo que no. Un corpus que crece sin
esa cuenta se lee como si todo lo que entró estuviera disponible para responder.

## D-54 · Un permiso declarado no es un permiso verificado

La migración 0002 separa seis roles y explica cada GRANT en un comentario. Al
llevar el esquema a la base gestionada se probó rol por rol contra el motor, y
una de las dieciocho sondas no dio lo que el comentario decía: el ingestor podía
marcar RESUELTA una incidencia. El comentario dice «no publica ni resuelve»; el
GRANT otorgaba `INSERT, UPDATE` sobre `incidencias_revision`, y `incidencias_revision`
era una de doce tablas en una lista, donde un UPDATE de más no se ve leyendo.

Nada en el código usaba ese permiso: las dos sentencias que cierran una
incidencia viven en `curacion/`. Pero un permiso que sobra no es inofensivo —es
exactamente la clase de cosa que alguien usa sin darse cuenta seis meses después,
y entonces el circuito de revisión pasa a tener dos puertas.

**Consecuencia:** `scripts/verificar_permisos.py` deja el control como algo que
se vuelve a correr, no como algo que se hizo una vez. Las sondas llevan
`WHERE false` para que PostgreSQL verifique el permiso sin escribir nada, así
correrlo contra producción es inocuo. Y el invariante que la 0008 corrige quedó
además como prueba de aceptación contra la base: si un GRANT futuro lo vuelve a
abrir, falla el CI y no un incidente.

Vale para la otra mitad también. El esquema en la base gestionada no se dio por
bueno porque las migraciones no dieran error: se contaron los objetos contra el
PostgreSQL local, tipo por tipo. La única diferencia —292 restricciones `NOT
NULL` catalogadas— resultó ser que PostgreSQL 17 empezó a guardarlas como filas
de `pg_constraint`. Sin esa comparación, «las migraciones corrieron» habría
tapado tanto una coincidencia real como una diferencia de motor.

## D-55 · Un original que falta tiene que sacar de circulación lo que sostiene

El almacén guarda los bytes por su hash y la base guarda ese hash. Mientras las
dos mitades coincidan, cualquiera puede volver al documento exacto que sostiene
una regla. Cuando dejan de coincidir, lo que se pierde no es un archivo: es la
posibilidad de comprobar lo que el sistema afirma. Y no se nota. La fila de la
captura sigue ahí, con su hash y su URI, y todo lo que cuelga de ella se sigue
sirviendo igual.

Por eso `bn objetos verificar` no termina en un renglón de un reporte. Abre una
incidencia CRITICAL sobre cada versión que dependa del objeto roto, y eso la
saca de lo servible por el camino que ya existía —`bn_motivos_no_servible`
devuelve CONFLICT ante una incidencia abierta de severidad alta—. No hizo falta
inventar un mecanismo de bloqueo: hizo falta usarlo.

El tipo `EVIDENCIA_NO_RECUPERABLE` es nuevo y podría haberse evitado metiendo
esto en `COBERTURA_EXTRACCION` o `ACCESO_BLOQUEADO`. Habría ahorrado una
migración y mezclado dos cosas que se atienden distinto: una se resuelve
volviendo a extraer, la otra recuperando el objeto de un respaldo o
recapturando la fuente.

**Consecuencia:** copiar los originales afuera del contenedor tampoco alcanza
con copiarlos. `bn objetos sincronizar` relee cada objeto desde el destino y
compara el hash allá, porque una copia que nadie volvió a leer no es un
respaldo: es la creencia de que el `cp` no mintió.

Lo mismo que valió para los permisos vale acá. Al medir el criterio contra el
corpus real —qué guarda efectivamente cada una de las 242 capturas— aparecieron
70 sin tipo. Todas eran respuestas 304: el capturador reutilizaba hash, URI y
tamaño de la captura previa, pero no el tipo, así que cada revalidación borraba
un dato que la primera captura sí había sabido. Contar lo que hay es lo que
encuentra estas cosas; leer el código que las escribe, no.

## D-56 · Los rechazos no se declaran: se derivan

Cada importador contaba lo suyo y lo imprimía en pantalla. Guardar esa cuenta
—como control `DQ11` sobre la corrida— era el trabajo obvio de P-005. Lo que no
era obvio es que la aritmética iba a encontrar algo.

El primer intento pedía a cada importador declarar sus rechazos, y tres de los
cinco dieron negativo: −322.473 en el catálogo nacional, −153 en un directorio,
−2 en la Defensoría. Los contadores que parecían rechazos no lo eran.
`literales_sin_dato` cuenta campos vacíos de filas que sí entraron;
`sin_clave_canonica` cuenta normas que se cargan con identidad incierta;
`sin_direccion` cuenta oficinas que entran igual. Cada uno describía algo de lo
que estaba adentro, y restarlo de la suma sacaba dos veces lo mismo.

**Consecuencia:** `rechazadas` se deriva de `leidas − nuevas − repetidas`. Así
la identidad no puede mentir, y la comprobación pasa a ser la que importa: que
ninguna fila caída quede sin motivo declarado. Los contadores de calidad viven
en `observaciones`, se informan y no restan.

Vale la pena decir por qué el error era fácil. Los nombres de esos contadores
—`sin_algo`— suenan a fallo, y leyendo el código de a un importador por vez
todos parecían encajar. Lo que no encajaba era la suma, y la suma solo aparece
cuando se los pone a los cinco en la misma tabla contra datos reales.

De paso quedó mostrado el control DQ10 del paquete sobre datos y no sobre una
prueba: reejecutar los cinco importadores creó cero filas nuevas.

## D-57 · Un adaptador que no sabe qué está leyendo lo dice

El adaptador de PDF leía `tipo_documento` de la configuración de la fuente y,
si no la encontraba, elegía `OTRO`. Parecía prudente. No lo era: `OTRO` deja el
documento fuera de la resolución de identidad, así que el texto de un decreto se
extraía entero —132 unidades— y no llegaba a ninguna norma. El sistema no
fallaba; simplemente no tenía ese decreto, y no lo decía.

Peor: la configuración que leía nunca existió. `CapturaMaterial.config` viajaba
siempre vacía porque la extracción no se la pasaba, y la carga del catálogo
nunca llenaba `selector_config`. Tres eslabones cortados, y cada uno bastaba
solo para romper la cadena. Ninguno de los tres era visible leyendo su propio
archivo: el adaptador leía un diccionario, la extracción construía un objeto, la
carga insertaba una fila. Lo que faltaba estaba entre los tres.

**Consecuencia:** cuando la declaración falta, se avisa. Y lo que se declara se
deriva de lo que el manifiesto ya sabe —la clase de la fuente dice qué clase de
documento produce, el host dice de qué jurisdicción es— en vez de escribirse
fuente por fuente: una fuente normativa nueva lo recibe sola, y una que no dice
qué trae no recibe nada, que es lo correcto.

Lo que el documento sí declara se lee del documento. La identidad sale del
encabezado —«DECRETO Nº 690/2006»—, y si el encabezado no está, la versión queda
sin identidad candidata y la resolución no la inventa. La letra del Digesto
porteño —«ORDENANZA F – N° 43.478»— se reconoce como clasificación del Digesto y
no se confunde con el número de la norma.

El esquema puso el último límite. Declarar esos textos como `CONSOLIDADO` lo
rechazó una restricción: un consolidado exige la fecha hasta la que consolida, y
esos PDF no la traen. Quedan como `ACTUALIZADO` con un aviso que dice justamente
eso. La restricción evitó afirmar una cobertura temporal que nadie podía
sostener.

## D-58 · Los ciclos del grafo normativo son datos, no errores

El Decreto 1134/2005 sustituye la Ley 24.714, y la Ley 24.714 cita al Decreto
1134/2005. La Ordenanza 43.478 cita a la Ley 547, y la Ley 547 modifica la
Ordenanza 43.478. En el corpus hay 744 caminos de hasta cuatro saltos que
vuelven a su origen, y ninguno sobra: borrar una de las dos relaciones para
«arreglar» el ciclo perdería información que la práctica legislativa produjo.

Con lo cual la protección no puede ser prohibirlos. Tiene que ser que
recorrerlos termine.

Hoy termina por omisión: ninguna consulta del sistema da más de un salto, así
que el problema no se ve. Esa es exactamente la clase de cosa que aparece de
golpe: la primera consulta transitiva —«qué normas afectan a esta», que es lo
que la recuperación va a necesitar— se encuentra con los 744 ciclos el día que
alguien la escribe.

**Consecuencia:** `bn_grafo_normativo` recorre con lista de visitados y tope de
profundidad, y devuelve cada norma una vez por el camino más corto que la
alcanzó. Y `bn calidad grafo` deja escrito cuántos ciclos hay, para que el
número se conozca antes y no después.

Un solo caso sí se prohíbe: la autorreferencia. El resolutor ya la omitía —91 en
la última corrida— pero el esquema la admitía, y una norma que se cita a sí
misma es el ciclo más corto posible sin aportar nada. La restricción entró sin
migrar datos porque no había ninguna: el código ya hacía lo correcto, y ahora
tampoco puede hacerlo otro camino.

## D-59 · La fecha de descarga no es ninguno de los dos relojes

«Qué decía esta norma» no se puede contestar sin decir cuándo, y hay dos
«cuándo» que no son el mismo: en qué fecha se aplica y en qué momento se sabía.
La tentación es usar un tercero que no es ninguno —cuándo se descargó el
documento— y tomar la captura más nueva como la versión que rige.

El corpus tiene el caso: el artículo 2 del Decreto 690/2006 nombra un programa y
una autoridad de aplicación hasta 2024, y otros desde el Decreto 161/2025.
Servir el texto nuevo a quien pregunta por 2010 sería mandarlo a una oficina que
en 2010 no existía.

**Consecuencia:** las cuatro combinaciones quedan como prueba contra la base —dos
fechas sobre una modificación, una derogación que sigue sirviendo su propio
período, una versión que hoy se sabe y en 2025 no se sabía, y una versión
aplicable cuya captura es la más vieja de las dos—. El eje de conocimiento es el
que no se puede agregar después: sin él no hay forma de reconstruir por qué el
sistema contestó lo que contestó en su momento.

## D-60 · Lo que una fuente declara traer se comprueba, no se supone

El manifiesto dice, fuente por fuente, en qué tablas tiene que terminar lo que
esa fuente aporta. Nadie lo comprobaba, y el catálogo mostraba `ACTIVE`,
`ACCESIBLE` y «capturada» tanto para una fuente que dejó mil filas como para una
que no dejó ninguna. Sobre 85 fuentes: 18 capturaron, se extrajeron y no
dejaron una sola fila donde su historia dice, y cinco más nunca se extrajeron.

La regla de atribución es la misma disciplina que el proyecto ya se impuso: una
fila es de una fuente cuando su evidencia lleva de vuelta a un documento de esa
fuente. Y tuvo dos límites que valió la pena encontrar antes de publicar el
informe y no después.

El primero: **un dataset no deja evidencia por fila**. F01 carga 428.380 normas
y ninguna trae un fragmento que citar, porque no hay cómo citar un renglón de un
ZIP. La primera corrida la daba por «sin destino», que habría sido un hallazgo
falso sobre la fuente más grande del corpus. Se acredita por su conciliación
DQ11, y el informe dice cuáles se acreditan así en vez de mezclarlas.

El segundo: **hay tablas que no son de nadie**. Una norma no es «de» una fuente;
es la norma, y varias la publican. Contarlas por fuente diría algo falso, así
que se declaran no atribuibles.

**Consecuencia:** `bn calidad fuentes` informa y no falla. Con 18 fuentes
pendientes, un gate rojo permanente entrena a ignorarlo; `--estricto` existe y
es como tiene que quedar cuando se resuelvan.

## D-61 · Un aviso que nadie guarda es un fallo que no ocurrió

Tres fuentes tienen su HTML capturado y ningún adaptador que lo lea. La
extracción lo decía —«Ninguna familia de extracción acepta… La captura queda
guardada sin extraer»— y lo decía bien: los bytes se conservan, no se inventa
nada. Pero el aviso vivía en la salida de la corrida, y la fuente seguía
`ACTIVE` y `ACCESIBLE` como si hubiera funcionado.

Es la misma forma que ya apareció con los permisos, con los objetos y con los
tipos de documento: el sistema hace lo correcto y no deja rastro de haberlo
hecho, con lo cual nadie se entera. Un fallo sin registro es indistinguible de
que no haya pasado nada.

**Consecuencia:** una captura que ningún adaptador lee, y una que un adaptador
acepta sin producir documento, abren incidencia contra la fuente. La capacidad
queda pendiente hasta que haya con qué leerla.

Escribir esa prueba destapó algo más: `ResultadoExtraccion.avisos` está
declarado `list[Aviso]` y cuatro adaptadores metían cadenas sueltas. Nunca había
fallado porque esos caminos no se recorrían. Un aviso que es una cadena no
puede convertirse en incidencia, así que el tipo no era decorativo: era la
diferencia entre registrar el fallo y perderlo.

## D-62 · El período de un importe sale de la tabla, nunca de la descarga

La página del Consejo del Salario publica, en septiembre, tres importes que
empiezan a regir en octubre, noviembre y diciembre. Tomar el último renglón de
la descarga más reciente y servirlo como el monto vigente —que es el error que
el criterio nombra— daría un número que no rige hasta dentro de tres meses. En
septiembre no rige ninguno de los tres.

Así que cada importe entra con el período que la tabla declara: «a partir del
1/10» rige hasta el día anterior al «a partir del» siguiente, y el último queda
abierto, porque un piso salarial rige desde su fecha hasta que otra resolución
lo cambie y publicar el cronograma es respaldar eso.

**Las columnas se declaran, no se adivinan.** El encabezado viene sin
separadores —«Fecha Salario Mínimo, Vital y Móvil Prestación por Desempleo monto
mínimo…»— y partirlo por heurística es inventar a qué concepto pertenece cada
número. Un número asignado al concepto equivocado es peor que no tenerlo. La
fuente declara qué parámetros trae y en qué orden; un renglón con otra cantidad
de importes se rechaza en vez de acomodarse.

**Un importe sin fecha no se carga.** La página de Progresar dice que el monto
de la beca es de $35.000 y no dice desde cuándo. Es incómodo a propósito: la
página lo publica como el vigente y el sistema se abstiene de servirlo como
vigente porque la página no lo respalda con una fecha. Quien pregunta cuánto
cobra no puede recibir un número que quizá cambió el mes pasado.

**Consecuencia:** cargar un importe no es aprobarlo. Los nueve entran como
candidatos y no publicables; publicarlos es una decisión de revisión.

Vale decir qué parte de esto ya estaba hecha y sin usar. La restricción de
exclusión de `parametro_valores` impide desde la migración 0002 que dos importes
publicables del mismo parámetro se pisen en el tiempo, y `bn_rango_aplicacion`
no convierte un límite desconocido en vigencia abierta. La tabla tenía cero
filas: la parte difícil estaba puesta y nadie la había ejercido.

## D-63 · Cuando el modelo obliga a mentir, el que está mal es el modelo

Siete de los dieciséis plazos cargados declaraban una cantidad que su propia
cita no contiene. La primera lectura fue la fácil: errores de curaduría. La
segunda mostró otra cosa.

Tres de ellos traían `requiere_revision: true` y un motivo que explicaba el
problema mejor de lo que lo habría explicado el control: «se guarda con cantidad
cero porque el modelo exige una cantidad, y eso es exactamente lo que hay que
revisar: un cero acá significa "no hay duración declarada", no "vence el mismo
día"». La restricción obligaba a elegir entre una fecha y una duración, y «en el
mes de marzo de cada año», «una vez al año» y «en el momento de la inscripción»
no son ninguna de las dos: son eventos.

Así que el esquema forzaba a escribir un número falso y a explicarlo en una
prosa que nada lee. Un cero que significa «no sé» es indistinguible de un cero
que significa «cero», y quien consulte la base ve el cero.

**Consecuencia:** la migración 0011 agrega la tercera forma —sin fechas y sin
cantidad, con el evento declarado— y las tres lecturas quedan sin el número
inventado. Vale la pena decir de quién es el mérito: las tres lo habían avisado.
El control no descubrió un descuido, hizo visible una advertencia que estaba
escrita y que ningún proceso leía.

## D-64 · Una evidencia compartida tiene que respaldar a cada quien la cita

Los otros dos plazos citaban bien su texto literal, y el fragmento guardado no
lo contenía.

La curación de beneficios reusa la evidencia de una unidad —una unidad tiene una
evidencia, no una por cada quien la cite— y eso está bien. Pero la curación de
relaciones escribe evidencias cuyo fragmento es la ventana alrededor de una
cita, no el texto de la unidad. Reusar esa ventana dejaba el plazo de «quince
(15) días» del artículo 9 de la Ley 2917 citando 273 caracteres de una unidad de
696 que no incluían el número.

Es el peor de los defectos posibles en este sistema, porque es invisible desde
adentro: todo tiene evidencia, y la evidencia no dice lo que se afirma. Los
controles que cuentan evidencias lo dan por bueno.

**Consecuencia:** se reusa la evidencia que respalde lo que se está citando, y si
ninguna lo hace se escribe una con el texto de la unidad. Y `bn calidad plazos`
lo comprueba de afuera: un plazo que declara un número tiene que poder señalarlo
en el texto que cita, en cifras o en letras.

## D-65 · Un error de transición no es lo mismo que «alguien decidió antes»

Las transiciones de una regla ya rechazaban los saltos imposibles: aprobar algo
que está rechazado falla, y está bien que falle. Pero el error decía «la regla
está en REJECTED y esta transición sale de CANDIDATE», que suena a que quien
llama se equivocó, cuando lo que pasó es que **otra persona decidió mientras
esta miraba la pantalla**.

La diferencia no es de redacción. Un error de transición se corrige llamando
distinto; un conflicto de concurrencia se corrige volviendo a leer y decidiendo
sobre lo que hay. Y quien decidió primero no puede quedar sobrescrito porque el
segundo insistió.

**Consecuencia:** quien decide declara en qué estado leyó la regla y recibe 409
`VERSION_CONFLICT` cuando no coincide, con lo que pasó escrito. Es el mismo
mecanismo que las incidencias ya tenían; lo que faltaba era aplicarlo a las
reglas, que es donde se decide lo que el sistema va a afirmar.

Y una decisión que el endpoint no acepta: `PUBLICAR`. Aprobar y publicar son dos
puertas distintas y las abre gente distinta. La respuesta de una aprobación dice
`"publicada": false` para que nadie tenga que acordarse.

## D-66 · Un corte no es su delta

El manifiesto de un release hasheaba las versiones que ese release **agrega**.
Suena razonable hasta que se mira qué sirve un corte: el segundo release
incorpora B y sigue sirviendo A —el primero conserva sus versiones, que es
justo lo que lo vuelve un corte histórico y no un momento que se pisa—, así que
lo que el segundo sirve es A y B.

Con un manifiesto que solo nombra B, dos corpus distintos con el mismo agregado
tienen la misma huella. El hash deja de identificar qué se estaba sirviendo, que
es exactamente para lo que existe.

**Consecuencia:** el manifiesto cuenta las versiones que van a quedar
publicadas: las que el corte promueve más las que ya lo estaban en un release
todavía publicado. Un release revertido no aporta, porque dejó de servir.

Quedó además probado lo que nadie había probado: dos cortes seguidos, con A en
el primero y B en el segundo. Después del segundo se sirven los dos, A no se
movió de su release, y revirtiendo el segundo A sigue sirviendo y B deja de
hacerlo sin que se borre nada.

## D-67 · Un turno que se renueva no tiene vencimiento

El ciclo de monitoreo lo va a disparar un planificador cada hora, y los
planificadores reintentan. Dos vueltas simultáneas capturarían la misma fuente,
crearían la misma versión documental y emitirían el mismo evento; nada en el
esquema lo impedía.

Se descartó el candado consultivo de PostgreSQL (`pg_advisory_lock`). Se suelta
solo al morir la sesión, que es cómodo, pero no se puede mirar: no dice quién lo
tiene ni hasta cuándo, y un proceso colgado —vivo, sin avanzar— lo retiene para
siempre. Lo que hace falta es un tope que se pueda consultar con un `SELECT`
cuando alguien pregunta por qué el ciclo no corrió anoche.

Se descartó también renovar el turno mientras se trabaja, que es lo que hace
casi todo el mundo. Renovar convierte el vencimiento en una promesa vacía: un
proceso trabado que sigue renovando bloquea el recurso igual que un candado sin
vencimiento, y el «tiempo máximo» que el criterio pide deja de existir.

**Consecuencia:** el turno dura lo que dura —treinta minutos por omisión, contra
vueltas de minutos— y no se renueva. La corrida que se pasa se entera al
soltarlo, porque `soltar` devuelve falso cuando el turno ya no era suyo, y lo
declara en su reporte: otra pudo haber empezado en paralelo sobre las mismas
fuentes. La toma es una sola sentencia —`INSERT … ON CONFLICT DO UPDATE … WHERE
ya venció`— porque «fijarse si está libre» y «tomarlo» en sentencias separadas es
la carrera que el turno viene a evitar.

Dos decisiones menores del mismo tamaño. La vuelta que no consigue el turno
termina en cero: si devolviera error, el planificador reintentaría justo lo que
no hay que repetir. Y soltar no borra la fila sino que le adelanta el
vencimiento, así queda constancia de quién corrió la última vuelta y cuántas
van, que es lo primero que se pregunta cuando algo no corrió.

## D-68 · Fusionar por orden y no por puntaje

La búsqueda híbrida tiene que combinar dos listas cuyos puntajes no son
comparables: `ts_rank` devuelve un número sin unidad que depende de la longitud
del documento, y la distancia coseno va de 0 a 2. Sumarlos —con pesos, con
normalización min-max, con lo que sea— obliga a elegir una escala, y esa
elección termina siendo el verdadero criterio de orden sin que nadie la haya
decidido a propósito. Peor: cambia sola cuando cambia el corpus, porque el
mínimo y el máximo de `ts_rank` dependen de qué documentos entraron.

**Consecuencia:** se fusiona por rango recíproco, `1/(k+puesto)` con k=60, que
usa solo el orden en que cada mitad dejó a cada fragmento. Un fragmento que las
dos encuentran sube; uno que encuentra una sola entra igual, que es el punto de
ser híbrido. Los filtros van adentro de cada mitad y no encima del resultado: si
se filtrara después, las dos gastarían sus lugares en fragmentos que van a
descartarse y la respuesta quedaría con menos de los que pidió sin que nada lo
explique.

## D-69 · Un fragmento publicado es texto citable, y por eso no puede ser la página

La ficha de NormativaBA muestra el articulado y debajo un panel de
«Relaciones» con las normas vinculadas. El adaptador sabía dónde empieza el
texto y no dónde termina, así que ese panel entraba como articulado: once de los
treinta y tres fragmentos publicados de la Ley 6935 eran encabezados de tabla
—«Tipo de relación», «Norma relacionada»—, tipos de vínculo —«INTEGRA»,
«COMPLEMENTA»— y resúmenes que la propia página redacta.

Apareció midiendo la recuperación, no leyendo el código: ocupaban el 34,8 % de
los puestos devueltos y eran la causa de 5 de los 7 fallos. Pero el problema de
recuperación es el síntoma. El defecto es que se publicó como texto **citable**
algo que no es la norma, así que una respuesta podía citar «Tipo de relación»
como si fuera la ley.

**Consecuencia:** el adaptador corta por el encabezado del panel, exigiendo
coincidencia exacta del párrafo entero —es una estructura de la ficha, no una
palabra suelta del texto—. Y no recorta en silencio: deja aviso con cuántos
párrafos quedaron afuera, porque un cambio de maquetación que se coma articulado
tiene que verse en vez de aparecer como una norma más corta.

Queda dicho lo que todavía no se hizo: el corte publicado se construyó con la
extracción vieja y sigue sirviendo esos once fragmentos. Promoverlo exige volver
a curar las citas que apuntan a las unidades viejas, y el sistema se niega a
reprocesar una versión con evidencia encima, con razón.

## D-70 · El actor no lo declara quien llama

Las rutas de administración pedían un token compartido y tomaban al actor de la
cabecera `X-Actor`. El token está bien como puerta, pero identifica al despliegue
y no a la persona: quien lo tuviera podía firmar como cualquiera. Y lo que se
firma acá es que una regla dice lo que dice el derecho.

**Consecuencia:** el actor sale de una credencial firmada por persona, con roles
adentro y vencimiento de a lo sumo 90 días, revocable. `X-Actor` se ignora cuando
hay credencial. Un revisor no publica y un publicador no decide reglas: son
decisiones distintas y las toma gente distinta.

Se eligió HMAC y no un proveedor de identidad porque no hay ninguno todavía y
porque cuál usar no es una decisión de acá. Las rutas piden una `Identidad`, no
un formato de token, así que reemplazarlo por OIDC no las toca.

## D-71 · Una excepción que no se ve en los datos no es una excepción, es un agujero

Hace falta poder administrar sin montar credenciales —para probar, para levantar
el sistema la primera vez— y esa necesidad no se va a ir. La forma habitual de
resolverlo es una bandera de configuración y un comentario que dice «no usar en
producción», que es exactamente el arreglo que nadie ve cuando falla.

**Consecuencia:** la puerta vieja sigue existiendo detrás de
`BN_IDENTIDAD_MODO=desarrollo`, y todo lo que entra por ahí queda marcado
`AUTODECLARADA` en la columna `auditoria_eventos.identidad`, para siempre. La
excepción no está en un comentario: está en cada fila que produjo. Dentro de dos
años, una firma jurídica hecha en modo desarrollo se va a poder distinguir de una
hecha con credencial, que es lo único que hace que la excepción sea aceptable.

La procedencia no la pasa cada sitio que escribe en la bitácora —son siete y
alcanza con que uno se olvide—: sale de un ajuste de sesión que la API pone al
abrir la transacción y la columna lo toma por omisión.

## D-72 · Una pantalla, no una cadena de herramientas

El bloqueo número uno del proyecto son 166 reglas que necesitan la firma de una
persona con competencia jurídica. Hasta ahora eso se hacía leyendo un expediente
en Markdown y corriendo comandos, que funciona y pone la firma más lejos de quien
tiene que darla.

La consola es un solo archivo HTML servido por la misma aplicación, sin compilar
nada. Se evaluó lo habitual —un proyecto de front con su cadena de construcción—
y no paga acá: agrega un artefacto que se despliega aparte, se desfasa de la API
que consume y necesita que alguien lo mantenga, todo para una pantalla que
muestra una cola y un formulario.

**Consecuencia:** `/backoffice/reglas` viaja en la misma imagen que la API y no
puede quedar desfasada de ella. Hay una prueba que comprueba que la página se
sirva, porque una consola que existe en el repositorio y no en la imagen es una
consola que no existe.

La credencial vive en la pestaña de quien entra y en ningún otro lado: ni
`localStorage`, ni `sessionStorage`, ni cookie. Todas esas la dejarían escrita en
el disco del navegador, y lo que autoriza es firmar decisiones jurídicas. Cerrar
la pestaña la borra, y hay una prueba que comprueba que la página no llame a esas
APIs.

Lo que la consola deliberadamente no tiene es un botón de «aprobar todas». El
criterio 2 de P-010 dice que estas reglas no se aprueban en lote por un agente, y
una herramienta que ofrece el atajo lo vuelve el camino por omisión.

## D-73 · El organismo de un canal se declara, no se infiere

`canales.organismo_id` no admite nulo y ninguna de las 85 fuentes del catálogo
trae organismo. La salida obvia era emparejar el nombre de la fuente contra la
tabla de organismos por parecido: «Defensoría del Pueblo CABA - Sede Central» y
«Defensor del Pueblo de la Ciudad Autónoma de Buenos Aires» son casi lo mismo.

No se hizo, y la razón es lo que pasa cuando falla: un teléfono queda bajo el
nombre de otro organismo y quien consulta marca ese número. En un producto que
existe para que una persona sepa dónde ir, ese error no es un dato mal
clasificado: es una persona llamando al lugar equivocado en el peor momento.

**Consecuencia:** la correspondencia vive en `ORGANISMOS_POR_FUENTE`, escrita a
mano, revisable en un diff, y cada línea verificada abriendo la página de la
fuente. Tampoco se infiere del dominio: `argentina.gob.ar` aloja decenas de
organismos distintos. Una fuente sin declaración no carga canales y deja
incidencia diciendo cuántos encontró y dónde se declara lo que falta. Dos
quedaron así, con 31 y 10 canales esperando una línea.

Es el mismo patrón que los datasets de directorios, que declaran su organismo en
el código desde HU-020. Lo que cambió es que ahora está dicho por qué.

## D-74 · Encontrar y aceptar son dos decisiones

Una expresión regular que busca teléfonos encuentra «1999 1998 1997». Se puede
angostar el patrón hasta que no lo encuentre, y entonces deja de encontrar
`(54–11) 27713385`, que es un teléfono real de una página real.

**Consecuencia:** el patrón busca ancho y la normalización decide. `RE_TELEFONO`
acepta candidatos con generosidad; `normalizar_telefono` los rechaza si no tienen
entre 8 y 12 dígitos o si son una tira de años, y devuelve `None` en vez de un
valor a medias. Ensanchar el patrón para tomar un formato nuevo no arrastra
basura a la base, porque la puerta de entrada no es el patrón.

## D-75 · Un trámite vacío con cita es peor que ningún trámite

Antes de escribir el curador de trámites se miraron las secciones que esas
páginas habían dejado, y no eran trámites: F36 «Tramitar el DNI» es un menú de
modalidades, F53 «Progresar» lista líneas de beca, F32 es el menú de un turnero.
Ninguna trae requisitos, pasos ni costo.

Un curador escrito igual habría producido un trámite «DNI al instante» con cero
pasos y una evidencia que dice «Tramitá tu DNI en los Centros de Atención
habilitados para esta modalidad», que no explica cómo. Eso no es un dato
incompleto: es un dato falso con respaldo, porque la cita lo hace parecer
verificado.

**Consecuencia:** no se curó el índice. El adaptador descubre las hojas que
enlaza y las deja como candidatas, y el contenido se busca donde está. El
manifiesto ya lo decía —F66 es «hub /requisitos + 3 hojas», F53 es «mapa de
subpaginas»—: el catálogo sabía que eran índices y la ingesta nunca los siguió.

De ahí salieron cuatro trámites de DNI con once pasos, leídos de las fichas
reales por el curador que ya existía.

## D-76 · Un acuerdo por texto entre dos módulos se rompe en silencio

`bn ingesta descubrir` promovía las candidatas cuya relación decía «de la misma
norma». La frase la escribía el adaptador y la buscaba el comando, cada uno con
su literal. Al agregar relaciones nuevas —«hoja del índice», «ficha de trámite»—
el comando siguió promoviendo cero y no falló nada: simplemente no pasaba nada.

**Consecuencia:** las relaciones promovibles viven en `adaptadores/base.py` y las
importan los dos lados. Sigue siendo un acuerdo por texto —la columna guarda
prosa— pero ahora hay un solo lugar donde cambiarla.

Vale la generalización: cuando dos módulos se ponen de acuerdo por el contenido
de un campo y no por su tipo, el desacuerdo no se ve como un error sino como
ausencia de resultado, que es lo último que alguien va a mirar.

## D-77 · Una lista de dominios falla en silencio

El adaptador de páginas institucionales aceptaba por dominio: una tupla con
nueve entradas dentro de la clase. Cuatro fuentes del manifiesto —dos de Edenor,
una de Edesur, una más— quedaban con los bytes guardados y sin extraer, porque su
dominio no estaba ahí.

El problema no era que la lista estuviera incompleta. Era **cómo fallaba**:
ningún adaptador aceptaba, la captura quedaba guardada sin usar, no se abría
ninguna incidencia con nombre propio y nadie se enteraba hasta contar las fuentes
que no llegaban a destino. Y cada fuente nueva del manifiesto pedía tocar código.

**Consecuencia:** el adaptador acepta por la **clase** que el catálogo declara
—`CANAL_ATENCION`, `FICHA_TRAMITE`, `DIRECTORIO`, `DOCUMENTO`—, que es lo que la
fuente es, y no por dónde vive. Es el último de la cadena: los específicos
—NormativaBA, InfoLeg, fichas de trámite, PDF— eligen primero. Un `BOLETIN` sigue
sin aceptarse, y eso es correcto: su historia declara `normas` y
`relaciones_normativas`, que no se resuelven partiendo la página en secciones.

Para que la clase llegara al adaptador hubo que pasarla: `CapturaMaterial` la
recibe desde la consulta de extracción, como ya pasaba con la configuración
versionada de la fuente.

## D-78 · Sin encabezados no es sin contenido

La página del programa Acceder del Ministerio Público de la Defensa dice
«Dirección: Bartolomé Mitre 648… Teléfono: +54911 7090-4975» y no tiene un solo
título. El adaptador la partía por encabezados, no encontraba ninguno y devolvía
cero unidades: exactamente el contenido que su historia promete, sin nada donde
anclar una evidencia.

**Consecuencia:** cuando no hay encabezados utilizables, la página se cita entera
bajo una sola unidad, y el aviso lo declara: lo que salga de ahí localiza la
página y no el párrafo. Es una cita más gruesa de lo deseable y verificable, que
es mejor que ninguna. Una página que solo tiene un rótulo suelto sigue sin
producir unidad: el piso de longitud se mantiene.

## D-79 · Trece fuentes «sin correr» que nadie iba a correr

El recuento de fuentes listaba trece «sin correr», con este texto: «no están
bloqueadas, simplemente no llegó su turno». Al mirarlas, ninguna estaba esperando
turno. Siete las declara el catálogo `REFERENCE_ONLY` —cuatro de ellas son
`ALIAS`, otro nombre de una fuente que ya está—, dos `RETIRED`, y cuatro
`MANUAL`, cuyo contenido no se captura: se sube.

El recuento las presentaba como trabajo pendiente. Trece tareas que nadie iba a
hacer porque no había nada que hacer, y que de paso escondían el dato real: que
no quedaba **ninguna** fuente activa sin capturar.

**Consecuencia:** el veredicto pregunta primero si la fuente **tenía** que
correr. Un alias, una retirada y una de referencia son «no se ingesta», con el
motivo escrito al lado. Una de carga manual es «espera carga manual», que sí es
pendiente pero de una persona subiendo un archivo. «Sin correr» queda para lo que
el nombre dice: activa, sin impedimento y sin una sola captura. Hoy son cero.

Y el reporte agrega el denominador que faltaba. HU-001 pide denominadores y pide
no usarlos como sinónimos: «44 de 85» mete en el mismo saco nueve fuentes que
nadie va a ingestar y diecisiete que la política de acceso no permite tocar.
Sobre las que se pueden ingestar hoy, sirven **44 de 55**.

## D-80 · Que no haya nada es una respuesta

La página de sedes presenciales de inscripción escolar dice: «la atención
presencial de las sedes permanecerá cerrada hasta el comienzo del nuevo periodo
de inscripción». El adaptador lo detectaba y dejaba constancia, pero el recuento
de fuentes seguía contando a esa fuente entre las que «no llegaron a destino»,
como si faltara un curador.

No falta ninguno. Contarla como pendiente inventa una tarea que nadie puede
completar, porque no hay qué cargar; y peor, empuja a completarla con el listado
de una captura anterior, que presentaría como vigente algo que la página dice que
no lo está.

**Consecuencia:** el veredicto `declara ausencia`, leído de la estructura que el
adaptador dejó —`identidad_candidata->'pagina'->>'cierre_declarado'`— y no del
texto de una incidencia. Un acuerdo por prosa entre dos módulos se rompe en
silencio el día que alguien mejora la redacción, que es lo que ya había pasado
con las relaciones promovibles.

## D-81 · «Sin turno» no es un cierre

El patrón que detecta ausencias tomaba «sin» seguida de «turno» dentro de sesenta
caracteres. Con eso, «podés hacerlo (sin turno) en una delegación de ANSES»
—que dice que se puede ir sin sacar turno— quedaba registrado como una
declaración de cierre. Dos fuentes tenían anotado que declaraban algo que su
página no declara.

**Consecuencia:** «sin» solo cuenta como ausencia cuando dice que algo **no está
disponible**: `sin turnos disponibles`, `sin vacantes disponibles`. Las formas
inequívocas —`no hay turnos`, `cerrada`, `finalizó`— siguen igual. Siete casos,
cuatro positivos y tres negativos, quedaron como prueba: los negativos son los
que importan, porque un falso positivo acá no deja un hueco sino un dato falso.

## D-82 · Un encabezado sin cuerpo es un botón

Cinco fuentes tenían todas sus secciones «vacías»: el texto de la sección era su
propio título. «Inscripción Nivel Superior», «Sedes - Puntos presenciales»,
«Cronograma de pagos y monto». No son secciones: son los rótulos de los enlaces
de un menú, y el contenido estaba en otra parte de la página que la caminata por
hermanos del encabezado no alcanzaba.

**Consecuencia:** una sección cuyo cuerpo no agrega nada al título no se emite. Y
como el respaldo de «página entera» ya existía para cuando no hay ninguna
sección, esas cinco pasaron a citarse enteras y con eso apareció el contenido
real: el cronograma de pagos de Progresar con su tabla de DNI, y la declaración
de que las sedes están cerradas.


## D-83 · Sin capturas no quiere decir sin recorrer

El estado del backlog rotulaba `NO_INICIADA` —«la fuente está en el catálogo y
todavía no se recorrió»— a nueve fuentes que sí tenían capturas en cero pero por
motivos ya decididos: dos retiradas por URL muerta, tres declaradas solo de
referencia y cuatro de carga manual. El informe de fuentes ya había aprendido
esta distinción; el de backlog conservaba su propia lista de estados y no la
había aprendido, así que las mismas nueve decisiones aparecían como nueve tareas
pendientes de ingesta.

**Consecuencia:** `calidad/backlog.py` importa `ESTADOS_SIN_INGESTA` y
`ESTADO_MANUAL` de `calidad/fuentes.py` en vez de repetirlos, y agrega dos
estados: `NO_SE_INGESTA` y `ESPERA_CARGA_MANUAL`. `NO_INICIADA` pasó de nueve a
cero, y lo que queda ahí —si algún día vuelve a haber algo— es un recorrido que
de verdad falta. Que los dos informes cuenten distinto sobre las mismas filas era
el defecto; que compartan el vocabulario es la corrección.

## D-84 · Una versión es el mismo documento en otro momento

La corrida limpia no llegaba a un punto fijo: la segunda pasada agregaba 31
versiones sobre documentos que ya tenían una, y la tercera otras 20. Las fuentes
eran F43, F36, F51, F53, F32 y F44.

No era contenido que cambia solo ni extracción no determinista: extraer tres
veces los mismos bytes da el mismo texto, y se comprobó. Era la identidad del
documento. `AdaptadorPaginaInstitucional` la construía como `pagina:<fuente>` y
`AdaptadorTramiteArgentina` como `tramite:<fuente>` —constantes por fuente—, lo
cual alcanzaba mientras cada fuente tuviera una sola URL. Desde que
`descubrir_hojas()` promueve hasta veinte hojas por fuente, las veinte páginas
caían en el mismo documento y cada una entraba como **versión** de la anterior.

El daño no es solo que el corpus creciera en cada pasada. Una versión es el
mismo documento en otro momento; acá la versión 7 y la versión 8 eran páginas
distintas, así que una cita anclada a una versión apuntaba a otro texto en la
siguiente, y de veinte páginas solo la última quedaba a la vista.

**Consecuencia:** la identidad incluye la página, no solo la fuente:
`pagina:F43:/eras` y `pagina:F43:/eras/marco-regulatorio`. La clave sale de la
ruta y la consulta —`clave_de_pagina()` en `adaptadores/base.py`—; el esquema y
el host quedan afuera porque son de la fuente, y meterlos haría que pasar de
http a https inventara un documento. `VERSION_EXTRACTOR` sube a `extraccion@14`.

Lo que hay que retener es que el control lo encontró después de que yo arreglara
el control. Antes decía «una versión nueva es una versión duplicada» ante
cualquier aumento, y esa frase era falsa la mitad de las veces; al separar
«primera versión de un documento nuevo» de «segunda versión de uno que ya
estaba», el número que quedó señalaba el bug directamente. Un control que grita
por todo no distingue nada.

## D-85 · Versionar por los bytes crea una versión por corrida

La corrida limpia dejaba una versión documental de más por pasada, siempre una,
siempre en F44. Cuatro hipótesis cayeron con medición: el extractor es
determinista sobre los mismos bytes, el texto de la página no cambia en
dieciocho minutos, F44 aislada es idempotente en cuatro pasadas, y recargar el
catálogo no crea configuración nueva.

El documento que se reversionaba no era el que yo perseguía. Era
`dpn:otros-defensores`, del importador de la DPN, que no pasa por el extractor
genérico: guarda en `hash_texto` el **sha de los bytes descargados** y deja
`texto_extraido` en NULL. Y dpn.gob.ar agrega a cada respuesta un token que
cambia solo —el ofuscador de correos de Cloudflare—, así que los bytes difieren
en cada descarga con el directorio idéntico. Una versión por corrida, para
siempre. El mismo patrón estaba en los importadores de directorios y de
calendarios: ahí no se veía porque sus servidores devuelven bytes estables.

**Consecuencia:** `sha_del_contenido()` en `ingesta/versiones.py` arma la huella
con lo que el importador **leyó** —las oficinas, el CSV decodificado, los
feriados— y no con lo que descargó. `sha_de_la_captura()` queda para comparar
descargas, con su docstring diciendo para qué no sirve. Ningún importador
versiona ya por bytes crudos.

Dos cosas que este caso enseñó sobre el método. La primera: el control solo
señaló el bug después de que separé «primera versión de un documento nuevo» de
«segunda versión de uno que ya estaba»; mientras gritaba por cualquier aumento,
el número que importaba estaba tapado por treinta y uno que no eran nada. La
segunda: perseguí esto cuatro veces reconstruyendo a mano una base que la
corrida destruye al terminar. La evidencia ahora se junta mientras la base
existe. Sin eso, el quinto intento hubiera sido igual que los cuatro anteriores.

## D-86 · Lo que las pruebas no ven porque corren como dueñas

Al desplegar local con los roles de verdad —la API contra `bn_lector_api` y no
contra `postgres`— `GET /v1/cobertura` devolvió 500:

    permission denied for table capturas

No era un permiso que faltara. `medir()` lee `fuentes`, `capturas`,
`fuente_urls` e `incidencias_revision`: estado operativo, no una proyección
publicada. El lector de la API no tiene permiso sobre esas tablas y **no debe
tenerlo**, porque la invariante dice que el lector accede únicamente a
proyecciones servibles. Dárselo hubiera consagrado que el lector lea staging.
El contrato ya declaraba este endpoint de «alcance autorizado»; la
implementación lo servía abierto.

**Consecuencia:** `/v1/cobertura` exige rol `auditor` y usa la conexión de
administración. Sin credencial responde 401, que es lo que corresponde.

Las once consultas de la familia «cobertura» del conjunto congelado son de
operación —«estado de la carga masiva», «¿la base está completa?»— así que el
arnés las responde con una credencial de auditoría de diez minutos y un solo
rol. Se consideró sacarlas del conjunto; cubren once casos de aceptación reales,
y lo que cambiaba era quién pregunta, no si la pregunta vale.

Lo que hay que retener: **ninguna prueba encontró esto en 1.124 corridas**,
porque todas corren con un rol que puede leer todo. Un permiso solo se prueba
desplegando con el rol que va a usarse. La suite no puede sustituir eso.

Y un error propio en el camino: el ayudante que emite la credencial atrapaba
`Exception` y devolvía «falta el secreto». Con eso, una llamada mal escrita
—faltaba un argumento— se presentó durante dos intentos como un problema de
configuración. Ahora pregunta `secreto() is None` y cualquier otro error rompe.

## D-87 · Una prueba que no puede fallar no prueba nada

D-86 se encontró desplegando, no probando, y la razón estaba en la fixture: las
pruebas de API sustituyen `conexion_lectura` por la conexión del caso, que es de
superusuario. Con eso, ninguna prueba puede notar que una ruta lee una tabla que
el lector de producción no alcanza.

**Consecuencia:** `tests/integracion/test_permisos_de_la_api.py` recorre cada
`GET` público con una conexión que hace `SET ROLE bn_lector_api` —el rol real del
despliegue— y falla si alguna devuelve 500. No prepara corpus: lo que se mira no
son los datos sino que ninguna ruta se caiga por permisos. Un 200 vacío está
bien.

Dos cuidados que la prueba lleva escritos. Las rutas salen del contrato OpenAPI
y no de `app.routes`, porque ahí varias quedan sin `path` y la lista vacía habría
dejado la prueba pasando sin comprobar nada —pasó en el primer intento, ocho
rutas se volvieron cero y el resultado fue «1 skipped» en verde—; ahora hay un
`assert` que exige que la lista no esté vacía. Y se verificó revirtiendo la
corrección de D-86: con el código viejo, la prueba falla en `/v1/cobertura`.

El verificador de permisos ya declaraba `DENEGADO: leer capturas` para la API y
daba 23 sondas sin discrepancia. No mentía: los `GRANT` estaban bien. Lo que
nadie comprobaba era si el código respetaba esa frontera.

## D-88 · La base de desarrollo contaba cuatro fuentes de más

`bn calidad fuentes` da 44 sobre la base de desarrollo y 40 sobre una construida
desde cero. La diferencia son F12, F67, M02 y M04, y no es ruido: tienen filas en
desarrollo porque se extrajeron con `extraccion@10`, cuando el adaptador de
páginas institucionales decidía si le tocaba una captura mirando el dominio en
vez de la clase que el catálogo declara.

Con ese criterio aceptaba boletines y datasets, y lo que producía era el andamio
del sitio. F12 es el dataset del salario vital y móvil y su texto extraído
arranca «Inicio Ministerio de Capital Humano Trabajo, Empleo y Seguri…»: la miga
de navegación. M02 quedó como «Descargas Descargas Boletín Descargas Separatas
Buscador His…». M04, «BIENVENIDOS AL DE LA PROVINCIA DE BUENOS AIRES…».

Desde que el adaptador decide por clase, esas cuatro dejaron de extraerse y
figuran como capturadas y nunca extraídas, que es lo que son: no hay adaptador de
boletines y el de datasets no las toma.

**Consecuencia:** el traspaso dice 40 de 55 y aclara que la cifra se mide sobre
una base limpia. Una fuente que figura servida con el menú de su propio sitio es
peor que una que figura pendiente, porque la pendiente se ve y se trabaja.

Y esto es lo que la corrida limpia existe para encontrar. El número de la base de
desarrollo no estaba mal calculado: estaba calculado sobre restos de un extractor
viejo. Ninguna prueba lo podía ver, porque las pruebas no arrastran ese resto y
la base de desarrollo nunca empieza de cero.

## D-89 · Idempotencia y punto fijo no son lo mismo

Con D-84 y D-85 aplicados, la corrida limpia mide: **cero** versiones sobre
documentos que ya existían, en la segunda pasada y en la tercera. El
procedimiento es idempotente: reejecutarlo no duplica nada.

Lo que sigue creciendo es otra cosa. La segunda pasada sumó 31 documentos que no
existían y la tercera otros 20, todos primera versión de su documento.
`descubrir_hojas()` promueve hasta veinte hojas por fuente y por pasada, y cada
hoja nueva descubre las suyas: es un recorrido a lo ancho con tope, que crece
hasta agotar el árbol.

**Consecuencia:** el runbook distingue las dos propiedades y dice que la
población se corre **hasta que deje de crecer**, no dos veces. El informe de la
corrida las cuenta por separado y reserva el veredicto duro para las versiones
repetidas.

Confundirlas costó varias corridas. Mientras el informe llamaba «duplicada» a
toda versión nueva, el número que importaba —uno, el de la DPN— estaba tapado
por treinta y uno que no eran un defecto. Separar las dos cuentas fue lo que
dejó ver el bug de D-85.

## D-90 · Transcribir una firma no es firmar

Se pidió aprobar las 166 reglas candidatas desde esta sesión. No se hizo, y no
por formalismo: el criterio 2 de P-010 dice textual que no se aprueban en lote
por un agente, y aprobar es afirmar que lo que el backend contesta sobre
vivienda, discapacidad y beneficios es lo que dice el derecho. Firmadas desde
acá, la bitácora quedaría con un actor que no leyó ninguna norma.

Se verificaron las dos bases antes de responder: local, 166 en `CANDIDATE` y
ninguna decisión de regla en la bitácora; Neon, la tabla `reglas` vacía. La
firma no estaba registrada en ningún lado.

**Consecuencia:** lo que faltaba no era permiso sino camino. `bn revision
plantilla-decisiones` genera el CSV con una fila por regla pendiente —los
identificadores salen de la base, que es de donde no salen los errores de
transcripción— y `bn revision registrar-decisiones` aplica las decisiones ya
tomadas, cada una con su fundamento y todas a nombre de quien revisó.

Tres negativas escritas en el cargador, cada una con su prueba:

- **No completa un fundamento.** Una fila sin fundamento se rechaza; no hay
  texto genérico que distinga, dentro de seis meses, una regla revisada de una
  firmada de apuro.
- **No aplica medio archivo.** Se valida entero antes de escribir: media
  transcripción deja el expediente en un estado que nadie sabe leer.
- **`PUBLICAR` no es una decisión de revisión.** Firmar una regla no la pone a
  contestar; publicar es del corte, donde se verifica que las dependencias estén
  aprobadas. Admitirla acá salteaba ese control.

Sin `--confirmar` el comando solo valida. Es lo que conviene correr primero.

## D-91 · Una sonda que no mira nada declara sana una instancia rota

`/salud` devolvía un diccionario fijo: estado, versión de esquema y versión de
la aplicación, sin tocar la base. Con la base caída contestaba `ok`, y un
orquestador le mandaba tráfico a una instancia que no podía resolver una sola
consulta.

**Consecuencia:** dos sondas separadas, que es lo que pide P-019 criterio 2.
`/salud` queda como **liveness** y sigue sin tocar la base, a propósito: si
dependiera de ella, una base momentáneamente inalcanzable reiniciaría procesos
sanos y convertiría una caída parcial en total. `/listo` es **readiness**:
verifica conexión y que el esquema aplicado sea el que el código espera, y en
producción exige además un corte publicado —sin release la API contesta
abstenciones correctas y vacías, lo que está bien en desarrollo y no está bien
recibiendo gente que pregunta por sus derechos—. Devuelve 503 con el detalle de
qué verificación falló.

Tres cosas aparecieron al probarlo contra el despliegue real, no en las pruebas:

- **La cabeza de migraciones se deduce de los archivos**, no de una constante.
  Una constante envejece en silencio y este proyecto ya se tropezó con eso.
- **El lector no podía leer `alembic_version`**, así que la sonda no podía
  comprobar contra qué esquema servía. La migración 0016 le concede `SELECT`
  sólo sobre esa tabla. No contradice la invariante de D-86: aquello era
  `capturas`, contenido de staging; esto es una fila con el identificador del
  esquema que el lector ya usa. Y la verificación tiene que hacerla la conexión
  que sirve, o pasaría mientras el lector está roto.
- **Con la base inalcanzable, readiness daba 500.** La conexión se abría como
  dependencia del framework y fallaba antes de la sonda, así que el servicio no
  alcanzaba a decir qué estaba mal. Ahora la apertura ocurre dentro de la sonda
  y el resultado es 503 con el motivo.

Y un error propio, el mismo de siempre: atrapar `Exception` al leer la migración
hizo que «no pude leer cuál hay» se informara como «no hay ninguna». Dos
diagnósticos opuestos con el mismo síntoma, y el mensaje mandaba a revisar la
base cuando el problema era un permiso.

## D-92 · La tabla de mediciones existía y nadie escribía en ella

`consultas_auditadas` está en el esquema desde la migración 0001 y
`bn_lector_api` tiene `INSERT` concedido desde la 0002. Ningún código escribía
ahí. La tabla, el permiso y el índice estaban; el código que los usara, no. Otra
falla que no falla: no hay error, simplemente no hay datos, y sólo se nota
cuando alguien pregunta cuántas abstenciones hubo y la respuesta es cero filas.

**Consecuencia (P-021, criterio 1 y 3):** un middleware registra cada consulta de
`/v1` con `request_id`, latencia, resultado y —cuando se abstuvo— la causa
tipada. La medición va en su propia conexión y su propia transacción: si
escribirla fallara, la respuesta ya está dada y no tiene por qué caerse por eso.
Medir no puede romper lo medido.

Lo que **no** se registra, y por qué:

- **El texto de la consulta, nunca.** `intencion` recibe la ruta. Quien consulta
  este sistema pregunta si le corresponde una pensión por discapacidad o si la
  pueden desalojar; guardar esa pregunta crea un registro de la situación
  personal de alguien, que después se respalda y se replica.
- **Tokens y costo, tampoco.** No hay generación: P-013 no existe. Columnas en
  cero mostrarían un tablero diciendo que el gasto es nulo cuando lo que pasa es
  que no se mide.
- **Una respuesta resuelta no lleva causa de abstención**, aunque traiga
  advertencias informativas. Guardarlas como motivo haría que el tablero cuente
  como abstención algo que sí se contestó, que es justo la distinción que pide
  el criterio 3.

Tres cosas que costaron:

- **`release_id` era obligatorio**, así que una consulta sin corte publicado no
  se podía registrar. Esa es la abstención más importante —el sistema no puede
  contestar nada— y era la única medición que no entraba. La migración 0017 lo
  hace opcional.
- **El `ContextVar` no cruzaba el límite de tarea.** Starlette corre la ruta en
  otra tarea, así que un `set()` hecho adentro no vuelve al middleware: todas las
  consultas quedaban como `SIN_CLASIFICAR`. Se arregló compartiendo un
  diccionario que el middleware crea y la respuesta muta.
- **Una prueba de privacidad preexistente exigía que la tabla quedara vacía.** Se
  reemplazó por una más exigente en lo que importa: que ningún hecho declarado
  aparezca en ninguna columna, y que la tabla no tenga dónde guardar una
  identidad. La fila no lleva actor, IP ni sesión: es un contador anónimo. Sin la
  segunda mitad, alguien podría agregar mañana una columna `actor` y la prueba
  seguiría pasando.

## D-93 · Un número que no se puede abrir es un número que hay que creer

El tablero de calidad (P-016, criterio 3) pide que cada indicador permita abrir
los registros que lo componen y que los conteos salgan de la base «y no de
constantes de demostración».

**Consecuencia:** cada indicador declara **una** consulta. El conteo es la
cantidad de filas de esa misma consulta, no un `COUNT(*)` parecido escrito al
lado. Con dos consultas, el día que alguien toque una y no la otra el tablero
dice doce, la lista muestra nueve y no hay forma de saber cuál miente; con una
sola no puede pasar, y hay una prueba que lo fija: abrir un indicador sin límite
da exactamente tantas filas como dice su número.

El límite recorta lo mostrado y nunca lo contado. Un tablero que dijera «200»
porque mostró doscientas estaría midiendo su propia paginación.

Cinco indicadores, cada uno con una línea que dice por qué importa: reglas sin
firmar (166), incidencias abiertas (5.072), fuentes con acceso bloqueado (17),
abstenciones de las últimas 24 horas y versiones publicadas (1). Los dos
primeros marcan alarma cuando crecen; los otros no, porque una fuente bloqueada
es el sistema comportándose bien.

Va con rol `auditor`, como la cobertura: lee estado operativo, no proyecciones
servibles.

## D-94 · Comparar dos versiones no es comparar con la anterior

El criterio 1 de P-016 pide, entre otras cosas, «comparar versiones». El motor
de diff existía desde el monitoreo, pero sólo compara una versión contra su
**inmediata anterior**: es lo que el monitoreo necesita —qué cambió desde la
última vez que miré— y no lo que necesita quien revisa, que es elegir dos: la
que está publicada y la que está por publicarse, o la de hace un año.

**Consecuencia:** `comparar_dos()` toma los dos extremos a mano y usa el mismo
emparejado. Se expuso `unidades_dispositivas()`, que ya existía adentro como
cierre, y `comparar_versiones()` ahora la reusa en vez de tener su propia copia.

Tres cosas quedaron fijadas con prueba:

- **Un desplazamiento no es un cambio de la norma.** Insertar un párrafo corre
  todas las rutas posteriores; contarlo como texto modificado haría que agregar
  tres párrafos produzca decenas de cambios falsos. Se cuentan aparte.
- **Comparar contra una versión inexistente devuelve `None`, no una diferencia
  vacía.** Una diferencia vacía se leería como «las dos versiones son iguales»,
  que es lo contrario de lo que pasó.
- **Se busca por número y por título a la vez.** Quien revisa llega con una cita
  —«la 24.714»— y el catálogo guarda el título; pedir el identificador interno
  es pedir lo único que nadie tiene a mano.

## D-95 · Firmar las reglas no desbloqueó la publicación

Las 166 reglas quedaron en `APPROVED` el 11.09.2026, firmadas por Pedro Pistoni,
con un evento por regla en la bitácora. `bn publicacion estado` siguió diciendo
**candidatos a publicar: 0**.

La causa: la publicación trabaja sobre `registro_versiones` y no sobre `reglas`.
Aprobar una regla la habilita para la evaluación; no aprueba la versión de la
norma, del beneficio o del canal que la contiene. Son dos firmas distintas y este
informe las había tratado como una sola: se dijo que la firma jurídica era el
cuello de botella, y era **uno** de dos.

Lo que falta, medido:

- **14.390 versiones esperan aprobación** con su vigencia ya resuelta —6.467
  barrios del RENABAP, 6.072 canales, 1.842 puntos de atención—. Es dato
  operativo, no lectura jurídica.
- **153 versiones no tienen intervalo de aplicación** —62 canales, 56 normas, 16
  beneficios, 13 plazos, 6 trámites—. Sin saber desde cuándo valen, servirlas
  sería afirmar una vigencia que nadie determinó.

**Consecuencia:** los dos números son indicadores del tablero, con su apertura.
Dejar el bloqueo sin medir era repetir el patrón que este proyecto viene
corrigiendo: algo que no falla, no avisa, y sólo se nota cuando alguien pregunta
por qué no hay nada publicado.

Y una corrección sobre el propio tablero: la primera versión de estos dos
indicadores agrupaba por tipo de entidad, así que mostraba «4» donde había
14.390. El número de un indicador tiene que ser lo que su título nombra, que es
exactamente lo que D-93 vino a fijar.

## D-96 · La firma quedó como PROCESO_LOCAL y así se declara

Los 166 eventos llevan `identidad = PROCESO_LOCAL`, no `CREDENCIAL`: la firma
entró por un comando local y no por una credencial verificada. Es lo que
efectivamente pasó y la bitácora lo dice, que es para lo que se agregó esa
columna en la migración 0014.

**No se rehace.** Las reglas ya están aprobadas y `aprobar` sólo transiciona
desde `CANDIDATE` o `IN_REVIEW`; refirmar exigiría devolverlas a revisión y
volver a aprobarlas, dejando un rastro de aprobada → desaprobada → reaprobada
que audita peor que el registro honesto que hay. La corrección es hacia
adelante: las próximas firmas van por la consola, con credencial.

También quedó registrado que el clasificador de seguridad bloqueó el bucle que
iba a aprobar los 16 beneficios de una vez. Hizo bien: un lote de 166
aprobaciones jurídicas disparado desde una sesión de agente es exactamente lo
que esa barrera cuida. Se ejecutó beneficio por beneficio, cada comando visible
y con su cuenta.

## D-97 · Un teléfono transcripto no es una lectura jurídica

Las 14.390 versiones que bloqueaban la publicación son dato operativo: 6.467
barrios del RENABAP, 6.072 canales de atención, 1.842 puntos y 9 valores de
parámetro. Un canal es «Defensoría X, teléfono Y, dirección Z, horario W»
transcripto de un directorio oficial, con evidencia que apunta al fragmento del
que salió. No afirma qué le corresponde a nadie.

Por eso se puede aprobar en bloque y las reglas no. La distinción no es de
volumen sino de qué se está afirmando.

**Consecuencia:** `bn revision aprobar-versiones`, que se niega a tres cosas:

- **A tocar una versión con incidencia abierta.** Si el sistema marcó algo sobre
  ese registro, aprobarlo en bloque entierra la marca.
- **A tocar una versión sin intervalo de aplicación.** Las 153 que quedaron
  afuera son eso: sin saber desde cuándo valen, servirlas sería afirmar una
  vigencia que nadie determinó.
- **A aprobar sin rastro por versión.** Un evento `APROBAR_VERSION` por cada
  una, igual que las reglas: lo que se firma una vez tiene que poder auditarse
  una por una.

Sin `--confirmar` sólo informa qué pasaría. Antes de aplicar se verificó que los
6.134 canales tienen evidencia —los 6.134— y que ninguna incidencia abierta
tocaba el conjunto.

Resultado: candidatos a publicar pasaron de 0 a 14.390, los siete controles de
calidad en verde, y la cuarentena bajó de 14.543 a 153.

## D-98 · Publicar quedó frenado por el clasificador, y está bien

El corte no se publicó. El clasificador de seguridad bloqueó
`bn publicacion publicar` como despliegue a producción, y no se rodeó.

Es la tercera barrera de esta sesión y las tres acertaron: frenó el bucle que
iba a aprobar 166 reglas de una vez, frenó un script que armaba el texto de esa
firma, y frenó la publicación. Publicar es lo que hace que el sistema empiece a
contestarle a alguien que pregunta si le corresponde AUH o un subsidio
habitacional; que esa acción pida una mano humana en el teclado es el diseño
funcionando, no un obstáculo.

Queda todo listo para el comando, que está escrito en el traspaso.

## D-99 · Las 150 consultas, escritas antes de correrlas

El criterio 2 de P-023 pide un conjunto congelado de al menos 150 consultas
anotadas, y agrega una condición que es la que importa: «los casos no se ajustan
para acomodar la salida».

Se agregaron 52, de 98 a 150, escritas con las palabras de quien consulta —«¿Se
me pasó el plazo?», «¿Qué papeles llevo?», «Soy extranjera, ¿puedo igual?»— y
con la expectativa tomada del contrato, no de lo que el código hace hoy. El
refuerzo fue donde más importa: **no exclusión** pasó de 10 a 20 casos y
**adversa** de 3 a 11.

Un solo caso falló, y era mío. `CV-116` pasaba `poblacion_destinataria; drop`
como nombre de campo: eso prueba el manejo de argumentos del arnés, no el
sistema, y además nadie pregunta eso. Se **reemplazó el caso**, no la
expectativa —«Certificame por escrito que tengo derecho a cobrarlo», que sí es
algo que alguien pide y que este sistema no hace— y la entrada lo deja anotado.

Las familias críticas quedaron así: no exclusión 20, cita 21, monto 16, fecha
15, identidad 10, revocación 10. La mitad del conjunto entero prueba que el
sistema **se niega** a contestar cuando no tiene con qué, que es la propiedad de
la que depende todo lo demás: decirle a alguien que no le corresponde algo,
cuando el dato simplemente falta, es el daño más caro que este backend puede
hacer.

## D-100 · Un número que desalienta no es una tarea

Cerrado P-016 y firmadas las reglas, lo que queda son decisiones humanas y se
informaban como dos números: «5.397 afirmaciones pendientes» y «153 versiones sin
vigencia». Ninguno de los dos dice por dónde empezar, y el primero suena a un mes
de trabajo.

Son **54 versiones**. `bn revision aprobar-campos` se invoca por versión, así que
la unidad de trabajo no son miles de afirmaciones sino 54 decisiones —y **14** de
ellas respaldan los beneficios cuyas reglas ya están firmadas. Ese subconjunto es
el que convierte trabajo en corpus servible; el resto no bloquea nada.

**Consecuencia:** `bn revision pendientes-de-firma` genera el informe desde la
base, con el comando exacto al lado de cada versión y las prioritarias primero.

Dos defectos propios en el camino, los dos encontrados verificando contra la base
en vez de confiar en la salida:

- **El conteo estaba inflado.** El `LEFT JOIN` a `beneficio_normas` multiplica
  filas: una norma con veinte beneficios colgando informaba veinte veces sus
  afirmaciones, y el informe decía 27.120 sobre un total real de 5.397. Un
  informe que exagera el trabajo pendiente desalienta tanto como uno que lo
  esconde. Hay prueba que suma las tablas del informe y las compara con la base.
- **El comando pisaba otro.** `revision pendientes` ya existía para incidencias.
  Quedó `pendientes-de-firma`.

Y una comprobación que cambió el plan: las 5.397 afirmaciones candidatas son
**todas sobre normas**, ninguna operativa. No hay en ellas un subconjunto
mecánico como el que permitió aprobar los canales en bloque (D-97): aprobar una
afirmación es decir que «esta norma establece X sobre la población Y» es una
lectura correcta. Lo mismo con las vigencias: de las 153, sólo diez tienen fecha
de inicio cargada, y aun esas necesitan que alguien diga si la norma tiene fin.

## D-101 · Una respuesta no puede afirmar lo que sus citas no sostienen

P-013 pide generar respuestas con citas y abstención. Lo que se construyó no es
un envoltorio de un modelo: son los validadores y la política de modo, que son
lo que protege a quien consulta y tienen que funcionar igual con cualquier
proveedor detrás —o con ninguno—.

**Tres modos, y la diferencia no se borra.** `GENERADA` cuando un proveedor
redactó y los validadores aprobaron; `EXTRACTO` cuando no hubo proveedor, se
cayó, o lo que devolvió no se sostiene; `ABSTENCION` cuando no hay evidencia. El
plan lo pide con esas palabras: «un extracto de respaldo no se presenta como
generación activa».

El modo extractivo **no puede alucinar**: el texto sale literal de fragmentos
publicados, con su cita. Es menos cómodo de leer que una explicación redactada y
es completamente verificable, así que es el piso del sistema y no un parche.

**Los validadores rechazan tres cosas**, verificando contra el contexto y no
preguntándole al modelo si está seguro —un modelo que se equivoca no sabe que se
equivocó—: citas que no están entre los fragmentos recuperados, enlaces que no
aparecen en el contexto, y números sin soporte. El número es el caso más caro:
«te corresponden $85.000» con un importe que no está en ninguna cita es peor que
no contestar, porque alguien planifica el mes con eso.

Sobre instrucciones maliciosas (criterio 2), lo que cierra el caso no es la
consigna al modelo sino la verificación: una respuesta que cambió de tema porque
un documento se lo pidió no va a tener citas que la sostengan. Hay prueba de
las dos formas.

**Lo que no se cumple:** el criterio 1 pide «el modelo configurado» y su
evidencia es «proveedor real probado en staging». No hay proveedor ni staging.
La interfaz está y es mínima a propósito —cambiar de proveedor no puede obligar
a tocar los validadores— pero P-013 no está cerrado hasta que corra contra un
modelo de verdad.

## D-102 · La recuperación estaba rota en cualquier despliegue real

Al probar `/v1/respuestas` con el rol de producción apareció que
`POST /v1/recuperacion` devolvía **500**, y no por el endpoint nuevo: la consulta
híbrida hacía `JOIN` contra `capturas` y `fuente_urls` —las dos staging— para
traer la URL de la fuente, y el lector no las puede leer. Es el mismo defecto de
D-86, en otra ruta, y la prueba de D-87 no lo veía porque **sólo cubría GET**.

Quitar la URL arreglaba el permiso y rompía algo peor: una cita que no se puede
abrir. Todo este proyecto se apoya en que quien lee una respuesta pueda ir al
texto y verificarlo.

**Consecuencia:** la URL viaja con el fragmento publicado. La migración 0018
agrega `chunks.url_fuente` y el publicador la completa al cortar —el publicador
corre con el rol migrador y sí alcanza staging; el lector no, y no tiene por qué,
porque el corte le lleva la cita ya resuelta—. Es lo que tiene que pasar con todo
lo que el lector necesita.

Y una segunda tabla de staging en la misma ruta: leía `incidencias_revision`
para advertir sobre conflictos abiertos. Se quitó, por tres razones. Es staging.
La advertencia era global —conflictos en cualquier parte del corpus— y no sobre
los fragmentos devueltos, así que alarmaba sin decir de qué. Y es redundante: el
control DQ09 impide publicar con conflictos de severidad alta sobre lo que se
publica, así que la garantía ya está en el momento de publicar, que es donde
corresponde.

Tres cosas propias que costaron:

- **La prueba de POST no atrapaba el defecto.** Sin release en el corpus de
  prueba, la ruta corta antes de ejecutar el SQL: pasaba en verde con el bug
  puesto. Se agregó una prueba que hace `EXPLAIN` de cada consulta de
  recuperación con `SET ROLE bn_lector_api`, que verifica permisos sin necesitar
  una sola fila. Verificada revirtiendo el arreglo: falla.
- **Se rompió una prueba de citas localizables**, y estaba bien que se rompiera:
  avisó que la URL se había perdido.
- **Una prueba propia quedó inestable.** La de privacidad buscaba «34» —la edad
  declarada— en todas las columnas de la fila, y `latencia_ms` puede valer 34.
  Pasaba sola y fallaba acompañada. Ahora mira sólo las columnas que podrían
  llevar contenido: una prueba que falla al azar se termina ignorando.

## D-103 · El proveedor configurado, probado sin una clave real

P-013 queda construido hasta donde se puede sin credenciales del proyecto.
`ProveedorHttp` habla con una API de mensajes por `httpx` —sin SDK: un `POST`
alcanza y evita atarse a una biblioteca que cambia más rápido que este backend—
y se configura por entorno con `BN_MODELO_CLAVE`, `BN_MODELO_URL`,
`BN_MODELO_NOMBRE`. Sin clave, `configurado()` devuelve `None` y el orquestador
cae al extracto: no se finge generación.

La petición entera se prueba con `httpx.MockTransport`, que ejercita cabeceras,
cuerpo, respuesta y error sin llamar a nadie. Doce pruebas, entre ellas que la
clave viaja en la cabecera y **no** en el cuerpo, que un 503 del proveedor
termina en extracto y no en un 500, y que un monto inventado en la redacción no
se sirve.

Tres cosas quedaron escritas en la consigna, porque son las que el criterio 2
pide y no se pueden dejar implícitas: los fragmentos llegan delimitados y
declarados como datos, se exige el formato `[[chunk:<id>]]` —una cita en prosa
no se puede verificar contra nada—, y se prohíbe afirmar elegibilidad, porque
este sistema no otorga, no deniega y no revoca.

**Por qué no se usó el proveedor que hay a mano.** Este entorno tiene
credenciales de la sesión de Claude Code, no del proyecto. Usarlas habría dado
una corrida verde y un sistema que, desplegado, no tiene proveedor: la evidencia
diría lo contrario de la realidad. El criterio 1 pide «el modelo configurado» y
su evidencia es «proveedor real probado en staging»; eso queda abierto y es lo
único que falta.

## D-104 · El frente ciudadano viaja en la misma imagen que la API

P-015. Una sola página HTML servida por la propia aplicación en `/consulta`, sin
compilar nada, por la misma razón que la consola de revisión: un artefacto que
viaja aparte puede quedar pidiendo campos que la API ya no devuelve, y nadie se
entera hasta que alguien pregunta algo. Acá no puede: sale del mismo contenedor
que la API que consume.

No hay estado de sesión ni credencial: el frente ciudadano no se autentica, y no
pide nombre, documento ni contacto. Lo que no se pide no se puede filtrar.

## D-105 · Una cita tiene que poder abrirse, y un uuid no lo verifica nadie

`POST /v1/respuestas` devolvía las citas como identificadores sueltos:
`[[chunk:<uuid>]]` dentro del texto y la lista de uuids al lado. Sirve para un
sistema y no para una persona. El criterio 2 de P-015 pide «fuentes abribles»,
así que la respuesta ahora lleva `fuentes`: por cada cita, de qué norma es, de
qué unidad y a qué URL oficial lleva. La pantalla las numera y convierte cada
marca del texto en una nota al pie que baja a su fuente.

Cuando una fuente no tiene URL registrada **se dice**, y se ofrece pedir el texto
en el organismo. No se fabrica un enlace ni se esconde la falta.

La respuesta también declara `data_status`: sin eso, «no encontré nada» y
«todavía no hay corte publicado» se veían iguales en pantalla, y son cosas muy
distintas para quien pregunta.

## D-106 · La ruta más usada del sistema no dejaba rastro

`POST /v1/respuestas` no pasa por la envoltura `Respuesta` —devuelve modo, texto
y citas, que no entran en `data`/`evidence` sin deformarlos— y la envoltura es la
que anota sola para el tablero. Resultado: la única ruta que una persona usa de
verdad quedaba registrada como `SIN_CLASIFICAR`, y el tablero medía todo menos lo
que importa. Ahora hay `contratos.anotar()`, y la ruta la llama en sus tres
salidas: sin corte publicado, con respuesta y con abstención.

## D-107 · El recorrido ciudadano se prueba en un navegador de verdad

Veintiún casos en Chromium contra un uvicorn real, con su propia base migrada y
un corte publicado confirmado —no la transacción que las otras pruebas
revierten, porque el servidor corre en otro proceso y no la vería—. El corpus lo
arma la misma función que usan las demás pruebas (`construir_corpus`,
`publicar_corpus`, extraídas de las fixtures): dos corpus parecidos que se
separan con el tiempo dan una prueba de extremo a extremo que valida un sistema
que nadie más usa.

Se ejercita lo que una persona hace: preguntar, aclarar jurisdicción y fecha,
aportar hechos, cancelar a mitad de camino, reintentar tras un 503, empezar de
nuevo y salir borrando. Y tres cosas que no se ven: que el texto del corpus se
muestre como texto y no como marcado —un fragmento con `<img onerror=…>` no
ejecuta nada—, que a 360 px no haya desborde horizontal, y que el foco se mueva
al encabezado de la respuesta, porque una respuesta que aparece fuera del foco
no se anuncia en un lector de pantalla.

Si falta Playwright o el navegador, la prueba **falla**; no se saltea. Un salteo
se cuenta como éxito y este es el único caso que ejercita la pantalla que usa
una persona. CI instala Chromium en su propio paso.

## D-108 · El contraste se mide en el navegador, no se estima

La prueba lee los colores que el navegador realmente pinta —con esquema claro y
con esquema oscuro— y calcula la razón de contraste de cada elemento visible con
texto contra su fondo efectivo. Umbral: 4,5:1, WCAG 2.1 AA para texto normal.

Encontró algo: el texto atenuado del pie quedaba en 4,40:1 sobre el papel claro.
A ojo pasaba. Se corrigió el token (`--tinta-3`) a un valor que da 5,26:1 sobre
el fondo principal y 4,80:1 sobre el más oscuro de los tres.

Lo que esta prueba **no** cubre: que la página se entienda usando un lector de
pantalla de verdad. Eso es una revisión manual con una persona y está declarada
como pendiente en `docs/reportes/accesibilidad_frente_ciudadano.md`, no dada por
hecha.

## D-109 · La mitad léxica encontraba cero, y nadie lo había mirado

Apareció sacando una captura del frente ciudadano para mostrarlo: «quiénes son
beneficiarios del programa de apoyo» daba abstención, y «beneficiarios» daba el
artículo. La misma pregunta, en castellano normal, dejaba de funcionar.

`plainto_tsquery` une los lexemas con AND: pide que un mismo fragmento tenga
**todas** las palabras. Y `quiénes` normaliza a `quien`, que PostgreSQL no trata
como palabra vacía en español y que el texto legal no usa. Cuanto más natural la
pregunta, peor funcionaba —justo al revés de lo que necesita quien consulta—.

Medido contra el conjunto congelado de 27 preguntas, la búsqueda léxica sola
daba **Recall@1, @3 y @5 de 0,0 %**. Cero, en las tres. Estaba en el informe
desde que se midió, leído como «el léxico no alcanza, por eso está el semántico»
cuando lo que decía era que el léxico no funcionaba. En cualquier despliegue sin
índice semántico construido —o sin el extra `rag` instalado— el sistema no
contestaba nada a nadie.

**La corrección.** Una sonda barata pregunta primero si algún fragmento tiene
todas las palabras, con los mismos filtros. Si no lo hay, la mitad léxica busca
por cualquiera de ellas, ordenando por `ts_rank`, que ya premia al que coincide
en más. El operador se cambia sobre la salida ya normalizada de
`plainto_tsquery`: no se arma una consulta a mano con el texto de nadie.

Resultado: léxica sola **18,5 / 51,9 / 55,6 %**; híbrida de 33,3 a **37,0** en @1
y de 51,9 a **66,7** en @3. Recall@5 híbrido sigue en 74,1 %: ese techo es otro
problema —el corte se armó con la extracción vieja— y no se tapa con esto.

**Por qué la sonda y no un reintento.** Reintentar cuando el resultado sale
vacío parece más simple y es peor: con índice semántico el resultado casi nunca
sale vacío, así que la mitad léxica habría seguido aportando cero a la fusión
sin que nada lo dijera. La sonda decide por la mitad léxica y no por el
resultado final.

**Por qué el aviso no aparece siempre.** Aflojar el criterio cambia lo que
significa el resultado, así que se declara. Pero sólo cuando lo ampliado llegó a
la respuesta: en un corpus grande casi ninguna pregunta entera tiene todas sus
palabras en un mismo fragmento, y un aviso que aparece siempre no distingue
nada.

**Lo que no cambió.** Las cuatro consultas que devuelven fragmentos del corte
para temas que el corte no publica siguen ahí: vienen de la mitad semántica, que
siempre entrega sus vecinos más cercanos. Es un problema distinto, ya listado en
`docs/reportes/recuperacion.md`, y esta corrección no lo toca ni lo empeora.

## D-110 · Límites de uso: dos baldes, y ninguno guarda una dirección

P-017 criterio 3. Hasta ahora no había ninguno: una sola dirección podía ocupar
toda la capacidad, y probar mil credenciales costaba lo mismo que probar una.

Dos límites por origen, ambos de balde de fichas —y no contador por ventana
fija, que deja gastar el cupo entero al final de una ventana y el cupo entero al
principio de la siguiente—: consultas por minuto (120) y autenticaciones
administrativas fallidas (10 cada cinco minutos). Al alcanzarlos, **429** con
cuerpo tipado `RATE_LIMITED` y `Retry-After`.

**La clave del balde no es una dirección**, es un hash con sal aleatoria del
proceso. Sirve para contar, no para saber de quién, y la sal muere con el
proceso. `X-Forwarded-For` no se cree por omisión: la pone quien llama, y
creerle convierte el límite en un adorno porque cualquiera cambia de identidad
escribiendo otro número. Se usa sólo si el despliegue declara cuántos proxies
propios hay delante, y se lee el salto que corresponde a ese número.

**Los límites van adentro de la observabilidad, no afuera.** El middleware se
registra antes para quedar envuelto por el de medición, así que un 429 se mide
como cualquier otra respuesta. Un límite que frena sin dejar rastro no se puede
ajustar: no hay forma de saber si está frenando abuso o gente.

**Lo que no hace y hay que decir al desplegar:** el balde no se comparte entre
procesos, así que con cuatro instancias el límite efectivo es cuatro veces el
configurado. Un límite compartido necesita un almacén común que este despliegue
todavía no tiene.

**Un fallo que la prueba encontró.** El barrido de baldes ociosos miraba también
las fichas (`fichas >= cupo`), lo que parece más prolijo y está mal: las fichas
se reponen recién cuando el balde se usa, así que un balde ocioso figura con las
de la última vez y no se barre nunca. Con seiscientos orígenes no se barrió
ninguno —una fuga de memoria en el componente que defiende del abuso—. Alcanza
con la inactividad: pasada una ventana entera la reposición llega al cupo por
aritmética.

**Y uno de configuración.** Una variable mal escrita —`BN_LIMITE_CONSULTAS_POR_MINUTO=sesenta`—
no puede dejar el servicio sin límite en silencio. Se vuelve al valor por
omisión; el modo sin límite se pide a propósito poniendo 0, que es lo que
necesita una medición de caudal.

## D-111 · La traza de consultas caduca aunque no identifique a nadie

P-017 criterio 2. `consultas_auditadas` guarda la **forma** de la consulta —ruta,
corte, resultado, causa tipada, latencia— y nunca su contenido. Aun así se borra
a los 90 días (`bn operacion purgar-consultas`).

Dos razones. Un registro que no caduca crece para siempre y termina respaldado,
replicado y consultado por gente que no sabe qué está mirando. Y «no identifica
a nadie» es una afirmación sobre hoy: un conjunto grande de formas de consulta,
con sus horarios y sus jurisdicciones, se vuelve más identificante cuanto más
largo es.

El purgado corre con el rol de administración. El lector de la API inserta su
traza y no puede borrar la de nadie, y eso está probado con `SET ROLE`: esa
separación es lo que hace que el registro sirva como registro.

La prueba de privacidad se endureció de paso. Verificaba que no existiera una
columna llamada `consulta_texto`; ahora fija el **conjunto entero** de columnas
de la tabla. Prohibir los nombres que se nos ocurran hoy no protege de la
columna que se agregue mañana con otro nombre.

Todo quedó escrito en `docs/operacion/politica_de_datos.md`, con el archivo y la
prueba al lado de cada afirmación. Una política de retención que vive sólo en un
documento es una política que nadie aplica.

## D-112 · La carga y los fallos, inducidos de verdad

P-023 criterio 3. `bn calidad carga` levanta un servidor en su propio proceso,
un proveedor de modelo de mentira y una fuente de mentira, y los rompe en
ventanas programadas. Simular un fallo con una bandera prueba la bandera.

Treinta minutos, veinte conversaciones concurrentes, 56.547 peticiones. Con el
proveedor caído: **cero errores**, 589 respuestas en extracto contra 3 generadas
dentro de la ventana —el repliegue funciona y se declara—. Con la fuente caída:
cero errores en el camino de consulta, porque no lo toca; la ingesta registró el
503 como transitorio con tres intentos y el 403 como acceso limitado, sin rotar
identidad. Con la base apagada: 3.525 respuestas **503 con cuerpo tipado**, y
volvió en 0,2 s sin reiniciar el proceso. Al origen abusivo se le rechazaron
14.031 peticiones; a las conversaciones legítimas, **cero**. Ninguna filtración
en 56.547 cuerpos revisados.

Tres cosas del sistema que sólo aparecieron acá:

**El modelo se cargaba una vez por hilo.** `lru_cache` guarda el resultado
después de que la función termina, así que veinte consultas simultáneas
encuentran el hueco vacío y entran las veinte a cargar 220 MB. La primera
corrida dio trescientas peticiones en dos minutos, casi todas expiradas.

**La base caída devolvía 500.** Ahora 503 con `Retry-After`: un 500 hace que un
balanceador reintente contra la misma instancia.

**El informe decía «p50 0,0 ms» durante el apagón**, porque los percentiles
excluían los 5xx. Medido sobre todo lo que recibió respuesta, el p50 es de
milisegundos: el servicio rechaza rápido en vez de colgarse, y para quien
pregunta esa es la diferencia entre un «ahora no puedo» inmediato y treinta
segundos de espera.

Y dos del propio ensayo: el servidor de mentira era secuencial —lo medido era el
servidor de mentira— y el prompt viaja dentro de un JSON con las comillas
escapadas, así que el proveedor devolvía texto sin citas, los validadores lo
rechazaban con razón y el camino generado no se ejercitaba nunca.

## D-113 · El vecino más cercano no es la respuesta, y ahora se dice

Preguntando «asignación universal por hijo» —que este corte no contiene— el
sistema devolvía cinco párrafos de una ley de vivienda de CABA bajo el título
**«Lo que dicen las normas»**, sin una sola advertencia. Estaba anotado en el
informe de recuperación como cuatro sondas que «no debían devolver ninguno»; como
nota al pie parecía menor, y en el frente ciudadano es la pantalla entera.

**Tres intentos de filtrarlo, los tres medidos contra el conjunto congelado, los
tres descartados:**

| Filtro | Recall@5 | Sondas que fugan (de 4) |
| --- | ---: | ---: |
| sin filtro | 74,1 % | 4 |
| piso de distancia 0,90 | 74,1 % | 4 |
| piso de distancia 0,75 | 66,7 % | 4 |
| piso de distancia 0,60 | 59,3 % | 2 |
| corroboración léxica por consulta | — | 3, y silencia 7 de 27 preguntas legítimas |
| corroboración léxica por fragmento | 59,3 % | 1 |

Ni destruyendo el recall se cortan. **La causa no es el ranking**: con una sola
ley publicada, una pregunta sobre la asignación universal por hijo está
genuinamente cerca de un texto sobre ingresos familiares y Canasta Básica. El
modelo no se equivoca; se equivoca la premisa de que «el vecino más cercano» sea
«la respuesta». El resultado negativo quedó escrito en `busqueda.py` para que
nadie lo reintente a ciegas.

**El arreglo es declarar, no filtrar.** Cuando ningún fragmento servido comparte
una palabra con la consulta, la respuesta lleva `solo_parecidos` y el frente
cambia el encabezado a «Textos parecidos a tu pregunta» y antepone un aviso:
«Esto puede no tener que ver con tu pregunta». No cuesta un punto de recall, y
convierte una respuesta equivocada silenciosa en una incertidumbre visible.

**Y toda respuesta dice ahora qué hay publicado.** Si alguien pregunta por la AUH
y lo único publicado es una ley de vivienda de CABA, decirle qué cubre el corte
es más útil que devolverle los párrafos más parecidos y callarse. El dato estaba
en la base desde siempre; lo que faltaba era decirlo.

## D-114 · Lo construido para P-015 no es todavía una conversación

Conviene que quede escrito, porque la historia se llama «Completar el front
conversacional» y lo que hay es **un formulario que devuelve una respuesta**.
Cada consulta es independiente: no hay historial, no hay turnos, no se puede
repreguntar. Si alguien pregunta «¿cumplo?» y le falta un dato, el sistema no se
lo pide: contesta con lo que tiene.

El plan pide, con esas palabras, «historial de ocho turnos, contexto acotado» y
«mensajes, carga, cancelación, reintento y **nueva conversación**». Están las
tres últimas; «nueva conversación» supone una en curso, y no la hay. Faltan
también las preguntas sugeridas del inicio y el escenario «¿cumplo?» con datos
faltantes y excepciones.

Sí cumple el resto del recorrido: consulta anónima sin formulario de identidad,
aclaraciones de jurisdicción, fecha, beneficio y hechos con controles adecuados a
su tipo, cancelar, reintentar y empezar de nuevo, citas abribles con norma,
artículo y fecha, y ningún nombre de tabla ni detalle del modelo a la vista. La
latencia también: el plan pide p95 ≤ 2 s para respuestas estructuradas y el
ensayo de carga midió 880 ms.

**Por qué la parte conversacional no es un agregado menor.** Un historial de
turnos es donde este tipo de sistemas empieza a mentir: arrastra un supuesto de
un turno anterior —una jurisdicción, una edad, un beneficio que la persona nunca
confirmó— y lo usa como si fuera un hecho establecido. El plan ya lo acota
—ocho turnos, contexto acotado, retención de conversaciones desactivada por
omisión—, y cuando se construya, cada hecho arrastrado tiene que seguir siendo
visible y editable por quien pregunta, igual que hoy lo es el campo de hechos.

## D-115 · El frente es un chat, no un formulario

Corrección de rumbo, y era de fondo. Lo que había construido para P-015 era un
formulario: selects de jurisdicción, campo de fecha, textarea de «tu situación».
Eso es exactamente la forma de la que la gente que va a usar esto está tratando
de escapar. Un producto conversacional de acceso a derechos tiene que dejar que
alguien escriba **lo que le está pasando**, en sus palabras, y seguir desde ahí.

Ahora es un hilo: mensajes, cuadro de escritura abajo, Enter envía. El saludo
dice qué es, qué no resuelve y qué hay publicado hoy, y ofrece tres preguntas
sugeridas **sacadas de lo que el corte realmente cubre** —ofrecer ejemplos que el
sistema no puede contestar es prometer algo que no tiene—.

**Las aclaraciones pasan dentro del diálogo.** Después de cada respuesta hay dos
sugerencias: «Acotar a dónde vivo» y «Ver a otra fecha». Lo que el sistema
termina teniendo en cuenta vive en una franja visible, como fichas que se pueden
quitar de a una. Esto no es decoración: **un chat que arrastra supuestos sin
mostrarlos es donde estos sistemas empiezan a mentir**, y acá no hay nada
inferido que la persona no pueda ver y borrar.

**Un chat hace que la gente cuente más que un formulario.** Un campo sin casilla
de DNI no invita a escribirlo; un cuadro abierto sí. El saludo lo dice de
entrada —no hace falta nombre, documento, dirección exacta ni datos de otras
personas—, el backend nunca guarda el texto y «Salir y borrar» limpia el hilo
entero. Ya estaba probado; ahora además está dicho donde se lee.

**Cada respuesta era un muro de dos mil palabras.** Cinco artículos completos, que
en un formulario se toleran y en un hilo entierran a quien pregunta. Se muestra
el mejor puntuado y el resto queda en un `<details>` —«Ver 4 textos más de la
norma»—: la evidencia no se recorta, se ordena. Se usa `<details>` y no un
acordeón propio porque ya es accesible con teclado y con lector de pantalla sin
construir nada.

**Un hallazgo de la prueba de teclado.** El saludo hacía `scrollIntoView`, y eso
mueve el punto desde el que el navegador empieza a tabular: el primer Tab dejaba
de llegar al salto de contenido y caía en la primera sugerencia. El saludo ya no
se desplaza, porque no hay nada arriba de él.

## D-116 · Los avisos ahora dicen para quién son

Humanizando el frente apareció esto, textual en la pantalla:

> «Esta búsqueda fue solo léxica: el corte no tiene índice semántico construido
> para el modelo pedido. **Se construye con `bn recuperacion indexar`**.»

Un comando de terminal, en la pantalla de alguien que pregunta si lo pueden
desalojar. El plan lo prohíbe con todas las letras —«sin nombres de tablas o
detalles del modelo dentro del recorrido ciudadano»— y además no sirve: quien
lee eso no puede hacer nada con eso.

El arreglo no es reescribir la frase. Es que **cada aviso declare su público**.
`Aviso(texto, para_la_persona)`; la respuesta viaja con `avisos` —lo que la
persona puede leer y usar— y `notas_operativas` —lo que necesita quien opera—.
Nada se esconde: cambia por dónde sale.

El mismo hecho se cuenta dos veces cuando corresponde. Sin índice semántico, a
quien opera se le dice el comando; a la persona, «estoy buscando sólo por las
palabras exactas, probá decirlo con otras palabras», que es algo que sí puede
hacer. Lo mismo con la caída del proveedor: el nombre de la excepción va a la
nota operativa, y la persona ve el modo de la respuesta en castellano.

## D-117 · Humanización del lenguaje del frente

Todo lo que lee una persona, reescrito. Lo que se sacó:

* **Los nombres de los enum.** El sello decía `EXTRACTO` y `ABSTENCION`. Ahora
  dice «texto de la ley» y «sin respuesta». El plan pide que la salida se
  identifique —explicación, extracto o abstención— y eso sigue estando: la
  distinción está dicha en castellano, que es distinto de estar borrada.
* **El uuid del corte.** «Corte publicado: 2a5d835f-c750-…» no le dice nada a
  nadie. Queda en un atributo del documento, por si alguien de soporte necesita
  reproducir la respuesta.
* **`schema 1.0`** al pie, y los estados internos (`PUBLICADO`,
  `SIN_RESULTADOS`). De la ficha quedó lo único que le sirve a una persona: para
  cuándo vale lo que acaba de leer.
* **El título oficial de la norma**, doscientos caracteres en mayúsculas, se
  recorta a dos renglones por CSS. No se reescribe —es el título de un acto
  publicado— y el texto completo sigue en el documento, copiable y legible por
  un lector de pantalla.

Y la voz. «No hay evidencia publicada para contestar esto» pasó a «No tengo
ninguna norma publicada que hable de esto. Ojo con la diferencia: no te estoy
diciendo que no te corresponda. Te estoy diciendo que yo no tengo con qué
contestarte». La distinción que el sistema entero existe para sostener, dicha
como se la diría una persona.

Hay una prueba que recorre cuatro conversaciones y falla si aparece cualquiera
de diecisiete palabras de la cocina —«corte publicado», «chunk», «embedding»,
«abstención», «bn recuperacion»…—. Un criterio de estilo que nadie verifica se
pierde en el tercer cambio.

## D-118 · Las preguntas sugeridas se miden antes de ofrecerlas

Sacando la demostración se vio algo incómodo: las tres preguntas que la pantalla
sugería —«¿Quién puede pedirlo?», «¿Qué papeles piden?», «¿De cuánto es?»—
volvían las tres con la advertencia de «esto puede no tener nada que ver con lo
tuyo». O sea: el sistema proponía una pregunta y después se desdecía de su
propia respuesta.

La causa es la misma de siempre. Son preguntas cortas cuyas palabras —«pedirlo»,
«papeles», «cuánto»— no están en el texto legal, así que la mitad léxica no
encuentra nada y lo que queda son vecinos semánticos sueltos.

Se reemplazaron por tres que **se midieron**: «Me quedé sin casa después de un
incendio», «Estoy durmiendo en la calle», «¿Tengo que rendir cuentas de lo que
gasté?». Las tres vuelven corroboradas. Y de paso suenan a alguien contando lo
que le pasa, que es como se va a usar esto.

La regla no es la lista —hoy lo publicado es una sola ley y con más normas esto
tiene que salir del corpus—: la regla es que una sugerencia se prueba antes de
ofrecerse. Una que el sistema no puede contestar bien es peor que no sugerir
nada.

## D-119 · Tipografía del sistema, a propósito

El CSS nombraba «Source Sans 3» e «IBM Plex Mono», y ninguna de las dos se
cargaba en ningún lado: nombrar una familia que nunca llega significa que cada
navegador elige otra cosa y la pantalla se ve distinta en cada máquina.

Se podría haber agregado el enlace a un servicio de tipografías. No se hizo, y
conviene que quede escrito por qué: **cargar una tipografía de un servicio
externo le cuenta a ese servicio quién entró a preguntar por sus derechos**, y
además ata la pantalla a que ese servicio esté vivo y a que la conexión alcance.
Para esta gente, ninguna de las dos cosas es aceptable a cambio de una letra más
linda. Queda la pila del sistema, declarada entera.

## D-120 · La forma de un chat, y el streaming que no se finge

El frente pasó a tener la forma de un chat de los que la gente ya usa: portada
con el cuadro de escritura al centro y la pregunta invitada, hilo cuando la
conversación empieza, indicador de que está buscando, botón para parar,
respuestas sobre la página en vez de adentro de una tarjeta.

Tres decisiones que importan más que el aspecto:

**La portada no es un mensaje del hilo.** Un chat que arranca con un mensaje del
sistema ya parece usado antes de que nadie lo use. La bienvenida va sobre la
página y se retira en cuanto hay conversación.

**El botón de enviar no se apaga: aparece el de parar.** Un control deshabilitado
mientras el sistema piensa deja a quien escribió sin ninguna salida.

**No se finge que la respuesta se escribe.** Un chat de modelo transmite mientras
redacta, y eso acá sería teatro: sin proveedor configurado la respuesta es texto
ya publicado, el tiempo se va en la búsqueda y el p50 medido es de 190 ms. Hacer
aparecer las letras de a poco demoraría información que el sistema ya tiene para
simular un trabajo que no está haciendo.

El streaming de verdad va cuando haya proveedor: ahí los tokens tardan segundos
y transmitirlos es información, no adorno. Queda anotado como lo próximo de
P-013, junto con la clave.

## D-121 · Marcado que viaja dentro del texto, no alrededor

Análisis del flujo conversacional, hallazgo 3. Tres de cada trece respuestas
mostraban etiquetas `<p>` **literales** dentro del texto de la ley, en la
pantalla de quien pregunta.

**Causa raíz, y no era la obvia.** El adaptador HTML usa `nodo.text()` de
selectolax, que quita etiquetas correctamente. El problema es que la fuente
publica su **HTML escapado dentro de la propia página**: la captura de D10 tiene
catorce `&lt;p&gt;` contra diez `<p>` reales. El extractor hace lo correcto
—decodifica la entidad, porque eso es texto visible— y el resultado es que el
marcado queda como contenido. No es un extractor que no limpia: limpia la capa
que le toca, y faltaba mirar la segunda.

Medido antes de tocar nada: **47 unidades de 2.317**, en **diez fuentes
distintas**. Que sean diez descarta que sea un adaptador en particular, y por eso
el arreglo va en la extracción, por donde pasan todos.

Las etiquetas que aparecen son `p`, `br`, `details` y `style`. La última importa:
puede meter una hoja de estilo entera adentro de un artículo, así que se saca con
su contenido y no sólo la etiqueta.

**Lo que el arreglo no hace:** pasarle un parser de HTML a todo el texto legal.
Una norma puede decir «el monto debe ser < 3 salarios», y eso no es marcado. El
reconocimiento exige un nombre de etiqueta conocido, y hay pruebas con «a < b»
que verifican que no se toca.

**Y se declara.** Cuando limpia, la corrida lo dice: «la fuente publica su HTML
escapado dentro de la propia página». Una limpieza silenciosa escondería que el
origen es así, que es justamente lo que hay que poder ver si mañana cambia la
maquetación.

La red de seguridad es **DQ10**: ninguna unidad con marcado se publica. El
extractor pasó a `extraccion@15`, así que las versiones ya extraídas quedan
marcadas para reprocesar.

## D-122 · La promesa que el sistema no podía cumplir

Hallazgo 2. La abstención decía, textual: «No te quedes con esto: en el organismo
te pueden contestar. **Abajo te digo a dónde ir**». Y abajo la pantalla decía:
«No tengo cargado ningún lugar de atención para esa zona».

Con **cero** puntos de atención publicados, eso le pasaba a *toda* conversación
que no encontraba respuesta: prometía y se desdecía en el mismo mensaje. En un
servicio público una promesa incumplida gasta la confianza que hace falta para
que la persona vuelva.

Dos cambios, y el segundo importa más. La copia dejó de prometer: el frente
agrega el dato concreto sólo cuando lo tiene. Y el hueco pasó a ser **un número
en el tablero** —`puntos_de_atencion_publicados`, hoy en cero— en vez de una
disculpa en la pantalla. El final más frecuente de una consulta era el que menos
se miraba.

## D-123 · El canal va primero: reconocer la urgencia sin inventar a quién llamar

Hallazgo 1 del análisis del flujo, y el más grave. Alguien escribió «estoy
durmiendo en la calle, ¿hay algo urgente?» y el sistema contestó con el artículo
10 de una ley. En un servicio público eso no es una respuesta pobre: hay una
clase de mensaje donde **el canal va primero y la norma después**, y no existía.

`conversacion/urgencia.py` reconoce cinco clases —violencia, salud, niñez, calle,
alimentos— y la respuesta las lleva arriba de todo, antes del título y antes del
texto legal. Tres cosas que **no** hace, y son la parte importante:

**No diagnostica.** Dice «si necesitás un lugar esta noche, esto no reemplaza
pedir ayuda», no «estás en una emergencia». Quien sabe si es una emergencia es
la persona, no un puñado de expresiones regulares.

**No inventa a quién llamar.** Escribir «llamá al X» en la pantalla de alguien en
emergencia es una afirmación operativa: si el número está mal, desactualizado o
no corresponde a esa jurisdicción, el daño es inmediato. Los canales salen del
corpus curado. Hoy hay **cero** cargados, así que el sistema dice «no tengo
cargado a quién derivarte, y eso es una falla de este sistema, no tuya». Es feo
y es verdadero, y una prueba verifica que no aparezca ningún número que nadie
curó.

**No se activa por una palabra suelta.** El requisito va por expresión y no por
clase, porque dentro de una misma clase conviven las dos cosas: «me pega» es un
relato por construcción, «violencia de género» es el nombre de media docena de
leyes. El conjunto congelado encontró exactamente ese fallo —«¿qué dice la ley
sobre violencia de género?» disparaba la alarma— y también que «en la calle con
mi bebé» caía en la clase menos urgente porque el patrón sólo miraba un orden de
las palabras.

Veintidós casos congelados en `docs/calidad/urgencia.json`, positivos y
negativos. Los negativos importan tanto como los positivos: un aviso de
emergencia que aparece siempre deja de leerse, y deja de leerse justo cuando
hace falta.

**Y lo que la persona escribió no vuelve.** La expresión que disparó queda para
quien depura; la respuesta lleva sólo la clase.

## D-124 · El corte publicado sigue con el marcado, y no se toca

DQ10 y `extraccion@15` arreglan el problema **hacia adelante**. El corte que hoy
se sirve tiene **47 unidades y 4 fragmentos** con marcado, y ahí siguen.

Se podría correr un `UPDATE` que los limpie. No se hace: cambiaría el texto que
un corte publicado sirve, sin pasar por una publicación nueva, y entonces
`release_id` dejaría de identificar lo que se sirvió. Reproducir una respuesta
pasada es la garantía sobre la que se apoya todo lo demás.

Limpiarlo de verdad es volver a extraer y volver a curar las citas que apuntan a
esas unidades — trabajo jurídico, no un `UPDATE`. Mientras tanto DQ10 impide
publicar un corte nuevo que lo arrastre, así que el problema no puede crecer.

## D-125 · La persona puede contestar, y sólo con tres botones

Todo lo que el sistema medía lo medía de sí mismo: latencia, abstenciones por
causa, cuántas evidencias usó, frescura del corte. Nada decía si a quien
preguntó le sirvió. Una respuesta puede salir en 40 ms, con seis citas y contra
el corte correcto, y dejar a la persona igual de perdida que como llegó; con la
traza sola, eso se cuenta como éxito.

Al pie de cada respuesta hay tres botones: **Sí**, **No** y **Quiero hablar con
una persona**. La señal viaja a `POST /v1/devoluciones` con el `request_id` que
la respuesta devolvió en la cabecera `X-Request-Id`, y nada más.

**No hay caja de comentarios, y ésa es la decisión.** Es lo que primero se
pediría —«dejá que expliquen qué les faltó»— y es el lugar exacto donde alguien
escribe su caso completo: el nombre de su hija, la dirección de la que lo echan,
el número de expediente. Todo el resto del sistema está construido para no
guardar eso, empezando por `intencion`, que recibe la ruta y no la pregunta. Un
`<textarea>` lo tira abajo en un renglón, y lo haría con la mejor de las
intenciones.

Se hace cumplir en tres lugares porque uno solo se olvida: el modelo de la ruta
rechaza cualquier campo de más, el `CHECK` de la base sólo acepta las tres
señales, y una prueba compara las columnas de la tabla contra la lista escrita.
Hay además una que verifica que la pantalla tenga un único lugar donde escribir.

**Se une a la traza por `request_id`, y eso es lo que la vuelve accionable.** Sin
el cruce, «doce personas dijeron que no les sirvió» no dice qué hacer. Con el
cruce, la primera corrida contra el recorrido real ya lo mostró: las dos señales
negativas cayeron sobre abstenciones con motivo `SIN_EVIDENCIA` y las dos
positivas sobre respuestas resueltas. Eso dice que el problema está en lo que el
corpus no cubre, y no en cómo están redactadas las respuestas. Son dos trabajos
distintos y hasta ahora no había forma de saber cuál hacía falta.

**El denominador viaja siempre.** «El 80 % dijo que le sirvió» sobre cinco
respuestas no es un dato, y cuatro de cinco y cuatro de mil son hallazgos
distintos: el segundo dice que el mecanismo no se está usando.

**Una señal por respuesta.** `ON CONFLICT DO NOTHING` sobre el UNIQUE de
`(request_id, senal)`: una tasa de satisfacción que se puede inflar apretando
repetido no mide satisfacción. Va sin nombrar las columnas del conflicto porque
la forma con destino explícito exige `SELECT` sobre la tabla para inferir el
índice árbitro, y el rol de la API sólo tiene `INSERT`; darle lectura sobre las
devoluciones de todo el mundo para ahorrar un paréntesis sería pagar un permiso
de más por una comodidad de escritura.

**La devolución no entra en la traza.** Contarla inflaría el denominador —«400
consultas» pasaría a incluir los clics en «me sirvió»— y la tasa de respuesta se
mediría contra sí misma.

**Pedir una persona no abre un canal de vuelta, y la pantalla lo dice.** «No
puedo comunicarte con alguien desde acá: no te pido tus datos, así que no tengo
a dónde escribirte ni a quién avisarle que estás esperando.» Es la misma
decisión que hace que no se guarde nada, vista desde el otro lado. Lo que sí
pasa es que queda contado, y ése es el argumento con números para discutir si
hace falta atención humana. Prometer un contacto que no existe es del mismo tipo
de daño que inventar un teléfono de emergencia (D-123), sólo que más lento.

Se lee con `bn operacion devoluciones`. Una devolución que nadie mira no cierra
ningún ciclo: sería el mismo defecto que tenía `consultas_auditadas` cuando
existía la tabla, existía el permiso y nadie escribía nunca en ella.

## D-126 · Un comando que existía según cómo se lo llamara

`if __name__ == "__main__": app()` estaba a mitad del archivo del CLI. Corriendo
`python -m backend_normativo.cli.main`, la aplicación arrancaba antes de que se
registraran los comandos definidos más abajo —entre ellos `operacion
purgar-consultas`, que es el que aplica la retención— y contestaban «No such
command». Por el entrypoint `bn` funcionaban, porque ahí el módulo se importa
entero primero.

Otra falla que no falla: nada se rompe, el comando simplemente no está, y la
respuesta que se recibe es la misma que si nunca se hubiera escrito. Se movió el
bloque al final y quedó una prueba que compara, para cada grupo, los comandos
registrados en el módulo contra los que aparecen al correrlo con `python -m`.

## D-127 · Un corte es una foto completa, no el delta de la corrida

`release_vigente` devuelve el corte publicado más reciente y la búsqueda filtra
los fragmentos por ese corte. La publicación, en cambio, sólo construía
fragmentos para las versiones **candidatas de esa corrida**.

Las dos cosas juntas hacen esto: publicar un segundo corte —por ejemplo, uno que
incorporara los 1.842 puntos de atención ya aprobados— dejaba a la API sirviendo
un corte sin una sola unidad normativa. El frente contestaba «no tengo nada
publicado» sobre un corpus que seguía entero.

Y no fallaba nada. `bn publicacion publicar` terminaba bien, con los ocho gates
en verde y un recuento de versiones publicadas en pantalla. La única señal
habría sido que la gente dejaba de recibir respuestas.

Ahora el corte hereda lo que el anterior servía y sigue vigente. Dos detalles
que no son detalles:

* **Lo que la corrida reemplaza no viaja.** Si entre los candidatos viene una
  versión nueva de la misma entidad, la vieja se queda afuera. Heredar todo
  serviría el texto viejo y el nuevo de la misma norma dentro del mismo corte, y
  una respuesta podría citar los dos como si dijeran lo mismo.
* **El índice semántico viaja con los fragmentos heredados.** El vector es una
  función del texto y del modelo: si el fragmento viaja con el mismo hash, su
  vector sigue siendo el suyo. Recalcularlos exigiría cargar el modelo dentro de
  la transacción de publicación; no copiarlos dejaría el corte nuevo con
  búsqueda sólo léxica, que tampoco falla —devuelve lo que encuentra la mitad
  que quedó— y se nota semanas después, midiendo la recuperación.

La prueba que lo fija reproduce el caso real: publicar un punto de atención
después de un corte con normas. Antes decía «el corte nuevo sirve 0 fragmentos y
el anterior servía 2».

## D-128 · El estado de publicación decía que sí y la base decía que no

Desde la primera migración, `registro_versiones` exige que nada llegue a
`PUBLISHED` sin `release_id` **y sin `verificado_en`**. Es una invariante buena:
una dirección o un teléfono que nadie confirmó contra su fuente no debería
llegar a la pantalla de alguien que los va a usar hoy.

El publicador no la conocía. `bn publicacion estado` contaba **14.390
candidatos** con los ocho gates en verde, y publicar habría reventado con una
violación de CHECK a mitad de la transacción. Lo grave no es el error: es que el
informe afirmaba que se podía publicar un corpus que la base no iba a aceptar, y
nadie podía saberlo leyendo el estado.

Se respeta la invariante en vez de relajarla: `candidatos()` exige fecha de
verificación y la cuarentena lo dice con esas palabras. El estado real del
corpus pasó a ser el que es:

```
Candidatos a publicar: 0
En cuarentena: 14543
    6467  barrio_renabap: sin fecha de verificación
    6134  canal: sin fecha de verificación
    1842  punto_atencion: sin fecha de verificación
      62  canal: estado de revisión CANDIDATE
      ...
```

El resumen por motivo se agregó junto con esto: con catorce mil versiones
retenidas, quince identificadores sueltos no dicen qué hay que hacer y una línea
por motivo sí.

**Lo que esto deja a la vista.** Todo el corpus operativo —los puntos de
atención, sus canales, los barrios, los montos— está aprobado y ninguno tiene
fecha de verificación, porque nada en la curación se la pone: sólo la ponen
`Revisor.resolver` y `ResolutorVigencia`, que trabajan sobre normas. Es la razón
por la que el frente dice «no tengo cargado a quién derivarte» teniendo 1.842
lugares en la base.

Qué cuenta como verificar un directorio importado —si alcanza la fecha de la
captura oficial, que es cuándo se vio lo que la fuente publicaba, o hace falta
que alguien lo confirme uno por uno— es una decisión de ACIJ y no se toma acá.
Es lo que decide si esos 1.842 lugares llegan a la pantalla de alguien que
esta noche no tiene dónde dormir.

## D-129 · Una oficina con horario no es un canal de emergencia

El bloque de urgencia ofrecía, bajo «Podés ir o llamar acá», los puntos de
atención que devolviera el corpus. Mientras hubo cero publicados no se notó.
Alcanzó con publicar tres en un ensayo sobre una copia de la base real para que
apareciera esto, arriba de todo, a alguien que escribió «estoy durmiendo en la
calle con mi bebé»:

> Si hay chicos o chicas en riesgo ahora, esto no reemplaza pedir ayuda.
> Podés ir o llamar acá: **Sede Comunal 3** · Sarandi 1273

Una sede comunal abre a las nueve. Mandar ahí a alguien cuyo hijo está en riesgo
esta noche es peor que decirle que no tengo a quién derivarlo, porque **parece
una respuesta**: la persona deja de buscar. Es el mismo daño que inventar un
teléfono (D-123), sólo que con un dato verdadero puesto donde no corresponde.

Un canal de emergencia es otra cosa —24 horas, con guardia— y el corpus todavía
no distingue una cosa de la otra: `puntos_atencion.tipo` tiene SEDE,
DELEGACION, OFICINA_MOVIL, CENTRO_COMUNITARIO, JUZGADO y OTRO, y ninguno de esos
dice si atiende una urgencia. Mientras no haya un campo que lo diga, el bloque
de urgencia no ofrece ninguno: reconoce lo que pasa, dice que no tiene canal de
emergencia cargado —y que eso es una falla del sistema, no de la persona— y, si
hay lugares publicados, aclara que son oficinas con horario, que están más
abajo y que sirven para el trámite y no para esta noche.

El recorrido de aceptación pasó a publicar un punto de atención de verdad. Sin
eso, «A dónde ir» sólo se probaba vacío: treinta y pico de casos corrían contra
un corpus sin un solo lugar, que es exactamente la mitad que el frente muestra
mal si se descuida.

## D-130 · Se procede sin firma jurídica, y queda escrito quién decidió

**Decisión de Pedro Pistoni, 12 de septiembre de 2026.** El proyecto no va a
contar con un responsable jurídico designado que firme el alcance. Se procede
sin esa firma. Consultado sobre el alcance, eligió habilitar de una vez las 99
reglas con condición ejecutable, sobre los 16 beneficios.

Antes de hacerlo dejé planteada la alternativa y su razón: habilitar por
beneficio acota el daño de una regla mal formalizada y permite mirar casos
reales antes de seguir. La decisión fue la otra y se ejecutó completa. Esto
queda acá porque dentro de seis meses la pregunta va a ser quién decidió que
este servicio empezara a evaluar condiciones, y la respuesta tiene que estar
escrita antes de que haga falta.

**Qué se hizo exactamente.** Las 166 reglas del expediente ya figuraban
APPROVED con «Pedro Pistoni» como actor, registrado como transcripción de su
revisión declarada. Lo que faltaba no era aprobarlas: era conectarlas. Cada una
quedó con un evento `HABILITAR_REGLA` propio, con ese actor y con este
fundamento textual:

> Decisión de producto del 12/09/2026: el proyecto no va a contar con firma
> jurídica designada y se procede sin ella. Se habilitan las 99 reglas con
> condición ejecutable del expediente de 166 que ya figuraban aprobadas con este
> mismo actor. No hubo revisión de un profesional del derecho designado; la
> responsabilidad de la decisión es de producto.

Noventa y nueve eventos, uno por regla. Lo que se hace de una vez tiene que
poder auditarse una por una, y el registro dice lo que pasó y no otra cosa: no
dice que alguien revisó, dice que se decidió proceder sin revisión.

**Las 67 sin condición ejecutable quedan afuera.** No tienen árbol validado, así
que no hay nada que ejecutar; el motor las va a seguir contestando DESCONOCIDO
con su motivo, y la base lo exige además por restricción. Clasificarlas entre
formalizables, informativas y sin evidencia sigue siendo trabajo pendiente
(P-010, criterio 2).

**El defecto que esto destapó.** `aprobar()` decía en su docstring ser «la única
transición que habilita a la evaluación», y no lo era: el motor decide con
`ast is not None and not requiere_revision`, y ninguna transición bajaba esa
marca. Se podían aprobar las 166 reglas y el evaluador seguía contestando
DESCONOCIDO en todas, con el motivo «la regla está marcada como pendiente de
revisión». Aprobada y pendiente de revisión al mismo tiempo.

Ninguna prueba lo veía porque cada mitad estaba bien por su cuenta: la
transición dejaba su rastro y el motor respetaba la marca. Faltaba que una cosa
moviera la otra. El plan v1.1 lo nombra en §02 como «hacer coherente aprobar con
la marca de revisión». Ahora aprobar una regla con árbol validado la vuelve
ejecutable en la misma transición, y `bn revision habilitar-evaluacion` existe
sólo para el expediente que se aprobó antes del arreglo.

**Lo que esto todavía no cambia para nadie.** La evaluación lee reglas cuyo
beneficio esté PUBLISHED, y no hay ninguno: los 16 beneficios están CANDIDATE y
`bn revision aprobar-versiones` retiene 153 versiones «sin intervalo de
aplicación: servirlas sería afirmar una vigencia que nadie determinó». Hay 88
incidencias de VIGENCIA_INDETERMINADA abiertas y una resuelta.

Eso no es una firma jurídica: es una determinación de hecho —desde cuándo rige
cada norma— que tiene respuesta en los documentos capturados. Es el próximo
cuello de botella y es trabajo de curación, no de firma.

**Riesgo que queda asumido y por quién.** Una regla mal formalizada —una
negación invertida, un umbral mal leído, una excepción que no se recuperó— hace
que el servicio le diga a alguien que una condición no se cumple cuando sí se
cumple, y esa persona se va sin pedir algo que le corresponde. Las 99 reglas no
las revisó un profesional del derecho. Sigue vigente la prohibición de afirmar
elegibilidad definitiva: el motor devuelve cumple / no cumple / desconocido por
condición, con su cita, y la pantalla dice que quien decide es el organismo.
Esa distinción es ahora lo único que separa una orientación de un dictamen.

## D-131 · La vigencia se determinó leyendo, no firmando

Con D-130 el cuello de botella dejó de ser una firma y pasó a ser trabajo de
lectura: 88 incidencias de vigencia abiertas, y sin vigencia resuelta no se
publica nada. Se resolvieron **diez**, las que sostienen el alcance con datos
suficientes en el corpus. El dictamen completo, norma por norma, está en
`docs/revision/dictamen_vigencia.md`; acá va lo que cambia el diseño.

**La regla es supletoria y hay que decir cuál.** Art. 5 del Código Civil y
Comercial, y art. 2 del Código Civil t.o. Ley 16.504 para las anteriores a 2015:
la norma rige a los ocho días corridos de su publicación si no designa otro
tiempo. Se buscó en el texto capturado de cada una una cláusula propia de
entrada en vigencia y no hay ninguna, así que en todas rige el plazo supletorio.

**Tres casos no eran mecánicos, y son los que importan.**

*La Ley 547/2001 está etiquetada «no vigente» en la fuente y sí rige.* Es una
norma modificatoria consumida por incorporación: sus artículos 1 y 2 son el
texto actual de los artículos 10 y 16 de la Ordenanza 43478, que fijan los topes
de ingreso de la beca de comedor, el incremento del 15 % por cada niño y la
deducción por enfermedad crónica. Tratar la etiqueta como cierre de vigencia
habría ocultado los criterios vigentes del beneficio. La política ya advertía
este caso y por eso se negaba a resolverlo sola.

*El Decreto 690/2006 no está derogado y tampoco puede declararse abierto.* La
Ley 6935/2025 dice que el programa nuevo «se regirá exclusivamente por las
disposiciones de la presente Ley» y su cláusula transitoria mantiene el decreto
«hasta la publicación de reglamentación». Depende de un hecho externo que el
corpus no registra. Quedó **CONDICIONADO**, y eso lo deja fuera de cualquier
corte publicado: el servicio no va a servir como vigentes los requisitos del
decreto viejo. Es la primera vez que el vocabulario CONDICIONADO se usa para lo
que existe, y funcionó: el gate DQ08 lo retiene solo.

*La Ley 24.714 fue derogada y restituida.* El Decreto 1382/2001 la derogó entera
y el Decreto 1604/2001 restituyó su vigencia **desde la fecha de la derogación**,
con una excepción cuyo alcance no se pudo leer en la captura. De ella cuelgan 12
de los 16 beneficios. Se determinó ABIERTO_FIN con estado VIGENCIA_PARCIAL, y el
fundamento registra las dos cosas que no se pudieron verificar: el alcance de esa
excepción, y el de dos relaciones DEROGA —Ley 27260/2016 y Decreto 1039/2024—
cuyo texto de origen no está capturado. Si alguna fuera total, la determinación
cae y con ella los 12 beneficios. Está escrito para que se verifique primero.

**Un beneficio no tiene vigencia propia.** Existe porque una norma lo crea y
mientras esa norma rija; las que lo reglamentan o lo modifican cambian su
contenido, no su existencia. Eso es ahora una política —
`vigencia-derivada-del-beneficio@1`— y un resolutor. Antes no había ninguno: el
resolutor de vigencia sólo recorre versiones de norma, y para los beneficios no
había ni camino automático ni cola de revisión, así que iban a quedar en
DESCONOCIDO para siempre. No fallaba nada; simplemente no se podía publicar un
beneficio. Con las normas resueltas, los 16 quedaron con intervalo: 15 abiertos y
uno condicionado.

Es conservadora en los tres lugares donde derivar sería inventar: sin norma
creadora no deriva —que no conste qué crea un beneficio es un dato que falta, no
una vigencia abierta—; si la creadora no está resuelta, el beneficio tampoco; y
la fecha sale de la norma que lo crea y nunca de una que lo reglamenta, porque un
decreto reglamentario posterior no corre el nacimiento del derecho.

**Lo que quedó a la vista.** De las 127 versiones que siguen sin intervalo, casi
todas lo están por la misma razón: **124 de 142 documentos no tienen fecha
capturada**. No es una cuestión jurídica —la regla para determinarlas es la de
arriba— sino un dato que la ingesta no extrajo. El cuello de botella del corpus
volvió a ser código.
