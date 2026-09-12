"""Marcado que viaja **dentro** del texto, no alrededor de él.

Una fuente publica su HTML escapado dentro de la propia página: la captura de
D10 tiene catorce `&lt;p&gt;` contra diez `<p>` reales. El extractor hace lo
correcto —decodifica la entidad— y el resultado es que el marcado queda como
contenido, y termina en la pantalla de quien pregunta por sus derechos:

    <p>CLÁUSULA TRANSITORIA de la Ley 6935: establece que…</p>

No es que el extractor no limpie: limpia la capa que le toca. Lo que faltaba era
mirar la segunda.
"""

from __future__ import annotations

import pytest

from backend_normativo.ingesta.extraccion import hay_marcado, limpiar_marcado


def test_se_saca_el_parrafo_que_vino_escapado() -> None:
    sucio = "<p>CLÁUSULA TRANSITORIA de la Ley 6935: establece que rige el Decreto 690/06.</p>"
    limpio, se_limpio = limpiar_marcado(sucio)
    assert se_limpio
    assert limpio == "CLÁUSULA TRANSITORIA de la Ley 6935: establece que rige el Decreto 690/06."


def test_se_sacan_las_etiquetas_que_aparecieron_de_verdad() -> None:
    """`style`, `br`, `details` y `p`: las cuatro que hay en el corpus."""
    for sucio, esperado in [
        ("Uno<br>Dos", "Uno Dos"),
        ("<details>Anexo I</details>", "Anexo I"),
        ("<style>.x{color:red}</style>Art. 1", "Art. 1"),
        ("<p>Art. 2</p><p>Art. 3</p>", "Art. 2 Art. 3"),
    ]:
        limpio, se_limpio = limpiar_marcado(sucio)
        assert se_limpio
        assert limpio == esperado


def test_un_texto_legal_normal_no_se_toca() -> None:
    """El arreglo no puede pasarle un parser encima a toda la norma."""
    for intacto in [
        "Art. 5°.- La prestación será de $ 100.000 mensuales.",
        "Se aplica a menores de 18 años.",
        "El plazo es de 30 días hábiles.",
    ]:
        limpio, se_limpio = limpiar_marcado(intacto)
        assert not se_limpio
        assert limpio == intacto


@pytest.mark.parametrize(
    "texto",
    [
        "el monto debe ser < 3 salarios",
        "a < b y b > c",
        "la condición 5 <= 10 se cumple",
    ],
)
def test_un_menor_que_no_es_una_etiqueta(texto: str) -> None:
    """Una norma puede decir «menor que». Eso no es marcado y no se toca.

    Por eso el reconocimiento exige un nombre de etiqueta conocido y no
    cualquier cosa entre signos: pasarle un parser de HTML a todo el texto
    legal rompería exactamente lo que hay que cuidar.
    """
    limpio, se_limpio = limpiar_marcado(texto)
    assert not se_limpio
    assert limpio == texto


def test_se_puede_preguntar_sin_limpiar() -> None:
    """El control de publicación necesita detectar sin modificar."""
    assert hay_marcado("<p>Art. 1</p>")
    assert not hay_marcado("Art. 1: el monto es < 5 salarios")
