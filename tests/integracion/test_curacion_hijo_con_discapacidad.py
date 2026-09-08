"""HU-011, HU-013 y HU-017: la asignación por hijo con discapacidad.

Es la prestación de la Ley 24.714 que más se parece a la asignación por hijo
común —mismo titular, mismo subsistema, mismas reglas de concurrencia— y por eso
se cura aparte: lo que la distingue es lo que se pierde si se la agrega como una
condición más. No tiene límite de edad, y el artículo 3 la exceptúa del tope de
ingresos que excluye a las demás.
"""

from __future__ import annotations

import pathlib
import re

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-hijo-con-discapacidad.json"

ARTICULOS = [
    (
        "INCISO",
        "a",
        "a) Un subsistema contributivo fundado en los principios de reparto de aplicación a los "
        "trabajadores que presten servicios remunerados en relación de dependencia en la "
        "actividad privada, cualquiera sea la modalidad de contratación laboral, beneficiarios "
        "de la Ley sobre Riesgos de Trabajo y beneficiarios del Seguro de Desempleo, el que se "
        "financiará con los recursos previstos en el artículo 5° de la presente ley. a’) Un "
        "subsistema contributivo de aplicación a las personas inscriptas y aportantes al "
        "Régimen Simplificado para Pequeños Contribuyentes (RS) establecido por la Ley N° "
        "24.977, sus complementarias y modificatorias, el que se financiará con los recursos "
        "previstos en el artículo 5° de la presente Ley. (Inciso sustituido por art. 13 del "
        "Decreto Nº 840/2020 B.O. 4/11/2020. Ver aplicación art. 17 del Decreto de referencia) "
        "b) Un subsistema no contributivo de aplicación a los beneficiarios del Sistema "
        "Integrado Previsional Argentino (SIPA), beneficiarios del régimen de pensiones no "
        "contributivas por invalidez, y para la Pensión Universal para el Adulto Mayor, el que "
        "se financiará con los recursos del régimen previsional previstos en el artículo 18 de "
        "la ley 24.241. (Inciso sustituido por art. 18 de la Ley N° 27.260 B.O. 22/7/2016. "
        "Vigencia: a partir del día siguiente al de su publicación en el Boletín Oficial.)",
        "DISPOSITIVO",
        "articulo-1/inciso-a-3",
    ),
    (
        "ARTICULO",
        "3",
        "ARTICULO 3°- Quedan excluidos de las prestaciones de esta ley, con excepción de las "
        "asignaciones familiares por maternidad y por hijos con discapacidad, los trabajadores "
        "que perciban una remuneración inferior a PESOS CIEN ($ 100) o igual o superior a PESOS "
        "CUATRO MIL CON UN CENTAVO ($ 4.000,01). (Tope máximo de remuneración sustituido por "
        "art. 1° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del 1º de julio de "
        "2007).",
        "DISPOSITIVO",
        "articulo-3",
    ),
    (
        "ARTICULO",
        "8",
        "ARTICULO 8°- La asignación por hijo con discapacidad consistirá en el pago de una suma "
        "mensual que se abonara al trabajador por cada hijo que se encuentre a su cargo en esa "
        "condición, sin limite de edad, a partir del mes en que se acredite tal condición ante "
        "el empleador. A los efectos de esta ley se entiende por discapacidad la definida en la "
        "Ley N° 22.431, artículo 2°.",
        "DISPOSITIVO",
        "articulo-8",
    ),
    (
        "INCISO",
        "b",
        "b) Asignación por Hijo con Discapacidad: la suma de PESOS CUATROCIENTOS ($ 400) para "
        "los trabajadores que perciban remuneraciones inferiores a PESOS DOS MIL CON UN CENTAVO "
        "($ 2.000,01); la suma de PESOS TRESCIENTOS ($ 300) para los trabajadores que perciban "
        "remuneraciones desde PESOS DOS MIL CON UN CENTAVO ($ 2.000,01) e inferiores a PESOS "
        "TRES MIL CON UN CENTAVO ($ 3.000,01) y la suma de PESOS DOSCIENTOS ($ 200) para los "
        "que perciban remuneraciones desde PESOS TRES MIL CON UN CENTAVO ($ 3.000,01). (Inciso "
        "sustituido por art. 3° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del "
        "1º de julio de 2007).",
        "DISPOSITIVO",
        "articulo-18/inciso-b-77",
    ),
    (
        "ARTICULO",
        "20",
        "ARTICULO 20.- Cuando ambos progenitores estén comprendidos en el presente régimen, las "
        "prestaciones enumeradas en los artículos 6º y 15 serán percibidas por uno solo de "
        "ellos.",
        "DISPOSITIVO",
        "articulo-20",
    ),
    (
        "ARTICULO",
        "21",
        "ARTICULO 21.- Cuando el trabajador se desempeñare en más de un empleo tendrá derecho a "
        "la percepción de las prestaciones de la presente ley en el que acredite mayor "
        "antigüedad, a excepción de la asignación por maternidad, que será percibida en cada "
        "uno de ellos.",
        "DISPOSITIVO",
        "articulo-21",
    ),
    (
        "ARTICULO",
        "22",
        "ARTICULO 22.- A los fines de otorgar las asignaciones por hijo, hijo con discapacidad "
        "y ayuda escolar anual, serán considerados como hijos los menores o personas con "
        "discapacidad cuya guarda, tenencia o tutela haya sido acordada al trabajador por "
        "autoridad judicial o administrativa competente. En tales supuestos, los respectivos "
        "padres no tendrán, por ese hijo, derecho al cobro de las mencionadas asignaciones.",
        "DISPOSITIVO",
        "articulo-22",
    ),
    (
        "ARTICULO",
        "23",
        "ARTICULO 23.- Las Asignaciones Familiares dispuestas en la presente ley son "
        "inembargables, no constituyen remuneración ni están sujetas a gravámenes, atento su "
        "naturaleza jurídica, tampoco serán tenidas en cuenta para la determinación del sueldo "
        "anual complementario, ni para el pago de las indemnizaciones por despido, enfermedad, "
        "accidente o para cualquier otro efecto. No pueden ser enajenadas ni afectadas a "
        "terceros por derecho alguno. (Tercer párrafo derogado por art. 2° del Decreto N° "
        "1039/2024 B.O. 25/11/2024. Vigencia: a partir de la fecha de su publicación en el "
        "BOLETÍN OFICIAL.)",
        "DISPOSITIVO",
        "articulo-23",
    ),
]


@pytest.fixture
def norma(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="F33",
        external_id="infoleg:39880:actualizado",
        tipo_version="ACTUALIZADO",
        identidad={
            "jurisdiccion": "AR",
            "infoleg_id": "39880",
            "tipo": "LEY",
            "numero": "24714",
            "anio": 1996,
            "titulo": "REGIMEN DE ASIGNACIONES FAMILIARES",
            "fechas": {"PUBLICACION": "1996-10-18"},
        },
        unidades=ARTICULOS,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()


@pytest.fixture
def curado(conexion: Connection, norma):
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


def test_cada_cita_esta_en_la_unidad_que_dice_citar(conexion: Connection, curado) -> None:
    assert curado.reglas == 8
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_el_tope_de_ingresos_no_alcanza_a_esta_asignacion(conexion: Connection, curado) -> None:
    """Es la diferencia más importante con la asignación por hijo común y la más
    fácil de perder: superar el tope no saca a nadie de esta prestación.

    Se guarda como excepción y no como condición, porque no hay nada que cumplir.
    """
    fila = conexion.execute(
        text(
            "SELECT categoria, ast, alcance FROM reglas "
            " WHERE texto_literal LIKE '%con excepción de las asignaciones familiares%'"
        )
    ).one()
    assert fila.categoria == "EXCEPCION"
    assert fila.ast is None
    assert "no saca a nadie de esta prestación" in fila.alcance


def test_ninguna_regla_pone_un_limite_de_edad(conexion: Connection, curado) -> None:
    """Un hijo de cuarenta años con discapacidad a cargo sigue dando derecho.

    Copiar el «menor de 18» de la asignación por hijo común sería el error que
    más gente dejaría afuera.
    """
    arboles = conexion.execute(text("SELECT ast FROM reglas WHERE ast IS NOT NULL")).scalars().all()

    def campos(nodo):
        if isinstance(nodo, dict):
            if "field" in nodo:
                yield nodo["field"]
            for hijo in nodo.get("args", ()):
                yield from campos(hijo)

    usados = {campo for arbol in arboles for campo in campos(arbol)}
    # Se busca la palabra, no la subcadena: «antiguedad» contiene «edad» y haría
    # pasar por límite de edad a la regla del empleo con mayor antigüedad.
    con_edad = {campo for campo in usados if re.search(r"\bedad\b", campo.replace("_", " "))}
    assert con_edad == set(), usados


def test_comparte_la_poblacion_con_la_asignacion_por_hijo(conexion: Connection, curado) -> None:
    """El mismo código de población, para que quede claro que no son dos grupos
    distintos de personas sino dos prestaciones para el mismo."""
    codigos = set(
        conexion.execute(
            text(
                "SELECT p.codigo FROM beneficio_poblaciones bp "
                "  JOIN poblaciones p ON p.id = bp.poblacion_id"
            )
        ).scalars()
    )
    assert codigos == {
        "AR.TRABAJADOR-EN-RELACION-DE-DEPENDENCIA",
        "AR.HIJO-CON-DISCAPACIDAD",
    }


def test_la_definicion_de_discapacidad_no_se_reconstruye(conexion: Connection, curado) -> None:
    """Vive en la Ley 22.431, que no está en el corpus.

    Escribir acá qué cuenta como discapacidad sería sustituir esa definición por
    una propia, y de esa definición depende el acceso.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE '%Ley N° 22.431, artículo 2°%'")
    ).scalar_one()
    assert ast is None
    abiertas = conexion.execute(
        text(
            "SELECT count(*) FROM incidencias_revision "
            " WHERE estado = 'ABIERTA' AND descripcion LIKE '%22.431%'"
        )
    ).scalar_one()
    assert abiertas == 1
