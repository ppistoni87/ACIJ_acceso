# ADR 0011 · Monitoreo, impacto y entrega de eventos

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

Un corpus normativo se desactualiza solo. El monitoreo tiene que detectar
cambios, entender a qué alcanzan y avisar, sin inventar certezas ni generar
ruido que nadie va a mirar.

## Decisión

1. **El diff compara unidades, no páginas.** Un hash distinto dice que algo
   cambió, no qué. Comparar por unidad permite decir qué artículo se modificó,
   cuál se agregó y cuál desapareció.
2. **Solo se comparan unidades dispositivas.** Un cambio de maquetación o de
   nota editorial no es un cambio en la norma, y tratarlo como tal llenaría de
   ruido la cola de revisión.
3. **El mismo hash no prueba que nada haya cambiado.** Una norma modificatoria
   publicada en otro boletín afecta a la modificada aunque su página no se
   toque. La corrida lo dice explícitamente en vez de reportar "sin novedades".
4. **El impacto se propaga.** Un cambio alcanza a las normas que citan a la
   modificada, a los beneficios que se apoyan en ella y a las reglas que
   dependen de sus artículos. Las versiones alcanzadas vencen su frescura:
   seguir sirviéndolas como frescas sería servir un dato vencido.
5. **Crear un evento no es entregarlo.** `entregado_en` solo se completa cuando
   un consumidor responde. Sin consumidor configurado, los eventos se acumulan y
   el reporte lo dice: no se declara una entrega que no ocurrió.
6. **La entrega es al menos una vez.** La clave de idempotencia viaja en una
   cabecera para que el consumidor descarte duplicados.
7. **Un evento que agotó los intentos pasa a una cola de fallos** y deja de
   reintentarse solo: es trabajo de operación, no ruido en cada corrida.
8. **Web Push ciudadano no está supuesto.** Lo que hay es un outbox y un
   consumidor configurable por variable de entorno.

## Consecuencias

- Reejecutar el monitoreo es seguro: la propagación es idempotente por clave y
  la revalidación no transfiere bytes cuando el recurso no cambió.
- Una corrida sin novedades no cierra el tema, y el reporte lo aclara. Es
  deliberado: la alternativa es un "todo al día" que no se puede sostener.
