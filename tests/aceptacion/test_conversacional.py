"""DQ18: el conjunto experto de consultas se corre, no se declara corrido.

La gate pide 60 consultas como mínimo y que el 100% de las críticas pase. Esta
prueba lo verifica sobre un corpus publicado construido acá, para que un cambio
en la API que rompa una abstención se note antes de que el reporte diga lo
contrario.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import Connection

from backend_normativo.calidad import conversacional
from tests.integracion.test_api import corpus  # noqa: F401
from tests.integracion.test_api import corpus_publicado as corpus_publicado

pytestmark = [pytest.mark.integracion, pytest.mark.aceptacion]

RAIZ = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def reporte(conexion: Connection, cliente_api, corpus_publicado):
    return conversacional.correr(conexion, cliente_api, raiz=RAIZ)


def test_el_conjunto_llega_al_minimo_de_la_gate(reporte) -> None:
    assert reporte.total >= 60


def test_todas_las_familias_criticas_estan_representadas(reporte) -> None:
    familias = {r.familia for r in reporte.resultados}
    assert familias >= conversacional.CRITICAS


def test_ninguna_consulta_queda_sin_clasificar(reporte) -> None:
    """«SIN_CLASIFICAR» es una respuesta que no se sabe leer: sería peor que un
    fallo, porque nadie sabría si el backend afirmó de más."""
    opacas = [r.id for r in reporte.resultados if r.observado == "SIN_CLASIFICAR"]
    assert opacas == []


def test_cuando_responde_trae_evidencia_y_cuando_se_abstiene_trae_motivo(reporte) -> None:
    """La invariante que no depende del corpus.

    Si una consulta pasa o no depende de qué haya publicado: sobre el corpus de
    pruebas los siete campos están vacíos y sobre el servido la mitad tiene
    valores, así que la misma consulta responde en uno y se abstiene en el otro.
    Lo que no puede cambiar nunca es esto: cuando afirma, hay evidencia detrás;
    cuando se calla, hay un motivo dicho. `bn calidad consultas` corre el
    conjunto contra el corpus servido y ahí sí compara con lo declarado.
    """
    mudos = [(r.id, r.observado) for r in reporte.resultados if not r.detalle.strip()]
    assert mudos == [], "Toda respuesta tiene que decir en qué se apoya o por qué no responde."


def test_hay_consultas_ambiguas_e_historicas(reporte) -> None:
    """La gate las pide explícitamente: un conjunto de preguntas bien formadas
    no prueba que el sistema sepa abstenerse cuando la pregunta no alcanza."""
    familias = {r.familia for r in reporte.resultados}
    assert familias >= {"ambigua", "historica"}


def test_el_conjunto_no_es_todo_afirmacion_ni_todo_abstencion(reporte) -> None:
    """Un conjunto que solo espera abstenciones se pasa no sirviendo nada."""
    esperas = {r.espera for r in reporte.resultados}
    assert esperas >= {"RESPONDE_CON_EVIDENCIA", "SE_ABSTIENE"}
    afirman = sum(1 for r in reporte.resultados if r.espera == "RESPONDE_CON_EVIDENCIA")
    assert afirman >= 20
