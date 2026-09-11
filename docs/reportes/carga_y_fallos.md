# Carga sostenida y fallos inducidos

20 conversaciones concurrentes durante 30.0 minutos. Cada conversación pide vocabularios, pregunta y busca el canal oficial, que es lo que hace el frente ciudadano.

- Peticiones totales: **56547**
- Modos de respuesta: **596** EXTRACTO, **17074** GENERADA

## Latencia por fase

| Fase | Peticiones | Fallidas | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| antes | 13646 | 0 | 194.8 ms | 865.4 ms | 1064.6 ms |
| durante · Proveedor de modelo caído (503) | 1780 | 0 | 204.9 ms | 892.8 ms | 1146.0 ms |
| después de · Proveedor de modelo caído (503) | 11861 | 0 | 188.0 ms | 875.9 ms | 1049.8 ms |
| durante · Fuente caída (503 transitorio y 403 de acceso limitado) | 933 | 0 | 180.3 ms | 816.4 ms | 937.3 ms |
| después de · Fuente caída (503 transitorio y 403 de acceso limitado) | 12710 | 4 | 191.3 ms | 880.8 ms | 1058.1 ms |
| durante · Base de datos apagada | 3530 | 3530 | 0.0 ms | 0.0 ms | 0.0 ms |
| después de · Base de datos apagada | 12087 | 6 | 185.3 ms | 846.5 ms | 1022.9 ms |

## Qué contestó el servicio en cada fase

| Fase | Códigos HTTP | Modos de respuesta |
| --- | --- | --- |
| antes | 13646×200 | 7×EXTRACTO, 4544×GENERADA |
| durante · Proveedor de modelo caído (503) | 1780×200 | 589×EXTRACTO, 3×GENERADA |
| después de · Proveedor de modelo caído (503) | 11861×200 | 3955×GENERADA |
| durante · Fuente caída (503 transitorio y 403 de acceso limitado) | 933×200 | 310×GENERADA |
| después de · Fuente caída (503 transitorio y 403 de acceso limitado) | 12706×200, 4×503 | 4235×GENERADA |
| durante · Base de datos apagada | 3525×503, 5×sin respuesta | — |
| después de · Base de datos apagada | 12081×200, 6×503 | 4027×GENERADA |

Un código importa tanto como una latencia. Con la base apagada el servicio contesta **503 con cuerpo tipado** y `Retry-After`, no 500: un 500 dice «esta petición salió mal» y un balanceador la vuelve a mandar a la misma instancia; un 503 dice «esta instancia no puede ahora». Y con el proveedor de modelo caído no hay error ninguno: la respuesta repliega a extracto, que es texto publicado y citado.

## Fallos inducidos

| Fallo | Se indujo | Recuperación | Hizo falta reiniciar |
| --- | --- | ---: | --- |
| Proveedor de modelo caído (503) | sí | no aplica | no |
| Fuente caída (503 transitorio y 403 de acceso limitado) | sí | no aplica | no |
| Base de datos apagada | sí | 0.2 s | no |

## Límites

Límite configurado: **120** consultas por minuto y por origen. Cada conversación llega con su propio origen, como llegaría detrás de un balanceador; además corre un origen abusivo que pide sin parar.

- Al origen abusivo se le rechazaron **14031** peticiones y se le sirvieron 3596.
- A las conversaciones legítimas se les rechazaron **0**.

Lo que importa no es que el abusivo reciba 429: es que los demás sigan siendo atendidos mientras lo recibe. Un límite que protege al servicio y deja afuera a todo el mundo no protege a nadie.

## Exposición de datos pendientes

Ninguna. Se revisó **cada** cuerpo de respuesta —de éxito y de error— buscando estados de trabajo, nombres internos y fragmentos que no pertenezcan al corte publicado.

## Lo que este ensayo no prueba

- Fuente caída, con el cliente de ingesta de verdad: 503 transitorio: 3 intento(s), error `HTTP 503`, acceso limitado = False. No quedó como «sin datos». · 403: acceso limitado = True, error `HTTP 403`. Se registra como acceso limitado y pausa la fuente; no se reintenta ni se rota identidad. · Repuesta la fuente: HTTP 200, 51 bytes. La ingesta vuelve sola.
- El proveedor de modelo es local y contesta al instante: lo que este ensayo mide de él es el camino de fallo y el repliegue a extracto, no la latencia de un modelo real.
- La carga se genera desde la misma máquina que sirve y que hospeda la base. Los números de latencia incluyen esa contención y no son los de un despliegue con instancias separadas.
