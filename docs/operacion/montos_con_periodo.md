# Acta: un importe histórico no es el importe de hoy

Evidencia de P-006 criterio 3, sobre las fuentes P0 de montos. Registra lo
verificado el 10 de septiembre de 2026.

## El caso

La página del Consejo Nacional del Salario publica esta tabla:

```
Fecha   Salario Mínimo, Vital y Móvil   Prest. Desempleo mín.   Prest. Desempleo máx.
a partir del 1/10/2026    $ 391.200    $ 195.600    $ 391.200
a partir del 1/11/2026    $ 398.800    $ 199.400    $ 398.800
a partir del 1/12/2026    $ 406.400    $ 203.200    $ 406.400
```

El error que el criterio nombra —«un importe histórico nunca reemplaza el actual
por ser el último descargado»— es tomar el último renglón de la descarga más
reciente y servirlo como el monto vigente. Acá se ve por qué no da: descargada
en **septiembre**, la tabla publica tres importes y **los tres empiezan a regir
en octubre o después**. En septiembre no rige ninguno de los tres.

`parametro_valores` estaba vacía: cero filas. Nunca se había cargado un importe.

## Cómo entran

Cada importe entra con su período, y **el período sale de la tabla, no de cuándo
se descargó**: «a partir del 1/10» rige hasta el día anterior al «a partir del»
siguiente, y el último queda abierto —un piso salarial rige desde su fecha hasta
que otra resolución lo cambie, y publicar el cronograma es respaldar eso—.

Verificado sobre F12: **9 valores** (3 períodos × 3 parámetros), con los rangos
`[2026-10-01,2026-11-01)`, `[2026-11-01,2026-12-01)` y `[2026-12-01,)`.
**Ninguno aplica al 10 de septiembre de 2026**, y exactamente uno aplica al 15 de
octubre.

Entran como `CANDIDATE` y no publicables: **cargar un importe no es aprobarlo.**
Publicarlo es una decisión de revisión, y el disparador de la tabla deja fuera de
lo publicable todo lo que no esté aprobado.

## Las columnas se declaran, no se adivinan

El encabezado de esa tabla es «Fecha Salario Mínimo, Vital y Móvil Prestación por
Desempleo monto mínimo Prestación por Desempleo monto máximo», sin separadores.
Partirlo por heurística es inventar a qué concepto pertenece cada número, y un
número asignado al concepto equivocado es peor que no tenerlo.

La fuente declara en su configuración qué parámetros trae y en qué orden. Si un
renglón no tiene esa cantidad de importes, se rechaza y se abre incidencia en vez
de acomodarlo. Sin declaración, no se carga nada y se dice por qué.

## Un importe sin fecha no se carga

La página de Progresar dice «El monto de la beca Progresar es de $35.000.-» y no
dice desde cuándo. Tomar la fecha de descarga como su período sería exactamente
el error que este criterio prohíbe, así que **no se carga**: queda una incidencia
que nombra el importe y dice qué le falta.

Es una decisión incómoda a propósito. La página publica ese monto como el
vigente, y el sistema se abstiene de servirlo como vigente porque la página no lo
respalda con una fecha. Abstenerse es lo correcto: quien pregunta «cuánto cobro»
no puede recibir un número que quizá cambió el mes pasado.

## Lo que ya estaba y no se usaba

El esquema tenía puesta la parte difícil desde la migración 0002 y nadie la había
ejercido:

- `parametro_valores_sin_solapamiento` impide que dos importes **publicables** del
  mismo parámetro se pisen en el tiempo. Aprobar un segundo importe que solape al
  primero falla en esa misma sentencia: un disparador propaga el cambio y la
  exclusión lo rechaza. Queda como prueba.
- `bn_rango_aplicacion` no convierte un límite desconocido en vigencia abierta, y
  el disparador deja no publicable todo valor sin rango. Un importe sin período
  no puede volverse el actual ni por error.

## Lo que este acta no acredita

- **Solo dos fuentes.** F12 carga y F52 registra su faltante. Las otras P0 de
  montos y plazos —F27, F36, F53— siguen sin llegar a destino: F36 no publica
  importes en el texto capturado, y F27 y F53 declaran `plazos`, que es la mitad
  de calendario del criterio y no se hizo en esta vuelta.
- **`plazos` sigue vacía.** El cronograma de pagos de Progresar —«DNI terminado
  en 0 y 1: 9 de febrero»— está en el texto capturado y no se carga todavía.
- **Los importes no están aprobados.** Los nueve son candidatos. Aprobarlos es
  P-009 y lo firma una persona.
- **La fecha de verificación es la de la captura.** El criterio pide registrar
  «período, fecha de verificación y beneficio»: el período está y la captura da
  la fecha, pero ninguno de estos importes está todavía asociado a un beneficio.
