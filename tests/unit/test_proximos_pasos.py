"""Los próximos pasos: que cada uno se sostenga en algo y que ninguno inicie nada.

Una orientación que termina en «estas son las condiciones» deja a la persona
donde estaba. Lo que se prueba acá es que los pasos que aparecen tengan de dónde
salir, que los que no sirven no aparezcan, y que la falta de trámite publicado
se declare en vez de leerse como «no hay nada que hacer».
"""

from __future__ import annotations

from dataclasses import dataclass

from backend_normativo.conversacion import pasos as pas
from backend_normativo.reglas.evaluacion import Ternario


@dataclass
class SalidaFalsa:
    excepciones: list


@dataclass
class PreguntaFalsa:
    texto_literal: str


def test_sin_nada_que_hacer_no_se_inventa_un_paso() -> None:
    salida = pas.armar(None)
    assert salida.pasos == []
    assert "inicia un trámite ni crea un expediente" in salida.aclaracion


def test_la_pregunta_pendiente_es_el_primer_paso_y_lleva_su_respaldo() -> None:
    """Y va primero porque es gratis: no obliga a nadie a moverse."""
    salida = pas.armar(None, pregunta=PreguntaFalsa("La norma pide dos años de residencia."))

    [paso] = salida.pasos
    assert paso.origen == pas.DE_LA_CONVERSACION
    assert paso.respaldo == "La norma pide dos años de residencia."


def test_una_excepcion_sin_resolver_es_un_paso_y_una_resuelta_no() -> None:
    """Mandar a alguien a golpear una puerta que ya se sabe cerrada es hacerle
    perder el día; esconderle una que puede estar abierta es peor."""
    salida = pas.armar(
        None,
        subsanaciones=[
            SalidaFalsa([("Excepción que podría alcanzarte.", Ternario.UNKNOWN)]),
            SalidaFalsa([("Excepción que no te alcanza.", Ternario.FALSE)]),
            SalidaFalsa([("Excepción que ya te alcanza.", Ternario.TRUE)]),
        ],
    )

    assert [p.respaldo for p in salida.pasos] == ["Excepción que podría alcanzarte."]
    assert salida.pasos[0].origen == pas.DE_LA_NORMA


def test_primero_lo_que_no_obliga_a_moverse() -> None:
    """Poner el trámite antes que la pregunta haría salir a alguien a hacer una
    cola que a lo mejor no le hace falta."""
    salida = pas.armar(
        None,
        pregunta=PreguntaFalsa("Un dato que falta."),
        subsanaciones=[SalidaFalsa([("Una excepción por averiguar.", Ternario.UNKNOWN)])],
    )

    assert [p.origen for p in salida.pasos] == [pas.DE_LA_CONVERSACION, pas.DE_LA_NORMA]


def test_sin_beneficio_no_se_afirma_que_falte_el_tramite() -> None:
    """`sin_tramite_publicado` es una afirmación sobre un beneficio concreto.

    Sin beneficio identificado no hay sobre qué afirmarla, y devolverla en
    `False` diría que el trámite está cargado cuando ni siquiera se buscó.
    """
    assert pas.armar(None).sin_tramite_publicado is True
