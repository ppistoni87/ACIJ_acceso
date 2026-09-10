# Acta: los índices no son el contenido

Evidencia de P-006. De las diecisiete fuentes «capturadas, extraídas y sin
destino», una parte no fallaba por falta de curador: fallaba porque **la página
que el catálogo captura es un índice y el contenido está un clic más allá**.

## Cómo apareció

Antes de escribir un curador de trámites, se miraron las secciones que esas
páginas dejaron. F36 «Tramitar el DNI» no tiene requisitos ni pasos: tiene un
menú de modalidades —DNI al instante, DNI 24 hs, DNI exprés— cada una enlazando
a su ficha. F53 «Progresar» lista líneas de beca. F18 lista inscripciones. F32
es el menú de un turnero.

Curar eso habría producido un trámite «DNI al instante» con cero pasos, cero
requisitos y una evidencia que dice «Tramitá tu DNI en los Centros de Atención
habilitados para esta modalidad» —que no explica cómo—. Un trámite vacío con
cita es peor que ningún trámite: parece un dato.

El manifiesto ya lo decía, con todas las letras: **F66** es «hub /requisitos + 3
hojas», **F53** es «mapa de subpaginas». El catálogo sabía que eran índices y la
ingesta nunca los siguió.

## Qué se hizo

El adaptador de páginas institucionales descubre sus hojas y las deja como
candidatas. Promoverlas sigue siendo una decisión de revisión —un enlace no
prueba que sea una fuente del alcance— y para eso ya existía `bn ingesta
descubrir`, que solo promovía relaciones «de la misma norma». Ahora las
relaciones promovibles viven en `adaptadores/base.py` y las comparten el
adaptador y el comando: si la frase cambia en un lado y no en el otro, las
candidatas dejan de promoverse **sin que nada falle**, que es la forma más
silenciosa de romperse.

El descubrimiento es acotado y no es un rastreador. Dos límites, y los dos
tienen prueba: **mismo host**, y solo lo que cuelga de la ruta de la propia
fuente o es una ficha de trámite. Sin ellos, una página de gobierno lleva a todo
el gobierno.

## Qué dio

96 URLs candidatas descubiertas. Se promovieron y capturaron 24 de cuatro
fuentes —F36, F53, F49, F66—, todas COMPLETA sin rechazos. De ahí salió la
primera ficha de trámite real de esas páginas y el curador que ya existía cargó
**4 trámites con 11 pasos**:

| Trámite | Pasos |
| --- | ---: |
| DNI 24 hs | 3 |
| DNI al instante | 2 |
| DNI en tu celular | 3 |
| DNI exprés | 3 |

El recuento pasó de **38 a 39 fuentes sirviendo** y de 10 a **9 sin destino**.

## Lo que este acta no acredita

- **Que las otras candidatas sirvan.** Quedan 87 sin promover, entre ellas 20 de
  F51 y 20 de F43, que son portales grandes. Promoverlas es tráfico de red y
  decisión de alcance, no un comando que convenga correr entero.
- **Que un índice no aporte nada.** Sus secciones quedan como unidades
  informativas citables: «el organismo publica estas cuatro modalidades» es un
  dato, aunque no sea el trámite.
- **Que las nueve que faltan se resuelvan igual.** F11, F49 y F50 siguen
  extrayendo cero unidades, que es un problema anterior y distinto. Y F66
  declara `reglas` y `beneficio_versiones`: eso es lectura jurídica, no ingesta.
