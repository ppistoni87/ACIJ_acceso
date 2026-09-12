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
    # Lo que este corte hereda del anterior. Un corte es una foto completa de lo
    # servible, no el delta de esta corrida: si fuera el delta, publicar los
    # puntos de atención dejaría a la API sin una sola norma que citar.
    chunks_heredados: int = 0
    vectores_heredados: int = 0
    eventos_emitidos: int = 0
    en_cuarentena: list[dict] = field(default_factory=list)
    gates: ResultadoGates | None = None
    # Versiones que salen publicadas con todas sus afirmaciones todavía sin
    # aprobar. No impide publicar —una versión puede no tener nada informado que
    # aprobar—, pero se avisa: la publicación promueve las afirmaciones
    # aprobadas, así que publicar antes de aprobarlas deja el release sin
    # evidencia que citar, y la ficha se sirve sin una sola cita.
    sin_afirmaciones_aprobadas: list[uuid.UUID] = field(default_factory=list)


class Publicador:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def candidatos(self) -> list[uuid.UUID]:
        """Versiones aprobadas, verificadas, con vigencia resuelta y sin conflictos.

        La fecha de verificación no es un requisito de este método: es una
        invariante de la base —`estado_revision <> 'PUBLISHED' OR (release_id IS
        NOT NULL AND verificado_en IS NOT NULL)`, desde la primera migración— y
        acá no se conocía. El resultado era que `bn publicacion estado` contaba
        14.390 candidatos con los ocho gates en verde y publicar reventaba con
        una violación de CHECK a mitad de la transacción. Peor que el error: el
        informe afirmaba que se podía publicar un corpus que no se podía servir.

        La invariante es buena y por eso se respeta en vez de relajarse. Una
        dirección o un teléfono que nadie confirmó contra la fuente no debería
        llegar a la pantalla de alguien que los va a usar hoy.
        """
        return list(
            self.conexion.execute(
                text(
                    "SELECT rv.id FROM registro_versiones rv "
                    " WHERE rv.estado_revision = 'APPROVED' "
                    "   AND rv.verificado_en IS NOT NULL "
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

    def sin_afirmaciones_aprobadas(self, candidatos: list[uuid.UUID]) -> list[uuid.UUID]:
        """Candidatas que tienen afirmaciones candidatas y ninguna aprobada.

        Es el orden que se equivoca solo: aprobar los siete campos después de
        publicar no sirve de nada, porque lo que promueve las afirmaciones a
        PUBLISHED es la publicación. La versión queda publicada y su ficha se
        sirve sin evidencia, que es indistinguible de una norma sin respaldo.
        """
        if not candidatos:
            return []
        return list(
            self.conexion.execute(
                text(
                    "SELECT rv.id FROM registro_versiones rv "
                    " WHERE rv.id = ANY(:ids) "
                    "   AND EXISTS (SELECT 1 FROM afirmaciones a "
                    "                WHERE a.registro_version_id = rv.id "
                    "                  AND a.estado_revision = 'CANDIDATE') "
                    "   AND NOT EXISTS (SELECT 1 FROM afirmaciones a "
                    "                    WHERE a.registro_version_id = rv.id "
                    "                      AND a.estado_revision = 'APPROVED')"
                ),
                {"ids": [str(c) for c in candidatos]},
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
                    "       rv.verificado_en, "
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
            if fila["verificado_en"] is None:
                # Con el motivo escrito, y no sólo ausente de la lista de
                # candidatos: quien lee el estado tiene que poder saber qué
                # falta hacer, que acá es verificar contra la fuente.
                motivos.append("sin fecha de verificación")
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
        # Se mira antes de promover: después de publicar, todas las aprobadas ya
        # figuran como publicadas y la pregunta no se puede hacer.
        resultado.sin_afirmaciones_aprobadas = self.sin_afirmaciones_aprobadas(candidatos)

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

        anterior = self._corte_anterior(release_id)
        if anterior is not None:
            resultado.chunks_heredados = self._heredar_fragmentos(release_id, anterior, candidatos)
            resultado.vectores_heredados = self._heredar_vectores(release_id, anterior)
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
        """Huella de lo que el corte sirve entero, no de lo que agrega.

        Un corte no es su delta. El segundo release incorpora B y sigue
        sirviendo A —el primero conserva sus versiones, y por eso las dos cosas
        se recuperan después del segundo—, así que un manifiesto que solo
        nombrara B no identificaría lo que el corte sirve: dos corpus distintos
        con el mismo agregado tendrían la misma huella.

        Se cuentan las versiones que van a quedar publicadas: las que este corte
        promueve más las que ya lo estaban en un release todavía publicado. Un
        release revertido no aporta, porque dejó de servir.
        """
        ya_publicadas = (
            self.conexion.execute(
                text(
                    "SELECT rv.id FROM registro_versiones rv "
                    "  JOIN releases r ON r.id = rv.release_id "
                    " WHERE rv.estado_revision = 'PUBLISHED' AND r.estado = 'PUBLICADO'"
                )
            )
            .scalars()
            .all()
        )
        todas = {str(c) for c in candidatos} | {str(v) for v in ya_publicadas}
        contenido = json.dumps(sorted(todas)).encode("utf-8")
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

    def _corte_anterior(self, release_id: uuid.UUID) -> uuid.UUID | None:
        """El último corte publicado antes de éste, si lo hay."""
        return self.conexion.execute(
            text(
                "SELECT id FROM releases "
                " WHERE estado = 'PUBLICADO' AND id <> :r "
                " ORDER BY publicado_en DESC LIMIT 1"
            ),
            {"r": release_id},
        ).scalar_one_or_none()

    def _heredar_fragmentos(
        self, release_id: uuid.UUID, anterior: uuid.UUID, candidatos: list[uuid.UUID]
    ) -> int:
        """Trae al corte nuevo lo que el anterior servía y sigue vigente.

        Un corte es la foto completa de lo servible en un momento, no el delta
        de esta corrida. La diferencia no era teórica: `release_vigente`
        devuelve el corte publicado más reciente y la búsqueda filtra los
        fragmentos por ese corte, así que un segundo corte armado sólo con sus
        candidatos —por ejemplo, uno que incorporara los puntos de atención—
        dejaba a la API contestando «no hay nada publicado» sobre un corpus que
        seguía entero. Sin error, sin gate en rojo y sin una línea en los logs.

        No se arrastra lo que esta corrida reemplaza: si entre los candidatos
        viene una versión nueva de la misma entidad, la vieja no viaja. Servir
        las dos sería mezclar dos textos de la misma norma en la misma
        respuesta.
        """
        heredados = (
            self.conexion.execute(
                text(
                    "INSERT INTO chunks (unidad_id, registro_version_id, release_id, texto, "
                    "                    hash, tipo, url_fuente) "
                    "SELECT c.unidad_id, c.registro_version_id, :nuevo, c.texto, c.hash, "
                    "       c.tipo, c.url_fuente "
                    "  FROM chunks c "
                    "  JOIN registro_versiones rv ON rv.id = c.registro_version_id "
                    " WHERE c.release_id = :anterior "
                    "   AND rv.estado_revision = 'PUBLISHED' "
                    "   AND NOT EXISTS ("
                    "     SELECT 1 FROM registro_versiones nueva "
                    "      WHERE nueva.id = ANY(:v) "
                    "        AND nueva.entidad_tipo = rv.entidad_tipo "
                    "        AND nueva.entidad_id = rv.entidad_id) "
                    "ON CONFLICT (release_id, unidad_id, hash) DO NOTHING "
                    "RETURNING id"
                ),
                {"nuevo": release_id, "anterior": anterior, "v": candidatos},
            )
            .scalars()
            .all()
        )
        return len(heredados)

    def _heredar_vectores(self, release_id: uuid.UUID, anterior: uuid.UUID) -> int:
        """Y el índice semántico de lo heredado, sin volver a embeber nada.

        El vector es una función del texto y del modelo: si el fragmento viaja
        con el mismo hash, su vector sigue siendo el suyo. Recalcularlos exigiría
        cargar el modelo dentro de la transacción de publicación, que es lo
        último que uno quiere ahí; no copiarlos dejaría el corte nuevo con
        búsqueda sólo léxica y nadie lo notaría hasta medir la recuperación.
        """
        self.conexion.execute(
            text(
                "INSERT INTO indices_semanticos (release_id, modelo, dimension, normalizacion) "
                "SELECT :nuevo, i.modelo, i.dimension, i.normalizacion "
                "  FROM indices_semanticos i WHERE i.release_id = :anterior "
                "ON CONFLICT (release_id, modelo) DO NOTHING"
            ),
            {"nuevo": release_id, "anterior": anterior},
        )
        copiados = (
            self.conexion.execute(
                text(
                    "INSERT INTO fragmento_vectores (indice_id, chunk_id, hash_texto, vector) "
                    "SELECT ni.id, nc.id, v.hash_texto, v.vector "
                    "  FROM fragmento_vectores v "
                    "  JOIN indices_semanticos oi ON oi.id = v.indice_id "
                    "   AND oi.release_id = :anterior "
                    "  JOIN indices_semanticos ni ON ni.release_id = :nuevo "
                    "   AND ni.modelo = oi.modelo "
                    "  JOIN chunks oc ON oc.id = v.chunk_id "
                    "  JOIN chunks nc ON nc.release_id = :nuevo "
                    "   AND nc.unidad_id = oc.unidad_id AND nc.hash = oc.hash "
                    "ON CONFLICT DO NOTHING "
                    "RETURNING chunk_id"
                ),
                {"nuevo": release_id, "anterior": anterior},
            )
            .scalars()
            .all()
        )
        self.conexion.execute(
            text(
                "UPDATE indices_semanticos i SET fragmentos = ("
                "  SELECT count(*) FROM fragmento_vectores v WHERE v.indice_id = i.id) "
                " WHERE i.release_id = :nuevo"
            ),
            {"nuevo": release_id},
        )
        return len(copiados)

    def _construir_chunks(self, release_id: uuid.UUID, candidatos: list[uuid.UUID]) -> int:
        """Fragmentos citables de lo publicado.

        Solo se indexa texto dispositivo: una nota editorial o un texto citado
        dentro de otro artículo no es la norma, y recuperarlo como si lo fuera
        haría que una respuesta cite algo que la norma no dice.
        """
        creados = (
            self.conexion.execute(
                text(
                    # `tsv` no se escribe: desde la 0013 es columna generada a
                    # partir de `texto`. Antes la escribía este INSERT y podía
                    # quedar distinta del texto que decía representar.
                    "INSERT INTO chunks (unidad_id, registro_version_id, release_id, texto, hash, "
                    "                    tipo, url_fuente) "
                    # La URL se copia al fragmento en el momento de publicar.
                    # El publicador corre con el rol migrador y sí alcanza
                    # staging; el lector no, y no tiene por qué: el corte le
                    # lleva la cita ya resuelta.
                    "SELECT u.id, nv.registro_version_id, :r, u.texto, "
                    "       encode(sha256(u.texto::bytea), 'hex'), :tipo, fu.url "
                    "  FROM unidades_documentales u "
                    "  JOIN norma_versiones nv ON nv.doc_version_id = u.doc_version_id "
                    "  LEFT JOIN documento_versiones dv ON dv.id = u.doc_version_id "
                    "  LEFT JOIN capturas cap ON cap.id = dv.captura_id "
                    "  LEFT JOIN fuente_urls fu ON fu.id = cap.source_url_id "
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
