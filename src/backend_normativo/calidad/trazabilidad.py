"""HU-035: trazabilidad entre los 80 casos de aceptación y las pruebas.

El paquete entrega los casos con `execution_status =
NOT_RUN_BACKEND_NOT_IMPLEMENTED` y pide ejecutarlos. Declarar "ejecutado" en una
planilla escrita a mano no prueba nada: este módulo lee el mapa, verifica contra
pytest que cada nodeid citado exista de verdad y —cuando se le pide— los corre.
Un nodeid que ya no existe (una prueba renombrada o borrada) hace fallar el
reporte en vez de dejar una cobertura declarada que nadie ejerce.

Un caso sin pruebas no se disimula: queda NO_EJECUTADO con el motivo concreto y
la capacidad que falta construir.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Literal

RUTA_MAPA = pathlib.Path("docs/calidad/trazabilidad_at.json")
RUTA_CASOS = pathlib.Path("docs/paquete/04_Calidad_y_Pruebas.json")

Estado = Literal["CUBIERTO", "CUBIERTO_PARCIAL", "NO_EJECUTADO"]


class MapaInconsistente(Exception):
    """El mapa no corresponde con los casos del paquete o cita pruebas que no
    existen."""


@dataclass
class CasoTrazado:
    id: str
    titulo: str
    historias: list[str]
    severidad: str
    estado: Estado
    pruebas: list[str] = field(default_factory=list)
    falta: str | None = None
    motivo: str | None = None
    resultado: str | None = None


@dataclass
class ReporteTrazabilidad:
    total: int = 0
    cubiertos: int = 0
    parciales: int = 0
    no_ejecutados: int = 0
    pruebas_citadas: int = 0
    ejecutado: bool = False
    fallidas: list[str] = field(default_factory=list)
    casos: list[CasoTrazado] = field(default_factory=list)

    @property
    def ejercidos(self) -> int:
        return self.cubiertos + self.parciales


def nodeids_disponibles(raiz: pathlib.Path | None = None) -> set[str]:
    """Los nodeids que pytest colecta hoy. Es la única fuente de verdad sobre
    qué pruebas existen."""
    salida = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        capture_output=True,
        text=True,
        cwd=raiz,
    )
    return {
        linea.split("[", 1)[0].strip()
        for linea in salida.stdout.splitlines()
        if "::" in linea and not linea.startswith(("ERROR", "FAILED"))
    }


def construir(
    *,
    ejecutar: bool = False,
    raiz: pathlib.Path | None = None,
) -> ReporteTrazabilidad:
    base = raiz or pathlib.Path.cwd()
    casos_paquete = {
        caso["id"]: caso for caso in json.loads((base / RUTA_CASOS).read_text())["test_cases"]
    }
    mapa = json.loads((base / RUTA_MAPA).read_text())["casos"]

    desconocidos = sorted(set(mapa) - set(casos_paquete))
    if desconocidos:
        raise MapaInconsistente(
            f"El mapa cita casos que el paquete no tiene: {desconocidos}. "
            "Un caso inventado no es cobertura."
        )

    disponibles = nodeids_disponibles(base)
    citadas: set[str] = set()
    for entrada in mapa.values():
        citadas.update(entrada.get("pruebas", ()))
    inexistentes = sorted(citadas - disponibles)
    if inexistentes:
        raise MapaInconsistente(
            "El mapa cita pruebas que pytest no colecta: "
            f"{inexistentes}. Se renombraron o se borraron; el mapa miente hasta corregirlo."
        )

    resultados: dict[str, str] = {}
    fallidas: list[str] = []
    if ejecutar and citadas:
        resultados, fallidas = _correr(sorted(citadas), base)

    reporte = ReporteTrazabilidad(total=len(casos_paquete), ejecutado=ejecutar)
    reporte.pruebas_citadas = len(citadas)
    reporte.fallidas = fallidas
    for identificador, caso in sorted(casos_paquete.items()):
        entrada = mapa.get(identificador, {})
        pruebas = list(entrada.get("pruebas", ()))
        if not pruebas:
            estado: Estado = "NO_EJECUTADO"
        elif entrada.get("falta"):
            estado = "CUBIERTO_PARCIAL"
        else:
            estado = "CUBIERTO"
        resultado = None
        if ejecutar and pruebas:
            propias = {resultados.get(n, "NO_REPORTADA") for n in pruebas}
            resultado = "PASSED" if propias == {"PASSED"} else ",".join(sorted(propias))
        reporte.casos.append(
            CasoTrazado(
                id=identificador,
                titulo=caso["title"],
                historias=list(caso["story_ids"]),
                severidad=caso["severity"],
                estado=estado,
                pruebas=pruebas,
                falta=entrada.get("falta"),
                motivo=entrada.get("motivo"),
                resultado=resultado,
            )
        )
        if estado == "CUBIERTO":
            reporte.cubiertos += 1
        elif estado == "CUBIERTO_PARCIAL":
            reporte.parciales += 1
        else:
            reporte.no_ejecutados += 1
    return reporte


def _correr(nodeids: list[str], base: pathlib.Path) -> tuple[dict[str, str], list[str]]:
    salida = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", *nodeids],
        capture_output=True,
        text=True,
        cwd=base,
    )
    resultados: dict[str, str] = dict.fromkeys(nodeids, "PASSED")
    fallidas: list[str] = []
    for linea in salida.stdout.splitlines():
        for marca, estado in (("FAILED ", "FAILED"), ("ERROR ", "ERROR")):
            if linea.startswith(marca):
                nodeid = linea[len(marca) :].split(" ", 1)[0].split("[", 1)[0]
                resultados[nodeid] = estado
                fallidas.append(nodeid)
    if salida.returncode != 0 and not fallidas:
        # pytest falló sin que se pueda atribuir a un caso: no se declara verde.
        fallidas.append(f"pytest terminó con código {salida.returncode}")
        resultados = dict.fromkeys(nodeids, "NO_CONCLUYENTE")
    return resultados, fallidas


def formatear(reporte: ReporteTrazabilidad) -> str:
    lineas = [
        "# Trazabilidad de los casos de aceptación",
        "",
        f"- Casos del paquete: **{reporte.total}**",
        f"- Cubiertos por pruebas que corren: **{reporte.cubiertos}**",
        f"- Cubiertos parcialmente: **{reporte.parciales}**",
        f"- No ejecutados: **{reporte.no_ejecutados}**",
        f"- Pruebas citadas: **{reporte.pruebas_citadas}** "
        f"({'ejecutadas' if reporte.ejecutado else 'verificadas por colección, no ejecutadas'})",
    ]
    if reporte.fallidas:
        lineas += ["", "> **Hay pruebas en rojo.** No se declara cobertura sobre ellas:"]
        lineas += [f"> - `{n}`" for n in reporte.fallidas]
    lineas += [
        "",
        "Cada caso remite a los nodeids que lo ejercen. `bn calidad trazabilidad` verifica",
        "que existan antes de contarlos; con `--ejecutar` además los corre.",
        "",
        "| Caso | Título | HU | Estado | Resultado | Pruebas / motivo |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for caso in reporte.casos:
        if caso.pruebas:
            detalle = "<br>".join(f"`{n.split('::')[-1]}`" for n in caso.pruebas)
            if caso.falta:
                detalle += f"<br>_Falta: {caso.falta}_"
        else:
            detalle = f"_{caso.motivo or 'Sin motivo declarado.'}_"
        lineas.append(
            f"| {caso.id} | {caso.titulo} | {', '.join(caso.historias)} | {caso.estado} "
            f"| {caso.resultado or '—'} | {detalle} |"
        )
    lineas += [
        "",
        "## Cómo leer los no ejecutados",
        "",
        "Un caso no ejecutado no es un caso que falle: es una capacidad que este alcance",
        "no construyó y que por eso no tiene nada que probar. El motivo dice cuál, para",
        "que la siguiente iteración sepa qué habilita cada caso.",
    ]
    return "\n".join(lineas)
