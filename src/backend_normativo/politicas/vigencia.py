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

import datetime as dt
from dataclasses import dataclass

from backend_normativo.db.vocabularios import EstadoLegal, ValidTipo

VERSION = "vigencia-declarada@2"

# Art. 5 del Código Civil y Comercial —y art. 2 del Código Civil, t.o. Ley
# 16.504, para las normas anteriores a 2015, de idéntico contenido en cuanto al
# plazo—: la norma rige a los ocho días corridos de su publicación oficial si no
# designa otro tiempo. El cómputo se hace acá, en un solo lugar, y no en la
# ingesta: la fecha en que una norma empieza a regir es una determinación, no un
# dato capturado.
#
# La norma que fija su propia entrada en vigencia es la excepción y esta política
# no la puede ver: por eso el automático se limita a los casos en que la fuente
# declara el estado con evidencia, y todo lo demás va a revisión.
DIAS_PARA_REGIR = 8

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
    # Cuándo empieza a regir, ya computado. `None` cuando no se puede afirmar.
    valid_desde: dt.date | None = None


def dictaminar(
    *,
    estado_declarado: str | None,
    fecha_publicacion: dt.date | None,
    cierres_aprobados: int,
    reaperturas_aprobadas: int,
    tiene_evidencia_de_estado: bool,
) -> Dictamen:
    """Aplica la política a los hechos observados de una versión.

    `fecha_publicacion` es la fecha de **publicación oficial** y ninguna otra.
    Antes acá llegaba un booleano y la fecha de inicio salía de la ingesta, que
    tomaba la publicación «o la sanción» y la escribía tal cual como comienzo de
    vigencia. Dos errores encadenados y silenciosos: la sanción no es la
    publicación —una norma sancionada y no publicada no rige— y la publicación
    tampoco es el comienzo, porque el plazo del art. 5 corre después.
    """

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

    if fecha_publicacion is None:
        return Dictamen(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            automatica=False,
            requiere_revision=True,
            fundamento=(
                "No se conoce la fecha de publicación oficial, así que no se puede computar "
                "desde cuándo rige. Una fecha de sanción o de firma no la reemplaza."
            ),
        )

    if estado_declarado == EstadoLegal.VIGENTE.value and tiene_evidencia_de_estado:
        desde = fecha_publicacion + dt.timedelta(days=DIAS_PARA_REGIR)
        return Dictamen(
            valid_tipo=ValidTipo.ABIERTO_FIN,
            estado_legal=EstadoLegal.VIGENTE,
            automatica=True,
            valid_desde=desde,
            fundamento=(
                f"La fuente oficial declara la norma vigente y la evidencia de esa "
                f"declaración está registrada. Rige desde el {desde.isoformat()}: "
                f"{DIAS_PARA_REGIR} días corridos después de su publicación del "
                f"{fecha_publicacion.isoformat()}, por el art. 5 del Código Civil y "
                f"Comercial. Política {VERSION}."
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


# --- Vigencia derivada de un beneficio ---------------------------------------
#
# **Identificador:** `vigencia-derivada-del-beneficio@1`
#
# Un beneficio no tiene vigencia propia: existe porque una norma lo crea, y
# mientras esa norma rija. Las que lo reglamentan o lo modifican cambian su
# contenido —requisitos, montos, procedimiento— y no su existencia. Por eso la
# derivación mira sólo las normas con rol CREA.
#
# Lo que esta política **no** habilita:
#
# * Resolver un beneficio cuya norma creadora no tiene vigencia resuelta. Sería
#   afirmar por transitividad lo que nadie determinó en el origen.
# * Resolver un beneficio sin ninguna norma con rol CREA. Si no consta qué lo
#   crea, no hay de dónde derivar; es un dato que falta, no una vigencia
#   abierta.
# * Ampliar la vigencia con la fecha de una norma que lo reglamenta. Un decreto
#   reglamentario posterior no corre el nacimiento del derecho.

VERSION_DERIVADA = "vigencia-derivada-del-beneficio@1"

ROL_CREADOR = "CREA"


@dataclass(frozen=True)
class DictamenDerivado:
    """Qué se puede afirmar de un beneficio a partir de las normas que lo crean."""

    valid_tipo: ValidTipo
    estado_legal: EstadoLegal
    valid_desde: object | None
    valid_hasta: object | None
    condicion: str | None
    automatica: bool
    fundamento: str


def dictaminar_derivada(creadoras: list[dict]) -> DictamenDerivado:
    """Deriva la vigencia de un beneficio de la de sus normas creadoras.

    Cada elemento de `creadoras` describe una norma con rol CREA:
    `valid_tipo`, `valid_desde`, `valid_hasta`, `condicion` y `norma`.
    """
    if not creadoras:
        return DictamenDerivado(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            valid_desde=None,
            valid_hasta=None,
            condicion=None,
            automatica=False,
            fundamento=(
                "No consta ninguna norma que cree este beneficio. Sin norma creadora no hay "
                "de dónde derivar la vigencia: es un dato que falta, no una vigencia abierta."
            ),
        )

    sin_resolver = [c for c in creadoras if c["valid_tipo"] == ValidTipo.DESCONOCIDO.value]
    if sin_resolver:
        nombres = ", ".join(str(c.get("norma", "?")) for c in sin_resolver)
        return DictamenDerivado(
            valid_tipo=ValidTipo.DESCONOCIDO,
            estado_legal=EstadoLegal.NO_DETERMINADA,
            valid_desde=None,
            valid_hasta=None,
            condicion=None,
            automatica=False,
            fundamento=(
                f"La vigencia de la norma que lo crea no está resuelta ({nombres}). Derivarla "
                "igual sería afirmar por transitividad lo que nadie determinó en el origen."
            ),
        )

    condicionadas = [c for c in creadoras if c["valid_tipo"] == ValidTipo.CONDICIONADO.value]
    if condicionadas:
        primera = condicionadas[0]
        return DictamenDerivado(
            valid_tipo=ValidTipo.CONDICIONADO,
            estado_legal=EstadoLegal.CONDICIONADA,
            valid_desde=min(c["valid_desde"] for c in creadoras if c["valid_desde"]),
            valid_hasta=None,
            condicion=primera.get("condicion"),
            automatica=True,
            fundamento=(
                f"La norma que lo crea ({primera.get('norma', '?')}) tiene vigencia "
                f"condicionada, así que el beneficio hereda esa condición. Política "
                f"{VERSION_DERIVADA}."
            ),
        )

    cerradas = [c for c in creadoras if c["valid_tipo"] == ValidTipo.CERRADO.value]
    desde = min(c["valid_desde"] for c in creadoras if c["valid_desde"])
    if cerradas:
        return DictamenDerivado(
            valid_tipo=ValidTipo.CERRADO,
            estado_legal=EstadoLegal.NO_VIGENTE,
            valid_desde=desde,
            valid_hasta=max(c["valid_hasta"] for c in cerradas if c["valid_hasta"]),
            condicion=None,
            automatica=True,
            fundamento=(
                f"La norma que lo crea tiene vigencia cerrada; el beneficio no puede "
                f"sobrevivirla. Política {VERSION_DERIVADA}."
            ),
        )

    nombres = ", ".join(str(c.get("norma", "?")) for c in creadoras)
    return DictamenDerivado(
        valid_tipo=ValidTipo.ABIERTO_FIN,
        estado_legal=EstadoLegal.VIGENTE,
        valid_desde=desde,
        valid_hasta=None,
        condicion=None,
        automatica=True,
        fundamento=(
            f"Rige desde que rige la norma que lo crea ({nombres}), de forma abierta y sin "
            f"cierre registrado. Las normas que lo reglamentan o lo modifican cambian su "
            f"contenido, no su existencia. Política {VERSION_DERIVADA}."
        ),
    )
