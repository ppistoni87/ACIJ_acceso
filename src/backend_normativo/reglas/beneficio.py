"""Dictamen preliminar sobre un beneficio.

Combina las reglas de un beneficio en un resultado explicable. El sistema no
otorga, no rechaza y no revoca: devuelve qué condiciones se cumplen, cuáles no,
cuáles quedan sin saber y qué salvaguardas hay que tener en cuenta antes de
presentar cualquier resultado negativo.

Reglas de la especificación que este módulo hace cumplir:

* `NO_CUMPLE_REGLA_EXPLICITA` exige haber evaluado **todas** las excepciones
  aplicables. Si una excepción no se pudo evaluar, no hay negativa: hay una
  pregunta pendiente o una revisión pendiente.
* Una regla que no está validada no se ejecuta. Si hacía falta para concluir, el
  resultado es `REQUIERE_REVISION`.
* Las salvaguardas nunca excluyen. Se informan siempre, sobre todo cuando el
  resultado es negativo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend_normativo.db.vocabularios import CategoriaRegla
from backend_normativo.reglas.evaluacion import (
    Evaluador,
    HechosDeclarados,
    ResultadoBeneficio,
    ResultadoCondicion,
    Ternario,
)

# Categorías que deciden si el beneficio puede corresponder hoy.
CATEGORIAS_DE_ACCESO = frozenset({CategoriaRegla.APLICABILIDAD, CategoriaRegla.EXCLUSION})

# Categorías que describen qué pasa después de otorgado. No se evalúan para
# decidir el acceso: detectar una causal potencial no es una decisión
# administrativa de revocación.
CATEGORIAS_POSTERIORES = frozenset(
    {
        CategoriaRegla.REVOCACION,
        CategoriaRegla.SUSPENSION,
        CategoriaRegla.CESE,
        CategoriaRegla.SUBSANACION,
        CategoriaRegla.REHABILITACION,
    }
)


@dataclass(frozen=True)
class ReglaEvaluable:
    id: uuid.UUID
    categoria: CategoriaRegla
    texto_literal: str
    ast: dict | None
    requiere_revision: bool
    alcance: str | None = None
    # Reglas de las que esta es excepción. Una excepción sin destino explícito
    # no se aplica sola: las precedencias no se resuelven por orden de carga.
    excepcion_de: tuple[uuid.UUID, ...] = ()

    @property
    def ejecutable(self) -> bool:
        return self.ast is not None and not self.requiere_revision


@dataclass
class CondicionEvaluada:
    regla_id: uuid.UUID
    categoria: CategoriaRegla
    texto_literal: str
    resultado: Ternario
    detalle: ResultadoCondicion | None
    alcance: str | None = None
    motivo_no_ejecutable: str | None = None


@dataclass
class Subsanacion:
    """Un bloqueo y las excepciones que la norma prevé para levantarlo.

    Existe porque el motor ya sabía esto y no lo decía. Cuando una condición
    bloquea, el resolvedor mira las excepciones para no informar una negativa
    sin haberlas evaluado —eso ya estaba—, pero el resultado sólo salía como una
    advertencia en prosa: «hay una excepción prevista que no se pudo evaluar».
    Quien pregunta no se enteraba de **cuál**, y esa excepción es, muchas veces,
    exactamente la vía que le queda.

    `excepciones` puede venir vacía. No significa que la norma no prevea
    ninguna: significa que en el corpus no hay ninguna registrada para esta
    condición, que es una afirmación sobre lo curado y no sobre la ley. Se
    distinguen porque la diferencia importa.
    """

    condicion: str
    categoria: CategoriaRegla
    excepciones: list[tuple[str, Ternario]] = field(default_factory=list)

    @property
    def alcanza_alguna(self) -> bool:
        return any(estado is Ternario.TRUE for _, estado in self.excepciones)

    @property
    def falta_saber(self) -> bool:
        return any(estado is Ternario.UNKNOWN for _, estado in self.excepciones)


@dataclass
class DictamenBeneficio:
    resultado: ResultadoBeneficio
    cumplidas: list[CondicionEvaluada] = field(default_factory=list)
    no_cumplidas: list[CondicionEvaluada] = field(default_factory=list)
    desconocidas: list[CondicionEvaluada] = field(default_factory=list)
    no_ejecutables: list[CondicionEvaluada] = field(default_factory=list)
    salvaguardas: list[CondicionEvaluada] = field(default_factory=list)
    posteriores: list[CondicionEvaluada] = field(default_factory=list)
    preguntas_faltantes: list[str] = field(default_factory=list)
    # Los bloqueos, con la salida que la norma prevé para cada uno. Se llena
    # siempre que haya un bloqueo, alcance o no la excepción: que no alcance
    # también es algo que la persona tiene derecho a leer.
    subsanaciones: list[Subsanacion] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def es_negativo(self) -> bool:
        return self.resultado is ResultadoBeneficio.NO_CUMPLE_REGLA_EXPLICITA


def evaluar_beneficio(
    reglas: list[ReglaEvaluable],
    hechos: HechosDeclarados,
    evaluador: Evaluador | None = None,
) -> DictamenBeneficio:
    evaluador = evaluador or Evaluador()
    dictamen = DictamenBeneficio(resultado=ResultadoBeneficio.POTENCIALMENTE_APLICABLE)

    evaluadas: dict[uuid.UUID, CondicionEvaluada] = {}
    for regla in reglas:
        condicion = _evaluar_regla(regla, hechos, evaluador)
        evaluadas[regla.id] = condicion
        _clasificar(dictamen, regla, condicion)

    _resolver(dictamen, reglas, evaluadas)
    return dictamen


def _evaluar_regla(
    regla: ReglaEvaluable, hechos: HechosDeclarados, evaluador: Evaluador
) -> CondicionEvaluada:
    if not regla.ejecutable:
        motivo = (
            "la regla todavía no tiene un árbol validado"
            if regla.ast is None
            else "la regla está marcada como pendiente de revisión"
        )
        return CondicionEvaluada(
            regla_id=regla.id,
            categoria=regla.categoria,
            texto_literal=regla.texto_literal,
            resultado=Ternario.UNKNOWN,
            detalle=None,
            alcance=regla.alcance,
            motivo_no_ejecutable=motivo,
        )
    detalle = evaluador.evaluar(regla.ast, hechos)
    return CondicionEvaluada(
        regla_id=regla.id,
        categoria=regla.categoria,
        texto_literal=regla.texto_literal,
        resultado=detalle.valor,
        detalle=detalle,
        alcance=regla.alcance,
    )


def _clasificar(
    dictamen: DictamenBeneficio, regla: ReglaEvaluable, condicion: CondicionEvaluada
) -> None:
    if regla.categoria is CategoriaRegla.SALVAGUARDA:
        # Una salvaguarda nunca excluye: se informa siempre.
        dictamen.salvaguardas.append(condicion)
        return
    if regla.categoria in CATEGORIAS_POSTERIORES:
        dictamen.posteriores.append(condicion)
        return

    if condicion.motivo_no_ejecutable:
        dictamen.no_ejecutables.append(condicion)
        return
    if condicion.resultado is Ternario.TRUE:
        dictamen.cumplidas.append(condicion)
    elif condicion.resultado is Ternario.FALSE:
        dictamen.no_cumplidas.append(condicion)
    else:
        dictamen.desconocidas.append(condicion)
        if condicion.detalle:
            dictamen.preguntas_faltantes.extend(condicion.detalle.faltantes())


def _resolver(
    dictamen: DictamenBeneficio,
    reglas: list[ReglaEvaluable],
    evaluadas: dict[uuid.UUID, CondicionEvaluada],
) -> None:
    por_id = {r.id: r for r in reglas}
    excepciones_por_regla: dict[uuid.UUID, list[ReglaEvaluable]] = {}
    for regla in reglas:
        if regla.categoria is CategoriaRegla.EXCEPCION:
            for objetivo in regla.excepcion_de:
                excepciones_por_regla.setdefault(objetivo, []).append(regla)

    # Condiciones que, tal como están, impiden el acceso.
    bloqueantes: list[CondicionEvaluada] = [
        c
        for c in dictamen.no_cumplidas
        if por_id[c.regla_id].categoria is CategoriaRegla.APLICABILIDAD
    ] + [c for c in dictamen.cumplidas if por_id[c.regla_id].categoria is CategoriaRegla.EXCLUSION]

    bloqueantes_firmes: list[CondicionEvaluada] = []
    for bloqueante in bloqueantes:
        excepciones = excepciones_por_regla.get(bloqueante.regla_id, [])
        # Antes de decidir nada: qué salida prevé la norma para este bloqueo.
        # Se registra siempre, con el estado de cada excepción, para que la
        # respuesta pueda decir cuál es la vía en vez de sólo que existe una.
        dictamen.subsanaciones.append(
            Subsanacion(
                condicion=bloqueante.texto_literal,
                categoria=por_id[bloqueante.regla_id].categoria,
                excepciones=[
                    (e.texto_literal, evaluadas[e.id].resultado)
                    for e in excepciones
                    if e.id in evaluadas
                ],
            )
        )
        estado = _estado_de_las_excepciones(excepciones, evaluadas)
        if estado is Ternario.TRUE:
            # Hay una excepción que se cumple: el bloqueo no aplica.
            dictamen.advertencias.append(
                f"Una excepción prevista alcanza a la condición «{bloqueante.texto_literal}»."
            )
            continue
        if estado is Ternario.UNKNOWN:
            # No se puede afirmar un resultado negativo sin haber evaluado todas
            # las excepciones aplicables.
            dictamen.desconocidas.append(bloqueante)
            dictamen.advertencias.append(
                "Hay una excepción prevista que no se pudo evaluar: no se informa un "
                "resultado negativo hasta resolverla."
            )
            continue
        bloqueantes_firmes.append(bloqueante)

    hay_excepciones_sin_ejecutar = any(
        c.motivo_no_ejecutable
        for c in dictamen.no_ejecutables
        if por_id[c.regla_id].categoria is CategoriaRegla.EXCEPCION
    )

    if dictamen.no_ejecutables:
        dictamen.resultado = ResultadoBeneficio.REQUIERE_REVISION
        dictamen.advertencias.append(
            f"{len(dictamen.no_ejecutables)} regla(s) todavía no están validadas para "
            "ejecutarse: el resultado necesita revisión de dominio."
        )
    elif dictamen.desconocidas:
        dictamen.resultado = ResultadoBeneficio.REQUIERE_DATOS
    elif bloqueantes_firmes and not hay_excepciones_sin_ejecutar:
        dictamen.resultado = ResultadoBeneficio.NO_CUMPLE_REGLA_EXPLICITA
    elif bloqueantes_firmes:
        dictamen.resultado = ResultadoBeneficio.REQUIERE_REVISION
    else:
        dictamen.resultado = ResultadoBeneficio.POTENCIALMENTE_APLICABLE

    if dictamen.es_negativo:
        dictamen.advertencias.append(
            "Este resultado dice que una condición explícita no se cumple con los datos "
            "declarados. No es una decisión del organismo ni una denegatoria."
        )

    # Sin duplicados y en orden de aparición: la primera pregunta que falta es
    # la que conviene hacer primero.
    vistas: set[str] = set()
    dictamen.preguntas_faltantes = [
        p for p in dictamen.preguntas_faltantes if not (p in vistas or vistas.add(p))
    ]


def _estado_de_las_excepciones(
    excepciones: list[ReglaEvaluable], evaluadas: dict[uuid.UUID, CondicionEvaluada]
) -> Ternario:
    """Si alguna excepción alcanza al bloqueo, si ninguna lo hace, o si no se sabe."""
    if not excepciones:
        return Ternario.FALSE
    valores = [evaluadas[e.id].resultado for e in excepciones if e.id in evaluadas]
    if Ternario.TRUE in valores:
        return Ternario.TRUE
    if Ternario.UNKNOWN in valores:
        return Ternario.UNKNOWN
    return Ternario.FALSE
