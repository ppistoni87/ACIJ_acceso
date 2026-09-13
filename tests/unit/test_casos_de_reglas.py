"""Los casos que cada regla ejecutable declara, y cuántas todavía no los declaran.

Doce de las catorce reglas de exclusión del corpus tenían la polaridad
invertida: el árbol decía «la remuneración está entre el piso y el techo» y la
categoría decía EXCLUSION, así que el motor le habría contestado a quien cobra
dentro de la banda —el que accede— que una regla explícita lo excluye.

Ninguna prueba lo agarró, y no por descuido: las del motor comprueban que `all`,
`any` y `not` se evalúen bien, y se evaluaban bien. El error estaba en la
traducción del texto legal al árbol, que ninguna prueba de unidad puede mirar.
Lo único que lo detecta es preguntarle al árbol por un caso donde el texto no
deje dudas, y eso es lo que estas pruebas corren.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from backend_normativo.db.vocabularios import CategoriaRegla
from backend_normativo.reglas.casos import (
    CATEGORIAS_DE_ACCESO,
    CasoInvalido,
    Desvio,
    correr,
    exigir,
)

LECTURAS = sorted(pathlib.Path("docs/curaduria").glob("*.json"))

# Cuántas reglas de acceso ejecutables todavía no declaran casos. Es un
# trinquete: el número solo puede bajar. No se exige que sea cero porque
# escribir 66 lecturas legales de una sentada, para que el cargador deje de
# quejarse, sería meter interpretaciones sin revisar en el único lugar que
# existe para revisarlas.
SIN_CASOS_TODAVIA = 66


def _reglas_de_acceso_ejecutables():
    for ruta in LECTURAS:
        for regla in json.loads(ruta.read_text(encoding="utf-8")).get("reglas", []):
            if not regla.get("ast"):
                continue
            if CategoriaRegla(regla["categoria"]) not in CATEGORIAS_DE_ACCESO:
                continue
            yield ruta, regla


def test_cada_regla_ejecutable_da_lo_que_su_lectura_dice() -> None:
    """La prueba que faltaba el día que se escribieron los doce árboles."""
    for ruta, regla in _reglas_de_acceso_ejecutables():
        try:
            exigir(regla["clave"], regla["categoria"], regla["ast"], regla.get("casos"))
        except CasoInvalido as exc:
            pytest.fail(f"{ruta.name} · {exc}")


def test_toda_exclusion_ejecutable_declara_sus_casos() -> None:
    """Es donde apareció el error y donde una inversión hace el daño más directo."""
    for ruta, regla in _reglas_de_acceso_ejecutables():
        if CategoriaRegla(regla["categoria"]) is CategoriaRegla.EXCLUSION:
            assert regla.get("casos"), f"{ruta.name} · {regla['clave']} no declara casos"


def test_las_que_faltan_estan_contadas_y_el_numero_no_sube() -> None:
    """Un trinquete dice la verdad sobre la cobertura; un cero forzado, no."""
    faltan = [
        (ruta.name, regla["clave"])
        for ruta, regla in _reglas_de_acceso_ejecutables()
        if not regla.get("casos")
    ]
    assert len(faltan) <= SIN_CASOS_TODAVIA, (
        f"Hay {len(faltan)} reglas de acceso ejecutables sin casos y el trinquete está en "
        f"{SIN_CASOS_TODAVIA}. Si agregaste una regla, agregale sus casos; si escribiste "
        "casos que faltaban, bajá el número."
    )
    if len(faltan) < SIN_CASOS_TODAVIA:
        pytest.fail(
            f"Quedan {len(faltan)} sin casos y el trinquete dice {SIN_CASOS_TODAVIA}: "
            "bajalo, que para eso está."
        )


def test_un_arbol_invertido_no_pasa() -> None:
    """La reproducción exacta del error, congelada.

    El árbol dice «está entre el piso y el techo», que es quien **accede**, y la
    categoría dice EXCLUSION. El caso lo agarra.
    """
    invertido = {
        "op": "all",
        "args": [
            {"op": "compare", "cmp": ">=", "field": "remuneracion", "value": 100, "unit": "ARS"},
            {"op": "compare", "cmp": "<", "field": "remuneracion", "value": 4000, "unit": "ARS"},
        ],
        "schema_version": "1.0",
    }
    casos = [
        {"nombre": "cobra dentro de la banda", "hechos": {"remuneracion": 2000}, "espera": "FALSE"}
    ]
    with pytest.raises(CasoInvalido, match="queda excluida"):
        exigir("REMUNERACION-FUERA-DE-LA-BANDA", "EXCLUSION", invertido, casos)


def test_una_regla_sin_arbol_no_necesita_casos() -> None:
    """Lo que la norma remite a la reglamentación entra con su texto y nada más."""
    exigir("REMITIDA-A-LA-REGLAMENTACION", "EXCLUSION", None, None)


def test_los_parametros_los_pone_el_caso_y_no_la_base() -> None:
    """Un caso que dependiera del corte dejaría de comprobar la regla el día que
    cambie un monto, que es justo cuando hace falta."""
    ast = {
        "op": "compare",
        "cmp": "<",
        "field": "haber",
        "unit": "ARS",
        "parameter": "AR.TOPE-MAXIMO-ASIGNACIONES",
        "schema_version": "1.0",
    }
    assert not correr(
        ast,
        [
            {
                "nombre": "por debajo",
                "hechos": {"haber": 10},
                "parametros": {"AR.TOPE-MAXIMO-ASIGNACIONES": 100},
                "espera": "TRUE",
            }
        ],
    )
    # Sin el parámetro no se inventa un valor: queda desconocido.
    assert not correr(ast, [{"nombre": "sin tope", "hechos": {"haber": 10}, "espera": "UNKNOWN"}])


def test_un_veredicto_que_no_existe_se_rechaza() -> None:
    with pytest.raises(CasoInvalido, match="veredicto"):
        correr({"op": "is_true", "field": "x"}, [{"nombre": "n", "hechos": {}, "espera": "SI"}])


def test_el_desvio_dice_que_esperaba_y_que_dio() -> None:
    (desvio,) = correr(
        {"op": "is_true", "field": "x", "schema_version": "1.0"},
        [{"nombre": "x es verdadero", "hechos": {"x": True}, "espera": "FALSE"}],
    )
    assert isinstance(desvio, Desvio)
    assert "se esperaba FALSE" in str(desvio)
    assert "dio TRUE" in str(desvio)


class TestRutaQueSobreviveALaResegmentacion:
    """El último tramo de una ruta lleva la posición de la unidad, no su nombre.

    El inciso c) del artículo 1 de la Ley 24.714 es `articulo-1/inciso-c-4` en
    una captura de 172 unidades y `articulo-1/inciso-c-6` en otra de 201: basta
    agregar una unidad antes para correr el número de todas las siguientes. Tres
    lecturas curadas habían dejado de cargar por eso, y con ellas se perdían tres
    de las doce correcciones de polaridad.
    """

    @staticmethod
    def _resolver(unidades, ruta):
        from backend_normativo.curacion.beneficios import CuradorDeBeneficios

        return CuradorDeBeneficios._resolver_ruta(
            {r: {"id": r, "texto": r} for r in unidades}, ruta
        )

    def test_la_ruta_exacta_gana(self) -> None:
        assert (
            self._resolver(
                ["articulo-1/inciso-c-4", "articulo-1/inciso-c-6"], "articulo-1/inciso-c-4"
            )["id"]
            == "articulo-1/inciso-c-4"
        )

    def test_el_ordinal_corrido_se_resuelve_si_no_hay_duda(self) -> None:
        assert self._resolver(["articulo-1/inciso-c-6"], "articulo-1/inciso-c-4")["id"] == (
            "articulo-1/inciso-c-6"
        )

    def test_con_dos_candidatas_no_se_adivina(self) -> None:
        """Del artículo 18 cuelgan veinte párrafos: ahí el ordinal es lo único
        que distingue, y elegir uno por parecido sería citar otro texto."""
        assert (
            self._resolver(
                ["articulo-18/parrafo-102", "articulo-18/parrafo-103"], "articulo-18/parrafo-55"
            )
            is None
        )

    def test_una_ruta_sin_ordinal_no_se_afloja(self) -> None:
        assert self._resolver(["articulo-14-bis"], "articulo-14-ter") is None

    def test_el_sufijo_bis_no_se_confunde_con_un_ordinal(self) -> None:
        assert self._resolver(["articulo-14-bis"], "articulo-14-bis")["id"] == "articulo-14-bis"
