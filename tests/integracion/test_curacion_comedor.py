"""HU-011, HU-013 y HU-017: la beca de comedor de la Ordenanza CABA 43.478.

Es el primer beneficio del corpus que no se paga en dinero: lo que recibe el
alumno es el almuerzo. Y es una norma de 1989 con texto consolidado, donde los
umbrales están en «sueldos mínimos», una unidad que la ordenanza no define.
Estas pruebas fijan las dos cosas: que la cuantía se guarde como especie y no
como un importe, y que ese umbral no se asimile a otro por analogía.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios, LecturaInvalida
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA = RAIZ / "docs" / "curaduria" / "ordenanza-caba-43478.json"

ARTICULOS = [
    (
        "ARTICULO",
        "10",
        "Art. 10. El Departamento Ejecutivo otorgará a los alumnos que concurran a las escuelas "
        "dependientes de la comuna, becas totales o medias becas para afrontar los gastos de "
        "Comedor, Refrigerio y Vianda, cuyas características y cantidades fijará anualmente el "
        "Concejo Deliberante.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-10",
    ),
    (
        "ARTICULO",
        "13",
        "Art. 13. La Secretaría de Educación priorizará el otorgamiento de las bocas a las "
        "escuelas que se encuentren en zonas de mayor demanda por sus características "
        "socioeconómicas.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-13",
    ),
    (
        "ARTICULO",
        "14",
        "Art. 14. El valor de la ración del servicio de comedor, refrigerio y vianda de los "
        "alumnos no becados no podrá superar el valor de la ración del alumno becado.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-14",
    ),
    (
        "PARRAFO",
        None,
        "Una vez constituida la Comisión se reunirá a los efectos de considerar las solicitudes "
        "recibidas, evaluándolas, determinará por simple mayoría de votos el otorgamiento o "
        "denegatoria de la beca, conforme a lo dispuesto en el Art. 16. El dictamen que "
        "deniegue el pedido deberá ser fundado y notificado al interesado quien tendrá derecho "
        "a recurrir directamente por vía de apelación dentro de los diez (10) días de ser "
        "notificado ante la Secretaría de Educación de la Comuna.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-15/parrafo-35",
    ),
    (
        "PARRAFO",
        None,
        "Dicha Comisión podrá reveer en cualquier momento el otorgamiento de la beca anual si "
        "se produjeran modificaciones en las circunstancias que motivaron el otorgamiento de la "
        "misma.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-15/parrafo-36",
    ),
    (
        "PARRAFO",
        None,
        "A los alumnos, que sean hijos de beneficiarios de Programas Alimentarlos Nacionales, "
        "Provinciales o Municipales.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-16/parrafo-39",
    ),
    (
        "PARRAFO",
        None,
        "Alumnos que estén a cargo de una sola persona (padre, madre, tutor o encargado) cuyo "
        "ingreso mensual sea hasta dos (2) sueldos mínimos. Alumnos que sean hijos de ex "
        "combatientes de Malvinas. Alumnos a cargo de jubilados y/o pensionados que perciban un "
        "haber hasta dos sueldos mínimos. Alumnos cuyas familias tengan ingresos hasta dos (2) "
        "sueldos mínimos.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-16/parrafo-40",
    ),
    (
        "PARRAFO",
        None,
        "Alumnos cuyas familias perciban un haber hasta cuatro (4) sueldos mínimos. Alumnos que "
        "provengan de familias numerosas, con hermanos en edad escolar cuando hicieran uso del "
        "comedor dos o más hermanos. Alumnos discapacitados o bajo tratamiento médico "
        "prolongado. Alumnos hijos de personal docente o no docente de la Escuela.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-16/parrafo-42",
    ),
    (
        "PARRAFO",
        None,
        "Los datos del solicitante, en los que se constata la situación socioeconómica familiar "
        "o particular, que le permita acceder a la beca serán suministrados por simple "
        "�declaración Jurada�, pudiendo la Comisión de Becas solicitar otros datos en aquellos "
        "casos en que lo considere necesario.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-16/parrafo-43",
    ),
    (
        "ARTICULO",
        "17",
        "Art. 17. Cuando el solicitante estuviese incluido en más de una de las causales "
        "mencionadas en el artículo anterior se procederá simplemente otorgando el mayor "
        "beneficio.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-17",
    ),
    (
        "ARTICULO",
        "18",
        "Art. 18. La solicitud de Beca se presentará en el momento de la inscripción, al "
        "finalizar el periodo escolar. La Comisión de Becas recibirá las solicitudes y elevará "
        "el pedido a !a DICOES.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-18",
    ),
    (
        "ARTICULO",
        "19",
        "Art. 19. La Comisión de Becas deberá expedirse en un plazo no mayor de siete (7) días "
        "corridos contados a partir del inicio del ciclo lectivo. Transcurrido el mismo, sin "
        "que mediara decisión, el solicitante podrá recurrir ante la Secretaría de Educación de "
        "la Municipalidad de la Ciudad de Buenos Aires.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-19",
    ),
    (
        "ARTICULO",
        "20",
        "Art. 20. Durante todo el ciclo lectivo podrán solicitarse becas de comedor, refrigerio "
        "o vianda, por circunstancias excepcionales, debiendo la Comisión expedirse, en el "
        "plazo de siete (7) días contados a partir de la presentación de la solicitud.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-20",
    ),
    (
        "ARTICULO",
        "21",
        "Art. 21. La Comisión de Becas a pedido del solicitante podrá otorgar beca total o "
        "media beca en casos no incluidos el Art. 16. Para estos casos se requerirá, la "
        "conformidad del DICOES.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-21",
    ),
    (
        "ARTICULO",
        "22",
        "Art. 22. los docentes de grado podrán solicitar becas a la Comisión en aquellos casos "
        "de alumnos en situación de riesgo social y que por sí o por falta de responsable no la "
        "hayan solicitado.",
        "DISPOSITIVO",
        "capitulo-VI/articulo-22",
    ),
]


@pytest.fixture
def norma(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma

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
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()


@pytest.fixture
def curado(conexion: Connection, norma):
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


def test_cada_cita_esta_en_la_unidad_que_dice_citar(conexion: Connection, curado) -> None:
    assert curado.reglas == 16
    filas = conexion.execute(
        text(
            "SELECT r.texto_literal, u.texto FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    for literal, unidad in filas:
        assert " ".join(literal.split()) in " ".join(unidad.split())


def test_lo_que_se_recibe_es_una_cosa_y_no_un_importe(conexion: Connection, curado) -> None:
    """Guardar la beca como fórmula obligaría a inventar un número, y el número
    es justamente lo que la ordenanza no da: el valor de la ración sale de la
    licitación de cada distrito."""
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, formula_ast, descripcion_especie   FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "ESPECIE"
    assert fila.valor_fijo is None
    assert fila.formula_ast is None
    assert "comedor, refrigerio o vianda" in fila.descripcion_especie


def test_un_tipo_de_cuantia_que_el_cargador_no_sabe_guardar_detiene_la_carga(
    conexion: Connection, norma, tmp_path
) -> None:
    """Un FIJO exige un valor y una moneda que ninguna lectura trajo todavía.

    Escribir ese camino sin un caso real sería adivinar cómo se guarda un monto
    que después se sirve como «lo que vas a cobrar».
    """
    import json

    lectura = json.loads(LECTURA.read_text())
    lectura["cuantia"]["tipo"] = "FIJO"
    ruta = tmp_path / "fija.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida, match="FORMULA, ESPECIE"):
        CuradorDeBeneficios(conexion).cargar(ruta)


def test_el_sueldo_minimo_no_se_asimila_al_salario_minimo_nacional(
    conexion: Connection, curado
) -> None:
    """La ordenanza mide en «sueldos mínimos» y no lo define.

    En 1989 la Municipalidad tenía su propio sueldo mínimo, distinto del salario
    mínimo, vital y móvil nacional. Apuntar al SMVM sería decidir, sin que lo
    diga ninguna norma, cuál es el umbral que separa a quien come gratis de
    quien paga media ración.
    """
    codigos = set(
        conexion.execute(
            text(
                "SELECT p.codigo FROM regla_parametros rp "
                "  JOIN parametros p ON p.id = rp.parametro_id"
            )
        ).scalars()
    )
    assert codigos == {"CABA.SUELDO-MINIMO"}
    assert "AR.SMVM" not in codigos


def test_el_plazo_que_dice_corridos_y_el_que_no_no_se_igualan(conexion: Connection, curado) -> None:
    """Los artículos 19 y 20 dan siete días y sólo uno dice «corridos».

    En una norma que distingue, la omisión no parece un descuido: suponer
    corridos acorta el plazo del organismo y suponer hábiles lo alarga.
    """
    tipos = dict(
        conexion.execute(
            text("SELECT evento_inicio, tipo_dia FROM plazos WHERE cantidad = 7")
        ).all()
    )
    assert tipos["inicio del ciclo lectivo"] == "CORRIDO"
    assert tipos["presentación de la solicitud excepcional"] == "NO_INFORMADO"


def test_la_via_para_quien_no_entra_en_ninguna_causal_queda_declarada(
    conexion: Connection, curado
) -> None:
    """El artículo 21 deja otorgar la beca en casos no previstos.

    Sin esa arista, una lectura diría que fuera del artículo 16 no hay nada, y
    el texto dice lo contrario.
    """
    dependencias = (
        conexion.execute(
            text(
                "SELECT r.texto_literal FROM regla_dependencias rd "
                "  JOIN reglas r ON r.id = rd.regla_id "
                " WHERE rd.tipo = 'EXCEPCION_DE'"
            )
        )
        .scalars()
        .all()
    )
    assert any("casos no incluidos" in t for t in dependencias)
