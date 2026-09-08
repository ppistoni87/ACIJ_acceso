# Decisiones de dominio

Las decisiones estructurales están en `docs/adr/` (una por tema, con su
contexto y sus consecuencias). Este documento registra las decisiones **de
dominio**: las que no son de arquitectura sino de qué se puede afirmar sobre una
norma y con qué respaldo. Cada una dice qué se decidió, por qué, y qué se
perdería si se decidiera al revés.

Las políticas que el sistema aplica están versionadas en el repositorio
(`vigencia-declarada@1`) y su versión viaja en el fundamento de cada decisión
automática, para que una respuesta vieja se pueda explicar con la política que
regía cuando se dio.

## D-01 · Frescura no es vigencia

Que una fuente responda `304 Not Modified` prueba que el documento no cambió,
no que su contenido siga rigiendo. Son dos ejes distintos: `valid_desde/hasta`
dice desde cuándo se aplica una norma; `verificado_en` y
`reverificar_antes_de` dicen cuándo la miramos por última vez.

Mezclarlos produce el error más caro del dominio: renovar la vigencia de un
dato porque el servidor devolvió 304. Una convocatoria cerrada sigue publicada
en la misma página durante meses.

**Consecuencia:** vencida la frescura, la versión deja de servirse aunque nadie
la haya derogado. No se deroga: se deja de afirmar.

## D-02 · La ausencia de derogación no prueba vigencia

La política automática resuelve solo lo que la fuente **declara**. Si la fuente
dice "vigente" y hay evidencia de esa declaración, se resuelve automáticamente.
Si no dice nada, va a revisión humana.

No haber encontrado una norma derogatoria no es lo mismo que haber comprobado
que no existe. La diferencia importa cuando la respuesta la lee alguien que
decide si presenta un trámite.

## D-03 · "No vigente" no cierra la vigencia por sí solo

Una norma etiquetada "no vigente" pudo incorporar disposiciones que siguen
aplicándose a través de la norma que modificó. La Ley CABA 547 es el caso: está
marcada no vigente y sus sustituciones siguen en el texto de la Ordenanza
43.478.

**Consecuencia:** la etiqueta no alcanza. Se compara la versión histórica con la
actualizada y la decisión queda con fundamento.

## D-04 · Una abrogación seguida de un restablecimiento no tiene lectura automática

La Ley 24.714 fue abrogada y su vigencia restablecida con excepciones. El grafo
de relaciones conserva ambos eventos con su alcance; ninguna regla los combina
en un estado. `estado_legal_validado` queda `NO_DETERMINADA` hasta que alguien
lo resuelva con fundamento.

Tomar el primer término ("abrogada") daría una respuesta rotundamente falsa
sobre la AUH.

## D-05 · Una clave canónica que no es única no es una clave

La numeración de leyes y decretos es jurisdiccional: "Ley 24.714" identifica.
La de resoluciones y disposiciones es por organismo: "Resolución 1/2023" no
identifica nada —el catálogo nacional trae 123 normas con esa clave—.

**Consecuencia:** esas normas se cargan con `identidad_incierta` y quedan fuera
del índice único parcial. No resuelven citas por número. La alternativa —dejar
que la primera fila importada se quede con la clave— haría que una cita se
resolviera con confianza a la norma equivocada por orden de archivo.

## D-06 · Evaluado no es informado

Que los siete campos estén evaluados no significa que tengan valor. Un campo
puede quedar `NO_INFORMADO_EN_FUENTES_REVISADAS`, y eso es un resultado, no una
falta: dice qué fuentes se revisaron y qué no se encontró.

**Consecuencia:** la cobertura se informa separada —porcentaje evaluado y
porcentaje con valor sustantivo validado— y nunca promediada. Un 100% de
evaluación con 0% sustantivo es un estado posible y honesto; un promedio de 50%
no significa nada.

## D-07 · Falta de dato no es incumplimiento

La evaluación de reglas es ternaria: verdadero, falso y desconocido. Un dato que
falta produce `UNKNOWN` y el resultado pide datos en vez de negar. `not(UNKNOWN)`
es `UNKNOWN`: no saber algo no prueba lo contrario.

**Consecuencia:** nunca se responde "no calificás" por un dato que la persona no
dio. Se responde qué falta.

## D-08 · Las excepciones se evalúan antes de concluir

Un criterio general en falso no alcanza para excluir: puede haber una excepción
aplicable y respaldada. Las salvaguardas de no exclusión nunca excluyen y
siempre se informan.

**Consecuencia:** el evaluador no puede cortar temprano por un criterio general.
Si hay excepciones sin evaluar, el resultado es "requiere datos", no "no".

## D-09 · La evaluación es preliminar y lo dice

El sistema no afirma elegibilidad definitiva, otorgamiento, denegatoria ni
revocación. Devuelve `POTENCIALMENTE_APLICABLE` con sus límites y sus citas, y
el cuerpo de la consulta no se persiste.

Quien decide es el organismo. Decir otra cosa desde un backend sería inventarse
una competencia que no tiene.

## D-10 · El contenido de una fuente es dato, nunca instrucción

Un documento oficial puede contener frases que parecen órdenes. Se guardan como
lo que son: el texto de un artículo. No cambian controles, no cambian permisos y
no se ejecutan. Lo mismo vale para las respuestas de un modelo: la IA puede
proponer una extracción, nunca inventar un dato ni resolver por su cuenta un
conflicto jurídico.

## D-11 · Un tope no es un monto

Un umbral de ingresos y una cuantía son cosas distintas aunque las dos sean
números con signo pesos en la misma tabla. Presentar el tope como "lo que vas a
cobrar" es el error que más rápido se convierte en un reclamo.

**Consecuencia:** las cuantías declaran su tipo y una fórmula reproducible; un
parámetro de umbral no puede servirse como cuantía.

## D-12 · Un acceso bloqueado se registra, no se evade

Un `403`, un `429` o una restricción de `robots.txt` pausan la fuente y quedan
registrados como acceso limitado, con motivo, responsable y capacidad afectada.
No se rotan identidades ni se cambia la huella para volver a entrar, y un error
nunca se convierte en "sin datos".

Un fallo de TLS se registra igual y se busca una fuente oficial equivalente o
una carga manual. La validación no se desactiva.
