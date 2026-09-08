"""Lo que toda lectura curada tiene que cumplir, sin mirar la base.

Las lecturas de `docs/curaduria/` son la parte del sistema que escribe una
persona a mano, y son las que deciden si alguien accede a un derecho. Estas
comprobaciones no dicen nada sobre si la lectura jurídica es correcta —eso lo
decide quien revisa— sino sobre las trampas en las que es fácil caer escribiendo
una: una regla sin condición y sin explicar por qué, dos beneficios con el mismo
código, un árbol que no cumple el contrato.

El cargador comprueba lo demás —que cada cita esté adentro de la unidad que dice
citar— porque eso necesita el texto capturado.
"""

from __future__ import annotations

import collections
import json
import pathlib

import pytest

from backend_normativo.reglas.ast import validar_ast

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURAS = sorted((RAIZ / "docs" / "curaduria").glob("*.json"))

# Vocabularios del esquema. Se repiten acá a propósito: si alguien agrega un
# valor nuevo a la base, esta prueba lo obliga a decidir si las lecturas curadas
# también lo aceptan.
CATEGORIAS = {
    "APLICABILIDAD",
    "EXCLUSION",
    "EXCEPCION",
    "PRIORIDAD",
    "SALVAGUARDA",
    "REVOCACION",
    "SUSPENSION",
    "CESE",
    "SUBSANACION",
    "REHABILITACION",
    "COMPATIBILIDAD",
}
TIPOS_DE_PLAZO = {
    "VIGENCIA_JURIDICA",
    "CONVOCATORIA",
    "DURACION_BENEFICIO",
    "RENOVACION",
    "PRESENTACION_DOCUMENTAL",
    "RESPUESTA_ORGANISMO",
    "SUBSANACION",
    "RECURSO",
    "FECHA_PAGO",
}
TIPOS_DE_DIA = {"CORRIDO", "HABIL_ADMINISTRATIVO", "HABIL_JUDICIAL", "NO_INFORMADO"}
ROLES_DE_PERSONA = {
    "TITULAR",
    "CAUSANTE",
    "SOLICITANTE",
    "REPRESENTANTE",
    "CONVIVIENTE",
    "GRUPO_FAMILIAR",
}
TIPOS_DE_CUANTIA = {"FIJO", "FORMULA", "ESPECIE", "NO_INFORMADO"}


def test_hay_lecturas_curadas() -> None:
    """Sin esto, todo lo demás pasaría por vacuidad."""
    assert LECTURAS


@pytest.fixture(params=LECTURAS, ids=lambda r: r.name)
def lectura(request) -> dict:
    return json.loads(request.param.read_text(encoding="utf-8"))


def test_una_regla_sin_condicion_dice_por_que(lectura: dict) -> None:
    """Una regla sin AST y sin motivo es una regla que nadie sabe por qué no se
    formalizó. Dentro de seis meses, la única lectura posible es que alguien se
    olvidó."""
    for regla in lectura["reglas"]:
        if regla.get("ast") is None:
            assert regla.get("requiere_revision"), regla["clave"]
        if regla.get("requiere_revision"):
            motivo = regla.get("motivo_revision", "")
            assert len(motivo) >= 40, f"{regla['clave']}: motivo demasiado corto"


def test_cada_arbol_cumple_el_contrato(lectura: dict) -> None:
    """Validar es barato y ejecutar un árbol mal formado es caro: una comparación
    con el operador equivocado no falla, devuelve la respuesta contraria."""
    for regla in lectura["reglas"]:
        if regla.get("ast") is not None:
            validar_ast(regla["ast"])


def test_las_claves_de_regla_no_se_repiten(lectura: dict) -> None:
    """Una clave repetida hace que `excepcion_de` apunte a cualquiera de las dos."""
    claves = collections.Counter(r["clave"] for r in lectura["reglas"])
    assert [c for c, n in claves.items() if n > 1] == []


def test_una_excepcion_apunta_a_una_regla_de_la_misma_lectura(lectura: dict) -> None:
    claves = {r["clave"] for r in lectura["reglas"]}
    for regla in lectura["reglas"]:
        referida = regla.get("excepcion_de")
        if referida is not None:
            assert referida in claves, f"{regla['clave']} → {referida}"


def test_los_vocabularios_son_los_del_esquema(lectura: dict) -> None:
    """Un valor fuera del vocabulario lo rechaza la base al cargar. Fallar acá
    dice cuál es, en vez de un error de restricción con el nombre del índice."""
    for regla in lectura["reglas"]:
        assert regla["categoria"] in CATEGORIAS, regla["clave"]
    for poblacion in lectura.get("poblaciones", ()):
        assert poblacion["rol_persona"] in ROLES_DE_PERSONA, poblacion["codigo"]
    for plazo in lectura.get("plazos", ()):
        assert plazo["tipo"] in TIPOS_DE_PLAZO, plazo["clave"]
        assert plazo["tipo_dia"] in TIPOS_DE_DIA, plazo["clave"]
    if lectura.get("cuantia"):
        assert lectura["cuantia"]["tipo"] in TIPOS_DE_CUANTIA


def test_un_plazo_habil_declara_de_que_jurisdiccion_es_el_calendario(lectura: dict) -> None:
    """Un plazo hábil computado con el calendario de otra jurisdicción adelanta
    el vencimiento, que es el error que hace perder un plazo."""
    for plazo in lectura.get("plazos", ()):
        if plazo["tipo_dia"] in ("HABIL_ADMINISTRATIVO", "HABIL_JUDICIAL"):
            assert plazo.get("calendario_jurisdiccion"), plazo["clave"]


def test_cada_pieza_cita_una_unidad(lectura: dict) -> None:
    """Sin ruta de evidencia no hay nada que verificar contra el texto."""
    assert lectura["beneficio"]["ruta_evidencia"]
    for grupo in ("poblaciones", "reglas", "plazos"):
        for pieza in lectura.get(grupo, ()):
            assert pieza.get("ruta_evidencia"), pieza.get("clave") or pieza.get("codigo")
    if lectura.get("cuantia"):
        assert lectura["cuantia"]["ruta_evidencia"]


def test_una_cita_no_elide(lectura: dict) -> None:
    """Una cita con puntos suspensivos no está en ninguna unidad: el cargador la
    rechaza. Fallar acá dice cuál es antes de necesitar la base."""
    for grupo in ("reglas", "plazos"):
        for pieza in lectura.get(grupo, ()):
            literal = pieza["texto_literal"]
            assert "..." not in literal and "…" not in literal, pieza["clave"]


def test_ninguna_cita_se_come_a_otra_de_la_misma_lectura(lectura: dict) -> None:
    """Una cita que contiene a otra está recortada de más.

    Pasa cuando se cita desde una frase hasta el final de la unidad en vez de
    hasta donde termina la condición: la regla queda respaldada por un texto que
    dice también lo que dice la regla de al lado, y la evidencia deja de señalar
    qué parte del artículo la sostiene. El cargador no lo detecta —las dos citas
    están adentro de la unidad— así que se detecta acá.
    """
    citas = [
        (pieza["clave"], " ".join(pieza["texto_literal"].split()))
        for grupo in ("reglas", "plazos")
        for pieza in lectura.get(grupo, ())
    ]
    engullidas = [
        (clave, otra)
        for clave, texto in citas
        for otra, otro in citas
        if clave != otra and otro in texto and otro != texto
    ]
    assert engullidas == []


def test_ningun_codigo_de_beneficio_se_repite_entre_lecturas() -> None:
    """Dos lecturas con el mismo código serían el mismo beneficio en la base, y
    la segunda pisaría a la primera sin que nadie se entere."""
    codigos = collections.Counter(
        json.loads(ruta.read_text(encoding="utf-8"))["beneficio"]["codigo"] for ruta in LECTURAS
    )
    assert [c for c, n in codigos.items() if n > 1] == []
