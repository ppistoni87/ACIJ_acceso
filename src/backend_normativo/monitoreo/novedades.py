"""Corrida de monitoreo: revalidar, comparar y propagar.

Revalidar una fuente y encontrar el mismo hash no cierra el tema. La
especificación es explícita: para páginas normativas cuyo texto tarda en
consolidarse hay que consultar también las normas modificatorias. Por eso la
corrida informa por separado lo que cambió y lo que sigue pendiente de
verificar por otra vía.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.ingesta.capturador import Capturador, PermisoDePoliticaDenegado
from backend_normativo.ingesta.extraccion import Extractor
from backend_normativo.ingesta.planificador import fuentes_pendientes
from backend_normativo.monitoreo.diff import comparar_versiones
from backend_normativo.monitoreo.impacto import propagar


@dataclass
class ResultadoMonitoreo:
    fuentes_revisadas: int = 0
    sin_cambios: int = 0
    con_cambios: int = 0
    bloqueadas: int = 0
    versiones_nuevas: int = 0
    normas_impactadas: int = 0
    eventos_emitidos: int = 0
    detalle: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def correr(
    conexion: Connection,
    *,
    capturador: Capturador,
    extractor: Extractor,
    limite: int | None = None,
    ahora: dt.datetime | None = None,
) -> ResultadoMonitoreo:
    ahora = ahora or dt.datetime.now(dt.UTC)
    resultado = ResultadoMonitoreo()

    for fuente in fuentes_pendientes(conexion, ahora=ahora, limite=limite):
        resultado.fuentes_revisadas += 1
        try:
            captura = capturador.capturar_fuente(fuente.source_id)
        except (PermisoDePoliticaDenegado, LookupError) as exc:
            resultado.bloqueadas += 1
            resultado.avisos.append(f"{fuente.source_id}: {exc}")
            continue

        if captura.rechazadas:
            resultado.bloqueadas += 1

        extraccion = extractor.extraer_pendientes(fuente.source_id)
        resultado.versiones_nuevas += extraccion.versiones_creadas

        cambios_de_la_fuente: list[dict] = []
        for version_id in extraccion.version_ids:
            diferencia = comparar_versiones(conexion, version_id)
            if diferencia is None or not diferencia.hay_cambios:
                continue
            cambios_de_la_fuente.append(
                {
                    "doc_version_id": str(version_id),
                    "resumen": diferencia.resumen,
                    "unidades": [
                        {"ruta": c.ruta, "clase": c.clase, "similitud": c.similitud}
                        for c in diferencia.cambios[:20]
                    ],
                }
            )
            norma_id = conexion.execute(
                text("SELECT norma_id FROM norma_versiones WHERE doc_version_id = :v"),
                {"v": version_id},
            ).scalar_one_or_none()
            if norma_id is None:
                continue
            impacto = propagar(
                conexion,
                norma_id,
                motivo=(
                    f"La fuente {fuente.source_id} publicó un texto distinto: {diferencia.resumen}."
                ),
                idempotency_key=f"cambio:{version_id}",
            )
            resultado.normas_impactadas += 1
            resultado.eventos_emitidos += impacto.eventos_emitidos

        if cambios_de_la_fuente:
            resultado.con_cambios += 1
            resultado.detalle.append(
                {"source_id": fuente.source_id, "cambios": cambios_de_la_fuente}
            )
        else:
            resultado.sin_cambios += 1

    if resultado.sin_cambios:
        resultado.avisos.append(
            f"{resultado.sin_cambios} fuente(s) devolvieron el mismo texto. Eso no prueba "
            "que nada haya cambiado: una norma modificatoria publicada en otro boletín "
            "afecta a la modificada aunque su página no se toque."
        )
    return resultado
