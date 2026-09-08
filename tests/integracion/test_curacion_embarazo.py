"""HU-011, HU-013 y HU-017: la Asignación por Embarazo para Protección Social.

Es la otra prestación del subsistema no contributivo de la Ley 24.714, y se cura
aparte de la Asignación Universal por Hijo a propósito: son dos prestaciones con
requisitos distintos sobre la misma ley. Estas pruebas fijan que esa diferencia
no se unifique.
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
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-embarazo.json"

ARTICULOS = [
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
        "ARTICULO 14 quater.- La Asignación por Embarazo para Protección Social consistirá en "
        "una prestación monetaria no retributiva mensual que se abonará a la persona gestante, "
        "desde el inicio de su embarazo hasta su interrupción o el nacimiento del hijo, siempre "
        "que no exceda de nueve (9) mensualidades, debiendo solicitarse a partir de la "
        "decimosegunda (12) semana de gestación. (Párrafo sustituido por art. 7° de la Ley N° "
        "27.611 B.O. 15/01/2021)",
        "DISPOSITIVO",
        "articulo-14-quater",
    ),
    (
        "PARRAFO",
        None,
        "Sólo corresponderá la percepción del importe equivalente a UNA (1) Asignación por "
        "Embarazo para Protección Social, aún cuando se trate de embarazo múltiple. La "
        "percepción de esta asignación no será incompatible con la Asignación Universal por "
        "Hijo para Protección Social por cada menor de DIECIOCHO (18) años, o sin límite de "
        "edad cuando se trate de un discapacitado, a cargo de la mujer embarazada.",
        "DISPOSITIVO",
        "articulo-14-quater/parrafo-52",
    ),
    (
        "INCISO",
        "a",
        "a) Que la embarazada sea argentina nativa o por opción, naturalizada o residente, con "
        "residencia legal en el país no inferior a TRES (3) años previos a la solicitud de la "
        "asignación.",
        "DISPOSITIVO",
        "articulo-14-quinquies/inciso-a-55",
    ),
    (
        "INCISO",
        "b",
        "b) Acreditar identidad, mediante Documento Nacional de Identidad.",
        "DISPOSITIVO",
        "articulo-14-quinquies/inciso-b-56",
    ),
    (
        "INCISO",
        "c",
        'c) La acreditación del estado de embarazo mediante la inscripción en el "Plan Nacer" '
        "del MINISTERIO DE SALUD. En aquellos casos que prevea la reglamentación, en que la "
        "embarazada cuente con cobertura de obra social, la acreditación del estado de embarazo "
        "será mediante certificado médico expedido de conformidad con lo previsto en dicho plan "
        "para su acreditación.",
        "DISPOSITIVO",
        "articulo-14-quinquies/inciso-c-57",
    ),
    (
        "PARRAFO",
        None,
        "Si el requisito se acredita con posterioridad al nacimiento o interrupción del "
        "embarazo, no corresponde el pago de la asignación por el período correspondiente al de "
        "gestación.",
        "DISPOSITIVO",
        "articulo-14-quinquies/parrafo-58",
    ),
    (
        "INCISO",
        "d",
        "d) La presentación por parte del titular del beneficio de una declaración jurada "
        "relativa al cumplimiento de los requisitos exigidos por la presente y a las calidades "
        "invocadas. De comprobarse la falsedad de alguno de estos datos, se producirá la "
        "pérdida del beneficio, sin perjuicio de las sanciones que correspondan.",
        "DISPOSITIVO",
        "articulo-14-quinquies/inciso-d-59",
    ),
    (
        "INCISO",
        "l",
        "l) Asignación por Embarazo para Protección Social: la mayor suma fijada en el inciso a).",
        "DISPOSITIVO",
        "articulo-18/inciso-l-98",
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
    assert curado.reglas == 9
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_los_tres_anios_de_residencia_no_se_unifican_con_los_dos_de_la_auh(
    conexion: Connection, curado
) -> None:
    """La misma ley pide tres años acá y dos para la Asignación Universal por Hijo.

    La diferencia está en el texto de los dos artículos. Unificarla sería más
    prolijo y le cambiaría el acceso a una persona embarazada con dos años y
    medio de residencia legal.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE '%residencia legal en el país%'")
    ).scalar_one()
    anios = [
        nodo["value"]
        for nodo in ast["args"]
        if nodo["op"] == "compare" and nodo["field"].startswith("residencia_legal")
    ]
    assert anios == [3]


def test_quien_cobra_es_la_misma_persona_sobre_la_que_se_mide(conexion: Connection, curado) -> None:
    """Es lo que la distingue de la Asignación Universal por Hijo, donde el
    causante es una persona distinta de quien cobra."""
    roles = dict(
        conexion.execute(
            text(
                "SELECT p.codigo, bp.rol_persona FROM beneficio_poblaciones bp "
                "  JOIN poblaciones p ON p.id = bp.poblacion_id"
            )
        ).all()
    )
    assert roles == {"AR.PERSONA-GESTANTE": "TITULAR"}


def test_un_embarazo_multiple_no_multiplica_la_asignacion(conexion: Connection, curado) -> None:
    """Contraste con la Asignación Universal por Hijo, que se paga por cada
    causante: acá el texto lo dice con todas las letras."""
    literal = conexion.execute(
        text("SELECT texto_literal FROM reglas WHERE texto_literal LIKE '%embarazo múltiple%'")
    ).scalar_one()
    assert "Sólo corresponderá la percepción del importe equivalente a UNA (1)" in literal


def test_la_apertura_de_la_semana_12_no_se_guarda_como_vencimiento(
    conexion: Connection, curado
) -> None:
    """Dice desde cuándo se puede pedir, no hasta cuándo.

    Leerlo como vencimiento haría creer que después de la semana doce ya no se
    puede solicitar, que es lo contrario de lo que dice el texto.
    """
    fila = conexion.execute(
        text("SELECT cantidad, unidad, evento_inicio, tipo FROM plazos  WHERE unidad = 'semanas'")
    ).one()
    assert (fila.cantidad, fila.unidad) == (12, "semanas")
    assert fila.evento_inicio == "inicio de la gestación"
    assert fila.tipo == "CONVOCATORIA"


def test_no_se_sirve_el_monto_del_articulo_18(conexion: Connection, curado) -> None:
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, formula_ast FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "FORMULA"
    assert fila.valor_fijo is None
    assert fila.formula_ast["parametros"]["REFERENCIA"] == ["AR.ASIGNACION-HIJO"]
