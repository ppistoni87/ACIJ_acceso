"""HU-011, HU-013 y HU-017: la Asignación por Cuidado de Salud Integral.

Es la única prestación de la Ley 24.714 que exige haber tenido derecho a otra
para acceder a ella. Un beneficio condicionado a otro beneficio es una forma que
el modelo no tenía, y lo que estas pruebas fijan es cómo quedó declarada: el
texto dice «hayan tenido derecho al cobro», no «hayan cobrado».
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
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-cuidado-de-salud.json"

ARTICULOS = [
    (
        "INCISO",
        "c",
        "c) Un subsistema no contributivo compuesto por la Asignación por Embarazo para "
        "Protección Social y la Asignación Universal por Hijo para Protección Social, "
        "destinado, respectivamente, a las mujeres embarazadas y a aquellos niños, niñas y "
        "adolescentes residentes en la REPUBLICA ARGENTINA; que pertenezcan a grupos familiares "
        "que se encuentren desocupados o se desempeñen en la economía informal. (Inciso "
        "sustituido por art. 1° del Decreto N° 446/2011 B.O. 19/4/2011)",
        "DISPOSITIVO",
        "articulo-1/inciso-c-4",
    ),
    (
        "PARRAFO",
        None,
        "Quedan excluidos del beneficio previsto en el artículo 1° inciso c) de la presente los "
        "trabajadores que se desempeñen en la economía informal, que perciban una remuneración "
        "superior al salario mínimo, vital y móvil. (Último párrafo sustituido por art. 72 inc. "
        "e) de la Ley N° 26.844 . Vigencia: de aplicación a todas las relaciones laborales "
        "alcanzadas por este régimen al momento de su entrada en vigencia) ( Nota Infoleg : en "
        "la edición del Boletón Oficial se publicó la modificación de referencia como inc. e) "
        "cuando debería ser consignada como inc. c))",
        "DISPOSITIVO",
        "articulo-3/parrafo-9",
    ),
    (
        "ARTICULO",
        "14",
        "Artículo 14 octies : La Asignación por Cuidado de Salud Integral consistirá en el pago "
        "de una suma de dinero que se abonará una (1) vez al año a las personas titulares "
        "comprendidas en el artículo 1° de la presente ley, por cada niño o niña menor de tres "
        "(3) años de edad que se encuentre a su cargo, siempre que hayan tenido derecho al "
        "cobro de la prestación establecida en el inciso i) del artículo 6º de la presente "
        "dentro del año calendario, y siempre que acrediten el cumplimiento del plan de "
        "vacunación y control sanitario, de conformidad con los requisitos que la "
        "Administración Nacional de la Seguridad Social (ANSES) establecerá a tales efectos.",
        "DISPOSITIVO",
        "articulo-14-octies",
    ),
    (
        "INCISO",
        "m",
        "m) Asignación por Cuidado de Salud Integral: la mayor suma fijada en los incisos a) o "
        "b), según corresponda. (Inciso m) incorporado por art. 6° de la Ley N° 27.611 B.O. "
        "15/01/2021)",
        "DISPOSITIVO",
        "articulo-18/inciso-m-102",
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
    assert curado.reglas == 5
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_el_requisito_es_haber_tenido_derecho_y_no_haber_cobrado(
    conexion: Connection, curado
) -> None:
    """Alguien a quien le correspondía la AUH y no la percibió tuvo el derecho igual.

    Escribir el campo como «cobró» invertiría el sentido del texto y dejaría
    afuera justo a quien ya quedó afuera una vez.
    """
    fila = conexion.execute(
        text(
            "SELECT ast, alcance FROM reglas "
            " WHERE texto_literal LIKE '%hayan tenido derecho al cobro%'"
        )
    ).one()
    assert fila.ast["field"] == "tuvo_derecho_a_la_auh_en_el_ano_calendario"
    assert "no «hayan cobrado»" in fila.alcance


def test_la_tension_del_encabezado_queda_declarada(conexion: Connection, curado) -> None:
    """El artículo dice «titulares comprendidas en el artículo 1°», que es toda
    la ley, y el requisito de haber tenido derecho a la AUH la acota de hecho al
    subsistema no contributivo."""
    alcance = conexion.execute(
        text(
            "SELECT bp.alcance FROM beneficio_poblaciones bp "
            "  JOIN poblaciones p ON p.id = bp.poblacion_id "
            " WHERE p.codigo = 'AR.TITULAR-DEL-SUBSISTEMA-NO-CONTRIBUTIVO'"
        )
    ).scalar_one()
    assert "toda la ley" in alcance
    assert "lo primero que hay que resolver" in alcance


def test_una_frecuencia_anual_sin_mes_no_finge_una_fecha(conexion: Connection, curado) -> None:
    """«Una vez al año» dice la frecuencia y no la fecha, a diferencia de la
    ayuda escolar, que sí dice marzo."""
    plazo = conexion.execute(text("SELECT tipo, evento_inicio FROM plazos")).one()
    assert plazo.tipo == "FECHA_PAGO"
    assert "año calendario" in plazo.evento_inicio
