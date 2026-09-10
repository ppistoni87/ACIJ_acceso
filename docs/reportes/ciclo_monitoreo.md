# Ciclo de monitoreo

- Corrida: `2026-09-10T02:58:43.099731+00:00`
- Fuentes que vuelven a la cola: **7**

| Paso | Cantidad | Detalle |
| --- | ---: | --- |
| planificacion | 7 | 7 fuente(s) quedaron fuera de su frecuencia y vuelven a la cola. Las que la política no habilita a automatizar y las que no tienen URL no entran: su brecha se resuelve por descubrimiento o carga manual. |

## A quién le tocaba

`F53`, `M01`, `M02`, `M03`, `M04`, `M06`, `F04`

Corrida en seco: se planificó y no se salió a la red.

## Qué falta para que esto sea periódico de verdad

El ciclo está completo, se puede correr entero con un comando y no corre dos veces
a la vez: cada vuelta pide un turno con vencimiento y la que no lo consigue se va
sin tocar nada. Lo que no hace es dispararse solo: eso lo tiene que hacer un
planificador del sistema o del orquestador llamando a `bn monitoreo ciclo` cada
hora. Es una decisión de despliegue, no código que falte, y hasta que exista se
actualiza cuando alguien corre el comando.
