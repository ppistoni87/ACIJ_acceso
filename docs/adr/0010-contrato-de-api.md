# ADR 0010 · Contrato de la API

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

El consumidor de esta API es un sistema conversacional que le va a hablar a una
persona sobre sus derechos. Lo que no viaje en la respuesta es información que
ese sistema no va a poder decir, y lo que viaje sin contexto se va a afirmar con
más seguridad de la que corresponde.

## Decisión

1. **Toda respuesta lleva la misma envoltura**: `schema_version`, `release_id`,
   `as_of`, `known_at`, `data_status`, `evidence`, `missing_fields` y
   `warnings`. No es ceremonia: sin `as_of` una respuesta no dice para cuándo
   vale, sin `release_id` no se puede reproducir, y sin `missing_fields` una
   abstención sería indistinguible de un "no".
2. **Una consulta se resuelve entera contra un release.** Mezclar dos sería
   servir una respuesta que ningún corte del corpus sostiene.
3. **Los errores son tipados y la información insuficiente no es un 500.**
   `INSUFFICIENT_EVIDENCE`, `STALE_DATA`, `CONFLICT`, `UNKNOWN_IDENTITY` y
   `UNSUPPORTED_SCOPE` son estados de dominio. El 500 queda para fallos reales
   del servicio y no revela detalles internos.
4. **La abstención se explica.** Cada versión declara si puede servirse para la
   capacidad consultada y, si no, por qué, con los motivos que devuelve
   `bn_motivos_no_servible`.
5. **Un candidato en revisión se cuenta pero no se sirve como valor.** Es lo que
   distingue "lo estamos mirando" de "esto dice la norma".
6. **La recuperación no toca staging** y sus fragmentos son para explicar y
   citar. Los montos, las fechas y los datos de contacto se consultan con las
   operaciones tipadas, no combinando fragmentos.
7. **Un valor de parámetro se busca por la fecha consultada, nunca por fecha
   máxima.** Servir el monto de otro período es la forma más directa de dar una
   respuesta incorrecta que parece correcta.
8. **El listado de beneficios no infiere elegibilidad** y lo dice en cada
   respuesta: pertenecer a una población no implica tener derecho.
9. **La evaluación preliminar no persiste el cuerpo de la solicitud.** Los
   hechos que declara una persona sobre su edad, sus ingresos o su hogar no
   forman parte del corpus normativo.
10. **La administración exige credencial y actor declarado.** Sin la variable de
    entorno configurada las rutas están cerradas: no hay credencial por defecto
    ni modo de desarrollo que las abra. El actor queda en la bitácora.
11. **Resolver una incidencia ya resuelta devuelve 409**, con concurrencia
    optimista sobre el estado esperado.
12. **Publicar sin pasar los gates devuelve 422 con los controles que fallaron**,
    no un error de servidor.

## Consecuencias

- El contrato OpenAPI se versiona en `docs/openapi.json` y se regenera con
  `bn api openapi`.
- La API lee con el rol `lector_api`, que no ve staging. Las rutas de
  administración usan otro motor y escriben solo a través de los módulos de
  revisión y publicación, nunca con SQL propio.
- Verificado contra el corpus real: la búsqueda devuelve las ocho normas con su
  cobertura por campo, y la recuperación devuelve fragmentos citables de la
  única norma publicada, con su unidad y su URL de origen.
