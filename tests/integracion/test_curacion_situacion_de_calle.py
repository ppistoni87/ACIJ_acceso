"""HU-011, HU-013 y HU-017: el subsidio del Decreto CABA 690/06.

Es el programa que la Ley CABA 6935/2025 continúa, y las dos normas dicen cosas
distintas sobre cuál rige. Estas pruebas fijan lo que esta lectura tiene que
seguir haciendo: declarar esa tensión en vez de resolverla, no servir montos de
2006 y dejar a la vista una remisión interna que no cierra.
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
LECTURA = RAIZ / "docs" / "curaduria" / "decreto-caba-690-2006.json"

# El texto es el que la extracción produce hoy sobre el decreto publicado en
# NormativaBA, con sus rutas y su literalidad.
ARTICULOS = [
    (
        "ARTICULO",
        "3",
        "Artículo 3° - El programa Atención para Familias en Situación de Calle, tiene como "
        "objeto el otorgamiento de subsidios a fin de brindar asistencia a las familias en "
        "situación de calle, fortaleciendo el ingreso familiar, exclusivamente con fines "
        "habitacionales y la orientación de aquéllas en la búsqueda de distintas estrategias de "
        "solución a su problemática habitacional.",
        "DISPOSITIVO",
        "articulo-3",
    ),
    (
        "ARTICULO",
        "4",
        "Artículo 4° - El presente programa asiste a familias o personas solas en situación de "
        "calle, entendiendo por tal a aquéllas que se encuentran en inminente situación de "
        "desamparo habitacional, o se hallen transitoriamente sin vivienda o refugio por causa "
        "de desalojo u otras causas y que reúnan las condiciones previstas en el artículo 8° "
        "del presente decreto.",
        "DISPOSITIVO",
        "articulo-4",
    ),
    (
        "ARTICULO",
        "5",
        "Artículo 5° - El subsidio creado consiste en la entrega, de un monto de hasta pesos "
        "dos mil setecientos ($ 2.700), el que puede ser otorgado en seis (6) cuotas iguales y "
        "consecutivas de hasta pesos cuatrocientos cincuenta ($ 450) cada una, pudiendo la "
        "autoridad de aplicación ampliar el presente subsidio inclusive en una suma adicional "
        "de pesos mil ochocientos ($ 1.800), pagadera en hasta cuatro (4) cuotas iguales y "
        "consecutivas de pesos cuatrocientos cincuenta ($ 450) cada una, en los casos "
        "particulares que, a criterio de aquélla, ameriten la mencionada extensión, en orden a "
        "la persistencia de la situación que en su momento, motivara la entrega del beneficio.",
        "DISPOSITIVO",
        "articulo-5",
    ),
    (
        "ARTICULO",
        "8",
        "Artículo 8° - En aquellos casos en que prima facie la autoridad de aplicación constate "
        "que un grupo familiar o persona sola se encuentra en situación de calle y hasta tanto "
        "pueda verificar las condiciones y requisitos establecidos en los artículos 7° y 11 "
        "respectivamente, o hasta que se efectivice la percepción del subsidio, puede derivar "
        "transitoriamente a la familia a paradores u otras alternativas habitacionales "
        "transitorias, o bien otorgarles una suma de hasta pesos cuatrocientos cincuenta ($ "
        "450) en concepto de adelanto de la primera cuota. En este último supuesto y de "
        "otorgarse el subsidio, se programarán las cuotas restantes teniendo en cuenta el monto "
        "máximo establecido en el artículo 5°.",
        "DISPOSITIVO",
        "articulo-8",
    ),
    (
        "ARTICULO",
        "9",
        "Artículo 9° - La titularidad del subsidio recaerá en los jefes o jefas de familia, "
        "salvo que se trate de familias biparentales, en cuyo caso recaerá preferentemente en "
        "la mujer.",
        "DISPOSITIVO",
        "articulo-9",
    ),
    (
        "ARTICULO",
        "10",
        "Artículo 10 - El subsidio que se otorgue puede ser destinado para: a) cubrir gastos de "
        "alojamiento, b) cubrir toda índole de gastos emergentes, en los casos en que a los "
        "beneficiarios del presente programa, se les otorgue un crédito hipotecario del "
        "Instituto de Vivienda de la Ciudad Autónoma de Buenos Aires, o requieran del mismo "
        "para la obtención de una solución habitacional definitiva.",
        "DISPOSITIVO",
        "articulo-10",
    ),
    (
        "ARTICULO",
        "11",
        "Artículo 11 - Para la obtención del subsidio creado por el presente decreto se "
        'requiere: a) encontrarse en "situación de calle" de conformidad con lo establecido '
        "en el artículo 3° y con las restricciones dispuestas por el artículo 4° del presente "
        "decreto; b) ser residente de la Ciudad Autónoma de Buenos Aires con una antigüedad "
        "mínima de un (1) año; c) poseer ingresos menores al monto resultante del índice "
        "correspondiente a la canasta básica alimentaria, elaborada mensualmente por el INDEC; "
        "d) presentar la documentación exigida por las normas reglamentarias del presente "
        "decreto, a fin de acreditar los requisitos establecidos en el presente artículo; e) "
        "estar inscriptos en el Registro Único de Beneficiarios.",
        "DISPOSITIVO",
        "articulo-11",
    ),
    (
        "ARTICULO",
        "12",
        "Artículo 12 - Las jefas y jefes de familia que sean beneficiarios del subsidio deben: "
        "a) aceptar los términos establecidos en el presente decreto; b) acreditar que el "
        "subsidio otorgado ha sido destinado a la obtención de una solución habitacional, "
        "mediante los comprobantes que disponga la autoridad de aplicación; c) concurrir a la "
        "sede de la autoridad de aplicación, cuando ésta lo convoque en relación con el "
        "presente decreto.",
        "DISPOSITIVO",
        "articulo-12",
    ),
    (
        "ARTICULO",
        "13",
        "Artículo 13 - Los/las titulares del beneficio asumen las siguientes "
        "corresponsabilidades: a. En materia de protección de la salud: 1. Efectuar controles "
        "mensuales de salud de la embarazada. 2. Efectuar control quincenal de salud de "
        'niños/as menores de un mes. 3. Efectuar controles de "niño sano" y desarrollo '
        "nutricional mensual para los/as niños/as de hasta los once (11) meses de edad. 4. "
        'Efectuar controles de "niño sano" y desarrollo nutricional bimestral para los/as '
        'niños/as de doce (12) a veintitrés (23) meses de edad. 5. Efectuar controles de "niño '
        'sano" y desarrollo nutricional trimestral de los/as niños/as de veinticuatro (24) a '
        "treinta y cinco (35) meses de edad. 6. Efectuar controles de salud y desarrollo "
        "nutricional semestrales en caso de niños/as de tres (3) a cinco (5) años de edad. 7. "
        "Efectuar controles de salud y desarrollo nutricional anual para los/as niños/as de "
        "seis (6) a trece (13) años de edad. 8. Efectuar controles de salud anual para los/as "
        "adolescentes de catorce (14) a dieciocho (18) años. 9. Efectuar controles de salud "
        "anual para los/as adultos mayores de sesenta y cinco (65) años de edad y las personas "
        "con necesidades especiales. 10. En todos los casos, cumplir con la aplicación de las "
        "vacunaciones obligatorias. b. En materia de educación: 1. Procurar que los/as niños/as "
        "entre tres (3) y cuatro (4) años de edad asistan al jardín de infantes. 2. Cumplir con "
        "la asistencia y permanencia de niños/as de cinco (5) años de edad en el nivel "
        "preescolar, presentando certificado de asistencia cada tres (3) meses. 3. Cumplir con "
        "la asistencia y permanencia de los/as niños/as o adolescentes de seis (6) a dieciocho "
        "(18) años de edad en la escuela, procurando su promoción al año siguiente, "
        "certificando asistencia cada tres (3) meses. En todos los casos, el cumplimiento de "
        "estas corresponsabilidades se acreditará conforme lo prevea la reglamentación "
        "correspondiente.",
        "DISPOSITIVO",
        "articulo-13",
    ),
    (
        "ARTICULO",
        "14",
        "Artículo 14 - Son causales de caducidad del beneficio: a) cesación de las causas que "
        "dieron origen al otorgamiento del subsidio, b) que el grupo familiar no cumpla con los "
        "requisitos establecidos en el artículo precedente.",
        "DISPOSITIVO",
        "articulo-14",
    ),
    (
        "ARTICULO",
        "15",
        "Artículo 15 - La autoridad de aplicación debe informar al beneficiario, que es "
        "condición necesaria para el mantenimiento del beneficio, que los miembros de su grupo "
        "familiar menores de quince (15) años, no realicen actividades que la Ciudad de Buenos "
        "Aires ha categorizado como trabajo infantil en la Ley N° 937, conforme declaración "
        "jurada que como Anexo forma parte del presente.",
        "DISPOSITIVO",
        "articulo-15",
    ),
    (
        "ARTICULO",
        "16",
        "Artículo 16 - El Ministerio de Derechos Humanos y Sociales, se encuentra facultado "
        "para el dictado de la reglamentación del presente decreto, y de aquellos actos "
        "administrativos que resulten necesarios para su correcta implementación.",
        "DISPOSITIVO",
        "articulo-16",
    ),
]


@pytest.fixture
def norma(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="D10",
        external_id="normativaba:86704:actualizado",
        tipo_version="ACTUALIZADO",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "86704",
            "tipo": "DECRETO",
            "numero": "690",
            "anio": 2006,
            "titulo": "ATENCION PARA FAMILIAS EN SITUACION DE CALLE",
            "fechas": {"PUBLICACION": "2006-06-01"},
        },
        unidades=ARTICULOS,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()


@pytest.fixture
def curado(conexion: Connection, norma):
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


def test_cada_cita_esta_en_la_unidad_que_dice_citar(conexion: Connection, curado) -> None:
    """Lo único que una máquina puede verificar sola de una lectura jurídica."""
    assert curado.reglas == 14
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_la_remision_rota_del_articulo_14_queda_a_la_vista(conexion: Connection, curado) -> None:
    """El artículo 14 da de baja el subsidio por incumplir «el artículo
    precedente», que es el 13 —corresponsabilidades— cuando los requisitos están
    en el 11.

    Las dos lecturas dan resultados opuestos: por el 13, un certificado escolar
    entregado tarde da de baja a una familia en la calle. No se elige ninguna.
    """
    motivo = conexion.execute(
        text("SELECT r.alcance FROM reglas r  WHERE r.texto_literal LIKE '%artículo precedente%'")
    ).scalar_one()
    assert "no tiene «requisitos»" in motivo
    assert "No se elige ninguna" in motivo

    ast = conexion.execute(
        text("SELECT r.ast FROM reglas r WHERE r.texto_literal LIKE '%artículo precedente%'")
    ).scalar_one()
    # Sin AST: escribir una condición sería elegir una de las dos lecturas en
    # silencio, y de esa elección depende quién pierde el subsidio.
    assert ast is None


def test_no_se_sirve_el_monto_de_2006(conexion: Connection, curado) -> None:
    """Cuatrocientos cincuenta pesos por cuota es lo que el artículo 5 fijó en
    2006. Decirle a alguien que va a cobrar eso es peor que decirle que no se
    sabe."""
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, formula_ast, unidad_beneficiaria FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "FORMULA"
    assert fila.valor_fijo is None
    assert fila.formula_ast["piso"] == []
    assert fila.unidad_beneficiaria == "HOGAR"


def test_la_tension_con_la_ley_6935_queda_declarada(conexion: Connection, curado) -> None:
    """La Ley 6935 dice que el programa se rige exclusivamente por ella y su
    cláusula transitoria dice que hasta reglamentarse rige este decreto.

    Cuál de las dos aplica hoy depende de un hecho que el corpus no tiene. Se
    declara como dependencia abierta: elegir una cambiaría el monto, los
    requisitos y las causales de baja que se le informan a alguien que está en
    la calle.
    """
    descripciones = (
        conexion.execute(
            text(
                "SELECT descripcion FROM incidencias_revision "
                " WHERE estado = 'ABIERTA' AND descripcion LIKE '%6935%'"
            )
        )
        .scalars()
        .all()
    )
    assert descripciones
    assert any("reglamentada" in d for d in descripciones)


def test_quien_cobra_no_es_el_grupo_que_se_evalua(conexion: Connection, curado) -> None:
    """Las condiciones se miden sobre el hogar y cobra una sola persona."""
    roles = dict(
        conexion.execute(
            text(
                "SELECT p.codigo, bp.rol_persona FROM beneficio_poblaciones bp "
                "  JOIN poblaciones p ON p.id = bp.poblacion_id"
            )
        ).all()
    )
    assert roles["CABA.FAMILIA-EN-SITUACION-DE-CALLE"] == "GRUPO_FAMILIAR"
    assert roles["CABA.JEFE-O-JEFA-DE-FAMILIA"] == "TITULAR"


def test_una_preferencia_no_se_formaliza_como_requisito(conexion: Connection, curado) -> None:
    """El artículo 9 prefiere a la mujer en familias biparentales, no lo exige.

    Convertirla en condición ejecutable haría que una solicitud a nombre del
    varón quedara rechazada por algo que el decreto no prohíbe.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE '%preferentemente en la mujer%'")
    ).scalar_one()
    assert ast is None
