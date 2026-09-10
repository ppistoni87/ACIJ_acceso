"""Una evidencia repetida no detiene al curador que la busca.

La evidencia es inmutable y se direcciona por contenido: dos curadores que citan
el mismo fragmento de la misma unidad escriben filas equivalentes, y eso no es
un error. Pedir exactamente una fila convertía ese empate —que no cambia nada de
lo que se afirma— en la caída del comando entero, y con él de la población.

Es el mismo defecto que ya había roto la evaluación de los siete campos. Estaba
en cinco lugares más, así que se comprueba de una vez sobre todos.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[2] / "src" / "backend_normativo"

INICIO = "SELECT id FROM evidencias WHERE"
# Lo que sigue a la consulta hasta que se ejecuta: alcanza para ver si ordena y
# si pide una fila única.
LARGO_DE_LA_LLAMADA = 500

# Si el código deja de escribir la consulta así, esta prueba no está mirando
# nada. El número está para que ese caso falle en vez de pasar en silencio.
BUSQUEDAS_CONOCIDAS = 8


def _busquedas() -> list[tuple[str, str]]:
    encontradas = []
    for archivo in sorted(RAIZ.rglob("*.py")):
        texto = archivo.read_text(encoding="utf-8")
        for coincidencia in re.finditer(re.escape(INICIO), texto):
            linea = texto[: coincidencia.start()].count("\n") + 1
            encontradas.append(
                (
                    f"{archivo.relative_to(RAIZ)}:{linea}",
                    texto[coincidencia.start() : coincidencia.start() + LARGO_DE_LA_LLAMADA],
                )
            )
    return encontradas


def test_estan_todas_las_busquedas_de_evidencia() -> None:
    """Una prueba que no encuentra qué mirar pasa siempre."""
    assert len(_busquedas()) == BUSQUEDAS_CONOCIDAS


def test_ninguna_busqueda_de_evidencia_pide_una_fila_unica_sin_ordenar() -> None:
    """El invariante se sostiene sobre el código, no sobre una corrida.

    Reproducir el empate exige montar dos curadores sobre la misma unidad, y
    montarlo seis veces deja seis pruebas que envejecen por separado. Lo que hay
    que sostener es más simple: una búsqueda de evidencia que no ordena no puede
    pedir una fila única.
    """
    sin_ordenar = [
        donde
        for donde, llamada in _busquedas()
        if "scalar_one" in llamada and "ORDER BY" not in llamada
    ]
    assert sin_ordenar == [], (
        "Estas búsquedas piden una fila única de `evidencias` sin ordenar: dos curadores que "
        f"citen la misma unidad las hacen fallar y detienen el comando. {sin_ordenar}"
    )
