# Ciclo de monitoreo

- Corrida: `2026-09-08T16:47:27.405343+00:00`
- Fuentes que vuelven a la cola: **2**

| Paso | Cantidad | Detalle |
| --- | ---: | --- |
| planificacion | 2 | 2 fuente(s) quedaron fuera de su frecuencia y vuelven a la cola. Las que la política no habilita a automatizar y las que no tienen URL no entran: su brecha se resuelve por descubrimiento o carga manual. |
| revalidacion | 2 | Se volvió a pedir cada fuente vencida y se guardaron los originales. |
| versiones | 0 | Las capturas con texto distinto produjeron una versión documental nueva. |
| cambios | 0 | Cada versión nueva se comparó con la anterior. Un desplazamiento no es un cambio: sólo lo sustantivo cuenta. |
| impacto | 0 | Las normas que citan lo que cambió también se marcan para revisar. |
| eventos | 0 | Lo sustantivo llegó a la cola de eventos, que es de donde se entrega. |
| bloqueadas | 2 | Fuentes que respondieron con un acceso limitado y quedaron pausadas. |

## A quién le tocaba

`F04`, `F06`

## Qué falta para que esto sea periódico de verdad

El ciclo está completo y se puede correr entero con un comando. Lo que no hace es
dispararse solo: eso lo tiene que hacer un planificador del sistema o del
orquestador llamando a `bn monitoreo ciclo` cada hora. Es una decisión de
despliegue, no código que falte, y hasta que exista el corpus se actualiza cuando
alguien corre el comando.
