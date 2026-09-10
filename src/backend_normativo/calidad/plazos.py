"""Un plazo que dice un número tiene que poder señalarlo en el texto que cita.

Es DQ02 aplicado a los plazos: «cero citas que solo comparten tema». Un plazo
curado declara una cantidad y una unidad —«30 días», «12 meses»— y cita el
fragmento del que salieron. Si ese fragmento no contiene el número, la cita
comparte tema con el plazo y no lo respalda, que es distinto.

El control tiene una trampa que hay que esquivar antes de acusar a nadie: los
textos legales escriben los números con letras tanto como con cifras —«antes de
los tres meses», «entre el tercer y cuarto mes»—, y buscar solo cifras da falsos
positivos sobre plazos que están bien. Por eso se buscan las dos formas.

Lo que este control no hace es interpretar. Que un fragmento contenga «30» no
prueba que ese 30 sean los días del plazo; prueba que el número está donde la
cita dice. Lo contrario —que no esté— sí es concluyente: nadie puede leer del
texto un número que el texto no tiene.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# Los números que aparecen en plazos legales, en las formas en que se escriben.
# No es una tabla de aritmética: es la lista de lo que hay que reconocer.
NUMEROS_EN_LETRAS: dict[int, tuple[str, ...]] = {
    1: ("un", "uno", "una", "primer", "primero", "primera"),
    2: ("dos", "segundo", "segunda"),
    3: ("tres", "tercer", "tercero", "tercera"),
    4: ("cuatro", "cuarto", "cuarta"),
    5: ("cinco", "quinto", "quinta"),
    6: ("seis", "sexto", "sexta"),
    7: ("siete", "séptimo", "septimo"),
    8: ("ocho", "octavo", "octava"),
    9: ("nueve", "noveno", "novena"),
    10: ("diez", "décimo", "decimo"),
    11: ("once",),
    12: ("doce",),
    13: ("trece",),
    14: ("catorce",),
    15: ("quince",),
    16: ("dieciséis", "dieciseis"),
    18: ("dieciocho",),
    20: ("veinte",),
    21: ("veintiún", "veintiuno", "veintiuna"),
    24: ("veinticuatro",),
    25: ("veinticinco",),
    30: ("treinta",),
    45: ("cuarenta y cinco",),
    60: ("sesenta",),
    90: ("noventa",),
    120: ("ciento veinte",),
    180: ("ciento ochenta",),
    365: ("trescientos sesenta y cinco",),
}

SOSTENIDO = "sostenido"
SIN_CANTIDAD = "sin cantidad"
NO_SOSTENIDO = "no sostenido"


def sostiene(cita: str, cantidad: int) -> bool:
    """¿El número está en el texto citado, en cifras o en letras?"""
    if re.search(rf"\b{cantidad}\b", cita):
        return True
    return any(
        re.search(rf"\b{re.escape(palabra)}\b", cita, re.IGNORECASE)
        for palabra in NUMEROS_EN_LETRAS.get(cantidad, ())
    )


@dataclass
class PlazoVerificado:
    tipo: str
    cantidad: int | None
    unidad: str | None
    evento_inicio: str | None
    dueño: str
    source_id: str
    cita: str

    @property
    def veredicto(self) -> str:
        if self.cantidad is None:
            # Un plazo que la norma expresa como evento —«al momento de la
            # inscripción»— no tiene número que comprobar, y está bien que no
            # lo tenga.
            return SIN_CANTIDAD
        return SOSTENIDO if sostiene(self.cita, self.cantidad) else NO_SOSTENIDO


@dataclass
class ReportePlazos:
    plazos: list[PlazoVerificado] = field(default_factory=list)

    @property
    def no_sostenidos(self) -> list[PlazoVerificado]:
        return [p for p in self.plazos if p.veredicto == NO_SOSTENIDO]

    @property
    def sin_cantidad(self) -> list[PlazoVerificado]:
        return [p for p in self.plazos if p.veredicto == SIN_CANTIDAD]


SQL = """
SELECT p.tipo, p.cantidad, p.unidad, p.evento_inicio,
       coalesce(b.codigo, n.tipo || ' ' || n.numero, t.codigo, 'sin dueño') AS dueno,
       d.source_id,
       regexp_replace(e.fragmento, '\\s+', ' ', 'g') AS cita
  FROM plazos p
  JOIN evidencias e ON e.id = p.evidencia_id
  JOIN documento_versiones dv ON dv.id = e.doc_version_id
  JOIN documentos d ON d.id = dv.documento_id
  LEFT JOIN beneficio_versiones bv ON bv.registro_version_id = p.beneficio_version_id
  LEFT JOIN beneficios b ON b.id = bv.beneficio_id
  LEFT JOIN norma_versiones nv ON nv.registro_version_id = p.norma_version_id
  LEFT JOIN normas n ON n.id = nv.norma_id
  LEFT JOIN tramite_versiones tv ON tv.registro_version_id = p.tramite_version_id
  LEFT JOIN tramites t ON t.id = tv.tramite_id
 ORDER BY 5, 1
"""


def construir(conexion: Connection) -> ReportePlazos:
    reporte = ReportePlazos()
    for fila in conexion.execute(text(SQL)).mappings():
        reporte.plazos.append(
            PlazoVerificado(
                tipo=fila["tipo"],
                cantidad=fila["cantidad"],
                unidad=fila["unidad"],
                evento_inicio=fila["evento_inicio"],
                dueño=fila["dueno"],
                source_id=fila["source_id"],
                cita=fila["cita"] or "",
            )
        )
    return reporte


def formatear(reporte: ReportePlazos) -> str:
    lineas = [
        "# Plazos contra su propia cita",
        "",
        "Un plazo que declara un número tiene que poder señalarlo en el texto que cita. "
        "Se buscan las dos formas en que los textos legales lo escriben: «30» y «treinta».",
        "",
        f"- Plazos cargados: {len(reporte.plazos)}",
        f"- Con la cantidad respaldada por su cita: "
        f"{len(reporte.plazos) - len(reporte.no_sostenidos) - len(reporte.sin_cantidad)}",
        f"- Expresados como evento, sin cantidad que comprobar: {len(reporte.sin_cantidad)}",
        f"- **Con una cantidad que su cita no contiene: {len(reporte.no_sostenidos)}**",
        "",
    ]
    if reporte.no_sostenidos:
        lineas += [
            "## Lo que la cita no dice",
            "",
            "El número declarado no está en el fragmento citado, ni en cifras ni en letras. "
            "O el plazo se leyó de otro lado, o el ancla apunta al párrafo equivocado.",
            "",
        ]
        for plazo in reporte.no_sostenidos:
            lineas.append(
                f"### {plazo.dueño} · {plazo.tipo} · {plazo.cantidad} {plazo.unidad or ''}"
            )
            lineas.append("")
            lineas.append(f"- Fuente: {plazo.source_id}")
            if plazo.evento_inicio:
                lineas.append(f"- Evento declarado: {plazo.evento_inicio}")
            lineas.append(f"- Cita: «{plazo.cita[:300]}»")
            lineas.append("")

    if reporte.sin_cantidad:
        lineas += [
            "## Plazos sin cantidad",
            "",
            "La norma los expresa como un evento y no como una duración. No hay número "
            "que comprobar, y forzarlos a uno sería inventarlo.",
            "",
        ]
        for plazo in reporte.sin_cantidad:
            lineas.append(
                f"- **{plazo.dueño}** · {plazo.tipo} — {plazo.evento_inicio or 'sin evento'}"
            )
        lineas.append("")

    lineas += [
        "## Qué no dice",
        "",
        "Que un plazo respaldado sea correcto. Que el fragmento contenga «30» prueba que el "
        "número está donde la cita dice, no que ese 30 sean los días de este plazo. Lo "
        "contrario sí es concluyente: nadie puede leer del texto un número que el texto no "
        "tiene.",
    ]
    return "\n".join(lineas) + "\n"
