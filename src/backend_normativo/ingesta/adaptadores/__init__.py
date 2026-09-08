"""Adaptadores de extracción: uno por familia técnica.

La especificación es explícita: un adaptador por familia y contratos específicos
por fuente. No 67 scripts aislados con copias divergentes del mismo parser.
"""

from backend_normativo.ingesta.adaptadores.base import (
    Adaptador,
    CapturaMaterial,
    DocumentoExtraido,
    ResultadoExtraccion,
    UrlDescubierta,
)

__all__ = [
    "Adaptador",
    "CapturaMaterial",
    "DocumentoExtraido",
    "ResultadoExtraccion",
    "UrlDescubierta",
]
