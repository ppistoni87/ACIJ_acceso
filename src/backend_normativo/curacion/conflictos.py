"""HU-F20 · AT-060: dos fuentes oficiales que dicen pisos distintos.

El dataset abierto de sedes comunales dice que la Subsede Comunal 2 está en
«Lopez, Vicente 2050, 3 piso». La ficha oficial de la Comuna 2, del mismo
gobierno, dice «Vicente López 2050, 4° piso». Coinciden en la calle y en la
altura, y difieren en el piso.

Hay tres maneras de arruinarlo y las tres producen una dirección que se lee bien:
elegir la primera fuente, elegir la más reciente, o componer una legible tomando
la calle de una y el piso de la otra. Las tres mandan a alguien a golpear una
puerta equivocada en un edificio correcto.

Lo que se hace es lo que el esquema ya permitía y nadie estaba usando: los dos
candidatos coexisten, el campo en disputa se marca como tal, y la dirección no
se publica hasta que alguien mire cuál es. Lo que sí se publica es la parte en
la que las dos fuentes coinciden, porque esa no está en duda.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import Severidad, TipoIncidencia

RE_PISO = re.compile(
    r"\b(?:piso\s*(?P<n1>\d{1,2})|(?P<n2>\d{1,2})\s*[°ºo]?\s*(?:er|do|ro|to|ma)?\.?\s*piso"
    r"|(?P<n3>pb|planta\s+baja|entrepiso|subsuelo))\b",
    re.IGNORECASE,
)
RE_ALTURA = re.compile(r"\b(\d{2,5})\b")

CAMPOS = ("calle", "altura", "piso")


@dataclass
class Direccion:
    cruda: str
    calle: str | None = None
    altura: str | None = None
    piso: str | None = None

    def componente(self, campo: str) -> str | None:
        return getattr(self, campo)


@dataclass
class Conflicto:
    campo: str
    valores: dict[str, str]

    def __str__(self) -> str:
        partes = ", ".join(f"{origen} dice «{valor}»" for origen, valor in self.valores.items())
        return f"{self.campo}: {partes}"


@dataclass
class Contraste:
    punto_id: uuid.UUID | None = None
    coinciden: dict[str, str] = field(default_factory=dict)
    conflictos: list[Conflicto] = field(default_factory=list)
    sin_dato: list[str] = field(default_factory=list)

    @property
    def hay_conflicto(self) -> bool:
        return bool(self.conflictos)

    @property
    def campos_en_disputa(self) -> list[str]:
        return [c.campo for c in self.conflictos]

    @property
    def direccion_publicable(self) -> str | None:
        """Lo que las dos fuentes afirman igual.

        Si el piso está en disputa no se compone una dirección con él, y
        tampoco se compone una sin él haciéndola pasar por completa: se
        devuelve lo coincidente y el conflicto viaja aparte.
        """
        if not self.coinciden.get("calle"):
            return None
        partes = [self.coinciden["calle"]]
        if self.coinciden.get("altura"):
            partes.append(self.coinciden["altura"])
        if self.coinciden.get("piso"):
            partes.append(f"piso {self.coinciden['piso']}")
        return " ".join(partes)


def _sin_tildes(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in plano if not unicodedata.combining(c))


def _normalizar_calle(texto: str) -> str:
    """«Lopez, Vicente 2050» y «Vicente López 2050» son la misma calle.

    Los datasets de la Ciudad invierten el nombre —apellido primero— y las
    fichas lo escriben derecho. Comparar los tokens ordenados evita leer eso
    como un conflicto de calle que no existe.
    """
    limpio = _sin_tildes(texto).lower()
    limpio = re.sub(r"\b(av|avda|avenida|calle|dr|pres|gral)\b\.?", " ", limpio)
    tokens = sorted(t for t in re.split(r"[^a-z0-9]+", limpio) if len(t) > 1 and not t.isdigit())
    return " ".join(tokens)


def leer_direccion(cruda: str) -> Direccion:
    """Separa una dirección en calle, altura y piso, sin inventar lo que falta."""
    direccion = Direccion(cruda=cruda)
    texto = " ".join(cruda.split())

    piso = RE_PISO.search(texto)
    if piso:
        crudo = piso.group("n1") or piso.group("n2") or piso.group("n3")
        direccion.piso = _sin_tildes(crudo).strip().lower()
        texto = texto[: piso.start()] + " " + texto[piso.end() :]

    # No se corta en la primera coma: el dataset de la Ciudad escribe
    # «Lopez, Vicente 2050» —apellido primero— y esa coma es parte del nombre
    # de la calle, no un separador.
    resto = texto.strip()
    altura = RE_ALTURA.findall(resto)
    if altura:
        direccion.altura = altura[-1]
        resto = resto[: resto.rfind(direccion.altura)]
    direccion.calle = resto.strip(" ,.;-") or None
    return direccion


def contrastar(candidatas: dict[str, str]) -> Contraste:
    """Compara lo que dice cada fuente sobre la misma dirección.

    `candidatas` va con el nombre de la fuente como clave, porque una diferencia
    sin saber quién dice qué no se puede resolver.
    """
    contraste = Contraste()
    leidas = {origen: leer_direccion(cruda) for origen, cruda in candidatas.items()}
    if len(leidas) < 2:
        return contraste

    for campo in CAMPOS:
        valores = {
            origen: direccion.componente(campo)
            for origen, direccion in leidas.items()
            if direccion.componente(campo)
        }
        if not valores:
            contraste.sin_dato.append(campo)
            continue
        if len(valores) < len(leidas):
            # Una fuente lo dice y la otra no: eso no es un conflicto, es una
            # fuente menos completa. Se toma lo que hay.
            contraste.coinciden[campo] = next(iter(valores.values()))
            continue

        comparables = (
            {o: _normalizar_calle(v) for o, v in valores.items()}
            if campo == "calle"
            else {o: v.lower() for o, v in valores.items()}
        )
        if len(set(comparables.values())) == 1:
            # Coinciden, y a veces con distinta forma: «Lopez, Vicente» y
            # «Vicente López». Se toma la más larga por ser determinista;
            # quedarse con la primera haría que el resultado dependiera del
            # orden en que llegaron las fuentes, que es elegir una.
            contraste.coinciden[campo] = max(sorted(valores.values()), key=len)
        else:
            contraste.conflictos.append(Conflicto(campo=campo, valores=valores))
    return contraste


class DetectorDeConflictos:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def revisar(self, punto_id: uuid.UUID) -> Contraste:
        """Contrasta las direcciones candidatas abiertas de un punto."""
        # El origen sale del canal presencial de esa versión, que es el que
        # lleva la evidencia. Cuando no lo tiene, el número de versión al menos
        # distingue una afirmación de la otra.
        candidatas = {
            (fila["origen"] or f"versión {fila['numero_version']}"): fila["direccion_cruda"]
            for fila in self.conexion.execute(
                text(
                    "SELECT pv.direccion_cruda, rv.numero_version, "
                    "  (SELECT d.source_id || ' (' || coalesce(u.rol, 'sin rol') || ')' "
                    "     FROM canales c "
                    "     JOIN evidencias e ON e.id = c.evidencia_id "
                    "     JOIN documento_versiones dv ON dv.id = e.doc_version_id "
                    "     JOIN documentos d ON d.id = dv.documento_id "
                    "     LEFT JOIN capturas cap ON cap.id = dv.captura_id "
                    "     LEFT JOIN fuente_urls u ON u.id = cap.source_url_id "
                    "    WHERE c.punto_id = pv.punto_id AND c.tipo = 'PRESENCIAL' "
                    "      AND c.valor_crudo = pv.direccion_cruda LIMIT 1) AS origen "
                    "  FROM punto_versiones pv "
                    "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                    " WHERE pv.punto_id = :p AND rv.known_hasta IS NULL "
                    "   AND pv.direccion_cruda IS NOT NULL"
                ),
                {"p": punto_id},
            ).mappings()
            if fila["direccion_cruda"]
        }
        contraste = contrastar(candidatas)
        contraste.punto_id = punto_id
        if contraste.hay_conflicto:
            self._incidencia(punto_id, contraste)
        return contraste

    def _incidencia(self, punto_id: uuid.UUID, contraste: Contraste) -> None:
        descripcion = (
            f"Dos fuentes oficiales difieren sobre la dirección del punto {punto_id}: "
            + "; ".join(str(c) for c in contraste.conflictos)
            + ". El campo queda en disputa: no se elige una fuente ni se compone una "
            "dirección mezclando las dos, porque eso manda a alguien a una puerta "
            "equivocada en un edificio correcto."
        )
        ya = self.conexion.execute(
            text("SELECT id FROM incidencias_revision WHERE descripcion = :d"),
            {"d": descripcion},
        ).scalar_one_or_none()
        if ya is not None:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, descripcion, "
                " responsable_rol) VALUES (:t, :s, 'ABIERTA', :d, 'curador de datos')"
            ),
            {
                "t": TipoIncidencia.CONFLICTO_DE_FUENTES.value,
                "s": Severidad.HIGH.value,
                "d": descripcion,
            },
        )
