"""Contrato común de los adaptadores de extracción.

Un adaptador recibe bytes ya capturados y devuelve documentos con sus unidades.
No accede a la red, no decide vigencia y no publica nada: eso corresponde a
otras capas. Trabajar sobre bytes guardados es lo que hace la extracción
reproducible.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Protocol

from backend_normativo.curacion.segmentacion import UnidadSegmentada
from backend_normativo.db.vocabularios import (
    ModoExtraccion,
    RolUrl,
    Severidad,
    TipoDocumento,
    TipoFecha,
    TipoIncidencia,
    TipoVersionDocumento,
)


@dataclass(frozen=True)
class Aviso:
    """Algo que la extracción encontró y que necesita decisión humana.

    Lleva tipo y severidad porque termina siendo una incidencia: sin eso, todo
    lo que el extractor observa se archiva bajo la misma etiqueta y la cola de
    revisión deja de poder priorizarse.
    """

    texto: str
    tipo: TipoIncidencia = TipoIncidencia.COBERTURA_EXTRACCION
    severidad: Severidad = Severidad.MEDIUM

    def __str__(self) -> str:
        return self.texto


@dataclass(frozen=True)
class CapturaMaterial:
    """Lo que el adaptador necesita saber de una captura."""

    source_id: str
    url_final: str
    contenido: bytes
    mime: str | None
    sha256: str
    config: dict = field(default_factory=dict)

    def texto(self) -> str:
        """Contenido decodificado con el juego de caracteres que declara.

        Se resuelve acá y no en cada adaptador: una tilde corrompida hace que el
        segmentador no reconozca "Artículo" y pierda la unidad entera.
        """
        from backend_normativo.ingesta.adaptadores.html import decodificar_html

        return decodificar_html(self.contenido, charset_declarado=self.charset)

    @property
    def charset(self) -> str | None:
        if not self.mime:
            return None
        for parte in self.mime.split(";"):
            clave, _, valor = parte.partition("=")
            if clave.strip().lower() == "charset":
                return valor.strip().strip('"') or None
        return None


# Relaciones que declaran que una URL descubierta es una vista de la **misma**
# fuente, y no un recurso nuevo cuyo alcance haya que decidir. Solo estas las
# promueve `bn ingesta descubrir` sin intervención.
#
# Viven acá y no escritas a mano en cada lado porque la promoción las busca por
# texto: si el adaptador cambia la frase y el comando no, las candidatas dejan
# de promoverse y nada falla —simplemente no pasa nada, que es la forma más
# silenciosa de romperse—.
RELACION_MISMA_NORMA = "de la misma norma"
RELACION_HOJA_INDICE = "hoja del índice"
RELACION_FICHA_TRAMITE = "ficha de trámite"
RELACIONES_PROMOVIBLES: tuple[str, ...] = (
    RELACION_MISMA_NORMA,
    RELACION_HOJA_INDICE,
    RELACION_FICHA_TRAMITE,
)


@dataclass
class UrlDescubierta:
    """URL encontrada dentro de una captura.

    El descubrimiento es acotado: cada URL nace de una evidencia concreta y
    declara qué relación tiene con la fuente que la produjo.
    """

    url: str
    rol: RolUrl
    relacion: str
    tipo_esperado: str | None = None


@dataclass
class DocumentoExtraido:
    tipo: TipoDocumento
    tipo_version: TipoVersionDocumento
    modo_extraccion: ModoExtraccion
    texto: str
    unidades: list[UnidadSegmentada] = field(default_factory=list)
    titulo: str | None = None
    external_id: str | None = None
    fecha_documento: dt.date | None = None
    tipo_fecha: TipoFecha = TipoFecha.DESCONOCIDA
    paginas: int | None = None
    chars_por_pagina: dict[str, int] | None = None
    # Señal técnica de la extracción, no un juicio sobre el contenido.
    extraccion_score: float | None = None
    # Identidad normativa candidata. Son candidatos: la resolución de identidad
    # es otra capa y puede rechazarlos.
    identidad: dict[str, object] = field(default_factory=dict)
    avisos: list[Aviso] = field(default_factory=list)


@dataclass
class ResultadoExtraccion:
    documentos: list[DocumentoExtraido] = field(default_factory=list)
    urls_descubiertas: list[UrlDescubierta] = field(default_factory=list)
    avisos: list[Aviso] = field(default_factory=list)


class Adaptador(Protocol):
    """Familia técnica de extracción."""

    nombre: str

    def acepta(self, captura: CapturaMaterial) -> bool:
        """Si este adaptador puede trabajar con esta captura."""
        ...

    def extraer(self, captura: CapturaMaterial) -> ResultadoExtraccion: ...


def calcular_score(
    *, caracteres_clasificados: int, caracteres_totales: int, unidades: int
) -> float:
    """Puntuación técnica de una extracción.

    Combina dos señales observables: cuánto del texto quedó dentro de una unidad
    y si se reconoció alguna estructura. No dice nada sobre si el contenido es
    correcto, está vigente o significa lo que parece.
    """
    if caracteres_totales <= 0:
        return 0.0
    cobertura = min(1.0, caracteres_clasificados / caracteres_totales)
    estructura = 1.0 if unidades else 0.0
    return round(0.7 * cobertura + 0.3 * estructura, 4)
