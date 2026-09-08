"""HU-019: trámites, sus pasos y lo que exigen.

Toma las fichas ya extraídas —la identidad candidata que dejó el adaptador— y
las convierte en trámites con pasos citables. La regla que gobierna el módulo es
la misma que en el resto del corpus: **lo que la ficha no dice no se completa**.

Una duración vacía no es «inmediato» y un costo vacío no es «gratuito». Los dos
son la respuesta que más rápido se convierte en un reclamo, porque quien
pregunta actúa sobre ella. Cuando la ficha no informa, el trámite se carga igual
con ese campo vacío y la ausencia queda como incidencia con su responsable.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EntidadVersionada,
    EstadoOperativo,
    EstadoRevision,
    PublicoTramite,
    Severidad,
    TipoEvidencia,
    TipoIncidencia,
    TipoOrganismo,
    ValidTipo,
)

JURISDICCION = "AR"


@dataclass
class ResultadoTramites:
    fichas_leidas: int = 0
    tramites_creados: int = 0
    tramites_conocidos: int = 0
    pasos_creados: int = 0
    sin_costo: int = 0
    sin_duracion: int = 0
    sin_pasos: int = 0
    avisos: list[str] = field(default_factory=list)


class CargadorTramites:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def cargar(self, source_id: str | None = None) -> ResultadoTramites:
        resultado = ResultadoTramites()
        for fila in self._fichas(source_id):
            ficha = (fila["identidad_candidata"] or {}).get("tramite")
            if not ficha:
                continue
            resultado.fichas_leidas += 1
            self._cargar_una(fila, ficha, resultado)
        self._avisos(resultado)
        return resultado

    # --- Internos -----------------------------------------------------------

    def _fichas(self, source_id: str | None):
        return (
            self.conexion.execute(
                text(
                    "SELECT dv.id AS doc_version_id, d.source_id, d.titulo, "
                    "       dv.identidad_candidata "
                    "  FROM documento_versiones dv JOIN documentos d ON d.id = dv.documento_id "
                    " WHERE d.tipo = 'PROCEDIMIENTO' "
                    "   AND dv.identidad_candidata ? 'tramite' "
                    "   AND (CAST(:s AS text) IS NULL OR d.source_id = :s) "
                    " ORDER BY d.source_id, dv.version"
                ),
                {"s": source_id},
            )
            .mappings()
            .all()
        )

    def _cargar_una(self, fila, ficha: dict, resultado: ResultadoTramites) -> None:
        titulo = (ficha.get("titulo") or fila["titulo"] or "").strip()
        if not titulo:
            return
        codigo = f"{fila['source_id']}.{_slug(titulo)}"
        organismo_id = self._organismo(fila["source_id"])

        tramite_id = self.conexion.execute(
            text("SELECT id FROM tramites WHERE codigo = :c"), {"c": codigo}
        ).scalar_one_or_none()
        if tramite_id is None:
            tramite_id = self.conexion.execute(
                text(
                    "INSERT INTO tramites (organismo_id, codigo, titulo, publico) "
                    "VALUES (:o, :c, :t, :p) RETURNING id"
                ),
                {
                    "o": organismo_id,
                    "c": codigo,
                    "t": titulo[:500],
                    # `publico` es el eje ciudadano/institucional, no el texto
                    # de «¿a quién está dirigido?». Deducirlo de esa frase sería
                    # adivinar; el texto se conserva en la descripción de la
                    # versión, que es donde la ficha lo dice.
                    "p": PublicoTramite.NO_INFORMADO.value,
                },
            ).scalar_one()
            resultado.tramites_creados += 1
        else:
            resultado.tramites_conocidos += 1

        costo = _valor(ficha.get("costo"))
        duracion = _valor(ficha.get("duracion"))
        pasos = ficha.get("pasos") or []
        if costo is None:
            resultado.sin_costo += 1
        if duracion is None:
            resultado.sin_duracion += 1
        if not pasos:
            resultado.sin_pasos += 1

        version_id, es_nueva = self._version(tramite_id, fila["doc_version_id"], ficha, duracion)
        if es_nueva:
            # Los pasos cuelgan de la versión: si la versión ya estaba, sus
            # pasos también, y volver a insertarlos los duplicaría.
            resultado.pasos_creados += self._pasos(version_id, fila["doc_version_id"], pasos)
        self._incidencias(fila["source_id"], titulo, costo, duracion, pasos)

    def _organismo(self, source_id: str) -> uuid.UUID:
        nombre = self.conexion.execute(
            text("SELECT nombre FROM fuentes WHERE source_id = :s"), {"s": source_id}
        ).scalar_one_or_none()
        return self.conexion.execute(
            text(
                "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) VALUES (:j, :n, :t) "
                "ON CONFLICT (jurisdiccion_id, nombre, tipo) DO UPDATE SET nombre = :n "
                "RETURNING id"
            ),
            {
                "j": JURISDICCION,
                "n": (nombre or source_id)[:300],
                "t": TipoOrganismo.PRESTADOR.value,
            },
        ).scalar_one()

    def _version(
        self,
        tramite_id: uuid.UUID,
        doc_version_id: uuid.UUID,
        ficha: dict,
        duracion: str | None,
    ) -> tuple[uuid.UUID, bool]:
        ya = self.conexion.execute(
            text(
                "SELECT registro_version_id FROM tramite_versiones "
                " WHERE tramite_id = :t AND doc_version_id = :d"
            ),
            {"t": tramite_id, "d": doc_version_id},
        ).scalar_one_or_none()
        if ya is not None:
            return ya, False

        registro = self.conexion.execute(
            text(
                "UPDATE registro_versiones SET known_hasta = now() "
                " WHERE entidad_tipo = :tipo AND entidad_id = :eid AND known_hasta IS NULL"
            ),
            {"tipo": EntidadVersionada.TRAMITE.value, "eid": tramite_id},
        )
        siguiente = self.conexion.execute(
            text(
                "SELECT coalesce(max(numero_version), 0) + 1 FROM registro_versiones "
                " WHERE entidad_tipo = :tipo AND entidad_id = :eid"
            ),
            {"tipo": EntidadVersionada.TRAMITE.value, "eid": tramite_id},
        ).scalar_one()
        del registro

        version_id = self.conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo) VALUES (:tipo, :eid, :nv, :estado, :vt) "
                "RETURNING id"
            ),
            {
                "tipo": EntidadVersionada.TRAMITE.value,
                "eid": tramite_id,
                "nv": siguiente,
                "estado": EstadoRevision.CANDIDATE.value,
                "vt": ValidTipo.DESCONOCIDO.value,
            },
        ).scalar_one()

        self.conexion.execute(
            text(
                "INSERT INTO tramite_versiones (registro_version_id, tramite_id, doc_version_id, "
                " descripcion, cta_url, duracion_texto, estado_operativo) "
                "VALUES (:rv, :t, :d, :desc, :cta, :dur, :estado)"
            ),
            {
                "rv": version_id,
                "t": tramite_id,
                "d": doc_version_id,
                "desc": ficha.get("dirigido"),
                "cta": ficha.get("cta_url"),
                # Vacío es vacío: la ficha no dijo cuánto tarda y nadie lo
                # completa con «inmediato».
                "dur": duracion,
                "estado": EstadoOperativo.NO_INFORMADO.value,
            },
        )
        return version_id, True

    def _pasos(self, version_id: uuid.UUID, doc_version_id: uuid.UUID, pasos: list) -> int:
        creados = 0
        for orden, paso in enumerate(pasos, start=1):
            texto = (paso.get("texto") or "").strip() if isinstance(paso, dict) else str(paso)
            if not texto:
                continue
            detalle = paso.get("detalle") or [] if isinstance(paso, dict) else []
            evidencia_id = self._evidencia(doc_version_id, orden, texto)
            self.conexion.execute(
                text(
                    "INSERT INTO tramite_pasos (tramite_version_id, evidencia_id, orden, "
                    " accion, documentacion) VALUES (:tv, :e, :o, :a, :doc)"
                ),
                {
                    "tv": version_id,
                    "e": evidencia_id,
                    "o": orden,
                    "a": texto,
                    # Las aclaraciones del paso no se pierden ni se convierten
                    # en pasos propios: son detalle del paso que las contiene.
                    "doc": "\n".join(detalle) or None,
                },
            )
            creados += 1
        return creados

    def _evidencia(self, doc_version_id: uuid.UUID, orden: int, texto: str) -> uuid.UUID:
        ya = self.conexion.execute(
            text("SELECT id FROM evidencias WHERE doc_version_id = :d AND selector = :s"),
            {"d": doc_version_id, "s": f"paso:{orden}"},
        ).scalar_one_or_none()
        if ya is not None:
            return ya
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, fragmento, selector, tipo, "
                " hash_fragmento) VALUES (:dv, :f, :s, :t, :h) RETURNING id"
            ),
            {
                "dv": doc_version_id,
                "f": texto,
                "s": f"paso:{orden}",
                "t": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "h": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            },
        ).scalar_one()

    def _incidencias(
        self,
        source_id: str,
        titulo: str,
        costo: str | None,
        duracion: str | None,
        pasos: list,
    ) -> None:
        faltan = [
            nombre
            for nombre, valor in (
                ("costo", costo),
                ("duración", duracion),
                ("pasos", pasos or None),
            )
            if not valor
        ]
        if not faltan:
            return
        descripcion = (
            f"La ficha de «{titulo}» no informa {', '.join(faltan)}. Se carga el trámite con "
            "esos campos vacíos: asignar cero, «gratuito» o «inmediato» sin evidencia "
            "explícita produce una respuesta sobre la que alguien va a actuar."
        )
        ya = self.conexion.execute(
            text("SELECT 1 FROM incidencias_revision WHERE source_id = :s AND descripcion = :d"),
            {"s": source_id, "d": descripcion},
        ).first()
        if ya is not None:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, source_id, "
                " descripcion, responsable_rol) "
                "VALUES (:t, :sev, 'ABIERTA', :s, :d, 'analisis funcional')"
            ),
            {
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "sev": Severidad.MEDIUM.value,
                "s": source_id,
                "d": descripcion,
            },
        )

    def _avisos(self, resultado: ResultadoTramites) -> None:
        if resultado.sin_costo or resultado.sin_duracion:
            resultado.avisos.append(
                f"{resultado.sin_costo} ficha(s) sin costo informado y "
                f"{resultado.sin_duracion} sin duración. Quedan vacíos: no se asigna cero, "
                "«gratuito» ni «inmediato» sin evidencia explícita."
            )
        if resultado.sin_pasos:
            resultado.avisos.append(
                f"{resultado.sin_pasos} ficha(s) sin pasos reconocibles. El trámite queda "
                "registrado y la capacidad de procedimiento no se publica sobre él."
            )


def _valor(bruto) -> str | None:
    limpio = " ".join(str(bruto or "").split())
    return limpio or None


def _slug(texto: str) -> str:
    """Código estable y legible; el esquema lo exige en mayúsculas."""
    tabla = str.maketrans("ÁÉÍÓÚÜÑ ", "AEIOUUN-")
    limpio = texto.upper().translate(tabla)
    return "".join(c for c in limpio if c.isalnum() or c in "-_.")[:80].strip("-")
