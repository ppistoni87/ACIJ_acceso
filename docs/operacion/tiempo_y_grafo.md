# Acta: dos ejes de tiempo y un grafo con ciclos

Evidencia de P-007, criterios 2 y 3. Registra lo verificado el 10 de septiembre
de 2026 sobre el corpus real y sobre pruebas contra la base.

## Criterio 3: qué versión se devuelve, y según qué reloj

Preguntar «qué decía esta norma» exige decir cuándo, y hay **dos «cuándo»
distintos**: en qué fecha se aplica y en qué momento se sabía. La fecha en que
se descargó el documento no es ninguno de los dos.

El caso está tomado del corpus: el artículo 2 del Decreto 690/2006 de CABA
tiene dos textos —el anterior y el que el Decreto 161/2025 sustituyó— y en el
mismo período hay normas derogadas. Sobre eso quedan cuatro ensayos contra la
base:

| Qué se prueba | Resultado |
| --- | --- |
| Una modificación parte la norma en dos períodos, y cada fecha cae en uno | Consultando 2010 se sirve la versión anterior y la posterior queda fuera de alcance; consultando 2026, al revés |
| Derogar cierra el período, no borra lo que rigió | La norma derogada no se sirve como actual y sí para una fecha dentro de su período |
| El eje de conocimiento es independiente del de aplicación | Una modificación de 2025 incorporada en 2026 se sirve hoy, y preguntando «qué sabíamos en junio de 2025» devuelve `STALE_DATA` |
| La fecha de descarga no decide vigencia | La versión aplicable a la fecha consultada es la de captura más vieja; la más nueva no gana por ser la más nueva |

El tercero es el que no se puede improvisar después: sin el eje de conocimiento
no hay forma de reconstruir por qué el sistema contestó lo que contestó en su
momento, y esa reconstrucción es lo que separa un registro auditable de uno que
solo dice lo que cree hoy.

Las pruebas preguntan por la capacidad `IDENTIFICACION` a propósito: es la única
que no exige ningún campo crítico, así que lo único que puede impedir servir es
el tiempo, que es lo que se está probando.

## Criterio 2: el grafo tiene ciclos, y está bien que los tenga

`bn calidad grafo` sobre el corpus real:

- **527** relaciones entre **125** normas
- **215** referencias pendientes de resolver
- **0** autorreferencias
- **744** caminos de hasta cuatro saltos que vuelven a su origen: 660 de largo 2,
  36 de largo 3, 48 de largo 4

Los ciclos no son un error de los datos. El Decreto 1134/2005 **sustituye** la
Ley 24.714, y la Ley 24.714 **cita** al Decreto 1134/2005: ninguna de las dos
relaciones sobra, y borrar una para deshacer el ciclo perdería información real.
Lo mismo con la Ordenanza 43.478 y la Ley 547.

Lo que no puede pasar es que recorrerlo no termine. Y hoy **no termina mal
porque nadie lo recorre**: todas las consultas del sistema dan un solo salto. La
primera consulta transitiva —«qué normas afectan a esta», que es exactamente lo
que la recuperación va a necesitar— se encontraría con 744 ciclos de golpe.

La migración 0010 agrega dos cosas:

- **`bn_grafo_normativo(norma, profundidad, sentido)`**: recorre con lista de
  visitados y tope de profundidad. Cada norma aparece una vez, por el camino más
  corto que la alcanzó. Sobre la Ley 24.714 con tres saltos y ambos sentidos:
  117 normas alcanzables, 0,12 s.
- **Un `CHECK` contra la autorreferencia.** El resolutor ya las omitía —91 en la
  última corrida real— pero el esquema las admitía, y una norma que se cita a sí
  misma es el ciclo más corto posible. No había ninguna en la base, así que la
  restricción entró sin migrar datos.

## Lo que este acta no acredita

- **No hay consulta transitiva en producción todavía.** Lo que se agrega es la
  primitiva segura y su prueba; usarla es de P-012 en adelante.
- **El informe no dice que las relaciones sean correctas.** Dice cuántas hay y
  cómo se conectan, no que cada `DEROGA` derogue lo que dice derogar. Eso lo
  sostiene la evidencia de cada relación.
- **Los ciclos se buscan hasta cuatro saltos.** Sin tope, en un grafo denso es
  una explosión combinatoria. Los que la práctica legislativa produce son
  cortos, pero uno más largo no se vería.
- **Las 215 referencias pendientes siguen pendientes.** Resolverlas es traer las
  normas que faltan, que es trabajo de fuente (P-006), no de curación.
- **El ensayo del criterio 3 es sobre versiones construidas para la prueba.** Las
  dos versiones reales del Decreto 690/2006 están en el corpus pero siguen en
  `CANDIDATE`, sin release ni vigencia curada: publicarlas es P-009 y P-011, y
  esa curación la firma una persona.
