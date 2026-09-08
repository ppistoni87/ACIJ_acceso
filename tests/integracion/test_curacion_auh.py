"""HU-011, HU-013 y HU-017: la Asignación Universal por Hijo, leída del corpus.

La AUH es una de las catorce prestaciones que regula la Ley 24.714, no la ley
entera. Estas pruebas verifican lo que distingue a esta lectura de la anterior:
que el causante no se confunda con quien cobra, y que el monto no se sirva
—porque el artículo 18 todavía dice cien pesos y hace años que nadie cobra eso—.
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
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-auh.json"

# El texto es el que la extracción produce hoy sobre la Ley 24.714 publicada en
# InfoLEG, con sus rutas y su literalidad. Recortarlo o emprolijarlo haría que
# las citas de la lectura curada pasaran contra un texto que no es el que se
# capturó, que es justamente lo que estas pruebas tienen que impedir.
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
        "ARTICULO 14 bis.- La Asignación Universal por Hijo para Protección Social consistirá "
        "en una prestación monetaria no retributiva de carácter mensual, que se abonará a uno "
        "solo o una sola de los padres o de las madres, tutor o tutora, curador o curadora o "
        "pariente por consanguinidad hasta el tercer grado, por cada niña, niño y/o adolescente "
        "menor de DIECIOCHO (18) años que se encuentre a su cargo, o sin límite de edad cuando "
        "se trate de una persona con discapacidad; en ambos casos, siempre que no estuviere "
        "empleado o empleada, emancipado o emancipada o percibiendo alguna de las prestaciones "
        "previstas en la presente Ley. (Artículo sustituido por art. 1º del Decreto Nº 840/2020 "
        "B.O. 4/11/2020. Ver aplicación art. 17 del Decreto de referencia)",
        "DISPOSITIVO",
        "articulo-14-bis",
    ),
    (
        "ARTICULO",
        "14",
        "ARTICULO 14 ter .- Para acceder a la Asignación Universal por Hijo para Protección "
        "Social, se requerirá: a. Que la niña, el niño, adolescente y/o la persona con "
        "discapacidad sea argentino o argentina nativo o nativa, naturalizado o naturalizada o "
        "por opción. Cuando la niña, el niño, adolescente y/o la persona con discapacidad y sus "
        "progenitores o sus progenitoras o las personas que los o las tengan a cargo sean "
        "extranjeros o extranjeras, deberán acreditar tanto la niña, el niño, adolescente y/o "
        "la persona con discapacidad como el o la titular que percibirá la Asignación, DOS (2) "
        "años de residencia legal en el país. b. Acreditar la identidad del o de la titular del "
        "beneficio y de la niña, del niño, adolescente y/o persona con discapacidad, mediante "
        "Documento Nacional de Identidad. c. Acreditar que la persona que percibirá el "
        "beneficio tiene a su cargo a la niña, al niño, adolescente y/o persona con "
        "discapacidad, en función de las disposiciones del Código Civil y Comercial de la "
        "Nación y de conformidad con la documentación que la ADMINISTRACIÓN NACIONAL DE LA "
        "SEGURIDAD SOCIAL (ANSES) disponga a estos fines. d. La acreditación de la condición de "
        "discapacidad será determinada en los términos del artículo 2º de la Ley Nº 22.431, "
        "certificada por autoridad competente. e. Hasta los CUATRO (4) años de edad "
        "-inclusive-, deberá acreditarse el cumplimiento de los controles sanitarios y del plan "
        "de vacunación obligatorio. Desde los CINCO (5) años de edad y hasta los DIECIOCHO (18) "
        "años, deberá acreditarse además la concurrencia de las niñas, los niños y adolescentes "
        "obligatoriamente a establecimientos educativos públicos. f. Acreditar que el o la "
        "titular del beneficio y la niña, el niño, adolescente y/o persona con discapacidad "
        "residen en el país. (Artículo sustituido por art. 2º del Decreto Nº 840/2020 B.O. "
        "4/11/2020. Ver aplicación art. 17 del Decreto de referencia)",
        "DISPOSITIVO",
        "articulo-14-ter",
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
        "ARTICULO",
        "14",
        "ARTICULO 14 sexies .- Los titulares de la Asignación Universal por Hijo para "
        "Protección Social establecida en el artículo 1°, inciso c) de la presente Ley tendrán "
        "derecho a la Asignación por Ayuda Escolar Anual prevista en el artículo 6°, inciso d) "
        "y definida por el artículo 10 de esta ley.",
        "DISPOSITIVO",
        "articulo-14-sexies",
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
        "INCISO",
        "k",
        "k) Asignación Universal por Hijo para Protección Social: la mayor suma fijada en los "
        "incisos a) o b), según corresponda. El OCHENTA POR CIENTO (80 %) del monto previsto en "
        "el primer párrafo se abonará mensualmente a los o a las titulares de las mismas a "
        "través del sistema de pagos de la ADMINISTRACIÓN NACIONAL DE LA SEGURIDAD SOCIAL "
        "(ANSES). El VEINTE POR CIENTO (20 %) reservado podrá cobrarse cuando el o la titular "
        "acredite, para los o las menores de hasta los CUATRO (4) años de edad -inclusive-, el "
        "cumplimiento de los controles sanitarios y el plan de vacunación obligatorio; y para "
        "los y las de edad escolar, la certificación que acredite, además, el cumplimiento del "
        "ciclo escolar lectivo correspondiente. La falta de acreditación producirá la pérdida "
        "del derecho al cobro del VEINTE POR CIENTO (20 %) reservado. (Inciso k) sustituido por "
        "art. 3º del Decreto Nº 840/2020 B.O. 4/11/2020. Ver aplicación art. 17 del Decreto de "
        "referencia)",
        "DISPOSITIVO",
        "articulo-18/inciso-k-97",
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
        "22",
        "ARTICULO 22.- A los fines de otorgar las asignaciones por hijo, hijo con discapacidad "
        "y ayuda escolar anual, serán considerados como hijos los menores o personas con "
        "discapacidad cuya guarda, tenencia o tutela haya sido acordada al trabajador por "
        "autoridad judicial o administrativa competente. En tales supuestos, los respectivos "
        "padres no tendrán, por ese hijo, derecho al cobro de las mencionadas asignaciones.",
        "DISPOSITIVO",
        "articulo-22",
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
    """Es lo único que una máquina puede verificar sola de una lectura jurídica.

    Que la interpretación sea correcta lo decide una persona; que el texto
    citado exista donde se dice que existe, no hace falta que lo decida nadie.
    Si la carga llegó hasta acá es porque las 16 reglas pasaron ese control.
    """
    assert curado.reglas == 16
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    assert len(filas) == 16
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_quien_cobra_no_es_quien_da_lugar_al_beneficio(conexion: Connection, curado) -> None:
    """El causante y el titular son dos personas distintas.

    Confundirlos haría que las condiciones del titular —residencia legal,
    identidad, vínculo— se le pidieran a un chico de cuatro años, o que la edad
    del chico se midiera sobre quien cobra.
    """
    roles = dict(
        conexion.execute(
            text(
                "SELECT p.codigo, bp.rol_persona FROM beneficio_poblaciones bp "
                "  JOIN poblaciones p ON p.id = bp.poblacion_id"
            )
        ).all()
    )
    assert roles["AR.NNA-A-CARGO"] == "CAUSANTE"
    assert roles["AR.TITULAR-AUH"] == "TITULAR"


def test_la_cuantia_no_sirve_el_monto_que_el_articulo_18_todavia_dice(
    conexion: Connection, curado
) -> None:
    """El artículo 18 fija cien pesos por hijo desde 2007.

    El monto real lo fijan resoluciones de ANSES que no están en el corpus. La
    cuantía queda como fórmula con sus parámetros de referencia y sin valor:
    servir el número de la ley sería decirle a alguien que va a cobrar cien
    pesos.
    """
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, unidad_beneficiaria, formula_ast FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "FORMULA"
    assert fila.valor_fijo is None
    # Se cobra por cada causante, no por hogar: con los mismos datos, una y otra
    # cosa dan importes distintos.
    assert fila.unidad_beneficiaria == "CAUSANTE"
    # No hay piso: el monto no es «al menos tanto», es una remisión a otra norma
    # que se actualiza sola.
    assert fila.formula_ast["piso"] == []
    assert fila.formula_ast["parametros"]["REFERENCIA"] == [
        "AR.ASIGNACION-HIJO",
        "AR.ASIGNACION-HIJO-DISCAPACIDAD",
    ]


def test_los_parametros_de_la_cuantia_entran_con_su_rol(conexion: Connection, curado) -> None:
    """Un parámetro de referencia no es un piso.

    El cargador guardaba solo los de piso, porque el primer beneficio curado no
    tenía otros. Perder el rol dejaría a la AUH indistinguible de un monto que
    nadie actualiza.
    """
    roles = dict(
        conexion.execute(
            text(
                "SELECT p.codigo, cp.rol FROM cuantia_parametros cp "
                "  JOIN parametros p ON p.id = cp.parametro_id"
            )
        ).all()
    )
    assert roles == {
        "AR.ASIGNACION-HIJO": "REFERENCIA",
        "AR.ASIGNACION-HIJO-DISCAPACIDAD": "REFERENCIA",
    }


def test_lo_que_la_ley_no_resuelve_queda_sin_condicion_ejecutable(
    conexion: Connection, curado
) -> None:
    """El artículo 20 dice que cobra uno solo de los progenitores y no dice cuál.

    Elegir un criterio —la madre, quien pida primero— sería escribir la parte
    que el legislador no escribió, y esa elección decide quién cobra.
    """
    sin_ast = [
        fila.texto_literal
        for fila in conexion.execute(text("SELECT texto_literal FROM reglas WHERE ast IS NULL"))
    ]
    assert any("percibidas por uno solo de ellos" in literal for literal in sin_ast)
    assert curado.reglas_sin_formalizar >= 2


def test_nada_de_esto_entra_aprobado(conexion: Connection, curado) -> None:
    """Ni una regla ejecutable ni el beneficio: la evaluación no los usa hasta
    que una persona con competencia jurídica los apruebe."""
    estados = {
        fila[0] for fila in conexion.execute(text("SELECT DISTINCT estado_revision FROM reglas"))
    }
    assert estados == {"CANDIDATE"}
    assert (
        conexion.execute(
            text(
                "SELECT count(*) FROM registro_versiones WHERE entidad_tipo = 'BENEFICIO' "
                "  AND estado_revision <> 'CANDIDATE'"
            )
        ).scalar_one()
        == 0
    )
