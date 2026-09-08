"""HU-016: cómputo de plazos, con el calendario que se usó a la vista.

Un vencimiento mal calculado por un día es indistinguible de uno bien calculado
hasta que alguien pierde el plazo. Por eso este módulo devuelve, además de la
fecha, con qué calendario la sacó y qué días excluyó: una fecha sin eso no se
puede auditar ni discutir.

Dos decisiones que gobiernan todo lo demás:

* **Sin calendario no hay días hábiles.** Contar «hábiles» salteando sábados y
  domingos y nada más es contar mal en cualquier mes con un feriado. Si el plazo
  es en días hábiles y no hay calendario, el resultado es no determinado, con el
  calendario que hace falta.
* **Fuera de la cobertura del calendario tampoco.** Un calendario que llega
  hasta diciembre no sabe nada de enero. Si el cómputo se pasa del rango, el
  resultado es no determinado y dice hasta dónde llegaba: extrapolar feriados
  es inventarlos.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from backend_normativo.db.vocabularios import TipoDia

# Los días hábiles administrativos y judiciales comparten el fin de semana; lo
# que los distingue son sus ferias, que viven en el calendario.
FIN_DE_SEMANA = (5, 6)

UNIDADES_EN_DIAS = {"dia": 1, "dias": 1, "día": 1, "días": 1, "semana": 7, "semanas": 7}


class CalendarioInsuficiente(Exception):
    """El calendario no alcanza para responder lo que se preguntó."""


@dataclass(frozen=True)
class Excepcion:
    """Un día que el calendario declara distinto de lo que sería por regla."""

    fecha: dt.date
    es_habil: bool
    motivo: str | None = None


@dataclass
class Calendario:
    """Un calendario jurisdiccional con su cobertura declarada."""

    id: str
    jurisdiccion: str
    nombre: str
    version: str
    desde: dt.date
    hasta: dt.date
    excepciones: dict[dt.date, Excepcion] = field(default_factory=dict)

    def cubre(self, fecha: dt.date) -> bool:
        return self.desde <= fecha <= self.hasta

    def es_habil(self, fecha: dt.date) -> tuple[bool, Excepcion | None]:
        excepcion = self.excepciones.get(fecha)
        if excepcion is not None:
            return excepcion.es_habil, excepcion
        return fecha.weekday() not in FIN_DE_SEMANA, None


@dataclass
class ResultadoComputo:
    """Una fecha, o la razón por la que no hay fecha."""

    vencimiento: dt.date | None = None
    determinado: bool = False
    motivo: str = ""
    calendario_usado: str | None = None
    dias_contados: int = 0
    excluidos: list[Excepcion] = field(default_factory=list)
    requiere: str | None = None

    @property
    def fundamento(self) -> str:
        """Cómo se llegó a esa fecha, en una línea que se pueda mostrar."""
        if not self.determinado:
            return self.motivo
        if not self.excluidos:
            return (
                f"{self.dias_contados} día(s) desde el inicio, sin días excluidos. "
                f"Calendario: {self.calendario_usado or 'no hizo falta'}."
            )
        detalle = "; ".join(
            f"{e.fecha.isoformat()} ({e.motivo or 'no hábil'})" for e in self.excluidos[:5]
        )
        return (
            f"{self.dias_contados} día(s) hábiles desde el inicio. "
            f"Se excluyeron {len(self.excluidos)}: {detalle}. "
            f"Calendario: {self.calendario_usado}."
        )


def calcular_vencimiento(
    *,
    inicio: dt.date,
    cantidad: int,
    unidad: str,
    tipo_dia: TipoDia | str,
    calendario: Calendario | None = None,
    inclusivo_desde: bool = False,
) -> ResultadoComputo:
    """Vencimiento de un plazo relativo, o el motivo por el que no se puede dar.

    `inclusivo_desde` dice si el día del evento cuenta como el primero. La
    norma lo declara; suponerlo mueve el vencimiento un día, que es toda la
    diferencia entre presentar a tiempo y no.
    """
    tipo = TipoDia(tipo_dia) if not isinstance(tipo_dia, TipoDia) else tipo_dia
    factor = UNIDADES_EN_DIAS.get(unidad.strip().lower())
    if factor is None:
        return ResultadoComputo(
            motivo=(
                f"La unidad {unidad!r} no está en el contrato de cómputo "
                f"({', '.join(sorted(set(UNIDADES_EN_DIAS)))}). No se convierte por analogía."
            ),
            requiere="unidad_soportada",
        )
    dias = cantidad * factor

    if tipo is TipoDia.NO_INFORMADO:
        return ResultadoComputo(
            motivo=(
                "La norma no dice si el plazo corre en días corridos o hábiles. "
                "La diferencia es de días: no se elige una por defecto."
            ),
            requiere="tipo_de_dia_declarado",
        )

    if tipo is TipoDia.CORRIDO:
        vencimiento = inicio + dt.timedelta(days=dias - 1 if inclusivo_desde else dias)
        return ResultadoComputo(
            vencimiento=vencimiento,
            determinado=True,
            motivo="Días corridos: no interviene ningún calendario.",
            dias_contados=dias,
        )

    if calendario is None:
        return ResultadoComputo(
            motivo=(
                "El plazo corre en días hábiles y no hay calendario cargado para esa "
                "jurisdicción. Saltear solo sábados y domingos cuenta mal cualquier mes "
                "con un feriado."
            ),
            requiere="calendario_jurisdiccional",
        )

    return _contar_habiles(
        inicio=inicio,
        dias=dias,
        calendario=calendario,
        inclusivo_desde=inclusivo_desde,
    )


def _contar_habiles(
    *, inicio: dt.date, dias: int, calendario: Calendario, inclusivo_desde: bool
) -> ResultadoComputo:
    resultado = ResultadoComputo(calendario_usado=f"{calendario.nombre}@{calendario.version}")
    if not calendario.cubre(inicio):
        resultado.motivo = (
            f"El inicio ({inicio.isoformat()}) queda fuera de la cobertura del calendario "
            f"{calendario.nombre}@{calendario.version} "
            f"({calendario.desde.isoformat()} a {calendario.hasta.isoformat()})."
        )
        resultado.requiere = "calendario_que_cubra_el_periodo"
        return resultado

    contados = 0
    cursor = inicio
    if inclusivo_desde:
        habil, excepcion = calendario.es_habil(cursor)
        if habil:
            contados = 1
        elif excepcion is not None:
            resultado.excluidos.append(excepcion)

    while contados < dias:
        cursor += dt.timedelta(days=1)
        if not calendario.cubre(cursor):
            resultado.motivo = (
                f"El cómputo se pasa de la cobertura del calendario "
                f"{calendario.nombre}@{calendario.version}, que llega hasta "
                f"{calendario.hasta.isoformat()}. Extrapolar feriados es inventarlos: "
                f"faltan {dias - contados} día(s) hábiles por contar."
            )
            resultado.requiere = "calendario_que_cubra_el_periodo"
            resultado.dias_contados = contados
            return resultado
        habil, excepcion = calendario.es_habil(cursor)
        if habil:
            contados += 1
        else:
            resultado.excluidos.append(
                excepcion or Excepcion(fecha=cursor, es_habil=False, motivo="fin de semana")
            )

    resultado.vencimiento = cursor
    resultado.determinado = True
    resultado.dias_contados = contados
    resultado.motivo = "Días hábiles computados contra el calendario declarado."
    return resultado
