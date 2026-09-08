"""HU-011 y HU-035: el decreto que reglamenta el Régimen de Becas Estudiantiles.

El Decreto CABA 75/2015 no crea un beneficio: precisa a quién está destinado el
de la Ley 2917 y conserva la beca a quienes la venían cobrando desde programas
del Ministerio. Lo que estas pruebas fijan es que se lea sobre el mismo
beneficio que la ley, que su excepción no se pierda, y que una cita no pueda
cruzar de unidad cuando el boletín parte una oración en tres.
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
LECTURA = RAIZ / "docs" / "curaduria" / "decreto-caba-75-2015.json"

# El texto es el capturado: NormativaBA parte la oración del artículo 1 en tres
# unidades, y la del artículo 2 en dos.
UNIDADES = [
    (
        "ARTICULO",
        "1",
        "Artículo 1°.- Establécese que el Régimen de Becas Estudiantiles creado por la Ley N°",
        "DISPOSITIVO",
        "articulo-1",
    ),
    (
        "PARRAFO",
        None,
        "2.917 se encuentra destinado a aquellos alumnos/as regulares matriculados que cursen "
        "obligatoriamente en escuelas de nivel medio de gestión estatal de todas las modalidades "
        "y orientaciones dependientes del Ministerio de Educación de la Ciudad",
        "DISPOSITIVO",
        "articulo-1/parrafo-4",
    ),
    (
        "PARRAFO",
        None,
        "Autónoma de Buenos Aires.",
        "DISPOSITIVO",
        "articulo-1/parrafo-5",
    ),
    (
        "ARTICULO",
        "2",
        "Artículo 2°.- Exceptúase de lo establecido en el artículo precedente a aquellos "
        "alumnos/as inscriptos en proyectos y programas implementados por el Ministerio de "
        "Educación con financiamiento del Gobierno de la Ciudad Autónoma de Buenos Aires que "
        "hayan sido beneficiarios de la beca otorgada en el marco del Régimen de Becas",
        "DISPOSITIVO",
        "articulo-2",
    ),
    (
        "PARRAFO",
        None,
        "Estudiantiles, creado por el artículo 1° de la Ley N° 2.917, y que a la fecha del "
        "dictado del presente se encuentren cursando estudios de nivel medio a través de los "
        "proyectos y programas mencionados, quienes podrán solicitar la renovación de dicho "
        "beneficio en tanto no se configuren los supuestos del artículo 16 de la citada Ley.",
        "DISPOSITIVO",
        "articulo-2/parrafo-7",
    ),
    (
        "ARTICULO",
        "3",
        "Artículo 3°.- El Ministerio de Educación dicta las normas operativas, complementarias y "
        "aclaratorias necesarias para la implementación de los mecanismos de recepción de "
        "solicitudes de becas y su otorgamiento y control, la evaluación socio-ambiental "
        "mediante muestras testigo, el seguimiento de los beneficiarios por parte de las "
        "autoridades escolares y la prevención del abandono escolar por parte de los "
        "beneficiarios, así como todas aquellas normas que considere necesarias para la "
        "ejecución del Régimen de Becas Estudiantiles, establecido en la Ley N° 2.917.",
        "DISPOSITIVO",
        "articulo-3",
    ),
    (
        "ARTICULO",
        "4",
        "Artículo 4°.- Derógase el Decreto N° 976/08.",
        "DISPOSITIVO",
        "articulo-4",
    ),
]


@pytest.fixture
def norma(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="F23",
        external_id="normativaba:273414:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "273414",
            "tipo": "DECRETO",
            "numero": "75",
            "anio": 2015,
            "titulo": "RÉGIMEN DE BECAS ESTUDIANTILES",
            "fechas": {"PUBLICACION": "2015-02-20"},
        },
        unidades=UNIDADES,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()


@pytest.fixture
def curado(conexion: Connection, norma):
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


def test_el_decreto_reglamenta_y_no_crea(conexion: Connection, curado) -> None:
    """El rol con el que la norma queda atada al beneficio no es decorativo.

    Decir que el decreto crea la beca sería decir que antes de 2015 no existía,
    y existe desde 2008.
    """
    rol = conexion.execute(
        text(
            "SELECT bn.rol FROM beneficio_normas bn "
            "  JOIN beneficio_versiones bv ON bv.registro_version_id = bn.beneficio_version_id "
            "  JOIN beneficios b ON b.id = bv.beneficio_id "
            " WHERE b.codigo = 'CABA.BECAS-ESTUDIANTILES'"
        )
    ).scalar_one()
    assert rol == "REGLAMENTA"


def test_la_excepcion_sabe_de_que_regla_es_excepcion(conexion: Connection, curado) -> None:
    """Quien venía cobrando la beca por un programa del Ministerio la conserva.

    Sin la arista, el evaluador no puede cumplir la promesa de no negar sin
    haber mirado las excepciones: le respondería «no cumplís el artículo 1» a
    alguien a quien el decreto expresamente se la conserva.
    """
    fila = conexion.execute(
        text(
            "SELECT origen.texto_literal, referida.texto_literal FROM regla_dependencias rd "
            "  JOIN reglas origen ON origen.id = rd.regla_id "
            "  JOIN reglas referida ON referida.id = rd.regla_referida_id "
            " WHERE origen.texto_literal LIKE '%podrán solicitar la renovación%'"
        )
    ).one()
    assert "proyectos y programas mencionados" in fila[0]
    assert "cursen obligatoriamente" in fila[1]


def test_una_cita_no_cruza_de_unidad_aunque_la_oracion_si(
    conexion: Connection, norma, tmp_path: pathlib.Path
) -> None:
    """El boletín parte la oración del artículo 1 en tres unidades.

    Citarla entera parece lo correcto y no lo es: la evidencia localiza una
    unidad, y un fragmento que no está adentro de ella apunta a un texto que no
    dice lo que se afirma.
    """
    lectura = json.loads(LECTURA.read_text(encoding="utf-8"))
    lectura["reglas"][0]["texto_literal"] = (
        "Establécese que el Régimen de Becas Estudiantiles creado por la Ley N° 2.917 se "
        "encuentra destinado a aquellos alumnos/as regulares matriculados"
    )
    ruta = tmp_path / "cita-que-cruza.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida) as error:
        CuradorDeBeneficios(conexion).cargar(ruta)
    assert "no está en ninguna unidad" in str(error.value)


def test_lo_que_el_decreto_remite_al_ministerio_queda_dicho(conexion: Connection, curado) -> None:
    """Que el trámite no esté no es que no exista: está en otra norma.

    Un canal ausente sin motivo se lee como «no hay dónde ir». Y no es uno de
    los siete campos que la completitud evalúa, así que va como vacío
    declarado: si fuera como campo no informado no actualizaría ninguna fila y
    el motivo se perdería.
    """
    assert curado.vacios == 2
    descripcion = conexion.execute(
        text(
            "SELECT descripcion FROM incidencias_revision "
            " WHERE descripcion LIKE 'Decreto CABA 75/2015 · canales:%'"
        )
    ).scalar_one()
    assert "Ministerio de Educación" in descripcion


def test_un_vacio_que_si_es_uno_de_los_siete_campos_detiene_la_carga(
    conexion: Connection, norma, tmp_path: pathlib.Path
) -> None:
    """Los dos lugares no son intercambiables.

    Un campo de los siete declarado como vacío quedaría de incidencia y no
    tocaría la evaluación de completitud, que es lo que la API sirve cuando
    alguien pregunta si le pueden quitar el beneficio.
    """
    lectura = json.loads(LECTURA.read_text(encoding="utf-8"))
    lectura["vacios_declarados"].append(
        {
            "dato": "criterios_revocacion",
            "motivo": "Un motivo suficientemente largo como para pasar el control de longitud.",
        }
    )
    ruta = tmp_path / "vacio-que-es-campo.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida) as error:
        CuradorDeBeneficios(conexion).cargar(ruta)
    assert "campos_no_informados" in str(error.value)


def test_un_campo_no_informado_fuera_de_los_siete_detiene_la_carga(
    conexion: Connection, norma, tmp_path: pathlib.Path
) -> None:
    """Antes no hacía nada y no decía nada.

    La carga actualiza la evaluación del campo por su nombre: uno que no está
    entre los siete no tenía fila que actualizar, así que el motivo que escribió
    la curaduría se perdía en silencio.
    """
    lectura = json.loads(LECTURA.read_text(encoding="utf-8"))
    lectura["campos_no_informados"] = [
        {"campo": "canales", "motivo": "Lo remite el Ministerio y no está en esta norma."}
    ]
    ruta = tmp_path / "campo-inventado.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida) as error:
        CuradorDeBeneficios(conexion).cargar(ruta)
    assert "vacios_declarados" in str(error.value)


def test_un_campo_no_informado_entra_aunque_todavia_no_se_hayan_evaluado_los_campos(
    conexion: Connection, tmp_path: pathlib.Path
) -> None:
    """En una base poblada desde cero la evaluación todavía no existe.

    Los siete campos se evalúan después de la curación, porque varios salen de
    la lectura curada. Un UPDATE a secas no encontraba fila y terminaba sin
    error: en cada puesta en marcha limpia se perdía el motivo que la curaduría
    había escrito, y el campo quedaba en PENDIENTE, indistinguible de uno que
    nadie miró.
    """
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="F23",
        external_id="normativaba:273414:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "273414",
            "tipo": "DECRETO",
            "numero": "75",
            "anio": 2015,
            "titulo": "RÉGIMEN DE BECAS ESTUDIANTILES",
            "fechas": {"PUBLICACION": "2015-02-20"},
        },
        unidades=UNIDADES,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    # A propósito no se corre `EvaluadorDeCampos`: es el orden de la población
    # real, donde los campos se evalúan después de cargar los beneficios.
    lectura = json.loads(LECTURA.read_text(encoding="utf-8"))
    lectura["campos_no_informados"] = [
        {
            "campo": "criterios_revocacion",
            "motivo": "El decreto no dice por qué se pierde la beca; eso está en la Ley 2917.",
        }
    ]
    ruta = tmp_path / "sin-evaluar-campos.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    CuradorDeBeneficios(conexion).cargar(ruta)
    estado, motivo = conexion.execute(
        text(
            "SELECT ec.estado, ec.motivo FROM evaluaciones_completitud ec "
            "  JOIN norma_versiones nv ON nv.registro_version_id = ec.norma_version_id "
            "  JOIN normas n ON n.id = nv.norma_id "
            " WHERE n.numero = '75' AND n.anio = 2015 "
            "   AND ec.campo_solicitado = 'criterios_revocacion'"
        )
    ).one()
    assert estado == "NO_INFORMADO_EN_FUENTES_REVISADAS"
    assert "Ley 2917" in motivo
