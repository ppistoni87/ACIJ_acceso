# Acta de la carga del corpus

Evidencia de P-005: reconstruir y actualizar el corpus sin eliminar información
ya aprobada. Registra lo verificado el 9 de septiembre de 2026.

## El bootstrap no trae credenciales propias

`scripts/poblar_corpus.sh` es la única definición del procedimiento de carga.
No contiene `DROP DATABASE`: quien quiere una base vacía la crea aparte, y ese
paso vive en `scripts/corrida_limpia.sh`, que es explícitamente un ensayo
destructivo y no el bootstrap.

Lo que sí contenía eran credenciales locales fijas. Seis lugares llamaban a
`psql -h 127.0.0.1 -U postgres`, más un `PGPASSWORD` con valor por defecto, y
con eso el bootstrap solo podía correr contra la base local de un contenedor:
apuntarlo a una base gestionada exigía editar el script. Ahora la conexión sale
de `BN_DATABASE_URL` y de ningún otro lado —psql entiende la URL entera:
usuario, host, base y modo TLS— y si la variable falta, el script se detiene
diciéndolo en vez de conectarse a algo que no era.

## Reanudar sin volver a pedir ni duplicar

El esquema tenía la columna `corridas_ingesta.checkpoint` desde la primera
migración, el respaldo la preservaba y la restauración la verificaba. Nadie la
escribía. Una corrida interrumpida no perdía datos —capturar es idempotente—
pero perdía el lugar: reanudar volvía a pedirle a la fuente todo lo que ya se
le había pedido.

Ahora el capturador anota, URL por URL, cuáles ya hizo, y al reanudar continúa
**la misma corrida** en vez de abrir otra. Continuarla importa: si abriera una
nueva, la conciliación de esa fuente quedaría partida en dos mitades que no
cierran ninguna.

Dos detalles que el ensayo obligó a resolver:

- **Un checkpoint que nadie confirma no sobrevive al corte que tiene que
  sobrevivir.** Si la fuente entera va en una transacción, la interrupción la
  revierte completa y el checkpoint se va con ella. Por eso el comando confirma
  URL por URL. Las pruebas no confirman nunca, porque su aislamiento depende de
  revertir al final; quien orquesta decide, y el capturador no lo decide solo.
- **Los contadores de lo hecho antes del corte no se pueden inventar.** Se
  recuentan de las capturas que la corrida ya tiene, y lo que quedó anotado como
  hecho sin dejar captura fue un rechazo. El esquema lo hizo notar: una
  restricción rechaza `procesadas > descargadas`, y el primer intento —contar
  cada URL reanudada como procesada sin sumarla a descargadas— la violó.

Al cerrar, el checkpoint se borra. Una corrida cerrada que lo conservara se
reanudaría en vez de correr de nuevo.

## Que las cuentas cierren

Cada importador contaba lo suyo y lo imprimía. Eso alcanza mientras alguien mira
la corrida; la cuenta se pierde con la terminal. Ahora queda guardada como
control `DQ11` sobre la corrida, y `bn ingesta conciliar` la lee de vuelta.

La identidad que se comprueba es `leidas = nuevas + repetidas + rechazadas`.
`actualizadas` no entra en la suma: una fila que ya existía y cambió es repetida
*y* actualizada, y sumarla dos veces haría que la identidad no cierre justo
cuando el importador funciona bien.

Sobre el corpus real, reejecutando los cinco importadores:

| Fuente | Importador | Leídas | Nuevas | Repetidas | Actualizadas | Rechazadas | Cierra |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| F01 | catalogo_infoleg | 428.380 | 0 | 428.380 | 8.860 | 0 | sí |
| F20 | directorio | 21 | 0 | 21 | 0 | 0 | sí |
| F39 | padron_renabap | 6.467 | 0 | 6.467 | 0 | 0 | sí |
| F44 | dpn | 57 | 0 | 57 | 0 | 0 | sí |
| F60 | directorio | 229 | 0 | 229 | 0 | 0 | sí |

Cero filas nuevas en las cinco: reingestar lo mismo no duplicó nada, que es el
control DQ10 del paquete mostrado sobre datos reales y no sobre una prueba.

### Lo que la conciliación encontró

En el primer intento cada importador declaraba sus rechazos, y tres de los cinco
dieron números negativos: −322.473 en F01, −153 en F60, −2 en F44. Los
contadores que parecían rechazos no lo eran. `literales_sin_dato` cuenta campos
vacíos de filas que sí entraron como punto de atención; `sin_clave_canonica`
cuenta normas que se cargan con identidad incierta; `sin_direccion` cuenta
oficinas que entran igual, sin dirección. Declararlos como caídas restaba de la
suma cosas que estaban adentro.

Ahora `rechazadas` no se declara: se deriva de `leidas − nuevas − repetidas`, con
lo cual la aritmética no puede mentir, y lo que se comprueba pasa a ser lo que
importa —que ninguna fila caída quede sin motivo—. Los contadores de calidad
viven en `observaciones`, que se informan aparte y no restan:

- **F01** — 322.331 con identidad incierta, 235.489 sin texto, 6.561 homónimas,
  142 sin número
- **F20** — 21 coordenadas sin CRS declarado
- **F44** — 55 correos no tomados, 38 sin alcance declarado
- **F60** — 153 literales sin dato

`bn ingesta conciliar` sale distinto de cero si algo no cierra, si hay una fila
caída sin motivo o si quedó una corrida a medias, y corre al final del
bootstrap: dar por cerrada una carga que tiene una corrida interrumpida la deja
incompleta sin decirlo.

## Lo que este acta no acredita

- **El bootstrap no se corrió contra la base gestionada.** Este contenedor no
  tiene egreso TCP al 5432, y el bootstrap necesita `psql` y conexiones reales,
  no el endpoint HTTP. Lo verificado es que ya no trae credenciales fijas y que
  se detiene si falta la URL; que corra contra Neon hay que correrlo desde donde
  haya puerto.
- **La reanudación se ensayó dentro de una transacción.** Las pruebas cortan la
  corrida, comprueban el checkpoint y reanudan sin confirmar. Que el `commit`
  por URL sobreviva a un proceso muerto de verdad —no a una excepción— es un
  ensayo que pide matar el proceso, y ese va con el despliegue.
- **La conciliación no dice que lo importado sea correcto.** Dice que el
  importador dio cuenta de cada fila que leyó. Tampoco dice que la fuente
  tuviera esas filas y no más: si la página paginó y el adaptador leyó una sola,
  la conciliación cierra igual sobre lo que leyó.
- **La curación no concilia.** Los cinco importadores sí; la carga de beneficios
  curados informa por su cuenta y no pasa todavía por este control.
