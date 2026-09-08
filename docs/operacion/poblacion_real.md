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

## Lo que falta y por qué

| Falta | Depende de | Afecta |
| --- | --- | --- |
| Vincular el anexo D07 con su resolución D04 | Curación de identidad sobre PDF | AT-029 |
| Fechar los documentos PDF por su contenido | Lectura de fecha en el propio documento | AT-075 |
| Trámites, pasos y canales | Importador de trámites (HU-019) | F03, F45, F60, F61 y los casos operativos |
| Directorios y puntos de atención | Importador de directorios (HU-020) | F05, F07, F10, F14, F20, F44 |
| Calendarios jurisdiccionales | Calculadora de días hábiles (HU-016) | AT-051 |

Ninguna de estas es una fuente inaccesible: son capacidades que este alcance no
construyó. Las fuentes que sí están bloqueadas —por antibot, por `robots.txt` o
por no tener URL inequívoca— figuran con su motivo, su responsable y su
capacidad afectada en el reporte de backlog, y su ingesta está pausada. No se
rota identidad para entrar.
