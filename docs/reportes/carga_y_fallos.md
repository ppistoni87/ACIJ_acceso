# Carga sostenida y fallos inducidos

20 conversaciones concurrentes durante 30.0 minutos. Cada conversación pide vocabularios, pregunta y busca el canal oficial, que es lo que hace el frente ciudadano.

- Peticiones totales: **55473**
- Modos de respuesta: **604** EXTRACTO, **16709** GENERADA

## Latencia por fase

| Fase | Peticiones | 5xx | Sin respuesta | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| antes | 13579 | 0 | 0 | 194.4 ms | 877.8 ms | 1082.5 ms |
| durante · Proveedor de modelo caído (503) | 1812 | 0 | 0 | 191.6 ms | 880.3 ms | 1102.4 ms |
| después de · Proveedor de modelo caído (503) | 11727 | 0 | 0 | 195.2 ms | 892.3 ms | 1077.2 ms |
| durante · Fuente caída (503 transitorio y 403 de acceso limitado) | 923 | 0 | 0 | 178.7 ms | 848.2 ms | 998.4 ms |
| después de · Fuente caída (503 transitorio y 403 de acceso limitado) | 12620 | 4 | 0 | 196.8 ms | 891.1 ms | 1077.2 ms |
| durante · Base de datos apagada | 3520 | 3519 | 1 | 5.3 ms | 12.3 ms | 26.7 ms |
| después de · Base de datos apagada | 11292 | 6 | 0 | 207.6 ms | 978.5 ms | 1280.7 ms |

## Qué contestó el servicio en cada fase

| Fase | Códigos HTTP | Modos de respuesta |
| --- | --- | --- |
| antes | 13579×200 | 6×EXTRACTO, 4522×GENERADA |
| durante · Proveedor de modelo caído (503) | 1812×200 | 598×EXTRACTO, 6×GENERADA |
| después de · Proveedor de modelo caído (503) | 11727×200 | 3909×GENERADA |
| durante · Fuente caída (503 transitorio y 403 de acceso limitado) | 923×200 | 309×GENERADA |
| después de · Fuente caída (503 transitorio y 403 de acceso limitado) | 12616×200, 4×503 | 4201×GENERADA |
| durante · Base de datos apagada | 3519×503, 1×sin respuesta | — |
| después de · Base de datos apagada | 11286×200, 6×503 | 3762×GENERADA |

Un código importa tanto como una latencia. Con la base apagada el servicio contesta **503 con cuerpo tipado** y `Retry-After`, no 500: un 500 dice «esta petición salió mal» y un balanceador la vuelve a mandar a la misma instancia; un 503 dice «esta instancia no puede ahora». Y con el proveedor de modelo caído no hay error ninguno: la respuesta repliega a extracto, que es texto publicado y citado.

Las pocas respuestas generadas que aparecen dentro de la ventana del proveedor caído son las que ya estaban en vuelo cuando se lo rompió: se pidieron antes y se contestaron después. No son un repliegue que no ocurrió.

## Fallos inducidos

| Fallo | Se indujo | Recuperación | Hizo falta reiniciar |
| --- | --- | ---: | --- |
| Proveedor de modelo caído (503) | sí | no aplica | no |
| Fuente caída (503 transitorio y 403 de acceso limitado) | sí | no aplica | no |
| Base de datos apagada | sí | 0.4 s | no |

## Límites

Límite configurado: **120** consultas por minuto y por origen. Cada conversación llega con su propio origen, como llegaría detrás de un balanceador; además corre un origen abusivo que pide sin parar.

- Al origen abusivo se le rechazaron **13536** peticiones y se le sirvieron 3597.
- A las conversaciones legítimas se les rechazaron **0**.

Lo que importa no es que el abusivo reciba 429: es que los demás sigan siendo atendidos mientras lo recibe. Un límite que protege al servicio y deja afuera a todo el mundo no protege a nadie.

## Exposición de datos pendientes

Ninguna. Se revisó **cada** cuerpo de respuesta —de éxito y de error— buscando estados de trabajo, nombres internos y fragmentos que no pertenezcan al corte publicado.

## Lo que este ensayo no prueba

- Fuente caída, con el cliente de ingesta de verdad: 503 transitorio: 3 intento(s), error `HTTP 503`, acceso limitado = False. No quedó como «sin datos». · 403: acceso limitado = True, error `HTTP 403`. Se registra como acceso limitado y pausa la fuente; no se reintenta ni se rota identidad. · Repuesta la fuente: HTTP 200, 51 bytes. La ingesta vuelve sola.
- El proveedor de modelo es local y contesta al instante: lo que este ensayo mide de él es el camino de fallo y el repliegue a extracto, no la latencia de un modelo real.
- La carga se genera desde la misma máquina que sirve y que hospeda la base. Los números de latencia incluyen esa contención y no son los de un despliegue con instancias separadas.
