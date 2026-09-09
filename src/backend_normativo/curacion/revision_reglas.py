"""HU-036: el circuito de revisión de las reglas curadas.

Las reglas nacen candidatas y la evaluación no las usa hasta que alguien con
competencia jurídica las aprueba. Faltaba la otra mitad: no había forma de
aprobarlas. `bn revision aprobar-campos` mueve afirmaciones, no reglas, así que
las ciento cincuenta y cuatro reglas curadas estaban condenadas a quedarse en
CANDIDATE por ausencia de un comando, no por falta de revisión.

Acá está el circuito, y está pensado para que revisar sea posible y no
declarativo:

- `expediente` arma, regla por regla, lo que hay que decidir: el texto literal,
  qué afirma la lectura, si tiene condición ejecutable, y la pregunta concreta
  que la curaduría dejó escrita. Sin eso, «revisar 154 reglas» es una tarea sin
  forma que nadie empieza.
- `marcar_en_revision` mueve de CANDIDATE a IN_REVIEW. No aprueba nada y no
  sirve nada: dice que la regla ya fue mirada y espera decisión.
- `aprobar` y `rechazar` exigen actor y fundamento, y quedan en la bitácora. Es
  lo único que convierte una lectura curada en derecho aplicable, y por eso es
  lo único que este módulo no hace solo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import EstadoRevision


class RevisionInvalida(Exception):
    """La transición pedida no corresponde al estado en que está la regla."""


@dataclass
class ReglaEnRevision:
    id: uuid.UUID
    beneficio: str
    categoria: str
    estado: str
    texto_literal: str
    descripcion: str
    tiene_condicion: bool
    requiere_revision: bool
    motivo_revision: str
    norma: str
    ruta: str

    @property
    def que_hay_que_decidir(self) -> str:
        """La pregunta concreta, no la etiqueta.

        Una regla sin condición ejecutable y una con condición esperando
        confirmación no plantean lo mismo, y mandarlas a la misma pila hace que
        la segunda se apruebe sin mirar y la primera se apruebe sin poder.
        """
        if self.motivo_revision:
            return self.motivo_revision
        if not self.tiene_condicion:
            return (
                "No tiene condición ejecutable ni motivo declarado. Antes de aprobarla hay que "
                "decidir si la condición se puede escribir o si la regla es informativa."
            )
        return (
            "Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita "
            "para la evaluación: hay que confirmar que la condición dice lo que dice la norma."
        )


@dataclass
class ResultadoRevision:
    reglas: list[ReglaEnRevision] = field(default_factory=list)
    por_estado: dict[str, int] = field(default_factory=dict)

    @property
    def sin_condicion(self) -> int:
        return sum(1 for r in self.reglas if not r.tiene_condicion)

    @property
    def sin_ubicar(self) -> int:
        """Reglas cuya evidencia no dice a qué unidad del texto mirar."""
        return sum(1 for r in self.reglas if not r.ruta)

    @property
    def por_categoria(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for regla in self.reglas:
            cuenta[regla.categoria] = cuenta.get(regla.categoria, 0) + 1
        return dict(sorted(cuenta.items()))


CONSULTA = """
SELECT r.id, b.codigo AS beneficio, r.categoria, r.estado_revision AS estado,
       r.texto_literal, r.descripcion, (r.ast IS NOT NULL) AS tiene_condicion,
       r.requiere_revision, coalesce(r.alcance, '') AS motivo_revision,
       coalesce(n.tipo || ' ' || n.numero || '/' || n.anio::text, '—') AS norma,
       coalesce(u.ruta, e.selector, '') AS ruta
  FROM reglas r
  JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id
  JOIN beneficios b ON b.id = bv.beneficio_id
  LEFT JOIN evidencias e ON e.id = r.evidencia_id
  -- La unidad es lo que localiza de verdad. El `selector` lo escribe quien crea
  -- la evidencia y una reusada por otro curador puede no traerlo: dos de cada
  -- tres reglas quedaban sin decir a qué artículo mirar, que es lo primero que
  -- necesita quien revisa.
  LEFT JOIN unidades_documentales u ON u.id = e.unidad_id
  LEFT JOIN documento_versiones dv ON dv.id = e.doc_version_id
  LEFT JOIN norma_versiones nv ON nv.doc_version_id = dv.id
  LEFT JOIN normas n ON n.id = nv.norma_id
 WHERE (CAST(:estado AS text) IS NULL OR r.estado_revision = :estado)
   AND (CAST(:beneficio AS text) IS NULL OR b.codigo = :beneficio)
 ORDER BY b.codigo, r.categoria, r.texto_literal
"""


def expediente(
    conexion: Connection,
    *,
    estado: str | None = EstadoRevision.CANDIDATE.value,
    beneficio: str | None = None,
) -> ResultadoRevision:
    """Lo que hay que decidir, regla por regla."""
    resultado = ResultadoRevision()
    for fila in conexion.execute(
        text(CONSULTA), {"estado": estado, "beneficio": beneficio}
    ).mappings():
        resultado.reglas.append(
            ReglaEnRevision(
                id=fila["id"],
                beneficio=fila["beneficio"],
                categoria=fila["categoria"],
                estado=fila["estado"],
                texto_literal=fila["texto_literal"],
                descripcion=fila["descripcion"] or "",
                tiene_condicion=bool(fila["tiene_condicion"]),
                requiere_revision=bool(fila["requiere_revision"]),
                motivo_revision=fila["motivo_revision"],
                norma=fila["norma"],
                ruta=fila["ruta"],
            )
        )
    for fila in conexion.execute(text("SELECT estado_revision, count(*) FROM reglas GROUP BY 1")):
        resultado.por_estado[fila[0]] = fila[1]
    return resultado


def _mover(
    conexion: Connection,
    regla_id: uuid.UUID,
    *,
    desde: tuple[str, ...],
    hasta: str,
    actor: str,
    fundamento: str,
    accion: str,
) -> None:
    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla_id}
    ).scalar_one_or_none()
    if estado is None:
        raise RevisionInvalida(f"No hay ninguna regla con id {regla_id}.")
    if estado not in desde:
        raise RevisionInvalida(
            f"La regla está en {estado} y esta transición sale de {' o '.join(desde)}. "
            "Los estados no se saltean: cada uno dice quién la miró y hasta dónde."
        )
    conexion.execute(
        text("UPDATE reglas SET estado_revision = :e WHERE id = :id"),
        {"e": hasta, "id": regla_id},
    )
    conexion.execute(
        text(
            "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
            "VALUES (:actor, :accion, 'reglas', :id, :motivo)"
        ),
        {"actor": actor, "accion": accion, "id": str(regla_id), "motivo": fundamento},
    )


def marcar_en_revision(
    conexion: Connection, regla_id: uuid.UUID, *, actor: str, fundamento: str
) -> None:
    """Deja constancia de que la regla ya fue mirada y espera decisión.

    No aprueba ni sirve nada. Existe porque «candidata» y «analizada y a la
    espera» son cosas distintas, y meterlas en la misma pila hace que una
    revisión de ciento cincuenta reglas no tenga por dónde empezar la segunda
    vez.
    """
    _mover(
        conexion,
        regla_id,
        desde=(EstadoRevision.CANDIDATE.value,),
        hasta=EstadoRevision.IN_REVIEW.value,
        actor=actor,
        fundamento=fundamento,
        accion="REGLA_EN_REVISION",
    )


def aprobar(conexion: Connection, regla_id: uuid.UUID, *, actor: str, fundamento: str) -> None:
    """Convierte una lectura curada en regla aplicable.

    Es la única transición que habilita a la evaluación a usarla, así que exige
    quién y por qué, y las dos cosas quedan en la bitácora. Que lo haya escrito
    una curaduría no lo vuelve derecho aplicable; que lo apruebe alguien con
    competencia, sí.
    """
    if not fundamento.strip():
        raise RevisionInvalida(
            "Aprobar una regla sin fundamento deja una decisión sin razón escrita. Dentro de "
            "seis meses nadie puede saber si se revisó o se aprobó de apuro."
        )
    _mover(
        conexion,
        regla_id,
        desde=(EstadoRevision.CANDIDATE.value, EstadoRevision.IN_REVIEW.value),
        hasta=EstadoRevision.APPROVED.value,
        actor=actor,
        fundamento=fundamento,
        accion="APROBAR_REGLA",
    )


def rechazar(conexion: Connection, regla_id: uuid.UUID, *, actor: str, fundamento: str) -> None:
    """Descarta una regla: la lectura afirmaba algo que la norma no dice."""
    if not fundamento.strip():
        raise RevisionInvalida("Rechazar una regla sin fundamento no explica qué estaba mal.")
    _mover(
        conexion,
        regla_id,
        desde=(EstadoRevision.CANDIDATE.value, EstadoRevision.IN_REVIEW.value),
        hasta=EstadoRevision.REJECTED.value,
        actor=actor,
        fundamento=fundamento,
        accion="RECHAZAR_REGLA",
    )


def aprobar_beneficio(
    conexion: Connection, codigo: str, *, actor: str, fundamento: str
) -> list[uuid.UUID]:
    """Aprueba de una vez las reglas candidatas de un beneficio.

    Una persona revisa un beneficio entero —sus reglas se leen juntas porque se
    aplican juntas— y firma una vez. Obligarla a ciento cincuenta invocaciones
    no hace la revisión más cuidadosa: hace que no se haga, o que se haga con un
    bucle que nadie mira.

    Cada regla igual deja su propio evento en la bitácora, con el mismo actor y
    el mismo fundamento: lo que se firma una vez tiene que poder auditarse una
    por una.
    """
    if not fundamento.strip():
        raise RevisionInvalida(
            "Aprobar sin fundamento deja una decisión sin razón escrita. Dentro de seis meses "
            "nadie puede saber si se revisó o se aprobó de apuro."
        )
    reglas = (
        conexion.execute(
            text(
                "SELECT r.id FROM reglas r "
                "  JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id "
                "  JOIN beneficios b ON b.id = bv.beneficio_id "
                " WHERE b.codigo = :c AND r.estado_revision IN ('CANDIDATE', 'IN_REVIEW')"
            ),
            {"c": codigo},
        )
        .scalars()
        .all()
    )
    if not reglas:
        raise RevisionInvalida(
            f"El beneficio {codigo!r} no tiene reglas candidatas ni en revisión. O el código "
            "está mal escrito, o ya se aprobaron: `bn revision reglas --estado todos` lo dice."
        )
    for regla_id in reglas:
        aprobar(conexion, regla_id, actor=actor, fundamento=fundamento)
    return list(reglas)


def formatear(resultado: ResultadoRevision) -> str:
    """El expediente, para que revisar tenga forma de tarea y no de intención."""
    lineas = [
        "# Expediente de revisión de reglas",
        "",
        "Las reglas curadas nacen candidatas y la evaluación no las usa hasta que alguien",
        "con competencia jurídica las aprueba. Este documento es lo que esa persona",
        "necesita para poder hacerlo: cada regla con su texto literal, qué afirma la",
        "lectura y la pregunta concreta que hay que contestar.",
        "",
        "Se genera con `bn revision reglas`. No aprueba nada: aprobar es",
        "`bn revision aprobar-regla`, que exige actor y fundamento y los deja en la",
        "bitácora.",
        "",
        "## Estado",
        "",
        "| Estado | Reglas |",
        "| --- | ---: |",
    ]
    for estado, cuantas in sorted(resultado.por_estado.items()):
        lineas.append(f"| {estado} | {cuantas} |")
    lineas += [
        "",
        f"En este expediente: **{len(resultado.reglas)}** regla(s), de las cuales "
        f"**{resultado.sin_condicion}** no tienen condición ejecutable. Esas dos pilas no se "
        "revisan igual: una condición escrita se confirma contra el texto, y una regla sin "
        "condición hay que decidir si se puede escribir o si es informativa.",
        "",
        "| Categoría | Reglas |",
        "| --- | ---: |",
    ]
    for categoria, cuantas in resultado.por_categoria.items():
        lineas.append(f"| {categoria} | {cuantas} |")
    if resultado.sin_ubicar:
        lineas += [
            "",
            f"**{resultado.sin_ubicar}** regla(s) no dicen a qué unidad del texto mirar: su "
            "evidencia no localiza una unidad. Revisarlas exige buscar el artículo a mano, así "
            "que conviene resolverlo antes de empezar.",
        ]
    lineas.append("")

    beneficio = None
    for regla in resultado.reglas:
        if regla.beneficio != beneficio:
            beneficio = regla.beneficio
            lineas += ["", f"## {beneficio}", ""]
        lineas += [
            f"### `{regla.id}` · {regla.categoria}",
            "",
            f"**Norma:** {regla.norma} · **Unidad:** `{regla.ruta or '—'}` · "
            f"**Estado:** {regla.estado} · "
            f"**Condición ejecutable:** {'sí' if regla.tiene_condicion else 'no'}",
            "",
            f"> {regla.texto_literal}",
            "",
            f"**La lectura afirma:** {regla.descripcion}",
            "",
            f"**Qué hay que decidir:** {regla.que_hay_que_decidir}",
            "",
        ]
    return "\n".join(lineas) + "\n"
