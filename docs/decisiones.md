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
