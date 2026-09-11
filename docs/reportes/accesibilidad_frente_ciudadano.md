# Accesibilidad del frente ciudadano

Pantalla revisada: `/consulta` (`src/backend_normativo/api/ciudadano/consulta.html`).
Referencia: WCAG 2.1 nivel AA. Criterio 3 de P-015.

Este informe separa tres cosas que suelen mezclarse: lo que una prueba
**mide** en cada corrida, lo que se **inspeccionó** una vez con el árbol de
accesibilidad del navegador, y lo que **no se puede afirmar desde acá**. Lo
último no es una nota al pie: es la parte que falta.

## 1 · Lo que se mide en cada corrida

Nueve de los veintiún casos de `tests/aceptacion/test_recorrido_ciudadano.py`
son de accesibilidad, y corren en Chromium contra el servidor real:

| Qué | Cómo se verifica | Criterio WCAG |
| --- | --- | --- |
| Todo control tiene nombre accesible | Se recorre cada `input`/`select`/`textarea` visible y se exige `label` asociada o `aria-label` | 1.3.1, 4.1.2 |
| Contraste ≥ 4,5:1, esquema claro y oscuro | Se leen los colores computados de cada elemento visible con texto y su fondo efectivo, y se calcula la razón | 1.4.3 |
| Sin desborde horizontal a 360 px | `scrollWidth - clientWidth ≤ 1` con la respuesta ya renderizada | 1.4.10 |
| El foco va a la respuesta | Tras contestar, `document.activeElement` es el encabezado de la respuesta | 2.4.3 |
| El estado se anuncia solo | `role="status"` y `aria-live="polite"` en el renglón de estado y en el contenedor de resultado | 4.1.3 |
| El recorrido se hace con teclado | Tabular al salto de contenido, escribir y enviar con Enter, sin mouse | 2.1.1 |
| Los mensajes de error se entienden | Un 503 produce «El servicio no pudo responder», no un código suelto, y deja reintentar | 3.3.1 |
| Salir borra lo privado visible | Campos, respuesta y almacenamiento del navegador quedan vacíos | — (criterio 3 de P-015) |

El umbral de contraste encontró algo real: el texto atenuado del pie daba
4,40:1 sobre el papel claro. A ojo pasaba. Se corrigió el token a 5,26:1.

## 2 · Lo que se inspeccionó con el árbol de accesibilidad

Una corrida con `Accessibility.getFullAXTree` (CDP) sobre la pantalla con una
respuesta ya cargada, a 360 px:

* **Idioma declarado**: `<html lang="es">`.
* **Regiones**: `header` (banner), `main`, `form`, `section` etiquetada por el
  encabezado de la respuesta, `footer` (contentinfo).
* **Encabezados en orden**: h1 «Consulta de derechos» → h2 con el modo de la
  respuesta → h3 «Lo que dicen las normas», «Fuentes», «Qué conviene saber»,
  «Canal oficial». Sin saltos de nivel.
* **Orden de tabulación**: salto al formulario → «Salir y borrar» → pregunta →
  situación → jurisdicción → tipo de beneficio → fecha → Consultar → Cancelar →
  Empezar de nuevo. Coincide con el orden visual.
* **Nombres de los controles**: cada uno se anuncia con su etiqueta visible
  («¿Qué querés averiguar?», «Tu situación (opcional)», «Jurisdicción»…).
* **Enlaces**: «fuente 1» (la nota al pie) y «Abrir el texto oficial (se abre en
  una pestaña nueva)», con el aviso de pestaña nueva en texto sólo para lectores.
* **Texto al 200 %**: con `font-size: 32px` en la raíz y 360 px de ancho, el
  desborde horizontal sigue siendo 0.

Dos cosas se corrigieron a partir de esta inspección:

1. **Los encabezados de sección iban en versalitas por CSS**
   (`text-transform: uppercase`). El nombre accesible que calcula el navegador
   sale del texto renderizado, y algunos lectores deletrean las palabras en
   mayúsculas: se anunciaba «L-O Q-U-E D-I-C-E-N…». Se sacó la transformación;
   el peso visual quedó en el tamaño y el espaciado.
2. **El sello del modo se anunciaba dos veces**: el encabezado decía «Texto de
   las normas, sin redactar» y a continuación se leía «EXTRACTO», en jerga. El
   sello quedó `aria-hidden`: sigue a la vista y ya no duplica.

## 3 · Lo que no se puede afirmar desde acá

**No hubo revisión con una persona usando un lector de pantalla.** Todo lo
anterior es medición automática e inspección del árbol que expone el navegador,
y eso no es lo mismo que alguien navegando con NVDA, JAWS o VoiceOver. Un árbol
correcto puede resultar igual incomprensible: el orden en que se anuncian las
fuentes, si la respuesta se entiende sin ver la numeración de las notas al pie,
si «Salir y borrar» se interpreta como lo que hace. Nada de eso lo contesta una
prueba.

Tampoco se probó:

* Ampliación al 400 % (WCAG 1.4.10 pide hasta ahí; se verificó al 200 %).
* Navegación por voz.
* Modo de alto contraste forzado del sistema operativo.
* Personas con discapacidad cognitiva leyendo el texto de las normas, que es
  texto jurídico literal y no está redactado para leerse fácil. El modo
  extracto es verificable y es difícil de leer; esa tensión no se resuelve con
  CSS.

Mientras no haya una revisión manual con personas, **el criterio 3 de P-015 no
está cerrado**, y este informe no debe citarse como si lo estuviera.
