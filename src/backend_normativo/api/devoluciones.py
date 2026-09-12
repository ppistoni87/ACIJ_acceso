"""Lo que la persona contesta sobre la respuesta que recibió (P-015).

Todo lo que el sistema mide hasta acá lo mide de sí mismo: cuánto tardó, si se
abstuvo, con cuántas evidencias. Nada de eso dice si a alguien le sirvió. Una
respuesta puede salir rápida, citada y contra el corte correcto, y dejar a la
persona igual de perdida que antes; con la traza sola eso se cuenta como éxito.

Este módulo agrega la otra mitad y la agrega con un límite explícito: **sin
texto libre**. Las señales son tres y son cerradas. La caja de comentarios es lo
que parece amable y es donde alguien escribe su caso completo —el nombre de su
hija, la dirección de la que lo echan—, y este sistema se construyó entero para
no guardar eso.

`QUIERE_PERSONA` está al lado de las otras dos porque es la señal más
importante: significa que la conversación no alcanzó. Que se pueda contar es lo
que permite discutir con números si hace falta atención humana y dónde.
"""

from __future__ import annotations

import enum

from sqlalchemy import Connection, text


class Senal(enum.StrEnum):
    """Lo único que se puede contestar. El CHECK en la base dice lo mismo."""

    SIRVIO = "SIRVIO"
    NO_SIRVIO = "NO_SIRVIO"
    QUIERE_PERSONA = "QUIERE_PERSONA"


def registrar(conexion: Connection, *, request_id: str, senal: Senal | str) -> bool:
    """Deja la señal. Devuelve si era nueva.

    `ON CONFLICT DO NOTHING` contra el UNIQUE de `(request_id, senal)`: apretar
    dos veces el mismo botón no cuenta dos veces. Una medición de satisfacción
    que se puede inflar repitiendo el clic no mide satisfacción.

    Va **sin** nombrar las columnas del conflicto a propósito. La forma con
    destino explícito —`ON CONFLICT (request_id, senal)`— necesita inferir el
    índice árbitro y para eso PostgreSQL exige `SELECT` sobre la tabla; el rol
    de la API solo tiene `INSERT`. Se puede comprobar en una consola: la misma
    sentencia con destino falla con «permission denied» y sin destino entra.
    Darle `SELECT` al lector sobre las devoluciones de todo el mundo para
    ahorrarse un paréntesis sería pagar un permiso de más por una comodidad de
    escritura.
    """
    valor = Senal(senal).value
    resultado = conexion.execute(
        text(
            "INSERT INTO devoluciones (request_id, senal) VALUES (:rid, :senal) "
            "ON CONFLICT DO NOTHING"
        ),
        {"rid": request_id[:200], "senal": valor},
    )
    return bool(resultado.rowcount)


# La traza se une por `request_id`. Un mismo identificador puede aparecer más de
# una vez —lo puede mandar quien llama en la cabecera— y un JOIN directo
# multiplicaría la devolución por cada traza repetida, inflando exactamente lo
# que el UNIQUE evitó al escribir. Se toma la traza más reciente y una sola.
RESUMEN = """
SELECT d.senal,
       coalesce(t.resultado_tipo, 'SIN_TRAZA') AS resultado,
       t.motivo_abstencion AS motivo,
       count(*) AS cuantas
  FROM devoluciones d
  LEFT JOIN LATERAL (
       SELECT c.resultado_tipo, c.motivo_abstencion
         FROM consultas_auditadas c
        WHERE c.request_id = d.request_id
        ORDER BY c.ocurrido_en DESC
        LIMIT 1
  ) t ON true
 WHERE d.ocurrido_en >= now() - make_interval(hours => :h)
 GROUP BY 1, 2, 3
 ORDER BY 4 DESC
"""


def resumen(conexion: Connection, *, desde_horas: int = 24) -> dict:
    """Las devoluciones del período, contra las consultas que hubo.

    El denominador viaja siempre. «El 80 % dijo que le sirvió» sobre cinco
    respuestas no es un dato, y sin saber cuántas consultas hubo tampoco se sabe
    si contestaron cuatro personas de cinco o cuatro de mil: la segunda dice que
    el mecanismo de devolución no se está usando, que es un hallazgo distinto y
    también importante.
    """
    filas = conexion.execute(text(RESUMEN), {"h": desde_horas}).mappings().all()
    consultas = conexion.execute(
        text(
            "SELECT count(*) FROM consultas_auditadas "
            " WHERE ocurrido_en >= now() - make_interval(hours => :h)"
        ),
        {"h": desde_horas},
    ).scalar_one()

    por_senal = {senal.value: 0 for senal in Senal}
    for fila in filas:
        por_senal[fila["senal"]] += fila["cuantas"]
    total = sum(por_senal.values())
    return {
        "periodo_horas": desde_horas,
        "consultas": int(consultas),
        "devoluciones": total,
        "por_senal": por_senal,
        # Con qué clase de respuesta se encontró cada señal. Es lo que convierte
        # «no me sirvió» en algo accionable: si se concentra en abstenciones por
        # falta de evidencia, el problema es el corpus; si cae sobre respuestas
        # resueltas, el problema es cómo están escritas.
        "por_resultado": [
            {
                "senal": fila["senal"],
                "resultado": fila["resultado"],
                "motivo": fila["motivo"],
                "cuantas": fila["cuantas"],
            }
            for fila in filas
        ],
    }


def borrar_anteriores(conexion: Connection, *, dias: int, simular: bool = False) -> int:
    """Misma retención que la traza, aplicada en el mismo lugar.

    Si se borrara la traza y quedaran las devoluciones, quedaría un registro que
    crece para siempre y que ya no se puede interpretar: una señal suelta, sin
    la consulta a la que se refería.
    """
    cuantas = conexion.execute(
        text(
            "SELECT count(*) FROM devoluciones "
            " WHERE ocurrido_en < now() - make_interval(days => :d)"
        ),
        {"d": dias},
    ).scalar_one()
    if cuantas and not simular:
        conexion.execute(
            text("DELETE FROM devoluciones  WHERE ocurrido_en < now() - make_interval(days => :d)"),
            {"d": dias},
        )
    return int(cuantas)
