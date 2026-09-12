"""Sacar el marcado HTML que quedó dentro del texto de unidades ya extraídas.

Hay fuentes que publican su HTML escapado dentro de la propia página: el texto
visible de la norma trae `<p>` como contenido. El extractor lo limpia desde
`extraccion@15`, pero las unidades extraídas antes se quedaron con las etiquetas
adentro, y DQ10 —con razón— no deja publicar un corte que las arrastre.

Esto aplica exactamente la misma función que el extractor, así que el texto
queda igual que si el documento se volviera a extraer. No se vuelve a extraer
porque eso crea una versión nueva del documento y de la norma, y detrás cuelga
toda la curación: reglas, evidencias y beneficios apuntando a la versión
anterior. Cambiar el texto de una unidad de staging no toca ninguna de esas
referencias.

**Las evidencias no se tocan, y es a propósito.** Son inmutables por diseño —hay
un disparador que lo impide— y lo que citan es lo que la fuente publicó, con su
marcado y todo. Después de limpiar, el fragmento citado ya no es un calco del
texto de la unidad: la evidencia sigue siendo fiel al documento original y la
unidad queda como lo que se sirve. La divergencia es esa y conviene tenerla
escrita; el informe la cuenta cada vez.

Sobre un corte ya publicado esto no corre: ahí el texto no se toca (D-124), y
por eso el filtro mira sólo unidades cuyas versiones todavía no se publicaron.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.ingesta.extraccion import ETIQUETAS_CONOCIDAS, limpiar_marcado

# Unidades con marcado que todavía no forman parte de un corte publicado. La
# condición de estado es la que hace que esto no pueda tocar lo que ya se sirve.
# La lista de etiquetas sale del extractor y no se copia: si mañana aprende una
# nueva, esto la busca sin que nadie se acuerde de venir a tocarla.
CANDIDATAS = f"""
SELECT u.id, u.texto,
       (SELECT count(*) FROM evidencias e WHERE e.unidad_id = u.id) AS evidencias
  FROM unidades_documentales u
  JOIN documento_versiones dv ON dv.id = u.doc_version_id
  JOIN norma_versiones nv ON nv.doc_version_id = dv.id
  JOIN registro_versiones rv ON rv.id = nv.registro_version_id
 WHERE rv.estado_revision <> 'PUBLISHED'
   AND u.texto ~ '</?({ETIQUETAS_CONOCIDAS})( [^<>]*)?/?>'
"""


@dataclass
class ResultadoLimpieza:
    unidades: int = 0
    limpiadas: int = 0
    evidencias_que_quedan_con_marcado: int = 0
    simulada: bool = False
    avisos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {
            "unidades_con_marcado": self.unidades,
            "limpiadas": self.limpiadas,
            "evidencias_que_quedan_con_marcado": self.evidencias_que_quedan_con_marcado,
            "simulada": self.simulada,
        }


def limpiar(
    conexion: Connection, *, actor: str, fundamento: str, simular: bool = False
) -> ResultadoLimpieza:
    """Aplica la limpieza del extractor a las unidades que quedaron con marcado."""
    if not fundamento.strip():
        raise ValueError(
            "Limpiar el texto de una unidad sin fundamento deja un cambio de contenido sin "
            "razón escrita. Es texto de una norma: tiene que poder explicarse."
        )
    filas = conexion.execute(text(CANDIDATAS)).mappings().all()
    resultado = ResultadoLimpieza(unidades=len(filas), simulada=simular)

    for fila in filas:
        limpio, hubo_cambio = limpiar_marcado(fila["texto"])
        resultado.evidencias_que_quedan_con_marcado += int(fila["evidencias"])
        if not hubo_cambio:
            # La expresión encontró algo que la limpieza no saca: conviene
            # saberlo en vez de contarlo como resuelto.
            resultado.avisos.append(
                f"La unidad {fila['id']} tiene marcado que la limpieza no quita."
            )
            continue
        resultado.limpiadas += 1
        if simular:
            continue
        conexion.execute(
            text("UPDATE unidades_documentales SET texto = :t WHERE id = :id"),
            {"t": limpio, "id": fila["id"]},
        )
        conexion.execute(
            text(
                "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
                "VALUES (:actor, 'LIMPIAR_MARCADO', 'unidades_documentales', :id, :motivo)"
            ),
            {"actor": actor, "id": str(fila["id"]), "motivo": fundamento},
        )
    return resultado
