"""HU-036: el circuito que faltaba para aprobar una regla curada.

Las reglas nacían candidatas y la evaluación no las usaba hasta que alguien con
competencia jurídica las aprobara. Faltaba la otra mitad: no había forma de
aprobarlas. `bn revision aprobar-campos` mueve afirmaciones, no reglas, así que
las reglas estaban condenadas a quedarse en CANDIDATE por ausencia de un
comando, no por falta de revisión.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.beneficios import CuradorDeBeneficios
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.curacion.revision_reglas import (
    RevisionInvalida,
    aprobar,
    aprobar_beneficio,
    expediente,
    formatear,
    marcar_en_revision,
    rechazar,
)

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]
LECTURA = RAIZ / "docs" / "curaduria" / "decreto-caba-75-2015.json"


@pytest.fixture
def curado(conexion: Connection):
    from tests.integracion.test_curacion import _documento_norma
    from tests.integracion.test_curacion_decreto_75 import UNIDADES

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
    return CuradorDeBeneficios(conexion).cargar(LECTURA)


def _reglas(conexion: Connection):
    return expediente(conexion, estado=None).reglas


def test_una_regla_se_puede_aprobar(conexion: Connection, curado) -> None:
    """Es la transición que convierte una lectura curada en derecho aplicable.

    Sin ella, curar bien no servía de nada: la evaluación seguía sin poder usar
    una sola regla.
    """
    regla = _reglas(conexion)[0]
    aprobar(conexion, regla.id, actor="dra. revisora", fundamento="Coincide con el artículo 1.")
    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla.id}
    ).scalar_one()
    assert estado == "APPROVED"


def test_aprobar_deja_quién_y_por_qué_en_la_bitácora(conexion: Connection, curado) -> None:
    """Una aprobación sin autor es una regla que nadie firmó."""
    regla = _reglas(conexion)[0]
    aprobar(conexion, regla.id, actor="dra. revisora", fundamento="Dice lo que dice la norma.")
    fila = conexion.execute(
        text(
            "SELECT actor, accion, motivo FROM auditoria_eventos "
            " WHERE objeto = 'reglas' AND objeto_id = :id"
        ),
        {"id": str(regla.id)},
    ).one()
    assert fila.actor == "dra. revisora"
    assert fila.accion == "APROBAR_REGLA"
    assert "Dice lo que dice la norma." in fila.motivo


def test_no_se_aprueba_sin_fundamento(conexion: Connection, curado) -> None:
    """Dentro de seis meses, un estado sin razón escrita no se distingue de un descuido."""
    regla = _reglas(conexion)[0]
    with pytest.raises(RevisionInvalida) as error:
        aprobar(conexion, regla.id, actor="alguien", fundamento="   ")
    assert "sin fundamento" in str(error.value)


def test_una_regla_ya_aprobada_no_se_vuelve_a_aprobar(conexion: Connection, curado) -> None:
    """Los estados no se saltean: cada uno dice quién la miró y hasta dónde."""
    regla = _reglas(conexion)[0]
    aprobar(conexion, regla.id, actor="dra. revisora", fundamento="Correcta.")
    with pytest.raises(RevisionInvalida) as error:
        aprobar(conexion, regla.id, actor="otra persona", fundamento="También me parece.")
    assert "APPROVED" in str(error.value)


def test_en_revision_no_habilita_nada(conexion: Connection, curado) -> None:
    """Separa «candidata» de «analizada y a la espera», y nada más.

    Es lo que hace que una revisión larga se pueda retomar sin volver a leer
    todo; no es una aprobación a medias.
    """
    regla = _reglas(conexion)[0]
    marcar_en_revision(
        conexion, regla.id, actor="analista", fundamento="Falta confirmar el alcance."
    )
    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla.id}
    ).scalar_one()
    assert estado == "IN_REVIEW"
    # Y desde ahí sí se puede aprobar: es un paso previo, no un desvío.
    aprobar(conexion, regla.id, actor="dra. revisora", fundamento="Alcance confirmado.")


def test_una_regla_se_puede_rechazar(conexion: Connection, curado) -> None:
    regla = _reglas(conexion)[0]
    rechazar(conexion, regla.id, actor="dra. revisora", fundamento="La norma no dice eso.")
    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla.id}
    ).scalar_one()
    assert estado == "REJECTED"


def test_aprobar_un_beneficio_firma_una_vez_y_audita_una_por_una(
    conexion: Connection, curado
) -> None:
    """Se revisa un beneficio entero porque sus reglas se aplican juntas.

    Obligar a una invocación por regla no hace la revisión más cuidadosa: hace
    que se haga con un bucle que nadie mira.
    """
    aprobadas = aprobar_beneficio(
        conexion,
        "CABA.BECAS-ESTUDIANTILES",
        actor="dra. revisora",
        fundamento="Revisado el decreto entero contra el texto publicado.",
    )
    assert len(aprobadas) == 3
    eventos = conexion.execute(
        text(
            "SELECT count(*) FROM auditoria_eventos "
            " WHERE objeto = 'reglas' AND accion = 'APROBAR_REGLA'"
        )
    ).scalar_one()
    assert eventos == 3


def test_aprobar_un_beneficio_que_no_existe_lo_dice(conexion: Connection, curado) -> None:
    with pytest.raises(RevisionInvalida) as error:
        aprobar_beneficio(conexion, "NO.EXISTE", actor="x", fundamento="y")
    assert "no tiene reglas candidatas" in str(error.value)


def test_el_expediente_dice_a_qué_unidad_mirar(conexion: Connection, curado) -> None:
    """Es lo primero que necesita quien revisa.

    La evidencia localiza una unidad; el `selector` lo escribe quien la crea y
    una evidencia reusada por otro curador puede no traerlo. Sin la unidad, hay
    que buscar el artículo a mano.
    """
    resultado = expediente(conexion)
    assert resultado.reglas
    assert resultado.sin_ubicar == 0
    assert all(r.ruta for r in resultado.reglas)


def test_el_expediente_dice_qué_hay_que_decidir_en_cada_una(conexion: Connection, curado) -> None:
    """«Revisar 154 reglas» no es una tarea; una lista de preguntas concretas sí."""
    texto = formatear(expediente(conexion))
    assert "Qué hay que decidir" in texto
    for regla in expediente(conexion).reglas:
        assert len(regla.que_hay_que_decidir) > 40


def test_las_reglas_se_agrupan_por_lo_que_hay_que_decidir(conexion: Connection, curado) -> None:
    """Ciento cincuenta y cuatro reglas no plantean ciento cincuenta y cuatro preguntas.

    Plantean unas pocas, repetidas. Sin agrupar, la revisión empieza de cero
    cada vez y no termina nunca.
    """
    resultado = expediente(conexion)
    clases = {r.clase for r in resultado.reglas}
    assert clases
    assert clases <= {
        "CONDICION_EJECUTABLE",
        "CONDICION_CON_UMBRAL_SIN_VALOR",
        "SIN_CONDICION_EJECUTABLE",
        "NO_ES_CONDICION_SOBRE_LA_PERSONA",
        "CONDICION_EN_CATEGORIA_QUE_NO_DECIDE_ACCESO",
    }


def test_una_regla_sin_condicion_y_de_prioridad_no_va_a_la_pila_de_acceso(
    conexion: Connection, curado
) -> None:
    """Una prioridad no dice si alguien accede: dice cómo se reparte un cupo.

    Aprobarla como condición de aplicabilidad la convertiría en un requisito
    que la norma no puso.
    """
    from backend_normativo.curacion.revision_reglas import ReglaEnRevision

    regla = ReglaEnRevision(
        id=next(r.id for r in expediente(conexion).reglas),
        beneficio="X",
        categoria="PRIORIDAD",
        estado="CANDIDATE",
        texto_literal="t",
        descripcion="d",
        tiene_condicion=False,
        requiere_revision=True,
        motivo_revision="m",
        norma="n",
        ruta="r",
    )
    assert regla.clase == "NO_ES_CONDICION_SOBRE_LA_PERSONA"


def test_un_umbral_sin_valor_es_una_pila_aparte(conexion: Connection, curado) -> None:
    """Es la pila de menor riesgo y conviene que se vea.

    Sin valor aprobado la evaluación devuelve desconocido, que es la respuesta
    correcta, y no «no calificás». Dejarlas candidatas no protege de nada.
    """
    from backend_normativo.curacion.revision_reglas import ReglaEnRevision

    regla = ReglaEnRevision(
        id=next(r.id for r in expediente(conexion).reglas),
        beneficio="X",
        categoria="APLICABILIDAD",
        estado="CANDIDATE",
        texto_literal="t",
        descripcion="d",
        tiene_condicion=True,
        requiere_revision=True,
        motivo_revision="m",
        norma="n",
        ruta="r",
        parametro_sin_valor=True,
    )
    assert regla.clase == "CONDICION_CON_UMBRAL_SIN_VALOR"


def test_el_expediente_dice_que_la_propuesta_no_es_una_aprobación(
    conexion: Connection, curado
) -> None:
    """La distinción es el punto entero del documento.

    Un expediente que se leyera como una aprobación haría exactamente el daño
    que el circuito de revisión existe para impedir.
    """
    texto = formatear(expediente(conexion))
    assert "Propuesta de disposición" in texto
    assert "no una aprobación" in texto
    assert "competencia jurídica" in texto
