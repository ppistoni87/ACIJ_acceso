# Acta: el circuito de revisión de reglas

Evidencia de P-009, criterios 1 a 3. Registra lo verificado el 10 de septiembre
de 2026.

## Lo que faltaba

Las transiciones de una regla —marcar en revisión, aprobar, rechazar— existían
como funciones de la CLI desde HU-036. Lo que no existía era el circuito: una
persona no puede revisar 166 reglas candidatas desde una terminal, y lo que se
decide desde una terminal no deja ver qué vio quien decidió.

Faltaban tres cosas, una por criterio.

## Criterio 1: todo a la vista, junto

`GET /v1/admin/reglas/{id}` devuelve el expediente completo: **literal,
interpretación, condición (el AST), dependencias, parámetros, vigencia y
controles**.

Juntos y no en seis pantallas. Una condición se aprueba o no según de qué
depende y sobre qué versión rige; pedirle a quien revisa que cruce seis
pantallas es pedirle que no las cruce. El expediente reusa la consulta del
listado en vez de escribir otra: dos consultas que tienen que decir lo mismo
terminan diciendo cosas distintas.

`POST /v1/admin/reglas/{id}/decidir` exige **actor autenticado y fundamento**.
Sin fundamento no se decide —dentro de seis meses nadie puede saber si se revisó
o se aprobó de apuro— y las dos cosas quedan en la bitácora con nombre.

## Criterio 2: quien decidió primero no se sobrescribe

Las transiciones ya rechazaban un salto de estado imposible, pero con un error
que parece del que lo intenta cuando en realidad **alguien ya decidió**. Ahora
quien decide declara en qué estado leyó la regla (`estado_esperado`), y si no
coincide recibe **409 `VERSION_CONFLICT`** con lo que pasó, no un error de
transición.

Probado: dos personas abren la misma regla candidata, la primera aprueba, la
segunda rechaza. La segunda recibe 409 y **la regla sigue aprobada**.

## Criterio 3: aprobar no es publicar

La respuesta de una aprobación dice `"publicada": false`, y no es cosmética: una
regla aprobada no se sirve hasta pasar el corte de release, que es otra puerta
con su propio control y la abre otra persona. Por eso `PUBLICAR` no está entre
las decisiones que este endpoint acepta, y pedirla devuelve 400 con la lista de
las que sí.

## Lo que este acta no acredita

- **Las 166 reglas candidatas siguen candidatas.** El circuito está; decidirlas
  es P-010 y el plan lo dice explícitamente: «no se aprueban en lote por un
  agente». No firmé ninguna.
- **No hay backoffice.** Hay API. La pantalla es P-016.
- **La autenticación es por token de administración.** Identidad OIDC por
  persona es P-017; hoy el actor viaja declarado en una cabecera y el token solo
  dice que quien llama tiene permiso de administrar.
- **La concurrencia se probó de a dos llamadas seguidas**, que es lo que el
  criterio describe. Dos transacciones realmente simultáneas sobre la misma fila
  las serializa PostgreSQL, y esa es otra prueba.
