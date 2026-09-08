"""Extracción: de bytes capturados a documentos, versiones y unidades.

Trabaja sobre capturas ya guardadas, nunca sobre la red. Eso es lo que hace la
extracción repetible: con la misma captura y la misma versión de extractor, el
resultado es el mismo.

Reingerir un contenido idéntico no duplica la versión documental ni sus
unidades. Sí deja la captura nueva, porque haber verificado que el texto no
cambió es información: no es lo mismo "no lo miramos desde marzo" que "lo
miramos ayer y sigue igual".
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import EstadoFuenteCandidata, Severidad, TipoIncidencia
from backend_normativo.ingesta.adaptadores.base import (
    Adaptador,
    CapturaMaterial,
    DocumentoExtraido,
    ResultadoExtraccion,
)
from backend_normativo.ingesta.adaptadores.infoleg_legacy import AdaptadorInfolegLegacy
from backend_normativo.ingesta.adaptadores.normativa_ba import AdaptadorNormativaBA
from backend_normativo.ingesta.adaptadores.normativa_nacional import AdaptadorNormativaNacional
from backend_normativo.ingesta.almacen import AlmacenObjetos

VERSION_EXTRACTOR = "extraccion@1"

# Cobertura mínima para no marcar la extracción como sospechosa. Es una señal
# técnica: por debajo de esto hay texto que no quedó en ninguna unidad, y
# publicar sobre esa versión sería publicar sobre un texto incompleto.
COBERTURA_MINIMA = 0.60


@dataclass
class ResultadoPersistencia:
    documentos_creados: int = 0
    versiones_creadas: int = 0
    versiones_repetidas: int = 0
    unidades_creadas: int = 0
    candidatas_creadas: int = 0
    incidencias_creadas: int = 0
    avisos: list[str] = field(default_factory=list)
    version_ids: list[uuid.UUID] = field(default_factory=list)


def adaptadores_por_defecto() -> list[Adaptador]:
    return [
        AdaptadorNormativaNacional(),
        AdaptadorInfolegLegacy(),
        AdaptadorNormativaBA(),
    ]


class Extractor:
    def __init__(
        self,
        conexion: Connection,
        adaptadores: list[Adaptador] | None = None,
        almacen: AlmacenObjetos | None = None,
    ) -> None:
        self.conexion = conexion
        self.adaptadores = adaptadores or adaptadores_por_defecto()
        self.almacen = almacen or AlmacenObjetos()

    # --- API ---------------------------------------------------------------

    def extraer_captura(self, captura_id: uuid.UUID) -> ResultadoPersistencia:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT c.id, c.sha256_raw, c.mime, c.url_final, u.source_id "
                    "FROM capturas c JOIN fuente_urls u ON u.id = c.source_url_id "
                    "WHERE c.id = :id"
                ),
                {"id": captura_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise LookupError(f"No existe la captura {captura_id}")

        resultado = ResultadoPersistencia()
        material = CapturaMaterial(
            source_id=fila["source_id"],
            url_final=fila["url_final"] or "",
            contenido=self.almacen.leer(fila["sha256_raw"]),
            mime=fila["mime"],
            sha256=fila["sha256_raw"],
        )

        adaptador = next((a for a in self.adaptadores if a.acepta(material)), None)
        if adaptador is None:
            resultado.avisos.append(
                f"Ninguna familia de extracción acepta {material.url_final!r} "
                f"(mime {material.mime!r}). La captura queda guardada sin extraer."
            )
            return resultado

        extraccion = adaptador.extraer(material)
        for documento in extraccion.documentos:
            self._persistir_documento(fila, documento, resultado)
        self._persistir_candidatas(fila["source_id"], extraccion, resultado)
        resultado.avisos.extend(extraccion.avisos)
        return resultado

    def extraer_pendientes(self, source_id: str | None = None) -> ResultadoPersistencia:
        """Capturas con cuerpo propio que todavía no produjeron una versión."""
        filas = (
            self.conexion.execute(
                text(
                    "SELECT c.id FROM capturas c "
                    "JOIN fuente_urls u ON u.id = c.source_url_id "
                    "WHERE coalesce(c.http_status, 0) <> 304 "
                    "  AND (CAST(:sid AS text) IS NULL OR u.source_id = :sid) "
                    "  AND NOT EXISTS (SELECT 1 FROM documento_versiones dv "
                    "                  WHERE dv.captura_id = c.id) "
                    "ORDER BY c.capturado_en"
                ),
                {"sid": source_id},
            )
            .scalars()
            .all()
        )

        total = ResultadoPersistencia()
        for captura_id in filas:
            parcial = self.extraer_captura(captura_id)
            total.documentos_creados += parcial.documentos_creados
            total.versiones_creadas += parcial.versiones_creadas
            total.versiones_repetidas += parcial.versiones_repetidas
            total.unidades_creadas += parcial.unidades_creadas
            total.candidatas_creadas += parcial.candidatas_creadas
            total.incidencias_creadas += parcial.incidencias_creadas
            total.avisos.extend(parcial.avisos)
            total.version_ids.extend(parcial.version_ids)
        return total

    # --- Persistencia -------------------------------------------------------

    def _persistir_documento(
        self, captura: dict, documento: DocumentoExtraido, resultado: ResultadoPersistencia
    ) -> None:
        documento_id, creado = self._documento_id(captura["source_id"], documento)
        resultado.documentos_creados += int(creado)

        hash_texto = hashlib.sha256(documento.texto.encode("utf-8")).hexdigest()
        existente = self.conexion.execute(
            text(
                "SELECT id FROM documento_versiones "
                "WHERE documento_id = :d AND hash_texto = :h AND tipo_version = :t"
            ),
            {"d": documento_id, "h": hash_texto, "t": documento.tipo_version.value},
        ).scalar_one_or_none()
        if existente is not None:
            # El texto no cambió: la captura queda como constancia de que se
            # verificó, y no se duplican unidades.
            resultado.versiones_repetidas += 1
            resultado.version_ids.append(existente)
            return

        proxima = self.conexion.execute(
            text(
                "SELECT coalesce(max(version), 0) + 1 FROM documento_versiones "
                "WHERE documento_id = :d"
            ),
            {"d": documento_id},
        ).scalar_one()

        version_id = self.conexion.execute(
            text(
                "INSERT INTO documento_versiones ("
                "  documento_id, captura_id, version, tipo_version, fecha_documento, "
                "  tipo_fecha, texto_extraido, hash_texto, modo_extraccion, paginas, "
                "  chars_por_pagina, extraccion_score, identidad_candidata"
                ") VALUES (:d, :c, :v, :tv, :fecha, :tf, :texto, :hash, :modo, :pag, "
                "          :chars, :score, :identidad) RETURNING id"
            ),
            {
                "d": documento_id,
                "c": captura["id"],
                "v": proxima,
                "tv": documento.tipo_version.value,
                "fecha": documento.fecha_documento,
                "tf": documento.tipo_fecha.value,
                "texto": documento.texto,
                "hash": hash_texto,
                "modo": documento.modo_extraccion.value,
                "pag": documento.paginas,
                "chars": json.dumps(documento.chars_por_pagina)
                if documento.chars_por_pagina
                else None,
                "score": documento.extraccion_score,
                "identidad": json.dumps(documento.identidad, ensure_ascii=False)
                if documento.identidad
                else None,
            },
        ).scalar_one()
        resultado.versiones_creadas += 1
        resultado.version_ids.append(version_id)

        resultado.unidades_creadas += self._persistir_unidades(version_id, documento)
        self._controlar_cobertura(captura, documento, version_id, resultado)

    def _documento_id(self, source_id: str, documento: DocumentoExtraido) -> tuple[uuid.UUID, bool]:
        if documento.external_id:
            existente = self.conexion.execute(
                text("SELECT id FROM documentos WHERE source_id = :s AND external_id = :e"),
                {"s": source_id, "e": documento.external_id},
            ).scalar_one_or_none()
            if existente is not None:
                return existente, False
        nuevo = self.conexion.execute(
            text(
                "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
                "VALUES (:s, :t, :titulo, :e) RETURNING id"
            ),
            {
                "s": source_id,
                "t": documento.tipo.value,
                "titulo": documento.titulo,
                "e": documento.external_id,
            },
        ).scalar_one()
        return nuevo, True

    def _persistir_unidades(self, version_id: uuid.UUID, documento: DocumentoExtraido) -> int:
        ids: dict[int, uuid.UUID] = {}
        for indice, unidad in enumerate(documento.unidades):
            padre = ids.get(unidad.padre_indice) if unidad.padre_indice is not None else None
            nuevo = self.conexion.execute(
                text(
                    "INSERT INTO unidades_documentales ("
                    "  doc_version_id, parent_id, tipo, numero, sufijo, rotulo, ruta, orden, "
                    "  texto, inicio, fin, pagina_desde, pagina_hasta, rol_contenido"
                    ") VALUES (:dv, :padre, :tipo, :numero, :sufijo, :rotulo, :ruta, :orden, "
                    "          :texto, :inicio, :fin, :pd, :ph, :rol) RETURNING id"
                ),
                {
                    "dv": version_id,
                    "padre": padre,
                    "tipo": unidad.tipo.value,
                    "numero": unidad.numero,
                    "sufijo": unidad.sufijo,
                    "rotulo": unidad.rotulo,
                    "ruta": unidad.ruta,
                    "orden": unidad.orden,
                    "texto": unidad.texto,
                    "inicio": unidad.inicio,
                    "fin": unidad.fin,
                    "pd": unidad.pagina_desde,
                    "ph": unidad.pagina_hasta,
                    "rol": unidad.rol_contenido.value,
                },
            ).scalar_one()
            ids[indice] = nuevo
        return len(ids)

    def _controlar_cobertura(
        self,
        captura: dict,
        documento: DocumentoExtraido,
        version_id: uuid.UUID,
        resultado: ResultadoPersistencia,
    ) -> None:
        """Registra el control DQ06 y abre incidencia si quedó texto afuera."""
        clasificados = sum(len(u.texto) for u in documento.unidades)
        total = len(documento.texto)
        cobertura = clasificados / total if total else 0.0
        pasa = cobertura >= COBERTURA_MINIMA or not documento.unidades

        self.conexion.execute(
            text(
                "INSERT INTO controles_calidad "
                "(corrida_id, control_id, version, resultado, severidad, observado, esperado) "
                "SELECT c.corrida_id, 'DQ06', :ver, :res, :sev, :obs, :esp "
                "FROM capturas c WHERE c.id = :cap"
            ),
            {
                "ver": VERSION_EXTRACTOR,
                "res": "PASA" if pasa else "FALLA",
                "sev": Severidad.MEDIUM.value if pasa else Severidad.HIGH.value,
                "obs": json.dumps(
                    {
                        "doc_version_id": str(version_id),
                        "cobertura": round(cobertura, 4),
                        "unidades": len(documento.unidades),
                        "caracteres_totales": total,
                    }
                ),
                "esp": json.dumps({"cobertura_minima": COBERTURA_MINIMA}),
                "cap": captura["id"],
            },
        )
        if not pasa:
            self._abrir_incidencia(
                captura["source_id"],
                TipoIncidencia.COBERTURA_EXTRACCION,
                Severidad.HIGH,
                f"La versión {version_id} clasificó el {cobertura:.0%} del texto. "
                "Queda texto sin unidad asignada: publicar sobre esta versión sería "
                "publicar sobre un texto incompleto.",
                resultado,
            )
        if documento.avisos:
            for aviso in documento.avisos:
                self._abrir_incidencia(
                    captura["source_id"],
                    TipoIncidencia.COBERTURA_EXTRACCION,
                    Severidad.MEDIUM,
                    aviso,
                    resultado,
                )

    def _persistir_candidatas(
        self, source_id: str, extraccion: ResultadoExtraccion, resultado: ResultadoPersistencia
    ) -> None:
        """Las URLs descubiertas entran como candidatas, no como fuentes.

        Promoverlas es una decisión de revisión: un enlace en un texto no prueba
        que sea una fuente del alcance.
        """
        for descubierta in extraccion.urls_descubiertas:
            creada = self.conexion.execute(
                text(
                    "INSERT INTO fuentes_candidatas "
                    "(source_id_origen, url, relacion, tipo_esperado, estado) "
                    "VALUES (:s, :u, :rel, :tipo, :estado) "
                    "ON CONFLICT (source_id_origen, url) DO NOTHING RETURNING id"
                ),
                {
                    "s": source_id,
                    "u": descubierta.url,
                    "rel": descubierta.relacion,
                    "tipo": descubierta.tipo_esperado,
                    "estado": EstadoFuenteCandidata.NUEVA.value,
                },
            ).scalar_one_or_none()
            resultado.candidatas_creadas += int(creada is not None)

    def _abrir_incidencia(
        self,
        source_id: str,
        tipo: TipoIncidencia,
        severidad: Severidad,
        descripcion: str,
        resultado: ResultadoPersistencia,
    ) -> None:
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(source_id, tipo, severidad, estado, descripcion, responsable_rol) "
                "VALUES (:s, :t, :sev, 'ABIERTA', :d, 'curacion_juridica')"
            ),
            {"s": source_id, "t": tipo.value, "sev": severidad.value, "d": descripcion},
        )
        resultado.incidencias_creadas += 1
