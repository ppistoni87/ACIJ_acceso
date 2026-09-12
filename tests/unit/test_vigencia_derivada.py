"""Un beneficio rige mientras rija la norma que lo crea.

No tiene vigencia propia: existe porque una norma lo crea. Las que lo
reglamentan o lo modifican cambian su contenido —requisitos, montos,
procedimiento— y no su existencia. La política deriva de ahí, y es conservadora
en los tres casos donde derivar sería inventar.
"""

from __future__ import annotations

import datetime as dt

from backend_normativo.db.vocabularios import EstadoLegal, ValidTipo
from backend_normativo.politicas.vigencia import dictaminar_derivada


def _creadora(**kwargs) -> dict:
    base = {
        "norma": "LEY 2917/2008",
        "valid_tipo": ValidTipo.ABIERTO_FIN.value,
        "valid_desde": dt.date(2009, 3, 14),
        "valid_hasta": None,
        "condicion": None,
    }
    base.update(kwargs)
    return base


def test_hereda_la_fecha_de_la_norma_que_lo_crea() -> None:
    dictamen = dictaminar_derivada([_creadora()])
    assert dictamen.automatica
    assert dictamen.valid_tipo is ValidTipo.ABIERTO_FIN
    assert dictamen.estado_legal is EstadoLegal.VIGENTE
    assert dictamen.valid_desde == dt.date(2009, 3, 14)


def test_sin_norma_creadora_no_se_deriva_nada() -> None:
    """Que no conste qué lo crea es un dato que falta, no una vigencia abierta."""
    dictamen = dictaminar_derivada([])
    assert not dictamen.automatica
    assert dictamen.valid_tipo is ValidTipo.DESCONOCIDO
    assert "No consta ninguna norma que cree" in dictamen.fundamento


def test_si_la_norma_no_tiene_vigencia_resuelta_el_beneficio_tampoco() -> None:
    """Derivar igual sería afirmar por transitividad lo que nadie determinó."""
    dictamen = dictaminar_derivada([_creadora(valid_tipo=ValidTipo.DESCONOCIDO.value)])
    assert not dictamen.automatica
    assert dictamen.valid_tipo is ValidTipo.DESCONOCIDO
    assert "LEY 2917/2008" in dictamen.fundamento


def test_una_norma_condicionada_condiciona_el_beneficio() -> None:
    """El caso del Decreto 690/06: rige hasta que se reglamente la ley que lo sucede."""
    dictamen = dictaminar_derivada(
        [
            _creadora(
                norma="DECRETO 690/2006",
                valid_tipo=ValidTipo.CONDICIONADO.value,
                valid_desde=dt.date(2006, 6, 29),
                condicion="Hasta que se publique la reglamentación de la Ley 6935/2025.",
            )
        ]
    )
    assert dictamen.valid_tipo is ValidTipo.CONDICIONADO
    assert dictamen.estado_legal is EstadoLegal.CONDICIONADA
    assert "reglamentación" in (dictamen.condicion or "")


def test_un_beneficio_no_sobrevive_a_la_norma_que_lo_crea() -> None:
    dictamen = dictaminar_derivada(
        [
            _creadora(
                valid_tipo=ValidTipo.CERRADO.value,
                valid_hasta=dt.date(2020, 12, 31),
            )
        ]
    )
    assert dictamen.valid_tipo is ValidTipo.CERRADO
    assert dictamen.estado_legal is EstadoLegal.NO_VIGENTE
    assert dictamen.valid_hasta == dt.date(2020, 12, 31)


def test_la_reglamentacion_posterior_no_corre_el_nacimiento_del_derecho() -> None:
    """Sólo se miran las creadoras: un decreto reglamentario de 2015 no hace
    nacer en 2015 un beneficio creado por una ley de 2009."""
    dictamen = dictaminar_derivada(
        [_creadora(), _creadora(norma="LEY 2917/2008 (segunda versión)")]
    )
    assert dictamen.valid_desde == dt.date(2009, 3, 14)
