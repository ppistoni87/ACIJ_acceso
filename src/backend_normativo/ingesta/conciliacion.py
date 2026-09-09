"""P-005: al cerrar una importación, que las cuentas cierren.

Cada importador cuenta lo suyo y lo imprime en pantalla. Eso alcanza mientras
alguien mira la corrida; no alcanza para saber, tres días después, si lo que
entró es lo que la fuente tenía. La cuenta se pierde con la terminal.

Acá se guarda, como un control de calidad de la corrida (`DQ11`), y se
comprueba una identidad simple: **cada fila leída terminó en algún lado**.

    leidas = nuevas + repetidas + rechazadas

`actualizadas` no entra en la suma: una fila que ya existía y cambió de
contenido es repetida *y* actualizada, y sumarla dos veces haría que la
identidad no cierre precisamente cuando el importador está funcionando bien.
Se declara aparte, como el subconjunto de repetidas que es.

`rechazadas` no se declara: se deriva. Cada importador dice cuántas filas leyó
y cuántas creó o reconoció; lo que falta es lo que se cayó. Declararlo llevó a
lo contrario de lo buscado en el primer intento: contadores como
`literales_sin_dato` o `sin_clave_canonica` parecían rechazos y en realidad
describen filas que sí entraron, así que la identidad daba números negativos
sobre importadores que funcionaban bien. Esos contadores viven ahora en
`observaciones`, que no participan de la suma.

Lo que sí se comprueba, entonces, es lo que importa: que ninguna fila caída
quede sin motivo declarado.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import Severidad

CONTROL = "DQ11"
VERSION_CONTROL = "conciliacion@1"


@dataclass
class Conciliacion:
    importador: str
    source_id: str = ""
    leidas: int = 0
    nuevas: int = 0
    repetidas: int = 0
    # Subconjunto de `repetidas`: ya estaban y cambiaron.
    actualizadas: int = 0
    # Por qué se cayó cada fila que se cayó.
    motivos: dict[str, int] = field(default_factory=dict)
    # Contadores que describen las filas que sí entraron: no son rechazos.
    observaciones: dict[str, int] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    @property
    def rechazadas(self) -> int:
        """Lo leído que no terminó ni como nuevo ni como ya conocido."""
        return max(0, self.leidas - self.nuevas - self.repetidas)

    @property
    def de_mas(self) -> int:
        """Más filas dadas de cuenta que leídas: contar mal en el otro sentido."""
        return max(0, self.nuevas + self.repetidas - self.leidas)

    @property
    def cuadra(self) -> bool:
        return self.de_mas == 0 and self.actualizadas <= self.repetidas

    @property
    def rechazos_con_causa(self) -> bool:
        """Una fila que se cayó sin motivo declarado es un error sin causa."""
        return sum(self.motivos.values()) >= self.rechazadas


def registrar(conexion: Connection, captura_id: uuid.UUID, conciliacion: Conciliacion) -> None:
    """Deja la conciliación pegada a la corrida que la produjo."""
    problemas = []
    if conciliacion.de_mas:
        problemas.append(
            f"{conciliacion.de_mas} fila(s) dadas de cuenta de más: se creó o se reconoció "
            "más de lo que se leyó"
        )
    if conciliacion.actualizadas > conciliacion.repetidas:
        problemas.append(
            f"{conciliacion.actualizadas} actualizadas sobre {conciliacion.repetidas} "
            "repetidas: actualizar algo que no estaba no es posible"
        )
    if not conciliacion.rechazos_con_causa:
        faltan = conciliacion.rechazadas - sum(conciliacion.motivos.values())
        problemas.append(f"{faltan} fila(s) se cayeron sin motivo declarado")

    conexion.execute(
        text(
            "INSERT INTO controles_calidad "
            "(corrida_id, control_id, version, resultado, severidad, observado, esperado) "
            "SELECT c.corrida_id, :control, :ver, :res, :sev, CAST(:obs AS jsonb), "
            "       CAST(:esp AS jsonb) "
            "  FROM capturas c WHERE c.id = :cap"
        ),
        {
            "control": CONTROL,
            "ver": VERSION_CONTROL,
            "res": "PASA" if not problemas else "FALLA",
            "sev": Severidad.INFO.value if not problemas else Severidad.HIGH.value,
            "obs": json.dumps(
                {
                    "importador": conciliacion.importador,
                    "source_id": conciliacion.source_id,
                    "leidas": conciliacion.leidas,
                    "nuevas": conciliacion.nuevas,
                    "repetidas": conciliacion.repetidas,
                    "actualizadas": conciliacion.actualizadas,
                    "rechazadas": conciliacion.rechazadas,
                    "motivos": conciliacion.motivos,
                    "observaciones": conciliacion.observaciones,
                    "avisos": conciliacion.avisos[:20],
                    "problemas": problemas,
                },
                ensure_ascii=False,
            ),
            "esp": json.dumps({"identidad": "leidas = nuevas + repetidas + rechazadas"}),
            "cap": captura_id,
        },
    )


@dataclass
class FilaConciliacion:
    source_id: str
    importador: str
    resultado: str
    ejecutado_en: str
    observado: dict


@dataclass
class ReporteConciliacion:
    filas: list[FilaConciliacion] = field(default_factory=list)
    corridas_abiertas: list[dict] = field(default_factory=list)

    @property
    def con_falla(self) -> list[FilaConciliacion]:
        return [f for f in self.filas if f.resultado == "FALLA"]

    @property
    def todo_cierra(self) -> bool:
        return not self.con_falla and not self.corridas_abiertas


def conciliar(conexion: Connection) -> ReporteConciliacion:
    """La última conciliación de cada importador, y lo que quedó a medias."""
    reporte = ReporteConciliacion()
    filas = conexion.execute(
        text(
            "SELECT DISTINCT ON (ci.source_id, cc.observado->>'importador') "
            "       ci.source_id, cc.observado, cc.resultado, cc.ejecutado_en "
            "  FROM controles_calidad cc "
            "  JOIN corridas_ingesta ci ON ci.id = cc.corrida_id "
            " WHERE cc.control_id = :control "
            " ORDER BY ci.source_id, cc.observado->>'importador', cc.ejecutado_en DESC"
        ),
        {"control": CONTROL},
    ).mappings()
    for fila in filas:
        observado = fila["observado"] or {}
        reporte.filas.append(
            FilaConciliacion(
                source_id=fila["source_id"],
                importador=observado.get("importador", "?"),
                resultado=fila["resultado"],
                ejecutado_en=fila["ejecutado_en"].isoformat(),
                observado=observado,
            )
        )

    # Una corrida con checkpoint es una que se cortó y espera reanudarse. No es
    # un error, pero dar por cerrada una carga que tiene una a medias sí lo es.
    reporte.corridas_abiertas = [
        dict(fila)
        for fila in conexion.execute(
            text(
                "SELECT source_id, id, inicio, "
                "       jsonb_array_length(coalesce(checkpoint->'urls_hechas', '[]'::jsonb)) "
                "         AS urls_hechas "
                "  FROM corridas_ingesta "
                " WHERE estado = 'EN_CURSO' AND checkpoint IS NOT NULL "
                " ORDER BY inicio"
            )
        ).mappings()
    ]
    return reporte


def formatear(reporte: ReporteConciliacion) -> str:
    lineas = [
        "# Conciliación de la ingesta",
        "",
        "Cada fila que un importador leyó terminó en algún lado: se creó, ya estaba, "
        "o se rechazó con motivo. La identidad que se comprueba es",
        "`leidas = nuevas + repetidas + rechazadas`; `actualizadas` es el subconjunto "
        "de repetidas que además cambió, y por eso no entra en la suma.",
        "",
    ]
    if not reporte.filas:
        lineas.append("No hay ninguna conciliación registrada todavía.")
        return "\n".join(lineas) + "\n"

    lineas += [
        "| Fuente | Importador | Leídas | Nuevas | Repetidas | Actualizadas "
        "| Rechazadas | Cierra |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for fila in sorted(reporte.filas, key=lambda f: (f.source_id, f.importador)):
        o = fila.observado
        lineas.append(
            f"| {fila.source_id} | {fila.importador} | {o.get('leidas', 0)} | "
            f"{o.get('nuevas', 0)} | {o.get('repetidas', 0)} | {o.get('actualizadas', 0)} | "
            f"{o.get('rechazadas', 0)} | {'sí' if fila.resultado == 'PASA' else '**NO**'} |"
        )

    fallas = reporte.con_falla
    if fallas:
        lineas += ["", "## Lo que no cierra", ""]
        for fila in fallas:
            o = fila.observado
            lineas.append(f"### {fila.source_id} · {fila.importador}")
            lineas.append("")
            for problema in o.get("problemas", []):
                lineas.append(f"- {problema}")
            lineas.append("")

    con_motivos = [
        f for f in reporte.filas if f.observado.get("motivos") and f.observado.get("rechazadas")
    ]
    if con_motivos:
        lineas += ["", "## Por qué se cayó lo que se cayó", ""]
        for fila in sorted(con_motivos, key=lambda f: f.source_id):
            motivos = ", ".join(
                f"{k}: {v}" for k, v in sorted(fila.observado["motivos"].items()) if v
            )
            lineas.append(f"- **{fila.source_id}** ({fila.importador}) — {motivos}")

    con_observaciones = [f for f in reporte.filas if f.observado.get("observaciones")]
    if con_observaciones:
        lineas += [
            "",
            "## Sobre las filas que sí entraron",
            "",
            "No son rechazos: describen algo de lo que entró y por eso no restan de la suma.",
            "",
        ]
        for fila in sorted(con_observaciones, key=lambda f: f.source_id):
            detalle = ", ".join(
                f"{k}: {v}" for k, v in sorted(fila.observado["observaciones"].items()) if v
            )
            if detalle:
                lineas.append(f"- **{fila.source_id}** ({fila.importador}) — {detalle}")

    if reporte.corridas_abiertas:
        lineas += [
            "",
            "## Corridas a medias",
            "",
            "Se cortaron y conservan su checkpoint. Reanudarlas continúa donde quedaron; "
            "dar la carga por cerrada sin hacerlo la deja incompleta.",
            "",
        ]
        for corrida in reporte.corridas_abiertas:
            lineas.append(
                f"- **{corrida['source_id']}** — {corrida['urls_hechas']} URL(s) hechas, "
                f"abierta el {corrida['inicio']:%Y-%m-%d %H:%M}"
            )

    lineas += [
        "",
        "## Qué no dice",
        "",
        "Que lo importado sea correcto. Dice que el importador dio cuenta de cada fila "
        "que leyó, no que haya interpretado bien lo que leyó.",
        "",
        "Tampoco dice que la fuente tuviera esas filas y no más: si la página paginó y el "
        "adaptador leyó una sola página, la conciliación cierra igual sobre lo que leyó. "
        "Eso lo cubre la historia de cada fuente, no esto.",
    ]
    return "\n".join(lineas) + "\n"
