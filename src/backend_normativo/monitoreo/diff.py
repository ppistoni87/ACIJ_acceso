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
    ruta_nueva: str | None = None

    @property
    def clase(self) -> str:
        if self.ruta_nueva is not None:
            return "DESPLAZADA"
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
        """Un desplazamiento no es un cambio de la norma.

        Cuando se agrega un párrafo, todas las rutas posteriores corren un
        lugar. Contar eso como texto modificado inundaría la cola de revisión
        con decenas de cambios falsos por cada inserción real.
        """
        return any(c.clase != "DESPLAZADA" for c in self.cambios)

    @property
    def sustantivos(self) -> list[CambioDeUnidad]:
        return [c for c in self.cambios if c.clase != "DESPLAZADA"]

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
    diferencia.cambios.extend(_comparar(viejas, nuevas))
    return diferencia


def _comparar(
    viejas: dict[str, tuple[str, str]], nuevas: dict[str, tuple[str, str]]
) -> list[CambioDeUnidad]:
    """Compara primero por contenido y recién después por ruta.

    Las rutas llevan un ordinal para que dos unidades sin número no colisionen,
    y ese ordinal corre cuando se inserta un párrafo. Comparar solo por ruta
    haría que agregar tres párrafos al Decreto 1382/2001 produjera 81 cambios:
    39 «eliminadas» y 42 «agregadas» que son el mismo texto un lugar más abajo.
    Emparejando primero por texto idéntico, lo que queda son los cambios que de
    verdad ocurrieron.
    """
    resto_viejo = {r: v for r, v in viejas.items() if nuevas.get(r, (None, None))[1] != v[1]}
    resto_nuevo = {r: v for r, v in nuevas.items() if viejas.get(r, (None, None))[1] != v[1]}

    # 1. Misma unidad en otra ruta: se movió, no cambió.
    por_texto: dict[str, list[str]] = {}
    for ruta, (_, texto) in resto_nuevo.items():
        por_texto.setdefault(texto, []).append(ruta)

    cambios: list[CambioDeUnidad] = []
    for ruta in sorted(resto_viejo):
        tipo, texto = resto_viejo[ruta]
        candidatas = por_texto.get(texto)
        if not candidatas:
            continue
        destino = candidatas.pop(0)
        cambios.append(
            CambioDeUnidad(ruta=ruta, tipo=tipo, antes=texto, despues=texto, ruta_nueva=destino)
        )
        del resto_viejo[ruta]
        del resto_nuevo[destino]

    # 2. Misma ruta con otro texto: se reescribió.
    for ruta in sorted(set(resto_viejo) & set(resto_nuevo)):
        cambios.append(
            CambioDeUnidad(
                ruta=ruta,
                tipo=resto_nuevo[ruta][0],
                antes=resto_viejo[ruta][1],
                despues=resto_nuevo[ruta][1],
            )
        )

    # 3. Lo que queda entró o salió de verdad.
    for ruta in sorted(set(resto_viejo) - set(resto_nuevo)):
        tipo, texto = resto_viejo[ruta]
        cambios.append(CambioDeUnidad(ruta=ruta, tipo=tipo, antes=texto, despues=None))
    for ruta in sorted(set(resto_nuevo) - set(resto_viejo)):
        tipo, texto = resto_nuevo[ruta]
        cambios.append(CambioDeUnidad(ruta=ruta, tipo=tipo, antes=None, despues=texto))
    return sorted(cambios, key=lambda c: c.ruta)
