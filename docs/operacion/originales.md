# Acta de los originales

Evidencia de P-004: recuperar el original exacto de cada afirmación aunque
cambie la página o se borre el contenedor. Registra lo verificado el 9 de
septiembre de 2026 sobre el corpus real de este entorno.

## Qué se guarda de cada captura

El criterio pide bytes, SHA-256, tipo, tamaño, fecha, URL solicitada y final,
resultado HTTP y versión del adaptador. Contra las 242 capturas de la base:

| Dato | Dónde vive | Faltantes |
| --- | --- | --- |
| Bytes | Almacén, direccionado por hash | 0 |
| SHA-256 | `capturas.sha256_raw` | 0 |
| Tipo | `capturas.mime` | 70 → ver abajo |
| Tamaño | `capturas.bytes` | 0 |
| Fecha | `capturas.capturado_en` | 0 |
| URL solicitada | `capturas.source_url_id` → `fuente_urls.url` | 0 |
| URL final | `capturas.url_final` | 1 |
| Resultado HTTP | `capturas.http_status` | 1 |
| Versión del adaptador | `corridas_ingesta.extractor_version` y `config_version_id` → `fuente_config_versiones.adaptador` | 0 |

**Las dos faltas de URL final y resultado HTTP son la misma fila, y es correcta.**
Es la carga manual de M05, hecha cuando ANSES respondió 403. No hubo respuesta
HTTP: poner un 200 diría que el servidor contestó. Su `cabeceras` guarda actor,
procedencia, fecha y archivo de origen.

**Las 70 sin tipo eran un defecto y está corregido.** Todas son respuestas
`304 Not Modified`. Un 304 no trae cuerpo y por eso tampoco trae
`Content-Type`; el capturador ya reutilizaba el hash, el URI y el tamaño de la
captura previa, pero no el tipo, así que cada revalidación borraba un dato que
la primera captura sí había sabido. Ahora lo hereda de la captura cuyos bytes
reutiliza. Las filas viejas quedan como están —`capturas` es inmutable por
trigger, y reescribir una captura sería exactamente lo que el esquema prohíbe—;
la próxima corrida limpia las produce completas.

## Deduplicación

El almacén direcciona por contenido: la ruta de un objeto es su SHA-256. Dos
capturas del mismo contenido comparten el objeto sin copiarlo dos veces, y una
captura nueva no puede pisar a otra, porque contenido distinto es hash distinto
y por lo tanto ruta distinta. En el corpus real esto se ve: **242 capturas
apoyadas en 94 objetos**. La escritura es por archivo temporal y renombrado, así
que una corrida interrumpida no deja un objeto a medias con un hash que promete
contenido completo.

## Que el original siga estando, comprobado

`bn objetos verificar` lee del almacén cada objeto que la base referencia y
compara el hash. Sobre el corpus real: **94 referencias, 94 recuperadas con
hash coincidente, 0 con problema.**

Cuando un objeto falta o difiere no alcanza con informarlo. Un objeto ausente es
indistinguible de uno correcto hasta que alguien lo lee, y para entonces lo que
dependía de él ya se sirvió. Así que la verificación abre una incidencia
CRITICAL sobre cada versión que dependa del objeto roto, y esa incidencia
bloquea la publicación por el camino que ya existía: `bn_motivos_no_servible`
devuelve CONFLICT ante una incidencia abierta de severidad alta. El tipo
`EVIDENCIA_NO_RECUPERABLE` lo agrega la migración 0009; los ocho anteriores
describen problemas de la norma o de la fuente, y este es del almacén.

Ensayo hecho sobre una copia del almacén real: se borró un objeto y se alteró
otro, ambos referenciados. La verificación encontró los dos, los distinguió
—«no está» contra «sus bytes no hashean a lo que la captura declara»— y terminó
con código 1. Verificar dos veces no duplica la incidencia.

## Que sobreviva al contenedor

`bn objetos sincronizar <destino>` copia al destino los objetos que la base
referencia y **relee cada uno desde allá** para comprobar el hash: una copia que
nadie volvió a leer no es un respaldo. Copia solo lo referenciado; el almacén
local acumula objetos de corridas que nadie citó, y conservarlos fuera es pagar
por guardar algo que ninguna afirmación necesita.

Ensayo sobre el corpus real: **94 objetos, 53,3 MiB, copiados y releídos con
hash correcto.** La segunda corrida copió 0 y encontró los 94 ya puestos.
Verificando después contra ese almacén, 94 de 94 íntegros: el original de
cualquier afirmación se recupera desde una instancia que no es la que lo
capturó, que es exactamente el criterio 3.

## Lo que este acta no acredita

- **No hay bucket privado.** El destino ensayado es un directorio. La interfaz
  del almacén está aislada y el comando apunta a donde se le diga —un volumen
  montado, un bucket montado—, pero provisionar el bucket exige una cuenta
  cloud, y escribir un backend `gs://` que nadie pudo probar sería peor que la
  excepción explícita que hay hoy para todo esquema que no sea `file://`.
- **No hay política de retención.** Cuántas copias, por cuánto tiempo, con qué
  objetivo de recuperación: nada de eso está decidido, y el comando no lo suple.
- **Verificar no valida contenido.** Que un objeto esté y hashee bien dice que
  es el mismo que se capturó, no que lo capturado sea correcto. Si la fuente
  publicó algo equivocado, esto lo confirma equivocado e intacto.
- **La verificación no repone nada.** Avisa que hace falta recuperar un
  original; traerlo exige tenerlo en otro lado.
