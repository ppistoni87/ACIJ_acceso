"""Aprobar versiones de dato operativo en bloque, con las protecciones puestas.

Un canal es «Defensoría X, teléfono Y, dirección Z, horario W» transcripto de un
directorio oficial, con una evidencia que apunta al fragmento exacto. No es una
lectura jurídica: no afirma qué le corresponde a nadie. Por eso se puede aprobar
en bloque y las reglas no.

Lo que **no** cambia es la exigencia de que aprobar signifique algo. Este módulo
se niega a tres cosas:

* **A tocar una versión con una incidencia abierta.** Si el sistema marcó algo
  sobre ese registro, aprobarlo en bloque es enterrar la marca.
* **A tocar una versión sin intervalo de aplicación.** Sin saber desde cuándo
  vale, servirla sería afirmar una vigencia que nadie determinó.
* **A aprobar sin dejar rastro por versión.** Lo que se firma una vez tiene que
  poder auditarse una por una, igual que las reglas.

Y no aprueba nada si el conjunto elegido incluye algo que no debería estar: un
bloque a medias deja al corpus en un estado que nadie sabe leer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text


class AprobacionInvalida(Exception):
    """El conjunto pedido no se puede aprobar tal como está."""


@dataclass
class Seleccion:
    """Lo que se aprobaría, y lo que queda afuera con su motivo."""

    aprobables: dict[str, int] = field(default_factory=dict)
    con_incidencia: int = 0
    sin_vigencia: int = 0

    @property
    def total(self) -> int:
        return sum(self.aprobables.values())


def revisar(conexion: Connection, *, tipos: list[str] | None = None) -> Seleccion:
    """Qué hay para aprobar y qué queda afuera, sin tocar nada."""
    filtro_tipo = "AND rv.entidad_tipo = ANY(:tipos)" if tipos else ""
    parametros = {"tipos": tipos} if tipos else {}

    seleccion = Seleccion()
    for fila in conexion.execute(
        text(
            "SELECT rv.entidad_tipo, count(*) AS cuantas "
            "  FROM registro_versiones rv "
            " WHERE rv.release_id IS NULL AND rv.estado_revision = 'CANDIDATE' "
            "   AND rv.valid_tipo <> 'DESCONOCIDO' "
            f"  {filtro_tipo} "
            "   AND NOT EXISTS (SELECT 1 FROM incidencias_revision i "
            "                    WHERE i.registro_version_id = rv.id AND i.estado = 'ABIERTA') "
            " GROUP BY rv.entidad_tipo ORDER BY 2 DESC"
        ),
        parametros,
    ).mappings():
        seleccion.aprobables[fila["entidad_tipo"]] = fila["cuantas"]

    seleccion.con_incidencia = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones rv "
            " WHERE rv.release_id IS NULL AND rv.estado_revision = 'CANDIDATE' "
            "   AND rv.valid_tipo <> 'DESCONOCIDO' "
            f"  {filtro_tipo} "
            "   AND EXISTS (SELECT 1 FROM incidencias_revision i "
            "                WHERE i.registro_version_id = rv.id AND i.estado = 'ABIERTA')"
        ),
        parametros,
    ).scalar_one()

    seleccion.sin_vigencia = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones rv "
            " WHERE rv.release_id IS NULL AND rv.estado_revision = 'CANDIDATE' "
            "   AND rv.valid_tipo = 'DESCONOCIDO' "
            f"  {filtro_tipo}"
        ),
        parametros,
    ).scalar_one()
    return seleccion


def aprobar(
    conexion: Connection, *, actor: str, fundamento: str, tipos: list[str] | None = None
) -> Seleccion:
    """Aprueba lo aprobable y deja un evento por versión."""
    if not actor.strip():
        raise AprobacionInvalida("Falta el actor: la bitácora tiene que decir quién aprobó.")
    if not fundamento.strip():
        raise AprobacionInvalida(
            "Aprobar sin fundamento deja catorce mil decisiones sin razón escrita."
        )

    seleccion = revisar(conexion, tipos=tipos)
    if seleccion.total == 0:
        raise AprobacionInvalida(
            "No hay ninguna versión aprobable con esos filtros. "
            f"Quedaron afuera {seleccion.con_incidencia} por incidencia abierta y "
            f"{seleccion.sin_vigencia} sin intervalo de aplicación."
        )

    filtro_tipo = "AND rv.entidad_tipo = ANY(:tipos)" if tipos else ""
    parametros: dict = {"tipos": tipos} if tipos else {}

    aprobadas = (
        conexion.execute(
            text(
                "UPDATE registro_versiones rv SET estado_revision = 'APPROVED' "
                " WHERE rv.release_id IS NULL AND rv.estado_revision = 'CANDIDATE' "
                "   AND rv.valid_tipo <> 'DESCONOCIDO' "
                f"  {filtro_tipo} "
                "   AND NOT EXISTS (SELECT 1 FROM incidencias_revision i "
                "                    WHERE i.registro_version_id = rv.id AND i.estado = 'ABIERTA') "
                " RETURNING rv.id"
            ),
            parametros,
        )
        .scalars()
        .all()
    )

    # Un evento por versión: lo que se firma una vez tiene que poder auditarse
    # una por una. Se insertan de a lotes porque son miles y una ida por fila
    # convertiría una aprobación en una espera.
    conexion.execute(
        text(
            "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
            "SELECT :actor, 'APROBAR_VERSION', 'registro_versiones', rv.id::text, :motivo "
            "  FROM registro_versiones rv WHERE rv.id = ANY(:ids)"
        ),
        {"actor": actor, "motivo": fundamento, "ids": list(aprobadas)},
    )
    return seleccion


def formatear(seleccion: Seleccion, *, aplicado: bool) -> str:
    verbo = "Aprobadas" if aplicado else "Se aprobarían"
    lineas = [f"{verbo} {seleccion.total} versión(es):"]
    for tipo, cuantas in sorted(seleccion.aprobables.items(), key=lambda p: -p[1]):
        lineas.append(f"  {cuantas:>7}  {tipo}")
    if seleccion.con_incidencia:
        lineas.append(
            f"  Quedan afuera {seleccion.con_incidencia} con una incidencia abierta: "
            "aprobarlas en bloque enterraría la marca."
        )
    if seleccion.sin_vigencia:
        lineas.append(
            f"  Quedan afuera {seleccion.sin_vigencia} sin intervalo de aplicación: "
            "servirlas sería afirmar una vigencia que nadie determinó."
        )
    if not aplicado:
        lineas.append("  Nada se escribió. Volvé a correrlo con --confirmar.")
    return "\n".join(lineas)
