# ADR 0008 · Reglas de aplicabilidad y evaluación de los siete campos

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

El sistema tiene que explicar si un beneficio puede corresponder, con qué
condiciones y qué falta averiguar, sin otorgar ni denegar nada. Y tiene que
evaluar los siete campos pedidos por norma y por beneficio, distinguiendo haber
buscado de haber encontrado.

## Decisión

1. **El árbol de reglas es un dato validado, no código.** Operadores cerrados
   (`all`, `any`, `not`, `compare`, `in`, `is_true`), sin `eval`, sin SQL y sin
   código generado. Se valida antes de ejecutarse: una comparación con el
   operador equivocado no falla, devuelve la respuesta contraria.
2. **Una comparación declara su unidad.** Comparar un ingreso contra un número
   sin decir si son pesos mensuales o anuales cambia quién accede al derecho.
   La lista de unidades es cerrada.
3. **Los importes se comparan como decimales.** Evaluar un derecho contra un
   tope con error de coma flotante es inaceptable, y por eso el factor de un
   parámetro viaja como texto.
4. **La lógica es ternaria y `UNKNOWN` no colapsa en `FALSE`.** Un sistema que
   los confunde excluye personas por falta de información. Un dato ausente y un
   "no sé" son lo mismo: falta de información, no una respuesta negativa.
5. **Sin valor vigente de un parámetro, la condición es `UNKNOWN`.** No es que
   la persona no cumpla: es que no sabemos contra qué comparar.
6. **`NO_CUMPLE_REGLA_EXPLICITA` exige haber evaluado todas las excepciones
   aplicables.** Si una excepción quedó sin evaluar, el resultado es
   `REQUIERE_DATOS` o `REQUIERE_REVISION`, nunca una negativa. Y el resultado
   negativo se acompaña siempre de la aclaración de que no es una decisión del
   organismo.
7. **Las salvaguardas nunca excluyen.** Se informan siempre, y con más razón
   cuando el resultado es negativo.
8. **Las causales de revocación, suspensión y cese no deciden el acceso.**
   Detectar una causal potencial no constituye una decisión administrativa.
9. **Evaluar un campo y tener valor sustantivo son cosas distintas.** DQ03 mide
   lo primero, DQ04 lo segundo, y se informan por separado. Un campo en
   `NO_INFORMADO_EN_FUENTES_REVISADAS` deja registro de qué fuentes se
   revisaron y nunca significa que el dato no exista.
10. **La detección de campos propone, no concluye.** Cada candidato apunta al
    fragmento exacto que lo sugiere y nace en estado `CANDIDATE`. Que un
    artículo contenga "caducará" sugiere una causal de cese, no la establece.
    Los patrones son amplios a propósito: es preferible proponer de más y que la
    revisión descarte, a perder una disposición que nadie va a volver a buscar.

## Consecuencias

- Los siete campos quedan evaluados al 100% sobre el corpus cargado y con cero
  valor sustantivo validado. Es el resultado honesto: se buscó en todas las
  fichas y todavía no hay nada aprobado para publicar.
- La cola de revisión de dominio arranca con candidatos localizados y con
  evidencia, no con una lista de normas para leer de cero.
- Las métricas de cobertura se informan separadas. Promediarlas produciría un
  número que suena bien y no significa nada.
