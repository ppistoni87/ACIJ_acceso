"""HU-011, HU-013 y HU-017: las cuatro prestaciones de pago único de la Ley 24.714.

Nacimiento, adopción, matrimonio y cónyuge del SIJP se cobran una vez, contra un
hecho o un acto acreditado, y no mes a mes mientras dure una situación. Comparten
la forma y no comparten casi nada más: estas pruebas fijan las diferencias, que
son lo que se perdería si alguien decidiera curarlas como una sola.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
CURADURIA = RAIZ / "docs" / "curaduria"
LECTURAS = {
    "nacimiento": CURADURIA / "ley-nacional-24714-nacimiento.json",
    "adopcion": CURADURIA / "ley-nacional-24714-adopcion.json",
    "matrimonio": CURADURIA / "ley-nacional-24714-matrimonio.json",
    "conyuge": CURADURIA / "ley-nacional-24714-conyuge-sijp.json",
}

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
        "INCISO",
        "c",
        "c) Un subsistema no contributivo compuesto por la Asignación por Embarazo para "
        "Protección Social y la Asignación Universal por Hijo para Protección Social, "
        "destinado, respectivamente, a las mujeres embarazadas y a aquellos niños, niñas y "
        "adolescentes residentes en la REPUBLICA ARGENTINA; que pertenezcan a grupos familiares "
        "que se encuentren desocupados o se desempeñen en la economía informal. (Inciso "
        "sustituido por art. 1° del Decreto N° 446/2011 B.O. 19/4/2011)",
        "DISPOSITIVO",
        "articulo-1/inciso-c-6",
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
        "12",
        "ARTICULO 12.- La asignación por nacimiento de hijo consistirá en el pago de una suma "
        "de dinero que se abonará una vez acreditado tal hecho ante la Administración Nacional "
        "de la Seguridad Social (ANSES). (Artículo sustituido por art. 8° de la Ley N° 27.611 "
        "B.O. 15/01/2021). ( Nota Infoleg : por art. 1° de la Resolución N° 265/2021 de la "
        "Administración Nacional de la Seguridad Social B.O. 24/12/2021, se establece que lo "
        "dispuesto por art. 8° de la Ley N° 27.611 resulta de aplicación para aquellos hechos "
        "y/o actos generadores que se hayan producido a partir del 24 de enero de 2021.)",
        "DISPOSITIVO",
        "articulo-12",
    ),
    (
        "ARTICULO",
        "13",
        "ARTICULO 13.- La asignación por adopción consistirá en el pago de una suma de dinero "
        "que se abonará una vez acreditado dicho acto ante la Administración Nacional de la "
        "Seguridad Social (ANSES). (Artículo sustituido por art. 9° de la Ley N° 27.611 B.O. "
        "15/01/2021). ( Nota Infoleg : por art. 1° de la Resolución N° 265/2021 de la "
        "Administración Nacional de la Seguridad Social B.O. 24/12/2021, se establece que lo "
        "dispuesto por art. 9° de la Ley N° 27.611 resulta de aplicación para aquellos hechos "
        "y/o actos generadores que se hayan producido a partir del 24 de enero de 2021.)",
        "DISPOSITIVO",
        "articulo-13",
    ),
    (
        "ARTICULO",
        "14",
        "ARTICULO 14.- La asignación por matrimonio consistirá en el pago de una suma de "
        "dinero, que se abonara en el mes en que se acredite dicho acto ante el empleador. Para "
        "el goce de este beneficio se requerirá una antigüedad mínima y continuada en el empleo "
        "de seis meses. Esta asignación se abonará a los dos cónyuges cuando ambos se "
        "encuentren en las disposiciones de la presente ley.",
        "DISPOSITIVO",
        "articulo-14",
    ),
    (
        "ARTICULO",
        "14",
        "ARTICULO 14 septies. - Las personas titulares comprendidas en el inciso c) del "
        "artículo 1º de la presente ley tendrán derecho a la percepción de las asignaciones por "
        "nacimiento y adopción establecidas en los incisos f) y g) del artículo 6º también de "
        "la presente. Para acceder a dichas prestaciones, las personas titulares deberán "
        "acreditar el hecho y/o el acto generador pertinente ante la Administración Nacional de "
        "la Seguridad Social (ANSES). (Artículo incorporado por art. 10 de la Ley N° 27.611 "
        "B.O. 15/01/2021)",
        "DISPOSITIVO",
        "articulo-14-septies",
    ),
    (
        "ARTICULO",
        "15",
        "ARTICULO 15.- Los beneficiarios del Sistema Integrado de Jubilaciones y Pensiones "
        "gozarán de las siguientes prestaciones:",
        "DISPOSITIVO",
        "articulo-15",
    ),
    (
        "ARTICULO",
        "16",
        "ARTICULO 16.- La asignación por cónyuge del beneficiario del Sistema Integrado de "
        "Jubilaciones y Pensiones consistirá en el pago de una suma de dinero que se abonara al "
        "beneficiario por su cónyuge.",
        "DISPOSITIVO",
        "articulo-16",
    ),
    (
        "INCISO",
        "f",
        "f) Asignación por nacimiento: la suma de $ 400.",
        "DISPOSITIVO",
        "articulo-18/inciso-f-81",
    ),
    (
        "INCISO",
        "g",
        "g) Asignación por adopción: la suma de $ 2.400.",
        "DISPOSITIVO",
        "articulo-18/inciso-g-82",
    ),
    (
        "INCISO",
        "h",
        "h) Asignación por matrimonio: la suma de $ 600.",
        "DISPOSITIVO",
        "articulo-18/inciso-h-83",
    ),
    (
        "INCISO",
        "i",
        "i) Asignación por Cónyuge del beneficiario del SISTEMA INTEGRADO DE JUBILACIONES Y "
        "PENSIONES: la suma de PESOS TREINTA ($ 30) para los que perciban haberes inferiores a "
        "PESOS CUATRO MIL CON UN CENTAVO ($ 4.000,01).",
        "DISPOSITIVO",
        "articulo-18/inciso-i-84",
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
def curados(conexion: Connection, norma):
    curador = CuradorDeBeneficios(conexion)
    return {nombre: curador.cargar(ruta) for nombre, ruta in LECTURAS.items()}


def test_cada_cita_esta_en_la_unidad_que_dice_citar(conexion: Connection, curados) -> None:
    """Las cuatro citan el mismo texto y ninguna puede citar lo que no dice."""
    assert sum(r.reglas for r in curados.values()) == 20
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_son_cuatro_beneficios_y_no_uno(conexion: Connection, curados) -> None:
    """Cada una tiene su propio código: en la base son cuatro cosas distintas."""
    codigos = set(conexion.execute(text("SELECT codigo FROM beneficios")).scalars())
    assert codigos == {
        "AR.ASIGNACION-POR-NACIMIENTO",
        "AR.ASIGNACION-POR-ADOPCION",
        "AR.ASIGNACION-POR-MATRIMONIO",
        "AR.ASIGNACION-POR-CONYUGE-SIJP",
    }


def test_solo_nacimiento_y_adopcion_tienen_la_puerta_del_no_contributivo() -> None:
    """El artículo 14 septies nombra a esas dos y no al matrimonio.

    Copiarle la segunda puerta al matrimonio sería darle un derecho que la ley no
    le da; sacársela a las otras dos, negarles uno que sí.
    """
    con_segunda_puerta = {
        nombre
        for nombre, ruta in LECTURAS.items()
        if any(
            r["clave"] == "POR-SER-TITULAR-DEL-NO-CONTRIBUTIVO"
            for r in json.loads(ruta.read_text())["reglas"]
        )
    }
    assert con_segunda_puerta == {"nacimiento", "adopcion"}


def test_el_matrimonio_pide_el_doble_de_antiguedad(conexion: Connection, curados) -> None:
    """Seis meses, contra los tres de la maternidad y la prenatal."""
    ast = conexion.execute(
        text(
            "SELECT ast FROM reglas "
            " WHERE texto_literal LIKE '%antigüedad mínima y continuada en el empleo de seis%'"
        )
    ).scalar_one()
    assert ast["value"] == 6
    assert ast["unit"] == "meses"


def test_el_matrimonio_es_la_unica_que_cobran_los_dos(conexion: Connection, curados) -> None:
    """Es la excepción al artículo 20, que para todas las demás manda que cobre
    uno solo. Y el monto que percibe la pareja es el doble del que dice el
    inciso: guardar uno sin decir lo otro respondería la mitad."""
    fila = conexion.execute(
        text(
            "SELECT categoria, alcance FROM reglas "
            " WHERE texto_literal LIKE '%se abonará a los dos cónyuges%'"
        )
    ).one()
    assert fila.categoria == "EXCEPCION"
    assert "artículo 20" in fila.alcance

    motivo = conexion.execute(
        text(
            "SELECT bc.formula_ast->>'descripcion' FROM beneficio_cuantias bc "
            "  JOIN beneficio_versiones bv ON bv.registro_version_id = bc.beneficio_version_id "
            "  JOIN beneficios b ON b.id = bv.beneficio_id "
            " WHERE b.codigo = 'AR.ASIGNACION-POR-MATRIMONIO'"
        )
    ).scalar_one()
    assert "monto único" in motivo


def test_el_tope_del_conyuge_no_es_el_del_articulo_3(conexion: Connection, curados) -> None:
    """El del cónyuge viaja en el inciso del monto y habla de haberes, no de
    remuneración. Se apunta al mismo parámetro porque el número escrito es el
    mismo, y eso es exactamente lo que hay que confirmar."""
    fila = conexion.execute(
        text(
            "SELECT ast, alcance FROM reglas "
            " WHERE texto_literal LIKE '%Asignación por Cónyuge del beneficiario%'"
        )
    ).one()
    assert fila.ast["field"] == "haber_previsional_del_titular"
    assert "apuntar al mismo parámetro sería un error" in fila.alcance


def test_ninguna_de_las_cuatro_sirve_un_monto(conexion: Connection, curados) -> None:
    """Cuatrocientos, dos mil cuatrocientos, seiscientos y treinta pesos son los
    valores con los que la ley se sancionó en 1996."""
    filas = conexion.execute(text("SELECT tipo, valor_fijo FROM beneficio_cuantias")).all()
    assert len(filas) == 4
    assert all(f.tipo == "FORMULA" and f.valor_fijo is None for f in filas)
