"""HU-010: construir relaciones normativas y dejar constancia de lo que falta.

Cada relación nace de una cita concreta en una unidad concreta, con su evidencia
localizable. Tres reglas que este módulo respeta:

* **Citar no es modificar.** Cuando el contexto no permite decidir qué relación
  jurídica hay, se registra `CITA` y nada más.
* **No se inventa el destino.** Si la norma citada no está identificada en el
  corpus, la referencia queda pendiente con su texto literal y sus candidatas.
  Resolverla después conserva la auditoría de cómo se resolvió.
* **Las relaciones nacen como candidatas.** Ninguna se publica sin revisión: el
  sentido jurídico de una relación no lo decide un patrón de texto.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.curacion.citas import CitaDetectada, detectar_citas
from backend_normativo.db.vocabularios import (
    EstadoRevision,
    RolContenido,
    TipoEvidencia,
    TipoRelacionNormativa,
)


@dataclass
class ResultadoRelaciones:
    unidades_analizadas: int = 0
    citas_detectadas: int = 0
    relaciones_creadas: int = 0
    relaciones_existentes: int = 0
    pendientes_creadas: int = 0
    autorreferencias_omitidas: int = 0
    avisos: list[str] = field(default_factory=list)


class ConstructorRelaciones:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def construir(self, source_id: str | None = None) -> ResultadoRelaciones:
        resultado = ResultadoRelaciones()
        versiones = (
            self.conexion.execute(
                text(
                    "SELECT nv.registro_version_id, nv.norma_id, nv.doc_version_id, "
                    "       n.jurisdiccion_id, d.source_id "
                    "  FROM norma_versiones nv "
                    "  JOIN normas n ON n.id = nv.norma_id "
                    "  JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                    "  JOIN documentos d ON d.id = dv.documento_id "
                    " WHERE (CAST(:sid AS text) IS NULL OR d.source_id = :sid)"
                ),
                {"sid": source_id},
            )
            .mappings()
            .all()
        )

        for version in versiones:
            self._procesar_version(dict(version), resultado)
        return resultado

    def _procesar_version(self, version: dict, resultado: ResultadoRelaciones) -> None:
        unidades = (
            self.conexion.execute(
                text(
                    "SELECT id, texto, rol_contenido, tipo, numero FROM unidades_documentales "
                    "WHERE doc_version_id = :dv ORDER BY orden"
                ),
                {"dv": version["doc_version_id"]},
            )
            .mappings()
            .all()
        )

        for unidad in unidades:
            resultado.unidades_analizadas += 1
            citas = detectar_citas(unidad["texto"])
            resultado.citas_detectadas += len(citas)
            for cita in citas:
                self._registrar(version, dict(unidad), cita, resultado)

    def _registrar(
        self,
        version: dict,
        unidad: dict,
        cita: CitaDetectada,
        resultado: ResultadoRelaciones,
    ) -> None:
        destino_id, candidatas = self._resolver_destino(version["jurisdiccion_id"], cita)

        if destino_id == version["norma_id"]:
            # Una norma que se nombra a sí misma no genera una relación: el
            # grafo se llenaría de bucles sin información.
            resultado.autorreferencias_omitidas += 1
            return

        evidencia_id = self._evidencia(version["doc_version_id"], unidad, cita)

        if destino_id is None:
            self._pendiente(version, cita, evidencia_id, candidatas, resultado)
            return

        origen, destino = (
            (destino_id, version["norma_id"])
            if cita.citada_es_origen
            else (version["norma_id"], destino_id)
        )
        unidad_origen = None if cita.citada_es_origen else unidad["id"]
        unidad_destino = unidad["id"] if cita.citada_es_origen else None

        creada = self.conexion.execute(
            text(
                "INSERT INTO relaciones_normativas ("
                "  norma_origen_id, norma_destino_id, evidencia_id, tipo, "
                "  unidad_origen_id, unidad_destino_id, alcance, estado_revision"
                ") VALUES (:o, :d, :e, :t, :uo, :ud, :alcance, :estado) "
                "ON CONFLICT (norma_origen_id, norma_destino_id, tipo, unidad_origen_id, "
                "             unidad_destino_id) DO NOTHING RETURNING id"
            ),
            {
                "o": origen,
                "d": destino,
                "e": evidencia_id,
                "t": cita.relacion.value,
                "uo": unidad_origen,
                "ud": unidad_destino,
                "alcance": self._alcance(unidad),
                # Ninguna relación se publica sin revisión: el sentido jurídico
                # no lo decide un patrón de texto.
                "estado": EstadoRevision.CANDIDATE.value,
            },
        ).scalar_one_or_none()
        if creada is None:
            resultado.relaciones_existentes += 1
        else:
            resultado.relaciones_creadas += 1

    @staticmethod
    def _alcance(unidad: dict) -> str | None:
        """La relación puede afectar solo un artículo, no la norma entera."""
        if unidad["tipo"] == "ARTICULO" and unidad["numero"]:
            return f"Citada en el artículo {unidad['numero']}"
        if unidad["rol_contenido"] == RolContenido.NOTA.value:
            return "Declarada en una nota editorial de la fuente, no en el texto de la norma"
        return None

    def _resolver_destino(
        self, jurisdiccion: str, cita: CitaDetectada
    ) -> tuple[uuid.UUID | None, list[dict]]:
        """Busca la norma citada en la misma jurisdicción.

        No se busca en otras jurisdicciones: una ordenanza citada en una norma de
        CABA es de CABA, y adivinar el ámbito produce relaciones entre normas que
        no tienen nada que ver.
        """
        parametros = {
            "j": jurisdiccion,
            "t": cita.tipo_norma.value,
            "n": cita.numero,
        }
        if cita.anio is not None:
            encontrada = self.conexion.execute(
                text(
                    "SELECT id FROM normas WHERE jurisdiccion_id = :j AND tipo = :t "
                    "  AND numero = :n AND anio = :a AND identidad_incierta = false"
                ),
                {**parametros, "a": cita.anio},
            ).scalar_one_or_none()
            return encontrada, []

        # Sin año, solo se resuelve si no hay ambigüedad.
        candidatas = (
            self.conexion.execute(
                text(
                    "SELECT id, anio FROM normas WHERE jurisdiccion_id = :j AND tipo = :t "
                    "  AND numero = :n AND identidad_incierta = false ORDER BY anio"
                ),
                parametros,
            )
            .mappings()
            .all()
        )
        if len(candidatas) == 1:
            return candidatas[0]["id"], []
        return None, [{"norma_id": str(c["id"]), "anio": c["anio"]} for c in candidatas]

    def _evidencia(self, doc_version_id: uuid.UUID, unidad: dict, cita: CitaDetectada) -> uuid.UUID:
        """Fragmento localizable que respalda la relación.

        El fragmento es el contexto de la cita, no la unidad entera: una cita
        que solo comparte tema con el texto no es evidencia de nada.
        """
        fragmento = cita.contexto
        hash_fragmento = hashlib.sha256(fragmento.encode("utf-8")).hexdigest()
        # Puede haber más de una: la evidencia es inmutable y se direcciona por
        # el contenido, así que dos curadores que citan el mismo fragmento de la
        # misma unidad escriben filas equivalentes. Se toma la más antigua para
        # que la elección no dependa del orden en que se hayan cargado; pedir
        # exactamente una detenía la población entera por un empate que no
        # cambia nada de lo que se afirma.
        existente = self.conexion.execute(
            text(
                "SELECT id FROM evidencias WHERE doc_version_id = :dv AND unidad_id = :u "
                "  AND hash_fragmento = :h ORDER BY creado_en, id LIMIT 1"
            ),
            {"dv": doc_version_id, "u": unidad["id"], "h": hash_fragmento},
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias "
                "(doc_version_id, unidad_id, fragmento, hash_fragmento, tipo, "
                " offset_inicio, offset_fin) "
                "VALUES (:dv, :u, :f, :h, :tipo, :ini, :fin) RETURNING id"
            ),
            {
                "dv": doc_version_id,
                "u": unidad["id"],
                "f": fragmento,
                "h": hash_fragmento,
                "tipo": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "ini": cita.posicion,
                "fin": cita.posicion + len(cita.texto_cita),
            },
        ).scalar_one()

    def _pendiente(
        self,
        version: dict,
        cita: CitaDetectada,
        evidencia_id: uuid.UUID,
        candidatas: list[dict],
        resultado: ResultadoRelaciones,
    ) -> None:
        identidad = {
            "tipo": cita.tipo_norma.value,
            "numero": cita.numero,
            "anio": cita.anio,
            "jurisdiccion_esperada": version["jurisdiccion_id"],
            "relacion_sugerida": cita.relacion.value,
            "citada_es_origen": cita.citada_es_origen,
            "candidatas_en_corpus": candidatas,
        }
        ya_existe = self.conexion.execute(
            text(
                "SELECT 1 FROM referencias_pendientes "
                "WHERE norma_origen_id = :n AND texto_cita = :t AND estado = 'PENDIENTE'"
            ),
            {"n": version["norma_id"], "t": cita.texto_cita},
        ).first()
        if ya_existe:
            return

        motivo = (
            "La norma citada no está en el corpus con esa identidad."
            if not candidatas
            else f"Hay {len(candidatas)} normas con ese tipo y número en la jurisdicción y la "
            "cita no declara el año."
        )
        self.conexion.execute(
            text(
                "INSERT INTO referencias_pendientes "
                "(norma_origen_id, evidencia_id, texto_cita, identidad_candidata, motivo, "
                " estado, responsable_rol) "
                "VALUES (:n, :e, :t, :i, :m, 'PENDIENTE', 'curacion_juridica')"
            ),
            {
                "n": version["norma_id"],
                "e": evidencia_id,
                "t": cita.texto_cita,
                "i": json.dumps(identidad, ensure_ascii=False),
                "m": motivo,
            },
        )
        resultado.pendientes_creadas += 1


__all__ = ["ConstructorRelaciones", "ResultadoRelaciones", "TipoRelacionNormativa"]
