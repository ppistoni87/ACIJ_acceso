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

Ocho normas del alcance tienen texto capturado, segmentado, con identidad
resuelta, relaciones candidatas y los siete campos evaluados. Una llegó a
release publicado y se sirve por la API.

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

## Documentos PDF

Ocho fuentes en PDF capturadas y extraídas: D07, D08, D09, F38, F40, F54, F62 y
F63. 712 unidades nuevas y 22 incidencias abiertas.

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

233 puntos de atención y 766 canales importados desde dos datasets abiertos:
sedes comunales de CABA (F20) y efectores de desarrollo humano (F60).

Los dos casos que el manual anticipa aparecieron tal cual:

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

La dirección se conserva como la escribió la fuente, con el piso adentro si
viene adentro. Componer una legible mezclando dos fuentes que no coinciden
produce una dirección que no existe en ninguna de las dos.

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

## Lo que falta y por qué

| Falta | Depende de | Afecta |
| --- | --- | --- |
| Vincular el anexo D07 con su resolución D04 | Curación de identidad sobre PDF | AT-029 |
| Fechar los documentos PDF por su contenido | Lectura de fecha en el propio documento | AT-075 |
| Fichas de trámite fuera del portal nacional | Un adaptador por portal (F24, F56 en buenosaires.gob.ar) | Trámites de CABA |
| Directorios en HTML | Adaptador por portal (HU-020) | F05, F07, F10, F44 |
| Ferias administrativas y judiciales, y feriados provinciales | Otros calendarios además del nacional | Plazos judiciales y provinciales |

Ninguna de estas es una fuente inaccesible: son capacidades que este alcance no
construyó. Las fuentes que sí están bloqueadas —por antibot, por `robots.txt` o
por no tener URL inequívoca— figuran con su motivo, su responsable y su
capacidad afectada en el reporte de backlog, y su ingesta está pausada. No se
rota identidad para entrar.
