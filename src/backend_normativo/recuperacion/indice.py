"""Construir el índice semántico de un corte publicado.

P-012 criterio 1. Se indexa lo que el corte sirve y nada más: los fragmentos que
el publicador dejó en `chunks` para ese release. No hay forma de indexar
staging, porque un vector cuelga de un índice y un índice cuelga de un release.

Reconstruir es barato y es lo que se hace: los vectores son datos derivados del
texto publicado. Lo que no se hace es actualizar en el lugar sin mirar, porque
entonces un fragmento cuyo texto cambió se quedaría con su vector viejo. Por eso
cada vector guarda el hash del texto que embebió y la reconstrucción compara.
"""

from __future__ import annotations

import dataclasses
import uuid

from sqlalchemy import Connection, text

from backend_normativo.recuperacion.embeddings import Embebedor, en_lotes, hash_de

LOTE = 64


@dataclasses.dataclass
class ResultadoIndice:
    indice_id: uuid.UUID | None = None
    release_id: uuid.UUID | None = None
    modelo: str = ""
    fragmentos: int = 0
    embebidos: int = 0
    reusados: int = 0
    vencidos: int = 0
    avisos: list[str] = dataclasses.field(default_factory=list)

    @property
    def completo(self) -> bool:
        return self.fragmentos > 0 and self.embebidos + self.reusados == self.fragmentos


class Indexador:
    def __init__(self, conexion: Connection, embebedor: Embebedor) -> None:
        self.conexion = conexion
        self.embebedor = embebedor

    def _release_publicado(self, release_id: uuid.UUID | None) -> uuid.UUID | None:
        if release_id is not None:
            fila = self.conexion.execute(
                text("SELECT id FROM releases WHERE id = :r AND estado = 'PUBLICADO'"),
                {"r": release_id},
            ).one_or_none()
            return fila.id if fila else None
        fila = self.conexion.execute(
            text(
                "SELECT id FROM releases WHERE estado = 'PUBLICADO' "
                "ORDER BY publicado_en DESC LIMIT 1"
            )
        ).one_or_none()
        return fila.id if fila else None

    def construir(self, release_id: uuid.UUID | None = None) -> ResultadoIndice:
        """Deja el índice del corte al día. Devuelve qué hizo y qué no pudo."""
        resultado = ResultadoIndice(modelo=self.embebedor.modelo)

        publicado = self._release_publicado(release_id)
        if publicado is None:
            resultado.avisos.append(
                "No hay ningún corte publicado que indexar. El índice semántico se "
                "construye sobre lo publicado: indexar staging serviría como citable "
                "algo que todavía no lo es."
            )
            return resultado
        resultado.release_id = publicado

        indice_id = self.conexion.execute(
            text(
                "INSERT INTO indices_semanticos (release_id, modelo, dimension, normalizacion) "
                "VALUES (:r, :m, :d, 'L2') "
                "ON CONFLICT (release_id, modelo) DO UPDATE SET construido_en = now() "
                "RETURNING id"
            ),
            {"r": publicado, "m": self.embebedor.modelo, "d": self.embebedor.dimension},
        ).scalar_one()
        resultado.indice_id = indice_id

        fragmentos = (
            self.conexion.execute(
                text(
                    "SELECT c.id, c.texto, c.hash, v.hash_texto AS hash_vector "
                    "  FROM chunks c "
                    "  LEFT JOIN fragmento_vectores v "
                    "         ON v.chunk_id = c.id AND v.indice_id = :i "
                    " WHERE c.release_id = :r "
                    " ORDER BY c.id"
                ),
                {"i": indice_id, "r": publicado},
            )
            .mappings()
            .all()
        )
        resultado.fragmentos = len(fragmentos)

        # Un vector sigue sirviendo si el texto que embebió es el mismo. El hash
        # que se compara es el del texto de verdad, recalculado acá: el de la
        # columna `chunks.hash` lo escribió el publicador y comparar contra él
        # daría por bueno un vector cuando lo que cambió fue el texto y no el
        # hash declarado.
        pendientes = []
        for fila in fragmentos:
            actual = hash_de(fila["texto"])
            if fila["hash_vector"] == actual:
                resultado.reusados += 1
                continue
            if fila["hash_vector"] is not None:
                resultado.vencidos += 1
            pendientes.append((fila["id"], fila["texto"], actual))

        for lote in en_lotes(pendientes, LOTE):
            vectores = self.embebedor.embeber([texto for _, texto, _ in lote])
            self.conexion.execute(
                text(
                    "INSERT INTO fragmento_vectores (indice_id, chunk_id, hash_texto, vector) "
                    "VALUES (:i, :c, :h, :v) "
                    "ON CONFLICT (indice_id, chunk_id) DO UPDATE "
                    "SET hash_texto = excluded.hash_texto, vector = excluded.vector"
                ),
                [
                    {
                        "i": indice_id,
                        "c": chunk_id,
                        "h": hash_texto,
                        "v": str(vector),
                    }
                    for (chunk_id, _, hash_texto), vector in zip(lote, vectores, strict=True)
                ],
            )
            resultado.embebidos += len(lote)

        # Los vectores de fragmentos que ya no están en el corte se van: el
        # índice no puede devolver algo que el corte dejó de servir.
        sobrantes = self.conexion.execute(
            text(
                "DELETE FROM fragmento_vectores v "
                " WHERE v.indice_id = :i "
                "   AND NOT EXISTS (SELECT 1 FROM chunks c "
                "                    WHERE c.id = v.chunk_id AND c.release_id = :r) "
                "RETURNING v.chunk_id"
            ),
            {"i": indice_id, "r": publicado},
        ).fetchall()
        if sobrantes:
            resultado.avisos.append(
                f"Se quitaron {len(sobrantes)} vector(es) de fragmentos que ya no están "
                "en el corte."
            )

        self.conexion.execute(
            text(
                "UPDATE indices_semanticos SET fragmentos = "
                "  (SELECT count(*) FROM fragmento_vectores WHERE indice_id = :i) "
                "WHERE id = :i"
            ),
            {"i": indice_id},
        )

        if resultado.vencidos:
            resultado.avisos.append(
                f"{resultado.vencidos} fragmento(s) tenían un vector calculado sobre un "
                "texto que ya no es el suyo y se volvieron a embeber."
            )
        return resultado


def formatear(resultado: ResultadoIndice) -> str:
    lineas = [
        "# Índice semántico",
        "",
        f"- Corte: `{resultado.release_id or '—'}`",
        f"- Modelo: `{resultado.modelo}`",
        f"- Fragmentos en el corte: **{resultado.fragmentos}**",
        f"- Embebidos en esta corrida: {resultado.embebidos}",
        f"- Reusados (el texto no cambió): {resultado.reusados}",
    ]
    for aviso in resultado.avisos:
        lineas += ["", aviso]
    return "\n".join(lineas)
