# Corrida limpia: de una base vacía a un corpus servible

Lo que esto demuestra es que la puesta en marcha es reproducible: las
migraciones corren desde cero, el catálogo de las 83 fuentes entra, el
planificador recorre la red de verdad, los importadores cargan el catálogo
nacional, el padrón y los directorios, y la curación trabaja sobre lo
capturado.

Lo que **no** demuestra es que corra igual en otra máquina o desde otra red.
Para eso hace falta otra máquina y otra red; lo que queda acá es el
procedimiento escrito, cronometrado y con el resultado fuente por fuente, para
que la diferencia se pueda medir cuando alguien lo corra allá.

Generado por `scripts/corrida_limpia.sh`. La base se crea y se destruye en la
misma corrida: si algo de acá se pudiera explicar por estado previo, no habría
estado previo del que agarrarse.

- Arranque: `2026-09-10T19:08:17+00:00`
- Cierre: `2026-09-10T19:13:50+00:00`
- Resultado: **interrumpida en «población completa»**
- Base: `backend_normativo_limpia`
- Fuentes que el planificador deja pendientes al cerrar: `—`

## Pasos

El detalle paso por paso vive en `scripts/poblar_corpus.sh`, que es lo que
corre acá. Lo que se mide es cuánto tarda entero y con qué queda.

| Paso | Duración | Última línea |
| --- | ---: | --- |
| migraciones | 1.4 s | INFO  [alembic.runtime.migration] Running upgrade 0014_identidad_en_la_bitacora -> 0015_… |
| población completa | 330.7 s | **falló** — F36: 8 URLs promovidas |

## Con qué quedó la base

| Qué | Cuántos |
| --- | ---: |
| Fuentes en el catálogo | 83 |
| Capturas | 66 |
| Unidades documentales | 1033 |
| Beneficios curados | 0 |
| Incidencias abiertas | 125 |

Las incidencias abiertas no son un fallo de la corrida: son lo que el sistema
encontró y no resolvió solo. Una corrida limpia que no abriera ninguna estaría
escondiendo algo. La enorme mayoría viene del catálogo nacional, que se importa
entero como metadatos: son normas cuyo tipo se numera por organismo y cuya
clave (tipo, número, año) no las distingue. Quedan marcadas para que ninguna
resuelva una cita por número, que es exactamente lo que la incidencia protege.

## Qué pasó fuente por fuente

Una fuente que no entrega no es una fuente vacía. Acá está el estado con el que
cerró cada corrida de ingesta, con lo que el servidor contestó cuando contestó
algo distinto de los datos.

| Fuente | Estado | Solicitadas | Descargadas | Rechazadas | Detalle |
| --- | --- | ---: | ---: | ---: | --- |
| F04 | FALLIDA | 1 | 0 | 1 | https://ladefe.gob.ar/soy-una-nina-nino-o-adolescente/: Fallo de validación TLS: [SSL: CERTIFICATE_VERIFY_FAIL |
| M05 | FALLIDA | 1 | 0 | 1 | https://www.anses.gob.ar/: HTTP 403. La fuente queda pausada; no se rotan identidades ni se evaden controles d |
| D01 | COMPLETA | 3 | 3 | 0 |  |
| D01 | COMPLETA | 1 | 1 | 0 |  |
| D02 | COMPLETA | 2 | 2 | 0 |  |
| D02 | COMPLETA | 1 | 1 | 0 |  |
| D03 | COMPLETA | 1 | 1 | 0 |  |
| D03 | COMPLETA | 1 | 1 | 0 |  |
| D04 | COMPLETA | 1 | 1 | 0 |  |
| D04 | COMPLETA | 1 | 1 | 0 |  |
| D05 | COMPLETA | 1 | 1 | 0 |  |
| D05 | COMPLETA | 1 | 1 | 0 |  |
| D06 | COMPLETA | 1 | 1 | 0 |  |
| D06 | COMPLETA | 1 | 1 | 0 |  |
| D07 | COMPLETA | 1 | 1 | 0 |  |
| D08 | COMPLETA | 1 | 1 | 0 |  |
| D09 | COMPLETA | 1 | 1 | 0 |  |
| D10 | COMPLETA | 1 | 1 | 0 |  |
| D10 | COMPLETA | 1 | 1 | 0 |  |
| F01 | COMPLETA | 1 | 1 | 0 |  |
| F03 | COMPLETA | 1 | 1 | 0 |  |
| F05 | COMPLETA | 1 | 1 | 0 |  |
| F07 | COMPLETA | 1 | 1 | 0 |  |
| F11 | COMPLETA | 1 | 1 | 0 |  |
| F12 | COMPLETA | 1 | 1 | 0 |  |
| F16 | COMPLETA | 2 | 2 | 0 |  |
| F17 | COMPLETA | 1 | 1 | 0 |  |
| F18 | COMPLETA | 1 | 1 | 0 |  |
| F19 | COMPLETA | 1 | 1 | 0 |  |
| F20 | COMPLETA | 1 | 1 | 0 |  |
| F23 | COMPLETA | 1 | 1 | 0 |  |
| F25 | COMPLETA | 1 | 1 | 0 |  |
| F27 | COMPLETA | 1 | 1 | 0 |  |
| F31 | COMPLETA | 1 | 1 | 0 |  |
| F32 | COMPLETA | 1 | 1 | 0 |  |
| F33 | COMPLETA | 1 | 1 | 0 |  |
| F33 | COMPLETA | 1 | 1 | 0 |  |
| F36 | COMPLETA | 1 | 1 | 0 |  |
| F39 | COMPLETA | 1 | 1 | 0 |  |
| F40 | COMPLETA | 1 | 1 | 0 |  |
| F43 | COMPLETA | 1 | 1 | 0 |  |
| F44 | COMPLETA | 1 | 1 | 0 |  |
| F45 | COMPLETA | 1 | 1 | 0 |  |
| F46 | COMPLETA | 1 | 1 | 0 |  |
| F47 | COMPLETA | 1 | 1 | 0 |  |
| F48 | COMPLETA | 1 | 1 | 0 |  |
| F49 | COMPLETA | 1 | 1 | 0 |  |
| F50 | COMPLETA | 1 | 1 | 0 |  |
| F51 | COMPLETA | 1 | 1 | 0 |  |
| F52 | COMPLETA | 1 | 1 | 0 |  |
| F53 | COMPLETA | 1 | 1 | 0 |  |
| F54 | COMPLETA | 1 | 1 | 0 |  |
| F60 | COMPLETA | 1 | 1 | 0 |  |
| F61 | COMPLETA | 1 | 1 | 0 |  |
| F62 | COMPLETA | 1 | 1 | 0 |  |
| F64 | COMPLETA | 1 | 1 | 0 |  |
| F66 | COMPLETA | 1 | 1 | 0 |  |
| F67 | COMPLETA | 2 | 2 | 0 |  |
| M01 | COMPLETA | 1 | 1 | 0 |  |
| M02 | COMPLETA | 1 | 1 | 0 |  |
| M03 | COMPLETA | 1 | 1 | 0 |  |
| M04 | COMPLETA | 1 | 1 | 0 |  |
| M06 | COMPLETA | 1 | 1 | 0 |  |

No todas las corridas en `FALLIDA` son iguales. Un tiempo de espera agotado o una
conexión cortada es el portal de turno teniendo un mal momento: el cliente reintenta
tres veces y a veces no alcanza, así que el número de capturas varía de una corrida a
la siguiente. Eso no cambia lo que el sistema afirma —una fuente que no entregó no
aporta nada, y se nota— pero explica por qué dos corridas del mismo día no dan
exactamente el mismo total.

Las otras dos no son un error del sistema: son el
sistema haciendo lo que tiene que hacer cuando el otro lado no deja pasar. Un
certificado que no valida no se acepta igual, y un 403 no se contesta rotando
identidad: la fuente queda pausada, con el motivo escrito en la fila de su
corrida, y su cobertura se resuelve por fuente equivalente o carga manual
trazada. Volverlas verdes relajando TLS o cambiando de identidad sería
convertir un acceso bloqueado en un dato inventado.

## La segunda pasada no agrega nada

El procedimiento se documenta como idempotente: reejecutarlo revalida las
capturas, no duplica versiones y solo reprocesa lo que cambió. Acá se corre
dos veces seguidas sobre la misma base y se cuenta lo que hay antes y después.
Una primera pasada nunca prueba la segunda, y la segunda es la que corre en
producción todos los días.

La segunda pasada no llegó a correr: la corrida se interrumpió antes.

## Lecturas curadas que no se pudieron cargar

Una lectura curada se apoya en el texto capturado de su norma: sin ese texto no
hay nada que citar y el beneficio no entra. Que falte no es un error de la
lectura, es que la fuente no entregó en esta corrida.

| Lectura | Norma que le falta |
| --- | --- |
| `decreto-nacional-1602-2009.json` | `infoleg:159466:original` |
| `decreto-nacional-1667-2012.json` | `infoleg:202004:original` |
| `decreto-nacional-840-2020.json` | `infoleg:343905:original` |

> **El reporte no cierra:** 22 lecturas curadas, 3 sin su norma
> en el corpus y 16 código(s) de beneficio distinto(s) entre las que sí la
> tienen, pero la base quedó con 0. Hay un error en este informe o una
> lectura que cargó a medias; no se puede leer como evidencia hasta resolverlo.

> **Faltan lecturas:** 22 lecturas curadas, 3 sin su norma en el
> corpus, así que tendrían que haber entrado 19 y entraron
> 0. Las que faltan no son fuentes que no entregaron: son lecturas que la
> carga rechazó, y el motivo está en la salida de `bn curacion beneficios`.

## Incidencias que abrió la corrida

| Tipo | Cuántas |
| --- | ---: |
| COBERTURA_EXTRACCION | 84 |
| ACCESO_BLOQUEADO | 17 |
| VIGENCIA_INDETERMINADA | 14 |
| CONFLICTO_DE_FUENTES | 3 |
| DISCREPANCIA_NUMERACION | 3 |
| DATO_FALTANTE_CRITICO | 2 |
| IDENTIDAD_AMBIGUA | 2 |
