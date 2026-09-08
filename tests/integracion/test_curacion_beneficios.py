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

ARTICULOS = [
    (
        "ARTICULO",
        "1",
        "Artículo 1°.- Objeto - Se crea el Programa de apoyo para personas en situación de "
        "vulnerabilidad habitacional, mediante una prestación económica no retributiva, "
        "intransferible e inembargable.",
        "DISPOSITIVO",
    ),
    (
        "ARTICULO",
        "2",
        "Art. 2°.- Beneficiarios - Son beneficiarios las personas residentes en la Ciudad "
        "Autónoma de Buenos Aires en situación de calle efectiva o riesgo habitacional "
        "inminente, conforme el artículo 2 de la Ley 3706.",
        "DISPOSITIVO",
    ),
    (
        "ARTICULO",
        "3",
        "Art. 3°.- Prestación económica - Se abonará con frecuencia mensual, con una escala "
        "diferenciada según la composición del hogar.",
        "DISPOSITIVO",
    ),
    (
        "ARTICULO",
        "5",
        "Art. 5°.- Opción de pago único - El ejercicio de la opción resulta excluyente de "
        "toda otra suma por el término que fije la reglamentación.",
        "DISPOSITIVO",
    ),
    (
        "ARTICULO",
        "6",
        "Art. 6°.- Requisitos de acceso - a) Acreditar residencia con antigüedad mínima de "
        "dos (2) años. Quedan exceptuadas las víctimas de trata o violencia de género.",
        "DISPOSITIVO",
    ),
    (
        "ARTICULO",
        "7",
        "Art. 7°.- Duración - La prestación se otorgará por un plazo inicial de hasta DOCE "
        "(12) meses. La continuidad estará sujeta a las corresponsabilidades que defina la "
        "reglamentación.",
        "DISPOSITIVO",
    ),
    (
        "ARTICULO",
        "8",
        "Art. 8°.- Ingreso provisorio - En casos de urgencia social la Autoridad podrá "
        "disponer el ingreso provisorio aun sin la totalidad de la documentación.",
        "DISPOSITIVO",
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
    # Los requisitos de acceso salen del artículo 6, no de cualquier lado.
    requisitos = {f.ruta for f in filas if f.categoria in ("APLICABILIDAD", "EXCLUSION")}
    assert requisitos == {"articulo-6"}


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
