"""HU-026: el ciclo periódico, de la planificación al evento.

Monitorear no es correr un comando: es que cada fuente se vuelva a mirar cuando
le toca, que lo capturado se extraiga, que el cambio se compare contra la
versión anterior y que el impacto llegue a la cola de eventos. Cada uno de esos
pasos ya existía suelto; lo que faltaba era el ciclo que los encadena y que dice
qué pasó en cada corrida.

Lo que este módulo **no** hace es dispararse solo. Eso lo hace un planificador
del sistema operativo o del orquestador, y es una decisión de despliegue: el
ciclo se deja listo para que algo lo llame cada hora, y el reporte de cada
corrida dice si hubo novedades o si simplemente no le tocaba a nadie.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import Connection

from backend_normativo.ingesta.planificador import fuentes_pendientes


@dataclass
class PasoDelCiclo:
    nombre: str
    detalle: str = ""
    fuentes: list[str] = field(default_factory=list)
    cuantos: int = 0


@dataclass
class ResultadoCiclo:
    ahora: dt.datetime | None = None
    pendientes: list[str] = field(default_factory=list)
    pasos: list[PasoDelCiclo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def hubo_trabajo(self) -> bool:
        return bool(self.pendientes)

    def paso(self, nombre: str) -> PasoDelCiclo | None:
        return next((p for p in self.pasos if p.nombre == nombre), None)


def correr(
    conexion: Connection,
    *,
    ahora: dt.datetime | None = None,
    limite: int | None = None,
    revalidar=None,
) -> ResultadoCiclo:
    """Una vuelta del ciclo: ver a quién le toca y revalidarlo.

    La revalidación se recibe como función para que el ciclo se pueda correr en
    seco —viendo a quién le toca sin salir a la red— y para que la prueba no
    dependa de que un sitio esté arriba.
    """
    ahora = ahora or dt.datetime.now(dt.UTC)
    resultado = ResultadoCiclo(ahora=ahora)

    pendientes = fuentes_pendientes(conexion, ahora=ahora, limite=limite)
    resultado.pendientes = [f.source_id for f in pendientes]
    resultado.pasos.append(
        PasoDelCiclo(
            nombre="planificacion",
            detalle=(
                f"{len(pendientes)} fuente(s) quedaron fuera de su frecuencia y vuelven a la "
                "cola. Las que la política no habilita a automatizar y las que no tienen URL "
                "no entran: su brecha se resuelve por descubrimiento o carga manual."
            ),
            fuentes=resultado.pendientes,
            cuantos=len(pendientes),
        )
    )
    if not pendientes:
        resultado.avisos.append(
            "No le toca a ninguna fuente todavía. Una corrida sin trabajo no es una corrida "
            "fallida: es la frecuencia haciendo lo suyo."
        )
        return resultado

    if revalidar is None:
        resultado.avisos.append("Corrida en seco: se planificó y no se salió a la red.")
        return resultado

    conteos = revalidar(resultado.pendientes) or {}
    for nombre, detalle in (
        ("revalidacion", "Se volvió a pedir cada fuente vencida y se guardaron los originales."),
        ("versiones", "Las capturas con texto distinto produjeron una versión documental nueva."),
        (
            "cambios",
            "Cada versión nueva se comparó con la anterior. Un desplazamiento no es un cambio: "
            "sólo lo sustantivo cuenta.",
        ),
        ("impacto", "Las normas que citan lo que cambió también se marcan para revisar."),
        ("eventos", "Lo sustantivo llegó a la cola de eventos, que es de donde se entrega."),
        ("bloqueadas", "Fuentes que respondieron con un acceso limitado y quedaron pausadas."),
    ):
        clave = {
            "revalidacion": "revisadas",
            "versiones": "versiones",
            "cambios": "con_cambios",
            "impacto": "impactadas",
            "eventos": "eventos",
            "bloqueadas": "bloqueadas",
        }[nombre]
        resultado.pasos.append(
            PasoDelCiclo(nombre=nombre, detalle=detalle, cuantos=int(conteos.get(clave, 0)))
        )
    return resultado


def formatear(resultado: ResultadoCiclo) -> str:
    lineas = [
        "# Ciclo de monitoreo",
        "",
        f"- Corrida: `{resultado.ahora.isoformat() if resultado.ahora else '—'}`",
        f"- Fuentes que vuelven a la cola: **{len(resultado.pendientes)}**",
        "",
        "| Paso | Cantidad | Detalle |",
        "| --- | ---: | --- |",
    ]
    lineas += [f"| {p.nombre} | {p.cuantos} | {p.detalle} |" for p in resultado.pasos]
    if resultado.pendientes:
        lineas += [
            "",
            "## A quién le tocaba",
            "",
            ", ".join(f"`{s}`" for s in resultado.pendientes),
        ]
    for aviso in resultado.avisos:
        lineas += ["", aviso]
    lineas += [
        "",
        "## Qué falta para que esto sea periódico de verdad",
        "",
        "El ciclo está completo y se puede correr entero con un comando. Lo que no hace es",
        "dispararse solo: eso lo tiene que hacer un planificador del sistema o del",
        "orquestador llamando a `bn monitoreo ciclo` cada hora. Es una decisión de",
        "despliegue, no código que falte, y hasta que exista el corpus se actualiza cuando",
        "alguien corre el comando.",
    ]
    return "\n".join(lineas)
