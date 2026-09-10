# Acta de la consola de revisión

Evidencia de P-016 criterio 1. La consola existe para una cosa: que las 166
reglas candidatas se puedan firmar en una sesión de trabajo, que es el bloqueo
número uno del proyecto. Hasta ahora eso se hacía por CLI leyendo un expediente
en Markdown, que funciona y pone la firma más lejos de quien tiene que darla.

## Cómo se usa

```
bn operacion emitir-credencial --actor "curacion_juridica:nombre" --rol revisor --dias 30
bn api servir
```

Después, `http://…/backoffice/reglas`, pegar la credencial y empezar.

La credencial vive en la pestaña de quien entra y en ningún otro lado: no se
escribe en `localStorage` ni en `sessionStorage` ni en una cookie, porque eso la
dejaría en el disco del navegador y lo que autoriza es firmar decisiones
jurídicas. Cerrar la pestaña la borra. Hay una prueba que comprueba que la página
servida no llame a ninguna de esas APIs.

## Qué muestra

**La cola, clasificada en pilas.** Contra el corpus real, las 166 candidatas caen
así:

| Pila | Cuántas | Qué hay que decidir |
| --- | ---: | --- |
| `CONDICION_EJECUTABLE` | 72 | Confirmar que la condición dice lo que dice la norma. |
| `SIN_CONDICION_EJECUTABLE` | 42 | Decidir si la condición se puede escribir o si la regla es informativa. |
| `NO_ES_CONDICION_SOBRE_LA_PERSONA` | 25 | No decide acceso: revisar como informativa. |
| `CONDICION_CON_UMBRAL_SIN_VALOR` | 20 | La condición existe pero su umbral no tiene valor cargado. |
| `CONDICION_EN_CATEGORIA_QUE_NO_DECIDE_ACCESO` | 7 | Tiene condición en una categoría que no resuelve elegibilidad. |

Las pilas no son decoración y no salen del texto del motivo, sino de hechos
observables —si tiene condición, si su umbral tiene valor, de qué categoría es—.
Importan porque el riesgo de aprobar no es el mismo en todas: mandarlas a la
misma cola hace que una condición ejecutable se apruebe sin mirar y una sin
condición se apruebe sin poder.

Las 166 están ubicadas en su artículo: **ninguna queda sin ubicar en el texto**.

**El expediente, en una pantalla.** La pregunta concreta que hay que contestar, el
texto literal de la norma, qué afirma la lectura curada, la condición ejecutable,
los parámetros de los que depende —marcando los que no tienen valor—, las otras
reglas de las que depende con su estado, la vigencia de la versión y los
controles de calidad. Todo junto, porque una condición se aprueba o no según de
qué depende y sobre qué versión rige, y pedirle a quien revisa que cruce seis
pantallas es pedirle que no las cruce.

**La decisión, con fundamento obligatorio.** Aprobar, rechazar o marcar en
revisión. Sin fundamento no se envía: una firma sin razones, para una decisión
jurídica, es casi lo mismo que no tenerla. Y va con `estado_esperado`, así que
dos personas revisando a la vez no se pisan: la segunda recibe conflicto.

## Lo que la consola no hace

- **Aprobar no publica.** La regla queda aprobada y recién el corte de release la
  vuelve servible. Son dos decisiones distintas y las toma gente distinta: una
  credencial de revisor no abre la ruta de publicación, verificado en prueba.
- **No aprueba en lote.** El plan lo prohíbe con nombre en el criterio 2 de
  P-010, y la consola no ofrece «aprobar todas»: cada regla se abre, se lee y se
  firma. Existe `bn revision aprobar-reglas <beneficio>` para quien decida usarlo
  desde la línea de comandos, y esa es una decisión de quien tiene competencia
  jurídica, no de la herramienta.
- **No es todo P-016.** Falta buscar normas y comparar versiones (criterio 1), el
  resumen del corte con sus controles antes de publicar (criterio 2) y el tablero
  de calidad con apertura de registros (criterio 3). Lo que hay es el circuito de
  reglas, que es el que está bloqueando el proyecto.

## Cómo se sirve

Un solo archivo HTML, sin compilar nada, servido por la misma aplicación en
`/backoffice/reglas`. No es minimalismo: quien tiene que firmar 166 reglas
necesita una pantalla, no una cadena de herramientas, y un artefacto que viaja
aparte se desfasa de la API que consume. Hay una prueba que comprueba que la
página se sirva, porque una consola que existe en el repositorio y no en la
imagen es una consola que no existe.

## Lo que este acta no acredita

- **No corrió con una persona usándola.** Se probó con navegador real —se entra
  con credencial, se abre un expediente, se firma y la regla sale de la cola— y
  a 400 px de ancho sin desborde horizontal, pero eso no es una revisión de
  accesibilidad ni una prueba de uso con quien va a revisar.
- **No está desplegada.** Corre donde corra la API. Publicarla en una URL estable
  es P-019 y necesita la cuenta de nube.
