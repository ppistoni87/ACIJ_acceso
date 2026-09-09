# Expediente de revisión de reglas

Las reglas curadas nacen candidatas y la evaluación no las usa hasta que alguien
con competencia jurídica las aprueba. Este documento es lo que esa persona
necesita para poder hacerlo: cada regla con su texto literal, qué afirma la
lectura y la pregunta concreta que hay que contestar.

Se genera con `bn revision reglas`. No aprueba nada: aprobar es
`bn revision aprobar-regla`, que exige actor y fundamento y los deja en la
bitácora.

## Estado

| Estado | Reglas |
| --- | ---: |
| CANDIDATE | 154 |
| SUPERSEDED | 10 |

En este expediente: **154** regla(s), de las cuales **59** no tienen condición ejecutable. Esas dos pilas no se revisan igual: una condición escrita se confirma contra el texto, y una regla sin condición hay que decidir si se puede escribir o si es informativa.

| Categoría | Reglas |
| --- | ---: |
| APLICABILIDAD | 78 |
| CESE | 4 |
| COMPATIBILIDAD | 6 |
| EXCEPCION | 14 |
| EXCLUSION | 15 |
| PRIORIDAD | 13 |
| REHABILITACION | 1 |
| REVOCACION | 3 |
| SALVAGUARDA | 17 |
| SUBSANACION | 1 |
| SUSPENSION | 2 |


## Propuesta de disposición, por pila

Las ciento cincuenta y cuatro reglas no plantean ciento cincuenta y cuatro
preguntas distintas: plantean unas pocas, repetidas. Agruparlas por lo que hay
que decidir convierte la revisión en decidir esas pocas y repartir, que es como
se trabaja de verdad.

Esto es una **propuesta**, no una aprobación. Aprobar es afirmar que lo que el
backend contesta es lo que dice el derecho, y eso lo firma una persona con
competencia jurídica, con su nombre y su fundamento en la bitácora.

### CONDICION_EJECUTABLE · 69 regla(s)

**Propuesta: Aprobar tras confirmar la condición contra el texto.** Tienen su condición escrita y validada, y su umbral tiene valor. Lo que queda es lo único que una máquina no puede hacer: leer el artículo citado y confirmar que la condición dice lo mismo. Es la pila donde aprobar habilita respuestas afirmativas, así que es la que hay que leer con más cuidado y la que más devuelve.

Beneficios alcanzados: AR.ASIGNACION-HIJO-CON-DISCAPACIDAD, AR.ASIGNACION-POR-ADOPCION, AR.ASIGNACION-POR-CONYUGE-SIJP, AR.ASIGNACION-POR-EMBARAZO, AR.ASIGNACION-POR-HIJO, AR.ASIGNACION-POR-MATERNIDAD, AR.ASIGNACION-POR-MATRIMONIO, AR.ASIGNACION-POR-NACIMIENTO, AR.ASIGNACION-PRENATAL, AR.AUH, AR.AYUDA-ESCOLAR-ANUAL, AR.CUIDADO-DE-SALUD-INTEGRAL, CABA.APOYO-VULNERABILIDAD-HABITACIONAL, CABA.BECA-COMEDOR-ESCOLAR, CABA.BECAS-ESTUDIANTILES, CABA.SUBSIDIO-SITUACION-DE-CALLE.

### SIN_CONDICION_EJECUTABLE · 34 regla(s)

**Propuesta: No aprobar todavía: primero decidir si la condición se puede escribir.** No tienen condición ejecutable porque la norma remite a una reglamentación que no está en el corpus, porque el dato que harían falta no existe en el modelo, o porque lo que dicen no se puede reducir a verdadero o falso. Aprobarlas no habilita nada —no hay qué evaluar— y sí las presenta como revisadas. Cada una necesita una de tres decisiones: se puede escribir la condición, hay que traer la norma que falta, o la regla es informativa y se conserva sin condición.

Beneficios alcanzados: AR.ASIGNACION-HIJO-CON-DISCAPACIDAD, AR.ASIGNACION-POR-EMBARAZO, AR.ASIGNACION-POR-HIJO, AR.ASIGNACION-POR-MATERNIDAD, AR.ASIGNACION-POR-MATRIMONIO, AR.AYUDA-ESCOLAR-ANUAL, CABA.APOYO-VULNERABILIDAD-HABITACIONAL, CABA.BECA-COMEDOR-ESCOLAR, CABA.BECAS-ESTUDIANTILES, CABA.SUBSIDIO-SITUACION-DE-CALLE.

### NO_ES_CONDICION_SOBRE_LA_PERSONA · 25 regla(s)

**Propuesta: No aprobar como condición de acceso: describen otra cosa.** Prioridades, salvaguardas, subsanaciones y rehabilitaciones no dicen si alguien accede: dicen cómo se reparte un cupo, qué pasa cuando nadie pidió el beneficio, o cómo se recupera. Aprobarlas como condición de aplicabilidad las convertiría en un requisito que la norma no puso, y son justamente las que evitan que la falta de solicitud se lea como falta de derecho. Hay que decidir cómo las representa el modelo, y esa es una decisión de diseño antes que jurídica.

Beneficios alcanzados: AR.ASIGNACION-HIJO-CON-DISCAPACIDAD, AR.ASIGNACION-POR-ADOPCION, AR.ASIGNACION-POR-CONYUGE-SIJP, AR.ASIGNACION-POR-EMBARAZO, AR.ASIGNACION-POR-HIJO, AR.ASIGNACION-POR-MATERNIDAD, AR.ASIGNACION-POR-MATRIMONIO, AR.ASIGNACION-POR-NACIMIENTO, AR.ASIGNACION-PRENATAL, AR.AUH, AR.AYUDA-ESCOLAR-ANUAL, AR.CUIDADO-DE-SALUD-INTEGRAL, CABA.APOYO-VULNERABILIDAD-HABITACIONAL, CABA.BECA-COMEDOR-ESCOLAR, CABA.BECAS-ESTUDIANTILES, CABA.SUBSIDIO-SITUACION-DE-CALLE.

### CONDICION_CON_UMBRAL_SIN_VALOR · 19 regla(s)

**Propuesta: Aprobar: mientras el parámetro no tenga valor, la regla contesta «no se sabe».** La condición está escrita y compara contra un parámetro que todavía no tiene valor aprobado —el salario mínimo del convenio de comercio, el sueldo mínimo municipal—. Aprobarlas es de bajo riesgo justamente por eso: sin valor, la evaluación devuelve desconocido, que es la respuesta correcta, y no «no calificás». Dejarlas candidatas no protege de nada y esconde condiciones que sí están bien leídas. Lo que hay que decidir aparte, y con evidencia, es el valor del parámetro.

Beneficios alcanzados: AR.ASIGNACION-POR-ADOPCION, AR.ASIGNACION-POR-CONYUGE-SIJP, AR.ASIGNACION-POR-EMBARAZO, AR.ASIGNACION-POR-HIJO, AR.ASIGNACION-POR-MATRIMONIO, AR.ASIGNACION-POR-NACIMIENTO, AR.ASIGNACION-PRENATAL, AR.AUH, AR.CUIDADO-DE-SALUD-INTEGRAL, CABA.APOYO-VULNERABILIDAD-HABITACIONAL, CABA.BECA-COMEDOR-ESCOLAR, CABA.BECAS-ESTUDIANTILES, CABA.SUBSIDIO-SITUACION-DE-CALLE.

### CONDICION_EN_CATEGORIA_QUE_NO_DECIDE_ACCESO · 7 regla(s)

**Propuesta: Revisar la categoría antes que la condición.** Tienen condición escrita pero están en una categoría que no decide acceso. O la categoría está mal puesta y la condición sirve, o la categoría está bien y la condición no debería evaluarse como aplicabilidad. Es un caso por caso corto.

Beneficios alcanzados: AR.ASIGNACION-HIJO-CON-DISCAPACIDAD, AR.ASIGNACION-POR-EMBARAZO, AR.ASIGNACION-POR-HIJO, AR.ASIGNACION-PRENATAL, CABA.APOYO-VULNERABILIDAD-HABITACIONAL, CABA.BECAS-ESTUDIANTILES.


## AR.ASIGNACION-HIJO-CON-DISCAPACIDAD

### `745a37fd-b9ad-4053-ba53-22a649d8003a` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> A los efectos de esta ley se entiende por discapacidad la definida en la Ley N° 22.431, artículo 2°.

**La lectura afirma:** La discapacidad es la definida en el artículo 2 de la Ley 22.431.

**Qué hay que decidir:** La definición vive en otra norma que no está en el corpus. Escribir acá qué cuenta como discapacidad sería sustituir esa definición por una propia, y de esa definición depende el acceso: el campo guarda si la condición está acreditada por autoridad competente y no reconstruye el criterio.

### `932c53aa-eb5e-4757-94b6-4796f55a16a4` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación por hijo con discapacidad consistirá en el pago de una suma mensual que se abonara al trabajador por cada hijo que se encuentre a su cargo en esa condición, sin limite de edad, a partir del mes en que se acredite tal condición ante el empleador.

**La lectura afirma:** Tener a cargo un hijo con discapacidad, sin límite de edad, desde el mes en que se acredita esa condición ante el empleador.

**Qué hay que decidir:** El derecho corre «a partir del mes en que se acredite tal condición ante el empleador», y eso no es una condición sobre la persona sino el momento desde el que se paga: una discapacidad certificada en marzo no habilita el pago de enero aunque existiera antes. El árbol guarda si la condición está acreditada y no desde cuándo; de esa fecha depende cuántos meses se cobran.

### `9f2c42b8-9836-4730-955c-70cbb1d09d5c` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo.

**Qué hay que decidir:** La lista junta cuatro situaciones del inciso a) y a’) con dos que entran por el artículo 24, que se rigen por este régimen «en cuanto a las prestaciones monto y topes» y no necesariamente en todo lo demás. Es la misma decisión pendiente que en la asignación por hijo: si se resuelve, se resuelve en las dos.

### `c92c818d-f3c0-438c-aac0-f4d37c15f220` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01). (Tope máximo de remuneración sustituido por art. 1° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del 1º de julio de 2007).

**La lectura afirma:** La exclusión por remuneración fuera del piso y el techo no alcanza a esta asignación: el artículo 3 la exceptúa expresamente junto con la de maternidad.

**Qué hay que decidir:** Es la diferencia más importante con la asignación por hijo común y la más fácil de perder: superar el tope de ingresos no saca a nadie de esta prestación. No se formaliza como condición porque no lo es —es una excepción a otra regla, y por eso se guarda como tal—, y escribirla como AST que devuelve verdadero haría creer que hay algo que cumplir. Lo que hay que confirmar es si la excepción alcanza también al piso mínimo o sólo al techo: el texto excluye por los dos extremos en la misma oración y exceptúa sin distinguir.

### `681fc6b9-31b9-4fe5-bc77-3ebeb84d1503` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-22` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> serán considerados como hijos los menores o personas con discapacidad cuya guarda, tenencia o tutela haya sido acordada al trabajador por autoridad judicial o administrativa competente. En tales supuestos, los respectivos padres no tendrán, por ese hijo, derecho al cobro de las mencionadas asignaciones.

**La lectura afirma:** Cuentan como hijos las personas con discapacidad cuya guarda, tenencia o tutela fue acordada al trabajador por autoridad competente; en ese caso los padres no cobran por ese hijo.

**Qué hay que decidir:** El artículo nombra expresamente a la asignación por hijo con discapacidad. Y dice «los menores o personas con discapacidad», que acá importa: como esta prestación no tiene límite de edad, la guarda o curatela de una persona adulta con discapacidad entra por esta puerta. Amplía qué cuenta como hijo y a la vez saca el derecho a los padres: son dos efectos y el árbol alcanza el primero.

### `9f006603-6b99-4bad-8eb2-e46e96026176` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-20` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> ARTICULO 20.- Cuando ambos progenitores estén comprendidos en el presente régimen, las prestaciones enumeradas en los artículos 6º y 15 serán percibidas por uno solo de ellos.

**La lectura afirma:** Cuando ambos progenitores están comprendidos en el régimen, la prestación la percibe uno solo de ellos.

**Qué hay que decidir:** La ley dice que cobra uno solo y no dice cuál. Elegir un criterio sería inventar la parte que el legislador no escribió, y esa elección decide quién cobra.

### `527b809c-95f1-40de-a8f7-ce2ae1f89546` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-21` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> ARTICULO 21.- Cuando el trabajador se desempeñare en más de un empleo tendrá derecho a la percepción de las prestaciones de la presente ley en el que acredite mayor antigüedad, a excepción de la asignación por maternidad, que será percibida en cada uno de ellos.

**La lectura afirma:** Con más de un empleo, la prestación se percibe en el que acredite mayor antigüedad.

**Qué hay que decidir:** Es una regla de dónde se cobra, no de si se cobra. Acá pesa menos que en la asignación por hijo común, porque el tope de ingresos no aplica: la elección del empleo no puede dejar a nadie afuera, sólo cambia quién liquida.

### `3acf050d-caa8-4c80-8b04-66f9e7dfe68d` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST. Se conserva porque es lo que hay que poder responder cuando alguien pregunta si le pueden descontar la asignación por una deuda.


## AR.ASIGNACION-POR-ADOPCION

### `a23fe304-ff6e-4f99-82f8-5727d14534d7` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-13` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación por adopción consistirá en el pago de una suma de dinero que se abonará una vez acreditado dicho acto ante la Administración Nacional de la Seguridad Social (ANSES).

**La lectura afirma:** Acreditar el acto de adopción ante ANSES.

**Qué hay que decidir:** El texto habla de acreditar «dicho acto», y en una adopción el acto puede ser la sentencia, la guarda con fines de adopción o la inscripción: cuál de los tres es no lo dice la ley, y entre uno y otro pueden pasar años.

### `1f2e94cc-2b65-487f-9ab3-1ede91eabae3` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-septies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Las personas titulares comprendidas en el inciso c) del artículo 1º de la presente ley tendrán derecho a la percepción de las asignaciones por nacimiento y adopción establecidas en los incisos f) y g) del artículo 6º también de la presente. Para acceder a dichas prestaciones, las personas titulares deberán acreditar el hecho y/o el acto generador pertinente ante la Administración Nacional de la Seguridad Social (ANSES).

**La lectura afirma:** Los titulares del subsistema no contributivo tienen derecho a esta asignación, acreditando el hecho ante ANSES.

**Qué hay que decidir:** La otra puerta. El artículo dice «tendrán derecho», no «podrán solicitar». Queda pendiente si quien entra por acá está sujeto al tope de ingresos del artículo 3, que está escrito para el subsistema contributivo y mide una remuneración que esta persona no tiene registrada.

### `9483113f-ed71-492b-a882-78f555dfdab1` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo.

**Qué hay que decidir:** Es una de las dos puertas de entrada, no un requisito: el artículo 14 septies abre la otra para los titulares del subsistema no contributivo. Un evaluador que exija las dos juntas dejaría afuera a todo el mundo.

### `76053d83-f2f8-484d-b35a-096cafc21cb0` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).

**La lectura afirma:** Queda excluido quien percibe una remuneración fuera del piso y el techo. La asignación por adopción no está entre las excepciones del artículo 3.

**Qué hay que decidir:** Los dos números del texto son de 2007 y no rigen: se comparan contra parámetros y, sin valor aprobado para el período consultado, la regla devuelve desconocido. En una prestación de pago único el tope se mide sobre la remuneración de un momento —el del hecho acreditado— y la ley no dice cuál, lo que en un sueldo variable cambia el resultado.

### `7586019d-c2a2-45db-9e59-0469274e523e` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST.


## AR.ASIGNACION-POR-CONYUGE-SIJP

### `c3ce4bdf-23da-431f-93bf-d3cb866d5223` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-15` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> ARTICULO 15.- Los beneficiarios del Sistema Integrado de Jubilaciones y Pensiones gozarán de las siguientes prestaciones:

**La lectura afirma:** Ser beneficiario del Sistema Integrado de Jubilaciones y Pensiones.

**Qué hay que decidir:** El artículo 15 abre una lista y el texto capturado la corta ahí: las prestaciones que enumera están en los artículos siguientes. La condición es clara; qué prestaciones exactas cubre esta puerta es lo que hay que leer completo antes de aprobarla.

### `03a28547-69dc-4970-8ee4-d394564c7ab8` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-16` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación por cónyuge del beneficiario del Sistema Integrado de Jubilaciones y Pensiones consistirá en el pago de una suma de dinero que se abonara al beneficiario por su cónyuge.

**La lectura afirma:** Tener cónyuge.

**Qué hay que decidir:** El artículo no pide acreditar nada ni fija antigüedad: dice sólo que se abona «por su cónyuge». Es la prestación de la ley con menos condiciones escritas, y eso no significa que no haya requisitos sino que no están acá. Y dice «cónyuge», no «conviviente».

### `0c3d0793-0e2a-4188-bce2-5dc5765c466d` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-18/inciso-i-84` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> i) Asignación por Cónyuge del beneficiario del SISTEMA INTEGRADO DE JUBILACIONES Y PENSIONES: la suma de PESOS TREINTA ($ 30) para los que perciban haberes inferiores a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).

**La lectura afirma:** El monto corresponde a quienes perciben haberes inferiores al tope que fija el propio inciso.

**Qué hay que decidir:** El tope viaja en el inciso del monto y no en el artículo 3, que habla de remuneración y no de haberes previsionales. Se apunta al mismo parámetro de tope máximo porque el número escrito es el mismo, y eso es exactamente lo que hay que confirmar: si las resoluciones vigentes los actualizan juntos o por separado, apuntar al mismo parámetro sería un error que decide quién cobra.

### `281711bd-a037-4101-a691-b275863c8c8a` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST.


## AR.ASIGNACION-POR-EMBARAZO

### `1a1b0ea3-4e5f-4c77-aca9-cf10e5fea213` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quinquies/inciso-c-57` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La acreditación del estado de embarazo mediante la inscripción en el "Plan Nacer" del MINISTERIO DE SALUD.

**La lectura afirma:** Acreditar el estado de embarazo mediante la inscripción en el Plan Nacer del Ministerio de Salud, o por certificado médico en los casos con cobertura de obra social que prevea la reglamentación.

**Qué hay que decidir:** El texto nombra el «Plan Nacer», un programa que dejó de llamarse así hace más de una década. La vía alternativa —certificado médico para quien tiene obra social— queda condicionada a lo que prevea la reglamentación, que no está en el corpus. El campo guarda si el embarazo está acreditado y no cuál de las dos vías se usó: elegir una diría que la otra no sirve.

### `82c06195-8899-4fdc-afd5-3513026cc8d1` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quinquies/inciso-a-55` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Que la embarazada sea argentina nativa o por opción, naturalizada o residente, con residencia legal en el país no inferior a TRES (3) años previos a la solicitud de la asignación.

**La lectura afirma:** Ser argentina nativa o por opción, naturalizada o residente, con residencia legal en el país no inferior a tres años previos a la solicitud.

**Qué hay que decidir:** Son tres años, y la Asignación Universal por Hijo del mismo subsistema pide dos. La diferencia está en el texto de las dos normas y no se unifica: cada prestación conserva su requisito. Además el inciso enumera «argentina nativa o por opción, naturalizada o residente» y la exigencia de residencia legal se lee sobre el último caso; leerla sobre todos le pediría tres años de residencia a una argentina nativa que volvió al país.

### `76e06c7e-9b8d-4bf2-96c7-7a773dbb9e09` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quinquies/inciso-b-56` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> b) Acreditar identidad, mediante Documento Nacional de Identidad.

**La lectura afirma:** Acreditar identidad mediante Documento Nacional de Identidad.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `39ee47d2-2d68-47d9-9bca-138c0c40805a` · COMPATIBILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quater/parrafo-52` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> La percepción de esta asignación no será incompatible con la Asignación Universal por Hijo para Protección Social por cada menor de DIECIOCHO (18) años, o sin límite de edad cuando se trate de un discapacitado, a cargo de la mujer embarazada.

**La lectura afirma:** Percibir esta asignación no es incompatible con percibir la Asignación Universal por Hijo por cada menor de dieciocho años, o sin límite de edad si tiene discapacidad, a cargo de la persona embarazada.

**Qué hay que decidir:** Es una afirmación de la ley, no una condición que alguien cumpla. Está acá porque una regla de compatibilidad omitida se lee como incompatibilidad, y eso haría que una persona gestante que ya cobra la AUH creyera que tiene que elegir. Cómo se representa una compatibilidad declarada es lo que la revisión tiene que decidir.

### `7e8fe227-4afc-4724-8676-8052064ad979` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3/parrafo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos del beneficio previsto en el artículo 1° inciso c) de la presente los trabajadores que se desempeñen en la economía informal, que perciban una remuneración superior al salario mínimo, vital y móvil.

**La lectura afirma:** Queda excluida quien se desempeñe en la economía informal y perciba una remuneración superior al salario mínimo, vital y móvil.

**Qué hay que decidir:** La exclusión es del inciso c) del artículo 1, que es el subsistema no contributivo entero: alcanza a esta asignación igual que a la Asignación Universal por Hijo. Pide dos cosas a la vez —informalidad y remuneración sobre el salario mínimo— y quien trabaja en la economía informal no tiene una remuneración registrada contra la cual medir: el dato es declarado. Mientras el umbral no tenga valor aprobado para el período consultado, la regla devuelve desconocido.

### `cb88140e-e7b0-4911-ac06-3307c465e5a8` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quinquies/parrafo-58` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Si el requisito se acredita con posterioridad al nacimiento o interrupción del embarazo, no corresponde el pago de la asignación por el período correspondiente al de gestación.

**La lectura afirma:** Si el embarazo se acredita después del nacimiento o de la interrupción, no corresponde el pago por el período de gestación.

**Qué hay que decidir:** No excluye del beneficio: excluye del pago de un período. El modelo guarda reglas que dicen si alguien accede, no reglas que recorten meses ya transcurridos, y clasificarla como exclusión sin decir esto haría que una acreditación tardía se leyera como «no te corresponde la asignación». Es lo contrario de lo que dice el texto.

### `d2d67cb3-9ead-4b84-b9d1-c6465e78e219` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quater/parrafo-52` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Sólo corresponderá la percepción del importe equivalente a UNA (1) Asignación por Embarazo para Protección Social, aún cuando se trate de embarazo múltiple.

**La lectura afirma:** Corresponde una sola asignación aunque el embarazo sea múltiple.

**Qué hay que decidir:** La regla es sobre cuántas se cobran, no sobre si se accede, y el AST guardado sólo dice que hay un embarazo acreditado. Es el contraste con la Asignación Universal por Hijo, que se paga por cada causante: acá el embarazo múltiple no multiplica la prestación. Cómo se guarda un tope de cantidad es la decisión que queda abierta.

### `18a3cc4f-0a86-454e-9b8e-a7900bf09289` · REVOCACION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quinquies/inciso-d-59` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> d) La presentación por parte del titular del beneficio de una declaración jurada relativa al cumplimiento de los requisitos exigidos por la presente y a las calidades invocadas. De comprobarse la falsedad de alguno de estos datos, se producirá la pérdida del beneficio, sin perjuicio de las sanciones que correspondan.

**La lectura afirma:** La titular presenta una declaración jurada sobre el cumplimiento de los requisitos; comprobada la falsedad de alguno de esos datos se pierde el beneficio, sin perjuicio de las sanciones que correspondan.

**Qué hay que decidir:** Es a la vez la vía de acreditación y la causal de pérdida, y el texto no dice qué pasa con lo ya percibido ni si la pérdida es definitiva. Tampoco dice quién comprueba la falsedad ni con qué procedimiento. Formalizar la pérdida sin eso convertiría una discrepancia en un dato declarado en una baja automática.

### `afb4bccf-93cb-4f09-8bcb-456951c2dc26` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración, no está sujeta a gravámenes y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** No es una condición de acceso: es una protección sobre lo cobrado, y por eso no tiene AST. Se conserva porque es lo que hay que poder responder cuando alguien pregunta si le pueden descontar la asignación por una deuda. El artículo tiene además un tercer párrafo derogado en 2024, así que qué protege exactamente hoy es una lectura que hay que hacer sobre el texto vigente.


## AR.ASIGNACION-POR-HIJO

### `87fb4ca1-6e82-47e1-9e27-f53308e9a541` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-7` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación por hijo consistirá en el pago de una suma mensual por cada hijo menor de 18 anos de edad que se encuentre a cargo del trabajador.

**La lectura afirma:** Tener a cargo un hijo menor de dieciocho años.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `b6629b37-2236-41c4-8033-4cf5e9d73fe2` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-4` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Se considerará remuneración a los efectos de esta ley, la definida por el Sistema Integrado de Jubilaciones y Pensiones (Ley Nº 24.241, artículos 6º y 9º) con excepción de las horas extras y el sueldo anual complementario (SAC).

**La lectura afirma:** Remuneración es la definida por la Ley 24.241 artículos 6 y 9, sin horas extras ni sueldo anual complementario.

**Qué hay que decidir:** No es una condición sino la definición del dato con el que se miden las demás. Está acá porque cambia el resultado: quien hace horas extras puede quedar por encima del tope si se cuentan y por debajo si no, y la ley dice que no se cuentan. La definición remite a otra norma que no está en el corpus.

### `140779cd-193c-4ea1-881e-2a3c8315fbf8` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo: relación de dependencia en la actividad privada, Ley sobre Riesgos del Trabajo o Seguro de Desempleo.

**Qué hay que decidir:** La lista junta cuatro situaciones del inciso a) y a’) con dos que entran por el artículo 24 —sector público y pensiones no contributivas—, que se rigen por este régimen «en cuanto a las prestaciones monto y topes» y no necesariamente en todo lo demás. Meterlas en la misma lista hace la regla usable y borra esa diferencia: qué del régimen les aplica y qué no es una lectura jurídica que hay que hacer.

### `0d66fe7a-f804-4672-9d50-fe2f9f06783e` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3/parrafo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Para los que trabajen en las Provincias de LA PAMPA, NEUQUEN, RIO NEGRO, CHUBUT, SANTA CRUZ, TIERRA DEL FUEGO, ANTARTIDA E ISLAS DEL ATLANTICO SUR; o en los Departamentos de Antofagasta de la Sierra (exclusivamente para los que se desempeñen en la actividad minera) de la Provincia de CATAMARCA; o en los Departamentos de Cochinoca, Humahuaca, Rinconada, Santa Catalina, Susques y Yavi de la Provincia de JUJUY; o en el Distrito Las Cuevas del Departamento de Las Heras, en los Distritos Potrerillos, Carrizal, Agrelo, Ugarteche, Perdriel y Las Compuertas del Departamento de Luján de Cuyo, en los Distritos de Santa Clara, Zapata, San José y Anchoris del Departamento Tupungato, en los Distritos de Los Arboles, Los Chacayes y Campo de los Andes del Departamento de Tunuyán, en el Distrito de Pareditas del Departamento San Carlos, en el Distrito de Cuadro Benegas del Departamento San Rafael, en los Distritos Malargüe, Río Grande, Río Barrancas, Agua Escondida del Departamento Malargüe, en los Distritos Russell, Cruz de Piedra, Las Barrancas y Lumlunta del Departamento Maipú, en los Distritos de El Mirador, Los Campamentos, Los Arboles, Reducción y Medrano del Departamento Rivadavia de la Provincia de MENDOZA; o en los Departamentos de General San Martín (excepto Ciudad de Tartagal y su ejido urbano), Rivadavia, Los Andes, Santa Victoria y Orán (excepto Ciudad de San Ramón de la Nueva Oran y su ejido urbano) de la Provincia de SALTA; o en los Departamentos Bermejo, Ramón Lista y Matacos de la Provincia de FORMOSA, la remuneración deberá ser inferior a PESOS CIEN ($100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01) para excluir al trabajador del cobro de las prestaciones previstas en la presente ley (Tope máximo de remuneración sustituido por art. 1° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del 1º de julio de 2007)

**La lectura afirma:** Para quienes trabajan en las provincias y departamentos que el artículo enumera, el tope máximo de remuneración es más alto.

**Qué hay que decidir:** El párrafo enumera provincias, departamentos y hasta distritos —Las Cuevas, Potrerillos, Cuadro Benegas— con un nivel de detalle que no se puede reducir a «zona desfavorable» sin perder cuál es cuál. Formalizarlo pide un catálogo de esas localidades que el corpus no tiene, y una lista escrita a ojo dejaría afuera a quien vive en un distrito que no se copió bien. Se conserva el texto entero.

### `13781b64-89e7-4452-b693-8a663b2ac8bd` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-22` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> serán considerados como hijos los menores o personas con discapacidad cuya guarda, tenencia o tutela haya sido acordada al trabajador por autoridad judicial o administrativa competente. En tales supuestos, los respectivos padres no tendrán, por ese hijo, derecho al cobro de las mencionadas asignaciones.

**La lectura afirma:** Cuentan como hijos los menores o personas con discapacidad cuya guarda, tenencia o tutela fue acordada al trabajador por autoridad judicial o administrativa; en ese caso los padres no cobran por ese hijo.

**Qué hay que decidir:** El artículo nombra expresamente a la asignación por hijo, así que acá sí aplica —a diferencia de la Asignación Universal por Hijo, que se incorporó trece años después y no está nombrada—. Amplía qué cuenta como hijo y a la vez saca el derecho a los padres: son dos efectos y el árbol guardado sólo alcanza el primero.

### `9ddc4b00-75e7-497d-8986-8e24e44e0a40` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-2` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Las empleadas/os del Régimen Especial de Contrato de Trabajo para el Personal de Casas Particulares se encuentran incluidas en el inciso c) del artículo 1°, siendo beneficiarias de la Asignación por Embarazo para Protección Social y de la Asignación Universal por Hijo para Protección Social, quedando excluidas de los incisos a) y b) del citado artículo con excepción del derecho a la percepción de la Asignación por Maternidad establecida por el inciso e) del artículo 6° de la presente ley.

**La lectura afirma:** El personal de casas particulares está en el subsistema no contributivo y queda excluido del contributivo, salvo la asignación por maternidad.

**Qué hay que decidir:** No es una exclusión del sistema sino un reencauzamiento: quien trabaja en casas particulares no cobra esta asignación y sí cobra la Asignación Universal por Hijo y la Asignación por Embarazo, que están curadas aparte. Una respuesta que diga sólo «quedás excluida» sería cierta y engañosa. Cómo se enlaza una exclusión con la prestación que sí corresponde es la decisión que queda abierta.

### `4c5e2217-cdde-48e2-a655-046aec01212c` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).

**La lectura afirma:** Queda excluido quien percibe una remuneración inferior al piso o igual o superior al techo, con excepción de las asignaciones por maternidad y por hijo con discapacidad.

**Qué hay que decidir:** Los dos números del texto —cien pesos de piso y cuatro mil con un centavo de techo— son de 2007 y hoy no rigen: las notas del artículo 26 registran una decena de resoluciones de ANSES que los fueron actualizando, y ninguna está en el corpus. Escribirlos como valores en el árbol habría excluido a todo el mundo por superar el tope, que es exactamente el error opuesto al que la norma quiere evitar. Se comparan contra parámetros: mientras no tengan valor aprobado para el período consultado, la regla devuelve desconocido en vez de excluir a alguien con un tope de hace dieciocho años.

### `51208ea3-ca51-4c69-b786-966bde0d4f72` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-20` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> ARTICULO 20.- Cuando ambos progenitores estén comprendidos en el presente régimen, las prestaciones enumeradas en los artículos 6º y 15 serán percibidas por uno solo de ellos.

**La lectura afirma:** Cuando ambos progenitores están comprendidos en el régimen, la prestación la percibe uno solo de ellos.

**Qué hay que decidir:** La ley dice que cobra uno solo y no dice cuál. No hay regla que formalizar: elegir un criterio sería inventar la parte que el legislador no escribió, y esa elección decide quién cobra.

### `ccc2b260-93b6-4230-af4e-094f9d607bd8` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-21` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> ARTICULO 21.- Cuando el trabajador se desempeñare en más de un empleo tendrá derecho a la percepción de las prestaciones de la presente ley en el que acredite mayor antigüedad, a excepción de la asignación por maternidad, que será percibida en cada uno de ellos.

**La lectura afirma:** Con más de un empleo, la prestación se percibe en el que acredite mayor antigüedad, salvo la asignación por maternidad.

**Qué hay que decidir:** Es una regla de dónde se cobra, no de si se cobra, y el árbol guardado sólo puede decir si el empleo consultado es el de mayor antigüedad. Importa además para el tope del artículo 3: si la remuneración que se compara es la de ese empleo o la suma de los dos, la ley no lo dice acá y la diferencia decide quién queda afuera.

### `bf32390a-bf00-409f-ac68-511324826abf` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración, no está sujeta a gravámenes ni se computa para el aguinaldo o las indemnizaciones.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST. Se conserva porque es lo que hay que poder responder cuando alguien pregunta si le pueden descontar la asignación por una deuda. El artículo tiene un tercer párrafo derogado en 2024: qué protege exactamente hoy es una lectura sobre el texto vigente.


## AR.ASIGNACION-POR-MATERNIDAD

### `44b274de-1dc9-420a-bc1e-ee277c81e239` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Para el goce de esta asignación se requerirá una antigüedad mínima y continuada en el empleo de tres meses.

**La lectura afirma:** Acreditar una antigüedad mínima y continuada en el empleo de tres meses.

**Qué hay que decidir:** «Mínima y continuada» pide dos cosas: que llegue a tres meses y que no se haya interrumpido. El árbol guarda la primera; qué interrumpe la continuidad —un cambio de empleador, una licencia sin goce de sueldo, una suspensión— no lo dice la ley y decide el acceso a la única prestación que reemplaza el sueldo durante la licencia.

### `3bf36d19-7afd-46f9-919b-edb75de948d0` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendida en el subsistema contributivo.

**Qué hay que decidir:** La lista incluye a las empleadas de casas particulares, que el artículo 2 saca del subsistema contributivo «con excepción del derecho a la percepción de la Asignación por Maternidad»: es la única prestación de este subsistema que sí les corresponde. Meterlas en la misma lista hace la regla usable acá y sería incorrecto en cualquier otra lectura de esta ley, así que la lista no se comparte entre prestaciones.

### `3ad196bf-a690-41e4-bede-90f7efea30b6` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> que se abonara durante el periodo de licencia legal correspondiente.

**La lectura afirma:** Se abona durante el período de licencia legal por maternidad.

**Qué hay que decidir:** La ley no dice cuánto dura la licencia ni dónde está escrita: dice «la licencia legal correspondiente», que remite al régimen laboral aplicable, y ese régimen es distinto para el contrato de trabajo común y para casas particulares. De ahí sale cuántos meses se cobra, que es la mitad de la respuesta.

### `18730208-6973-43a2-9a11-e2c223d22e64` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-21` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Cuando el trabajador se desempeñare en más de un empleo tendrá derecho a la percepción de las prestaciones de la presente ley en el que acredite mayor antigüedad, a excepción de la asignación por maternidad, que será percibida en cada uno de ellos.

**La lectura afirma:** Con más de un empleo, esta asignación se percibe en cada uno, a diferencia de las demás prestaciones de la ley.

**Qué hay que decidir:** Es coherente con que el importe sea el sueldo: si reemplaza la remuneración, tiene que reemplazar la de cada empleo. Es la excepción a la regla general del mismo artículo, que manda cobrar en el de mayor antigüedad. No se formaliza como condición sobre la persona porque no lo es: cambia cuántas veces se liquida, y el modelo guarda un beneficio con condiciones y no un multiplicador.

### `8adfafe1-400c-4d2c-bfcb-94a3669ca073` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01). (Tope máximo de remuneración sustituido por art. 1° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del 1º de julio de 2007).

**La lectura afirma:** La exclusión por remuneración fuera del piso y el techo no alcanza a esta asignación: el artículo 3 la exceptúa expresamente.

**Qué hay que decidir:** Tiene sentido que esté exceptuada: el importe es el propio sueldo, así que un tope de ingresos que la excluyera dejaría sin cobertura a quien más gana justo cuando deja de cobrar. No se formaliza como condición porque no lo es. Queda por confirmar si la excepción alcanza también al piso mínimo o sólo al techo: el texto excluye por los dos extremos en la misma oración y exceptúa sin distinguir.

### `dea65c40-5f4e-466d-9141-5b2e627569cd` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-2` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> quedando excluidas de los incisos a) y b) del citado artículo con excepción del derecho a la percepción de la Asignación por Maternidad establecida por el inciso e) del artículo 6° de la presente ley. Facúltase al Poder Ejecutivo nacional para que dicte las normas pertinentes a efectos de adecuar y extender a las empleadas/os de dicho régimen especial estatutario las demás asignaciones familiares previstas en la presente ley. Facúltase a la Administración Federal de Ingresos Públicos (AFIP) para establecer las alícuotas correspondientes para el financiamiento de la asignación familiar por maternidad correspondiente a las empleadas del Régimen Especial de Contrato de Trabajo para el Personal de Casas Particulares. (Artículo sustituido por art. 72 inc. b) de la Ley N° 26.844 . Vigencia: de aplicación a todas las relaciones laborales alcanzadas por este régimen al momento de su entrada en vigencia)

**La lectura afirma:** Las empleadas de casas particulares quedan excluidas del subsistema contributivo salvo para esta asignación, que sí les corresponde.

**Qué hay que decidir:** Es la excepción que hace que esta lectura no pueda compartir la lista de situaciones laborales con las demás prestaciones de la ley. El mismo artículo faculta al Poder Ejecutivo a extenderles el resto de las asignaciones y a la AFIP a fijar las alícuotas que la financian: si esas normas existen hoy, no están en el corpus, y de ellas depende si la excepción sigue siendo excepción.

### `ee27700e-7907-4520-ab70-dc3dd7293797` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Acá dice algo más fuerte que en las otras prestaciones: el importe es igual al sueldo y sin embargo no es remuneración, así que no se computa para el aguinaldo ni para las indemnizaciones. Es una consecuencia que la persona no espera y que hay que poder responder.


## AR.ASIGNACION-POR-MATRIMONIO

### `8ed2dd63-0d32-4994-a919-1450ccb41006` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación por matrimonio consistirá en el pago de una suma de dinero, que se abonara en el mes en que se acredite dicho acto ante el empleador.

**La lectura afirma:** Acreditar el matrimonio ante el empleador; se abona en el mes de la acreditación.

**Qué hay que decidir:** Es la única de las cuatro que sigue acreditándose ante el empleador: las de nacimiento y adopción pasaron a ANSES con la Ley 27.611 y ésta no se tocó. Y se abona «en el mes en que se acredite», así que acreditar tarde corre el pago; si además lo hace perder, no se dice.

### `d9c9cac1-556b-4814-af24-82a8bc0103a7` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Para el goce de este beneficio se requerirá una antigüedad mínima y continuada en el empleo de seis meses.

**La lectura afirma:** Acreditar seis meses de antigüedad mínima y continuada en el empleo.

**Qué hay que decidir:** Son seis meses y no tres: es el doble que la asignación por maternidad y la prenatal, las otras dos que piden antigüedad. Como en ellas, «mínima y continuada» pide dos cosas y el árbol guarda una: qué interrumpe la continuidad no lo dice la ley.

### `f50de2d4-73bf-4bdc-b611-50dab5fae7cc` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo.

**Qué hay que decidir:** La lista es la misma que en la asignación por hijo. A diferencia de las de nacimiento y adopción, acá no hay una segunda puerta por el subsistema no contributivo: el artículo 14 septies no la nombra.

### `b1bed37d-3567-4b32-9b2a-17ca3b7dae55` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Esta asignación se abonará a los dos cónyuges cuando ambos se encuentren en las disposiciones de la presente ley.

**La lectura afirma:** Se abona a los dos cónyuges cuando ambos están comprendidos en la ley.

**Qué hay que decidir:** Es la excepción a la regla del artículo 20, que para todas las demás prestaciones manda que cobre uno solo cuando ambos progenitores están comprendidos. Acá cobran los dos, y es la única de la ley que lo dice. No se formaliza como condición sobre la persona porque no lo es: cambia cuántas veces se liquida el mismo hecho.

### `a7130b54-5600-4564-b56a-f6d92088ecd2` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).

**La lectura afirma:** Queda excluido quien percibe una remuneración fuera del piso y el techo. La asignación por matrimonio no está entre las excepciones del artículo 3.

**Qué hay que decidir:** Los dos números del texto son de 2007 y no rigen: se comparan contra parámetros y, sin valor aprobado para el período consultado, la regla devuelve desconocido. En una prestación de pago único el tope se mide sobre la remuneración de un momento —el del hecho acreditado— y la ley no dice cuál, lo que en un sueldo variable cambia el resultado.

### `42ac550e-a0b6-410c-a286-bf2ee9d167ae` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST.


## AR.ASIGNACION-POR-NACIMIENTO

### `661caf03-b1c6-4821-8400-aed9e3b5edb2` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-12` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación por nacimiento de hijo consistirá en el pago de una suma de dinero que se abonará una vez acreditado tal hecho ante la Administración Nacional de la Seguridad Social (ANSES).

**La lectura afirma:** Acreditar el nacimiento ante ANSES.

**Qué hay que decidir:** Desde la Ley 27.611 el hecho se acredita ante ANSES y no ante el empleador, que es como lo pedía el texto anterior. La nota del boletín agrega que eso rige para hechos ocurridos a partir del 24 de enero de 2021: para un nacimiento anterior, la vía es la vieja, y esta lectura no distingue las dos épocas.

### `d726cdfd-b333-4539-be90-80f3340edde5` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-septies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Las personas titulares comprendidas en el inciso c) del artículo 1º de la presente ley tendrán derecho a la percepción de las asignaciones por nacimiento y adopción establecidas en los incisos f) y g) del artículo 6º también de la presente. Para acceder a dichas prestaciones, las personas titulares deberán acreditar el hecho y/o el acto generador pertinente ante la Administración Nacional de la Seguridad Social (ANSES).

**La lectura afirma:** Los titulares del subsistema no contributivo tienen derecho a esta asignación, acreditando el hecho ante ANSES.

**Qué hay que decidir:** La otra puerta. El artículo dice «tendrán derecho», no «podrán solicitar». Queda pendiente si quien entra por acá está sujeto al tope de ingresos del artículo 3, que está escrito para el subsistema contributivo y mide una remuneración que esta persona no tiene registrada.

### `2edc4cca-868a-486c-be80-8616c102e4ec` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo.

**Qué hay que decidir:** Es una de las dos puertas de entrada, no un requisito: el artículo 14 septies abre la otra para los titulares del subsistema no contributivo. Un evaluador que exija las dos juntas dejaría afuera a todo el mundo.

### `41788ad5-8155-4897-add0-c6244b130ca9` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).

**La lectura afirma:** Queda excluido quien percibe una remuneración fuera del piso y el techo. La asignación por nacimiento no está entre las excepciones del artículo 3.

**Qué hay que decidir:** Los dos números del texto son de 2007 y no rigen: se comparan contra parámetros y, sin valor aprobado para el período consultado, la regla devuelve desconocido. En una prestación de pago único el tope se mide sobre la remuneración de un momento —el del hecho acreditado— y la ley no dice cuál, lo que en un sueldo variable cambia el resultado.

### `14d88fbd-14bc-456e-9b1e-4c61fa7f581e` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST.


## AR.ASIGNACION-PRENATAL

### `f3566c56-05b7-4c88-9638-df82439d7043` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Este estado debe ser acreditado entre el tercer y cuarto mes de embarazo, mediante certificado médico.

**La lectura afirma:** El estado de embarazo se acredita entre el tercer y el cuarto mes, mediante certificado médico.

**Qué hay que decidir:** Es la condición más filosa de esta prestación y el árbol no la captura entera. El texto abre una ventana —«entre el tercer y cuarto mes»— y no dice qué pasa fuera de ella: si acreditar en el sexto mes hace perder el derecho, lo hace perder desde el sexto mes, o no cambia nada. Escribir una condición que devuelva falso fuera de la ventana daría por perdido un derecho que la ley no dice que se pierda; escribir una que la ignore borraría la ventana. Se guarda la acreditación y la ventana queda como plazo aparte, con este mismo motivo.

### `fa3d0c47-a702-40e3-8d3f-4565a1484e4b` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La asignación prenatal consistirá en el pago de una suma equivalente a la asignación por hijo, que se abonara desde el momento de la concepción hasta el nacimiento del hijo.

**La lectura afirma:** Se abona desde el momento de la concepción hasta el nacimiento.

**Qué hay que decidir:** El derecho corre «desde el momento de la concepción», que no es un dato que nadie pueda acreditar: lo que se acredita es el estado de embarazo, entre el tercer y el cuarto mes. De la diferencia entre esas dos fechas depende si los primeros meses se pagan retroactivamente o se pierden, y el texto no lo dice.

### `cce889c6-3928-40f8-ac57-2835a2f7f55a` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Para el goce de esta asignación se requerirá una antigüedad mínima y continuada en el empleo de tres meses.

**La lectura afirma:** Acreditar una antigüedad mínima y continuada en el empleo de tres meses.

**Qué hay que decidir:** Es la misma exigencia que la asignación por maternidad y con el mismo problema: «mínima y continuada» pide dos cosas y el árbol guarda una. Qué interrumpe la continuidad no lo dice la ley. La Asignación por Embarazo del otro subsistema no pide antigüedad alguna: pide tres años de residencia legal, que mide algo completamente distinto.

### `1bd32989-64eb-4e05-8469-f73971d6d5e7` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo.

**Qué hay que decidir:** La lista no incluye a las empleadas de casas particulares: el artículo 2 les conserva sólo la asignación por maternidad y las manda al subsistema no contributivo, donde cobran la Asignación por Embarazo. Es la misma lista que en la asignación por hijo y distinta de la de maternidad, y esa diferencia es la que hay que confirmar antes de aprobar cualquiera de las tres.

### `a8bd0c92-1cb7-4db5-8204-0b22ae77a2ba` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).

**La lectura afirma:** Queda excluido quien percibe una remuneración inferior al piso o igual o superior al techo. La prenatal no está entre las excepciones del artículo 3.

**Qué hay que decidir:** Los dos números del texto son de 2007 y no rigen: se comparan contra parámetros y, sin valor aprobado para el período consultado, la regla devuelve desconocido. Y una asimetría que conviene mirar: el artículo 3 exceptúa a la asignación por maternidad del tope, y a la prenatal no, aunque las dos cubren el mismo embarazo en momentos distintos.

### `b07514be-18f7-4024-a2af-126c1fd1c63f` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-20` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> ARTICULO 20.- Cuando ambos progenitores estén comprendidos en el presente régimen, las prestaciones enumeradas en los artículos 6º y 15 serán percibidas por uno solo de ellos.

**La lectura afirma:** Cuando ambos progenitores están comprendidos en el régimen, la prestación la percibe uno solo de ellos.

**Qué hay que decidir:** La ley dice que cobra uno solo y no dice cuál. Acá pesa distinto que en la asignación por hijo: la persona gestante es una sola y el artículo no dice que la prenatal tenga que cobrarla ella.

### `883b917f-72e3-47fa-afc0-b42b16e09fe5` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-21` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Cuando el trabajador se desempeñare en más de un empleo tendrá derecho a la percepción de las prestaciones de la presente ley en el que acredite mayor antigüedad, a excepción de la asignación por maternidad, que será percibida en cada uno de ellos.

**La lectura afirma:** Con más de un empleo, la prestación se percibe en el que acredite mayor antigüedad.

**Qué hay que decidir:** Se cruza con la antigüedad mínima de tres meses del artículo 9: si el empleo de mayor antigüedad tiene tres meses pero el otro no, o al revés, cuál es el que cuenta para el requisito no lo dice la ley.

### `36bc0bd6-2656-4309-ac39-a473916fc155` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST.


## AR.AUH

### `4b69cac3-d5b5-403e-9921-50397e7306fa` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Desde los CINCO (5) años de edad y hasta los DIECIOCHO (18) años, deberá acreditarse además la concurrencia de las niñas, los niños y adolescentes obligatoriamente a establecimientos educativos públicos.

**La lectura afirma:** Desde los cinco y hasta los dieciocho años se acredita además la concurrencia obligatoria a establecimientos educativos públicos.

**Qué hay que decidir:** El texto vigente dice «establecimientos educativos públicos», y el campo lo refleja tal cual. Si en la práctica la escolaridad en gestión privada también acredita, eso no surge de esta norma sino de la reglamentación, que no está en el corpus. Ampliarlo por cuenta propia sería servir como derecho algo que el texto no dice; restringirlo sin verificar dejaría afuera a quien sí cumple.

### `243fe434-09db-439a-b56c-0760279b09b5` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a. Que la niña, el niño, adolescente y/o la persona con discapacidad sea argentino o argentina nativo o nativa, naturalizado o naturalizada o por opción. Cuando la niña, el niño, adolescente y/o la persona con discapacidad y sus progenitores o sus progenitoras o las personas que los o las tengan a cargo sean extranjeros o extranjeras, deberán acreditar tanto la niña, el niño, adolescente y/o la persona con discapacidad como el o la titular que percibirá la Asignación, DOS (2) años de residencia legal en el país.

**La lectura afirma:** El causante es argentino nativo, naturalizado o por opción; si tanto el causante como quien lo tiene a cargo son extranjeros, ambos acreditan dos años de residencia legal.

**Qué hay que decidir:** El texto condiciona los dos años a que el causante «y sus progenitores o sus progenitoras o las personas que los o las tengan a cargo sean extranjeros»: en su letra, la exigencia aparece cuando ambos son extranjeros, y no dice qué pasa cuando el causante es argentino y quien lo tiene a cargo no. Se formalizó la letra —causante argentino alcanza— y no la lectura más restrictiva, porque exigir de más deja gente afuera de un derecho. La diferencia hay que resolverla con criterio jurídico, no con la que suene más prolija.

### `b567d80d-cc45-4d93-826f-f998c39baaf3` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> b. Acreditar la identidad del o de la titular del beneficio y de la niña, del niño, adolescente y/o persona con discapacidad, mediante Documento Nacional de Identidad.

**La lectura afirma:** Titular y causante acreditan identidad con Documento Nacional de Identidad.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `7da487fc-02cc-4f2e-b16f-5bc4fc566005` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> c. Acreditar que la persona que percibirá el beneficio tiene a su cargo a la niña, al niño, adolescente y/o persona con discapacidad, en función de las disposiciones del Código Civil y Comercial de la Nación y de conformidad con la documentación que la ADMINISTRACIÓN NACIONAL DE LA SEGURIDAD SOCIAL (ANSES) disponga a estos fines.

**La lectura afirma:** El titular tiene a su cargo al causante, según el Código Civil y Comercial y la documentación que ANSES disponga.

**Qué hay que decidir:** «A cargo» remite al Código Civil y Comercial y a documentación que fija ANSES por vía reglamentaria. El campo guarda si el vínculo de cuidado está acreditado, no reconstruye el criterio: decidir por cuenta propia qué convivencia o qué guarda de hecho cuenta como «a cargo» sería resolver un conflicto jurídico con una heurística.

### `8bbe303c-618e-41d3-ba1e-cd7c40030935` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> d. La acreditación de la condición de discapacidad será determinada en los términos del artículo 2º de la Ley Nº 22.431, certificada por autoridad competente.

**La lectura afirma:** Cuando se invoca discapacidad, se acredita en los términos del artículo 2 de la Ley 22.431 y con certificación de autoridad competente.

**Qué hay que decidir:** El requisito solo muerde cuando se invoca la discapacidad —para levantar el límite de edad o para acceder al monto del inciso b) del artículo 18—. Formalizarlo como condición general haría que un trámite sin discapacidad invocada fallara por no acreditar una discapacidad que nadie alegó. La condición «se invoca» no está en el texto de la ley: es la forma de acotar el alcance del requisito, y por eso queda a revisión.

### `217eb176-be97-44e4-b32b-aa50977d36ec` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> e. Hasta los CUATRO (4) años de edad -inclusive-, deberá acreditarse el cumplimiento de los controles sanitarios y del plan de vacunación obligatorio.

**La lectura afirma:** Hasta los cuatro años inclusive se acredita el cumplimiento de los controles sanitarios y del plan de vacunación obligatorio.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `217f7e72-d398-455f-aa66-6d860603c418` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-ter` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> f. Acreditar que el o la titular del beneficio y la niña, el niño, adolescente y/o persona con discapacidad residen en el país.

**La lectura afirma:** Titular y causante residen en el país.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `64420946-3954-49ce-b349-8c756b188785` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-bis` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> por cada niña, niño y/o adolescente menor de DIECIOCHO (18) años que se encuentre a su cargo, o sin límite de edad cuando se trate de una persona con discapacidad; en ambos casos

**La lectura afirma:** El causante es menor de dieciocho años, o de cualquier edad si es persona con discapacidad.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `a4809bd7-3fb9-4de3-abf3-c36b80d7e336` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-bis` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> que se abonará a uno solo o una sola de los padres o de las madres, tutor o tutora, curador o curadora o pariente por consanguinidad hasta el tercer grado

**La lectura afirma:** Quien percibe es padre, madre, tutor, tutora, curador, curadora o pariente por consanguinidad hasta el tercer grado.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `163f4ffc-4bce-4532-86f7-739889c99533` · COMPATIBILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-quater/parrafo-52` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> La percepción de esta asignación no será incompatible con la Asignación Universal por Hijo para Protección Social por cada menor de DIECIOCHO (18) años, o sin límite de edad cuando se trate de un discapacitado, a cargo de la mujer embarazada.

**La lectura afirma:** Percibir la Asignación por Embarazo para Protección Social no es incompatible con percibir la AUH por cada causante a cargo.

**Qué hay que decidir:** La compatibilidad es una afirmación de la ley, no una condición que la persona cumpla o deje de cumplir, y meterla como hecho a evaluar la vuelve una pregunta que no tiene sentido hacerle a nadie. Está acá porque una regla de compatibilidad omitida se lee como incompatibilidad, que es peor; cómo se representa una compatibilidad declarada es la decisión que la revisión tiene que tomar.

### `183585a6-56ec-4004-843c-f13a8d144ea8` · COMPATIBILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-septies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Las personas titulares comprendidas en el inciso c) del artículo 1º de la presente ley tendrán derecho a la percepción de las asignaciones por nacimiento y adopción establecidas en los incisos f) y g) del artículo 6º también de la presente. Para acceder a dichas prestaciones, las personas titulares deberán acreditar el hecho y/o el acto generador pertinente ante la Administración Nacional de la Seguridad Social (ANSES).

**La lectura afirma:** Los titulares del subsistema no contributivo tienen derecho a las asignaciones por nacimiento y adopción, acreditando el hecho o acto generador ante ANSES.

**Qué hay que decidir:** Mismo caso que la ayuda escolar: es un derecho a otras dos prestaciones, cada una con su monto y su acreditación. Queda declarado para que no se pierda, no formalizado como si esta lectura pudiera liquidarlas.

### `8a40d591-b367-4c06-9d18-fdda3e19b3e0` · COMPATIBILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-sexies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Los titulares de la Asignación Universal por Hijo para Protección Social establecida en el artículo 1°, inciso c) de la presente Ley tendrán derecho a la Asignación por Ayuda Escolar Anual prevista en el artículo 6°, inciso d) y definida por el artículo 10 de esta ley.

**La lectura afirma:** Los titulares de la AUH tienen derecho a la Asignación por Ayuda Escolar Anual del artículo 6 inciso d).

**Qué hay que decidir:** Es un derecho a otra prestación, no una condición de esta. Formalizarlo como regla de la AUH la deja donde se puede encontrar, pero la Ayuda Escolar Anual merece su propia lectura curada con su propio monto y su propia evidencia. Hasta que exista, esto informa que el derecho está y no lo liquida.

### `bcdd9337-31a1-40ac-9ba4-2c2b04449d64` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3/parrafo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos del beneficio previsto en el artículo 1° inciso c) de la presente los trabajadores que se desempeñen en la economía informal, que perciban una remuneración superior al salario mínimo, vital y móvil.

**La lectura afirma:** Queda excluido quien se desempeñe en la economía informal y perciba una remuneración superior al salario mínimo, vital y móvil.

**Qué hay que decidir:** La exclusión pide dos cosas a la vez: informalidad y remuneración sobre el salario mínimo. Quien trabaja en la economía informal no tiene una remuneración registrada contra la cual medir, así que el dato con el que se evalúa es declarado y no verificable contra un recibo. Además el umbral es un parámetro que se actualiza fuera de esta ley: mientras no tenga valor aprobado para el período que se consulta, la regla devuelve desconocido en vez de excluir a alguien con un tope viejo.

### `3fd738c8-674d-45da-a58e-d2d565763f5c` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-bis` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> siempre que no estuviere empleado o empleada, emancipado o emancipada o percibiendo alguna de las prestaciones previstas en la presente Ley.

**La lectura afirma:** El causante no está empleado, ni emancipado, ni percibe otra prestación de esta misma ley.

**Qué hay que decidir:** La oración admite dos lecturas: que las tres condiciones se midan sobre el causante, o que «percibiendo alguna de las prestaciones» se refiera al titular. Se leyó sobre el causante porque es el sujeto de la oración y porque el artículo 14 sexies da a los titulares de AUH derecho a otra prestación de esta misma ley, lo que haría contradictoria la otra lectura. Queda dicho porque la diferencia decide accesos.

### `402b68d4-60ec-4e5a-bf06-5641dfa25f15` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-20` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> ARTICULO 20.- Cuando ambos progenitores estén comprendidos en el presente régimen, las prestaciones enumeradas en los artículos 6º y 15 serán percibidas por uno solo de ellos.

**La lectura afirma:** Cuando ambos progenitores están comprendidos en el régimen, la prestación la percibe uno solo de ellos.

**Qué hay que decidir:** La ley dice que cobra uno solo y no dice cuál. No hay AST porque no hay regla que formalizar: elegir un criterio —la madre, quien tenga mayor antigüedad, quien solicite primero— sería inventar la parte que el legislador no escribió, y esa elección decide quién cobra. Se guarda el texto literal y queda para la revisión.

### `a8817538-a612-47c3-a293-403a7022c759` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-22` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> serán considerados como hijos los menores o personas con discapacidad cuya guarda, tenencia o tutela haya sido acordada al trabajador por autoridad judicial o administrativa competente. En tales supuestos, los respectivos padres no tendrán, por ese hijo, derecho al cobro de las mencionadas asignaciones.

**La lectura afirma:** Cuando la guarda, tenencia o tutela fue acordada por autoridad judicial o administrativa, el causante cuenta como hijo de quien la tiene y los padres pierden por ese hijo el derecho al cobro.

**Qué hay que decidir:** El artículo 22 nombra las asignaciones por hijo, por hijo con discapacidad y por ayuda escolar anual, y no nombra la AUH, que se incorporó trece años después. Aplicarla por analogía resolvería un conflicto de titularidad —quién cobra, el progenitor o el guardador— que el texto no resolvió para esta prestación. Queda el texto y la pregunta.


## AR.AYUDA-ESCOLAR-ANUAL

### `2260b608-a623-4513-be0b-f3b1c1a6959d` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-10` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Esta asignación se abonará por cada hijo que concurra regularmente a establecimientos de enseñanza básica y polimodal o bien, cualquiera sea su edad, si concurre a establecimientos oficiales o privados donde se imparta educación diferencial.

**La lectura afirma:** El hijo concurre regularmente a enseñanza básica y polimodal, o a educación diferencial cualquiera sea su edad.

**Qué hay que decidir:** «Enseñanza básica y polimodal» son los niveles de la Ley Federal de Educación de 1993, derogada por la Ley 26.206 en 2006, que renombró los niveles a primario y secundario. La norma no se actualizó y el campo la refleja tal cual: traducir los nombres acá sería decidir por analogía qué nivel corresponde a cuál, y de eso depende si un chico de sala de cinco entra o no. La vía de educación diferencial sí es explícita en que no mira la edad.

### `aece9182-4f78-40d2-890c-6a2c3999fa69` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-sexies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Los titulares de la Asignación Universal por Hijo para Protección Social establecida en el artículo 1°, inciso c) de la presente Ley tendrán derecho a la Asignación por Ayuda Escolar Anual prevista en el artículo 6°, inciso d) y definida por el artículo 10 de esta ley.

**La lectura afirma:** Los titulares de la Asignación Universal por Hijo tienen derecho a esta ayuda escolar.

**Qué hay que decidir:** La otra puerta de entrada. El artículo dice «tendrán derecho», no «podrán solicitar»: es una extensión del derecho y no una posibilidad sujeta a evaluación. Queda pendiente si quien entra por acá tiene que acreditar la concurrencia escolar del artículo 10 o si le alcanza con la escolaridad que ya acredita para la AUH, que es la misma información pedida dos veces.

### `18bcada6-6b8c-4a96-893f-a709f5fe8c0d` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-1/inciso-a-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los trabajadores que presten servicios remunerados en relación de dependencia en la actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se financiará con los recursos previstos en el artículo 5° de la presente ley.

**La lectura afirma:** Estar comprendido en el subsistema contributivo.

**Qué hay que decidir:** Es una de las dos puertas de entrada, no un requisito: el artículo 14 sexies abre la otra para los titulares del subsistema no contributivo. Escritas como dos reglas de aplicabilidad separadas, un evaluador que las exija juntas dejaría afuera a todo el mundo. Cómo se representa una disyunción entre dos vías de acceso es la decisión de fondo que esta lectura deja abierta.

### `07e7153c-d60b-4485-ac05-9ed587b7145c` · EXCEPCION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-22` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> A los fines de otorgar las asignaciones por hijo, hijo con discapacidad y ayuda escolar anual, serán considerados como hijos los menores o personas con discapacidad cuya guarda, tenencia o tutela haya sido acordada al trabajador por autoridad judicial o administrativa competente. En tales supuestos, los respectivos padres no tendrán, por ese hijo, derecho al cobro de las mencionadas asignaciones.

**La lectura afirma:** Cuentan como hijos los menores o personas con discapacidad cuya guarda, tenencia o tutela fue acordada al trabajador; en ese caso los padres no cobran por ese hijo.

**Qué hay que decidir:** El artículo nombra expresamente a la ayuda escolar anual, así que acá aplica. Amplía qué cuenta como hijo y a la vez saca el derecho a los padres: son dos efectos y el árbol alcanza el primero.

### `c8ba5d04-efad-4859-aaa1-b5c0228eddae` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Quedan excluidos de las prestaciones de esta ley, con excepción de las asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01). (Tope máximo de remuneración sustituido por art. 1° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del 1º de julio de 2007).

**La lectura afirma:** Esta asignación no está entre las excepciones del artículo 3: la exclusión por remuneración fuera del piso y el techo la alcanza.

**Qué hay que decidir:** Se guarda la exclusión precisamente porque la ayuda escolar **no** está exceptuada: el artículo 3 exceptúa maternidad e hijo con discapacidad y a ninguna otra. Omitirla acá haría que esta prestación pareciera fuera del alcance del tope, que es lo contrario. Qué pasa con quien entra por el artículo 14 sexies —titular de la AUH, sin remuneración registrada contra la cual medir un tope— es la pregunta que hay que resolver: el tope del artículo 3 está escrito para el subsistema contributivo.

### `84e012f5-8b31-4ead-8700-b14421ce93f9` · PRIORIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-20` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> ARTICULO 20.- Cuando ambos progenitores estén comprendidos en el presente régimen, las prestaciones enumeradas en los artículos 6º y 15 serán percibidas por uno solo de ellos.

**La lectura afirma:** Cuando ambos progenitores están comprendidos en el régimen, la prestación la percibe uno solo de ellos.

**Qué hay que decidir:** La ley dice que cobra uno solo y no dice cuál. Elegir un criterio sería inventar la parte que el legislador no escribió.

### `97129484-32ed-4d8e-96dc-28063ff80f63` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST. Se conserva porque es lo que hay que poder responder cuando alguien pregunta si le pueden descontar la ayuda escolar por una deuda.


## AR.CUIDADO-DE-SALUD-INTEGRAL

### `3154548c-8dbd-43f8-aeee-0fedc5ab9e87` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-octies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> por cada niño o niña menor de tres (3) años de edad que se encuentre a su cargo

**La lectura afirma:** Tener a cargo un niño o niña menor de tres años.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `2c260e48-625f-43c8-979e-7bfe386c5858` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-octies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> siempre que acrediten el cumplimiento del plan de vacunación y control sanitario, de conformidad con los requisitos que la Administración Nacional de la Seguridad Social (ANSES) establecerá a tales efectos.

**La lectura afirma:** Acreditar el cumplimiento del plan de vacunación y del control sanitario, según los requisitos que establezca ANSES.

**Qué hay que decidir:** Los requisitos concretos los fija ANSES y no están en el corpus. Es además la misma acreditación que la Asignación Universal por Hijo pide para liberar su veinte por ciento reservado hasta los cuatro años: si es el mismo trámite o son dos, no sale de esta ley, y de eso depende que a una persona se le pida dos veces lo mismo.

### `25155962-fb24-4b30-b42d-1f13fd762a4f` · APLICABILIDAD

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-14-octies` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> siempre que hayan tenido derecho al cobro de la prestación establecida en el inciso i) del artículo 6º de la presente dentro del año calendario

**La lectura afirma:** Haber tenido derecho al cobro de la Asignación Universal por Hijo dentro del año calendario.

**Qué hay que decidir:** Es la única condición de esta ley que exige otro beneficio, y el texto elige con cuidado las palabras: «hayan tenido derecho al cobro», no «hayan cobrado». Alguien a quien le correspondía la Asignación Universal por Hijo y no la percibió —porque no la tramitó, porque se la liquidaron mal— tuvo el derecho igual. Escribir el campo como «cobró» invertiría el sentido y dejaría afuera justo a quien ya quedó afuera una vez. El campo guarda el derecho y no el cobro, y de cómo se determine ese derecho depende todo lo demás.

### `3e7920d7-b60b-47f6-88e1-f955805a9678` · EXCLUSION

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-3/parrafo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan excluidos del beneficio previsto en el artículo 1° inciso c) de la presente los trabajadores que se desempeñen en la economía informal, que perciban una remuneración superior al salario mínimo, vital y móvil.

**La lectura afirma:** Queda excluido quien se desempeñe en la economía informal y perciba una remuneración superior al salario mínimo, vital y móvil.

**Qué hay que decidir:** La exclusión es del inciso c) del artículo 1, el subsistema no contributivo entero. Se guarda acá porque el requisito de haber tenido derecho a la Asignación Universal por Hijo ubica a esta prestación en ese subsistema; si la revisión decide que el encabezado del artículo 14 octies la extiende a todo el artículo 1, esta exclusión deja de aplicar a la parte contributiva y hay que revisarla.

### `a3114479-a17e-4cef-90b5-d297fe8119c8` · SALVAGUARDA

**Norma:** LEY 24714/1996 · **Unidad:** `articulo-23` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Las Asignaciones Familiares dispuestas en la presente ley son inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a terceros por derecho alguno.

**La lectura afirma:** La asignación es inembargable, no constituye remuneración y no puede ser enajenada ni afectada a terceros.

**Qué hay que decidir:** Es una protección sobre lo cobrado y no una condición de acceso, así que no tiene AST.


## CABA.APOYO-VULNERABILIDAD-HABITACIONAL

### `7eee1c07-1415-4d20-ab7d-c478e547204d` · APLICABILIDAD

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-6/inciso-a-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) Acreditar identidad y residencia en la Ciudad Autónoma de Buenos Aires con una antigüedad mínima de dos (2) años.

**La lectura afirma:** Antigüedad de residencia en CABA de al menos dos años.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `72684e6c-bdef-4cbb-ae10-1e3c5512d308` · APLICABILIDAD

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-6/inciso-b-12` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> b) No alcanzar el ingreso total de las familias, según su conformación, para cubrir la Canasta Básica Total (CBT) fijada por el Instituto Nacional de Estadísticas y Censos (INDEC), u organismo que en el futuro lo reemplace;

**La lectura afirma:** El ingreso total del hogar no alcanza a cubrir la Canasta Básica Total del INDEC correspondiente a su conformación.

**Qué hay que decidir:** La CBT varía según la conformación del hogar y el parámetro cargado no está segmentado por composición. Comparar contra un valor único daría por debajo o por encima del umbral a hogares que no corresponden.

### `e586b5a4-ee3f-4baa-8255-f0d2e1b77956` · CESE

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-7` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> La continuidad de la prestación estará sujeta al cumplimiento de las corresponsabilidades definidas por la reglamentación.

**La lectura afirma:** El incumplimiento de las corresponsabilidades puede interrumpir la continuidad de la prestación.

**Qué hay que decidir:** La ley sujeta la continuidad a corresponsabilidades que define la reglamentación, y esa norma no está en el corpus. Cuáles son, cómo se acreditan y qué consecuencia tiene incumplirlas —suspensión, cese o revocación— no surge del texto: son tres efectos distintos y la ley no elige.

### `83a25fa7-697a-46e2-b8a3-345828348bde` · COMPATIBILIDAD

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-5/parrafo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> El ejercicio de la opción por parte del beneficiario de percibir la prestación económica alternativa en una (1) cuota única por solución habitacional estable resulta excluyente de la percepción de toda otra suma de dinero dispuesta en la presente Ley por el término que fije la reglamentación.

**La lectura afirma:** Optar por el pago único excluye percibir otras sumas de esta Ley durante el término que fije la reglamentación.

**Qué hay que decidir:** El término de la incompatibilidad lo fija la reglamentación, que no está en el corpus. Sin ese plazo no se puede decir hasta cuándo dura la exclusión, y decir «para siempre» o «por un año» serían las dos invenciones posibles.

### `ed3fdb29-4891-4a1b-b593-cd42332add6f` · EXCEPCION

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-6/inciso-a-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Quedan exceptuadas de este requisito las personas víctimas de trata de personas o violencia de género, debidamente acreditadas por los organismos competentes.

**La lectura afirma:** La antigüedad de residencia no se exige a víctimas de trata o de violencia de género acreditadas por el organismo competente.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `3b66d2cb-7c7f-47d8-a624-1d0757f3a408` · EXCLUSION

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-6/inciso-c-13` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> c) No ser titular de bienes inmuebles

**La lectura afirma:** Ser titular de un bien inmueble excluye del programa.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `649e748e-014a-4833-a76c-68bc40db17b4` · EXCLUSION

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-6/inciso-c-13` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> ni percibir otros subsidios económicos de carácter habitacional de origen nacional, provincial o municipal.

**La lectura afirma:** Percibir otro subsidio habitacional de cualquier jurisdicción excluye del programa.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `5eb32c53-82af-4b91-85e7-e42bb009e5c8` · SALVAGUARDA

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> En casos de urgencia social o situación de calle efectiva, la Autoridad de Aplicación podrá disponer el ingreso provisorio al programa y liquidar la primera cuota de la prestación como pago de emergencia, aun cuando el hogar no cuente con la totalidad de la documentación requerida.

**La lectura afirma:** La urgencia social o la situación de calle efectiva habilitan el ingreso provisorio aunque falte documentación. Nunca excluye: siempre se informa.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `ec0d3afa-a903-4f22-ace4-25408fd96b3b` · SUBSANACION

**Norma:** LEY 6935/2025 · **Unidad:** `articulo-6/parrafo-15` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> La reglamentación podrá establecer mecanismos de interoperabilidad de datos para eximir a los solicitantes de presentar documentación que ya obrare en poder del Estado, y mecanismos flexibles para la acreditación de requisitos en casos de extrema vulnerabilidad o falta de documentación, admitiendo el ingreso provisorio.

**La lectura afirma:** La falta de documentación admite acreditación flexible e ingreso provisorio; no es por sí sola un motivo de rechazo.

**Qué hay que decidir:** La ley habilita el mecanismo y lo remite a la reglamentación, que no está en el corpus. No se puede formalizar qué documentación se subsana ni en qué plazo, y afirmar que algo es subsanable sin saber el plazo puede hacer que alguien pierda el suyo.


## CABA.BECA-COMEDOR-ESCOLAR

### `bca2acaf-2e83-46ea-a0f6-046134448a53` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-39` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> A los alumnos, que sean hijos de beneficiarios de Programas Alimentarlos Nacionales, Provinciales o Municipales.

**La lectura afirma:** Corresponde beca total al alumno hijo de beneficiarios de programas alimentarios nacionales, provinciales o municipales.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `a5f757fc-3cce-4339-b06f-7d82749a9ed8` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-40` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos a cargo de jubilados y/o pensionados que perciban un haber hasta dos sueldos mínimos.

**La lectura afirma:** Corresponde beca total al alumno a cargo de jubilados o pensionados cuyo haber llega hasta dos sueldos mínimos.

**Qué hay que decidir:** El mismo parámetro sin definir. Además el texto dice «dos sueldos mínimos» sin el número entre paréntesis que sí usa en las otras causales: es la misma cifra, y se deja anotado porque en una norma consolidada de 1989 una diferencia de redacción puede ser un error de transcripción o una diferencia real.

### `70e11e62-d38e-4f15-9e3c-defb5ae840d7` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-42` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos cuyas familias perciban un haber hasta cuatro (4) sueldos mínimos.

**La lectura afirma:** Corresponde media beca al alumno cuya familia percibe un haber de hasta cuatro sueldos mínimos.

**Qué hay que decidir:** El mismo parámetro sin definir. Y el modelo guarda un beneficio con condiciones, no dos niveles del mismo beneficio: esta regla y las de beca total conviven en la misma lista sin que nada diga que una da el cien por ciento y otra la mitad. Cómo se representa esa diferencia es lo que la revisión tiene que decidir; mientras tanto está en la descripción de cada regla y en el texto literal.

### `1ae41bf3-ce3a-4d33-bb6b-502993a6d580` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-40` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos cuyas familias tengan ingresos hasta dos (2) sueldos mínimos.

**La lectura afirma:** Corresponde beca total al alumno cuya familia tiene ingresos de hasta dos sueldos mínimos.

**Qué hay que decidir:** «Sueldo mínimo» no está definido en la ordenanza. En 1989 la Municipalidad tenía su propio sueldo mínimo, distinto del salario mínimo, vital y móvil nacional; hoy el primero no existe con ese nombre. Se creó un parámetro propio en vez de apuntar al SMVM: mapearlos sería decidir, sin que lo diga ninguna norma, cuál es el umbral que separa a quien come gratis de quien paga media ración. Mientras el parámetro no tenga valor aprobado, la regla devuelve desconocido.

### `a3dbea4a-f0d0-4da3-9506-0c8bc4d5f5c1` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-42` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos discapacitados o bajo tratamiento médico prolongado.

**La lectura afirma:** Corresponde media beca al alumno con discapacidad o bajo tratamiento médico prolongado.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `2ea70d0e-07d5-4560-a595-804fb8aa6e94` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-42` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos hijos de personal docente o no docente de la Escuela.

**La lectura afirma:** Corresponde media beca al alumno hijo de personal docente o no docente de la escuela.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `3c70bcea-dde5-42e4-a3e0-1292edf5d14c` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-40` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos que estén a cargo de una sola persona (padre, madre, tutor o encargado) cuyo ingreso mensual sea hasta dos (2) sueldos mínimos.

**La lectura afirma:** Corresponde beca total al alumno a cargo de una sola persona cuyo ingreso mensual llega hasta dos sueldos mínimos.

**Qué hay que decidir:** Mismo parámetro sin definir que la causal anterior, y una diferencia que no hay que perder: acá el umbral se mide sobre el ingreso de la persona a cargo y allá sobre el de la familia. Unificarlos sería más prolijo y cambiaría quién entra.

### `73d31086-6703-41f1-97ab-7647a34946bc` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-42` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos que provengan de familias numerosas, con hermanos en edad escolar cuando hicieran uso del comedor dos o más hermanos.

**La lectura afirma:** Corresponde media beca al alumno de familia numerosa cuando dos o más hermanos en edad escolar usan el comedor.

**Qué hay que decidir:** La causal pide dos cosas —familia numerosa y dos o más hermanos usando el comedor— y no define «numerosa». Se formalizó la parte que el texto sí cuantifica; tomar «numerosa» como sinónimo de «dos o más hermanos» es una lectura posible y no la única.

### `aa61f3e8-479d-4c30-b8b0-6c21a174ad3f` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-40` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Alumnos que sean hijos de ex combatientes de Malvinas.

**La lectura afirma:** Corresponde beca total al alumno hijo de ex combatientes de Malvinas.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `71b11773-8127-4e7f-ab2c-8fbc3d80dcc3` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-2/parrafo-5` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Cuando el grupo familiar esté integrado por más de un niño que concurra a la escuela pública, el tope de ingresos fijado para determinar la modalidad de la beca a otorgarse de conformidad a lo dispuesto en el presente artículo, se incrementará en un quince por ciento (15%) por cada niño que se sume.

**La lectura afirma:** El tope de ingresos sube un 15% por cada niño del grupo familiar que concurra a la escuela pública además del primero.

**Qué hay que decidir:** No es una condición sobre la persona: modifica el umbral de las dos reglas anteriores. El AST del modelo compara un campo contra un parámetro y no sabe correr el parámetro según cuántos hermanos van a la escuela pública, así que formalizarla exigiría o un parámetro por cantidad de niños o un campo con el tope ya calculado, y ninguna de las dos cosas la dice la ley. Se deja escrita porque omitirla dejaría afuera a familias que la ley incluye: con dos hijos en la escuela pública el tope de la beca total no es 2,5 sueldos, es 2,875.

### `c58666bc-3eaa-41a1-b312-e23808193953` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-10` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> El Departamento Ejecutivo otorgará a los alumnos que concurran a las escuelas dependientes de la comuna, becas totales o medias becas para afrontar los gastos de Comedor, Refrigerio y Vianda,

**La lectura afirma:** Concurrir a una escuela dependiente de la Ciudad.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `2aede62d-ee78-4b79-8265-d87f68b84fa7` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-1/articulo-10[sustitutivo:2]` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> El Poder Ejecutivo brindará un servicio de desayuno o de merienda en forma indistinta y gratuita a todos los alumnos que lo consuman en las escuelas dependientes del Gobierno de la Ciudad incorporadas al respectivo programa.

**La lectura afirma:** El desayuno o la merienda es gratuito para todo alumno que lo consuma en una escuela incorporada al programa, sin beca y sin condición de ingresos.

**Qué hay que decidir:** Es la regla que más cambia lo que alguien recibe como respuesta y la que más fácil se pierde: el desayuno o la merienda no se piden, no se becan y no miran el ingreso de nadie. La condición se escribió sobre la única cualidad que el texto exige del alumno —concurrir a una escuela de la Ciudad— y le falta la otra mitad, que la escuela esté «incorporada al respectivo programa»: eso no es una cualidad de la persona sino de la escuela, y el corpus no tiene la lista de escuelas incorporadas. Hasta que esté, la regla afirma de más para quien va a una escuela que no está en el programa.

### `fba97563-aa5a-4803-8c0e-0f28f605885b` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-2/parrafo-6` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> En caso que un integrante del grupo familiar se encuentre afectado por una enfermedad crónica que requiera tratamiento continuo o por períodos prolongados, los gastos derivados de dicho tratamiento podrán deducirse del monto del ingreso mensual del grupo familiar que se toma como base para el otorgamiento de becas totales y medias becas.

**La lectura afirma:** Los gastos de tratamiento de un integrante del grupo familiar con enfermedad crónica pueden deducirse del ingreso que se compara con el tope.

**Qué hay que decidir:** Tampoco es una condición sobre la persona: cambia el número que se compara, no el umbral. Y dice «podrán deducirse», no «se deducirán», así que ni siquiera es automática. Formalizarla como si el ingreso computable fuera el ingreso menos los gastos de tratamiento convertiría una facultad de la Comisión en un derecho. Queda declarada porque una respuesta que la omita le dice «no calificás» a una familia que con la deducción sí calificaría.

### `ae96fee2-7af3-45c3-be0d-3de37d56c738` · APLICABILIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-16/parrafo-43` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Los datos del solicitante, en los que se constata la situación socioeconómica familiar o particular, que le permita acceder a la beca serán suministrados por simple �declaración Jurada�, pudiendo la Comisión de Becas solicitar otros datos en aquellos casos en que lo considere necesario.

**La lectura afirma:** La situación socioeconómica se acredita por simple declaración jurada, y la Comisión de Becas puede pedir otros datos si lo considera necesario.

**Qué hay que decidir:** No es una condición de acceso sino la vía de acreditación de todas las demás, y una vía que baja la barrera en vez de subirla: la ordenanza no pide documentación probatoria. Formalizarla como requisito la convertiría en un trámite más. Queda declarada porque, omitida, alguien podría suponer que hay que probar los ingresos.

### `8350a46c-6a5b-4787-ac23-528014e8e5b3` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-2/parrafo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Los datos del solicitante, en los que se constate la situación socioeconómica familiar y particular que le permita acceder a la beca serán suministrados por declaración jurada, pudiendo la Comisión de Becas solicitar otros datos en aquellos casos en que lo considere necesario.

**La lectura afirma:** La situación socioeconómica se acredita por declaración jurada, y la Comisión de Becas puede pedir otros datos si lo considera necesario.

**Qué hay que decidir:** No es una condición de acceso sino la vía de acreditación de todas las demás, y una que baja la barrera: la ley no pide documentación probatoria. Se conserva por la misma razón que en la ordenanza —omitida, alguien podría suponer que hay que probar los ingresos— y se declara aparte porque el texto no es el mismo: la ordenanza decía «simple declaración jurada» y esta ley dice «declaración jurada». Si esa palabra cambia algo es una lectura jurídica, no una diferencia de transcripción que se pueda unificar al cargar.

### `7d1fb945-34e3-466f-8861-c2666fb77d01` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-1/articulo-10[sustitutivo:2]` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Para los asistentes a jardines maternales o a escuelas o colegios con régimen de internado, el beneficio que se otorgue comprenderá también el pago del gasto que insuma el servicio de cena

**La lectura afirma:** En jardines maternales y en escuelas o colegios con internado la beca cubre además la cena.

**Qué hay que decidir:** No decide si alguien accede a la beca sino qué comidas cubre la beca que ya le corresponde, y el modelo guarda un beneficio con condiciones, no un beneficio con alcances variables. La condición está escrita sobre lo que el texto sí distingue —dónde asiste el alumno— y qué representa ese verdadero es lo que la revisión tiene que decidir: hoy leída como aplicabilidad diría que solo acceden los de internado, que es lo contrario de lo que la ley dice.

### `912065ac-4e5b-4c89-a4c8-7b1c870ec6c5` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-1/articulo-10[sustitutivo:2]` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> el Poder Ejecutivo otorgará becas totales o medias becas, cuyas características y cantidades fijará anualmente la Legislatura de la Ciudad

**La lectura afirma:** Las características y la cantidad de becas las fija la Legislatura cada año.

**Qué hay que decidir:** No es una condición que cumpla una persona: es un cupo anual decidido por otro poder y fuera del corpus. Formalizarla como condición de acceso sería inventar un requisito; omitirla sería peor, porque haría creer que cumplir el artículo 16 alcanza para tener la beca cuando el número de becas del año puede no alcanzar. Queda declarada para que la respuesta no prometa lo que depende de un cupo.

### `fd99df2d-5585-4615-b562-e8136af5bb61` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-2/articulo-16[sustitutivo:4]` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> otorgará becas totales a los mismos cuando la totalidad de los ingresos mensuales del grupo familiar al que pertenecen no supere el equivalente al sueldo mínimo fijado en el convenio para empleados de comercio, multiplicado por 2,5.

**La lectura afirma:** Corresponde beca total cuando el ingreso mensual total del grupo familiar no supera 2,5 sueldos mínimos del convenio de empleados de comercio.

**Qué hay que decidir:** El umbral está definido —el sueldo mínimo del convenio de empleados de comercio— y aun así el parámetro entra sin valor: es un piso de convenio colectivo que se renegocia y que ninguna fuente del corpus publica. Es un parámetro distinto del «sueldo mínimo» de la ordenanza que esta ley sustituye, y por eso tiene código propio: unificarlos sería decidir que son lo mismo, que es justamente lo que la ordenanza no decía. Mientras no tenga valor aprobado, la regla devuelve desconocido.

### `efc8e291-c4e4-484d-82d1-da065efc37ab` · APLICABILIDAD

**Norma:** LEY 547/2001 · **Unidad:** `articulo-2/articulo-16[sustitutivo:4]` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> se otorgarán medias becas cuando los referidos ingresos superen el tope establecido para las becas totales sin llegar a exceder el equivalente al sueldo mínimo fijado en el convenio para empleados de comercio, multiplicado por 3,5.

**La lectura afirma:** Corresponde media beca cuando el ingreso del grupo familiar pasa el tope de la beca total y no supera 3,5 sueldos mínimos del convenio de empleados de comercio.

**Qué hay que decidir:** El mismo parámetro sin valor, y la misma decisión de fondo que la lectura de la ordenanza dejó abierta: el modelo guarda un beneficio con condiciones y acá conviven la condición de la beca entera y la de la mitad, sin que nada en la estructura diga que dan resultados distintos. La diferencia está en la descripción y en el texto literal de cada regla. Además el tramo se escribió como «mayor que 2,5 y menor o igual que 3,5» porque el texto dice «superen el tope» y «sin llegar a exceder»: si la revisión leyera el tope de la beca total como excluyente, el borde de 2,5 cambiaría de lado.

### `f7949e00-d48a-44e9-9dbb-062403ed9775` · EXCEPCION

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-21` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Art. 21. La Comisión de Becas a pedido del solicitante podrá otorgar beca total o media beca en casos no incluidos el Art. 16. Para estos casos se requerirá, la conformidad del DICOES.

**La lectura afirma:** La Comisión de Becas puede otorgar beca total o media beca en casos no incluidos en el artículo 16, con la conformidad del DICOES.

**Qué hay que decidir:** Es la válvula de la ordenanza: no cumplir ninguna causal del artículo 16 no cierra la puerta. No se formaliza porque depende de una decisión discrecional de la Comisión y de la conformidad de otro organismo, y un AST que devolviera verdadero haría creer que la beca está garantizada. Omitirla sería peor: la lectura diría que fuera del artículo 16 no hay nada, y el texto dice lo contrario.

### `aa6a2b6d-dd60-4cea-9ee1-6f5f8f7e8da3` · EXCEPCION

**Norma:** LEY 547/2001 · **Unidad:** `articulo-2/parrafo-7` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Se concederán también becas totales, con prescindencia de los ingresos del grupo familiar, cuando se trate de hijos de personal docente, en el caso en que dicho personal se encuentre a cargo de los alumnos en turno de comedor que almuercen dentro del ámbito de éste.

**La lectura afirma:** El hijo del docente que está a cargo del turno de comedor tiene beca total sin que se miren los ingresos de su familia.

**Qué hay que decidir:** Es la única causal del artículo que expresamente prescinde del ingreso, y depende de un hecho que no es del alumno ni de su familia sino del puesto de trabajo de su madre o su padre en ese turno: que el docente esté a cargo de los alumnos que almuerzan en el comedor. El corpus no tiene ese dato ni un campo donde ponerlo. Se conserva sin condición ejecutable porque escribirla sobre «es hijo de docente» a secas ampliaría la excepción a todo el personal docente de la Ciudad.

### `13fb2aa4-8f73-4885-ba87-39a8b22500bc` · PRIORIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-13` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Art. 13. La Secretaría de Educación priorizará el otorgamiento de las bocas a las escuelas que se encuentren en zonas de mayor demanda por sus características socioeconómicas.

**La lectura afirma:** La autoridad prioriza el otorgamiento en escuelas de zonas de mayor demanda por sus características socioeconómicas.

**Qué hay que decidir:** «Priorizará» es una preferencia en la distribución de cupos entre escuelas, no una condición del alumno. El texto se conserva como está publicado, con «las bocas» donde dice «becas»: corregir la errata haría que la cita dejara de coincidir con el texto capturado, que es lo único contra lo que se puede verificar.

### `09363b9f-2006-4799-b10c-e0581b6a200a` · PRIORIDAD

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-17` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Art. 17. Cuando el solicitante estuviese incluido en más de una de las causales mencionadas en el artículo anterior se procederá simplemente otorgando el mayor beneficio.

**La lectura afirma:** Cuando el solicitante entra en más de una causal, se otorga el mayor beneficio.

**Qué hay que decidir:** Es la regla que resuelve la concurrencia de causales y no se puede escribir como condición sobre la persona: no dice si alguien accede, dice cuál de dos resultados se elige. Formalizarla necesita que el modelo distinga beca total de media beca, que es la decisión de fondo que esta lectura deja abierta.

### `bb092cc7-75a4-4114-8312-835528e42048` · REVOCACION

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-15/parrafo-36` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Dicha Comisión podrá reveer en cualquier momento el otorgamiento de la beca anual si se produjeran modificaciones en las circunstancias que motivaron el otorgamiento de la misma.

**La lectura afirma:** La Comisión puede revisar en cualquier momento el otorgamiento de la beca anual si cambian las circunstancias que lo motivaron.

**Qué hay que decidir:** El texto habilita revisar y no dice qué resultado tiene la revisión: si la beca se reduce, se da de baja o se conserva hasta terminar el ciclo lectivo. Tampoco dice si el cambio de circunstancias tiene que ser informado por la familia. Clasificarla como revocación es la lectura más probable y por eso mismo hay que confirmarla: revisar y revocar no son lo mismo.

### `5ede5f94-f6b5-4604-8d31-85495a136b24` · SALVAGUARDA

**Norma:** ORDENANZA 43478/1989 · **Unidad:** `capitulo-VI/articulo-22` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Art. 22. los docentes de grado podrán solicitar becas a la Comisión en aquellos casos de alumnos en situación de riesgo social y que por sí o por falta de responsable no la hayan solicitado.

**La lectura afirma:** Los docentes de grado pueden pedir la beca para alumnos en situación de riesgo social que no la solicitaron por sí o por falta de responsable.

**Qué hay que decidir:** Es la salvaguarda que hace que la falta de solicitud no equivalga a la falta de necesidad: un chico sin adulto que le tramite la beca no queda afuera. No es una condición que cumpla el alumno sino una facultad del docente, así que no se formaliza; se conserva porque una lectura que la omita responde «hay que solicitarla» a quien no tiene quién la solicite.


## CABA.BECAS-ESTUDIANTILES

### `6b3ce712-f677-45f3-88bf-b59e92efd047` · APLICABILIDAD

**Norma:** DECRETO 75/2015 · **Unidad:** `articulo-1/parrafo-4` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> 2.917 se encuentra destinado a aquellos alumnos/as regulares matriculados que cursen obligatoriamente en escuelas de nivel medio de gestión estatal de todas las modalidades y orientaciones dependientes del Ministerio de Educación de la Ciudad

**La lectura afirma:** El régimen está destinado a alumnos regulares matriculados que cursan obligatoriamente el nivel medio en escuelas de gestión estatal del Ministerio de Educación de la Ciudad.

**Qué hay que decidir:** La condición escrita es la misma que la del artículo 1 de la ley, y a propósito: lo único que el decreto agrega es «matriculados» y «obligatoriamente», y ninguna de las dos tiene campo en el modelo. «Obligatoriamente» puede no cambiar nada —el nivel medio es obligatorio en la Ciudad— o puede dejar afuera a quien cursa el secundario de adultos, que es exactamente la persona a la que una beca de este tipo le hace falta. Formalizarlo sin decidirlo sería elegir una de las dos lecturas; omitirlo sería decir que el decreto no dice nada nuevo. La cita se corta donde la corta el boletín: el texto capturado parte la oración en tres unidades y una cita no puede cruzar de unidad.

### `2c0c55ae-383a-461d-9f62-c23d12d4ce8d` · APLICABILIDAD

**Norma:** RESOLUCION 1621/2025 · **Unidad:** `anexo-3/articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Aprobar los "Procedimientos para el otorgamiento, control y evaluación del Régimen de Becas Estudiantiles de la Ley 2917"

**La lectura afirma:** Los procedimientos de otorgamiento, control y evaluación están aprobados por un anexo que la resolución no transcribe.

**Qué hay que decidir:** Es la remisión que explica por qué el trámite concreto sigue sin estar: la resolución aprueba un anexo y remite a la separata del Boletín Oficial. Queda declarada para que la ausencia se lea como remisión a un texto identificado y no como que el procedimiento no existe. El propio texto capturado adelanta que el anexo «regula las etapas de inscripción, evaluación y notificación, bajo una gestión digital integral, contemplando las instancias de subsanación», y eso es lo único que se sabe de su contenido.

### `e91b1f7b-3364-41af-9759-ca3615863a3b` · APLICABILIDAD

**Norma:** RESOLUCION 1621/2025 · **Unidad:** `anexo-3/articulo-4` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Crear y aprobar el uso de la plataforma "Becas Ciudad" para gestionar los procedimientos de otorgamiento y control del Régimen de Becas Estudiantiles de la Ley 2917

**La lectura afirma:** El otorgamiento y el control de la beca se gestionan por la plataforma «Becas Ciudad».

**Qué hay que decidir:** No es una condición sobre la persona: es por dónde se hace el trámite, que es de las primeras cosas que alguien pregunta y que hasta esta norma no estaba en el corpus. El modelo guarda los canales atados a un organismo o a un punto de atención, y los carga desde los directorios, no desde una lectura curada: por eso queda acá como regla declarada y no como canal. Y falta lo que hace que un canal sirva —la dirección web, si hay que autenticarse, en qué fechas abre—: eso está en el anexo que la resolución no transcribe.

### `b86825a0-73f2-4e78-aa09-369c90502335` · APLICABILIDAD

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-1` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Créase el Régimen de Becas Estudiantiles para alumnos/as regulares de nivel medio/secundario de escuelas de gestión estatal de todas las modalidades y orientaciones dependientes del Ministerio de Educación de la Ciudad Autónoma de Buenos Aires.

**La lectura afirma:** Ser alumno o alumna regular de nivel medio en una escuela de gestión estatal del Ministerio de Educación de la Ciudad.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `01b198ad-87c9-4cbf-933b-9a7119d8f649` · APLICABILIDAD

**Norma:** RESOLUCION 1621/2025 · **Unidad:** `anexo-3/articulo-1` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Dejar sin efecto las Resoluciones 1293-MEGC/09 y 62-SSIECE/13.

**La lectura afirma:** Quedan sin efecto las resoluciones que regían el procedimiento antes de 2025.

**Qué hay que decidir:** No es una condición: es lo que impide que alguien resuelva el trámite con la norma anterior. Ninguna de las dos resoluciones que deja sin efecto está en el corpus, así que no se puede decir qué cambió; lo único verificable es que ya no rigen. Se conserva porque una respuesta que las siga citando estaría citando algo derogado.

### `6cce1d61-0211-4eaa-9845-5bd6bb90c2ce` · APLICABILIDAD

**Norma:** DECRETO 75/2015 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> El Ministerio de Educación dicta las normas operativas, complementarias y aclaratorias necesarias para la implementación de los mecanismos de recepción de solicitudes de becas y su otorgamiento y control, la evaluación socio-ambiental mediante muestras testigo, el seguimiento de los beneficiarios por parte de las autoridades escolares y la prevención del abandono escolar por parte de los beneficiarios

**La lectura afirma:** Cómo se reciben las solicitudes, cómo se otorga y controla la beca y cómo se evalúa la situación socio-ambiental lo fija el Ministerio de Educación por normas operativas.

**Qué hay que decidir:** No es una condición sobre nadie: es la remisión que explica por qué el trámite concreto —dónde se presenta, con qué formulario, en qué fecha— no está en el corpus. Queda declarada para que la ausencia de esos datos se lea como remisión a otra norma y no como que el trámite no existe. Vale la pena registrar lo que menciona al pasar: la evaluación socio-ambiental se hace «mediante muestras testigo», es decir que no se verifica caso por caso.

### `7a76610e-72f7-4a57-879f-52d76e6d506f` · APLICABILIDAD

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-5` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Son beneficiarios/as directos con acreditación de por lo menos una de las condiciones establecidas a continuación, los alumnos/as: a) Que integren un hogar cuyo ingreso mensual resulte igual o menor a 1, 5 del salario mínimo, vital y móvil. b) Que concurran a escuelas de reingreso. c) Que se encuentren en situación de calle. d) Que se encuentren alejados/as de sus familias en hogares convivenciales, o en otros tipos de programas de asistencia; e) que integren un hogar con Necesidades Básicas Insatisfechas (NBI). f) Que residan en Núcleos Habitacionales Precarios o Transitorios. g) que sean padres o madres adolescentes, o adolescentes embarazadas. h) Que tengan necesidades especiales o enfermedad graves. i) Que integren un hogar con mas de tres miembros en edad escolar, siempre que los ingresos del mismo resulten hasta un 50% por encima de lo establecido en el punto a). j) que tengan al su padre y/o madre privado de la libertad en el sistema penal, siempre que los ingresos de su hogar resulten hasta un 50 % por encima de lo establecido en el punto a).

**La lectura afirma:** Acreditar al menos una de las diez condiciones del artículo 5. Son alternativas, no acumulativas: la ley dice «por lo menos una».

**Qué hay que decidir:** Los incisos i) y j) dicen «hasta un 50% por encima de lo establecido en el punto a)». Se leyó como 1,5 × 1,5 = 2,25 SMVM, que es la lectura literal de «un 50% por encima de 1,5». La otra lectura posible —1,5 + 0,5 = 2 SMVM— cambia quién entra y quién no, y el texto no la descarta. Hay que elegirla con criterio jurídico, no por aritmética.

### `241c837f-32ef-43d8-a8fc-c8f0ec171830` · APLICABILIDAD

**Norma:** RESOLUCION 1621/2025 · **Unidad:** `anexo-3/articulo-5/parrafo-10` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> así como a establecer y actualizar los indicadores de vulnerabilidad socioeconómica, en el marco de lo dispuesto por el artículo 6 de la Ley 2917.

**La lectura afirma:** Los indicadores de vulnerabilidad socioeconómica del artículo 6 de la Ley 2917 los establece y actualiza la Subsecretaría Gestión del Aprendizaje.

**Qué hay que decidir:** Cierra una pregunta que la lectura de la Ley 2917 dejó abierta: la ley admite «otros indicadores de vulnerabilidad socioeconómica» además de las diez condiciones del artículo 5, y no decía quién los fija. Ahora se sabe quién, y sigue sin saberse cuáles: los indicadores no están en el corpus. Formalizarla no tiene sentido —no es una condición sobre nadie— y omitirla dejaría creer que fuera del artículo 5 no hay nada.

### `b7824492-a38c-45cd-bac9-d292562f2051` · CESE

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-16` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> El derecho del beneficiario/a a la percepción de la beca se extingue por: a) Desaparición de las causales que justificaron el otorgamiento del beneficio. b) Egreso del becario/a del nivel medio. c) Abandono de sus estudios. d) Fallecimiento del beneficiario/a.

**La lectura afirma:** El derecho se extingue por desaparición de las causales que lo justificaron, egreso del nivel medio, abandono de los estudios o fallecimiento.

**Qué hay que decidir:** La ley llama «extinción» a las cuatro causales juntas, pero fallecimiento y egreso son hechos que cierran el derecho, mientras que «desaparición de las causales» es una revisión de las condiciones que puede ser reversible. Cese y revocación tienen efectos distintos sobre lo ya percibido y el texto no distingue: se cargan como cese sin afirmar que lo percibido sea repetible.

### `3e2ef8b8-91c8-49ad-a5a6-58f63c44dca9` · COMPATIBILIDAD

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-7` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> El alumno/a que sea titular de otra beca estudiantil sólo puede resultar beneficiario del Régimen creado por la presente Ley, cuando el monto de esa beca sea inferior al dispuesto por el artículo 4°. En tal caso, el beneficio a otorgar se reducirá a la suma de dinero necesaria para alcanzar dicho monto.

**La lectura afirma:** Tener otra beca estudiantil no excluye, siempre que su monto sea inferior al del artículo 4. En ese caso esta beca cubre la diferencia hasta alcanzarlo.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `9e3c1218-6386-44dc-80cc-2808c57323a5` · EXCEPCION

**Norma:** DECRETO 75/2015 · **Unidad:** `articulo-2/parrafo-7` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Estudiantiles, creado por el artículo 1° de la Ley N° 2.917, y que a la fecha del dictado del presente se encuentren cursando estudios de nivel medio a través de los proyectos y programas mencionados, quienes podrán solicitar la renovación de dicho beneficio en tanto no se configuren los supuestos del artículo 16 de la citada Ley.

**La lectura afirma:** Quienes ya cobraban la beca cursando por proyectos y programas del Ministerio pueden pedir la renovación aunque no cumplan el artículo 1, salvo que se configuren las causales de extinción del artículo 16 de la Ley 2917.

**Qué hay que decidir:** Es una excepción con fecha: alcanza a quien estaba cobrando la beca y cursando por esos programas «a la fecha del dictado del presente», que es 2015. No es una condición que alguien pueda cumplir hoy empezando algo, y el modelo no tiene cómo expresar «lo que era cierto en una fecha pasada». Formalizarla como condición vigente extendería la excepción a cualquiera que hoy curse por un programa del Ministerio, que es más gente de la que el decreto incluye. Se conserva porque omitirla le responde «no cumplís el artículo 1» a alguien a quien el decreto expresamente le conserva la beca.

### `862795a8-1415-47d7-8a11-8112953e9ced` · EXCEPCION

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-6` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Sin perjuicio de lo establecido en el Art. 5°, pueden ser beneficiarios/as del Régimen de Becas Estudiantiles, quienes presenten otros indicadores de vulnerabilidad socioeconómica que, según la autoridad de aplicación, resulten suficientes para acreditar tal condición de vulnerabilidad.

**La lectura afirma:** La autoridad de aplicación puede admitir otros indicadores de vulnerabilidad socioeconómica además de los del artículo 5.

**Qué hay que decidir:** No tiene AST y no puede tenerlo: la condición es «lo que la autoridad de aplicación considere suficiente». Escribir una regla ejecutable acá inventaría un criterio que la ley delegó a propósito. Se conserva como excepción declarada para que no se lea el artículo 5 como una lista cerrada, que es el error que dejaría afuera a quien la ley quiso incluir.

### `f79ef26d-192f-44b7-adb0-bed3c82dc9f5` · REHABILITACION

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-3` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Es renovable anualmente cuando el beneficiario/a acredite fehacientemente que se mantienen las condiciones que determinaron su otorgamiento.

**La lectura afirma:** La beca se renueva por año si se acredita fehacientemente que se mantienen las condiciones que la originaron.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `7c70bc49-45dc-4dce-8c99-ae3808381245` · REVOCACION

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> Los beneficiarios/as que aspiran a que se renueve el beneficio deben acreditar mediante la documentación correspondiente que se mantienen las condiciones que dieron origen al beneficio durante el ciclo lectivo anterior y tienen la obligación de informar toda modificación que pudiera haberse producido. El incumplimiento de dicha obligación puede dar lugar a la perdida del beneficio.

**La lectura afirma:** No informar una modificación de las condiciones que originaron la beca puede dar lugar a su pérdida.

**Qué hay que decidir:** La ley dice «puede dar lugar», no «da lugar». Es una facultad y no un efecto automático: servir esta regla como si la pérdida fuera segura le diría a alguien que ya perdió la beca cuando la autoridad todavía no decidió nada.

### `12848158-d2b2-49cd-b928-eeca48f5af83` · SALVAGUARDA

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-16` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> En ningún caso son causales de extinción del beneficio las sanciones comprendidas en la Ley 223 ni la condición de repitente del alumno/a.

**La lectura afirma:** Ni las sanciones disciplinarias de la Ley 223 ni repetir de año extinguen la beca. La ley lo dice con «en ningún caso».

**Qué hay que decidir:** El AST está escrito para que la regla nunca dé falso: es una salvaguarda, no una condición que alguien pueda incumplir. Lo que importa de esta pieza no es su valor sino que exista y quede ligada a las causales de cese, para que un lector no infiera que repetir de año da de baja la beca. Repetir y abandonar son cosas distintas y la ley las separa.

### `799a8184-7dde-4b2f-81c8-a5479792eb68` · SALVAGUARDA

**Norma:** LEY 2917/2008 · **Unidad:** `articulo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Los alumnos de las modalidades técnicas y artísticas no quedan inhabilitados para recibir otros beneficios o subsidios del Gobierno de la Ciudad destinados a atender las necesidades especiales de dichas modalidades.

**La lectura afirma:** Cobrar esta beca no inhabilita a los alumnos de modalidades técnicas y artísticas para recibir otros beneficios del Gobierno de la Ciudad destinados a esas modalidades.

**Qué hay que decidir:** Es una salvaguarda sobre otros beneficios, no una condición de éste: no se evalúa acá, se conserva para que la respuesta sobre compatibilidades no diga que hay una incompatibilidad que la ley descarta expresamente.


## CABA.SUBSIDIO-SITUACION-DE-CALLE

### `6af18b04-ad62-4f67-b003-3092ff4643cc` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-16` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Artículo 16 - El Ministerio de Derechos Humanos y Sociales, se encuentra facultado para el dictado de la reglamentación del presente decreto, y de aquellos actos administrativos que resulten necesarios para su correcta implementación.

**La lectura afirma:** La reglamentación del decreto está a cargo del Ministerio de Derechos Humanos y Sociales.

**Qué hay que decidir:** Se conserva porque explica por qué varios campos de esta lectura quedan sin informar: el decreto delega en la reglamentación la documentación exigida, la acreditación de las corresponsabilidades y el procedimiento. No es una condición de acceso y no se formaliza como tal.

### `4f8b3170-e5fd-414d-9ea7-ec0449bd7259` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-10` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> El subsidio que se otorgue puede ser destinado para: a) cubrir gastos de alojamiento, b) cubrir toda índole de gastos emergentes, en los casos en que a los beneficiarios del presente programa, se les otorgue un crédito hipotecario del Instituto de Vivienda de la Ciudad Autónoma de Buenos Aires, o requieran del mismo para la obtención de una solución habitacional definitiva.

**La lectura afirma:** El subsidio se destina a gastos de alojamiento o a gastos emergentes ligados a un crédito hipotecario del Instituto de Vivienda para una solución habitacional definitiva.

**Qué hay que decidir:** El artículo dice a qué puede destinarse el dinero, no qué tiene que cumplir una persona para cobrarlo. Es una restricción de destino que se verifica después, con los comprobantes del artículo 12: tratarla como condición de acceso pediría acreditar el gasto antes de recibir el dinero con el que se hace.

### `ee65e86a-b9b1-42e9-b148-82feb0af0d97` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) encontrarse en "situación de calle" de conformidad con lo establecido en el artículo 3° y con las restricciones dispuestas por el artículo 4° del presente decreto;

**La lectura afirma:** Encontrarse en situación de calle según los artículos 3 y 4 del decreto.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `76baea6c-44e0-4ab5-9666-2e073ea46beb` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> b) ser residente de la Ciudad Autónoma de Buenos Aires con una antigüedad mínima de un (1) año;

**La lectura afirma:** Residir en la Ciudad Autónoma de Buenos Aires con una antigüedad mínima de un año.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `7b211594-d01b-4e99-b8a4-c191c90c28f3` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> c) poseer ingresos menores al monto resultante del índice correspondiente a la canasta básica alimentaria, elaborada mensualmente por el INDEC;

**La lectura afirma:** Tener ingresos menores al índice de la canasta básica alimentaria del INDEC.

**Qué hay que decidir:** El umbral es la canasta básica alimentaria, que el INDEC publica todos los meses y que depende de la composición del hogar: no es un número, es una función de cuántas personas adultas equivalentes hay. El AST compara contra el parámetro y no lo calcula; mientras el parámetro no tenga valor aprobado para el período consultado y para ese hogar, la regla devuelve desconocido en vez de excluir a alguien con una canasta de otro mes. Además el decreto dice «canasta básica alimentaria» y no «canasta básica total», que es un umbral más alto: la diferencia decide quién entra.

### `30d6aee0-af9c-456f-b28c-dff0b6c60feb` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> d) presentar la documentación exigida por las normas reglamentarias del presente decreto, a fin de acreditar los requisitos establecidos en el presente artículo;

**La lectura afirma:** Presentar la documentación que exijan las normas reglamentarias para acreditar los requisitos.

**Qué hay que decidir:** El decreto remite a su reglamentación y no dice qué documentos son. No hay condición que escribir: enumerar los documentos que se piden en la práctica sería afirmar como exigencia normativa algo que esta norma no exige, y a alguien en situación de calle un documento de más lo deja afuera.

### `daa28930-8902-44ea-aa8e-1d96ed7f3951` · APLICABILIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-11` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> e) estar inscriptos en el Registro Único de Beneficiarios.

**La lectura afirma:** Estar inscripto en el Registro Único de Beneficiarios.

**Qué hay que decidir:** Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita para la evaluación: hay que confirmar que la condición dice lo que dice la norma.

### `486da2fb-bf27-46f4-b3e0-051f2eea7342` · CESE

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-14` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> a) cesación de las causas que dieron origen al otorgamiento del subsidio

**La lectura afirma:** Caduca el beneficio cuando cesan las causas que dieron origen a su otorgamiento.

**Qué hay que decidir:** «Cesación de las causas» se leyó como que el hogar dejó de estar en situación de calle, que es la causa que el artículo 3 declara. No es la única lectura posible: el subsidio se otorga para conseguir una solución habitacional, así que conseguirla es a la vez el objetivo del programa y, en esta lectura, la causal de su baja. Decidir eso es una lectura jurídica, no una inferencia de texto.

### `ceaa0556-62dc-45cd-8dec-66dac95c3c6f` · CESE

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-14` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> b) que el grupo familiar no cumpla con los requisitos establecidos en el artículo precedente.

**La lectura afirma:** Caduca el beneficio cuando el grupo familiar no cumple con los requisitos del artículo precedente.

**Qué hay que decidir:** El artículo precedente al 14 es el 13, que no tiene «requisitos» sino corresponsabilidades de salud y educación; los requisitos están en el artículo 11. La remisión no cierra, y las dos lecturas dan resultados opuestos: por el 13, un certificado escolar entregado tarde da de baja el subsidio de una familia en la calle; por el 11, la baja procede cuando el hogar deja de reunir las condiciones de acceso. No se elige ninguna: se declara la ambigüedad con el texto a la vista.

### `c8bd679d-329f-4002-8b7f-bb4f06ab7357` · PRIORIDAD

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-9` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Artículo 9° - La titularidad del subsidio recaerá en los jefes o jefas de familia, salvo que se trate de familias biparentales, en cuyo caso recaerá preferentemente en la mujer.

**La lectura afirma:** La titularidad recae en los jefes o jefas de familia; en familias biparentales, preferentemente en la mujer.

**Qué hay que decidir:** «Preferentemente» no es «obligatoriamente»: la norma expresa una preferencia y no una condición que se cumpla o no se cumpla. Formalizarla como regla ejecutable la convertiría en un requisito —y una solicitud a nombre del varón quedaría rechazada por algo que el decreto no prohíbe—. Se conserva el texto y la preferencia queda declarada.

### `f4286fe7-89bd-4f18-86df-6f145b903db1` · SALVAGUARDA

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-8` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> En aquellos casos en que prima facie la autoridad de aplicación constate que un grupo familiar o persona sola se encuentra en situación de calle y hasta tanto pueda verificar las condiciones y requisitos establecidos en los artículos 7° y 11 respectivamente, o hasta que se efectivice la percepción del subsidio, puede derivar transitoriamente a la familia a paradores u otras alternativas habitacionales transitorias, o bien otorgarles una suma de hasta pesos cuatrocientos cincuenta ($ 450) en concepto de adelanto de la primera cuota.

**La lectura afirma:** Constatada prima facie la situación de calle y hasta verificar las condiciones y requisitos, la autoridad puede derivar a paradores u otras alternativas transitorias, o adelantar la primera cuota.

**Qué hay que decidir:** Es la salvaguarda del decreto: permite responder antes de terminar de verificar. No se formaliza como condición porque no la cumple la persona sino la autoridad —«puede», no «debe»—, y escribir un AST que devuelva verdadero haría creer que el adelanto está garantizado cuando el texto lo deja a criterio del organismo. Omitirla sería peor: sin ella, la lectura diría que no hay nada hasta que termine la verificación.

### `71cd79e3-5993-45dc-8922-131cb7caf727` · SALVAGUARDA

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-15` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> La autoridad de aplicación debe informar al beneficiario, que es condición necesaria para el mantenimiento del beneficio, que los miembros de su grupo familiar menores de quince (15) años, no realicen actividades que la Ciudad de Buenos Aires ha categorizado como trabajo infantil en la Ley N° 937, conforme declaración jurada que como Anexo forma parte del presente.

**La lectura afirma:** Es condición de mantenimiento del beneficio que los menores de quince años del hogar no realicen las actividades que la Ley 937 categoriza como trabajo infantil.

**Qué hay que decidir:** La condición está declarada y su contenido no: qué cuenta como trabajo infantil lo define la Ley CABA 937, que no está en el corpus, y la acreditación es una declaración jurada que vive en un anexo del decreto que tampoco está. Además el artículo obliga a la autoridad a informarlo, lo que hace que la condición dependa de un acto del propio organismo. Ninguna de las tres cosas se completa por analogía.

### `cc5b02d2-9343-4c7b-9a53-6211f6f8c25a` · SUSPENSION

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-13` · **Estado:** CANDIDATE · **Condición ejecutable:** no

> Los/las titulares del beneficio asumen las siguientes corresponsabilidades: a. En materia de protección de la salud:

**La lectura afirma:** El titular asume corresponsabilidades de control de salud y de escolaridad, con periodicidad según la edad de cada integrante del hogar.

**Qué hay que decidir:** Son trece obligaciones distintas con periodicidades distintas por edad —control mensual de la embarazada, quincenal del recién nacido, anual del adulto mayor, certificado escolar cada tres meses—. Cada una es una condición separada sobre una persona distinta del hogar, y comprimirlas en un solo booleano diría «cumple» o «no cumple» sin decir qué. Se conserva el texto entero hasta que la revisión decida cómo se modelan y, sobre todo, qué se responde cuando una sola de las trece no se cumple.

### `37567d65-9508-42ab-a9bf-d641599b34c8` · SUSPENSION

**Norma:** DECRETO 690/2006 · **Unidad:** `articulo-12` · **Estado:** CANDIDATE · **Condición ejecutable:** sí

> b) acreditar que el subsidio otorgado ha sido destinado a la obtención de una solución habitacional, mediante los comprobantes que disponga la autoridad de aplicación;

**La lectura afirma:** El titular acredita, con los comprobantes que disponga la autoridad de aplicación, que el subsidio se destinó a obtener una solución habitacional.

**Qué hay que decidir:** El decreto pone la obligación y no dice qué pasa si no se cumple: no la nombra entre las causales de caducidad del artículo 14 ni la asocia a una suspensión. Se clasifica como suspensión porque es lo que la práctica sugiere y por eso mismo hay que confirmarlo: incumplir una obligación y perder el beneficio no son lo mismo, y el texto no los une.

