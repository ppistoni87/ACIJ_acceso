"""HU-011, HU-013 y HU-017: el primer beneficio curado desde el corpus.

La lectura jurídica vive en `docs/curaduria/` y estas pruebas verifican lo que
el cargador impone sobre ella, que es lo que la vuelve confiable: que cada
afirmación apunte a su artículo, que nada entre aprobado, y que lo que la ley
remite a la reglamentación no se complete.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import (
    CuradorDeBeneficios,
    LecturaInvalida,
    cargar_todas,
)
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA = RAIZ / "docs" / "curaduria" / "ley-caba-6935.json"

# Las unidades son las que la extracción produce hoy sobre el texto real de la
# norma, con sus rutas anidadas y su literalidad —erratas de la fuente
# incluidas—. Una prueba con artículos inventados y prolijos no probaría lo
# que hay que probar: que la cita de la lectura curada esté adentro de la
# unidad que dice citar, en el texto tal como se publicó.
ARTICULOS = [
    (
        "ARTICULO",
        "1",
        'Artículo 1°.- Objeto - Se cres el "Programa de apoyo para personas en situación de '
        'vulnerabilidad habitacional" en el ámbito de la Ciudad Autónoma de Buenos Aires a fin '
        "de garantizar el acceso a una solución habitacional transitoria mediante una prestación "
        "económica no retributiva, intransferible e inembargable, y la implementación de "
        "dispositivos de abordaje y acompañamiento social para promover la autonomía de los "
        "beneficiarios. El Programa es continuador del establecido por el Decreto 690/06, y se "
        "regirá exclusivamente por las disposiciones de la presente Ley.",
        "DISPOSITIVO",
        "articulo-1",
    ),
    (
        "ARTICULO",
        "2",
        "Art. 2°.- Beneficiarios - Son beneficiarios del presente programa las personas "
        "residentes en la Ciudad Autónoma de Buenos Aires que se encuentren en situación de calle "
        "efectiva o en riesgo habitacional inminente, todo ello conforme a las definiciones "
        "previstas en el artículo 2, incisos a) y b) de la Ley 3706. Quedan expresamente "
        "comprendidos en los alcances de la presente Ley aquellas personas que se encuentren en "
        "forma transitoria sin vivienda o refugio por causa de desocupación administrativa, "
        "incendio, derrumbe o catástrofes naturales",
        "DISPOSITIVO",
        "articulo-2",
    ),
    (
        "ARTICULO",
        "3",
        "Art. 3°.- Prestación económica - La prestación económica del presente programa se "
        "abonará a los beneficiarios con frecuencia mensual. La Autoridad de Aplicación "
        "establecerá una escala de montos diferenciada según la composición del hogar, la cual "
        "para grupos familiares de cuatro (4) o más miembros integrantes, en los meses que "
        "corresponda la actualización, no podrá ser inferior al monto del componente alquiler de "
        'la Canasta de Consumo para Hogares "tipo 5", publicada por el Instituto de '
        "Estadísticas y Censos de la Ciudad Autónoma de Buenos Aires (IDECBA), fijándose como "
        "valor inicial el correspondiente al mes de octubre 2025. La actualización de la "
        "prestación económica se realiza semestralmente en función de la evolución de los precios "
        "del alquiler de viviendas y afines, relevada por el Instituto de Estadística y Censos de "
        "la Ciudad Autónoma de Buenos Aires (IDECBA) con una periodicidad semestral, los meses de "
        "abril y octubre de cada ejercicio. Adicionalmente a la actualización prevista en el "
        "párrafo anterior, la Autoridad de Aplicación conjuntamente con el Ministerio de Hacienda "
        "y Finanzas, o el organismo que lo reemplace en el futuro, podrán acordar un incremento "
        "de la prestación económica referida",
        "DISPOSITIVO",
        "articulo-3",
    ),
    (
        "PARRAFO",
        None,
        "El ejercicio de la opción por parte del beneficiario de percibir la prestación económica "
        "alternativa en una (1) cuota única por solución habitacional estable resulta excluyente "
        "de la percepción de toda otra suma de dinero dispuesta en la presente Ley por el término "
        "que fije la reglamentación.",
        "DISPOSITIVO",
        "articulo-5/parrafo-9",
    ),
    (
        "INCISO",
        "a",
        "a) Acreditar identidad y residencia en la Ciudad Autónoma de Buenos Aires con una "
        "antigüedad mínima de dos (2) años. Quedan exceptuadas de este requisito las personas "
        "víctimas de trata de personas o violencia de género, debidamente acreditadas por los "
        "organismos competentes.",
        "DISPOSITIVO",
        "articulo-6/inciso-a-11",
    ),
    (
        "INCISO",
        "b",
        "b) No alcanzar el ingreso total de las familias, según su conformación, para cubrir la "
        "Canasta Básica Total (CBT) fijada por el Instituto Nacional de Estadísticas y Censos "
        "(INDEC), u organismo que en el futuro lo reemplace;",
        "DISPOSITIVO",
        "articulo-6/inciso-b-12",
    ),
    (
        "INCISO",
        "c",
        "c) No ser titular de bienes inmuebles ni percibir otros subsidios económicos de carácter "
        "habitacional de origen nacional, provincial o municipal.",
        "DISPOSITIVO",
        "articulo-6/inciso-c-13",
    ),
    (
        "PARRAFO",
        None,
        "La reglamentación podrá establecer mecanismos de interoperabilidad de datos para eximir "
        "a los solicitantes de presentar documentación que ya obrare en poder del Estado, y "
        "mecanismos flexibles para la acreditación de requisitos en casos de extrema "
        "vulnerabilidad o falta de documentación, admitiendo el ingreso provisorio.",
        "DISPOSITIVO",
        "articulo-6/parrafo-15",
    ),
    (
        "ARTICULO",
        "7",
        "Art. 7°.- Duración, permanencia y corresponsabilidades - La prestación económica se "
        "otorgará por un plazo inicial de hasta DOCE (12) meses. La Autoridad de Aplicación podrá "
        "disponer la prórroga del beneficio por períodos sucesivos. La continuidad de la "
        "prestación estará sujeta al cumplimiento de las corresponsabilidades definidas por la "
        "reglamentación.",
        "DISPOSITIVO",
        "articulo-7",
    ),
    (
        "ARTICULO",
        "8",
        "Art. 8°.- Ingreso provisorio y pago de emergencia - En casos de urgencia social o "
        "situación de calle efectiva, la Autoridad de Aplicación podrá disponer el ingreso "
        "provisorio al programa y liquidar la primera cuota de la prestación como pago de "
        "emergencia, aun cuando el hogar no cuente con la totalidad de la documentación "
        "requerida. La incorporación definitiva y la continuidad de los pagos subsiguientes "
        "quedarán condicionadas a la regularización documental dentro del plazo que fije la "
        "reglamentación y a la acreditación de la persistencia de la vulnerabilidad habitacional.",
        "DISPOSITIVO",
        "articulo-8",
    ),
]


@pytest.fixture
def norma(conexion: Connection):
    """La misma norma que la lectura curada cita, con sus artículos."""
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="D06",
        external_id="normativaba:830431:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "830431",
            "tipo": "LEY",
            "numero": "6935",
            "anio": 2025,
            "titulo": "PROGRAMA DE APOYO",
            "fechas": {"PUBLICACION": "2025-12-23"},
        },
        unidades=ARTICULOS,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()


@pytest.fixture
def curado(conexion: Connection, norma):
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


# --- Cada afirmación apunta a su artículo ---------------------------------------


def test_cada_regla_cita_el_articulo_que_la_sostiene(conexion: Connection, curado) -> None:
    """Una condición de acceso sin evidencia es una condición que el sistema
    inventó."""
    filas = conexion.execute(
        text(
            "SELECT r.categoria, u.ruta FROM reglas r "
            "  JOIN evidencias e ON e.id = r.evidencia_id "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id"
        )
    ).all()
    assert len(filas) == curado.reglas
    assert all(f.ruta.startswith("articulo-") for f in filas)
    # Los requisitos de acceso salen del artículo 6, no de cualquier lado, y de
    # sus incisos: la evidencia apunta al inciso que dice la condición, no al
    # artículo entero. Un requisito anclado al artículo completo se cumple aunque
    # el inciso que lo sostiene deje de estar.
    requisitos = {f.ruta for f in filas if f.categoria in ("APLICABILIDAD", "EXCLUSION")}
    assert requisitos
    assert all(r.startswith("articulo-6") for r in requisitos)
    assert all("/" in r for r in requisitos)


def test_una_ruta_que_no_existe_en_el_texto_detiene_la_carga(
    conexion: Connection, norma, tmp_path
) -> None:
    """Si la lectura cita un artículo que la norma no tiene, lo que sigue sería
    una regla colgada de nada."""
    lectura = json.loads(LECTURA.read_text())
    lectura["reglas"] = [{**lectura["reglas"][0], "ruta_evidencia": "articulo-99"}]
    ruta = tmp_path / "mala.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False))
    with pytest.raises(LecturaInvalida, match="articulo-99"):
        CuradorDeBeneficios(conexion).cargar(ruta)


def test_una_cita_que_no_esta_en_la_unidad_detiene_la_carga(
    conexion: Connection, norma, tmp_path
) -> None:
    """Una afirmación cuya evidencia no la dice es peor que una sin evidencia.

    Con la ruta existente y el texto cambiado, la carga seguiría adelante y la
    regla quedaría respaldada por un artículo que no dice eso. Es el error que
    no se nota: todo tiene evidencia, y la evidencia no dice lo que se afirma.
    """
    lectura = json.loads(LECTURA.read_text())
    regla = dict(lectura["reglas"][0])
    regla["texto_literal"] = "a) Acreditar residencia con una antigüedad mínima de diez (10) años."
    lectura["reglas"] = [regla]
    ruta = tmp_path / "lectura.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida, match="no está en la unidad"):
        CuradorDeBeneficios(conexion).cargar(ruta)


def test_el_error_de_cita_dice_en_que_unidad_si_esta(conexion: Connection, norma, tmp_path) -> None:
    """Cuando la segmentación se mueve, la cita sigue en el texto pero en otra
    unidad. El error lo dice para que se corrija la ruta en vez de la cita."""
    lectura = json.loads(LECTURA.read_text())
    regla = dict(lectura["reglas"][0])
    regla["ruta_evidencia"] = "articulo-1"
    lectura["reglas"] = [regla]
    ruta = tmp_path / "lectura.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LecturaInvalida, match="El texto sí está en 'articulo-6/inciso-a"):
        CuradorDeBeneficios(conexion).cargar(ruta)


def test_un_ast_que_no_cumple_el_contrato_detiene_la_carga(
    conexion: Connection, norma, tmp_path
) -> None:
    lectura = json.loads(LECTURA.read_text())
    lectura["reglas"] = [
        {**lectura["reglas"][0], "ast": {"schema_version": "1.0", "op": "eval", "args": []}}
    ]
    ruta = tmp_path / "mala.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False))
    with pytest.raises(LecturaInvalida, match="no cumple el contrato"):
        CuradorDeBeneficios(conexion).cargar(ruta)


# --- Nada entra aprobado ---------------------------------------------------------


def test_ninguna_regla_queda_ejecutable_sin_revision(conexion: Connection, curado) -> None:
    """Una regla ejecutable sin revisión decide accesos con la lectura de una
    sola persona. El esquema lo impide y el cargador no busca la vuelta."""
    filas = conexion.execute(text("SELECT estado_revision, requiere_revision FROM reglas")).all()
    assert all(f.estado_revision == "CANDIDATE" for f in filas)
    assert all(f.requiere_revision is True for f in filas)


def test_el_beneficio_nace_con_vigencia_desconocida(conexion: Connection, curado) -> None:
    """Que la ley esté publicada no dice desde cuándo rige el beneficio: eso lo
    decide la revisión con fundamento."""
    fila = conexion.execute(
        text(
            "SELECT rv.estado_revision, rv.valid_tipo FROM beneficio_versiones bv "
            "  JOIN registro_versiones rv ON rv.id = bv.registro_version_id"
        )
    ).one()
    assert fila.estado_revision == "CANDIDATE"
    assert fila.valid_tipo == "DESCONOCIDO"


# --- HU-013: los roles no se mezclan ----------------------------------------------


def test_la_poblacion_distingue_al_titular_del_grupo_familiar(conexion: Connection, curado) -> None:
    """La ley mide la residencia del titular y el ingreso del hogar. Mezclarlos
    excluye a quien califica."""
    roles = dict(
        conexion.execute(
            text("SELECT rol_persona, count(*) FROM beneficio_poblaciones GROUP BY 1")
        ).all()
    )
    assert roles.get("TITULAR", 0) >= 1
    assert roles.get("GRUPO_FAMILIAR", 0) == 1


def test_la_excepcion_sabe_de_que_regla_es_excepcion(conexion: Connection, curado) -> None:
    """Sin esa arista el evaluador no puede cumplir la promesa de no negar sin
    haber mirado las excepciones: no sabría cuáles mirar."""
    fila = conexion.execute(
        text(
            "SELECT g.categoria AS excepcion, r.categoria AS general, r.descripcion "
            "  FROM regla_dependencias d "
            "  JOIN reglas g ON g.id = d.regla_id "
            "  JOIN reglas r ON r.id = d.regla_referida_id "
            " WHERE d.tipo = 'EXCEPCION_DE'"
        )
    ).one()
    assert fila.excepcion == "EXCEPCION"
    assert "residencia" in fila.descripcion.lower()


def test_una_excepcion_que_apunta_a_una_regla_inexistente_no_se_carga(
    conexion: Connection, norma, tmp_path
) -> None:
    lectura = json.loads(LECTURA.read_text())
    for regla in lectura["reglas"]:
        if regla.get("excepcion_de"):
            regla["excepcion_de"] = "NO-EXISTE"
    ruta = tmp_path / "mala.json"
    ruta.write_text(json.dumps(lectura, ensure_ascii=False))
    with pytest.raises(LecturaInvalida, match="NO-EXISTE"):
        CuradorDeBeneficios(conexion).cargar(ruta)


# --- HU-017: suspensión, cese y revocación no se eligen por el legislador ---------


def test_lo_que_la_ley_remite_a_la_reglamentacion_no_se_formaliza(
    conexion: Connection, curado
) -> None:
    """Formalizar lo que la norma no dijo es la manera más rápida de que el
    sistema afirme algo que ninguna autoridad dispuso."""
    filas = conexion.execute(
        text(
            "SELECT categoria, ast, alcance FROM reglas "
            " WHERE categoria IN ('CESE', 'SUBSANACION', 'COMPATIBILIDAD')"
        )
    ).all()
    assert filas
    assert all(f.ast is None for f in filas)
    assert all(f.alcance and "reglamentaci" in f.alcance.lower() for f in filas)


def test_el_texto_literal_se_conserva_aunque_no_haya_ast(conexion: Connection, curado) -> None:
    """Sin condición formal, el texto es lo único que queda para que una persona
    decida. Perderlo dejaría la regla como un hueco sin nombre."""
    literal = conexion.execute(
        text("SELECT texto_literal FROM reglas WHERE categoria = 'CESE'")
    ).scalar_one()
    assert "corresponsabilidades" in literal


def test_los_criterios_de_revocacion_quedan_no_informados_con_su_motivo(
    conexion: Connection, curado
) -> None:
    """No informado no es inexistente: responder «no te lo pueden quitar» sería
    la lectura opuesta a la correcta."""
    fila = conexion.execute(
        text(
            "SELECT estado, motivo FROM evaluaciones_completitud "
            " WHERE campo_solicitado = 'criterios_revocacion'"
        )
    ).one()
    assert fila.estado == "NO_INFORMADO_EN_FUENTES_REVISADAS"
    assert "no elige" in fila.motivo


def test_la_salvaguarda_no_excluye_y_esta_declarada(conexion: Connection, curado) -> None:
    fila = conexion.execute(
        text("SELECT ast, descripcion FROM reglas WHERE categoria = 'SALVAGUARDA'")
    ).one()
    assert fila.ast is not None, "La salvaguarda sí se puede formalizar: la ley la define."
    assert "provisorio" in fila.descripcion


# --- La cuantía y el plazo no se inventan -----------------------------------------


def test_la_cuantia_no_sirve_un_piso_como_si_fuera_el_monto(conexion: Connection, curado) -> None:
    """La ley fija un piso para hogares de cuatro o más y remite el resto a la
    Autoridad de Aplicación. Servir el piso diría que todos cobran lo mismo."""
    fila = conexion.execute(
        text("SELECT tipo, valor_fijo, formula_version FROM beneficio_cuantias")
    ).one()
    assert fila.tipo == "FORMULA"
    assert fila.valor_fijo is None
    assert fila.formula_version


def test_el_plazo_no_declara_corridos_ni_habiles_porque_la_ley_no_lo_dice(
    conexion: Connection, curado
) -> None:
    fila = conexion.execute(text("SELECT cantidad, unidad, tipo_dia FROM plazos")).one()
    assert (fila.cantidad, fila.unidad) == (12, "meses")
    assert fila.tipo_dia == "NO_INFORMADO"


# --- Dependencias e idempotencia --------------------------------------------------


def test_las_normas_que_faltan_quedan_como_incidencia_abierta(conexion: Connection, curado) -> None:
    """La Ley 3706 define quién es beneficiario y no está en el corpus: mientras
    falte, la población queda declarada y no evaluable."""
    descripciones = (
        conexion.execute(
            text(
                "SELECT descripcion FROM incidencias_revision "
                " WHERE responsable_rol = 'curacion juridica' AND estado = 'ABIERTA'"
            )
        )
        .scalars()
        .all()
    )
    assert any("3706" in d for d in descripciones)
    assert any("Reglamentación" in d for d in descripciones)


def test_cargar_dos_veces_no_duplica_nada(conexion: Connection, norma) -> None:
    curador = CuradorDeBeneficios(conexion)
    primera = curador.cargar(LECTURA)
    segunda = curador.cargar(LECTURA)
    assert primera.reglas == segunda.reglas
    assert conexion.execute(text("SELECT count(*) FROM reglas")).scalar_one() == primera.reglas
    assert conexion.execute(text("SELECT count(*) FROM beneficios")).scalar_one() == 1
    assert conexion.execute(text("SELECT count(*) FROM beneficio_cuantias")).scalar_one() == 1


def test_cargar_todas_encuentra_las_lecturas_del_repositorio(conexion: Connection, norma) -> None:
    resultados = cargar_todas(conexion, raiz=RAIZ)
    assert len(resultados) >= 1
    cargadas = [r for r in resultados if r.beneficio_id is not None]
    assert cargadas, "ninguna lectura del repositorio se pudo cargar"


def test_una_lectura_sin_su_norma_no_impide_cargar_las_demas(conexion: Connection, norma) -> None:
    """La fixture trae la norma de una sola lectura. Las otras citan normas que
    no están y tienen que reportarse sin arrastrar al lote entero."""
    resultados = cargar_todas(conexion, raiz=RAIZ)

    bloqueadas = [r for r in resultados if r.beneficio_id is None]
    assert bloqueadas, "se esperaba al menos una lectura sin su norma en el corpus"
    for bloqueada in bloqueadas:
        assert any("no se cargó" in a for a in bloqueada.avisos)
    assert any(r.beneficio_id is not None for r in resultados)


def test_corregir_una_cita_no_deja_atras_la_regla_vieja(
    conexion: Connection, norma, tmp_path
) -> None:
    """Las reglas se reconocen por su texto literal.

    Corregir una cita —recortarla donde termina la causal, sacarle unos puntos
    suspensivos— crea una regla nueva y deja la anterior en la base. Nadie la
    vuelve a escribir en la lectura y nadie la borra: queda una regla candidata
    que ningún archivo curado reclama, citable como cualquier otra.
    """
    lectura = json.loads(LECTURA.read_text())
    curador = CuradorDeBeneficios(conexion)
    curador.cargar(LECTURA)

    corregida = json.loads(LECTURA.read_text())
    original = corregida["reglas"][0]["texto_literal"]
    corregida["reglas"][0]["texto_literal"] = original[: len(original) // 2].strip()
    ruta = tmp_path / "corregida.json"
    ruta.write_text(json.dumps(corregida, ensure_ascii=False), encoding="utf-8")

    resultado = curador.cargar(ruta)

    assert any("SUPERSEDED" in aviso for aviso in resultado.avisos)
    estados = dict(
        conexion.execute(
            text("SELECT estado_revision, count(*) FROM reglas GROUP BY estado_revision")
        ).all()
    )
    assert estados["SUPERSEDED"] == 1
    assert estados["CANDIDATE"] == len(lectura["reglas"])
    # No se borra: sigue explicando qué se afirmaba antes de corregir la cita.
    conservada = conexion.execute(
        text("SELECT texto_literal, alcance FROM reglas WHERE estado_revision = 'SUPERSEDED'")
    ).one()
    assert conservada.texto_literal == original
    assert "ya no contiene esta regla" in conservada.alcance
