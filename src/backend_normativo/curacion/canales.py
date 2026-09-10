"""Canales oficiales de atención, leídos de lo que el organismo publica.

P-006. Doce de las diecisiete fuentes «sin destino» declaran `canales` en su
historia: teléfonos, correos, WhatsApp y formularios por donde se accede a un
derecho. Es también una de las siete dimensiones y una de las ocho capacidades,
y es lo primero que necesita quien consulta: dónde ir.

Tres reglas gobiernan este módulo, y las tres son sobre lo que **no** se hace.

**El organismo se declara, no se adivina.** `canales.organismo_id` no admite
nulo, y ninguna fuente del catálogo trae organismo. Emparejar el nombre de una
fuente contra la tabla de organismos por parecido pondría el teléfono de un
organismo bajo el nombre de otro, y quien llame va a marcar ese número. Así que
la correspondencia vive acá, en `ORGANISMOS_POR_FUENTE`, escrita a mano y
revisable en un diff. Una fuente sin declaración no se cura: deja incidencia con
los candidatos que encontró, para que alguien la declare.

**Un valor que no normaliza no es un canal.** «1999 1998 1997» tiene la forma de
un teléfono para una expresión regular y es una lista de años. Lo que no pasa
las comprobaciones se cuenta como descartado y no entra.

**Cada canal cita la sección de donde salió.** La evidencia apunta a la unidad
informativa y guarda el fragmento exacto. Un teléfono sin cita es un teléfono
que nadie puede verificar contra la página que lo publicó.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import re
import uuid

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EntidadVersionada,
    Severidad,
    TipoCanal,
    TipoEvidencia,
    TipoIncidencia,
)


@dataclasses.dataclass(frozen=True)
class DeclaracionOrganismo:
    """A qué organismo pertenecen los canales que publica una fuente."""

    nombre: str
    jurisdiccion: str


# La correspondencia fuente -> organismo. Cada línea se verificó abriendo la
# página de la fuente y leyendo de quién es. No se infiere de la URL ni del
# nombre del recurso: `argentina.gob.ar` aloja decenas de organismos distintos.
ORGANISMOS_POR_FUENTE: dict[str, DeclaracionOrganismo] = {
    "F03": DeclaracionOrganismo(
        "Defensoría del Pueblo de la Ciudad Autónoma de Buenos Aires", "AR-C"
    ),
    "F05": DeclaracionOrganismo(
        "Asesoría General Tutelar - Ministerio Público Tutelar (CABA)", "AR-C"
    ),
    "F07": DeclaracionOrganismo(
        "Consejo de Derechos de Niñas, Niños y Adolescentes (CABA)", "AR-C"
    ),
    "F11": DeclaracionOrganismo("Ministerio Público de la Defensa de la Nación", "AR"),
    "F27": DeclaracionOrganismo("Ministerio de Educación (CABA)", "AR-C"),
    "F32": DeclaracionOrganismo("Ministerio de Educación (CABA)", "AR-C"),
    "F43": DeclaracionOrganismo("Ente Regulador de Agua y Saneamiento (ERAS)", "AR"),
    "F49": DeclaracionOrganismo("Ente Nacional Regulador de la Electricidad (ENRE)", "AR"),
    "F50": DeclaracionOrganismo("Ente Nacional Regulador de la Electricidad (ENRE)", "AR"),
    "F51": DeclaracionOrganismo("Ente Nacional Regulador de la Electricidad (ENRE)", "AR"),
    "F61": DeclaracionOrganismo("Secretaría de Integración Socio Urbana (SISU) - RENABAP", "AR"),
    "F64": DeclaracionOrganismo("Ministerio de Educación (CABA)", "AR-C"),
}

# Un teléfono argentino publicado: 0800 de siete u ocho dígitos, o un número
# con característica y abonado. Se pide separador entre los bloques —espacio,
# guion o paréntesis— porque una tira de ocho dígitos pegados es tan probable
# que sea un CUIT, un expediente o un año repetido.
# Separadores que las páginas usan de verdad: espacio, guion, raya y punto. La
# raya (–) aparece tal cual en argentina.gob.ar y un patrón que solo acepta
# guion la pierde sin decir nada.
SEP = r"[\s\-\u2013.]"

# Un teléfono argentino publicado: un 0800, o una característica —entre
# paréntesis o no, con el país adelante o sin él— seguida del abonado. Se exige
# separador entre los bloques: una tira de ocho dígitos pegados es tan probable
# que sea un CUIT, un expediente o un año repetido, y este módulo prefiere
# perder un teléfono a publicar un número que nadie marcó.
RE_TELEFONO = re.compile(
    rf"(?<![\d\-])(?:"
    rf"0800{SEP}?\d{{3}}{SEP}?\d{{3,4}}"
    rf"|\(\s*(?:\+?54{SEP}?)?0?\d{{2,4}}\s*\){SEP}?\d{{3,4}}{SEP}?\d{{4}}"
    rf"|(?:\+?54{SEP}?)?0?\d{{2,4}}{SEP}\d{{3,4}}{SEP}\d{{4}}"
    rf"|(?:\+?54{SEP}?)\d{{10,11}}"
    rf")(?![\d\-])"
)

RE_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+\.[\w.-]{2,}(?<![.,;])")
RE_URL = re.compile(r"https?://[^\s<>\"')]+")

# Un encabezado que dice de qué canal habla. El tipo sale del rótulo de la
# sección y no del formato del valor: un número puede ser teléfono o WhatsApp y
# eso lo dice la página, no el número.
RE_WHATSAPP = re.compile(r"whats\s*app", re.I)
RE_FORMULARIO = re.compile(r"\bformulario\b", re.I)

# Dígitos que un teléfono argentino puede tener, sin el país.
DIGITOS_MINIMOS, DIGITOS_MAXIMOS = 8, 12

# Años sueltos, códigos postales, montos. Se descartan antes de mirar el patrón.
RE_ANIOS = re.compile(r"^(?:19|20)\d{2}(?:[\s\-](?:19|20)\d{2})*$")


@dataclasses.dataclass
class Candidato:
    tipo: TipoCanal
    crudo: str
    normalizado: str
    unidad_id: uuid.UUID
    doc_version_id: uuid.UUID
    source_id: str
    rotulo: str


@dataclasses.dataclass
class ResultadoCanales:
    secciones_leidas: int = 0
    candidatos: int = 0
    descartados: int = 0
    creados: int = 0
    repetidos: int = 0
    fuentes_sin_organismo: dict[str, int] = dataclasses.field(default_factory=dict)
    por_fuente: dict[str, int] = dataclasses.field(default_factory=dict)
    avisos: list[str] = dataclasses.field(default_factory=list)


def normalizar_telefono(crudo: str) -> str | None:
    """Deja solo los dígitos, con el país si viene. `None` si no es un teléfono.

    No inventa la característica cuando falta: un número de ocho dígitos sin
    característica es un número al que no se puede llamar desde afuera de esa
    ciudad, y completarlo con la de Buenos Aires sería fabricar el dato.
    """
    limpio = crudo.strip()
    if RE_ANIOS.match(re.sub(r"[^\d\s\-]", "", limpio).strip()):
        return None
    digitos = re.sub(r"\D", "", limpio)
    if not (DIGITOS_MINIMOS <= len(digitos) <= DIGITOS_MAXIMOS):
        return None
    if digitos.startswith("54"):
        return f"+{digitos}"
    if digitos.startswith("0800"):
        return digitos
    return digitos


def candidatos_de(texto: str, rotulo: str) -> list[tuple[TipoCanal, str, str]]:
    """Qué canales publica esta sección, con su valor crudo y normalizado."""
    encontrados: list[tuple[TipoCanal, str, str]] = []
    contexto = f"{rotulo} {texto}"
    es_whatsapp = bool(RE_WHATSAPP.search(contexto))

    for coincidencia in RE_TELEFONO.finditer(texto):
        crudo = coincidencia.group(0).strip()
        normalizado = normalizar_telefono(crudo)
        if normalizado is None:
            encontrados.append((TipoCanal.TELEFONO, crudo, ""))
            continue
        tipo = TipoCanal.WHATSAPP if es_whatsapp else TipoCanal.TELEFONO
        encontrados.append((tipo, crudo, normalizado))

    for coincidencia in RE_EMAIL.finditer(texto):
        crudo = coincidencia.group(0).strip()
        encontrados.append((TipoCanal.EMAIL, crudo, crudo.lower()))

    for coincidencia in RE_URL.finditer(texto):
        crudo = coincidencia.group(0).rstrip(".,;)")
        tipo = TipoCanal.FORMULARIO_WEB if RE_FORMULARIO.search(contexto) else TipoCanal.WEB
        encontrados.append((tipo, crudo, crudo))

    return encontrados


CONSULTA_SECCIONES = """
SELECT u.id, u.doc_version_id, u.texto, coalesce(u.rotulo, '') AS rotulo,
       fu.source_id
  FROM unidades_documentales u
  JOIN documento_versiones dv ON dv.id = u.doc_version_id
  JOIN capturas cap ON cap.id = dv.captura_id
  JOIN fuente_urls fu ON fu.id = cap.source_url_id
 WHERE u.rol_contenido = 'INFORMATIVO'
   AND (cast(:fuente AS varchar) IS NULL OR fu.source_id = :fuente)
 ORDER BY fu.source_id, u.orden
"""


class CuradorDeCanales:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def cargar(self, source_id: str | None = None) -> ResultadoCanales:
        resultado = ResultadoCanales()
        ahora = dt.datetime.now(dt.UTC)
        vistos: set[tuple[str, str, str]] = set()

        filas = (
            self.conexion.execute(text(CONSULTA_SECCIONES), {"fuente": source_id}).mappings().all()
        )
        for fila in filas:
            resultado.secciones_leidas += 1
            hallazgos = candidatos_de(fila["texto"], fila["rotulo"])
            if not hallazgos:
                continue

            declaracion = ORGANISMOS_POR_FUENTE.get(fila["source_id"])
            if declaracion is None:
                resultado.fuentes_sin_organismo[fila["source_id"]] = (
                    resultado.fuentes_sin_organismo.get(fila["source_id"], 0) + len(hallazgos)
                )
                continue

            organismo_id = self._organismo(declaracion)
            for tipo, crudo, normalizado in hallazgos:
                resultado.candidatos += 1
                if not normalizado:
                    resultado.descartados += 1
                    continue
                clave = (str(organismo_id), tipo.value, normalizado)
                if clave in vistos:
                    resultado.repetidos += 1
                    continue
                if self._ya_esta(organismo_id, tipo, normalizado):
                    resultado.repetidos += 1
                    vistos.add(clave)
                    continue
                vistos.add(clave)
                self._crear(fila, tipo, crudo, normalizado, organismo_id, ahora)
                resultado.creados += 1
                resultado.por_fuente[fila["source_id"]] = (
                    resultado.por_fuente.get(fila["source_id"], 0) + 1
                )

        self._incidencias(resultado)
        return resultado

    def _organismo(self, declaracion: DeclaracionOrganismo) -> uuid.UUID:
        existente = self.conexion.execute(
            text("SELECT id FROM organismos WHERE nombre = :n AND jurisdiccion_id = :j"),
            {"n": declaracion.nombre, "j": declaracion.jurisdiccion},
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        return self.conexion.execute(
            text(
                "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
                "VALUES (:j, :n, 'ORGANISMO_CONTROL') RETURNING id"
            ),
            {"j": declaracion.jurisdiccion, "n": declaracion.nombre},
        ).scalar_one()

    def _ya_esta(self, organismo_id: uuid.UUID, tipo: TipoCanal, normalizado: str) -> bool:
        return (
            self.conexion.execute(
                text(
                    "SELECT 1 FROM canales WHERE organismo_id = :o AND tipo = :t "
                    "  AND valor_normalizado = :v LIMIT 1"
                ),
                {"o": organismo_id, "t": tipo.value, "v": normalizado},
            ).scalar_one_or_none()
            is not None
        )

    def _crear(
        self,
        fila,
        tipo: TipoCanal,
        crudo: str,
        normalizado: str,
        organismo_id: uuid.UUID,
        ahora: dt.datetime,
    ) -> None:
        # El fragmento es la sección entera y no solo el número: un teléfono
        # suelto no dice para qué es, y la cita tiene que poder leerse.
        fragmento = fila["texto"][:2000]
        evidencia_id = self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, "
                " hash_fragmento, tipo) VALUES (:dv, :u, :f, :h, :t) RETURNING id"
            ),
            {
                "dv": fila["doc_version_id"],
                "u": fila["id"],
                "f": fragmento,
                "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
                "t": TipoEvidencia.FRAGMENTO_TEXTO.value,
            },
        ).scalar_one()

        canal_id = uuid.uuid4()
        registro = self.conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo, known_desde) "
                "VALUES (:tipo, :eid, 1, 'CANDIDATE', 'DESCONOCIDO', :ahora) RETURNING id"
            ),
            {"tipo": EntidadVersionada.CANAL.value, "eid": canal_id, "ahora": ahora},
        ).scalar_one()

        self.conexion.execute(
            text(
                "INSERT INTO canales (registro_version_id, canal_id, organismo_id, "
                " evidencia_id, tipo, valor_crudo, valor_normalizado, publico) "
                "VALUES (:rv, :c, :o, :e, :t, :crudo, :norm, true)"
            ),
            {
                "rv": registro,
                "c": canal_id,
                "o": organismo_id,
                "e": evidencia_id,
                "t": tipo.value,
                "crudo": crudo,
                "norm": normalizado,
            },
        )

    def _incidencias(self, resultado: ResultadoCanales) -> None:
        for source_id, cuantos in sorted(resultado.fuentes_sin_organismo.items()):
            descripcion = (
                f"La fuente {source_id} publica {cuantos} canal(es) de atención y el catálogo "
                "no declara a qué organismo pertenecen. No se cargan: emparejar el nombre de "
                "la fuente con un organismo por parecido pondría un teléfono bajo el nombre de "
                "otro, y quien llame va a marcar ese número. Se declara en "
                "`curacion/canales.py`, en ORGANISMOS_POR_FUENTE."
            )
            existe = self.conexion.execute(
                text(
                    "SELECT 1 FROM incidencias_revision "
                    " WHERE source_id = :s AND tipo = :t AND estado = 'ABIERTA' "
                    "   AND descripcion = :d LIMIT 1"
                ),
                {"s": source_id, "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value, "d": descripcion},
            ).scalar_one_or_none()
            if existe:
                continue
            self.conexion.execute(
                text(
                    "INSERT INTO incidencias_revision (source_id, tipo, severidad, "
                    " descripcion, estado) VALUES (:s, :t, :sev, :d, 'ABIERTA')"
                ),
                {
                    "s": source_id,
                    "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                    "sev": Severidad.HIGH.value,
                    "d": descripcion,
                },
            )
            resultado.avisos.append(
                f"{source_id}: {cuantos} canal(es) sin organismo declarado. Queda incidencia."
            )


def formatear(resultado: ResultadoCanales) -> str:
    lineas = [
        "# Canales de atención curados",
        "",
        f"- Secciones informativas leídas: **{resultado.secciones_leidas}**",
        f"- Candidatos encontrados: {resultado.candidatos}",
        f"- **Canales cargados: {resultado.creados}**",
        f"- Descartados por no normalizar: {resultado.descartados}",
        f"- Repetidos (ya estaban): {resultado.repetidos}",
    ]
    if resultado.por_fuente:
        lineas += ["", "| Fuente | Canales |", "| --- | ---: |"]
        lineas += [f"| {s} | {n} |" for s, n in sorted(resultado.por_fuente.items())]
    for aviso in resultado.avisos:
        lineas += ["", aviso]
    lineas += [
        "",
        "Un valor que no normaliza no se carga: «1999 1998 1997» tiene la forma de un",
        "teléfono para una expresión regular y es una lista de años. Y el organismo se",
        "declara, no se infiere del nombre de la fuente: un teléfono bajo el organismo",
        "equivocado es alguien marcando el número equivocado.",
    ]
    return "\n".join(lineas)
