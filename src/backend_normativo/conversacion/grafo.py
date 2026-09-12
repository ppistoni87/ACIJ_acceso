"""El recorrido de un turno, como grafo (P-025, §08.2 del plan).

El plan describe el flujo así: recepción y normalización, identificación de
intención, aclaración cuando sea necesaria, consulta de funciones y evidencias,
armado, verificación y emisión. Hasta acá eso vivía desparramado adentro de
`POST /v1/respuestas`, en una sola función que hacía todo seguido y no podía
detenerse a preguntar.

Acá está como grafo. Lo que gana no es elegancia: gana **poder parar**. Después
de evaluar, el turno puede terminar preguntando el único dato que cambia la
orientación en vez de contestar con lo que hay. Eso es el criterio 2 de P-025 y
no se puede escribir cómodo en una función lineal.

**Ningún nodo llama a un modelo.** Todos los pasos de este grafo son
deterministas: buscar, identificar el beneficio, evaluar las reglas, elegir la
pregunta. Cuando haya proveedor configurado, la redacción entra como un nodo más
y la política de modos no cambia. Se puede ejercer entero hoy, que es la razón
de construirlo ahora.

**No se usa el checkpointer de LangGraph, y es a propósito.** Sus
`checkpointers` persisten el estado completo del grafo, que incluye los mensajes.
La política de este proyecto dice que el historial no se guarda, y hay un CHECK
en la base que lo hace cumplir sobre `sesiones_conversacion`. El estado
conversacional vive ahí, con sus plazos; LangGraph orquesta y no persiste.

**LangSmith queda apagado.** `langgraph` arrastra `langsmith`, que envía trazas a
un servicio externo si encuentra su variable de entorno. Acá se apaga
explícitamente al importar: una consulta sobre un desalojo no se le manda a un
tercero por una variable que alguien dejó puesta en un `.env`.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, TypedDict

from sqlalchemy import Connection, text

# Antes de importar nada de langgraph: si la variable ya venía puesta, se
# desactiva igual. Es una decisión del servicio, no del entorno.
for _variable in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING"):
    os.environ[_variable] = "false"

from langgraph.graph import END, START, StateGraph  # noqa: E402

TRAZA_EXTERNA_APAGADA = True


class EstadoTurno(TypedDict, total=False):
    """Lo que viaja por el grafo durante un turno. No es lo que se persiste."""

    consulta: str
    jurisdiccion: str | None
    fecha: dt.date | None
    hechos: dict[str, Any]
    urgencia: dict | None
    fragmentos: list
    avisos: list[str]
    beneficio_id: uuid.UUID | None
    beneficio_codigo: str | None
    dictamen: Any
    pregunta: str | None
    motivo_sin_evaluar: str | None


@dataclass
class Turno:
    """El resultado de correr el grafo una vez."""

    urgencia: dict | None = None
    fragmentos: list = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    beneficio_codigo: str | None = None
    dictamen: Any = None
    pregunta: str | None = None
    motivo_sin_evaluar: str | None = None

    @property
    def espera_respuesta(self) -> bool:
        return self.pregunta is not None


# --- Nodos --------------------------------------------------------------------
#
# Cada uno recibe el estado y devuelve sólo lo que cambia. Se construyen con la
# conexión ya atada: el grafo se arma por pedido, no es un singleton, y así no
# hay estado compartido entre conversaciones.


def _nodo_recibir(_conexion):
    def recibir(estado: EstadoTurno) -> dict:
        """Antes que nada: si el mensaje parecía una emergencia, eso se sabe ya.

        Va primero y no depende de encontrar nada: alguien que escribe «estoy
        durmiendo en la calle» necesita lo mismo tenga el corpus lo que tenga.
        """
        from backend_normativo.conversacion.urgencia import detectar

        return {"urgencia": detectar(estado["consulta"]).a_dict()}

    return recibir


def _nodo_buscar(conexion, *, release_id, embebedor, limite):
    def buscar(estado: EstadoTurno) -> dict:
        from backend_normativo.recuperacion.busqueda import buscar as buscar_fragmentos

        hallazgo = buscar_fragmentos(
            conexion,
            estado["consulta"],
            release_id=release_id,
            embebedor=embebedor,
            limite=limite,
            jurisdiccion=estado.get("jurisdiccion"),
            as_of=estado.get("fecha"),
        )
        return {
            "fragmentos": hallazgo.fragmentos,
            "avisos": hallazgo.avisos_de_la_persona,
        }

    return buscar


# Un fragmento pertenece a una norma, y una norma puede crear beneficios. Con
# eso se pasa de «encontré este artículo» a «esto es sobre la beca de comedor»,
# que es lo que la persona vino a preguntar aunque no sepa el nombre.
BENEFICIOS_DE_LOS_FRAGMENTOS = """
SELECT b.id, b.codigo, count(*) AS fragmentos
  FROM chunks c
  JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id
  JOIN beneficio_normas bn ON bn.norma_version_id = nv.registro_version_id
  JOIN beneficio_versiones bv ON bv.registro_version_id = bn.beneficio_version_id
  JOIN registro_versiones rvb ON rvb.id = bv.registro_version_id
  JOIN beneficios b ON b.id = bv.beneficio_id
 WHERE c.id = ANY(:ids) AND rvb.estado_revision = 'PUBLISHED'
 GROUP BY b.id, b.codigo
 ORDER BY count(*) DESC, b.codigo
"""


def _nodo_identificar(conexion):
    def identificar(estado: EstadoTurno) -> dict:
        """De los fragmentos al beneficio del que hablan.

        Con un solo candidato se evalúa. Con varios **no se elige**: elegir por
        cantidad de fragmentos sería decidir por parecido cuál de dos programas
        le corresponde a alguien, que es justo lo que el plan prohíbe. Se deja
        dicho y el turno contesta con la evidencia, sin dictamen.
        """
        ids = [f.chunk_id for f in estado.get("fragmentos") or []]
        if not ids:
            return {"motivo_sin_evaluar": "no se recuperó ningún fragmento"}
        filas = conexion.execute(text(BENEFICIOS_DE_LOS_FRAGMENTOS), {"ids": ids}).mappings().all()
        if not filas:
            return {"motivo_sin_evaluar": "los textos no cuelgan de ningún beneficio publicado"}
        if len(filas) > 1:
            nombres = ", ".join(f["codigo"] for f in filas[:4])
            return {
                "motivo_sin_evaluar": (
                    f"la consulta toca más de un beneficio ({nombres}) y elegir uno por "
                    "parecido sería decidir por la persona"
                )
            }
        return {"beneficio_id": filas[0]["id"], "beneficio_codigo": filas[0]["codigo"]}

    return identificar


def _nodo_evaluar(conexion, *, release_id):
    def evaluar(estado: EstadoTurno) -> dict:
        from backend_normativo.api.routers.evaluaciones import (
            _reglas_publicadas,
            _resolver_parametro,
        )
        from backend_normativo.reglas.beneficio import evaluar_beneficio
        from backend_normativo.reglas.evaluacion import Evaluador, HechosDeclarados

        beneficio_id = estado.get("beneficio_id")
        if beneficio_id is None:
            return {}
        reglas = _reglas_publicadas(conexion, beneficio_id)
        if not reglas:
            return {"motivo_sin_evaluar": "el beneficio no tiene reglas publicadas"}
        hechos = HechosDeclarados(
            valores=estado.get("hechos") or {},
            fecha=estado.get("fecha") or dt.date.today(),
        )
        dictamen = evaluar_beneficio(
            reglas,
            hechos,
            Evaluador(resolver_parametro=_resolver_parametro(conexion, release_id)),
        )
        return {"dictamen": dictamen}

    return evaluar


def _nodo_aclarar(_conexion):
    def aclarar(estado: EstadoTurno) -> dict:
        """Una pregunta por turno, y la que cambia la orientación.

        Se toma la primera que el motor dejó pendiente. No se piden tres datos
        juntos: el plan lo dice y además es lo que hace que alguien abandone.
        """
        dictamen = estado.get("dictamen")
        faltantes = list(getattr(dictamen, "preguntas_faltantes", []) or [])
        return {"pregunta": faltantes[0]} if faltantes else {}

    return aclarar


def _hay_que_aclarar(estado: EstadoTurno) -> str:
    dictamen = estado.get("dictamen")
    if dictamen is None:
        return "responder"
    return "aclarar" if getattr(dictamen, "preguntas_faltantes", None) else "responder"


def construir(conexion: Connection, *, release_id, embebedor=None, limite: int = 5):
    """Arma el grafo del turno con la conexión y el corte ya atados."""
    grafo = StateGraph(EstadoTurno)
    grafo.add_node("recibir", _nodo_recibir(conexion))
    grafo.add_node(
        "buscar", _nodo_buscar(conexion, release_id=release_id, embebedor=embebedor, limite=limite)
    )
    grafo.add_node("identificar", _nodo_identificar(conexion))
    grafo.add_node("evaluar", _nodo_evaluar(conexion, release_id=release_id))
    grafo.add_node("aclarar", _nodo_aclarar(conexion))
    grafo.add_node("responder", lambda estado: {})

    grafo.add_edge(START, "recibir")
    grafo.add_edge("recibir", "buscar")
    grafo.add_edge("buscar", "identificar")
    grafo.add_edge("identificar", "evaluar")
    grafo.add_conditional_edges(
        "evaluar", _hay_que_aclarar, {"aclarar": "aclarar", "responder": "responder"}
    )
    grafo.add_edge("aclarar", END)
    grafo.add_edge("responder", END)
    return grafo.compile()


def correr(
    conexion: Connection,
    consulta: str,
    *,
    release_id,
    embebedor=None,
    limite: int = 5,
    jurisdiccion: str | None = None,
    fecha: dt.date | None = None,
    hechos: dict | None = None,
) -> Turno:
    """Corre un turno completo y devuelve lo que el frente necesita mostrar."""
    salida = construir(conexion, release_id=release_id, embebedor=embebedor, limite=limite).invoke(
        {
            "consulta": consulta,
            "jurisdiccion": jurisdiccion,
            "fecha": fecha,
            "hechos": hechos or {},
        }
    )
    return Turno(
        urgencia=salida.get("urgencia"),
        fragmentos=salida.get("fragmentos") or [],
        avisos=salida.get("avisos") or [],
        beneficio_codigo=salida.get("beneficio_codigo"),
        dictamen=salida.get("dictamen"),
        pregunta=salida.get("pregunta"),
        motivo_sin_evaluar=salida.get("motivo_sin_evaluar"),
    )
