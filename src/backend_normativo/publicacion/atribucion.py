"""HU-022 · AT-066: quién dice lo que se está diciendo.

En el corpus hay 83 fuentes oficiales y una secundaria: ACIJ, que publica un
análisis del Proyecto de Presupuesto 2026 de la Ciudad y afirma que las partidas
de los organismos de vivienda caen 22,9% en términos reales y que son las más
bajas en catorce años. El GCBA publica el proyecto de presupuesto; no publica
esa lectura.

Hay dos maneras de arruinarlo. Descartar la afirmación pierde información que a
alguien le sirve y que está sostenida en un documento público. Presentarla sin
decir quién la hace —o peor, junto al resto de los datos del organismo— le da
una autoridad que no tiene: quien la lea va a creer que el Gobierno de la Ciudad
dijo que su propio presupuesto de vivienda es el más bajo en catorce años.

Lo que se hace es conservar la atribución. Una afirmación sostenida sólo por una
fuente secundaria se sirve diciendo quién la afirma, y nunca se adjudica al
organismo de la fuente oficial.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import CaracterDeFuente


@dataclass
class Atribucion:
    campo_path: str
    source_id: str | None = None
    fuente: str | None = None
    caracter: str = CaracterDeFuente.OFICIAL.value
    organismo: str | None = None
    evidencia_id: uuid.UUID | None = None

    @property
    def es_secundaria(self) -> bool:
        return self.caracter == CaracterDeFuente.SECUNDARIA.value

    @property
    def atribuible_al_organismo(self) -> bool:
        """Si lo que dice esta afirmación puede presentarse como del organismo.

        Sólo cuando la fuente es oficial. Una lectura de la sociedad civil sobre
        un dato oficial no es una afirmación del organismo, ni siquiera cuando
        el dato de base sí lo es.
        """
        return not self.es_secundaria and self.organismo is not None

    @property
    def leyenda(self) -> str:
        if self.es_secundaria:
            return (
                f"Afirmado por {self.fuente or self.source_id}, que es una fuente secundaria. "
                "No consta en la fuente oficial revisada y no se le atribuye a ella."
            )
        if self.organismo:
            return f"Afirmado por {self.organismo} en su publicación oficial."
        return "Afirmado por la fuente oficial revisada."


@dataclass
class Explicacion:
    """Lo que se puede decir de un campo, con quién lo sostiene."""

    campo_path: str
    atribuciones: list[Atribucion] = field(default_factory=list)

    @property
    def oficiales(self) -> list[Atribucion]:
        return [a for a in self.atribuciones if not a.es_secundaria]

    @property
    def secundarias(self) -> list[Atribucion]:
        return [a for a in self.atribuciones if a.es_secundaria]

    @property
    def solo_secundaria(self) -> bool:
        return bool(self.secundarias) and not self.oficiales

    @property
    def se_abstiene(self) -> bool:
        return not self.atribuciones

    def texto(self) -> str:
        if self.se_abstiene:
            return (
                f"No hay ninguna fuente revisada que afirme «{self.campo_path}». "
                "La ausencia no es una negación."
            )
        if self.solo_secundaria:
            quienes = ", ".join(a.fuente or a.source_id or "?" for a in self.secundarias)
            return (
                f"«{self.campo_path}» lo afirma únicamente {quienes}, que es una fuente "
                "secundaria. La fuente oficial revisada no lo dice. Se conserva la "
                "atribución: no se presenta como afirmación del organismo."
            )
        return " ".join(a.leyenda for a in self.atribuciones)


def explicar(conexion: Connection, registro_version_id: uuid.UUID, campo_path: str) -> Explicacion:
    """Quién sostiene lo que se afirma sobre un campo de una versión."""
    explicacion = Explicacion(campo_path=campo_path)
    for fila in conexion.execute(
        text(
            "SELECT a.campo_path, a.source_id, a.evidencia_id, "
            "       f.nombre AS fuente, f.caracter, o.nombre AS organismo "
            "  FROM afirmaciones a "
            "  LEFT JOIN fuentes f ON f.source_id = a.source_id "
            "  LEFT JOIN organismos o ON o.id = f.organismo_id "
            " WHERE a.registro_version_id = :v AND a.campo_path = :c "
            "   AND a.estado_campo = 'INFORMADO' "
            " ORDER BY f.caracter, a.observado_en"
        ),
        {"v": registro_version_id, "c": campo_path},
    ).mappings():
        explicacion.atribuciones.append(
            Atribucion(
                campo_path=fila["campo_path"],
                source_id=fila["source_id"],
                fuente=fila["fuente"],
                caracter=fila["caracter"] or CaracterDeFuente.OFICIAL.value,
                # El organismo sólo viaja cuando la fuente es oficial: es
                # justamente lo que no hay que adjudicar.
                organismo=(
                    fila["organismo"]
                    if fila["caracter"] != CaracterDeFuente.SECUNDARIA.value
                    else None
                ),
                evidencia_id=fila["evidencia_id"],
            )
        )
    return explicacion
