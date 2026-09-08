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
| `evidencias` | 7,495 |
| `registro_versiones` | 7,888 |
| `puntos_atencion` | 311 |
| `canales` | 1,077 |
| `barrios_renabap` | 6,467 |

## Latencias

| Consulta | Ruta | Filas | 1ª (ms) | p50 (ms) | p95 (ms) | máx (ms) | HTTP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normas: listado | `/v1/normas` | 20 | 33.19 | 21.43 | 22.32 | 33.19 | 200 |
| normas: búsqueda por texto | `/v1/normas` | 20 | 20.97 | 19.96 | 20.97 | 21.13 | 200 |
| normas: búsqueda por tipo y año | `/v1/normas` | 50 | 21.0 | 21.47 | 22.3 | 24.85 | 200 |
| beneficios | `/v1/beneficios` | 1 | 17.61 | 6.71 | 7.36 | 17.61 | 200 |
| puntos de atención | `/v1/puntos-atencion` | 0 | 8.82 | 7.05 | 7.47 | 8.82 | 200 |
| puntos por jurisdicción | `/v1/puntos-atencion` | 0 | 7.76 | 6.03 | 7.26 | 7.76 | 200 |
| puntos por alcance municipal | `/v1/puntos-atencion` | 0 | 7.05 | 7.18 | 7.73 | 8.02 | 200 |
| barrios RENABAP por nombre | `/v1/barrios-renabap` | 100 | 11.64 | 9.92 | 10.81 | 11.64 | 200 |
| cobertura del release | `/v1/cobertura` | — | 43.78 | 26.62 | 29.82 | 43.78 | 200 |

## Qué dicen y qué no dicen estos números

La primera repetición se informa aparte porque es la única que se parece a un
servidor recién arrancado: las siguientes encuentran la caché del motor caliente.

La consulta más lenta es «cobertura del release» con 29.82 ms en el percentil 95.

**Esto no es una prueba de carga.** Las consultas se ejecutan una después de otra,
sobre la misma conexión y sin latencia de red. No dice cuántas consultas por segundo
resiste el sistema ni qué pasa cuando varias personas preguntan a la vez: eso necesita
un entorno con el despliegue real y generadores de carga, y hasta tenerlo lo honesto
es no afirmar un número de concurrencia.
