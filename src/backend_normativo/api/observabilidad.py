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

`tokens` y `costo` no se registran mientras no haya un proveedor de modelo
configurado: en modo extracto no se gasta nada. Inventar columnas en cero
mostraría un tablero que dice que el gasto es nulo, cuando lo que pasa es que no
se mide.

La retención vive acá abajo, en `purgar()`. Está en el mismo módulo que lo que
escribe a propósito: una política de retención que vive sólo en un documento es
una política que nadie aplica.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

from backend_normativo.api.devoluciones import borrar_anteriores as borrar_devoluciones

# Cabecera de correlación. Se acepta la que venga de afuera —un balanceador o un
# front suelen ponerla— y si no viene se genera: perder la correlación porque
# nadie la mandó deja cada salto contando su propia historia.
CABECERA_REQUEST_ID = "X-Request-Id"

# Rutas de `/v1` que no son consultas y no entran en el denominador. Hoy es
# una sola: la devolución es la respuesta de la persona a una consulta que ya
# quedó registrada, y contarla otra vez mediría el mecanismo de medición.
RUTAS_SIN_TRAZA = frozenset({"/v1/devoluciones"})

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


# --- Retención (P-017, criterio 2) -------------------------------------------
#
# Lo que se guarda de una consulta no tiene identidad —ni texto, ni dirección,
# ni quién— y aun así se borra. Dos razones. La primera es que un registro que
# no caduca crece para siempre y termina respaldado, replicado y consultado por
# gente que no sabe qué está mirando. La segunda es que «no identifica a nadie»
# es una afirmación sobre hoy: un conjunto grande de formas de consulta, con sus
# horarios y sus jurisdicciones, se vuelve más identificante cuanto más largo
# es.

VARIABLE_RETENCION = "BN_RETENCION_CONSULTAS_DIAS"
RETENCION_DIAS_DEFECTO = 90


def retencion_configurada() -> int:
    import os

    crudo = (os.environ.get(VARIABLE_RETENCION) or "").strip()
    if not crudo:
        return RETENCION_DIAS_DEFECTO
    try:
        dias = int(crudo)
    except ValueError:
        return RETENCION_DIAS_DEFECTO
    # Cero o negativo sería «borrar todo, siempre». No se acepta por variable de
    # entorno mal escrita: para no guardar nada hay que no registrar, que es
    # otra decisión y se toma en otro lado.
    return max(1, dias)


@dataclass(frozen=True)
class Purga:
    dias: int
    # Cuántas caen bajo la retención. En una simulación es lo que se borraría;
    # en una corrida de verdad es lo que se borró. Separarlo de `borradas` evita
    # el informe que dice «borradas 0» después de contar mil.
    candidatas: int
    borradas: int
    quedan: int
    mas_antigua: object | None = None
    simulada: bool = False
    # Las devoluciones caducan con la misma regla y en la misma corrida. Van
    # contadas aparte porque son otra tabla y porque, si alguna vez el número
    # queda en cero mientras la traza se purga, eso es el síntoma de que se
    # están dejando señales huérfanas atrás.
    devoluciones_candidatas: int = 0
    devoluciones_borradas: int = 0

    def a_dict(self) -> dict:
        return {
            "dias_de_retencion": self.dias,
            "candidatas": self.candidatas,
            "borradas": self.borradas,
            "devoluciones_candidatas": self.devoluciones_candidatas,
            "devoluciones_borradas": self.devoluciones_borradas,
            "quedan": self.quedan,
            "mas_antigua": self.mas_antigua.isoformat() if self.mas_antigua else None,
            "simulada": self.simulada,
        }


def purgar(conexion: Connection, *, dias: int | None = None, simular: bool = False) -> Purga:
    """Borra las consultas auditadas más viejas que la retención configurada.

    Corre con el rol de administración y no con el de la API: el lector puede
    insertar su traza y no puede borrar la de nadie, que es exactamente la
    separación que hace que el registro sirva como registro.
    """
    dias = retencion_configurada() if dias is None else max(1, dias)
    parametros = {"d": dias}
    cuantas = conexion.execute(
        text(
            "SELECT count(*) FROM consultas_auditadas "
            " WHERE ocurrido_en < now() - make_interval(days => :d)"
        ),
        parametros,
    ).scalar_one()
    if not simular and cuantas:
        conexion.execute(
            text(
                "DELETE FROM consultas_auditadas "
                " WHERE ocurrido_en < now() - make_interval(days => :d)"
            ),
            parametros,
        )
    # Lo que la persona contestó sobre esas respuestas caduca junto con ellas.
    caidas = borrar_devoluciones(conexion, dias=dias, simular=simular)
    quedan = conexion.execute(text("SELECT count(*) FROM consultas_auditadas")).scalar_one()
    mas_antigua = conexion.execute(
        text("SELECT min(ocurrido_en) FROM consultas_auditadas")
    ).scalar_one()
    return Purga(
        dias=dias,
        candidatas=int(cuantas),
        borradas=0 if simular else int(cuantas),
        quedan=int(quedan),
        mas_antigua=mas_antigua,
        simulada=simular,
        devoluciones_candidatas=caidas,
        devoluciones_borradas=0 if simular else caidas,
    )
