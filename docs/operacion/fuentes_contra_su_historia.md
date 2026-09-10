# Acta: cada fuente contra la historia que declara

Evidencia parcial de P-006, criterios 1 y 2. Registra lo verificado el 10 de
septiembre de 2026 sobre el corpus real.

## El punto del criterio: un HTTP 200 no basta

El manifiesto declara, para cada una de las 85 fuentes, en qué tablas tiene que
terminar lo que esa fuente aporta. **Nadie lo comprobaba.** Una fuente podía
capturarse bien, extraerse bien y no dejar una sola fila donde su historia dice
que debería, y el catálogo la mostraba igual: `ACTIVE`, `ACCESIBLE`, capturada.

`bn calidad fuentes` compara lo declarado con lo que hay. La regla de atribución
es la disciplina del proyecto: **una fila es de una fuente cuando su evidencia
lleva de vuelta a un documento de esa fuente.**

| Veredicto | Fuentes |
| --- | ---: |
| Sirven: dejaron filas donde su historia dice | 30 |
| **Capturadas, extraídas y sin llegar a destino** | **18** |
| **Capturadas y nunca extraídas** | **5** |
| Solo descubrimiento: su destino es el catálogo mismo | 2 |
| Bloqueadas | 17 |
| Sin correr | 13 |
| **Total** | **85** |

Siete de las 18 sin destino son P0, y dos de las cinco nunca extraídas también.

## Dos cosas que la atribución obligó a resolver

**Un dataset no deja evidencia por fila.** F01 carga 428.380 normas del catálogo
nacional y ninguna trae un fragmento que citar: no hay cómo citar un renglón de
un ZIP. La primera versión de este informe la daba por «sin destino», que habría
sido un hallazgo falso. Se acredita por la conciliación DQ11 del importador —la
que P-005 empezó a guardar—, y el informe dice cuáles fuentes se acreditan así.

**Hay tablas que no son de nadie.** Una norma no es «de» una fuente: es la
norma, y varias fuentes la publican. Contar `normas`, `organismos`, `parametros`
o `norma_identificadores` por fuente diría algo falso, así que se declaran no
atribuibles y se dicen como tales en vez de contar cero y hacerlo pasar por
vacío.

## Criterio 2: el fallo se conserva, y ahora también se registra

Tres fuentes —F46, F47, F48— tienen su HTML capturado y **ningún adaptador que
lo lea**: están configuradas como `API_JSON` y los sitios devuelven HTML, y el
adaptador genérico de páginas solo acepta los portales del corpus. La extracción
ya lo decía —«Ninguna familia de extracción acepta… La captura queda guardada
sin extraer»— pero el aviso vivía en la salida de la corrida. Mientras tanto la
fuente seguía `ACTIVE` y `ACCESIBLE`, como si hubiera funcionado.

Lo mismo con M01 y M03: un adaptador las acepta y no sale ningún documento.

Ahora las dos situaciones abren incidencia `COBERTURA_EXTRACCION` de severidad
alta contra la fuente, así que la capacidad queda pendiente hasta que haya con
qué leerlas. Los bytes están guardados desde siempre; lo que faltaba era que su
ilegibilidad dejara rastro.

### Un tipo que no se respetaba

Al escribir la prueba de eso apareció que `ResultadoExtraccion.avisos` está
declarado `list[Aviso]` y cuatro adaptadores metían cadenas sueltas —los
mensajes de «esta URL no es mía»—. Nunca había fallado porque esos caminos no se
recorrían: `acepta()` filtra antes. La prueba los recorrió y reventó con
`'str' object has no attribute 'texto'`. Un aviso que es una cadena no puede
llegar a ser incidencia, así que el tipo no era decorativo: era la diferencia
entre registrar el fallo y perderlo.

## Lo que este acta no acredita

- **Las 18 fuentes sin destino siguen sin destino.** Este informe las encuentra
  y las nombra; arreglarlas es el resto de P-006 y son 18 trabajos distintos.
- **No verifica paginación, anexos ni contenido esperado.** El criterio 1 pide
  las cuatro cosas y esto cubre una: que algo haya llegado a la tabla declarada.
  Las otras tres las verifica la prueba de cada familia de fuentes, que es la
  evidencia «fixtures de regresión por familia» y no está hecha.
- **`--estricto` no está activado en el bootstrap.** Hacer fallar la población
  por 18 fuentes pendientes trabaría un trabajo que no es el mismo. La opción
  existe y es como tiene que quedar cuando se resuelvan.
- **Criterio 3 sin tocar.** Montos y calendarios —que un importe histórico no
  reemplace al actual por ser el último descargado— no se verificó en esta
  vuelta.
- **13 fuentes nunca se corrieron.** No están bloqueadas: no llegó su turno, y
  por eso su estado de acceso sigue sin verificar. Verificarlo es intentarlo.
