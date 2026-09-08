"""HU-023: resolver vigencia y frescura por capacidad.

Aplica la política `politicas/vigencia.py` a cada versión de norma y deja el
resto en la cola de revisión con su fundamento. Nunca deduce una vigencia
abierta de la ausencia de una derogación registrada.

La frescura es otra cosa y se guarda aparte: `verificado_en` dice cuándo se
comprobó la fuente y `reverificar_antes_de` hasta cuándo esa comprobación se
considera suficiente. Vencer ese plazo no deroga nada.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoRevision,
    Severidad,
)
from backend_normativo.politicas import vigencia as politica


@dataclass
class ResultadoVigencia:
    versiones: int = 0
    resueltas_por_politica: int = 0
    derivadas_a_revision: int = 0
    incidencias_creadas: int = 0
    avisos: list[str] = field(default_factory=list)


class ResolutorVigencia:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def resolver(
        self, *, ahora: dt.datetime | None = None, source_id: str | None = None
    ) -> ResultadoVigencia:
        ahora = ahora or dt.datetime.now(dt.UTC)
        resultado = ResultadoVigencia()

        versiones = (
            self.conexion.execute(
                text(
                    "SELECT nv.registro_version_id, nv.norma_id, nv.estado_legal_declarado, "
                    "       nv.fundamento_estado_evidencia_id, rv.valid_desde, rv.valid_tipo, "
                    "       rv.estado_revision, d.source_id, "
                    "       (SELECT c.ttl_defecto FROM fuente_config_versiones c "
                    "         WHERE c.source_id = d.source_id "
                    "         ORDER BY c.version DESC LIMIT 1) AS ttl "
                    "  FROM norma_versiones nv "
                    "  JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
                    "  JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                    "  JOIN documentos d ON d.id = dv.documento_id "
                    " WHERE rv.estado_revision IN ('CANDIDATE', 'IN_REVIEW') "
                    "   AND (CAST(:sid AS text) IS NULL OR d.source_id = :sid)"
                ),
                {"sid": source_id},
            )
            .mappings()
            .all()
        )

        for version in versiones:
            resultado.versiones += 1
            self._resolver_version(dict(version), ahora, resultado)
        return resultado

    def _resolver_version(
        self, version: dict, ahora: dt.datetime, resultado: ResultadoVigencia
    ) -> None:
        cierres, reaperturas = self._relaciones_de_vigencia(version["norma_id"])
        evidencia_estado = self._evidencia_del_estado(version)

        dictamen = politica.dictaminar(
            estado_declarado=version["estado_legal_declarado"],
            tiene_fecha_inicio=version["valid_desde"] is not None,
            cierres_aprobados=cierres,
            reaperturas_aprobadas=reaperturas,
            tiene_evidencia_de_estado=evidencia_estado is not None,
        )

        if not dictamen.automatica:
            resultado.derivadas_a_revision += 1
            self._abrir_incidencia(version, dictamen, resultado)
            return

        ttl = version["ttl"] or dt.timedelta(days=30)
        self.conexion.execute(
            text(
                "UPDATE registro_versiones "
                "   SET valid_tipo = :vt, verificado_en = :ahora, "
                "       reverificar_antes_de = :hasta, estado_revision = :estado "
                " WHERE id = :id"
            ),
            {
                "vt": dictamen.valid_tipo.value,
                "ahora": ahora,
                # Frescura: hasta cuándo alcanza esta comprobación. No tiene
                # nada que ver con hasta cuándo rige la norma.
                "hasta": ahora + ttl,
                "estado": EstadoRevision.APPROVED.value,
                "id": version["registro_version_id"],
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
                "estado": dictamen.estado_legal.value,
                "evidencia": evidencia_estado,
                "id": version["registro_version_id"],
            },
        )
        self.conexion.execute(
            text(
                "INSERT INTO auditoria_eventos "
                "(actor, accion, objeto, objeto_id, motivo) "
                "VALUES (:actor, 'RESOLVER_VIGENCIA', 'registro_versiones', :id, :motivo)"
            ),
            {
                "actor": f"politica:{politica.VERSION}",
                "id": str(version["registro_version_id"]),
                "motivo": dictamen.fundamento,
            },
        )
        resultado.resueltas_por_politica += 1

    def _relaciones_de_vigencia(self, norma_id) -> tuple[int, int]:
        fila = self.conexion.execute(
            text(
                "SELECT "
                "  count(*) FILTER (WHERE tipo = ANY(:cierran)) AS cierres, "
                "  count(*) FILTER (WHERE tipo = ANY(:reabren)) AS reaperturas "
                "FROM relaciones_normativas "
                "WHERE norma_destino_id = :n AND estado_revision IN ('APPROVED', 'PUBLISHED')"
            ),
            {
                "n": norma_id,
                "cierran": list(politica.RELACIONES_QUE_CIERRAN),
                "reabren": list(politica.RELACIONES_QUE_REABREN),
            },
        ).one()
        return int(fila[0]), int(fila[1])

    def _evidencia_del_estado(self, version: dict):
        """Evidencia que respalda el estado declarado por la fuente.

        Se busca en la ficha de la misma norma: el estado es un campo de la
        ficha, no del texto.
        """
        if version["fundamento_estado_evidencia_id"] is not None:
            return version["fundamento_estado_evidencia_id"]
        return self.conexion.execute(
            text(
                "SELECT e.id FROM evidencias e "
                "  JOIN documento_versiones dv ON dv.id = e.doc_version_id "
                "  JOIN norma_versiones nv ON nv.doc_version_id = dv.id "
                " WHERE nv.norma_id = :n ORDER BY e.creado_en LIMIT 1"
            ),
            {"n": version["norma_id"]},
        ).scalar_one_or_none()

    def _abrir_incidencia(
        self, version: dict, dictamen: politica.Dictamen, resultado: ResultadoVigencia
    ) -> None:
        ya_existe = self.conexion.execute(
            text(
                "SELECT 1 FROM incidencias_revision "
                " WHERE registro_version_id = :rv AND tipo = 'VIGENCIA_INDETERMINADA' "
                "   AND estado <> 'RESUELTA'"
            ),
            {"rv": version["registro_version_id"]},
        ).first()
        if ya_existe:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(registro_version_id, source_id, tipo, severidad, estado, descripcion, "
                " responsable_rol) "
                "VALUES (:rv, :s, 'VIGENCIA_INDETERMINADA', :sev, 'ABIERTA', :d, "
                " 'curacion_juridica')"
            ),
            {
                "rv": version["registro_version_id"],
                "s": version["source_id"],
                "sev": Severidad.MEDIUM.value,
                "d": dictamen.fundamento,
            },
        )
        resultado.incidencias_creadas += 1
