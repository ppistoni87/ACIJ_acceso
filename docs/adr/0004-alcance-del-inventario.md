# ADR 0004 · Alcance del inventario y derivación de vocabularios

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

El manifiesto describe 83 fuentes con el vocabulario del manual de ingesta
(técnicas de extracción, estados de relevamiento). El esquema usa vocabularios
controlados con otro propósito: `clase` dice qué es una fuente, `adaptador` cómo
se la lee, `estado` en qué punto del ciclo está y `access_status` qué se pudo
hacer la última vez. La correspondencia no es uno a uno.

## Decisión

1. **Los 83 identificadores se conservan tal cual.** F01–F67 son la clave de
   trazabilidad con el manual y no se renumeran; D01–D10 y M01–M06 se agregan
   con prefijo propio para que las incorporaciones se distingan del relevamiento
   original.
2. **La derivación de vocabularios vive en un solo módulo**
   (`catalogo/derivacion.py`), es explícita y se audita en el reporte. Cuando
   una señal no alcanza para decidir, el resultado es el valor menos
   comprometido (`OTRA`, `SIN_ADAPTADOR`, `NO_VERIFICADO`) y no una suposición.
3. **Ninguna fuente arranca en `ACTIVE`.** Activo significa que la ingesta corrió
   y funcionó; este paquete no ingirió nada, y el manifiesto lo declara.
   `access_status` arranca en `NO_VERIFICADO` aunque el manual haya identificado
   la URL en agosto: eso no acredita que responda hoy.
4. **Las 15 fuentes sin URL conservan su brecha.** Quedan en el catálogo con
   `access_status = SIN_URL_CONOCIDA`, con política
   `NO_AUTOMATION_UNTIL_IDENTIFIED_AND_PUBLIC` y con una incidencia abierta que
   nombra responsable y tarea. No se fabrica una dirección, no se las descarta y
   siguen contando en el denominador de cobertura.
5. **`estado`, `access_status` y `alias_of` son independientes.** Un alias no
   está caído por ser alias, y una fuente activa puede estar limitada hoy.
6. **La carga es idempotente y no pisa el estado operativo.** Reejecutarla
   refresca la procedencia documental y las notas del manual, pero deja
   `estado` y `access_status` como los dejó la ingesta: el manifiesto describe el
   punto de partida, no el presente.
7. **Los denominadores se informan por separado.** Fuentes, alias, URLs,
   documentos, normas, beneficios y dependencias pendientes son cantidades
   distintas. 83 fuentes no son 83 leyes.

## Consecuencias

- El reporte de conciliación (`bn catalogo conciliar`) es reproducible y dice
  explícitamente qué no acredita: concilia el inventario, no la ingesta.
- Si el manifiesto cambia de forma, `bn catalogo validar` lo detecta antes de
  tocar la base.
- La derivación de `clase` a partir de las tablas destino es una lectura
  razonada, no un dato del manual. Queda registrada y es discutible: cambiarla
  es editar una tabla de correspondencias, no rehacer la carga.
