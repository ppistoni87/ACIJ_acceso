"""HU-011, HU-013 y HU-017: la asignación prenatal.

Es la contraparte contributiva de la Asignación por Embarazo para Protección
Social: el mismo hecho de la vida cubierto por los dos subsistemas con
requisitos que no se parecen. Estas pruebas fijan las diferencias, que son lo
que se pierde si alguien decide que «son la misma».
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
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-prenatal.json"
EMBARAZO = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-embarazo.json"

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
        "9",
        "ARTICULO 9°- La asignación prenatal consistirá en el pago de una suma equivalente a la "
        "asignación por hijo, que se abonara desde el momento de la concepción hasta el "
        "nacimiento del hijo. Este estado debe ser acreditado entre el tercer y cuarto mes de "
        "embarazo, mediante certificado médico. Para el goce de esta asignación se requerirá "
        "una antigüedad mínima y continuada en el empleo de tres meses.",
        "DISPOSITIVO",
        "articulo-9",
    ),
    (
        "INCISO",
        "c",
        "c) Asignación prenatal: una suma igual a la de asignación por hijo.",
        "DISPOSITIVO",
        "articulo-18/inciso-c-78",
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


def test_no_pide_lo_mismo_que_la_asignacion_por_embarazo() -> None:
    """Mismo embarazo, dos subsistemas, requisitos que no se parecen.

    La prenatal pide tres meses de antigüedad en el empleo; la del otro
    subsistema pide tres años de residencia legal. Promediarlas o unificarlas
    cambiaría quién accede a cuál.
    """
    import json as _json

    prenatal = _json.loads(LECTURA.read_text())
    embarazo = _json.loads(EMBARAZO.read_text())

    claves_prenatal = {r["clave"] for r in prenatal["reglas"]}
    claves_embarazo = {r["clave"] for r in embarazo["reglas"]}
    assert "ANTIGUEDAD-MINIMA-DE-TRES-MESES" in claves_prenatal
    assert "ANTIGUEDAD-MINIMA-DE-TRES-MESES" not in claves_embarazo
    assert "NACIONALIDAD-O-RESIDENCIA-LEGAL-3-ANIOS" in claves_embarazo
    assert "NACIONALIDAD-O-RESIDENCIA-LEGAL-3-ANIOS" not in claves_prenatal

    # Y una asimetría del propio artículo 3: exceptúa del tope a la maternidad y
    # no a la prenatal, aunque las dos cubren el mismo embarazo.
    assert any(r["categoria"] == "EXCLUSION" for r in prenatal["reglas"])


def test_la_ventana_de_acreditacion_dice_lo_que_la_ley_no_dice(
    conexion: Connection, curado
) -> None:
    """«Entre el tercer y cuarto mes» tiene dos extremos y el modelo guarda uno.

    Lo que hay que no perder es que la ley no dice qué pasa fuera de la ventana:
    una condición que devuelva falso daría por perdido un derecho que la ley no
    dice que se pierda.
    """
    plazo = conexion.execute(text("SELECT tipo, cantidad, unidad, evento_inicio FROM plazos")).one()
    assert plazo.tipo == "PRESENTACION_DOCUMENTAL"
    assert (plazo.cantidad, plazo.unidad) == (4, "meses")
    assert plazo.evento_inicio == "inicio del embarazo"

    motivo = conexion.execute(
        text(
            "SELECT alcance FROM reglas "
            " WHERE texto_literal LIKE '%acreditado entre el tercer y cuarto mes%'"
        )
    ).scalar_one()
    assert "no dice qué pasa fuera de ella" in motivo


def test_la_cuantia_hereda_la_escala_del_inciso_a(conexion: Connection, curado) -> None:
    """El inciso c) no fija un valor propio: remite al de la asignación por hijo.

    Y no es lo mismo que la Asignación por Embarazo, que remite a «la mayor suma
    fijada en el inciso a)»: con una escala por tramos, igual y mayor difieren.
    """
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, formula_ast FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "FORMULA"
    assert fila.valor_fijo is None
    assert fila.formula_ast["parametros"]["REFERENCIA"] == ["AR.ASIGNACION-HIJO"]
