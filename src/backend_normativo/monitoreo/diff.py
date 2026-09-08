"""HU-026 y HU-027: qué cambió entre dos versiones de un documento.

Un hash distinto dice que algo cambió, no qué. Y un hash igual no prueba que
nada haya cambiado en el mundo: un boletín puede tardar en consolidar un texto,
y una norma modificatoria publicada hoy afecta a la modificada aunque su página
no se toque.

Por eso el diff compara unidades y no páginas, y la revalidación de una fuente
no cierra el tema: las normas que la citan también se revisan.
"""

from __future__ import annotations

import difflib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text


@dataclass
class CambioDeUnidad:
    ruta: str
    tipo: str
    antes: str | None
    despues: str | None

    @property
    def clase(self) -> str:
        if self.antes is None:
            return "AGREGADA"
        if self.despues is None:
            return "ELIMINADA"
        return "MODIFICADA"

    @property
    def similitud(self) -> float:
        if self.antes is None or self.despues is None:
            return 0.0
        return round(difflib.SequenceMatcher(None, self.antes, self.despues).ratio(), 4)


@dataclass
class Diferencia:
    documento_id: uuid.UUID
    version_anterior: uuid.UUID | None
    version_nueva: uuid.UUID
    cambios: list[CambioDeUnidad] = field(default_factory=list)

    @property
    def hay_cambios(self) -> bool:
        return bool(self.cambios)

    @property
    def resumen(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for cambio in self.cambios:
            conteo[cambio.clase] = conteo.get(cambio.clase, 0) + 1
        return conteo


def comparar_versiones(conexion: Connection, version_nueva: uuid.UUID) -> Diferencia | None:
    """Compara una versión documental con la anterior del mismo documento.

    Solo se comparan unidades dispositivas: un cambio de maquetación o de nota
    editorial no es un cambio en la norma, y tratarlo como tal llenaría la cola
    de revisión de ruido.
    """
    fila = (
        conexion.execute(
            text("SELECT dv.documento_id, dv.version FROM documento_versiones dv WHERE dv.id = :v"),
            {"v": version_nueva},
        )
        .mappings()
        .first()
    )
    if fila is None:
        return None

    anterior = conexion.execute(
        text(
            "SELECT id FROM documento_versiones "
            " WHERE documento_id = :d AND version < :n ORDER BY version DESC LIMIT 1"
        ),
        {"d": fila["documento_id"], "n": fila["version"]},
    ).scalar_one_or_none()

    diferencia = Diferencia(
        documento_id=fila["documento_id"],
        version_anterior=anterior,
        version_nueva=version_nueva,
    )
    if anterior is None:
        return diferencia

    def unidades(version_id: uuid.UUID) -> dict[str, tuple[str, str]]:
        return {
            f["ruta"]: (f["tipo"], f["texto"])
            for f in conexion.execute(
                text(
                    "SELECT ruta, tipo, texto FROM unidades_documentales "
                    " WHERE doc_version_id = :v AND rol_contenido = 'DISPOSITIVO'"
                ),
                {"v": version_id},
            ).mappings()
        }

    viejas, nuevas = unidades(anterior), unidades(version_nueva)
    for ruta in sorted(set(viejas) | set(nuevas)):
        vieja = viejas.get(ruta)
        nueva = nuevas.get(ruta)
        if vieja and nueva and vieja[1] == nueva[1]:
            continue
        diferencia.cambios.append(
            CambioDeUnidad(
                ruta=ruta,
                tipo=(nueva or vieja)[0],
                antes=vieja[1] if vieja else None,
                despues=nueva[1] if nueva else None,
            )
        )
    return diferencia
