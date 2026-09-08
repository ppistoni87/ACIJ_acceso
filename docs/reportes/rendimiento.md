# Rendimiento de las consultas sobre el corpus real

Una latencia sin decir sobre cuántas filas se midió no significa nada, así que el
tamaño del corpus va primero.

- Tamaño de la base: **304 MB**
- Repeticiones por consulta: **12**

| Tabla | Filas |
| --- | ---: |
| `normas` | 423,718 |
| `norma_versiones` | 12 |
| `unidades_documentales` | 992 |
| `evidencias` | 7,439 |
| `registro_versiones` | 7,809 |
| `puntos_atencion` | 290 |
| `canales` | 1,012 |
| `barrios_renabap` | 6,467 |

## Latencias

| Consulta | Ruta | Filas | 1ª (ms) | p50 (ms) | p95 (ms) | máx (ms) | HTTP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normas: listado | `/v1/normas` | 20 | 32.82 | 21.77 | 31.82 | 32.82 | 200 |
| normas: búsqueda por texto | `/v1/normas` | 20 | 22.54 | 18.1 | 21.71 | 22.54 | 200 |
| normas: búsqueda por tipo y año | `/v1/normas` | 50 | 20.34 | 19.56 | 21.4 | 23.95 | 200 |
| beneficios | `/v1/beneficios` | 3 | 25.3 | 6.58 | 7.5 | 25.3 | 200 |
| puntos de atención | `/v1/puntos-atencion` | 0 | 8.76 | 7.35 | 8.76 | 8.9 | 200 |
| puntos por jurisdicción | `/v1/puntos-atencion` | 0 | 6.7 | 5.63 | 6.48 | 6.7 | 200 |
| puntos por alcance municipal | `/v1/puntos-atencion` | 0 | 7.28 | 6.64 | 7.28 | 7.67 | 200 |
| barrios RENABAP por nombre | `/v1/barrios-renabap` | 100 | 13.11 | 10.53 | 11.17 | 13.11 | 200 |
| cobertura del release | `/v1/cobertura` | — | 44.38 | 25.99 | 29.51 | 44.38 | 200 |

## Con varias consultas a la vez

Cada petición toma su propia conexión del pool, así que la contención de
conexiones y la del motor son reales.

| Hilos | Consultas | Duración (s) | Consultas/s | p50 (ms) | p95 (ms) | máx (ms) | Errores |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 0.139 | 71.9 | 14.24 | 25.07 | 25.07 | 0 |
| 4 | 40 | 0.584 | 68.5 | 52.3 | 127.05 | 138.22 | 0 |
| 16 | 160 | 2.172 | 73.7 | 180.7 | 454.27 | 468.55 | 0 |

## Qué dicen y qué no dicen estos números

La primera repetición se informa aparte porque es la única que se parece a un
servidor recién arrancado: las siguientes encuentran la caché del motor caliente.

La consulta más lenta es «normas: listado» con 31.82 ms en el percentil 95.

**Esto sigue sin ser una prueba de carga de producción.** Corre en proceso, sin red,
sin balanceador y contra una sola instancia. El número de consultas por segundo es un
techo optimista, no una capacidad comprometida.

### Dónde está el techo

Con la misma concurrencia, el motor sostiene **1389.1 consultas por segundo** y la API se queda en **73.7**. La diferencia dice dónde está el límite: no en la base ni en las conexiones, sino en el proceso que arma y serializa cada respuesta.

Es un dato que cambia qué hacer para escalar. Agrandar el pool o agregar índices no mueve este número; agregar procesos sí. Medirlo antes de optimizar evita gastar el trabajo en el lado que no era.
