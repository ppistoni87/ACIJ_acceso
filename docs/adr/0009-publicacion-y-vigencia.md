# ADR 0009 · Resolución de vigencia, revisión y publicación

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

Nada del corpus puede servirse hasta que su vigencia esté resuelta, y resolver
la vigencia de una norma es una decisión jurídica. Al mismo tiempo, exigir
revisión humana para todo haría el sistema inoperable. La especificación resuelve
la tensión permitiendo publicación automática solo con una política versionada
que identifique campos, autoridad, evidencia y pruebas exigidas.

## Decisión

1. **La política de vigencia vive en el repositorio y se versiona con git**
   (`politicas/vigencia.py`, identificador `vigencia-declarada@1`). Su
   identificador queda en la bitácora de cada hecho que habilitó.
2. **La política cubre un solo caso**: la fuente oficial declara explícitamente
   la norma vigente, esa declaración tiene evidencia registrada, se conoce la
   fecha de inicio y no hay relaciones aprobadas que cierren la vigencia. Todo
   lo demás va a la cola de revisión con su fundamento.
3. **Lo que la política no habilita**, y está escrito en ella: concluir que una
   norma sigue vigente porque nadie registró su derogación; cerrar la vigencia
   por una etiqueta "no vigente", porque la norma pudo incorporar disposiciones
   que siguen aplicándose a través de la que modificó; e interpretar una nota
   editorial que dice a la vez que una norma fue abrogada y que su vigencia fue
   restablecida.
4. **Una decisión de revisión exige actor, decisión y fundamento.** Sin la
   evidencia que lo respalda no se afirma un estado de vigencia. La resolución
   no borra el conflicto: lo cierra dejando quién decidió y cuándo, y queda en
   la bitácora append-only.
5. **Resolver dos veces la misma incidencia falla por conflicto de versión.** Es
   el 409 del contrato de API: alguien más ya la movió.
6. **Publicar es atómico.** El release, el cambio de estado de las versiones, los
   fragmentos citables y el evento ocurren en la misma transacción. Una consulta
   nunca puede mezclar dos releases incompatibles porque nunca existe un estado
   intermedio visible.
7. **Solo se indexa texto dispositivo.** Recuperar una nota editorial o un
   artículo transcripto dentro de otro como si fueran la norma haría que una
   respuesta cite algo que la norma no dice.
8. **La cuarentena dice por qué no se publica cada cosa.** Sin esa lista, "no
   aparece en la respuesta" y "no existe" serían indistinguibles.
9. **Crear un evento no es entregarlo.** `entregado_en` solo se completa cuando
   un consumidor confirma: no se afirma haber enviado un mensaje que nadie
   recibió.
10. **Revertir no borra.** Las versiones vuelven a estado aprobado, el release
    queda marcado como revertido y los fragmentos se conservan.
11. **Cada control de calidad queda atado a la versión que evaluó.** Un control
    suelto no permitiría decir después bajo qué controles se publicó una versión.

## Consecuencias

- Sobre el corpus cargado, las nueve versiones quedaron derivadas a revisión: en
  ninguna la fuente declara el estado de vigencia. Es el resultado correcto, y
  es también el trabajo que hay por delante.
- Publicar exige pasar por la cola de revisión. No hay atajo, y eso es deliberado.
- La publicación por capacidad funciona como pide la especificación: la Ley CABA
  6935/2025 revisada sirve identificación, descripción, requisitos, monto, canal
  y explicación histórica, y se abstiene en plazo y evaluación preliminar porque
  esos campos no tienen valor respaldado.
