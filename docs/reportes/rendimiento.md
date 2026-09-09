# Rendimiento de las consultas sobre el corpus real

Una latencia sin decir sobre cuántas filas se midió no significa nada, así que el
tamaño del corpus va primero.

- Tamaño de la base: **314 MB**
- Repeticiones por consulta: **12**

| Tabla | Filas |
| --- | ---: |
| `normas` | 423,718 |
| `norma_versiones` | 54 |
| `unidades_documentales` | 1,921 |
| `evidencias` | 8,930 |
| `registro_versiones` | 11,832 |
| `puntos_atencion` | 290 |
| `canales` | 4,048 |
| `barrios_renabap` | 6,467 |

## Latencias

| Consulta | Ruta | Filas | 1ª (ms) | p50 (ms) | p95 (ms) | máx (ms) | HTTP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normas: listado | `/v1/normas` | 20 | 31.26 | 19.24 | 21.33 | 31.26 | 200 |
| normas: búsqueda por texto | `/v1/normas` | 20 | 19.07 | 19.01 | 20.18 | 20.76 | 200 |
| normas: búsqueda por tipo y año | `/v1/normas` | 50 | 20.87 | 19.32 | 20.87 | 21.33 | 200 |
| beneficios | `/v1/beneficios` | 16 | 21.02 | 6.9 | 8.08 | 21.02 | 200 |
| puntos de atención | `/v1/puntos-atencion` | 0 | 8.45 | 6.61 | 7.21 | 8.45 | 200 |
| puntos por jurisdicción | `/v1/puntos-atencion` | 0 | 5.46 | 6.34 | 6.81 | 7.26 | 200 |
| puntos por alcance municipal | `/v1/puntos-atencion` | 0 | 6.96 | 6.76 | 7.79 | 7.79 | 200 |
| barrios RENABAP por nombre | `/v1/barrios-renabap` | 100 | 14.37 | 9.89 | 11.89 | 14.37 | 200 |
| cobertura del release | `/v1/cobertura` | — | 43.27 | 27.24 | 28.62 | 43.27 | 200 |

## Con varias consultas a la vez

Cada petición toma su propia conexión del pool, así que la contención de
conexiones y la del motor son reales.

| Hilos | Consultas | Duración (s) | Consultas/s | p50 (ms) | p95 (ms) | máx (ms) | Errores |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 0.134 | 74.6 | 13.68 | 24.26 | 24.26 | 0 |
| 4 | 40 | 0.553 | 72.3 | 40.7 | 128.98 | 132.77 | 0 |
| 16 | 160 | 2.215 | 72.2 | 182.4 | 480.31 | 497.38 | 0 |

## Qué dicen y qué no dicen estos números

La primera repetición se informa aparte porque es la única que se parece a un
servidor recién arrancado: las siguientes encuentran la caché del motor caliente.

La consulta más lenta es «cobertura del release» con 28.62 ms en el percentil 95.

**Esto sigue sin ser una prueba de carga de producción.** Corre en proceso, sin red,
sin balanceador y contra una sola instancia. El número de consultas por segundo es un
techo optimista, no una capacidad comprometida.

### Dónde está el techo

Con la misma concurrencia, el motor sostiene **1217.9 consultas por segundo** y la API se queda en **74.6**. La diferencia dice dónde está el límite: no en la base ni en las conexiones, sino en el proceso que arma y serializa cada respuesta.

Es un dato que cambia qué hacer para escalar. Agrandar el pool o agregar índices no mueve este número; agregar procesos sí. Medirlo antes de optimizar evita gastar el trabajo en el lado que no era.
