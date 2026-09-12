"""Qué puede hacer ahora quien preguntó (P-030, criterio 3).

Una orientación que termina en «estas son las condiciones» deja a la persona
exactamente donde estaba: sabiendo más y sin saber qué hacer. Los próximos pasos
son lo que convierte una lectura en algo accionable.

**Cada paso se sostiene en algo.** No hay consejos generales. Un paso sale de una
de tres cosas: un dato que la conversación necesita, una excepción que la norma
prevé y podría cambiar el resultado, o un trámite publicado con sus pasos
curados. Si nada de eso hay, no hay pasos, y se dice.

**Nada de esto inicia nada.** El criterio lo pide con todas las letras y la
pantalla lo repite: esto no crea expediente, no equivale a presentar un trámite
y no garantiza ninguna prestación. Un sistema que le hace creer a alguien que ya
hizo el trámite le hace perder el plazo.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Connection, text

# De dónde sale cada paso. Viaja con el paso porque no es lo mismo «esto lo
# necesito yo para poder seguir mirando» que «esto lo pide el organismo».
DE_LA_CONVERSACION = "conversacion"
DE_LA_NORMA = "norma"
DEL_TRAMITE = "tramite"


@dataclass(frozen=True)
class Paso:
    """Algo concreto que hacer, y en qué se apoya."""

    accion: str
    origen: str
    respaldo: str | None = None

    def a_dict(self) -> dict:
        return {"accion": self.accion, "origen": self.origen, "respaldo": self.respaldo}


@dataclass(frozen=True)
class ProximosPasos:
    pasos: list[Paso]
    # El corpus no tiene ningún trámite publicado para este beneficio. Se dice:
    # callarlo haría pasar por «no hay nada que hacer» lo que en realidad es
    # «no lo tengo cargado».
    sin_tramite_publicado: bool
    aclaracion: str = (
        "Nada de esto inicia un trámite ni crea un expediente. Es lo que podés hacer vos; "
        "presentarlo sigue siendo un paso aparte, y quien decide es el organismo."
    )

    def a_dict(self) -> dict:
        return {
            "pasos": [p.a_dict() for p in self.pasos],
            "sin_tramite_publicado": self.sin_tramite_publicado,
            "aclaracion": self.aclaracion,
        }


# Los pasos que el organismo pide, cuando están curados y publicados. Hoy el
# corpus no tiene ninguno: los seis trámites cargados siguen en CANDIDATE y sin
# beneficio asociado. La consulta existe igual y se enciende sola el día que
# curación los publique.
PASOS_DEL_TRAMITE = """
SELECT t.titulo, tp.orden, tp.accion
  FROM tramites t
  JOIN tramite_versiones tv ON tv.tramite_id = t.id
  JOIN registro_versiones rv ON rv.id = tv.registro_version_id
  JOIN tramite_pasos tp ON tp.tramite_version_id = tv.registro_version_id
 WHERE t.beneficio_id = :b AND rv.estado_revision = 'PUBLISHED'
   AND (CAST(:r AS uuid) IS NULL
        OR EXISTS (SELECT 1 FROM release_versiones m
                    WHERE m.registro_version_id = rv.id AND m.release_id = :r))
 ORDER BY t.titulo, tp.orden
"""


def armar(
    conexion: Connection,
    *,
    beneficio_id=None,
    release_id=None,
    pregunta=None,
    subsanaciones=(),
) -> ProximosPasos:
    """Los pasos que se pueden justificar, en el orden en que conviene hacerlos.

    Primero lo que depende de la persona y es gratis —contestar un dato,
    averiguar si una excepción le alcanza—, después lo que exige moverse. Poner
    el trámite antes que la pregunta haría salir a alguien a hacer una cola que
    a lo mejor no le hace falta.
    """
    pasos: list[Paso] = []

    if pregunta is not None:
        pasos.append(
            Paso(
                accion=(
                    "Contestame lo que te pregunté acá arriba: con ese dato puedo decirte "
                    "algo más preciso, y no tenés que ir a ningún lado para eso."
                ),
                origen=DE_LA_CONVERSACION,
                respaldo=getattr(pregunta, "texto_literal", None),
            )
        )

    # Las excepciones que todavía podrían cambiar el resultado. Sólo las que no
    # están resueltas: una que ya se sabe que no alcanza no es un paso, es una
    # puerta cerrada, y mandar a alguien a golpearla es hacerle perder el día.
    for salida in subsanaciones:
        for texto, estado in getattr(salida, "excepciones", ()):
            if getattr(estado, "value", estado) != "UNKNOWN":
                continue
            pasos.append(
                Paso(
                    accion=(
                        "Fijate si te alcanza esta excepción que prevé la norma. Si te "
                        "alcanza, lo que hoy te frena deja de frenarte."
                    ),
                    origen=DE_LA_NORMA,
                    respaldo=texto,
                )
            )

    sin_tramite = True
    if beneficio_id is not None:
        filas = (
            conexion.execute(text(PASOS_DEL_TRAMITE), {"b": beneficio_id, "r": release_id})
            .mappings()
            .all()
        )
        sin_tramite = not filas
        for fila in filas:
            pasos.append(Paso(accion=fila["accion"], origen=DEL_TRAMITE, respaldo=fila["titulo"]))

    return ProximosPasos(pasos=pasos, sin_tramite_publicado=sin_tramite)
