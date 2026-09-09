"""HU-035: el decreto que puso el texto vigente de la AUH, y el que sacó el tope.

El Decreto 840/2020 reescribió los artículos 14 bis y 14 ter de la Ley 24.714.
Sus reglas son las mismas que hoy tiene el texto consolidado, y esa repetición es
el punto: quien pregunte por qué la residencia son dos años y no tres tiene que
poder llegar al decreto que lo cambió y no solo al texto donde quedó.

Lo que el decreto sacó es lo que estas pruebas cuidan: el texto de 2009 topeaba
la prestación en cinco menores acumulables y el de 2020 no lo tiene. Los dos
están en el corpus y el de 2009 no dice en ninguna parte que fue reemplazado.
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
LECTURA = RAIZ / "docs" / "curaduria" / "decreto-nacional-840-2020.json"

UNIDADES = [
    (
        "ARTICULO",
        "1",
        "ARTÍCULO 1°.- Sustitúyese el artículo 14 bis de la Ley Nº 24.714 y sus modificatorias, "
        "el cual quedará redactado de la siguiente forma:",
        "DISPOSITIVO",
        "articulo-1",
    ),
    (
        "PARRAFO",
        None,
        '"ARTÍCULO 14 bis.- La Asignación Universal por Hijo para Protección Social consistirá '
        "en una prestación monetaria no retributiva de carácter mensual, que se abonará a uno "
        "solo o una sola de los padres o de las madres, tutor o tutora, curador o curadora o "
        "pariente por consanguinidad hasta el tercer grado, por cada niña, niño y/o adolescente "
        "menor de DIECIOCHO (18) años que se encuentre a su cargo, o sin límite de edad cuando "
        "se trate de una persona con discapacidad; en ambos casos, siempre que no estuviere "
        "empleado o empleada, emancipado o emancipada o percibiendo alguna de las prestaciones "
        'previstas en la presente Ley".',
        "SUSTITUTIVO",
        "articulo-1/parrafo-4",
    ),
    (
        "INCISO",
        "a",
        "a. Que la niña, el niño, adolescente y/o la persona con discapacidad sea argentino o "
        "argentina nativo o nativa, naturalizado o naturalizada o por opción. Cuando la niña, el "
        "niño, adolescente y/o la persona con discapacidad y sus progenitores o sus progenitoras "
        "o las personas que los o las tengan a cargo sean extranjeros o extranjeras, deberán "
        "acreditar tanto la niña, el niño, adolescente y/o la persona con discapacidad como el o "
        "la titular que percibirá la Asignación, DOS (2) años de residencia legal en el país.",
        "SUSTITUTIVO",
        "articulo-2/inciso-a-7",
    ),
    (
        "INCISO",
        "c",
        "Acreditar que la persona que percibirá el beneficio tiene a su cargo a la niña, al "
        "niño, adolescente y/o persona con discapacidad, en función de las disposiciones del "
        "Código Civil y Comercial de la Nación y de conformidad con la documentación que la "
        "ADMINISTRACIÓN NACIONAL DE LA SEGURIDAD SOCIAL (ANSES) disponga a estos fines.",
        "SUSTITUTIVO",
        "articulo-2/inciso-c-9",
    ),
    (
        "INCISO",
        "e",
        "Hasta los CUATRO (4) años de edad -inclusive-, deberá acreditarse el cumplimiento de "
        "los controles sanitarios y del plan de vacunación obligatorio. Desde los CINCO (5) años "
        "de edad y hasta los DIECIOCHO (18) años, deberá acreditarse además la concurrencia de "
        "las niñas, los niños y adolescentes obligatoriamente a establecimientos educativos "
        "públicos.",
        "SUSTITUTIVO",
        "articulo-2/inciso-e-11",
    ),
    (
        "INCISO",
        "f",
        "Acreditar que el o la titular del beneficio y la niña, el niño, adolescente y/o persona "
        'con discapacidad residen en el país".',
        "SUSTITUTIVO",
        "articulo-2/inciso-f-12",
    ),
    (
        "PARRAFO",
        None,
        "El VEINTE POR CIENTO (20 %) reservado podrá cobrarse cuando el o la titular acredite, "
        "para los o las menores de hasta los CUATRO (4) años de edad -inclusive-, el "
        "cumplimiento de los controles sanitarios y el plan de vacunación obligatorio; y para "
        "los y las de edad escolar, la certificación que acredite, además, el cumplimiento del "
        "ciclo escolar lectivo correspondiente.",
        "SUSTITUTIVO",
        "articulo-3/parrafo-16",
    ),
]


@pytest.fixture
def curado(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="F33",
        external_id="infoleg:343905:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR",
            "infoleg_id": "343905",
            "tipo": "DECRETO",
            "numero": "840",
            "anio": 2020,
            "titulo": "LEY Nº 24.714 - MODIFICACION",
            "fechas": {"PUBLICACION": "2020-11-04"},
        },
        unidades=UNIDADES,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


def test_el_decreto_modifica_y_no_crea(conexion: Connection, curado) -> None:
    """No hay dos AUH: hay una, y este decreto le cambió el texto."""
    rol = conexion.execute(
        text(
            "SELECT bn.rol FROM beneficio_normas bn "
            "  JOIN beneficio_versiones bv ON bv.registro_version_id = bn.beneficio_version_id "
            "  JOIN beneficios b ON b.id = bv.beneficio_id "
            " WHERE b.codigo = 'AR.AUH'"
        )
    ).scalar_one()
    assert rol == "MODIFICA"


def test_el_tope_de_cinco_menores_queda_como_conflicto_y_no_como_regla(
    conexion: Connection, curado
) -> None:
    """El texto de 2009 sigue en el corpus diciendo que hay tope.

    Y no dice en ninguna parte que fue reemplazado, así que quien lo lea hoy
    concluiría que una familia con seis hijos cobra por cinco. Cargarlo como
    regla haría que el sistema lo afirmara; callarlo dejaría al lector solo.
    """
    assert curado.conflictos == 1
    incidencia = conexion.execute(
        text(
            "SELECT tipo, estado, descripcion FROM incidencias_revision "
            " WHERE descripcion LIKE '%EL-TOPE-DE-CINCO-MENORES-YA-NO-ESTA%'"
        )
    ).one()
    assert incidencia.tipo == "CONFLICTO_DE_FUENTES"
    assert incidencia.estado == "ABIERTA"
    assert "CINCO (5) menores" in incidencia.descripcion
    # Ninguna regla afirma el tope.
    reglas = conexion.execute(
        text("SELECT count(*) FROM reglas WHERE texto_literal LIKE '%máximo acumulable%'")
    ).scalar_one()
    assert reglas == 0


def test_los_controles_de_salud_no_condicionan_el_acceso(conexion: Connection, curado) -> None:
    """Es la diferencia entre «no te corresponde» y «te falta un papel».

    No acreditar los controles no quita el derecho a la asignación: posterga el
    cobro del veinte por ciento reservado. Escribirlo como condición de
    aplicabilidad respondería lo primero.
    """
    ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE texto_literal LIKE 'Hasta los CUATRO (4) años%'")
    ).scalar_one()
    assert ast is None


def test_la_residencia_se_le_pide_a_los_dos(conexion: Connection, curado) -> None:
    """El texto de 2009 pedía tres años y solo al menor; este pide dos y a los dos.

    Si la condición se escribiera sobre una sola persona, alguien con dos años de
    residencia cuyo hijo tiene uno pasaría, y el decreto dice que no.
    """
    ast = conexion.execute(
        text("SELECT ast::text FROM reglas WHERE texto_literal LIKE '%DOS (2) años de residencia%'")
    ).scalar_one()
    assert "residencia_legal_del_causante" in ast
    assert "residencia_legal_del_titular" in ast
