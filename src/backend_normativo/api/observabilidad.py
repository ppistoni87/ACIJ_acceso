"""Qué se registra de cada consulta, y qué deliberadamente no (P-021).

El criterio pide latencia, errores, abstenciones **por causa**, recuperación,
frescura y conexiones, con `request_id` y **sin conversación sensible en los
logs**. Esa última parte no es un detalle de cumplimiento: quien consulta este
sistema pregunta si le corresponde una pensión por discapacidad o si la pueden
desalojar. Guardar el texto de esa pregunta crea un registro de la situación
personal de alguien, y ese registro después se respalda, se replica y se
consulta.

Así que se registra la **forma** de la consulta y no su contenido: qué ruta se
pidió, contra qué corte, cuánto tardó, si se contestó o se abstuvo y por qué.
Con eso se puede medir todo lo que el criterio pide y no queda escrito qué
preguntó nadie.

`tokens` y `costo` no se registran porque no hay generación: P-013 no está
construido y no hay proveedor de modelo. Inventar columnas en cero mostraría un
tablero que dice que el gasto es nulo, cuando lo que pasa es que no se mide.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

# Cabecera de correlación. Se acepta la que venga de afuera —un balanceador o un
# front suelen ponerla— y si no viene se genera: perder la correlación porque
# nadie la mandó deja cada salto contando su propia historia.
CABECERA_REQUEST_ID = "X-Request-Id"

# Lo que se contesta cuando sí hay respuesta. Todo lo demás es una abstención, y
# una abstención sin causa es indistinguible de un error silencioso.
RESUELTA = "RESUELTA"


@dataclass(frozen=True)
class Anotacion:
    """Lo que se sabe de una consulta al terminar de resolverla."""

    request_id: str
    ruta: str
    resultado: str
    latencia_ms: int
    release_id: uuid.UUID | None = None
    motivo: str | None = None
    evidencias: int = 0

    @property
    def se_abstuvo(self) -> bool:
        return self.resultado != RESUELTA


def request_id_de(cabeceras) -> str:
    """El identificador de esta consulta: el que vino, o uno nuevo."""
    entrante = (cabeceras.get(CABECERA_REQUEST_ID) or "").strip()
    # Se acota el largo: la cabecera la pone quien llama y termina en una
    # columna y en un log. Un identificador de treinta mil caracteres no es un
    # identificador.
    return entrante[:200] if entrante else uuid.uuid4().hex


def registrar(conexion: Connection, anotacion: Anotacion) -> None:
    """Deja la fila. Nunca guarda el texto de la consulta.

    `intencion` recibe la ruta —`/v1/beneficios`— y no lo que la persona
    escribió. Es lo que hace falta para medir por operación sin escribir qué
    preguntó nadie.
    """
    conexion.execute(
        text(
            "INSERT INTO consultas_auditadas ("
            "  id, request_id, release_id, intencion, resultado_tipo, motivo_abstencion, "
            "  latencia_ms, evidencias_usadas"
            ") VALUES (gen_random_uuid(), :rid, :rel, :ruta, :res, :motivo, :ms, :ev)"
        ),
        {
            "rid": anotacion.request_id,
            "rel": anotacion.release_id,
            "ruta": anotacion.ruta,
            "res": anotacion.resultado,
            "motivo": anotacion.motivo,
            "ms": max(0, anotacion.latencia_ms),
            "ev": f'{{"cantidad": {max(0, anotacion.evidencias)}}}',
        },
    )


def resumen(conexion: Connection, *, desde_horas: int = 24) -> dict:
    """Lo que el tablero necesita para distinguir abstención de respuesta.

    Devuelve el denominador junto al numerador a propósito: «12 abstenciones» no
    dice nada sin saber sobre cuántas consultas, y el criterio 3 pide que los
    objetivos se presenten como mediciones con período y denominador.
    """
    filas = (
        conexion.execute(
            text(
                "SELECT resultado_tipo, motivo_abstencion, count(*) AS cuantas, "
                "       percentile_disc(0.95) WITHIN GROUP (ORDER BY latencia_ms) AS p95 "
                "  FROM consultas_auditadas "
                " WHERE ocurrido_en >= now() - make_interval(hours => :h) "
                " GROUP BY 1, 2 ORDER BY 3 DESC"
            ),
            {"h": desde_horas},
        )
        .mappings()
        .all()
    )

    total = sum(f["cuantas"] for f in filas)
    resueltas = sum(f["cuantas"] for f in filas if f["resultado_tipo"] == RESUELTA)
    return {
        "periodo_horas": desde_horas,
        "consultas": total,
        "resueltas": resueltas,
        "abstenciones": total - resueltas,
        "por_causa": [
            {
                "resultado": f["resultado_tipo"],
                "motivo": f["motivo_abstencion"],
                "cuantas": f["cuantas"],
                "latencia_p95_ms": f["p95"],
            }
            for f in filas
        ],
    }
