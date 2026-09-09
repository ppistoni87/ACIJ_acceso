# Escalado por procesos: ¿el caudal se multiplica?

La medición anterior golpeaba la API desde hilos dentro del mismo proceso de
prueba. Eso dice dónde está el techo de un proceso y no si ese techo se
multiplica, que es lo que hay que saber antes de decidir cómo se despliega.

Acá la API corre en varios procesos de verdad, que comparten el socket de
escucha —el reparto lo hace el núcleo—, y la carga la genera otro proceso. La
base es la misma PostgreSQL, con su pool y su contención reales.

Generado por `bn calidad escalado` sobre una máquina de **4 CPU**.
Pool por proceso: **30** conexiones · máximo de la base: **100**.

| Procesos | Clientes | Peticiones | Errores | Caudal (pet/s) | p95 | CPU |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 16 | 1047 | 0 | **172.7** | 198.13 ms | 92.8% |
| 2 | 16 | 1137 | 0 | **187.6** | 203.02 ms | 98.6% |
| 4 | 16 | 1160 | 0 | **191.2** | 191.43 ms | 99.1% |

## Hasta dónde aguanta, con 4 procesos

Se repite la medición subiendo la concurrencia de clientes. Si el caudal sube al
agregar clientes, el que estaba saturado era el generador de carga y no la API.
Si deja de subir y la demora crece, la API está en su techo. Si además aparecen
errores, el techo no es un techo: es un derrumbe.

| Clientes | Peticiones | Errores | Caudal (pet/s) | p95 | CPU |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 900 | 0 | **149.7** | 56.83 ms | 91.6% |
| 32 | 1129 | 0 | **184.4** | 378.38 ms | 98.9% |
| 64 | 1070 | 0 | **171.0** | 810.05 ms | 98.5% |

## Qué dice

- El caudal máximo medido es 191.2 peticiones por segundo, con 4 proceso(s) y 16 clientes, y ahí la máquina usa el 99.1% de su CPU.
- Con 2 procesos el caudal se multiplica por 1.09 y no por 2, y con 92.8% de CPU ya ocupada por un solo proceso. No queda máquina para repartir: acá la API, la base y el generador de carga comparten los mismos núcleos, así que esto **no** dice que el sistema no escale. Dice que esta máquina no tiene con qué mostrarlo, y que la pregunta sigue necesitando instancias en máquinas separadas.
- Con 4 procesos el caudal se multiplica por 1.11 y no por 4, y con 92.8% de CPU ya ocupada por un solo proceso. No queda máquina para repartir: acá la API, la base y el generador de carga comparten los mismos núcleos, así que esto **no** dice que el sistema no escale. Dice que esta máquina no tiene con qué mostrarlo, y que la pregunta sigue necesitando instancias en máquinas separadas.
- Subir la concurrencia de clientes no sube el caudal y sí la demora (4 clientes → 56.83 ms, 32 clientes → 378.38 ms, 64 clientes → 810.05 ms): el sistema está saturado y encola en vez de rechazar. Una petición que expira consume igual y no devuelve nada, así que un despliegue tiene que poner el límite antes.
- Cada proceso puede abrir hasta 30 conexiones y la base admite 100 en total: con 4 procesos el despliegue puede pedir 120, que es más de lo que hay. Bajo carga las que sobran no esperan: la base las rechaza y la petición se cae. Es una cuenta que hay que hacer antes de agregar instancias, no después.

## Qué no dice

La red es loopback y todo comparte la misma máquina: la API, PostgreSQL y el
generador de carga se pelean por los mismos núcleos. Cuando la CPU llega al
tope, esta medición deja de poder distinguir el costo de la API del de la base
del generador, y ahí la pregunta de si el caudal se multiplica al agregar
instancias solo la contesta un despliegue con máquinas separadas.

Lo que sí queda medido, y no dependía de eso, es todo lo demás: dónde está el
techo de esta máquina, qué le pasa al sistema cuando lo empujan más allá —encola
y la demora crece, en vez de rechazar—, y que el pool de cada proceso por la
cantidad de procesos puede pedirle a la base más conexiones de las que admite,
que es una cuenta que hay que hacer antes de agregar instancias y no después.
