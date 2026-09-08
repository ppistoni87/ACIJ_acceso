"""HU-024: resolver una incidencia con decisión, actor y fundamento.

Una resolución no borra el conflicto: lo cierra dejando quién decidió, con qué
fundamento y cuándo. Los candidatos que estaban en discusión se conservan, y la
decisión queda en la bitácora append-only.

Este es el camino por el que un dato llega a poder publicarse. No hay otro: la
política automática solo cubre los casos que declara, y todo lo demás pasa por
acá.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoIncidencia,
    EstadoLegal,
    EstadoRevision,
    ValidTipo,
)


class ConflictoDeVersion(Exception):
    """La incidencia cambió desde que se leyó. La decisión no se aplica."""


class DecisionInvalida(ValueError):
    """La decisión no cumple lo que exige el tipo de incidencia."""


@dataclass
class ResultadoResolucion:
    incidencia_id: uuid.UUID
    version_afectada: uuid.UUID | None
    aplico_vigencia: bool = False


class Revisor:
    """Aplica decisiones de revisión sobre incidencias abiertas."""

    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def resolver(
        self,
        incidencia_id: uuid.UUID,
        *,
        decision: str,
        actor: str,
        fundamento_evidencia_id: uuid.UUID | None = None,
        vigencia: dict | None = None,
        estado_esperado: str = EstadoIncidencia.ABIERTA.value,
        ahora: dt.datetime | None = None,
    ) -> ResultadoResolucion:
        ahora = ahora or dt.datetime.now(dt.UTC)
        if not decision.strip():
            raise DecisionInvalida("una resolución necesita decir qué se decidió")
        if not actor.strip():
            raise DecisionInvalida("una resolución necesita decir quién decidió")

        incidencia = (
            self.conexion.execute(
                text(
                    "SELECT id, tipo, estado, registro_version_id FROM incidencias_revision "
                    " WHERE id = :id FOR UPDATE"
                ),
                {"id": incidencia_id},
            )
            .mappings()
            .first()
        )
        if incidencia is None:
            raise LookupError(f"No existe la incidencia {incidencia_id}")
        if incidencia["estado"] != estado_esperado:
            # Concurrencia optimista: alguien más ya la movió.
            raise ConflictoDeVersion(
                f"La incidencia está en {incidencia['estado']} y se esperaba {estado_esperado}."
            )

        resultado = ResultadoResolucion(
            incidencia_id=incidencia_id, version_afectada=incidencia["registro_version_id"]
        )

        if incidencia["tipo"] == "VIGENCIA_INDETERMINADA":
            if vigencia is None:
                raise DecisionInvalida(
                    "resolver una vigencia indeterminada exige decir qué vigencia queda"
                )
            if fundamento_evidencia_id is None:
                raise DecisionInvalida(
                    "afirmar un estado de vigencia exige la evidencia que lo fundamenta"
                )
            self._aplicar_vigencia(
                incidencia["registro_version_id"], vigencia, fundamento_evidencia_id, ahora
            )
            resultado.aplico_vigencia = True

        self.conexion.execute(
            text(
                "UPDATE incidencias_revision "
                "   SET estado = :estado, decision = :decision, decidido_por = :actor, "
                "       fundamento_evidencia_id = :evidencia, resuelta_en = :ahora "
                " WHERE id = :id"
            ),
            {
                "estado": EstadoIncidencia.RESUELTA.value,
                "decision": decision,
                "actor": actor,
                "evidencia": fundamento_evidencia_id,
                "ahora": ahora,
                "id": incidencia_id,
            },
        )
        self.conexion.execute(
            text(
                "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
                "VALUES (:actor, 'RESOLVER_INCIDENCIA', 'incidencias_revision', :id, :motivo)"
            ),
            {"actor": actor, "id": str(incidencia_id), "motivo": decision},
        )
        return resultado

    def _aplicar_vigencia(
        self,
        registro_version_id: uuid.UUID | None,
        vigencia: dict,
        evidencia_id: uuid.UUID,
        ahora: dt.datetime,
    ) -> None:
        if registro_version_id is None:
            raise DecisionInvalida(
                "la incidencia no está asociada a una versión: no hay qué actualizar"
            )

        valid_tipo = ValidTipo(vigencia["valid_tipo"])
        estado_legal = EstadoLegal(vigencia.get("estado_legal", EstadoLegal.NO_DETERMINADA.value))

        self.conexion.execute(
            text(
                "UPDATE registro_versiones "
                "   SET valid_tipo = :vt, valid_desde = coalesce(:desde, valid_desde), "
                "       valid_hasta = :hasta, condicion_vigencia = :condicion, "
                "       verificado_en = :ahora, reverificar_antes_de = :hasta_frescura, "
                "       estado_revision = :estado "
                " WHERE id = :id"
            ),
            {
                "vt": valid_tipo.value,
                "desde": vigencia.get("valid_desde"),
                "hasta": vigencia.get("valid_hasta"),
                "condicion": vigencia.get("condicion_vigencia"),
                "ahora": ahora,
                "hasta_frescura": ahora + dt.timedelta(days=vigencia.get("ttl_dias", 30)),
                "estado": EstadoRevision.APPROVED.value,
                "id": registro_version_id,
            },
        )
        self.conexion.execute(
            text(
                "UPDATE norma_versiones "
                "   SET estado_legal_validado = :estado, "
                "       fundamento_estado_evidencia_id = :evidencia "
                " WHERE registro_version_id = :id"
            ),
            {
                "estado": estado_legal.value,
                "evidencia": evidencia_id,
                "id": registro_version_id,
            },
        )

    def aprobar_afirmaciones(
        self, registro_version_id: uuid.UUID, campo: str, *, actor: str
    ) -> int:
        """Aprueba los candidatos de un campo para una versión.

        Aprobar es lo que convierte un candidato en valor sustantivo. Solo se
        aprueban los que tienen evidencia: la restricción del esquema ya lo
        exige, y acá se filtra explícitamente para que el conteo no mienta.
        """
        aprobadas = (
            self.conexion.execute(
                text(
                    "UPDATE afirmaciones SET estado_revision = 'APPROVED' "
                    " WHERE registro_version_id = :rv AND campo_path = :c "
                    "   AND estado_revision = 'CANDIDATE' AND evidencia_id IS NOT NULL "
                    " RETURNING id"
                ),
                {"rv": registro_version_id, "c": campo},
            )
            .scalars()
            .all()
        )
        if aprobadas:
            self.conexion.execute(
                text(
                    "INSERT INTO auditoria_eventos "
                    "(actor, accion, objeto, objeto_id, motivo) "
                    "VALUES (:actor, 'APROBAR_AFIRMACIONES', 'registro_versiones', :id, :m)"
                ),
                {
                    "actor": actor,
                    "id": str(registro_version_id),
                    "m": f"{len(aprobadas)} afirmación(es) de «{campo}» aprobadas.",
                },
            )
        return len(aprobadas)
