"""HU-011, HU-013 y HU-017: la asignación por ayuda escolar anual.

Es la única prestación de la Ley 24.714 que cruza los dos subsistemas: se cobra
por el contributivo y el artículo 14 sexies se la da también a los titulares de
la Asignación Universal por Hijo. Curarla cerrando ese cruce es lo que evita
responderle «no te corresponde» a alguien que cobra la AUH.
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
LECTURA = RAIZ / "docs" / "curaduria" / "ley-nacional-24714-ayuda-escolar.json"

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
        "10",
        "ARTICULO 10.- La asignación por ayuda escolar anual consistirá en el pago de una suma "
        "de dinero que se hará efectiva en el mes de marzo de cada año. Esta asignación se "
        "abonará por cada hijo que concurra regularmente a establecimientos de enseñanza básica "
        "y polimodal o bien, cualquiera sea su edad, si concurre a establecimientos oficiales o "
        "privados donde se imparta educación diferencial. (párrafo modificado por art. 3° de la "
        "Ley N° 25.231 B.O. 31/12/1999)",
        "DISPOSITIVO",
        "articulo-10",
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
        "INCISO",
        "d",
        "d) Asignación por ayuda escolar anual para la educación inicial, general básica y "
        "polimodal: la suma de $ 130. (Inciso sustituido por art. 4° de la Ley N° 25.231 B.O. "
        "31/12/1999)",
        "DISPOSITIVO",
        "articulo-18/inciso-d-79",
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


def test_las_dos_puertas_de_entrada_estan_las_dos(conexion: Connection, curado) -> None:
    """Se entra por el subsistema contributivo o por ser titular de la AUH.

    Una lectura que sólo mire el artículo 6 inciso d) le responde «no te
    corresponde» a quien cobra la AUH, que es exactamente a quien el artículo 14
    sexies se la da.
    """
    poblaciones = set(
        conexion.execute(
            text(
                "SELECT p.codigo FROM beneficio_poblaciones bp "
                "  JOIN poblaciones p ON p.id = bp.poblacion_id"
            )
        ).scalars()
    )
    assert "AR.TRABAJADOR-EN-RELACION-DE-DEPENDENCIA" in poblaciones
    assert "AR.TITULAR-DEL-SUBSISTEMA-NO-CONTRIBUTIVO" in poblaciones

    claves = (
        conexion.execute(text("SELECT texto_literal FROM reglas WHERE categoria = 'APLICABILIDAD'"))
        .scalars()
        .all()
    )
    assert any("subsistema contributivo" in t for t in claves)
    assert any("Los titulares de la Asignación Universal por Hijo" in t for t in claves)


def test_las_dos_puertas_avisan_que_no_son_requisitos_acumulativos(
    conexion: Connection, curado
) -> None:
    """Escritas como dos reglas de aplicabilidad separadas, un evaluador que las
    exija juntas dejaría afuera a todo el mundo. El motivo lo dice."""
    motivos = conexion.execute(
        text(
            "SELECT alcance FROM reglas "
            " WHERE texto_literal LIKE '%subsistema contributivo fundado%'"
        )
    ).scalar_one()
    assert "dejaría afuera a todo el mundo" in motivos


def test_los_niveles_educativos_derogados_no_se_traducen(conexion: Connection, curado) -> None:
    """«Básica y polimodal» son los niveles de una ley derogada en 2006.

    Traducirlos acá sería decidir por analogía qué nivel corresponde a cuál, y de
    eso depende si un chico de sala de cinco entra o no.
    """
    motivo = conexion.execute(
        text("SELECT alcance FROM reglas WHERE texto_literal LIKE '%educación diferencial%'")
    ).scalar_one()
    assert "26.206" in motivo
    abiertas = conexion.execute(
        text(
            "SELECT count(*) FROM incidencias_revision "
            " WHERE estado = 'ABIERTA' AND descripcion LIKE '%26.206%'"
        )
    ).scalar_one()
    assert abiertas == 1


def test_esta_asignacion_no_esta_exceptuada_del_tope(conexion: Connection, curado) -> None:
    """El artículo 3 exceptúa maternidad e hijo con discapacidad, y a ninguna otra.

    Omitir la exclusión acá haría que esta prestación pareciera fuera del alcance
    del tope, que es lo contrario de lo que dice el texto.
    """
    fila = conexion.execute(
        text(
            "SELECT categoria, alcance FROM reglas "
            " WHERE texto_literal LIKE '%Quedan excluidos de las prestaciones%'"
        )
    ).one()
    assert fila.categoria == "EXCLUSION"
    assert "no** está exceptuada" in fila.alcance or "no está exceptuada" in fila.alcance


def test_una_fecha_recurrente_sin_anio_dice_que_es_una_aproximacion(
    conexion: Connection, curado
) -> None:
    """«El mes de marzo de cada año» no es un plazo que corra desde un evento.

    El modelo guarda intervalos y plazos relativos, y ninguno describe eso: se
    carga aproximado y el motivo lo dice, en vez de fingir precisión.
    """
    fila = conexion.execute(text("SELECT tipo, evento_inicio FROM plazos")).one()
    assert fila.tipo == "FECHA_PAGO"
    assert "marzo" in fila.evento_inicio
