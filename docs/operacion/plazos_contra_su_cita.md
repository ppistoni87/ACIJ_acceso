# Acta: los plazos contra su propia cita

Registra lo verificado el 10 de septiembre de 2026. Empezó como el intento de
cargar plazos desde las páginas de montos y calendarios —la otra mitad del
criterio 3 de P-006— y terminó en otro lado, que resultó más importante.

## Lo que se buscaba y lo que apareció

La idea era cargar los cronogramas de Progresar. No se pudo, y por una razón
legítima: un plazo necesita un dueño —un beneficio, un trámite o una norma— y
Progresar no está en el corpus como beneficio. Inventarlo desde una página
institucional habría sido crear una identidad sin norma detrás.

Mirando los 16 plazos que sí estaban cargados apareció otra cosa: **siete
declaraban una cantidad que su propia cita no contenía**. Un plazo que dice «30
días» y cita un fragmento donde no está el 30 comparte tema con el plazo y no lo
respalda, que es distinto. Es DQ02 —«cero citas que solo comparten tema»—
aplicado a los plazos.

Dos de esos siete resultaron falsos positivos míos: los textos legales escriben
los números con letras tanto como con cifras —«antes de los tres meses», «entre
el tercer y cuarto mes»— y buscar solo cifras acusa a plazos que están bien. El
control busca las dos formas. Quedaron **cinco** reales, de dos clases
distintas.

## Clase 1: el modelo obligaba a inventar un número

Tres plazos declaraban una cantidad que la norma no dice, y **los tres lo
avisaban**. Traían `requiere_revision: true` y un motivo que explica el problema
mejor de lo que lo habría explicado el control:

> «Se guarda con cantidad cero **porque el modelo exige una cantidad**, y eso es
> exactamente lo que hay que revisar: un cero acá significa "no hay duración
> declarada", no "vence el mismo día".»

No era un error de curaduría. Era el esquema: `ck_plazos_fechado_o_relativo_no_ambos`
obligaba a elegir entre una fecha y una duración, y estos tres plazos no son
ninguna de las dos cosas.

- «La ayuda escolar se hará efectiva **en el mes de marzo de cada año**» — una
  fecha recurrente, cargada como «1 día».
- «Se abonará **una (1) vez al año**» — una frecuencia, cargada como «1 día».
- «La solicitud se presentará **en el momento de la inscripción**» — un evento,
  cargado como «0 días».

La migración **0011** agrega la tercera forma: sin fechas y sin cantidad, con el
evento declarado. Sigue prohibido tener fecha y cantidad a la vez, y sigue
exigido que una cantidad venga con su unidad y su evento. Las tres lecturas
quedaron corregidas: sin el número inventado, con el evento y con el motivo
actualizado.

## Clase 2: la evidencia era la ventana de otro

Los otros dos —«quince (15) días» de la Ley 2917 y «cada tres (3) meses» del
Decreto 690— citaban su `texto_literal` correctamente. Lo que no coincidía era el
**fragmento guardado**.

La curación de beneficios reusa la evidencia de una unidad: una unidad tiene una
evidencia, no una por cada quien la cite. Pero la curación de relaciones escribe
evidencias cuyo fragmento es **la ventana alrededor de una cita**, no el texto de
la unidad. Reusar esa ventana dejaba plazos apuntando a un fragmento que no
contiene lo que afirman: el de «quince (15) días» citaba 273 caracteres de una
unidad de 696 que no incluían el número.

Todo tenía evidencia, y la evidencia no decía lo que se afirmaba. Ahora se reusa
la evidencia **que respalde lo que se está citando**; si ninguna lo hace, se
escribe una con el texto de la unidad.

## Resultado

`bn calidad plazos` sobre el corpus: **13 plazos, 11 con su cantidad respaldada
por la cita, 2 expresados como evento sin cantidad que comprobar, 0 sin
respaldo.** El control corre al final del bootstrap y falla si alguno vuelve a
quedar sin respaldo.

## Lo que este acta no acredita

- **Que un plazo respaldado sea correcto.** Que el fragmento contenga «30» prueba
  que el número está donde la cita dice, no que ese 30 sean los días de este
  plazo. Lo contrario sí es concluyente: nadie puede leer del texto un número que
  el texto no tiene.
- **Los cronogramas de Progresar siguen sin cargar.** F52 y F53 publican fechas
  de pago y ventanas de convocatoria, y el beneficio que las tendría como dueño
  no existe en el corpus. Crearlo es curaduría jurídica y la firma una persona.
- **Son 13 y no 16 porque tres lecturas no cargan en esta base de desarrollo.**
  Citan `articulo-1/inciso-c-4` de la Ley 24.714 y la versión documental más
  nueva de F33 numera esa ruta como `inciso-c-6`: un resto del episodio del
  corte por `<br>`, con dos versiones conviviendo. La carga se detiene y lo dice,
  que es lo correcto. En una corrida limpia hay una sola versión; que ahí carguen
  las dieciséis lo dice la corrida limpia, que no se rehizo.
