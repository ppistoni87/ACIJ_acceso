"""HU-011 y HU-035: un beneficio leído desde dos normas que no coinciden.

La Ley CABA 547 sustituyó en 2001 los artículos 10 y 16 de la Ordenanza 43.478,
que es la que crea la beca de comedor. Es la misma beca, así que las dos
lecturas cargan sobre el mismo beneficio, y eso pone a prueba dos cosas que
antes no existían: que una lectura no retire las reglas que escribió la otra, y
que el corpus pueda tener dos redacciones del mismo artículo diciendo cosas
distintas sin que la carga elija una.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios, LecturaInvalida
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA_ORDENANZA = RAIZ / "docs" / "curaduria" / "ordenanza-caba-43478.json"
LECTURA_LEY = RAIZ / "docs" / "curaduria" / "ley-caba-547.json"

# El texto es el capturado de NormativaBA, con la anidación que trae: los
# artículos sustituidos cuelgan del artículo sustituyente.
UNIDADES_LEY = [
    (
        "ARTICULO",
        "1",
        "Artículo 1° - Sustitúyese el artículo 10 de la Ordenanza N° 43.478 (B.M. N° 18.466, "
        "texto conforme artículo 12 de la Ordenanza N° 45.518, B.M. N° 19.234) por el "
        "siguiente:",
        "DISPOSITIVO",
        "articulo-1",
    ),
    (
        "ARTICULO",
        "10",
        "Artículo 10 - El Poder Ejecutivo brindará un servicio de desayuno o de merienda en "
        "forma indistinta y gratuita a todos los alumnos que lo consuman en las escuelas "
        "dependientes del Gobierno de la Ciudad incorporadas al respectivo programa. Sin "
        "perjuicio de lo precedentemente dispuesto, el Poder Ejecutivo otorgará becas totales "
        "o medias becas, cuyas características y cantidades fijará anualmente la Legislatura "
        "de la Ciudad para que los alumnos que concurren a las escuelas dependientes de la "
        "Comuna puedan afrontar los gastos de los servicios de comedor, refrigerio y vianda. "
        "Para los asistentes a jardines maternales o a escuelas o colegios con régimen de "
        "internado, el beneficio que se otorgue comprenderá también el pago del gasto que "
        "insuma el servicio de cena que se suministre en tales jardines, escuelas o colegios.",
        "SUSTITUTIVO",
        "articulo-1/articulo-10[sustitutivo:2]",
    ),
    (
        "ARTICULO",
        "2",
        "Artículo 2° - Sustitúyese el artículo 16 de la Ordenanza N° 43.478 (B.M. N° 18.466, "
        "texto conforme artículo 14 de la Ordenanza N° 45.518, B.M. N° 19.234) por el "
        "siguiente:",
        "DISPOSITIVO",
        "articulo-2",
    ),
    (
        "ARTICULO",
        "16",
        "Artículo 16 - La Comisión para el otorgamiento de las becas de Comedor, Refrigerio y "
        "Vianda, destinadas a los alumnos de las escuelas dependientes del Gobierno de la "
        "Ciudad de Buenos Aires, otorgará becas totales a los mismos cuando la totalidad de "
        "los ingresos mensuales del grupo familiar al que pertenecen no supere el equivalente "
        "al sueldo mínimo fijado en el convenio para empleados de comercio, multiplicado por "
        "2,5. De igual manera, se otorgarán medias becas cuando los referidos ingresos superen "
        "el tope establecido para las becas totales sin llegar a exceder el equivalente al "
        "sueldo mínimo fijado en el convenio para empleados de comercio, multiplicado por 3,5.",
        "SUSTITUTIVO",
        "articulo-2/articulo-16[sustitutivo:4]",
    ),
    (
        "PARRAFO",
        None,
        "Cuando el grupo familiar esté integrado por más de un niño que concurra a la escuela "
        "pública, el tope de ingresos fijado para determinar la modalidad de la beca a "
        "otorgarse de conformidad a lo dispuesto en el presente artículo, se incrementará en "
        "un quince por ciento (15%) por cada niño que se sume.",
        "DISPOSITIVO",
        "articulo-2/parrafo-5",
    ),
    (
        "PARRAFO",
        None,
        "En caso que un integrante del grupo familiar se encuentre afectado por una enfermedad "
        "crónica que requiera tratamiento continuo o por períodos prolongados, los gastos "
        "derivados de dicho tratamiento podrán deducirse del monto del ingreso mensual del "
        "grupo familiar que se toma como base para el otorgamiento de becas totales y medias "
        "becas. Estas circunstancias deberán ser debidamente acreditadas.",
        "DISPOSITIVO",
        "articulo-2/parrafo-6",
    ),
    (
        "PARRAFO",
        None,
        "Se concederán también becas totales, con prescindencia de los ingresos del grupo "
        "familiar, cuando se trate de hijos de personal docente, en el caso en que dicho "
        "personal se encuentre a cargo de los alumnos en turno de comedor que almuercen dentro "
        "del ámbito de éste.",
        "DISPOSITIVO",
        "articulo-2/parrafo-7",
    ),
    (
        "PARRAFO",
        None,
        "Los datos del solicitante, en los que se constate la situación socioeconómica familiar "
        "y particular que le permita acceder a la beca serán suministrados por declaración "
        "jurada, pudiendo la Comisión de Becas solicitar otros datos en aquellos casos en que "
        "lo considere necesario.",
        "DISPOSITIVO",
        "articulo-2/parrafo-8",
    ),
]


@pytest.fixture
def normas(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma
    from tests.integracion.test_curacion_comedor import ARTICULOS

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="F23",
        external_id="normativaba:38345:actualizado",
        tipo_version="ACTUALIZADO",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "38345",
            "tipo": "ORDENANZA",
            "numero": "43478",
            "anio": 1989,
            "titulo": "SERVICIO DE COMEDOR, REFRIGERIO Y VIANDA",
            "fechas": {"PUBLICACION": "1989-03-01"},
        },
        unidades=ARTICULOS,
    )
    _documento_norma(
        conexion,
        source_id="F23",
        external_id="normativaba:11223:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "11223",
            "tipo": "LEY",
            "numero": "547",
            "anio": 2001,
            "titulo": "MODIFICACIÓN DE LA ORDENANZA 43478",
            "fechas": {"PUBLICACION": "2001-01-25"},
        },
        unidades=UNIDADES_LEY,
        sufijo_url="-ley-547",
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()


def _reglas(conexion: Connection) -> dict[str, str]:
    return {
        fila[0]: fila[1]
        for fila in conexion.execute(
            text(
                "SELECT r.texto_literal, r.estado_revision FROM reglas r "
                "  JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id "
                "  JOIN beneficios b ON b.id = bv.beneficio_id "
                " WHERE b.codigo = 'CABA.BECA-COMEDOR-ESCOLAR'"
            )
        )
    }


def test_una_lectura_no_retira_las_reglas_que_escribio_la_otra(
    conexion: Connection, normas
) -> None:
    """Las dos lecturas comparten la versión del beneficio.

    Antes, cargar la segunda marcaba SUPERSEDED todo lo que había escrito la
    primera —ninguna de sus citas figura en el archivo de la otra— y el
    resultado dependía del orden de los archivos. Una lectura retira lo que
    ella misma escribió y nada más.
    """
    curador = CuradorDeBeneficios(conexion)
    curador.cargar(LECTURA_ORDENANZA)
    de_la_ordenanza = _reglas(conexion)
    assert de_la_ordenanza and set(de_la_ordenanza.values()) == {"CANDIDATE"}

    curador.cargar(LECTURA_LEY)
    despues = _reglas(conexion)
    for literal, estado in de_la_ordenanza.items():
        assert despues[literal] == estado, f"la Ley 547 retiró una regla de la ordenanza: {literal}"

    # Y al revés: volver a cargar la ordenanza no retira lo que escribió la ley.
    curador.cargar(LECTURA_ORDENANZA)
    final = _reglas(conexion)
    assert final == despues


def test_las_dos_redacciones_del_articulo_16_conviven_sin_que_la_carga_elija(
    conexion: Connection, normas
) -> None:
    """Dos textos del corpus dicen cosas distintas sobre el mismo umbral.

    El consolidado de NormativaBA mide en «sueldos mínimos» sin definirlos y la
    Ley 547 mide contra el sueldo del convenio de empleados de comercio. La
    carga deja las dos, con su cita, y abre el conflicto: cuál rige es una
    decisión jurídica y elegir una al cargar sería tomarla en silencio.
    """
    curador = CuradorDeBeneficios(conexion)
    curador.cargar(LECTURA_ORDENANZA)
    resultado = curador.cargar(LECTURA_LEY)
    assert resultado.conflictos == 1

    incidencia = conexion.execute(
        text(
            "SELECT tipo, severidad, estado, descripcion FROM incidencias_revision "
            " WHERE descripcion LIKE '%ARTICULO-16-CON-DOS-REDACCIONES%'"
        )
    ).one()
    assert incidencia.tipo == "CONFLICTO_DE_FUENTES"
    assert incidencia.estado == "ABIERTA"
    # La incidencia localiza los dos textos: sin eso, quien la lea tiene que
    # buscarlos a mano y no sabe si el conflicto sigue existiendo.
    assert "articulo-2" in incidencia.descripcion
    assert "capitulo-VI/articulo-16" in incidencia.descripcion

    literales = _reglas(conexion)
    assert any("multiplicado por 2,5" in t for t in literales)
    assert any("hasta dos (2) sueldos mínimos" in t for t in literales)


def test_el_umbral_de_la_ley_no_se_confunde_con_el_de_la_ordenanza(
    conexion: Connection, normas
) -> None:
    """Son dos parámetros, no dos nombres del mismo.

    La ordenanza dice «sueldo mínimo» y no lo define; la ley dice «el sueldo
    mínimo fijado en el convenio para empleados de comercio». Unificarlos sería
    decidir por analogía cuál es el ingreso que separa a quien come gratis de
    quien paga media ración.
    """
    curador = CuradorDeBeneficios(conexion)
    curador.cargar(LECTURA_ORDENANZA)
    curador.cargar(LECTURA_LEY)
    codigos = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT codigo FROM parametros WHERE codigo LIKE 'CABA.SUELDO-MINIMO%'")
        )
    }
    assert codigos == {"CABA.SUELDO-MINIMO", "CABA.SUELDO-MINIMO-CONVENIO-COMERCIO"}
    sin_valor = conexion.execute(
        text(
            "SELECT count(*) FROM parametro_valores pv JOIN parametros p ON p.id = pv.parametro_id "
            " WHERE p.codigo = 'CABA.SUELDO-MINIMO-CONVENIO-COMERCIO'"
        )
    ).scalar_one()
    assert sin_valor == 0


def test_un_conflicto_que_cita_un_texto_que_no_lo_dice_detiene_la_carga(
    conexion: Connection, normas, tmp_path: pathlib.Path
) -> None:
    """Un conflicto mal citado no es un conflicto: es un error de lectura.

    Abrir la incidencia igual dejaría a alguien buscando en un artículo que no
    dice nada de lo que la incidencia afirma.
    """
    lectura = json.loads(LECTURA_LEY.read_text(encoding="utf-8"))
    lectura["conflictos"][0]["ruta_evidencia"] = "articulo-2/parrafo-8"
    ruta = tmp_path / "conflicto-mal-citado.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida) as error:
        CuradorDeBeneficios(conexion).cargar(ruta)
    assert "articulo-2/parrafo-8" in str(error.value)
    abiertas = conexion.execute(
        text(
            "SELECT count(*) FROM incidencias_revision "
            " WHERE descripcion LIKE '%ARTICULO-16-CON-DOS-REDACCIONES%'"
        )
    ).scalar_one()
    assert abiertas == 0
