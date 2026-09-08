"""Jurisdicciones de referencia.

Los identificadores son los códigos ISO 3166-2:AR, que son estables y públicos.
Usarlos evita el problema que advierte el diccionario: municipios homónimos en
provincias distintas, o "Buenos Aires" refiriéndose a la provincia en un lado y
a la ciudad en otro.

Los municipios no se cargan acá: entran cuando una fuente los aporta, colgando
de su provincia.
"""

from __future__ import annotations

from typing import NamedTuple

from backend_normativo.db.vocabularios import NivelJurisdiccion


class JurisdiccionSemilla(NamedTuple):
    id: str
    nombre: str
    nivel: NivelJurisdiccion
    parent_id: str | None
    codigo_oficial: str | None


NACION = JurisdiccionSemilla("AR", "República Argentina", NivelJurisdiccion.NACIONAL, None, "AR")

PROVINCIAS: tuple[JurisdiccionSemilla, ...] = tuple(
    JurisdiccionSemilla(codigo, nombre, nivel, "AR", codigo)
    for codigo, nombre, nivel in (
        ("AR-A", "Salta", NivelJurisdiccion.PROVINCIAL),
        ("AR-B", "Buenos Aires", NivelJurisdiccion.PROVINCIAL),
        ("AR-C", "Ciudad Autónoma de Buenos Aires", NivelJurisdiccion.CIUDAD_AUTONOMA),
        ("AR-D", "San Luis", NivelJurisdiccion.PROVINCIAL),
        ("AR-E", "Entre Ríos", NivelJurisdiccion.PROVINCIAL),
        ("AR-F", "La Rioja", NivelJurisdiccion.PROVINCIAL),
        ("AR-G", "Santiago del Estero", NivelJurisdiccion.PROVINCIAL),
        ("AR-H", "Chaco", NivelJurisdiccion.PROVINCIAL),
        ("AR-J", "San Juan", NivelJurisdiccion.PROVINCIAL),
        ("AR-K", "Catamarca", NivelJurisdiccion.PROVINCIAL),
        ("AR-L", "La Pampa", NivelJurisdiccion.PROVINCIAL),
        ("AR-M", "Mendoza", NivelJurisdiccion.PROVINCIAL),
        ("AR-N", "Misiones", NivelJurisdiccion.PROVINCIAL),
        ("AR-P", "Formosa", NivelJurisdiccion.PROVINCIAL),
        ("AR-Q", "Neuquén", NivelJurisdiccion.PROVINCIAL),
        ("AR-R", "Río Negro", NivelJurisdiccion.PROVINCIAL),
        ("AR-S", "Santa Fe", NivelJurisdiccion.PROVINCIAL),
        ("AR-T", "Tucumán", NivelJurisdiccion.PROVINCIAL),
        ("AR-U", "Chubut", NivelJurisdiccion.PROVINCIAL),
        (
            "AR-V",
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
            NivelJurisdiccion.PROVINCIAL,
        ),
        ("AR-W", "Corrientes", NivelJurisdiccion.PROVINCIAL),
        ("AR-X", "Córdoba", NivelJurisdiccion.PROVINCIAL),
        ("AR-Y", "Jujuy", NivelJurisdiccion.PROVINCIAL),
        ("AR-Z", "Santa Cruz", NivelJurisdiccion.PROVINCIAL),
    )
)

SEMILLA: tuple[JurisdiccionSemilla, ...] = (NACION, *PROVINCIAS)
