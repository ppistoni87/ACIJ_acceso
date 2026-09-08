"""Política de resolución de vigencia.

Resolver la vigencia de una norma es una decisión jurídica. Esta política define
el único caso en que puede tomarse sin revisión caso por caso, y deja todo lo
demás en la cola de revisión.

**Identificador:** `vigencia-declarada@1`

**Campos que habilita:** `valid_tipo`, `valid_desde`, `valid_hasta` de una
versión de norma, y `estado_legal_validado`.

**Autoridad admitida:** el boletín oficial que publica la norma, cuando declara
explícitamente el estado en la ficha (`estado_legal_declarado`).

**Evidencia exigida:** la evidencia de la ficha que respalda ese estado, más la
ausencia de relaciones de derogación o abrogación aprobadas en sentido
contrario.

**Pruebas exigidas:** las de `tests/integracion/test_vigencia.py`.

Lo que esta política **no** habilita:

* Concluir que una norma sigue vigente porque nadie registró su derogación. La
  ausencia de una relación no es prueba de nada si la fuente no declara el
  estado.
* Cerrar la vigencia de una norma por la fecha de otra que la modifica
  parcialmente: una modificación no deroga la norma entera.
* Interpretar una nota editorial. La nota es del editor del boletín y puede
  decir a la vez que una norma fue abrogada y que su vigencia fue restablecida.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend_normativo.db.vocabularios import EstadoLegal, ValidTipo

VERSION = "vigencia-declarada@1"

# Relaciones que, aprobadas y en contra de la norma, cierran su vigencia.
RELACIONES_QUE_CIERRAN = ("DEROGA", "ABROGA")

# Relaciones que reabren una vigencia cerrada.
RELACIONES_QUE_REABREN = ("RESTABLECE",)


@dataclass(frozen=True)
class Dictamen:
    """Qué se puede afirmar de la vigencia de una versión, y con qué fundamento."""

    valid_tipo: ValidTipo
    estado_legal: EstadoLegal
    automatica: bool
    fundamento: str
    requiere_revision: bool = False


def dictaminar(
    *,
    estado_declarado: str | None,
    tiene_fecha_inicio: bool,
    cierres_aprobados: int,
    reaperturas_aprobadas: int,
    tiene_evidencia_de_estado: bool,
) -> Dictamen:
    """Aplica la política a los hechos observados de una versión."""

    if cierres_aprobados and reaperturas_aprobadas:
        # El caso de la Ley 24.714: abrogada y con la vigencia restablecida
        # después, con excepciones. No hay lectura automática posible.
        return Dictamen(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            automatica=False,
            requiere_revision=True,
            fundamento=(
                "La norma tiene relaciones aprobadas que cierran su vigencia y también "
                "relaciones que la restablecen. El alcance de la restitución puede tener "
                "excepciones y no se deduce del grafo: hace falta revisión de dominio."
            ),
        )

    if cierres_aprobados:
        return Dictamen(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            automatica=False,
            requiere_revision=True,
            fundamento=(
                "Hay una relación aprobada que deroga o abroga la norma. La fecha de cierre "
                "y su alcance salen del texto de la norma derogatoria, no de la existencia "
                "de la arista."
            ),
        )

    if not tiene_fecha_inicio:
        return Dictamen(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            automatica=False,
            requiere_revision=True,
            fundamento="No se conoce la fecha desde la que rige.",
        )

    if estado_declarado == EstadoLegal.VIGENTE.value and tiene_evidencia_de_estado:
        return Dictamen(
            valid_tipo=ValidTipo.ABIERTO_FIN,
            estado_legal=EstadoLegal.VIGENTE,
            automatica=True,
            fundamento=(
                f"La fuente oficial declara la norma vigente y la evidencia de esa "
                f"declaración está registrada. Política {VERSION}."
            ),
        )

    if estado_declarado == EstadoLegal.NO_VIGENTE.value:
        # Una etiqueta "no vigente" no basta para cerrar la vigencia: la norma
        # pudo incorporar disposiciones que siguen aplicándose a través de la
        # norma que modificó.
        return Dictamen(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            automatica=False,
            requiere_revision=True,
            fundamento=(
                "La fuente etiqueta la norma como no vigente, pero eso no dice desde cuándo "
                "ni si sus disposiciones siguen aplicándose a través de las normas que "
                "modificó. Hace falta revisión de dominio."
            ),
        )

    return Dictamen(
        valid_tipo=ValidTipo.DESCONOCIDO,
        estado_legal=EstadoLegal.NO_DETERMINADA,
        automatica=False,
        requiere_revision=True,
        fundamento=(
            "La fuente no declara el estado de vigencia. La ausencia de una derogación "
            "registrada no prueba que la norma siga rigiendo."
        ),
    )
