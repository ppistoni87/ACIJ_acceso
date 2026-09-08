# Población real del corpus

Qué hay efectivamente cargado, con qué evidencia y qué falta. Los números salen
de la base; se regeneran con `bn calidad cobertura` y `bn calidad backlog`.

## Catálogo nacional (F01)

El manifiesto habilita expresamente importar el catálogo nacional como
metadatos. Se capturó el recurso de producción —el ZIP, no la muestra
histórica— y se importó entero.

| Medida | Valor |
| --- | --- |
| Filas del dataset | 428.380 |
| Normas creadas | 423.708 |
| Identificadores oficiales conservados | 423.711 |
| Organismos emisores derivados | 1.642 |
| Sin número (`S/N`) | 142 |
| Metadata-only (sin URL de texto) | 235.489 |
| Con texto actualizado | 8.860 |
| Identidad incierta por numeración por organismo | 322.331 |
| Identidad incierta por clave repetida | 6.561 |
| Normas conjuntas plegadas | 4.489 filas extra, con incidencia abierta |
| Normas sin identificador oficial | 0 |

Tres cosas que el catálogo real obligó a decidir, y que quedaron así:

**`S/N` no es un número.** 142 normas no tienen número. Se conservan con
`numero` en NULL —fuera de la clave canónica— y se identifican por su id
oficial. Escribir "SN" como número habría creado 142 normas con el mismo
número.

**Una clave canónica repetida no identifica.** La numeración de resoluciones y
disposiciones es por organismo: el catálogo trae 123 normas cuya clave es
("Resolución", "1", 2023), emitidas por 123 organismos distintos. Esas 322.331
normas se cargan con `identidad_incierta`, igual que las 6.561 que comparten
clave con una homónima del propio catálogo (hay cuatro decretos "1/2001").
Ninguna resuelve citas por número, que es exactamente lo que corresponde:
"Resolución 1/2023" no señala una norma.

**Los contadores no son aristas.** `modificada_por = 3` dice cuántas normas
intervienen, no cuáles. No se construyó ninguna relación con ellos.

Y una que el catálogo obligó a descubrir: **las normas conjuntas vienen
desnormalizadas**, una fila por organismo firmante con el mismo id oficial. Son
4.489. Se pliegan en una norma y los demás firmantes quedan como incidencia
abierta, porque el modelo admite un solo emisor y perderlos en silencio
inventaría una autoría única que la fuente no afirma.

**Metadata-only.** 235.489 normas —el 55% del catálogo— no traen URL de texto.
Se conservan igual: que una norma exista y no tengamos su texto es información,
y descartarlas haría creer que no existen.

## Idempotencia comprobada

Dos corridas seguidas del importador sobre la misma captura:

| Corrida | Filas leídas | Normas creadas | Ya presentes |
| --- | --- | --- | --- |
| 1 | 428.380 | 423.708 | 3 |
| 2 | 428.380 | 0 | 428.380 |

La segunda no creó nada y no dejó ninguna norma huérfana. La reconciliación es
por identificador oficial, no por posición ni por orden de archivo.

## Corpus con texto

Doce versiones normativas tienen texto capturado, segmentado, con identidad
resuelta, relaciones candidatas y los siete campos evaluados. Una llegó a
release publicado y se sirve por la API.

Sobre 84 fuentes del catálogo, 55 tienen al menos una captura y 48 tienen
documentos extraídos. Las 29 que quedan pendientes no están pendientes por
igual: 15 no tienen URL inequívoca en el manual, 2 están bloqueadas —una por un
certificado que no valida y otra por un 403— y el resto son de referencia, de
carga manual o retiradas, que el planificador no pide porque la política no lo
habilita. Una corrida anterior mostraba 64 fuentes con captura, y esa diferencia
no es una pérdida: eran capturas hechas antes de que el catálogo clasificara esas
fuentes, y hoy pedirlas sería recorrer lo que el manual dice que no se recorre.

Los tres casos difíciles que el paquete nombra están resueltos como pide:

- **F33 (Ley 24.714)**: abrogada *y* restablecida con excepciones. El grafo
  conserva ambos eventos y `estado_legal_validado` queda `NO_DETERMINADA`: no
  hay lectura automática posible.
- **F23 (Ley CABA 547)**: sustituye artículos de la Ordenanza 43.478. El texto
  transcrito queda anidado en la sustitución y no como artículo raíz de la
  modificatoria.
- **F19 (Resolución 1621/MEDGC/2025)**: la síntesis de la ficha dice 1261 y el
  encabezado dice 1621. La discrepancia se detectó como transposición de
  dígitos y quedó registrada; no se creó una norma 1261.

## Correspondencia entre versiones de una norma

El Decreto 1382/2001 tiene en InfoLEG dos textos: el original y el actualizado,
con 105 y 108 unidades dispositivas. Comparar los dos dio 60 correspondencias
reales: 59 renumeraciones y una sustitución.

Las 59 son unidades que corren de lugar sin cambiar de texto, porque arriba se
agregó un párrafo. El inciso 1 del artículo 10 pasa del ordinal 61 al 62; en el
texto viejo el 62 era el inciso 2. Quien resuelva «la unidad 62 del artículo 10»
obtiene «tener cónyuge» en una versión y «ser beneficiario del SIJP» en la otra.

La sustitución es el artículo 3, y es el caso más silencioso: conserva su número
con otro texto. InfoLEG consolidó ahí la corrección del Decreto 1407/2001 —«donde
dice incisos 1) y 5) debe decir incisos 1) a 5)»—. Una cita al artículo 3 sigue
apuntando a un artículo que existe; sólo que ya no dice lo mismo.

Las 60 quedaron `CANDIDATE`. Una correspondencia sin aprobar no redirige ninguna
cita: emparejar por texto idéntico la deriva pero no la comprueba, y dos
párrafos iguales en artículos distintos se emparejan solos. Aprobar es una
decisión con actor y fundamento (`bn revision aprobar-equivalencia`).

Cuatro unidades del texto nuevo no vienen de ninguna del viejo y una del viejo
no tiene destino. No reciben equivalencia: que un texto haya desaparecido no
significa que su contenido esté en otro lado.

## Documentos PDF

Seis fuentes en PDF capturadas y extraídas: D07, D08, D09, F40, F54 y F62, con
261 unidades. F38 y F63 también tienen texto en PDF y no se recorren solas: el
catálogo las declara de referencia y de carga manual, y el planificador no pide
lo que la política no habilita.

Las 261 unidades son menos que las 712 de la corrida anterior y dicen más. Antes
el adaptador de PDF armaba un párrafo por cada línea que devuelve
`extract_text_lines`, así que una oración quedaba repartida en cuatro unidades y
ninguna cita de una frase entera entraba en ninguna. Ahora los renglones se unen
y D09 —la Ley CABA 2917 en PDF— queda con sus artículos completos, de 186
caracteres promedio en vez de 76.

El caso que el manual describe como «prefijo PDF conocido» no era hipotético.
El endpoint legacy del Boletín Oficial de CABA
(`boletinoficialpdf.buenosaires.gob.ar/util/imagen.php`) antepone 231 bytes de
una advertencia de PHP al archivo, con `Content-Type: application/pdf`. Aparece
igual en D08, D09 y F40. Los bytes crudos quedan intactos en la captura; la
reparación produce un derivado y registra el desplazamiento exacto y el prefijo
descartado. Esos 231 bytes reales están guardados como fixture.

El caso de los períodos mixtos tampoco. En F62 —el PDF de montos del ciclo
lectivo 2026— la página 4 menciona septiembre, octubre y noviembre de 2025 y
trae tres tablas. Ninguna se resolvió por cercanía: las diez tablas del
documento quedaron en revisión con el motivo dicho. En F40, una página con tres
años distintos dejó su tabla en el mismo estado.

F54 tiene una página de cierre gráfica: se clasificó como tal y las otras seis
se usaron igual, sin declarar vacío el documento y sin hacerle OCR a la
carátula.

## Qué período rige para cada tabla de montos

El PDF de montos de becas (F62) trae once tablas repartidas en cinco páginas, y
la página 4 tiene tres tablas con tres meses distintos. Asociarlas por cercanía
haría que una tabla herede el monto de otro mes.

Mirando la geometría se ve que el epígrafe no está arriba de la tabla: **es su
primera fila**, adentro del recuadro. «CORRESPONDIENTES AL MES DE OCTUBRE 2025»
cae entre el borde superior y el inferior de su propia tabla. Eso convierte la
asociación en contención y no en proximidad: un período que está adentro de una
tabla no puede pertenecer a otra.

Diez de las once tablas quedaron fechadas así, contra una antes. Dos detalles
del documento real:

- La primera tabla de la página 5 dice «CORRESPONDIENTES A LOS MESES DE
  DICIEMBRE A MARZO 2026» y cubre cuatro meses. Quedarse con «marzo 2026»
  perdería diciembre, enero y febrero.
- La tabla de topes de monotributo de la página 3 no lleva su período adentro:
  lo lleva en una nota al pie, «**Hasta diciembre 2025», y la tabla misma tiene
  un «**». La marca es lo que las une, no la distancia.

La única que quedó en revisión es la de la página 7, y es correcto: no declara
período adentro y los dos que menciona la página —«ciclo lectivo 2026» y
«octubre 2018»— están cientos de puntos más abajo, en un párrafo. Fecharla con
ellos sería fecharla con el período de un texto que habla de otra cosa.

## Padrón RENABAP

6.467 barrios populares importados como snapshot versionado, cada uno con la
evidencia de su fila y su identidad lógica conservada entre versiones del
padrón.

El listado no viaja en el HTML de la página oficial: la página lo renderiza
desde una planilla publicada cuyo identificador declara su propio script. Ese
recurso se registró como candidata de F39 con esa evidencia antes de
promoverse a URL de la fuente, y se capturó por el camino normal.

Dos cosas que el padrón obligó a decidir:

**No se inventa una fecha de corte.** La planilla no declara ninguna. Se
registra la fecha de captura como referencia y `fecha_corte` queda vacía:
ponerla ahí haría creer que el padrón se cerró ese día.

**Un barrio que sale del padrón no se borra.** Cada importación crea una
versión nueva y cierra el intervalo de conocimiento anterior. La versión vieja
sigue diciendo que ese día estaba, que es lo único que permite responder qué
decía el padrón anterior.

`GET /v1/barrios-renabap` responde siempre diciendo contra qué versión del
padrón se buscó y por dónde se gestiona la inclusión. Que un barrio no figure
es un dato de ese corte y la respuesta lo dice con esas palabras: no habilita
ninguna conclusión sobre derechos.

## Directorios de atención

311 puntos de atención y 1.077 canales importados desde dos datasets abiertos
—sedes comunales de CABA (21 puntos, 61 canales) y efectores de desarrollo
humano (212 y 766)— y desde el directorio en HTML de la Defensoría del Pueblo de
la Nación (78 y 250).

Los casos que el manual anticipa aparecieron tal cual:

**Las coordenadas no son WGS84.** El dataset de sedes comunales trae
`POINT (28615.88 70947.08)`: una grilla local, sin CRS declarado. Interpretado
como longitud y latitud está fuera del planeta; con los ejes invertidos, en el
Golfo de Guinea. Las 21 sedes quedaron con `lat`/`lng` vacías, su geometría
cruda conservada con su origen, y una incidencia abierta pidiendo confirmar la
proyección. No se responde por cercanía hasta entonces.

**`N/A` no es un dato.** El dataset de efectores usa ese literal en nombre,
tipo y teléfono. 153 campos se guardaron como ausencia. El resto de la fila se
conserva: perder un correo electrónico bueno porque el teléfono venía vacío
sería descartar información por información.

**Quien publica el listado no es quien atiende.** El directorio de la DPN trae
tres secciones con el mismo formato: 4 oficinas regionales, 17 receptorías y 57
defensorías provinciales y municipales que son organismos autónomos. Las 57
quedaron con su propio organismo titular, en su propia jurisdicción, y con la
DPN como operadora del listado. A quien pregunta quién lo atiende en Avellaneda
se le responde el Defensor del Pueblo de Avellaneda. La carga abrió una
incidencia: la competencia y los horarios los fija cada organismo, no quien lo
lista.

**El recuento de la fuente encontró un error de lectura.** Cada panel del
directorio anuncia cuántas oficinas contiene. La primera versión del importador
leía sólo la primera de cada panel y cargó 39 de 78 sin que nada fallara: las
restricciones se cumplían y los reportes daban bien. Verificar el recuento
declarado contra lo leído es lo que lo mostró.

**Los correos vienen protegidos y no se toman.** Las 76 direcciones de correo
del directorio están ofuscadas con una protección contra recolección
automática. Se registró que el canal existe, con `publico` en falso y una nota
que remite al sitio del organismo; el valor no se decodificó.

**Un teléfono publicado se guarda como está.** De los 78 teléfonos, 36 son un
número único y se normalizaron. Los otros 42 traen varias líneas separadas por
`/`, internos o rótulos: partirlos fabricaría números que nadie publicó, así
que queda el texto de la fuente sin normalizar. Dos resultaron ser WhatsApp y
no se ofrecen como teléfono.

La dirección se conserva como la escribió la fuente, con el piso adentro si
viene adentro. Componer una legible mezclando dos fuentes que no coinciden
produce una dirección que no existe en ninguna de las dos.

## Cronogramas que no dicen de cuándo son

La página de cronograma de pagos de Progresar (F52) tiene cuatro contenedores y
dos vienen vacíos: se toma el que tiene contenido, no el primero. Y lo que ese
contenedor publica es un cronograma sin período: «El cronograma de pagos de la
beca Progresar correspondiente a **este mes** inicia el 9 de febrero», con las
fechas de la tabla —9, 10, 11, 12 y 13 de febrero— también sin año.

El monto y el orden por terminación de DNI se conservan, que son datos. Lo que
no se afirma es a qué mes corresponden. Completar el año con la fecha de captura
sería el mismo error que fechar un PDF por su carpeta, con un agravante: una
página que quedó sin actualizar publica el cronograma del mes pasado con
exactamente las mismas palabras.

La página de inscripción escolar (F17) cae en lo mismo por otra vía: dice «este
año». Las otras dos páginas institucionales del corpus sí declaran su período y
no quedan pendientes.

## Estado de las 83 fuentes

Ninguna quedó sin recorrer. 60 en curso, 18 bloqueadas con su motivo y su
responsable, 4 alias registrados y 1 cerrada con versión publicada.

Los tres bloqueos que aparecieron al recorrer el corpus completo son los que el
manual describe, y el sistema los trató como corresponde:

| Fuente | Qué pasó | Qué se hizo |
| --- | --- | --- |
| M05 (ANSES) | HTTP 403 | La fuente queda pausada. No se rotan identidades ni se evaden controles de acceso |
| F04 (La Defe) | El certificado no valida contra las CA del sistema | Se registra como `ERROR_TLS`. **No se relaja la validación**: hay que buscar fuente oficial equivalente o carga manual trazada |
| F06 (CDNNyA subsedes) | HTTP 404 | Se registra como `NO_ENCONTRADA` con la brecha de cobertura de subsedes |

Los bloqueos restantes son fuentes sin URL inequívoca: el manifiesto conserva su
identificador y su brecha, y nadie inventó una dirección para taparla.

Para todas ellas existe la vía de carga manual (`bn ingesta cargar-manual`),
que exige declarar quién consiguió el archivo, de dónde y cuándo. La fuente
queda en `MANUAL` y no en `ACTIVE`: haber conseguido un archivo una vez no la
vuelve recorrible.

Las páginas capturadas cuya extracción ninguna familia acepta quedan guardadas
sin extraer, con el aviso que lo dice. Son portales que necesitan un adaptador
propio: la captura está, el texto no, y el reporte no simula lo contrario.

## Calendario de plazos

28 feriados nacionales de 2026 cargados desde el archivo oficial que publica
`datos.gob.ar`, cada uno con la evidencia del fragmento que lo declara. El
archivo mezcla feriados inamovibles, trasladables, días no laborables y días no
laborables con fines turísticos: todos entran como no hábiles y conservan su
clase en el motivo, porque no todos se computan igual en todos los regímenes.

Con eso, un plazo de 5 días hábiles desde el 20 de marzo de 2026 vence el 31 y
no el 27: el cómputo excluye el fin de semana, el día no laborable con fines
turísticos del 23 y el feriado del 24. Un plazo que arranca el 20 de diciembre
queda no determinado, porque el calendario llega hasta el 31.

## Trámites

Dos fichas del portal nacional cargadas con 9 pasos citables: el reclamo ante
Defensa del Consumidor (F45) y la obtención del Certificado Único de
Discapacidad (M06).

Las dos declaran su costo y **ninguna declara cuánto tarda**. El campo de
duración existe en la ficha y está vacío. Queda vacío también en la base, con
una incidencia abierta: completarlo con «inmediato» produce una respuesta sobre
la que alguien planifica.

Los pasos no se aplanan. «Completá el formulario con: tus datos personales, los
datos del reclamo, los datos del proveedor» es un paso con tres aclaraciones, no
cuatro pasos; aplanarlo haría que el paso 3 que se le responde a alguien sea en
realidad un detalle del paso 2. Las aclaraciones quedan como documentación del
paso que las contiene.

`publico` no se deduce del texto de «¿a quién está dirigido?»: que diga «a los
consumidores» no dice si el trámite es ciudadano o institucional. Y que la ficha
esté publicada no prueba que el trámite esté tomando solicitudes hoy, así que el
estado operativo queda `NO_INFORMADO`.

## Los pasos de un instructivo en PDF

El instructivo de revisión de solicitudes (F54) numera sus pasos y trae cinco.
Se leen los cinco, en el orden que el documento declara y no en el que el
extractor devuelve el texto: si un rótulo sale después de su contenido, ordenar
por lectura invierte el trámite.

Dos cosas del documento real que obligan a algo más que buscar «Paso N»:

- **El paso 4 cruza de página.** Empieza en la página 3 y su «Documentación
  necesaria» —el DNI, la constancia de alumno regular, los comprobantes de
  ingresos— está en la 4, sin rótulo propio. Es el mismo paso, no uno nuevo sin
  número.
- **Cada página repite «Becas alimentarias» arriba y el folio abajo.** El
  encabezado se detecta por repetición en vez de configurarse: cada instructivo
  tiene el suyo y una lista de encabezados conocidos envejece mal.

Un número repetido, un salto en la serie o un paso que sólo muestra una captura
de pantalla no se corrigen solos: se cargan los pasos que hay y se dice cuál es
el problema. Renumerar por orden de aparición inventaría una secuencia que el
documento no declara.

## Páginas institucionales

31 páginas de portales oficiales extraídas: cronogramas, listados de sedes,
directorios y páginas de inscripción. No tienen articulado, así que lo que
importa de ellas es lo que el adaptador se niega a dar por bueno, y los tres
casos que el manual anticipa estaban ahí.

**Un contenedor vacío no es contenido.** Estas páginas repiten la misma
estructura para varios períodos y la del que todavía no arrancó viene en
blanco. F52 tiene 4 contenedores y 2 vacíos; F53, 13 y 7. Tomar el primero
porque es el primero deja una carga exitosa sin datos.

**Lo que la página esconde no es lo que publica.** F27 trae 2 bloques detrás de
un `d-none` y F17 trae 5. No entran como contenido vigente y se informan
aparte: que la página tenga un ciclo viejo escondido permite responder «esa
inscripción es del ciclo anterior» en vez de no responder.

**Una tabla que no está no es una tabla vacía.** F64 dice, con esas palabras,
que «la atención presencial de las sedes permanecerá cerrada hasta el comienzo
del nuevo periodo de inscripción». Eso es el dato de hoy. Rescatar el listado de
una captura anterior lo presentaría como vigente.

## Primer beneficio curado

La Ley CABA 6935 publicada dejó de ser solo texto: es un beneficio con 3
poblaciones, 9 reglas y una cuantía, cada pieza atada al artículo que la
sostiene. La lectura jurídica vive en `docs/curaduria/ley-caba-6935.json` y no
en el código, para que se pueda discutir contra la ley sin leer Python.

Cinco reglas se pudieron formalizar: la antigüedad de residencia de dos años, su
excepción para víctimas de trata o violencia de género, las dos exclusiones del
artículo 6.c y la salvaguarda de ingreso provisorio del artículo 8.

**Cuatro no.** El ingreso contra la Canasta Básica Total varía según la
conformación del hogar y el parámetro no está segmentado; la subsanación
documental, la incompatibilidad del pago único y las corresponsabilidades del
artículo 7 los remite la ley a una reglamentación que no está en el corpus. Las
cuatro conservan su texto literal y ninguna condición inventada.

`criterios_revocacion` queda `NO_INFORMADO`. La ley habla de continuidad sujeta
a corresponsabilidades y de regularización documental, pero suspensión, cese y
revocación son tres efectos distintos y el texto no elige entre ellos. Que no
consten no significa que no existan.

La cuantía es una fórmula sin valor. La ley fija un piso para hogares de cuatro
o más integrantes y remite el resto de la escala a la Autoridad de Aplicación:
servir el piso como «el monto» diría que todos cobran lo mismo.

Nada de esto entra aprobado. Todo queda candidato, porque la evaluación de un
beneficio decide si alguien puede pedir algo y que lo haya escrito una curaduría
no lo vuelve derecho aplicable. El esquema lo impone: una regla con AST solo
puede quedar sin revisión si ya está aprobada.

## Lo que falta y por qué

| Falta | Depende de | Afecta |
| --- | --- | --- |
| Vincular el anexo D07 con su resolución D04 | Curación de identidad sobre PDF | AT-029 |
| Fechar los documentos PDF por su contenido | Lectura de fecha en el propio documento | AT-075 |
| Fichas de trámite fuera del portal nacional | Un adaptador por portal (F24, F56 en buenosaires.gob.ar) | Trámites de CABA |
| Directorios en HTML de F05, F07 y F10 | Un adaptador por portal: F44 ya está cargado; F05 y F07 son páginas de navegación cuyo listado vive en otra URL y F10 arma su tabla desde una planilla publicada | F05, F07, F10 |
| Ferias administrativas y judiciales, y feriados provinciales | Otros calendarios además del nacional | Plazos judiciales y provinciales |

Ninguna de estas es una fuente inaccesible: son capacidades que este alcance no
construyó. Las fuentes que sí están bloqueadas —por antibot, por `robots.txt` o
por no tener URL inequívoca— figuran con su motivo, su responsable y su
capacidad afectada en el reporte de backlog, y su ingesta está pausada. No se
rota identidad para entrar.
