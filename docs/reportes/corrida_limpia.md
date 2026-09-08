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

- Arranque: `2026-09-08T18:24:17+00:00`
- Cierre: `2026-09-08T18:30:57+00:00`
- Resultado: **completa**
- Base: `backend_normativo_limpia`
- Fuentes que el planificador deja pendientes al cerrar: `2`

## Pasos

El detalle paso por paso vive en `scripts/poblar_corpus.sh`, que es lo que
corre acá. Lo que se mide es cuánto tarda entero y con qué queda.

| Paso | Duración | Última línea |
| --- | ---: | --- |
| migraciones | 1.3 s | INFO  [alembic.runtime.migration] Running upgrade 0006_indice_de_listado -> 0007_servibl… |
| población completa | 397.4 s | Incidencias abiertas: 12 |
| planificación al cierre (en seco) | 0.7 s | alguien corre el comando. |

## Con qué quedó la base

| Qué | Cuántos |
| --- | ---: |
| Fuentes en el catálogo | 84 |
| Capturas | 69 |
| Unidades documentales | 992 |
| Beneficios curados | 3 |
| Incidencias abiertas | 4602 |

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
| C01 | COMPLETA | 1 | 1 | 0 |  |
| D01 | COMPLETA | 1 | 1 | 0 |  |
| D01 | COMPLETA | 3 | 3 | 0 |  |
| D02 | COMPLETA | 1 | 1 | 0 |  |
| D02 | COMPLETA | 2 | 2 | 0 |  |
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
| F39 | COMPLETA | 2 | 2 | 0 |  |
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

Las corridas en `FALLIDA` de esta lista no son un error del sistema: son el
sistema haciendo lo que tiene que hacer cuando el otro lado no deja pasar. Un
certificado que no valida no se acepta igual, y un 403 no se contesta rotando
identidad: la fuente queda pausada, con el motivo escrito en la fila de su
corrida, y su cobertura se resuelve por fuente equivalente o carga manual
trazada. Volverlas verdes relajando TLS o cambiando de identidad sería
convertir un acceso bloqueado en un dato inventado.

## Incidencias que abrió la corrida

| Tipo | Cuántas |
| --- | ---: |
| IDENTIDAD_AMBIGUA | 4492 |
| COBERTURA_EXTRACCION | 43 |
| VIGENCIA_INDETERMINADA | 24 |
| ACCESO_BLOQUEADO | 17 |
| DATO_FALTANTE_CRITICO | 17 |
| DISCREPANCIA_NUMERACION | 5 |
| CONFLICTO_DE_FUENTES | 4 |
