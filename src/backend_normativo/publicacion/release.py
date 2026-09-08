"""HU-025: publicación atómica y cuarentena.

Un release es un corte coherente de proyecciones. Publicar cambia el estado de
las versiones, construye los fragmentos citables y emite el evento, todo en la
misma transacción: una consulta nunca puede mezclar dos releases incompatibles
porque nunca existe un estado intermedio visible.

Lo que no pasa los gates queda en cuarentena con su motivo. No se publica "casi
todo": se publica lo que está en condiciones, y lo demás sigue siendo visible
como pendiente.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoRelease,
    EstadoRevision,
    TipoChunk,
    TipoEventoOutbox,
)
from backend_normativo.publicacion.gates import ResultadoGates, evaluar_gates


class PublicacionRechazada(Exception):
    """Los gates no se cumplen. No hay release."""

    def __init__(self, gates: ResultadoGates) -> None:
        detalle = "; ".join(f"{g.id}: {g.descripcion}" for g in gates.fallidos)
        super().__init__(f"La publicación no pasa los controles de calidad: {detalle}")
        self.gates = gates


class NadaQuePublicar(PublicacionRechazada):
    """No hay ninguna versión en condiciones de publicarse.

    Es distinto de que fallen los controles, y decirlo con las palabras de un
    control fallido —«no pasa los controles de calidad:» seguido de nada— manda
    a buscar un problema de calidad donde lo que hay es que ya está todo
    publicado, o que todavía no se aprobó nada.
    """

    def __init__(self, gates: ResultadoGates, *, en_cuarentena: int) -> None:
        Exception.__init__(
            self,
            "No hay ninguna versión para publicar: o ya están todas publicadas, o las "
            f"candidatas siguen sin aprobar. Quedan {en_cuarentena} en cuarentena; "
            "`bn publicacion estado` dice por qué cada una.",
        )
        self.gates = gates


@dataclass
class ResultadoPublicacion:
    release_id: uuid.UUID
    versiones_publicadas: int = 0
    chunks_creados: int = 0
    eventos_emitidos: int = 0
    en_cuarentena: list[dict] = field(default_factory=list)
    gates: ResultadoGates | None = None


class Publicador:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def candidatos(self) -> list[uuid.UUID]:
        """Versiones aprobadas, con vigencia resuelta y sin conflictos abiertos."""
        return list(
            self.conexion.execute(
                text(
                    "SELECT rv.id FROM registro_versiones rv "
                    " WHERE rv.estado_revision = 'APPROVED' "
                    "   AND rv.valid_tipo NOT IN ('DESCONOCIDO', 'CONDICIONADO') "
                    "   AND NOT EXISTS ("
                    "     SELECT 1 FROM incidencias_revision i "
                    "      WHERE i.registro_version_id = rv.id "
                    "        AND i.estado IN ('ABIERTA', 'EN_REVISION') "
                    "        AND i.severidad IN ('CRITICAL', 'HIGH'))"
                    " ORDER BY rv.known_desde"
                )
            ).scalars()
        )

    def cuarentena(self) -> list[dict]:
        """Lo que no puede publicarse todavía, con el motivo de cada caso.

        Es tan importante como lo publicable: sin esta lista, "no aparece en la
        respuesta" y "no existe" se vuelven indistinguibles.
        """
        filas = (
            self.conexion.execute(
                text(
                    "SELECT rv.id, rv.entidad_tipo, rv.estado_revision, rv.valid_tipo, "
                    "       (SELECT count(*) FROM incidencias_revision i "
                    "         WHERE i.registro_version_id = rv.id "
                    "           AND i.estado IN ('ABIERTA','EN_REVISION') "
                    "           AND i.severidad IN ('CRITICAL','HIGH')) AS conflictos "
                    "  FROM registro_versiones rv "
                    " WHERE rv.estado_revision <> 'PUBLISHED'"
                )
            )
            .mappings()
            .all()
        )

        cuarentena: list[dict] = []
        for fila in filas:
            motivos: list[str] = []
            if fila["estado_revision"] not in ("APPROVED", "PUBLISHED"):
                motivos.append(f"estado de revisión {fila['estado_revision']}")
            if fila["valid_tipo"] in ("DESCONOCIDO", "CONDICIONADO"):
                motivos.append(f"intervalo de aplicación {fila['valid_tipo']}")
            if fila["conflictos"]:
                motivos.append(f"{fila['conflictos']} conflicto(s) abiertos de severidad alta")
            if motivos:
                cuarentena.append(
                    {
                        "registro_version_id": str(fila["id"]),
                        "entidad_tipo": fila["entidad_tipo"],
                        "motivos": motivos,
                    }
                )
        return cuarentena

    def publicar(
        self,
        *,
        actor: str,
        motivo: str,
        candidatos: list[uuid.UUID] | None = None,
        ahora: dt.datetime | None = None,
    ) -> ResultadoPublicacion:
        ahora = ahora or dt.datetime.now(dt.UTC)
        candidatos = candidatos if candidatos is not None else self.candidatos()
        if not candidatos:
            raise NadaQuePublicar(
                evaluar_gates(self.conexion, []), en_cuarentena=len(self.cuarentena())
            )

        gates = evaluar_gates(self.conexion, candidatos)
        self._registrar_controles(gates, candidatos, ahora)
        if not gates.pasa:
            raise PublicacionRechazada(gates)

        manifiesto = self._manifiesto(candidatos)
        release_id = self.conexion.execute(
            text(
                "INSERT INTO releases (estado, publicado_en, manifest_hash, aprobado_por, motivo) "
                "VALUES (:estado, :ahora, :hash, :actor, :motivo) RETURNING id"
            ),
            {
                "estado": EstadoRelease.PUBLICADO.value,
                "ahora": ahora,
                "hash": manifiesto,
                "actor": actor,
                "motivo": motivo,
            },
        ).scalar_one()

        resultado = ResultadoPublicacion(release_id=release_id, gates=gates)

        self.conexion.execute(
            text(
                "UPDATE registro_versiones SET estado_revision = :estado, release_id = :r "
                " WHERE id = ANY(:v)"
            ),
            {"estado": EstadoRevision.PUBLISHED.value, "r": release_id, "v": candidatos},
        )
        resultado.versiones_publicadas = len(candidatos)

        self.conexion.execute(
            text(
                "UPDATE afirmaciones SET estado_revision = 'PUBLISHED' "
                " WHERE registro_version_id = ANY(:v) AND estado_revision = 'APPROVED'"
            ),
            {"v": candidatos},
        )

        resultado.chunks_creados = self._construir_chunks(release_id, candidatos)
        resultado.eventos_emitidos = self._emitir_eventos(release_id, candidatos, manifiesto)
        resultado.en_cuarentena = self.cuarentena()

        self.conexion.execute(
            text(
                "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, "
                " despues_hash, motivo) "
                "VALUES (:actor, 'PUBLICAR_RELEASE', 'releases', :id, :hash, :motivo)"
            ),
            {"actor": actor, "id": str(release_id), "hash": manifiesto, "motivo": motivo},
        )
        return resultado

    def revertir(self, release_id: uuid.UUID, *, actor: str, motivo: str) -> int:
        """Deja de servir un release sin borrar nada.

        Las versiones vuelven a estado aprobado y quedan disponibles para otro
        release. El historial del release revertido se conserva.
        """
        afectadas = (
            self.conexion.execute(
                text(
                    "UPDATE registro_versiones SET estado_revision = 'APPROVED' "
                    " WHERE release_id = :r RETURNING id"
                ),
                {"r": release_id},
            )
            .scalars()
            .all()
        )
        self.conexion.execute(
            text("UPDATE releases SET estado = :estado, motivo = :motivo WHERE id = :r"),
            {"estado": EstadoRelease.REVERTIDO.value, "motivo": motivo, "r": release_id},
        )
        self.conexion.execute(
            text(
                "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
                "VALUES (:actor, 'REVERTIR_RELEASE', 'releases', :id, :motivo)"
            ),
            {"actor": actor, "id": str(release_id), "motivo": motivo},
        )
        return len(afectadas)

    # --- Internos ----------------------------------------------------------

    def _manifiesto(self, candidatos: list[uuid.UUID]) -> str:
        """Huella del contenido del release, reproducible desde sus versiones."""
        contenido = json.dumps(sorted(str(c) for c in candidatos)).encode("utf-8")
        return hashlib.sha256(contenido).hexdigest()

    def _registrar_controles(
        self, gates: ResultadoGates, candidatos: list[uuid.UUID], ahora: dt.datetime
    ) -> None:
        """Deja el resultado de cada control sobre cada versión evaluada.

        Un control tiene que quedar atado a algo concreto: si se guardara suelto,
        más adelante nadie podría decir bajo qué controles se publicó una versión
        determinada.
        """
        for gate in gates.gates:
            for candidato in candidatos:
                self.conexion.execute(
                    text(
                        "INSERT INTO controles_calidad "
                        "(registro_version_id, control_id, version, resultado, severidad, "
                        " observado, esperado, ejecutado_en) "
                        "VALUES (:rv, :id, 'gates@1', :res, :sev, :obs, :esp, :ahora)"
                    ),
                    {
                        "rv": candidato,
                        "id": gate.id,
                        "res": "PASA" if gate.pasa else "FALLA",
                        "sev": "INFO" if gate.pasa else "CRITICAL",
                        "obs": json.dumps(gate.observado),
                        "esp": json.dumps(gate.esperado),
                        "ahora": ahora,
                    },
                )

    def _construir_chunks(self, release_id: uuid.UUID, candidatos: list[uuid.UUID]) -> int:
        """Fragmentos citables de lo publicado.

        Solo se indexa texto dispositivo: una nota editorial o un texto citado
        dentro de otro artículo no es la norma, y recuperarlo como si lo fuera
        haría que una respuesta cite algo que la norma no dice.
        """
        creados = (
            self.conexion.execute(
                text(
                    "INSERT INTO chunks (unidad_id, registro_version_id, release_id, texto, hash, "
                    "                    tipo, tsv) "
                    "SELECT u.id, nv.registro_version_id, :r, u.texto, "
                    "       encode(sha256(u.texto::bytea), 'hex'), :tipo, "
                    "       to_tsvector('spanish', u.texto) "
                    "  FROM unidades_documentales u "
                    "  JOIN norma_versiones nv ON nv.doc_version_id = u.doc_version_id "
                    " WHERE nv.registro_version_id = ANY(:v) "
                    "   AND u.rol_contenido = 'DISPOSITIVO' "
                    "   AND length(btrim(u.texto)) > 0 "
                    "ON CONFLICT (release_id, unidad_id, hash) DO NOTHING "
                    "RETURNING id"
                ),
                {"r": release_id, "v": candidatos, "tipo": TipoChunk.UNIDAD_NORMATIVA.value},
            )
            .scalars()
            .all()
        )
        return len(creados)

    def _emitir_eventos(
        self, release_id: uuid.UUID, candidatos: list[uuid.UUID], manifiesto: str
    ) -> int:
        """Deja el evento en el outbox. Crearlo no es entregarlo.

        `entregado_en` solo se completa cuando un consumidor confirma. No se
        afirma que se envió un mensaje que nadie recibió.
        """
        self.conexion.execute(
            text(
                "INSERT INTO eventos_outbox (release_id, tipo, aggregate_id, payload, "
                " idempotency_key) VALUES (:r, :tipo, :agg, :payload, :clave)"
            ),
            {
                "r": release_id,
                "tipo": TipoEventoOutbox.RELEASE_PUBLICADO.value,
                "agg": str(release_id),
                "payload": json.dumps(
                    {
                        "release_id": str(release_id),
                        "manifest_hash": manifiesto,
                        "versiones": len(candidatos),
                    }
                ),
                "clave": f"release:{release_id}",
            },
        )
        return 1
