"""El turno como grafo: lo que gana es poder parar a preguntar.

Hasta acá el recorrido vivía adentro de una función lineal que hacía todo
seguido y contestaba con lo que tuviera. El criterio 2 de P-025 pide otra cosa:
que cuando falte el dato que cambia la orientación, el turno termine
preguntándolo. Eso es una bifurcación, y por eso hay un grafo.
"""

from __future__ import annotations

import datetime as dt
from typing import ClassVar

import pytest

from backend_normativo.conversacion import grafo

pytestmark = pytest.mark.integracion


def test_la_traza_externa_esta_apagada() -> None:
    """`langgraph` arrastra `langsmith`, que manda trazas afuera si la dejan.

    Una consulta sobre un desalojo no se le manda a un tercero porque alguien
    dejó una variable puesta en un `.env`.
    """
    import os

    from langsmith import utils

    assert grafo.TRAZA_EXTERNA_APAGADA
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"
    assert utils.tracing_is_enabled() is False


def test_el_grafo_no_usa_el_checkpointer_de_langgraph() -> None:
    """Sus checkpointers persisten el estado entero, mensajes incluidos.

    El historial no se guarda —hay un CHECK en la base que lo impide— así que la
    persistencia es nuestra y LangGraph sólo orquesta.
    """
    compilado = grafo.construir(None, release_id=None)
    assert compilado.checkpointer is None, (
        "un checkpointer de LangGraph guardaría el estado entero del grafo, mensajes "
        "incluidos, que es justo lo que la política dice que no se guarda"
    )
    assert compilado.store is None


def test_un_turno_reconoce_la_urgencia_antes_que_nada(conexion, corpus_publicado) -> None:
    """El primer nodo no depende de que la búsqueda encuentre algo."""
    from backend_normativo.api.dependencias import release_vigente

    corte = release_vigente(conexion, dt.datetime.now(dt.UTC))
    turno = grafo.correr(conexion, "estoy durmiendo en la calle con mi bebé", release_id=corte)
    assert turno.urgencia is not None
    assert turno.urgencia["clase"] in {"CALLE", "NINEZ"}


def test_un_turno_devuelve_fragmentos_citables(conexion, corpus_publicado) -> None:
    from backend_normativo.api.dependencias import release_vigente

    corte = release_vigente(conexion, dt.datetime.now(dt.UTC))
    turno = grafo.correr(conexion, "beneficiarios del programa", release_id=corte)
    assert turno.fragmentos, "sin fragmentos no hay nada que citar"


def test_sin_beneficio_publicado_no_hay_dictamen_y_se_dice_por_que(
    conexion, corpus_publicado
) -> None:
    """No evaluar es una respuesta, siempre que se diga el motivo."""
    from backend_normativo.api.dependencias import release_vigente

    corte = release_vigente(conexion, dt.datetime.now(dt.UTC))
    turno = grafo.correr(conexion, "beneficiarios del programa", release_id=corte)
    assert turno.dictamen is None
    assert turno.motivo_sin_evaluar
    assert not turno.espera_respuesta


def test_el_grafo_tiene_la_bifurcacion_que_permite_preguntar() -> None:
    """Es la razón de ser del grafo: después de evaluar puede parar."""
    grafo_compilado = grafo.construir(None, release_id=None)
    nodos = set(grafo_compilado.get_graph().nodes)
    assert {"recibir", "buscar", "identificar", "evaluar", "aclarar", "responder"} <= nodos


def test_una_pregunta_por_turno() -> None:
    """Pedir tres datos juntos es lo que hace que alguien abandone."""

    class DictamenFalso:
        preguntas_faltantes: ClassVar[list[str]] = [
            "ingreso_mensual_del_hogar",
            "edad",
            "tiene_hijos",
        ]

    aclarar = grafo._nodo_aclarar(None)
    assert aclarar({"dictamen": DictamenFalso()}) == {"pregunta": "ingreso_mensual_del_hogar"}


def test_sin_preguntas_pendientes_no_se_inventa_una() -> None:
    class DictamenCompleto:
        preguntas_faltantes: ClassVar[list[str]] = []

    assert grafo._nodo_aclarar(None)({"dictamen": DictamenCompleto()}) == {}
    assert grafo._hay_que_aclarar({"dictamen": DictamenCompleto()}) == "responder"
    assert grafo._hay_que_aclarar({"dictamen": None}) == "responder"
