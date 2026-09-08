# Rendimiento de las consultas sobre el corpus real

Una latencia sin decir sobre cuántas filas se midió no significa nada, así que el
tamaño del corpus va primero.

- Tamaño de la base: **371 MB**
- Repeticiones por consulta: **12**

| Tabla | Filas |
| --- | ---: |
| `normas` | 423,718 |
| `norma_versiones` | 12 |
| `unidades_documentales` | 1,562 |
| `evidencias` | 7,498 |
| `registro_versiones` | 7,893 |
| `puntos_atencion` | 311 |
| `canales` | 1,077 |
| `barrios_renabap` | 6,467 |

## Latencias

| Consulta | Ruta | Filas | 1ª (ms) | p50 (ms) | p95 (ms) | máx (ms) | HTTP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normas: listado | `/v1/normas` | 20 | 34.13 | 21.04 | 22.76 | 34.13 | 200 |
| normas: búsqueda por texto | `/v1/normas` | 20 | 20.94 | 20.3 | 21.37 | 21.8 | 200 |
| normas: búsqueda por tipo y año | `/v1/normas` | 50 | 20.56 | 20.76 | 21.39 | 21.56 | 200 |
| beneficios | `/v1/beneficios` | 2 | 20.94 | 5.98 | 6.45 | 20.94 | 200 |
| puntos de atención | `/v1/puntos-atencion` | 0 | 7.68 | 6.34 | 7.04 | 7.68 | 200 |
| puntos por jurisdicción | `/v1/puntos-atencion` | 0 | 5.8 | 5.33 | 6.01 | 6.16 | 200 |
| puntos por alcance municipal | `/v1/puntos-atencion` | 0 | 5.63 | 5.69 | 6.21 | 6.26 | 200 |
| barrios RENABAP por nombre | `/v1/barrios-renabap` | 100 | 10.24 | 8.83 | 10.24 | 10.82 | 200 |
| cobertura del release | `/v1/cobertura` | — | 39.98 | 24.46 | 26.98 | 39.98 | 200 |

## Con varias consultas a la vez

Cada petición toma su propia conexión del pool, así que la contención de
conexiones y la del motor son reales.

| Hilos | Consultas | Duración (s) | Consultas/s | p50 (ms) | p95 (ms) | máx (ms) | Errores |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 0.138 | 72.5 | 13.51 | 25.55 | 25.55 | 0 |
| 4 | 40 | 0.529 | 75.6 | 39.11 | 116.54 | 124.44 | 0 |
| 16 | 160 | 2.272 | 70.4 | 188.6 | 481.23 | 496.18 | 0 |

## Qué dicen y qué no dicen estos números

La primera repetición se informa aparte porque es la única que se parece a un
servidor recién arrancado: las siguientes encuentran la caché del motor caliente.

La consulta más lenta es «cobertura del release» con 26.98 ms en el percentil 95.

**Esto sigue sin ser una prueba de carga de producción.** Corre en proceso, sin red,
sin balanceador y contra una sola instancia. El número de consultas por segundo es un
techo optimista, no una capacidad comprometida.

### Dónde está el techo

Con la misma concurrencia, el motor sostiene **1270.8 consultas por segundo** y la API se queda en **75.6**. La diferencia dice dónde está el límite: no en la base ni en las conexiones, sino en el proceso que arma y serializa cada respuesta.

Es un dato que cambia qué hacer para escalar. Agrandar el pool o agregar índices no mueve este número; agregar procesos sí. Medirlo antes de optimizar evita gastar el trabajo en el lado que no era.
