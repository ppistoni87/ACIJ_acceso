"""P-007 criterio 2: el grafo de relaciones, y por qué recorrerlo termina.

Los ciclos del grafo normativo no son un error de los datos. La Ordenanza
43.478 cita a la Ley 547, y la Ley 547 modifica la Ordenanza 43.478: ninguna de
las dos relaciones sobra, y borrar una para «arreglar» el ciclo perdería
información real.

Lo que no puede pasar es que recorrerlo no termine. Hoy ninguna consulta del
sistema da más de un salto, así que el problema no se ve; la primera consulta
transitiva que alguien escriba lo encuentra de golpe. `bn_grafo_normativo`
recorre con lista de visitados y tope de profundidad, y este informe deja
escrito cuántos ciclos hay para que aparezcan antes y no después.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# Cuatro saltos: alcanza para encontrar los ciclos que importan —los de dos y
# tres normas, que son los que produce la práctica legislativa— sin pagar la
# explosión combinatoria de un grafo denso.
PROFUNDIDAD = 4

SQL_CICLOS = """
WITH RECURSIVE camino AS (
    SELECT norma_origen_id AS raiz, norma_destino_id AS actual,
           ARRAY[norma_origen_id, norma_destino_id] AS visitados, 1 AS salto
      FROM relaciones_normativas
    UNION ALL
    SELECT c.raiz, r.norma_destino_id, c.visitados || r.norma_destino_id, c.salto + 1
      FROM camino c
      JOIN relaciones_normativas r ON r.norma_origen_id = c.actual
     WHERE c.salto < :profundidad
       AND NOT r.norma_destino_id = ANY(c.visitados)
)
SELECT c.salto + 1 AS largo, count(*) AS ciclos
  FROM camino c
  JOIN relaciones_normativas r ON r.norma_origen_id = c.actual
 WHERE r.norma_destino_id = c.raiz
 GROUP BY 1
 ORDER BY 1
"""

SQL_EJEMPLOS = """
SELECT o.tipo || ' ' || o.numero || '/' || o.anio AS origen,
       r.tipo AS ida,
       d.tipo || ' ' || d.numero || '/' || d.anio AS destino,
       r2.tipo AS vuelta
  FROM relaciones_normativas r
  JOIN relaciones_normativas r2
    ON r2.norma_origen_id = r.norma_destino_id
   AND r2.norma_destino_id = r.norma_origen_id
  JOIN normas o ON o.id = r.norma_origen_id
  JOIN normas d ON d.id = r.norma_destino_id
 WHERE o.id < d.id
 GROUP BY 1, 2, 3, 4
 ORDER BY 1
 LIMIT 10
"""


@dataclass
class ReporteGrafo:
    relaciones: int = 0
    normas_con_relacion: int = 0
    autorreferencias: int = 0
    pendientes: int = 0
    ciclos_por_largo: dict[int, int] = field(default_factory=dict)
    ejemplos: list[dict] = field(default_factory=list)
    profundidad: int = PROFUNDIDAD

    @property
    def ciclos(self) -> int:
        return sum(self.ciclos_por_largo.values())


def construir(conexion: Connection, profundidad: int = PROFUNDIDAD) -> ReporteGrafo:
    reporte = ReporteGrafo(profundidad=profundidad)
    reporte.relaciones = conexion.execute(
        text("SELECT count(*) FROM relaciones_normativas")
    ).scalar_one()
    reporte.normas_con_relacion = conexion.execute(
        text(
            "SELECT count(DISTINCT n) FROM ("
            "  SELECT norma_origen_id AS n FROM relaciones_normativas "
            "  UNION ALL SELECT norma_destino_id FROM relaciones_normativas"
            ") AS t"
        )
    ).scalar_one()
    reporte.autorreferencias = conexion.execute(
        text("SELECT count(*) FROM relaciones_normativas WHERE norma_origen_id = norma_destino_id")
    ).scalar_one()
    reporte.pendientes = conexion.execute(
        text("SELECT count(*) FROM referencias_pendientes WHERE estado = 'PENDIENTE'")
    ).scalar_one()
    reporte.ciclos_por_largo = {
        fila.largo: fila.ciclos
        for fila in conexion.execute(text(SQL_CICLOS), {"profundidad": profundidad})
    }
    reporte.ejemplos = [dict(f) for f in conexion.execute(text(SQL_EJEMPLOS)).mappings()]
    return reporte


def formatear(reporte: ReporteGrafo) -> str:
    lineas = [
        "# Grafo de relaciones normativas",
        "",
        f"- Relaciones: {reporte.relaciones}",
        f"- Normas con al menos una relación: {reporte.normas_con_relacion}",
        f"- Referencias pendientes de resolver: {reporte.pendientes}",
        f"- Autorreferencias: {reporte.autorreferencias}",
        "",
    ]
    if reporte.autorreferencias:
        lineas += [
            "**Hay autorreferencias.** Una norma que se cita a sí misma es el ciclo más "
            "corto posible, y desde la migración 0010 el esquema no las admite: si "
            "aparecen, algo las escribió esquivando la restricción.",
            "",
        ]

    lineas += [
        f"## Ciclos (hasta {reporte.profundidad} saltos)",
        "",
        f"Se encontraron **{reporte.ciclos}** caminos que vuelven a su origen.",
        "",
    ]
    if reporte.ciclos_por_largo:
        lineas += ["| Largo del ciclo | Caminos |", "| ---: | ---: |"]
        for largo, cuantos in sorted(reporte.ciclos_por_largo.items()):
            lineas.append(f"| {largo} | {cuantos} |")
        lineas.append("")

    if reporte.ejemplos:
        lineas += ["### Pares que se citan mutuamente", ""]
        for ejemplo in reporte.ejemplos:
            lineas.append(
                f"- **{ejemplo['origen']}** —{ejemplo['ida']}→ **{ejemplo['destino']}** "
                f"—{ejemplo['vuelta']}→ vuelta"
            )
        lineas.append("")

    lineas += [
        "## Por qué esto no es una lista de errores",
        "",
        "Un ciclo entre dos normas es normal: la que cita y la que después la modifica se "
        "nombran mutuamente. Borrar una de las dos relaciones para deshacer el ciclo "
        "perdería información real.",
        "",
        "Lo que sí importa es que recorrer el grafo termine. `bn_grafo_normativo` lleva la "
        "lista de nodos visitados y un tope de profundidad, así que devuelve cada norma "
        "una vez, por el camino más corto que la alcanzó. Este informe existe para que el "
        "número de ciclos se conozca antes de escribir la primera consulta transitiva y no "
        "después.",
        "",
        "## Qué no dice",
        "",
        "Que las relaciones sean correctas. Dice cuántas hay y cómo se conectan, no que "
        "cada `DEROGA` derogue de verdad lo que dice derogar: eso lo sostiene la evidencia "
        "de cada relación, que se revisa aparte.",
        "",
        f"Tampoco dice que no haya ciclos más largos que {reporte.profundidad} saltos. Se "
        "acota a propósito: en un grafo denso, buscar sin tope es una explosión "
        "combinatoria, y los ciclos que la práctica legislativa produce son cortos.",
    ]
    return "\n".join(lineas) + "\n"
