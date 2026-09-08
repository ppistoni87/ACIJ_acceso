"""HU-F23 · AT-032: a qué unidad de la versión nueva corresponde una de la vieja.

Una regla se cita contra el artículo que la dice. Cuando el texto se consolida,
ese contenido puede quedar en otro lugar: el artículo 10 pasa a ser el 9, o un
inciso corre un lugar porque arriba se agregó un párrafo. Buscar por número
devuelve entonces el texto equivocado, y lo devuelve con toda confianza.

En el Decreto 1382/2001, entre el texto original y el actualizado, el inciso 1
del artículo 10 corre del ordinal 61 al 62. En el texto viejo el 62 era el inciso
2: quien resuelva «la unidad 62 del artículo 10» obtiene «tener cónyuge» en una
versión y «ser beneficiario del SIJP» en la otra. Y el artículo 3 conserva su
número con otro texto, que es el caso más silencioso: la cita sigue apuntando a
un artículo que existe, sólo que ya no dice lo mismo.

Por eso la correspondencia se registra y se aprueba, y sólo una correspondencia
aprobada redirige una cita. Una derivada automáticamente es una propuesta: dos
párrafos con el mismo texto en dos artículos distintos se emparejan solos y
nadie los revisó.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import EstadoRevision, TipoEvidencia
from backend_normativo.monitoreo.diff import _comparar

# El diff distingue por qué dos unidades se corresponden; acá eso se traduce al
# vocabulario de la tabla. Una división o una fusión no se derivan solas: que un
# artículo se haya partido en dos es una lectura, no una coincidencia de texto.
TIPO_POR_CLASE = {"DESPLAZADA": "RENUMERACION", "MODIFICADA": "SUSTITUCION"}

ESTADOS_QUE_REDIRIGEN = (EstadoRevision.APPROVED.value, EstadoRevision.PUBLISHED.value)


class NormaSinDosVersiones(Exception):
    """No hay dos versiones de la misma norma que comparar."""


@dataclass
class Correspondencia:
    origen_ruta: str
    destino_ruta: str
    tipo: str
    motivo: str
    cambio_de_articulo: bool


@dataclass
class ResultadoEquivalencias:
    norma_id: uuid.UUID | None = None
    origen_version_id: uuid.UUID | None = None
    destino_version_id: uuid.UUID | None = None
    renumeraciones: int = 0
    sustituciones: int = 0
    ya_registradas: int = 0
    cambian_de_articulo: int = 0
    sin_destino: int = 0
    sin_origen: int = 0
    avisos: list[str] = field(default_factory=list)


def _articulo(ruta: str) -> str | None:
    """El tramo de artículo de una ruta, si lo tiene.

    `titulo-II/articulo-10/inciso-1-61` es el inciso 1 del artículo 10. Que la
    ruta entera cambie no dice si cambió el artículo o sólo el ordinal de
    adentro, y las dos cosas se leen distinto.
    """
    for tramo in ruta.split("/"):
        if tramo.startswith("articulo"):
            return tramo
    return None


def derivar(viejas: dict[str, tuple[str, str]], nuevas: dict[str, tuple[str, str]]):
    """Las correspondencias que se desprenden de comparar dos textos."""
    correspondencias: list[Correspondencia] = []
    sin_destino = sin_origen = 0
    for cambio in _comparar(viejas, nuevas):
        tipo = TIPO_POR_CLASE.get(cambio.clase)
        if tipo is None:
            sin_destino += int(cambio.clase == "ELIMINADA")
            sin_origen += int(cambio.clase == "AGREGADA")
            continue
        destino = cambio.ruta_nueva or cambio.ruta
        articulo_viejo, articulo_nuevo = _articulo(cambio.ruta), _articulo(destino)
        cambio_de_articulo = articulo_viejo != articulo_nuevo
        if tipo == "RENUMERACION":
            motivo = f"Mismo texto en otra ubicación: {cambio.ruta} → {destino}." + (
                f" Cambia de artículo ({articulo_viejo} → {articulo_nuevo})."
                if cambio_de_articulo
                else " Corre el ordinal dentro del mismo artículo."
            )
        else:
            motivo = f"Misma ubicación con otro texto: {destino}. Similitud {cambio.similitud}."
        correspondencias.append(
            Correspondencia(
                origen_ruta=cambio.ruta,
                destino_ruta=destino,
                tipo=tipo,
                motivo=motivo,
                cambio_de_articulo=cambio_de_articulo,
            )
        )
    return correspondencias, sin_destino, sin_origen


class CuradorDeEquivalencias:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def derivar_para_norma(self, norma_id: uuid.UUID) -> ResultadoEquivalencias:
        """Compara las dos últimas versiones conocidas de la norma."""
        filas = self.conexion.execute(
            text(
                "SELECT nv.doc_version_id, nv.tipo_version, dv.version "
                "  FROM norma_versiones nv "
                "  JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                "  JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
                " WHERE nv.norma_id = :n "
                " ORDER BY rv.numero_version, dv.version"
            ),
            {"n": norma_id},
        ).all()
        if len(filas) < 2:
            raise NormaSinDosVersiones(
                f"La norma {norma_id} tiene {len(filas)} versión(es) documentales. Una "
                "correspondencia necesita dos textos para compararse; no se infiere de uno."
            )
        return self.derivar_entre(norma_id, filas[-2][0], filas[-1][0])

    def derivar_entre(
        self, norma_id: uuid.UUID, origen_version_id: uuid.UUID, destino_version_id: uuid.UUID
    ) -> ResultadoEquivalencias:
        resultado = ResultadoEquivalencias(
            norma_id=norma_id,
            origen_version_id=origen_version_id,
            destino_version_id=destino_version_id,
        )
        viejas = self._unidades(origen_version_id)
        nuevas = self._unidades(destino_version_id)
        if not viejas or not nuevas:
            resultado.avisos.append(
                "Alguna de las dos versiones no tiene unidades dispositivas extraídas: sin "
                "texto segmentado no hay nada que corresponder."
            )
            return resultado

        ids_viejas = self._ids(origen_version_id)
        ids_nuevas = self._ids(destino_version_id)

        correspondencias, resultado.sin_destino, resultado.sin_origen = derivar(viejas, nuevas)
        for c in correspondencias:
            origen_id, destino_id = ids_viejas.get(c.origen_ruta), ids_nuevas.get(c.destino_ruta)
            if origen_id is None or destino_id is None or origen_id == destino_id:
                continue
            evidencia_id = self._evidencia(destino_version_id, destino_id, nuevas[c.destino_ruta])
            nueva = self._registrar(origen_id, destino_id, evidencia_id, c)
            if not nueva:
                resultado.ya_registradas += 1
                continue
            resultado.cambian_de_articulo += int(c.cambio_de_articulo)
            if c.tipo == "RENUMERACION":
                resultado.renumeraciones += 1
            else:
                resultado.sustituciones += 1

        self._avisos(resultado)
        return resultado

    # --- Internos -----------------------------------------------------------

    def _avisos(self, resultado: ResultadoEquivalencias) -> None:
        total = resultado.renumeraciones + resultado.sustituciones
        if total:
            resultado.avisos.append(
                f"{total} correspondencia(s) quedan como candidatas. Una correspondencia sin "
                "aprobar no redirige ninguna cita: dos párrafos con el mismo texto en dos "
                "artículos distintos se emparejan solos y nadie los revisó."
            )
        if resultado.cambian_de_articulo:
            resultado.avisos.append(
                f"{resultado.cambian_de_articulo} de ellas cambian de artículo, no sólo de "
                "ordinal. Son las que hay que mirar primero: una cita al artículo viejo "
                "devuelve otro artículo."
            )
        if resultado.sin_destino:
            resultado.avisos.append(
                f"{resultado.sin_destino} unidad(es) del texto viejo no tienen correspondencia "
                "en el nuevo. Quedan sin equivalencia: que un texto haya desaparecido no "
                "significa que su contenido esté en otro lado."
            )
        if resultado.sin_origen:
            resultado.avisos.append(
                f"{resultado.sin_origen} unidad(es) del texto nuevo no vienen de ninguna del "
                "viejo: son contenido agregado, no una renumeración."
            )

    def _unidades(self, version_id: uuid.UUID) -> dict[str, tuple[str, str]]:
        return {
            f["ruta"]: (f["tipo"], f["texto"])
            for f in self.conexion.execute(
                text(
                    "SELECT ruta, tipo, texto FROM unidades_documentales "
                    " WHERE doc_version_id = :v AND rol_contenido = 'DISPOSITIVO'"
                ),
                {"v": version_id},
            ).mappings()
        }

    def _ids(self, version_id: uuid.UUID) -> dict[str, uuid.UUID]:
        return {
            f["ruta"]: f["id"]
            for f in self.conexion.execute(
                text(
                    "SELECT id, ruta FROM unidades_documentales "
                    " WHERE doc_version_id = :v AND rol_contenido = 'DISPOSITIVO'"
                ),
                {"v": version_id},
            ).mappings()
        }

    def _evidencia(
        self, version_id: uuid.UUID, unidad_id: uuid.UUID, unidad: tuple[str, str]
    ) -> uuid.UUID:
        """La evidencia es el texto de la unidad de destino, en su propia versión.

        Lo que sostiene la correspondencia es que ese texto está ahí; el selector
        nombra la unidad, no su posición.
        """
        fragmento = unidad[1]
        selector = f"equivalencia:{unidad_id}"
        ya = self.conexion.execute(
            # Puede haber más de una: la evidencia es inmutable y varios
            # curadores citan la misma unidad con el mismo selector. Se toma la
            # más antigua para que la elección no dependa del orden de carga;
            # pedir exactamente una detiene el comando entero por un empate que
            # no cambia nada de lo que se afirma.
            text(
                "SELECT id FROM evidencias WHERE doc_version_id = :v AND selector = :s "
                " ORDER BY creado_en, id LIMIT 1"
            ),
            {"v": version_id, "s": selector},
        ).scalar_one_or_none()
        if ya is not None:
            return ya
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, selector, tipo, "
                " hash_fragmento) VALUES (:v, :u, :f, :s, :t, :h) RETURNING id"
            ),
            {
                "v": version_id,
                "u": unidad_id,
                "f": fragmento,
                "s": selector,
                "t": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
            },
        ).scalar_one()

    def _registrar(
        self,
        origen_id: uuid.UUID,
        destino_id: uuid.UUID,
        evidencia_id: uuid.UUID,
        c: Correspondencia,
    ) -> bool:
        insertado = self.conexion.execute(
            text(
                "INSERT INTO equivalencias_unidades (origen_unidad_id, destino_unidad_id, "
                " evidencia_id, tipo, motivo, estado_revision) "
                "VALUES (:o, :d, :e, :t, :m, :estado) "
                "ON CONFLICT (origen_unidad_id, destino_unidad_id, tipo) DO NOTHING RETURNING id"
            ),
            {
                "o": origen_id,
                "d": destino_id,
                "e": evidencia_id,
                "t": c.tipo,
                "m": c.motivo,
                # Derivada, no comprobada. Aprobarla es una decisión con nombre.
                "estado": EstadoRevision.CANDIDATE.value,
            },
        ).scalar_one_or_none()
        return insertado is not None


def resolver(
    conexion: Connection, unidad_id: uuid.UUID, *, en_version: uuid.UUID
) -> uuid.UUID | None:
    """A qué unidad de `en_version` corresponde `unidad_id`, si está comprobado.

    Devuelve `None` cuando no hay correspondencia aprobada. Eso es lo correcto:
    ante la duda, la cita se responde con la unidad que efectivamente se citó y
    con su versión, no con la que hoy ocupa ese número.
    """
    if _misma_version(conexion, unidad_id, en_version):
        return unidad_id
    return conexion.execute(
        text(
            "SELECT eq.destino_unidad_id FROM equivalencias_unidades eq "
            "  JOIN unidades_documentales u ON u.id = eq.destino_unidad_id "
            " WHERE eq.origen_unidad_id = :o AND u.doc_version_id = :v "
            "   AND eq.estado_revision = ANY(:estados) "
            " LIMIT 1"
        ),
        {"o": unidad_id, "v": en_version, "estados": list(ESTADOS_QUE_REDIRIGEN)},
    ).scalar_one_or_none()


def _misma_version(conexion: Connection, unidad_id: uuid.UUID, version_id: uuid.UUID) -> bool:
    return (
        conexion.execute(
            text("SELECT doc_version_id FROM unidades_documentales WHERE id = :u"),
            {"u": unidad_id},
        ).scalar_one_or_none()
        == version_id
    )


def aprobar(conexion: Connection, equivalencia_id: uuid.UUID, *, actor: str, decision: str) -> None:
    """Una correspondencia aprobada redirige citas: la aprueba alguien, con motivo."""
    if not actor.strip() or len(decision.strip()) < 15:
        raise ValueError(
            "Aprobar una equivalencia exige actor y un fundamento de al menos 15 caracteres: "
            "es la decisión de que una cita vieja se responda con otro texto."
        )
    actualizadas = conexion.execute(
        text(
            "UPDATE equivalencias_unidades SET estado_revision = :aprobado, "
            " motivo = motivo || :nota WHERE id = :id AND estado_revision = :candidato"
        ),
        {
            "id": equivalencia_id,
            "aprobado": EstadoRevision.APPROVED.value,
            "candidato": EstadoRevision.CANDIDATE.value,
            "nota": f" · Aprobada por {actor.strip()}: {decision.strip()}",
        },
    ).rowcount
    if not actualizadas:
        raise ValueError(
            f"La equivalencia {equivalencia_id} no existe o no está pendiente de revisión."
        )
