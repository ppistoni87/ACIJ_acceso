"""Lectura tipada de `05_Manifiesto_Fuentes.json`.

El manifiesto es la entrada del inventario: 83 identificadores que conservan los
67 originales del manual más las 16 incorporaciones. Se valida al leerlo para
que un cambio de forma se detecte acá y no a mitad de una carga.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from backend_normativo.config import REPO_ROOT

RUTA_MANIFIESTO = REPO_ROOT / "docs" / "paquete" / "05_Manifiesto_Fuentes.json"


class FuenteManifiesto(BaseModel):
    """Una fuente tal como la declara el manifiesto, sin reinterpretar."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    title: str
    origin: str
    manual_page: int | None = None
    urls: list[str] = Field(default_factory=list)
    url_status: str
    manual_technique: str | None = None
    adapter_hint: str
    manual_ttl_days: int | None = None
    default_reverify_days: int | None = None
    initial_state: str
    alias_of: str | None = None
    priority: str
    owner_capability: str
    target_tables: list[str] = Field(default_factory=list)
    task: str | None = None
    specific_acceptance: list[str] = Field(default_factory=list)
    manual_selector_reference: str | None = None
    manual_fields_reference: str | None = None
    content_status: str
    last_live_pipeline_run: str | None = None
    access_policy: str
    related_source_ids: list[str] = Field(default_factory=list)

    @property
    def sin_url_conocida(self) -> bool:
        return not self.urls


class Manifiesto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    created_on: str
    source_manual: str
    manual_observation_date: str
    source_count: int
    manual_cards: int
    manual_content_cards: int
    manual_discard_cards: int
    # Contadores declarados por el propio manifiesto. Se comparan con lo que
    # traen los datos: si no coinciden, es un cambio de forma a revisar.
    original_ids: int
    additional_sources: int
    missing_original_url_ids: list[str]
    notes: list[str] = Field(default_factory=list)
    sources: list[FuenteManifiesto]

    def validar_coherencia(self) -> list[str]:
        """Contradicciones internas del manifiesto. Se informan, no se corrigen
        en silencio: si el archivo cambia, el equipo tiene que verlo."""
        problemas: list[str] = []

        ids = [f.source_id for f in self.sources]
        if len(ids) != len(set(ids)):
            repetidos = sorted({i for i in ids if ids.count(i) > 1})
            problemas.append(f"IDs repetidos en el manifiesto: {', '.join(repetidos)}")

        if len(ids) != self.source_count:
            problemas.append(f"El manifiesto declara {self.source_count} fuentes y trae {len(ids)}")

        # Los 67 identificadores originales del manual son F01–F67 y se
        # conservan enteros: perder uno es perder cobertura sin que se note.
        esperados_originales = {f"F{n:02d}" for n in range(1, self.original_ids + 1)}
        faltantes = sorted(esperados_originales - set(ids))
        if faltantes:
            problemas.append(f"IDs originales ausentes: {', '.join(faltantes)}")

        adicionales = sorted(set(ids) - esperados_originales)
        if len(adicionales) != self.additional_sources:
            problemas.append(
                f"El manifiesto declara {self.additional_sources} incorporaciones "
                f"y trae {len(adicionales)}"
            )

        conocidos = set(ids)
        for fuente in self.sources:
            if fuente.alias_of and fuente.alias_of not in conocidos:
                problemas.append(
                    f"{fuente.source_id} es alias de {fuente.alias_of}, que no está en el catálogo"
                )
            for relacionada in fuente.related_source_ids:
                if relacionada not in conocidos:
                    problemas.append(
                        f"{fuente.source_id} referencia {relacionada}, que no está en el catálogo"
                    )

        sin_url = {f.source_id for f in self.sources if f.sin_url_conocida}
        declaradas = set(self.missing_original_url_ids)
        if sin_url != declaradas:
            solo_en_datos = sorted(sin_url - declaradas)
            solo_declaradas = sorted(declaradas - sin_url)
            if solo_en_datos:
                problemas.append(
                    "Fuentes sin URL que el manifiesto no declara como brecha: "
                    + ", ".join(solo_en_datos)
                )
            if solo_declaradas:
                problemas.append(
                    "Brechas declaradas que sí tienen URL: " + ", ".join(solo_declaradas)
                )

        return problemas


def cargar_manifiesto(ruta: Path | None = None) -> Manifiesto:
    datos = json.loads((ruta or RUTA_MANIFIESTO).read_text(encoding="utf-8"))
    return Manifiesto.model_validate(datos)
