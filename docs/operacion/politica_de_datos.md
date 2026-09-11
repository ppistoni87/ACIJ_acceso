# Política de datos y retención

P-017, criterios 2 y 3. Esto describe lo que el sistema **hace**, no lo que se
pretende que haga: cada afirmación tiene el archivo donde está implementada y la
prueba que la verifica.

## Qué se le pide a quien consulta

Nada obligatorio más que la pregunta.

| Dato | ¿Se pide? | Dónde |
| --- | --- | --- |
| Pregunta | Sí, es la consulta | `POST /v1/respuestas` |
| Situación personal («hechos mínimos») | Opcional, texto libre | campo `#hechos` del frente |
| Jurisdicción, fecha, tipo de beneficio | Opcional, de una lista | selectores del frente |
| DNI, CUIL | **No existe el campo** | verificado en `test_frente_ciudadano.py` |
| Nombre, domicilio, teléfono, correo | **No existe el campo** | ídem |
| Datos de menores | **No existe el campo** | ídem |

El frente lo dice en la pantalla, no sólo acá: «no hace falta que pongas tu
nombre, tu documento ni datos de contacto».

No hay cuenta, no hay sesión y no hay credencial del lado ciudadano. Como no hay
sesión, no hay cookie de sesión que robar ni petición autenticada que falsificar:
**CSRF no aplica** a este frente. No es que esté mitigado; es que no hay
mecanismo que atacar. Si algún día hay sesión ciudadana, esta línea deja de ser
cierta y hay que volver acá.

## Qué se guarda de una consulta

Una fila en `consultas_auditadas`, con la **forma** de la consulta y no su
contenido (`src/backend_normativo/api/observabilidad.py`):

| Se guarda | No se guarda |
| --- | --- |
| `request_id` de correlación | El texto de la pregunta |
| Ruta pedida (`/v1/respuestas`) | Los hechos que la persona escribió |
| Corte publicado que la respondió | Dirección IP |
| Resultado: resuelta o abstenida, y la causa tipada | Cualquier identificador de persona |
| Latencia en milisegundos | Cabeceras de la petición |
| Cuántas evidencias se usaron | Texto de las fuentes servidas |

La causa de abstención se guarda como código tipado —`INSUFFICIENT_EVIDENCE`,
`SIN_EVIDENCIA`— y nunca en prosa: el detalle en prosa puede nombrar lo que la
persona preguntó.

La tabla no tiene ninguna columna de identidad. Está verificado por una prueba
que falla si alguien agrega una.

## Qué se guarda en el navegador

Nada. El frente no escribe en `localStorage` ni en `sessionStorage`, y «Salir y
borrar» vacía los campos, la respuesta en pantalla y cualquier cosa que haya
quedado en el almacenamiento del navegador. Una pantalla compartida —un locutorio,
la computadora de una oficina de atención— es el caso normal, no el raro.

Verificado en `tests/aceptacion/test_recorrido_ciudadano.py`.

## Cuánto tiempo se guarda

**90 días**, configurable con `BN_RETENCION_CONSULTAS_DIAS`.

```bash
bn operacion purgar-consultas --simular   # cuenta y no borra
bn operacion purgar-consultas             # aplica la retención
```

Se borra aunque la fila no identifique a nadie. Dos razones: un registro que no
caduca crece para siempre y termina respaldado, replicado y consultado por gente
que no sabe qué está mirando; y «no identifica a nadie» es una afirmación sobre
hoy —un conjunto grande de formas de consulta, con sus horarios y sus
jurisdicciones, se vuelve más identificante cuanto más largo es—.

Poner la variable en 0 o en un valor ilegible **no** borra todo: se toma el
mínimo de 1 día. Para no guardar nada hay que no registrar, que es otra decisión
y se toma en otro lado.

El purgado corre con el rol de administración. El lector de la API puede
insertar su traza y no puede borrar la de nadie: esa separación es lo que hace
que el registro sirva como registro.

## Límites de uso

`src/backend_normativo/api/limites.py`. Dos baldes de fichas por origen:

| Límite | Valor por omisión | Variable |
| --- | ---: | --- |
| Consultas por minuto | 120 | `BN_LIMITE_CONSULTAS_POR_MINUTO` |
| Credenciales administrativas fallidas (por 5 min) | 10 | `BN_LIMITE_AUTENTICACIONES_FALLIDAS` |

Al alcanzarlos se contesta **429** con cuerpo tipado (`RATE_LIMITED`) y
`Retry-After`. El 429 queda medido como cualquier otra respuesta: un límite que
frena sin dejar rastro no se puede ajustar, porque no hay forma de saber si está
frenando abuso o gente.

Tres advertencias que no se pueden omitir al desplegar:

1. **El límite es por proceso.** El balde vive en memoria y no se comparte. Con
   cuatro instancias el límite efectivo es cuatro veces el configurado.
2. **`X-Forwarded-For` no se cree por omisión.** Esa cabecera la pone quien
   llama. Se usa sólo si el despliegue declara cuántos proxies propios hay
   delante (`BN_PROXIES_CONFIABLES`), y se lee el salto que corresponde a ese
   número, no el primero de la lista.
3. **Un origen puede ser mucha gente.** Una oficina entera detrás de una misma
   salida a internet comparte balde. El número por omisión está elegido para que
   eso no moleste; si se baja, hay que pensar en ese caso antes.

La clave del balde es un hash con sal aleatoria del proceso. Sirve para contar,
no para saber de quién, y la sal muere con el proceso.

## Secretos

Ninguno viaja al frente. El frente ciudadano no lleva credenciales; la consola
de revisión pide la credencial a quien entra y vive en su pestaña, y el servidor
no la guarda ni la conoce hasta que llega en un pedido.

La configuración operativa se lee del entorno. `.env.example` documenta las
variables sin valores reales.

## Inyección de contenido

El texto del corpus se muestra **como texto**: se escapa antes de entrar al DOM.
Un fragmento con `<img onerror=…>` no ejecuta nada, y uno que diga «ignorá las
instrucciones anteriores» se lee como lo que es, una cadena de caracteres
publicada por un organismo. Verificado con un caso que inyecta las dos cosas.

Los enlaces de las fuentes se filtran por esquema: sólo `http` y `https`. Un
`javascript:` guardado en la base no se convierte en un enlace ejecutable por
pasar por la pantalla.

## Lo que esta política no cubre

* **Proveedor de identidad (OIDC)** para el acceso administrativo. Hoy la
  identidad administrativa es una credencial firmada por persona, con roles,
  vencimiento y revocación —criterio 1 de P-017, cerrado—, pero no hay
  federación con un proveedor.
* **Retención de conversación**, en el sentido de un historial por persona: no
  existe, porque no hay conversación persistida. Si alguna vez la hay, esta
  política necesita una sección nueva y no un párrafo agregado.
* **Un modelo de amenazas acotado** escrito como tal. La evidencia de P-017 lo
  pide y todavía no está.
