"""HU-012 y HU-034: los siete campos evaluados y las métricas separadas."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.calidad.cobertura import formatear, medir
from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS
from tests.integracion.test_curacion import _documento_norma

pytestmark = pytest.mark.integracion


@pytest.fixture
def norma_con_texto(conexion: Connection):
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
        },
        unidades=[
            (
                "ARTICULO",
                "7",
                "ARTICULO 7º - La asignación por hijo consistirá en el pago de una suma "
                "mensual por cada hijo menor de 18 años que estuviere a cargo del "
                "beneficiario.",
                "DISPOSITIVO",
            ),
            (
                "ARTICULO",
                "8",
                "ARTICULO 8°- Los beneficiarios deberán acreditar residencia, salvo en "
                "caso de imposibilidad debidamente fundada, en cuyo caso podrán subsanar "
                "la documentación.",
                "DISPOSITIVO",
            ),
            (
                "ARTICULO",
                "26",
                "ARTICULO 26 - El beneficio caducará cuando se compruebe la falsedad de "
                "los datos declarados.",
                "DISPOSITIVO",
            ),
        ],
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    return EvaluadorDeCampos(conexion).evaluar()


def test_los_siete_campos_quedan_evaluados_por_version(
    conexion: Connection, norma_con_texto
) -> None:
    """DQ03: el 100% de los campos pedidos evaluados por norma."""
    campos = (
        conexion.execute(text("SELECT campo_solicitado FROM evaluaciones_completitud ORDER BY 1"))
        .scalars()
        .all()
    )
    assert sorted(campos) == sorted(CAMPOS_SOLICITADOS)
    assert len(campos) == 7


def test_ningun_campo_se_declara_informado_sin_revision(
    conexion: Connection, norma_con_texto
) -> None:
    """DQ04: un candidato de extracción no es un valor sustantivo validado."""
    estados = set(
        conexion.execute(text("SELECT DISTINCT estado FROM evaluaciones_completitud")).scalars()
    )
    assert "INFORMADO" not in estados
    assert estados <= {"PENDIENTE", "NO_INFORMADO_EN_FUENTES_REVISADAS"}


def test_los_candidatos_nacen_con_evidencia_localizable(
    conexion: Connection, norma_con_texto
) -> None:
    filas = conexion.execute(
        text(
            "SELECT a.campo_path, a.estado_revision, e.fragmento, e.unidad_id "
            "FROM afirmaciones a JOIN evidencias e ON e.id = a.evidencia_id"
        )
    ).all()
    assert filas
    assert all(f.estado_revision == "CANDIDATE" for f in filas)
    assert all(f.unidad_id is not None and f.fragmento.strip() for f in filas)


def test_la_deteccion_encuentra_los_campos_del_texto(conexion: Connection, norma_con_texto) -> None:
    """Cada artículo del fixture habla de un campo distinto."""
    campos = set(conexion.execute(text("SELECT DISTINCT campo_path FROM afirmaciones")).scalars())
    assert "beneficio_otorgado" in campos  # "consistirá en el pago de una suma"
    assert "criterios_revocacion" in campos  # "caducará"
    assert "no_descartar" in campos  # "salvo", "podrán subsanar"


def test_un_campo_sin_senales_dice_donde_se_busco(conexion: Connection, norma_con_texto) -> None:
    """`NO_INFORMADO_EN_FUENTES_REVISADAS` nunca significa `NO_EXISTE`."""
    fila = conexion.execute(
        text(
            "SELECT motivo, fuentes_revisadas FROM evaluaciones_completitud "
            "WHERE estado = 'NO_INFORMADO_EN_FUENTES_REVISADAS' LIMIT 1"
        )
    ).one()
    assert "no significa que no existan" in fila.motivo.lower()
    assert fila.fuentes_revisadas


def test_reevaluar_no_duplica_filas(conexion: Connection, norma_con_texto) -> None:
    antes = conexion.execute(text("SELECT count(*) FROM evaluaciones_completitud")).scalar_one()
    EvaluadorDeCampos(conexion).evaluar()
    assert (
        conexion.execute(text("SELECT count(*) FROM evaluaciones_completitud")).scalar_one()
        == antes
    )


# --- Métricas -----------------------------------------------------------------


def test_evaluacion_completa_no_es_base_completa(conexion: Connection, norma_con_texto) -> None:
    """Cien por ciento de campos evaluados con cero valor sustantivo es un
    resultado posible, y las métricas lo muestran en vez de promediarlo."""
    metricas = medir(conexion)
    assert metricas.campos.porcentaje_evaluado == 100.0
    assert metricas.campos.con_valor_sustantivo == 0
    assert metricas.campos.porcentaje_sustantivo == 0.0

    texto = formatear(metricas).replace("\n", " ")
    assert "no cuenta como valor sustantivo" in texto


def test_una_fuente_sin_capturar_no_cuenta_como_poblada(
    conexion: Connection, norma_con_texto
) -> None:
    metricas = medir(conexion)
    assert metricas.fuentes.total == 83
    assert metricas.fuentes.con_captura < metricas.fuentes.total
    assert metricas.fuentes.pendientes > 0
    assert metricas.fuentes.sin_url_conocida == 15


def test_sin_release_publicado_ninguna_capacidad_sirve_datos(
    conexion: Connection, norma_con_texto
) -> None:
    """Publicar es un acto explícito: mientras no ocurra, la API se abstiene."""
    metricas = medir(conexion)
    assert set(metricas.capacidades_publicables) == {
        "IDENTIFICACION",
        "DESCRIPCION_GENERAL",
        "REQUISITOS",
        "EVALUACION_PRELIMINAR",
        "MONTO",
        "PLAZO",
        "CANAL",
        "EXPLICACION_HISTORICA",
    }
    assert all(v == 0 for v in metricas.capacidades_publicables.values())
