"""Contrato de respuesta de la API.

Toda respuesta lleva la misma envoltura: qué release la respalda, para qué fecha
y con qué conocimiento se resolvió, si el dato es publicable, qué evidencia lo
sostiene, qué falta y qué advertencias corresponden.

No es ceremonia. Sin `as_of` una respuesta no dice para cuándo vale; sin
`release_id` no se puede reproducir; sin `missing_fields` una abstención es
indistinguible de un "no". El consumidor de esta API es un sistema
conversacional, y lo que no viaje en la respuesta no va a poder decirlo.
"""

from __future__ import annotations

import datetime as dt
import uuid
from contextvars import ContextVar
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from backend_normativo import SCHEMA_VERSION

T = TypeVar("T")


class DataStatus(StrEnum):
    """Qué tan sostenible es lo que devuelve la respuesta."""

    PUBLICADO = "PUBLICADO"
    PARCIAL = "PARCIAL"
    NO_PUBLICABLE = "NO_PUBLICABLE"
    SIN_RESULTADOS = "SIN_RESULTADOS"


class CodigoError(StrEnum):
    """Errores tipados del contrato.

    Información insuficiente es un estado de dominio, no un fallo del servidor:
    nunca se disfraza de 500.
    """

    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    STALE_DATA = "STALE_DATA"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"
    UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    VERSION_CONFLICT = "VERSION_CONFLICT"


class Evidencia(BaseModel):
    """Localizador verificable de una afirmación."""

    model_config = ConfigDict(frozen=True)

    evidencia_id: uuid.UUID
    fragmento: str
    norma: str | None = None
    unidad: str | None = None
    url_fuente: str | None = None
    source_id: str | None = None
    capturado_en: dt.datetime | None = None


class Advertencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: CodigoError
    detalle: str


# Dónde queda anotado el resultado de la respuesta, para que el middleware de
# observabilidad sepa si la consulta se resolvió o se abstuvo, y por qué.
#
# Va por acá y no por diecisiete rutas anotando a mano: toda respuesta pasa por
# esta envoltura, así que es el único lugar donde no se puede olvidar.
#
# El contenedor es un **diccionario que el middleware crea y la respuesta
# muta**, y no un valor que la respuesta asigna. La diferencia importa: Starlette
# corre la ruta en otra tarea, así que un `ContextVar.set()` hecho adentro no
# vuelve al middleware —se probó, y todas las consultas quedaban registradas como
# SIN_CLASIFICAR—. La identidad del objeto sí viaja, y mutarlo se ve de los dos
# lados. Es una variable de contexto y no un global porque el servidor atiende
# consultas en paralelo y mezclarlas daría la medición de otra persona.
_anotacion: ContextVar[dict | None] = ContextVar("bn_anotacion_respuesta", default=None)


def abrir_anotacion() -> dict:
    """Reserva el lugar donde la respuesta de esta consulta va a anotarse."""
    hueco: dict = {}
    _anotacion.set(hueco)
    return hueco


def ultima_respuesta() -> dict | None:
    return _anotacion.get()


class Respuesta(BaseModel, Generic[T]):
    """Envoltura común de toda respuesta."""

    schema_version: str = SCHEMA_VERSION
    release_id: uuid.UUID | None = None
    as_of: dt.date
    known_at: dt.datetime
    data_status: DataStatus
    data: T
    evidence: list[Evidencia] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[Advertencia] = Field(default_factory=list)

    def model_post_init(self, _contexto: object) -> None:
        """Deja anotado el resultado sin que la ruta tenga que acordarse.

        El motivo de una abstención sale de la primera advertencia: son códigos
        tipados —`INSUFFICIENT_EVIDENCE`, `STALE_DATA`, `CONFLICT`— y es
        exactamente lo que el criterio 3 pide para distinguir una abstención
        correcta de una respuesta resuelta. No se guarda el detalle en prosa:
        puede nombrar lo que la persona preguntó.
        """
        hueco = _anotacion.get()
        if hueco is None:
            return
        hueco.update(
            {
                "data_status": self.data_status.value,
                "release_id": str(self.release_id) if self.release_id else None,
                "motivo": self.warnings[0].codigo.value if self.warnings else None,
                "evidencias": len(self.evidence),
            }
        )


class ErrorRespuesta(BaseModel):
    """Cuerpo de un error tipado."""

    schema_version: str = SCHEMA_VERSION
    codigo: CodigoError
    detalle: str
    as_of: dt.date | None = None
    known_at: dt.datetime | None = None
    missing_fields: list[str] = Field(default_factory=list)


# --- Modelos de dominio expuestos --------------------------------------------


class CoberturaDeCampos(BaseModel):
    """Estado de los siete campos pedidos para una versión."""

    model_config = ConfigDict(frozen=True)

    poblacion_destinataria: str = "PENDIENTE"
    criterios_aplicabilidad: str = "PENDIENTE"
    plazos: str = "PENDIENTE"
    criterios_revocacion: str = "PENDIENTE"
    interdependencias: str = "PENDIENTE"
    beneficio_otorgado: str = "PENDIENTE"
    no_descartar: str = "PENDIENTE"


class NormaResumen(BaseModel):
    model_config = ConfigDict(frozen=True)

    norma_id: uuid.UUID
    jurisdiccion: str
    tipo: str
    numero: str | None
    anio: int | None
    titulo: str
    emisor: str | None = None
    identificadores: dict[str, str] = Field(default_factory=dict)
    identidad_incierta: bool = False
    versiones_publicadas: int = 0
    cobertura_de_campos: CoberturaDeCampos | None = None


class RelacionResumen(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: str
    direccion: str
    norma: str
    alcance: str | None = None
    estado_revision: str


class VersionNorma(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: uuid.UUID
    tipo_version: str
    estado_legal_declarado: str | None
    estado_legal_validado: str
    valid_tipo: str
    valid_desde: dt.date | None
    valid_hasta: dt.date | None
    verificado_en: dt.datetime | None
    reverificar_antes_de: dt.datetime | None
    servible: bool
    motivos_no_servible: list[str] = Field(default_factory=list)


class NormaDetalle(BaseModel):
    model_config = ConfigDict(frozen=True)

    norma: NormaResumen
    versiones: list[VersionNorma] = Field(default_factory=list)
    campos: dict[str, dict] = Field(default_factory=dict)
    relaciones: list[RelacionResumen] = Field(default_factory=list)
    referencias_pendientes: list[dict] = Field(default_factory=list)


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limite: int
    desplazamiento: int
