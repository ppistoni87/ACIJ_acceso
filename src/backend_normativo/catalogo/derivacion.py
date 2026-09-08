"""Traducción del vocabulario del manifiesto al del esquema.

El manifiesto describe cada fuente con el vocabulario del manual (técnicas de
extracción, estados de relevamiento). El esquema usa vocabularios controlados.
La correspondencia se declara acá, en un solo lugar y de forma explícita, para
que se pueda auditar y discutir: cada valor derivado queda además registrado en
el reporte de conciliación junto con la señal que lo produjo.

Nada de esto inventa información. Cuando una señal no alcanza para decidir, el
resultado es el valor menos comprometido (`OTRA`, `SIN_ADAPTADOR`,
`NO_VERIFICADO`) y no una suposición.
"""

from __future__ import annotations

import datetime as dt

from backend_normativo.catalogo.manifiesto import FuenteManifiesto
from backend_normativo.db import vocabularios as voc

# --- Adaptador ---------------------------------------------------------------
# `adapter_hint` mezcla familia técnica y estado de relevamiento. Solo la parte
# técnica se traduce a un adaptador; el resto queda sin adaptador asignado
# porque todavía no hay contrato de extracción que ejecutar.
ADAPTADOR_POR_PISTA: dict[str, voc.Adaptador] = {
    "DATASET ABIERTO": voc.Adaptador.DATASET_ABIERTO,
    "ENDPOINT JSON": voc.Adaptador.API_JSON,
    "HTML ESTATICO": voc.Adaptador.HTML_ESTATICO,
    "NORMATIVE_HTML": voc.Adaptador.HTML_ESTATICO,
    "PDF": voc.Adaptador.PDF,
    "PDF CON TEXTO": voc.Adaptador.PDF,
    "MANUAL_OR_LINK_ONLY": voc.Adaptador.CARGA_MANUAL,
    # Descartada, pendiente de identificar o pendiente de descubrir el índice
    # público: no hay adaptador que correr todavía.
    "DESCARTAR": voc.Adaptador.SIN_ADAPTADOR,
    "DISCOVERY_REQUIRED": voc.Adaptador.SIN_ADAPTADOR,
    "DISCOVER_PUBLIC_INDEX": voc.Adaptador.SIN_ADAPTADOR,
}

# --- Clase -------------------------------------------------------------------
# La clase describe qué es la fuente, no cómo se la lee. Se deduce de las tablas
# destino que el manifiesto le asigna, tomando la primera coincidencia en este
# orden de especificidad.
CLASE_POR_TABLA_DESTINO: tuple[tuple[str, voc.ClaseFuente], ...] = (
    ("barrios_renabap", voc.ClaseFuente.PADRON),
    ("normas", voc.ClaseFuente.PORTAL_NORMATIVO),
    ("norma_versiones", voc.ClaseFuente.PORTAL_NORMATIVO),
    ("relaciones_normativas", voc.ClaseFuente.PORTAL_NORMATIVO),
    ("norma_identificadores", voc.ClaseFuente.PORTAL_NORMATIVO),
    ("equivalencias_unidades", voc.ClaseFuente.PORTAL_NORMATIVO),
    ("tramites", voc.ClaseFuente.FICHA_TRAMITE),
    ("tramite_pasos", voc.ClaseFuente.FICHA_TRAMITE),
    ("puntos_atencion", voc.ClaseFuente.DIRECTORIO),
    ("canales", voc.ClaseFuente.CANAL_ATENCION),
    ("parametro_valores", voc.ClaseFuente.DOCUMENTO),
    ("documentos", voc.ClaseFuente.DOCUMENTO),
    ("documento_versiones", voc.ClaseFuente.DOCUMENTO),
    ("unidades_documentales", voc.ClaseFuente.DOCUMENTO),
    ("fuentes_candidatas", voc.ClaseFuente.DIRECTORIO),
    ("fuentes", voc.ClaseFuente.DIRECTORIO),
    ("fuente_urls", voc.ClaseFuente.DIRECTORIO),
)

# --- Frecuencia de revisión --------------------------------------------------
# Valores iniciales de la especificación §6, en horas. Son configurables por
# fuente y se versionan con la configuración: el TTL del manual es antecedente,
# no una garantía de frescura.
FRECUENCIA_POR_PRIORIDAD_HORAS: dict[voc.Prioridad, int] = {
    voc.Prioridad.P0: 24,
    voc.Prioridad.P1: 24 * 7,
    voc.Prioridad.P2: 24 * 30,
    voc.Prioridad.P3: 24 * 90,
}

# Los monitores de novedades se revisan a diario mientras estén activos.
PREFIJO_MONITOR = "M"


def clase_de(fuente: FuenteManifiesto) -> voc.ClaseFuente:
    if fuente.alias_of:
        return voc.ClaseFuente.ALIAS
    if fuente.adapter_hint == "DATASET ABIERTO":
        return voc.ClaseFuente.DATASET
    if fuente.source_id.startswith(PREFIJO_MONITOR):
        return voc.ClaseFuente.BOLETIN
    destino = set(fuente.target_tables)
    for tabla, clase in CLASE_POR_TABLA_DESTINO:
        if tabla in destino:
            return clase
    return voc.ClaseFuente.OTRA


def adaptador_de(fuente: FuenteManifiesto) -> voc.Adaptador:
    return ADAPTADOR_POR_PISTA.get(fuente.adapter_hint, voc.Adaptador.SIN_ADAPTADOR)


def estado_de(fuente: FuenteManifiesto) -> voc.EstadoFuente:
    """El estado inicial viene del manifiesto y se conserva tal cual.

    Ninguna fuente arranca como `ACTIVE`: activo significa que la ingesta ya
    corrió y funcionó, y este paquete no ingirió nada.
    """
    return voc.EstadoFuente(fuente.initial_state)


def access_status_de(fuente: FuenteManifiesto) -> voc.AccessStatus:
    """Disponibilidad técnica antes de haber tocado la fuente.

    Sin URL conocida el estado es explícito; con URL, sigue sin verificarse: el
    manifiesto la identificó en agosto y eso no acredita que responda hoy.
    """
    if fuente.sin_url_conocida:
        return voc.AccessStatus.SIN_URL_CONOCIDA
    return voc.AccessStatus.NO_VERIFICADO


def motivo_estado_de(fuente: FuenteManifiesto) -> str | None:
    """Un estado de excepción se explica; el resto no necesita motivo."""
    estado = estado_de(fuente)
    if estado not in (
        voc.EstadoFuente.DEGRADED,
        voc.EstadoFuente.QUARANTINED,
        voc.EstadoFuente.RETIRED,
    ):
        return None
    partes = [f"Estado inicial declarado por el manifiesto ({fuente.origin})."]
    if fuente.manual_technique:
        partes.append(f"Técnica registrada en el manual: {fuente.manual_technique}.")
    if fuente.task:
        partes.append(fuente.task)
    return " ".join(partes)


def politica_acceso_de(fuente: FuenteManifiesto) -> voc.PoliticaAcceso:
    return voc.PoliticaAcceso(fuente.access_policy)


def rol_url(indice: int, fuente: FuenteManifiesto) -> voc.RolUrl:
    """La primera URL de una fuente es su entrada; las demás son alternativas
    hasta que la ingesta descubra qué son en realidad."""
    if indice == 0:
        return voc.RolUrl.ENTRADA
    return voc.RolUrl.ALTERNATIVA


def tipo_acceso_de(fuente: FuenteManifiesto, url: str) -> voc.TipoAcceso:
    adaptador = adaptador_de(fuente)
    if adaptador is voc.Adaptador.CARGA_MANUAL:
        return voc.TipoAcceso.CARGA_MANUAL
    if adaptador is voc.Adaptador.API_JSON:
        return voc.TipoAcceso.API_PUBLICA
    if adaptador in (voc.Adaptador.DATASET_ABIERTO, voc.Adaptador.PDF):
        return voc.TipoAcceso.DESCARGA_ARCHIVO
    if url.lower().endswith((".pdf", ".zip", ".csv", ".xlsx")):
        return voc.TipoAcceso.DESCARGA_ARCHIVO
    return voc.TipoAcceso.HTTP_GET_PUBLICO


def ttl_de(fuente: FuenteManifiesto) -> dt.timedelta | None:
    """TTL de frescura, no fecha de vencimiento jurídico."""
    dias = fuente.manual_ttl_days or fuente.default_reverify_days
    return dt.timedelta(days=dias) if dias else None


def frecuencia_de(fuente: FuenteManifiesto) -> dt.timedelta:
    if fuente.source_id.startswith(PREFIJO_MONITOR):
        return dt.timedelta(hours=24)
    ttl = ttl_de(fuente)
    if ttl is not None:
        return ttl
    prioridad = voc.Prioridad(fuente.priority)
    return dt.timedelta(hours=FRECUENCIA_POR_PRIORIDAD_HORAS[prioridad])


def presupuesto_de(fuente: FuenteManifiesto) -> dict[str, object]:
    """Presupuesto por dominio de la especificación §6.

    InfoLEG y NormativaBA se recorren de a una solicitud por vez; el resto
    admite hasta dos cuando el dominio lo permite.
    """
    dominios_conservadores = ("infoleg.gob.ar", "boletinoficial.buenosaires.gob.ar")
    conservador = any(d in url for url in fuente.urls for d in dominios_conservadores)
    return {
        "delay_dominio_s": 2.0,
        "concurrencia": 1 if conservador else 2,
        "reintentos_max": 3,
        "respetar_robots": True,
        "validar_tls": True,
    }
