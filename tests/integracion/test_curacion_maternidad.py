"""HU-011, HU-013 y HU-017: la asignación por maternidad.

Es la prestación de la Ley 24.714 hecha de excepciones: su importe es el propio
sueldo y no una escala, el artículo 3 la exceptúa del tope de ingresos, el
artículo 21 la deja cobrar en cada empleo y el artículo 2 se la conserva a las
empleadas de casas particulares, que quedan fuera del resto del subsistema.
Cada una de esas cuatro cosas es una excepción a una regla general, y por eso
esta lectura no puede compartir nada con las demás.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-maternidad.json"

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
        "2",
        "ARTICULO 2°- Las empleadas/os del Régimen Especial de Contrato de Trabajo para el "
        "Personal de Casas Particulares se encuentran incluidas en el inciso c) del artículo "
        "1°, siendo beneficiarias de la Asignación por Embarazo para Protección Social y de la "
        "Asignación Universal por Hijo para Protección Social, quedando excluidas de los "
        "incisos a) y b) del citado artículo con excepción del derecho a la percepción de la "
        "Asignación por Maternidad establecida por el inciso e) del artículo 6° de la presente "
        "ley. Facúltase al Poder Ejecutivo nacional para que dicte las normas pertinentes a "
        "efectos de adecuar y extender a las empleadas/os de dicho régimen especial estatutario "
        "las demás asignaciones familiares previstas en la presente ley. Facúltase a la "
        "Administración Federal de Ingresos Públicos (AFIP) para establecer las alícuotas "
        "correspondientes para el financiamiento de la asignación familiar por maternidad "
        "correspondiente a las empleadas del Régimen Especial de Contrato de Trabajo para el "
        "Personal de Casas Particulares. (Artículo sustituido por art. 72 inc. b) de la Ley N° "
        "26.844 . Vigencia: de aplicación a todas las relaciones laborales alcanzadas por este "
        "régimen al momento de su entrada en vigencia)",
        "DISPOSITIVO",
        "articulo-2",
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
        "11",
        "ARTICULO 11.- La asignación por maternidad consistirá en el pago de una suma igual a "
        "la remuneración que la trabajadora hubiera debido percibir en su empleo, que se "
        "abonara durante el periodo de licencia legal correspondiente. Para el goce de esta "
        "asignación se requerirá una antigüedad mínima y continuada en el empleo de tres meses.",
        "DISPOSITIVO",
        "articulo-11",
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
    assert curado.reglas == 7
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_el_importe_es_el_sueldo_y_no_una_escala(conexion: Connection, curado) -> None:
    """Es la única cuantía de esta ley que no remite a un monto del artículo 18.

    Por eso no tiene parámetros y por eso tampoco tiene valor: depende de un dato
    de la persona, no de una resolución de ANSES.
    """
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, formula_ast FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "FORMULA"
    assert fila.valor_fijo is None
    assert fila.formula_ast["parametros"] == {}
    assert conexion.execute(text("SELECT count(*) FROM cuantia_parametros")).scalar_one() == 0


def test_las_empleadas_de_casas_particulares_conservan_esta_asignacion(
    conexion: Connection, curado
) -> None:
    """El artículo 2 las saca del subsistema contributivo «con excepción» de ésta.

    Es la razón por la que esta lectura no comparte la lista de situaciones
    laborales con las demás prestaciones de la ley: incluirlas acá es correcto y
    en cualquier otra sería un error.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE '%subsistema contributivo fundado%'")
    ).scalar_one()
    assert "CASAS_PARTICULARES" in ast["values"]

    excepcion = conexion.execute(
        text(
            "SELECT categoria FROM reglas "
            " WHERE texto_literal LIKE '%con excepción del derecho a la percepción%'"
        )
    ).scalar_one()
    assert excepcion == "EXCEPCION"


def test_se_cobra_en_cada_empleo_y_no_en_el_de_mayor_antiguedad(
    conexion: Connection, curado
) -> None:
    """Coherente con que el importe sea el sueldo: si reemplaza la remuneración,
    tiene que reemplazar la de cada empleo."""
    fila = conexion.execute(
        text(
            "SELECT categoria, texto_literal FROM reglas "
            " WHERE texto_literal LIKE '%se desempeñare en más de un empleo%'"
        )
    ).one()
    assert fila.categoria == "EXCEPCION"
    assert "percibida en cada uno de ellos" in fila.texto_literal


def test_la_duracion_no_se_trae_de_otra_norma(conexion: Connection, curado) -> None:
    """«La licencia legal correspondiente» remite a un régimen laboral que esta
    ley no fija, y que es distinto para casas particulares.

    Cargar acá los noventa días del contrato de trabajo común sería aplicárselos
    también a quien se rige por otro régimen.
    """
    assert conexion.execute(text("SELECT count(*) FROM plazos")).scalar_one() == 0
    motivo = conexion.execute(
        text("SELECT motivo FROM evaluaciones_completitud  WHERE campo_solicitado = 'plazos'")
    ).scalar_one()
    assert "licencia legal" in motivo
