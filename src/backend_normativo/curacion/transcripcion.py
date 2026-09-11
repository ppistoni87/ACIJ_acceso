"""Registra decisiones que **ya tomó una persona**, una por una.

Este módulo no decide nada. Existe porque la firma jurídica ocurre fuera del
sistema —en una planilla, en un documento, en una reunión— y después hay que
dejarla registrada sin que el trayecto la deforme. La diferencia con aprobar
desde acá es toda: una cosa es transcribir lo que alguien resolvió y otra es
resolverlo. Lo primero deja en la bitácora el nombre de quien revisó; lo segundo
deja el de un proceso que no leyó la norma.

De ahí las tres cosas que este cargador se niega a hacer:

* **No completa un fundamento.** Una fila sin fundamento se rechaza. El
  fundamento es lo único que, dentro de seis meses, distingue una regla revisada
  de una aprobada de apuro, y no hay texto genérico que pueda sustituirlo.
* **No aplica nada si alguna fila está mal.** Se valida el archivo entero antes
  de escribir: media transcripción es peor que ninguna, porque nadie sabe dónde
  quedó.
* **No inventa el actor.** Va declarado y es el mismo para todo el archivo, que
  es como se firma un expediente: una persona se hace cargo de la revisión.
"""

from __future__ import annotations

import csv
import io
import json
import pathlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection

from backend_normativo.curacion.revision_reglas import (
    RevisionInvalida,
    aprobar,
    marcar_en_revision,
    rechazar,
)

# Lo que una fila puede decidir. Deliberadamente no incluye «publicar»: publicar
# es del corte y no de la revisión, y mezclarlos haría que firmar una regla la
# ponga a contestar sin pasar por el control del release.
DECISIONES = {
    "APROBAR": aprobar,
    "RECHAZAR": rechazar,
    "EN_REVISION": marcar_en_revision,
}


class ArchivoInvalido(Exception):
    """El archivo de decisiones no se puede aplicar tal como está."""


@dataclass
class Fila:
    numero: int
    regla_id: uuid.UUID
    decision: str
    fundamento: str


@dataclass
class ResultadoTranscripcion:
    actor: str
    aplicadas: int = 0
    por_decision: dict[str, int] = field(default_factory=dict)
    fuente: str = ""


def leer(contenido: str, *, nombre: str = "decisiones") -> list[Fila]:
    """Interpreta el archivo y se planta ante la primera fila que no cierra.

    Acepta CSV y JSON porque quien revisa exporta de donde puede, y pedirle que
    convierta el formato agrega un paso donde se pierden filas.
    """
    crudo = contenido.strip()
    if not crudo:
        raise ArchivoInvalido(f"{nombre} está vacío: no hay ninguna decisión que registrar.")

    if crudo[0] in "[{":
        try:
            datos = json.loads(crudo)
        except json.JSONDecodeError as error:
            raise ArchivoInvalido(f"{nombre} no es JSON válido: {error}") from error
        registros = datos if isinstance(datos, list) else datos.get("decisiones", [])
    else:
        registros = list(csv.DictReader(io.StringIO(crudo)))

    if not registros:
        raise ArchivoInvalido(f"{nombre} no trae ninguna fila de decisión.")

    filas: list[Fila] = []
    problemas: list[str] = []
    vistas: dict[uuid.UUID, int] = {}

    for numero, registro in enumerate(registros, start=1):
        if not isinstance(registro, dict):
            problemas.append(f"fila {numero}: no es un registro con columnas.")
            continue
        crudo_id = str(registro.get("regla") or registro.get("regla_id") or "").strip()
        decision = str(registro.get("decision") or registro.get("decisión") or "").strip().upper()
        fundamento = str(registro.get("fundamento") or "").strip()

        try:
            regla_id = uuid.UUID(crudo_id)
        except ValueError:
            problemas.append(f"fila {numero}: «{crudo_id}» no es un id de regla.")
            continue
        if decision not in DECISIONES:
            problemas.append(
                f"fila {numero}: decisión «{decision or '(vacía)'}» desconocida. "
                f"Las admitidas son {', '.join(sorted(DECISIONES))}."
            )
            continue
        if not fundamento:
            problemas.append(
                f"fila {numero} ({regla_id}): sin fundamento. Una decisión sin razón escrita "
                "no se puede auditar, y no hay texto genérico que la reemplace."
            )
            continue
        if regla_id in vistas:
            problemas.append(
                f"fila {numero}: la regla {regla_id} ya venía decidida en la fila "
                f"{vistas[regla_id]}. Dos decisiones sobre la misma regla no se resuelven solas."
            )
            continue
        vistas[regla_id] = numero
        filas.append(
            Fila(numero=numero, regla_id=regla_id, decision=decision, fundamento=fundamento)
        )

    if problemas:
        raise ArchivoInvalido(
            f"{nombre}: {len(problemas)} fila(s) no se pueden aplicar, así que no se aplica "
            "ninguna. Media transcripción deja el expediente en un estado que nadie sabe leer.\n"
            + "\n".join(f"  - {p}" for p in problemas)
        )
    return filas


def aplicar(
    conexion: Connection, filas: list[Fila], *, actor: str, fuente: str = ""
) -> ResultadoTranscripcion:
    """Registra cada decisión con su propio fundamento.

    Corre dentro de la transacción que le den: si una fila falla contra la base
    —una regla que ya no está candidata, un id que no existe— no queda media
    firma registrada.
    """
    if not actor.strip():
        raise ArchivoInvalido(
            "Falta el actor: la transcripción tiene que decir quién revisó, no quién la cargó."
        )

    resultado = ResultadoTranscripcion(actor=actor, fuente=fuente)
    for fila in filas:
        registrar = DECISIONES[fila.decision]
        try:
            registrar(conexion, fila.regla_id, actor=actor, fundamento=fila.fundamento)
        except RevisionInvalida as error:
            raise ArchivoInvalido(f"fila {fila.numero} ({fila.regla_id}): {error}") from error
        resultado.aplicadas += 1
        resultado.por_decision[fila.decision] = resultado.por_decision.get(fila.decision, 0) + 1
    return resultado


def formatear(resultado: ResultadoTranscripcion) -> str:
    partes = [f"{resultado.aplicadas} decisión(es) registradas a nombre de {resultado.actor}."]
    for decision, cuantas in sorted(resultado.por_decision.items()):
        partes.append(f"  {decision}: {cuantas}")
    if resultado.fuente:
        partes.append(f"  origen: {resultado.fuente}")
    return "\n".join(partes)


def plantilla(conexion: Connection, limite: int | None = None) -> str:
    """El CSV que hay que completar, con las reglas que esperan decisión.

    Se genera desde la base y no se escribe a mano para que ningún id se
    transcriba mal, y viene con la columna `fundamento` vacía a propósito: es lo
    que tiene que escribir quien revisa.
    """
    from sqlalchemy import text

    consulta = (
        "SELECT r.id, b.codigo, left(replace(r.texto_literal, chr(10), ' '), 120) AS literal "
        "  FROM reglas r "
        "  LEFT JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id "
        "  LEFT JOIN beneficios b ON b.id = bv.beneficio_id "
        " WHERE r.estado_revision IN ('CANDIDATE', 'IN_REVIEW') "
        " ORDER BY b.codigo NULLS LAST, r.id"
    )
    if limite:
        consulta += f" LIMIT {int(limite)}"

    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(["regla", "decision", "fundamento", "beneficio", "literal"])
    for fila in conexion.execute(text(consulta)).mappings():
        escritor.writerow([fila["id"], "", "", fila["codigo"] or "", fila["literal"] or ""])
    return salida.getvalue()


def desde_archivo(ruta: pathlib.Path) -> list[Fila]:
    return leer(ruta.read_text(encoding="utf-8"), nombre=str(ruta))
