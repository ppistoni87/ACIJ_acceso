# Fuentes contra su historia

El manifiesto declara en qué tablas tiene que terminar lo que cada fuente aporta. Esto compara lo declarado con lo que hay. Una fila se atribuye a una fuente cuando su evidencia lleva de vuelta a un documento de esa fuente.

- Fuentes en el catálogo: 85
- **Sirven** (dejaron filas donde su historia dice): 44, de las cuales 1 acreditadas por la conciliación del importador y no por evidencia por fila
- **Capturadas, extraídas y sin destino** (200 y ninguna fila): 7
- **Capturadas y nunca extraídas**: 2
- Solo descubrimiento (su destino es el catálogo mismo): 2
- Bloqueadas: 17
- Sin correr: 13

## Capturadas y sin llegar a destino

Estas respondieron, se extrajeron y no dejaron una sola fila donde su historia dice que deberían. Es exactamente lo que el criterio quiere ver: un HTTP 200 no acredita nada por sí solo.

| Fuente | Prioridad | Versiones | Unidades | Tablas declaradas y vacías |
| --- | --- | ---: | ---: | --- |
| F18 | P0 | 2 | 3 | canales |
| F52 | P0 | 2 | 1 | parametro_valores, plazos |
| F53 | P0 | 9 | 23 | tramites, plazos |
| F66 | P0 | 5 | 7 | reglas, beneficio_versiones |
| F32 | P1 | 1 | 5 | canales |
| F49 | P1 | 7 | 6 | tramites, canales |
| F64 | P1 | 1 | 1 | puntos_atencion |

## Capturadas y nunca extraídas

Respondieron 200, los bytes están guardados y ninguna versión documental salió de ellos. No es lo mismo que la anterior: acá el problema está antes, en que ningún adaptador las procesó.

| Fuente | Prioridad | Capturas | Último HTTP | Tablas declaradas |
| --- | --- | ---: | ---: | --- |
| M01 | P0 | 1 | 200 | documentos, relaciones_normativas |
| M03 | P0 | 1 | 200 | normas |

## Bloqueadas

El fallo se conserva y la capacidad queda pendiente. No se convierte en «sin datos».

| Fuente | Estado de acceso | Motivo | Incidencias abiertas |
| --- | --- | --- | ---: |
| M05 | ACCESO_LIMITADO | Contenido incorporado por carga manual (ingesta:equipo-de-datos): Marcador de vía manual creado durante la imp | 9 |
| F04 | ERROR_TLS | https://ladefe.gob.ar/soy-una-nina-nino-o-adolescente/: Fallo de validación TLS: [SSL: CERTIFICATE_VERIFY_FAIL | 7 |
| F08 | SIN_URL_CONOCIDA | — | 1 |
| F13 | SIN_URL_CONOCIDA | — | 1 |
| F14 | SIN_URL_CONOCIDA | — | 1 |
| F15 | SIN_URL_CONOCIDA | — | 1 |
| F21 | SIN_URL_CONOCIDA | — | 1 |
| F22 | SIN_URL_CONOCIDA | — | 1 |
| F26 | SIN_URL_CONOCIDA | — | 1 |
| F30 | SIN_URL_CONOCIDA | — | 1 |
| F34 | SIN_URL_CONOCIDA | — | 1 |
| F35 | SIN_URL_CONOCIDA | — | 1 |
| F37 | SIN_URL_CONOCIDA | — | 1 |
| F42 | SIN_URL_CONOCIDA | — | 1 |
| F57 | SIN_URL_CONOCIDA | — | 1 |
| F58 | SIN_URL_CONOCIDA | — | 1 |
| F59 | SIN_URL_CONOCIDA | — | 1 |

## Sin correr

Ninguna captura las tocó. No están bloqueadas —no hay impedimento registrado— simplemente no llegó su turno, y por eso su estado de acceso sigue sin verificar: verificarlo es intentarlo.

- F02, F06, F09, F10, F24, F28, F29, F38, F41, F55, F56, F63, F65

## Qué no dice

Que lo que llegó sea correcto ni completo. Dice que llegó algo a la tabla que la historia declara. Que la paginación se haya recorrido entera, que los anexos estén y que el contenido sea el esperado lo verifica la prueba de cada familia de fuentes, no este recuento.

Tampoco dice que una fuente sin filas esté rota: puede que su aporte ya estuviera cargado por otra que publica la misma norma. Lo que dice es que su historia, como está declarada, no se cumplió.
