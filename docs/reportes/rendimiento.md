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
| `evidencias` | 7,443 |
| `registro_versiones` | 7,812 |
| `puntos_atencion` | 290 |
| `canales` | 1,012 |
| `barrios_renabap` | 6,467 |

## Latencias

| Consulta | Ruta | Filas | 1ª (ms) | p50 (ms) | p95 (ms) | máx (ms) | HTTP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normas: listado | `/v1/normas` | 20 | 32.13 | 21.18 | 22.69 | 32.13 | 200 |
| normas: búsqueda por texto | `/v1/normas` | 20 | 20.34 | 18.34 | 20.34 | 20.35 | 200 |
| normas: búsqueda por tipo y año | `/v1/normas` | 50 | 19.23 | 19.28 | 21.8 | 22.33 | 200 |
| beneficios | `/v1/beneficios` | 4 | 20.19 | 6.57 | 7.06 | 20.19 | 200 |
| puntos de atención | `/v1/puntos-atencion` | 0 | 8.91 | 6.66 | 7.12 | 8.91 | 200 |
| puntos por jurisdicción | `/v1/puntos-atencion` | 0 | 6.55 | 5.55 | 6.55 | 6.64 | 200 |
| puntos por alcance municipal | `/v1/puntos-atencion` | 0 | 7.07 | 7.05 | 7.9 | 8.08 | 200 |
| barrios RENABAP por nombre | `/v1/barrios-renabap` | 100 | 12.78 | 9.64 | 10.5 | 12.78 | 200 |
| cobertura del release | `/v1/cobertura` | — | 40.14 | 25.34 | 27.87 | 40.14 | 200 |

## Con varias consultas a la vez

Cada petición toma su propia conexión del pool, así que la contención de
conexiones y la del motor son reales.

| Hilos | Consultas | Duración (s) | Consultas/s | p50 (ms) | p95 (ms) | máx (ms) | Errores |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 0.143 | 69.9 | 14.55 | 26.68 | 26.68 | 0 |
| 4 | 40 | 0.564 | 70.9 | 41.1 | 136.53 | 140.46 | 0 |
| 16 | 160 | 2.225 | 71.9 | 145.33 | 472.09 | 510.79 | 0 |

## Qué dicen y qué no dicen estos números

La primera repetición se informa aparte porque es la única que se parece a un
servidor recién arrancado: las siguientes encuentran la caché del motor caliente.

La consulta más lenta es «cobertura del release» con 27.87 ms en el percentil 95.

**Esto sigue sin ser una prueba de carga de producción.** Corre en proceso, sin red,
sin balanceador y contra una sola instancia. El número de consultas por segundo es un
techo optimista, no una capacidad comprometida.

### Dónde está el techo

Con la misma concurrencia, el motor sostiene **1049.5 consultas por segundo** y la API se queda en **71.9**. La diferencia dice dónde está el límite: no en la base ni en las conexiones, sino en el proceso que arma y serializa cada respuesta.

Es un dato que cambia qué hacer para escalar. Agrandar el pool o agregar índices no mueve este número; agregar procesos sí. Medirlo antes de optimizar evita gastar el trabajo en el lado que no era.
