"""HU-011, HU-013 y HU-017: la asignación por hijo del subsistema contributivo.

Tercera prestación de la Ley 24.714 curada por separado, y la primera del
subsistema contributivo. Lo que la distingue es que el derecho está condicionado
a un piso y un techo de remuneración que el artículo 3 fija en pesos de 2007:
escribir esos números en el árbol habría excluido a todo el mundo por superar el
tope.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.reglas.ast import parametros_referidos

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-asignacion-por-hijo.json"

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
        "PARRAFO",
        None,
        "Para los que trabajen en las Provincias de LA PAMPA, NEUQUEN, RIO NEGRO, CHUBUT, SANTA "
        "CRUZ, TIERRA DEL FUEGO, ANTARTIDA E ISLAS DEL ATLANTICO SUR; o en los Departamentos de "
        "Antofagasta de la Sierra (exclusivamente para los que se desempeñen en la actividad "
        "minera) de la Provincia de CATAMARCA; o en los Departamentos de Cochinoca, Humahuaca, "
        "Rinconada, Santa Catalina, Susques y Yavi de la Provincia de JUJUY; o en el Distrito "
        "Las Cuevas del Departamento de Las Heras, en los Distritos Potrerillos, Carrizal, "
        "Agrelo, Ugarteche, Perdriel y Las Compuertas del Departamento de Luján de Cuyo, en los "
        "Distritos de Santa Clara, Zapata, San José y Anchoris del Departamento Tupungato, en "
        "los Distritos de Los Arboles, Los Chacayes y Campo de los Andes del Departamento de "
        "Tunuyán, en el Distrito de Pareditas del Departamento San Carlos, en el Distrito de "
        "Cuadro Benegas del Departamento San Rafael, en los Distritos Malargüe, Río Grande, Río "
        "Barrancas, Agua Escondida del Departamento Malargüe, en los Distritos Russell, Cruz de "
        "Piedra, Las Barrancas y Lumlunta del Departamento Maipú, en los Distritos de El "
        "Mirador, Los Campamentos, Los Arboles, Reducción y Medrano del Departamento Rivadavia "
        "de la Provincia de MENDOZA; o en los Departamentos de General San Martín (excepto "
        "Ciudad de Tartagal y su ejido urbano), Rivadavia, Los Andes, Santa Victoria y Orán "
        "(excepto Ciudad de San Ramón de la Nueva Oran y su ejido urbano) de la Provincia de "
        "SALTA; o en los Departamentos Bermejo, Ramón Lista y Matacos de la Provincia de "
        "FORMOSA, la remuneración deberá ser inferior a PESOS CIEN ($100) o igual o superior a "
        "PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01) para excluir al trabajador del cobro de "
        "las prestaciones previstas en la presente ley (Tope máximo de remuneración sustituido "
        "por art. 1° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del 1º de "
        "julio de 2007)",
        "DISPOSITIVO",
        "articulo-3/parrafo-8",
    ),
    (
        "ARTICULO",
        "4",
        "ARTICULO 4°- Se considerará remuneración a los efectos de esta ley, la definida por el "
        "Sistema Integrado de Jubilaciones y Pensiones (Ley Nº 24.241, artículos 6º y 9º) con "
        "excepción de las horas extras y el sueldo anual complementario (SAC).",
        "DISPOSITIVO",
        "articulo-4",
    ),
    (
        "ARTICULO",
        "7",
        "ARTICULO 7º - La asignación por hijo consistirá en el pago de una suma mensual por "
        "cada hijo menor de 18 anos de edad que se encuentre a cargo del trabajador.",
        "DISPOSITIVO",
        "articulo-7",
    ),
    (
        "INCISO",
        "a",
        "a) Asignación por Hijo: la suma de PESOS CIEN ($ 100) para los trabajadores que "
        "perciban remuneraciones desde PESOS CIEN ($ 100) e inferiores a PESOS DOS MIL CON UN "
        "CENTAVO ($ 2.000,01); la suma de PESOS SETENTA Y CINCO ($ 75) para los trabajadores "
        "que perciban remuneraciones desde PESOS DOS MIL CON UN CENTAVO ($ 2.000,01) e "
        "inferiores a PESOS TRES MIL CON UN CENTAVO ($ 3.000,01) y la suma de PESOS CINCUENTA "
        "($ 50) para los que perciban remuneraciones desde PESOS TRES MIL CON UN CENTAVO ($ "
        "3.000,01) e inferiores a PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01). (Inciso "
        "sustituido por art. 3° del Decreto N° 1345/2007 B.O. 5/10/2007. Vigencia: a partir del "
        "1º de julio de 2007).",
        "DISPOSITIVO",
        "articulo-18/inciso-a-76",
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
    assert curado.reglas == 10
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_los_topes_de_2007_no_entran_como_valores_en_el_arbol(conexion: Connection, curado) -> None:
    """Cien pesos de piso y cuatro mil de techo son de 2007.

    Escribirlos como literales habría excluido a todo el mundo por superar el
    tope, que es el error opuesto al que la norma quiere evitar. Se comparan
    contra parámetros y, sin valor aprobado, la regla devuelve desconocido.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE '%Quedan excluidos de las prest%'")
    ).scalar_one()
    assert parametros_referidos(ast) == {
        "AR.TOPE-MINIMO-ASIGNACIONES",
        "AR.TOPE-MAXIMO-ASIGNACIONES",
    }
    # Ninguna hoja compara contra un literal: si lo hiciera, el número viejo
    # decidiría el acceso.
    for nodo in ast["args"]:
        assert "value" not in nodo


def test_quedar_excluida_del_contributivo_no_es_quedarse_sin_nada(
    conexion: Connection, curado
) -> None:
    """El personal de casas particulares no cobra esta asignación y sí cobra las
    del subsistema no contributivo, que están curadas aparte.

    Una respuesta que diga sólo «quedás excluida» sería cierta y engañosa.
    """
    motivo = conexion.execute(
        text("SELECT alcance FROM reglas WHERE texto_literal LIKE '%Casas Particulares%'")
    ).scalar_one()
    assert "reencauzamiento" in motivo
    assert "cierta y engañosa" in motivo


def test_la_zona_desfavorable_no_se_reduce_a_una_etiqueta(conexion: Connection, curado) -> None:
    """El párrafo enumera provincias, departamentos y distritos.

    Formalizarlo pide un catálogo que el corpus no tiene, y una lista escrita a
    ojo dejaría afuera a quien vive en un distrito mal copiado.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE '%LA PAMPA%'")
    ).scalar_one()
    assert ast is None


def test_la_excepcion_sabe_de_que_regla_es_excepcion(conexion: Connection, curado) -> None:
    """Sin esa arista, el evaluador no puede cumplir la promesa de no negar sin
    haber mirado las excepciones: no sabría cuáles mirar."""
    pares = conexion.execute(
        text(
            "SELECT origen.texto_literal, referida.texto_literal "
            "  FROM regla_dependencias rd "
            "  JOIN reglas origen ON origen.id = rd.regla_id "
            "  JOIN reglas referida ON referida.id = rd.regla_referida_id "
            " WHERE rd.tipo = 'EXCEPCION_DE'"
        )
    ).all()
    assert len(pares) == 2
    assert any("LA PAMPA" in o and "Quedan excluidos" in r for o, r in pares)
    assert any("guarda, tenencia o tutela" in o and "menor de 18" in r for o, r in pares)


def test_la_asignacion_no_declara_plazos_porque_la_ley_no_los_fija(
    conexion: Connection, curado
) -> None:
    """Se paga mes a mes mientras se cumplan las condiciones y no requiere
    solicitud: poner un plazo inventaría un vencimiento que no existe."""
    assert conexion.execute(text("SELECT count(*) FROM plazos")).scalar_one() == 0
    motivo = conexion.execute(
        text(
            "SELECT motivo FROM evaluaciones_completitud "
            " WHERE campo_solicitado = 'plazos' AND estado = "
            "       'NO_INFORMADO_EN_FUENTES_REVISADAS'"
        )
    ).scalar_one()
    assert "no fija plazo" in motivo
