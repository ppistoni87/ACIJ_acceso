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
    rehusados: list[str]
    orientar: bool
    beneficio_elegido: str | None
    urgencia: dict | None
    hallazgo: Any
    fragmentos: list
    avisos: list[str]
    beneficio_id: uuid.UUID | None
    beneficio_codigo: str | None
    beneficio_nombre: str | None
    reglas: list
    dictamen: Any
    pregunta: Any
    sin_preguntar: int
    motivo_sin_evaluar: str | None
    candidatos: list[dict]


@dataclass
class Turno:
    """El resultado de correr el grafo una vez."""

    urgencia: dict | None = None
    hallazgo: Any = None
    fragmentos: list = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    beneficio_id: uuid.UUID | None = None
    beneficio_codigo: str | None = None
    beneficio_nombre: str | None = None
    dictamen: Any = None
    pregunta: Any = None
    sin_preguntar: int = 0
    motivo_sin_evaluar: str | None = None
    candidatos: list[dict] = field(default_factory=list)

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


def _nodo_buscar(conexion, *, release_id, embebedor, limite, beneficio=None, known_at=None):
    def buscar(estado: EstadoTurno) -> dict:
        from backend_normativo.recuperacion.busqueda import buscar as buscar_fragmentos

        hallazgo = buscar_fragmentos(
            conexion,
            estado["consulta"],
            release_id=release_id,
            embebedor=embebedor,
            limite=limite,
            jurisdiccion=estado.get("jurisdiccion"),
            beneficio=beneficio,
            as_of=estado.get("fecha"),
            known_at=known_at,
        )
        # El hallazgo entero viaja, no sólo los fragmentos: lleva los avisos de
        # quien opera y si lo encontrado se parece nada más. Quedárselo evita
        # que quien arme la respuesta tenga que volver a buscar.
        return {
            "hallazgo": hallazgo,
            "fragmentos": hallazgo.fragmentos,
            "avisos": hallazgo.avisos_de_la_persona,
        }

    return buscar


# Un fragmento pertenece a una norma, y una norma puede crear beneficios. Con
# eso se pasa de «encontré este artículo» a «esto es sobre la beca de comedor»,
# que es lo que la persona vino a preguntar aunque no sepa el nombre.
BENEFICIOS_DE_LOS_FRAGMENTOS = """
SELECT b.id, b.codigo, b.nombre, count(*) AS fragmentos
  FROM chunks c
  JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id
  JOIN beneficio_normas bn ON bn.norma_version_id = nv.registro_version_id
  JOIN beneficio_versiones bv ON bv.registro_version_id = bn.beneficio_version_id
  JOIN registro_versiones rvb ON rvb.id = bv.registro_version_id
  JOIN beneficios b ON b.id = bv.beneficio_id
 WHERE c.id = ANY(:ids) AND rvb.estado_revision = 'PUBLISHED'
 GROUP BY b.id, b.codigo, b.nombre
 ORDER BY count(*) DESC, b.codigo
"""


# Por qué un turno no pudo dar orientación. Son códigos, no frases: la frase la
# escribe la pantalla, que es la que sabe con qué palabras se lo dice a alguien.
SIN_FRAGMENTOS = "sin_fragmentos"
SIN_BENEFICIO = "sin_beneficio"
VARIOS_BENEFICIOS = "varios_beneficios"
SIN_REGLAS = "sin_reglas"


# El beneficio que la persona eligió cuando la consulta tocaba varios. Se busca
# por código y **dentro del corte con el que se está contestando**: elegir uno
# no lo deja elegido para siempre, y resolverlo contra una versión de otro corte
# serviría condiciones que el corte de hoy no sostiene.
BENEFICIO_ELEGIDO = """
SELECT b.id, b.codigo, b.nombre
  FROM beneficios b
  JOIN beneficio_versiones bv ON bv.beneficio_id = b.id
  JOIN registro_versiones rv ON rv.id = bv.registro_version_id
 WHERE b.codigo = :c AND rv.estado_revision = 'PUBLISHED'
   AND (CAST(:r AS uuid) IS NULL
        OR EXISTS (SELECT 1 FROM release_versiones m
                    WHERE m.registro_version_id = rv.id AND m.release_id = :r))
 LIMIT 1
"""


def _nodo_identificar(conexion, *, release_id=None):
    def identificar(estado: EstadoTurno) -> dict:
        """De los fragmentos al beneficio del que hablan.

        Con un solo candidato se evalúa. Con varios **no se elige**: elegir por
        cantidad de fragmentos sería decidir por parecido cuál de dos programas
        le corresponde a alguien, que es justo lo que el plan prohíbe. Se
        devuelven los candidatos para que elija la persona, que es de quien es
        la decisión, y hasta que elija el turno contesta con la evidencia.

        Si ya eligió, eso manda: no se vuelve a adivinar en cada mensaje.
        """
        elegido = estado.get("beneficio_elegido")
        if elegido:
            fila = (
                conexion.execute(text(BENEFICIO_ELEGIDO), {"c": elegido, "r": release_id})
                .mappings()
                .first()
            )
            if fila is not None:
                return {
                    "beneficio_id": fila["id"],
                    "beneficio_codigo": fila["codigo"],
                    "beneficio_nombre": fila["nombre"],
                }
            # El código elegido ya no está publicado —cambió el corte—. No se
            # sigue con él ni se elige otro por parecido: se vuelve a preguntar.

        ids = [f.chunk_id for f in estado.get("fragmentos") or []]
        if not ids:
            return {"motivo_sin_evaluar": SIN_FRAGMENTOS}
        filas = conexion.execute(text(BENEFICIOS_DE_LOS_FRAGMENTOS), {"ids": ids}).mappings().all()
        if not filas:
            return {"motivo_sin_evaluar": SIN_BENEFICIO}
        if len(filas) > 1:
            # Los nombres, no los códigos: `AR.AUH` es cómo lo llamamos nosotros.
            return {
                "motivo_sin_evaluar": VARIOS_BENEFICIOS,
                "candidatos": [{"codigo": f["codigo"], "nombre": f["nombre"]} for f in filas[:4]],
            }
        return {
            "beneficio_id": filas[0]["id"],
            "beneficio_codigo": filas[0]["codigo"],
            "beneficio_nombre": filas[0]["nombre"],
        }

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
            return {"motivo_sin_evaluar": SIN_REGLAS}
        hechos = HechosDeclarados(
            valores=estado.get("hechos") or {},
            fecha=estado.get("fecha") or dt.date.today(),
        )
        dictamen = evaluar_beneficio(
            reglas,
            hechos,
            Evaluador(resolver_parametro=_resolver_parametro(conexion, release_id)),
        )
        # Las reglas siguen en el estado: la pregunta que viene después se arma
        # con el texto literal de la que dejó el dato sin saber.
        return {"dictamen": dictamen, "reglas": reglas}

    return evaluar


def _nodo_aclarar(_conexion):
    def aclarar(estado: EstadoTurno) -> dict:
        """Una pregunta por turno, y la que cambia la orientación.

        Se toma la primera que el motor dejó pendiente. No se piden tres datos
        juntos: el plan lo dice y además es lo que hace que alguien abandone.
        """
        from backend_normativo.conversacion.preguntas import pendientes, sin_preguntar

        reglas = estado.get("reglas") or []
        dictamen = estado.get("dictamen")
        rehusados = estado.get("rehusados") or ()
        preguntas = pendientes(reglas, dictamen, rehusados=rehusados)
        # Lo que falta y no se puede preguntar se cuenta igual: es información
        # que la orientación no tiene, y eso se dice.
        salida = {"sin_preguntar": sin_preguntar(reglas, dictamen, rehusados=rehusados)}
        if preguntas:
            salida["pregunta"] = preguntas[0]
        return salida

    return aclarar


def _hay_que_orientar(estado: EstadoTurno) -> str:
    """Sin conversación abierta no se identifica ni se evalúa, y no es una
    optimización: la orientación se sostiene en hechos que la persona confirma, y
    sin dónde guardarlos la pregunta no tendría a dónde volver. Se contesta con
    la evidencia, que es lo que hay.
    """
    return "identificar" if estado.get("orientar") else "responder"


def _hay_que_aclarar(estado: EstadoTurno) -> str:
    """Se pregunta sólo si queda algo por preguntar que la persona no rehusó.

    Un dato rehusado sigue faltando para el motor —y así se muestra—, pero no
    vuelve a la pantalla como pregunta: ya lo contestó diciendo que no quiere
    contestarlo.
    """
    dictamen = estado.get("dictamen")
    if dictamen is None:
        return "responder"
    faltantes = set(getattr(dictamen, "preguntas_faltantes", None) or ())
    return "aclarar" if faltantes - set(estado.get("rehusados") or ()) else "responder"


def construir(
    conexion: Connection,
    *,
    release_id,
    embebedor=None,
    limite: int = 5,
    beneficio=None,
    known_at=None,
):
    """Arma el grafo del turno con la conexión y el corte ya atados."""
    grafo = StateGraph(EstadoTurno)
    grafo.add_node("recibir", _nodo_recibir(conexion))
    grafo.add_node(
        "buscar",
        _nodo_buscar(
            conexion,
            release_id=release_id,
            embebedor=embebedor,
            limite=limite,
            beneficio=beneficio,
            known_at=known_at,
        ),
    )
    grafo.add_node("identificar", _nodo_identificar(conexion, release_id=release_id))
    grafo.add_node("evaluar", _nodo_evaluar(conexion, release_id=release_id))
    grafo.add_node("aclarar", _nodo_aclarar(conexion))
    grafo.add_node("responder", lambda estado: {})

    grafo.add_edge(START, "recibir")
    grafo.add_edge("recibir", "buscar")
    grafo.add_conditional_edges(
        "buscar", _hay_que_orientar, {"identificar": "identificar", "responder": "responder"}
    )
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
    rehusados: list[str] | None = None,
    beneficio: str | None = None,
    known_at=None,
    orientar: bool = True,
    beneficio_elegido: str | None = None,
) -> Turno:
    """Corre un turno completo y devuelve lo que el frente necesita mostrar."""
    compilado = construir(
        conexion,
        release_id=release_id,
        embebedor=embebedor,
        limite=limite,
        beneficio=beneficio,
        known_at=known_at,
    )
    salida = compilado.invoke(
        {
            "consulta": consulta,
            "jurisdiccion": jurisdiccion,
            "fecha": fecha,
            "hechos": hechos or {},
            "rehusados": list(rehusados or ()),
            "orientar": orientar,
            "beneficio_elegido": beneficio_elegido,
        }
    )
    return Turno(
        urgencia=salida.get("urgencia"),
        hallazgo=salida.get("hallazgo"),
        fragmentos=salida.get("fragmentos") or [],
        avisos=salida.get("avisos") or [],
        beneficio_id=salida.get("beneficio_id"),
        beneficio_codigo=salida.get("beneficio_codigo"),
        beneficio_nombre=salida.get("beneficio_nombre"),
        dictamen=salida.get("dictamen"),
        pregunta=salida.get("pregunta"),
        sin_preguntar=salida.get("sin_preguntar") or 0,
        motivo_sin_evaluar=salida.get("motivo_sin_evaluar"),
        candidatos=salida.get("candidatos") or [],
    )
