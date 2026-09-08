"""HU-020: el directorio de defensorías de la Nación, sin atribuir de más.

La Defensoría del Pueblo de la Nación publica tres secciones en el mismo
directorio y con el mismo formato: sus oficinas regionales, sus receptorías y
—la tercera— los defensores del pueblo provinciales y municipales, que son
organismos autónomos y no oficinas suyas.

Cargarlas todas como oficinas de la DPN es el error que este importador existe
para no cometer. A quien pregunta «¿qué organismo me atiende?» hay que
responderle el Defensor del Pueblo de Avellaneda, no la Defensoría de la Nación:
son competencias distintas y quien reclama ante el organismo equivocado pierde
tiempo que a veces es un plazo.

La página agrupa por jurisdicción: cada panel es una provincia y contiene tantas
oficinas como anuncia su propio rótulo («Buenos Aires | 16»). Ese número es un
control de integridad que la fuente regala y que acá se verifica: si el panel
dice dieciséis y se leen tres, la lectura está mal y hay que saberlo, no cargar
tres en silencio.

Y no se decodifican los correos. El sitio los publica ofuscados con una
protección de Cloudflare, que es una medida contra la recolección automática.
El canal existe y se registra; su valor no se toma.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser, Node
from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    AlcanceTerritorial,
    EntidadVersionada,
    EstadoRevision,
    ModoExtraccion,
    Severidad,
    TipoCanal,
    TipoDocumento,
    TipoEvidencia,
    TipoFecha,
    TipoIncidencia,
    TipoOrganismo,
    TipoPuntoAtencion,
    TipoVersionDocumento,
    ValidTipo,
)
from backend_normativo.ingesta.adaptadores.html import decodificar_html
from backend_normativo.ingesta.almacen import AlmacenObjetos
from backend_normativo.ingesta.versiones import (
    proxima_version,
    sha_de_la_captura,
    version_ya_existente,
)

SOURCE_ID = "F44"
ORGANISMO_NACIONAL = "Defensoría del Pueblo de la Nación"
JURISDICCION_NACIONAL = "AR"

# Las tres secciones del directorio, por el identificador que usa el sitio.
SECCIONES = {
    "2100": ("Oficinas regionales", True),
    "2200": ("Receptorías", True),
    # Las de la tercera sección no son oficinas de la DPN: son organismos
    # autónomos que la DPN lista.
    "2300": ("Otros Defensores", False),
}

RE_SECCION = re.compile(r"idS=(\d+)")
RE_TITULO = re.compile(r"^(?P<jurisdiccion>.*?)(?:\|\s*(?P<cantidad>\d+))?$")
RE_CP_LOCALIDAD = re.compile(r"^\((?P<cp>[^)]*)\)\s*(?P<localidad>.*)$")
# Un teléfono se normaliza sólo si el texto publicado es un único número:
# «(11) 4227-7184 / 7110 / 4222-8226» son tres líneas de las que «7110» no se
# marca sola, y «(299) 449.1200 int. 4600» lleva interno. Partirlas fabricaría
# números que nadie publicó.
RE_UN_SOLO_NUMERO = re.compile(r"^\(?\d[\d\s\-.()]*\d$")
DIGITOS_PLAUSIBLES = range(8, 12)

# El sitio rotula los WhatsApp con el mismo icono que los teléfonos; lo único
# que los distingue es que lo dicen en el texto.
MARCAS_WHATSAPP = ("whatsapp", "wasap", "wsp")

# El sitio rotula los teléfonos con dos iconos distintos según sean fijos o
# móviles. Los dos son un teléfono al que se puede llamar.
ICONOS_TELEFONO = ("fa-phone", "fa-mobile")

# Texto que el sitio deja en lugar del correo cuando lo ofusca.
MARCA_CORREO_OFUSCADO = "email"

# La página abrevia dos jurisdicciones de un modo que el catálogo no usa.
ALIAS_JURISDICCIONES = {
    "caba": "Ciudad Autónoma de Buenos Aires",
    "tierra del fuego": "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
}


# Lo que un nombre declara sobre su alcance. Sólo se clasifica lo explícito:
# «Defensor del Pueblo de Córdoba» puede ser la provincia o la ciudad, y las dos
# existen. Adivinar manda a alguien al organismo equivocado.
RE_PROVINCIAL = re.compile(
    r"\bde\s+la\s+Provincia\s+(?:de|del)\s+(?P<ambito>.+)$|"
    r"\bde\s+la\s+Ciudad\s+Aut[óo]noma\s+de\s+(?P<caba>Buenos\s+Aires)$",
    re.IGNORECASE,
)
RE_MUNICIPAL = re.compile(
    r"\bde\s+la\s+Municipalidad\s+(?:de|del)\s+(?P<m1>.+)$|"
    r"\bde\s+la\s+Ciudad\s+(?:de|del)\s+(?P<m2>.+)$|"
    r"\bde\s+los\s+Vecinos\s+de\s+la\s+Ciudad\s+(?:de|del)\s+(?P<m3>.+)$|"
    r"\bdel\s+Vecino\s+(?:de|del)\s+(?P<m4>.+)$",
    re.IGNORECASE,
)


class FormaInesperada(Exception):
    """La página no tiene la estructura de paneles del directorio."""


@dataclass
class Oficina:
    nombre: str
    jurisdiccion_listada: str | None = None
    direccion: str | None = None
    codigo_postal: str | None = None
    localidad: str | None = None
    telefonos: list[str] = field(default_factory=list)
    web: str | None = None
    correo_ofuscado: bool = False


@dataclass
class Lectura:
    seccion: str
    propias_de_la_dpn: bool
    oficinas: list[Oficina] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


@dataclass
class ResultadoDpn:
    seccion: str = ""
    propias_de_la_dpn: bool = True
    oficinas: int = 0
    puntos_creados: int = 0
    puntos_conocidos: int = 0
    canales: int = 0
    correos_no_tomados: int = 0
    sin_direccion: int = 0
    jurisdicciones_sin_mapear: int = 0
    alcance_sin_declarar: int = 0
    avisos: list[str] = field(default_factory=list)


def leer(html: str, *, url: str) -> Lectura:
    """Las oficinas de una sección, y si son de la DPN o de terceros."""
    coincidencia = RE_SECCION.search(url)
    clave = coincidencia.group(1) if coincidencia else ""
    if clave not in SECCIONES:
        raise FormaInesperada(
            f"La URL {url} no identifica ninguna de las tres secciones conocidas "
            f"({', '.join(SECCIONES)}). Cargar un directorio sin saber de quién son las "
            "oficinas es exactamente lo que hay que evitar."
        )
    nombre_seccion, propias = SECCIONES[clave]

    paneles = HTMLParser(html).css(".panel")
    if not paneles:
        raise FormaInesperada(
            "La página no trae paneles de oficinas. Cambió de estructura y no se importa a "
            "ciegas: un directorio mal leído atribuye oficinas a quien no las tiene."
        )

    lectura = Lectura(seccion=nombre_seccion, propias_de_la_dpn=propias)
    for panel in paneles:
        jurisdiccion, declaradas = _titulo(panel.css_first(".panel-title"))
        cuerpos = panel.css(".panel-body")
        leidas: list[Oficina] = []
        for cuerpo in cuerpos:
            leidas.extend(_oficinas_del_cuerpo(cuerpo, jurisdiccion))
        # El rótulo del panel anuncia cuántas oficinas contiene. Si no coinciden,
        # se dice: una lectura incompleta que no avisa es peor que un error.
        if declaradas is not None and declaradas != len(leidas):
            lectura.avisos.append(
                f"«{jurisdiccion or 'sin jurisdicción'}» anuncia {declaradas} oficina(s) y se "
                f"leyeron {len(leidas)}. Se cargan las leídas y queda la diferencia anotada: "
                "el rótulo de la fuente es el control y no coincide."
            )
        lectura.oficinas.extend(leidas)
    return lectura


def _titulo(titulo: Node | None) -> tuple[str | None, int | None]:
    """El rótulo es «Provincia | N»: la jurisdicción y cuántas oficinas trae."""
    if titulo is None:
        return None, None
    limpio = " ".join(titulo.text(strip=True).split())
    coincidencia = RE_TITULO.match(limpio)
    if coincidencia is None:
        return limpio or None, None
    jurisdiccion = coincidencia.group("jurisdiccion").strip() or None
    cantidad = coincidencia.group("cantidad")
    return jurisdiccion, int(cantidad) if cantidad else None


def _oficinas_del_cuerpo(cuerpo: Node, jurisdiccion: str | None) -> list[Oficina]:
    """Cada `h4` abre una oficina; los `p` que siguen son sus campos."""
    oficinas: list[Oficina] = []
    actual: Oficina | None = None
    for nodo in cuerpo.iter():
        if nodo.tag == "h4":
            nombre = _limpio(nodo)
            if nombre:
                actual = Oficina(nombre=nombre, jurisdiccion_listada=jurisdiccion)
                oficinas.append(actual)
            continue
        if nodo.tag != "p" or actual is None:
            continue
        _asignar(actual, nodo)
    return oficinas


def _asignar(oficina: Oficina, parrafo: Node) -> None:
    icono = parrafo.css_first("icon")
    clases = (icono.attributes.get("class") or "") if icono is not None else ""
    valor = _limpio(parrafo)
    if not valor:
        return

    if "fa-map-marker" in clases:
        oficina.direccion = valor
    elif "fa-location-arrow" in clases:
        coincidencia = RE_CP_LOCALIDAD.match(valor)
        if coincidencia:
            oficina.codigo_postal = coincidencia.group("cp").strip() or None
            oficina.localidad = coincidencia.group("localidad").strip() or None
        else:
            oficina.localidad = valor
    elif any(icono_tel in clases for icono_tel in ICONOS_TELEFONO):
        # Se guarda el texto tal como lo publica el sitio. Ver `normalizar_telefono`.
        oficina.telefonos.append(valor)
    elif "fa-globe" in clases:
        oficina.web = valor
    elif "fa-envelope" in clases:
        # El correo viene ofuscado por Cloudflare, que es una protección contra
        # la recolección automática. Se registra que existe y no se decodifica.
        oficina.correo_ofuscado = MARCA_CORREO_OFUSCADO in valor.lower()


def _limpio(nodo: Node) -> str:
    return " ".join(nodo.text(separator=" ", strip=True).replace("\xa0", " ").split())


def alcance_de(nombre: str) -> tuple[str, str | None]:
    """Qué alcance declara el nombre de un organismo, y sobre qué ámbito.

    Devuelve `NO_DECLARADO` cuando el nombre no lo dice. Es el caso más común y
    el más importante de no resolver: «Defensor del Pueblo de Salta» puede ser
    el provincial o el de la capital, y responder el equivocado manda a alguien
    a un organismo sin competencia sobre su reclamo.
    """
    limpio = " ".join(nombre.split())
    provincial = RE_PROVINCIAL.search(limpio)
    if provincial:
        ambito = provincial.group("ambito") or provincial.group("caba")
        return AlcanceTerritorial.PROVINCIAL.value, (ambito.strip() if ambito else None)
    municipal = RE_MUNICIPAL.search(limpio)
    if municipal:
        ambito = next((g for g in municipal.groups() if g), None)
        if ambito:
            return AlcanceTerritorial.MUNICIPAL.value, ambito.strip()
    return AlcanceTerritorial.NO_DECLARADO.value, None


def es_whatsapp(crudo: str) -> bool:
    return any(marca in crudo.lower() for marca in MARCAS_WHATSAPP)


def normalizar_telefono(crudo: str) -> str | None:
    """Los dígitos, y sólo cuando el texto publicado es un número y nada más.

    Devuelve `None` ante cualquier ambigüedad —varias líneas separadas por `/`,
    un interno, un rótulo— para que un valor normalizado, cuando existe, se
    pueda marcar sin dudar.
    """
    limpio = crudo.strip()
    if not RE_UN_SOLO_NUMERO.match(limpio):
        return None
    digitos = re.sub(r"\D", "", limpio)
    # Dos números pegados con un espacio pasan el patrón pero no la cuenta.
    return digitos if len(digitos) in DIGITOS_PLAUSIBLES else None


def _clave(nombre: str) -> str:
    """Un nombre comparable: sin tildes, sin mayúsculas y sin los puntos de la
    sigla, para que «C.A.B.A.» y «CABA» sean la misma clave."""
    sin_tildes = unicodedata.normalize("NFKD", nombre)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"[^a-z]+", " ", sin_tildes.lower().replace(".", "")).strip()


class ImportadorDpn:
    def __init__(self, conexion: Connection, almacen: AlmacenObjetos | None = None) -> None:
        self.conexion = conexion
        self.almacen = almacen or AlmacenObjetos()
        self._jurisdicciones = self._catalogo_de_jurisdicciones()

    def importar_desde_captura(self, captura_id: uuid.UUID) -> ResultadoDpn:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT c.sha256_raw, c.mime, c.capturado_en, c.url_final "
                    "  FROM capturas c WHERE c.id = :c"
                ),
                {"c": captura_id},
            )
            .mappings()
            .one()
        )
        html = decodificar_html(self.almacen.leer(fila["sha256_raw"]), charset_declarado=None)
        return self.importar(
            html,
            captura_id=captura_id,
            url=fila["url_final"],
            capturado_en=fila["capturado_en"],
        )

    def importar(
        self, html: str, *, captura_id: uuid.UUID, url: str, capturado_en: dt.datetime
    ) -> ResultadoDpn:
        lectura = leer(html, url=url)
        resultado = ResultadoDpn(
            seccion=lectura.seccion,
            propias_de_la_dpn=lectura.propias_de_la_dpn,
            oficinas=len(lectura.oficinas),
            avisos=list(lectura.avisos),
        )

        doc_version_id = self._version_documental(captura_id, lectura.seccion)
        nacional_id = self._organismo(ORGANISMO_NACIONAL, JURISDICCION_NACIONAL)
        sin_mapear: set[str] = set()

        for oficina in lectura.oficinas:
            if not oficina.direccion:
                resultado.sin_direccion += 1
            if oficina.correo_ofuscado:
                resultado.correos_no_tomados += 1

            jurisdiccion = self._jurisdiccion(oficina.jurisdiccion_listada)
            if jurisdiccion is None and oficina.jurisdiccion_listada:
                sin_mapear.add(oficina.jurisdiccion_listada)

            # Acá está la decisión: de quién es la oficina. En las dos primeras
            # secciones, de la DPN. En la tercera, del organismo listado, que
            # además pertenece a su propia jurisdicción, no a la nacional.
            if lectura.propias_de_la_dpn:
                titular_id, operador_id = nacional_id, None
            else:
                titular_id = self._organismo(oficina.nombre, jurisdiccion or JURISDICCION_NACIONAL)
                operador_id = nacional_id

            evidencia_id = self._evidencia(doc_version_id, oficina, lectura.seccion)
            if not lectura.propias_de_la_dpn:
                resultado.alcance_sin_declarar += int(
                    alcance_de(oficina.nombre)[0] == AlcanceTerritorial.NO_DECLARADO.value
                )
            punto_id, nuevo = self._punto(titular_id, operador_id, oficina, lectura, jurisdiccion)
            resultado.puntos_creados += int(nuevo)
            resultado.puntos_conocidos += int(not nuevo)

            self._version_de_punto(punto_id, oficina, capturado_en)
            resultado.canales += self._canales(
                punto_id, titular_id, evidencia_id, oficina, capturado_en
            )

        resultado.jurisdicciones_sin_mapear = len(sin_mapear)
        self._avisos(resultado, sin_mapear)
        return resultado

    # --- Internos -----------------------------------------------------------

    def _catalogo_de_jurisdicciones(self) -> dict[str, str]:
        filas = self.conexion.execute(text("SELECT id, nombre FROM jurisdicciones")).all()
        catalogo = {_clave(nombre): jid for jid, nombre in filas}
        for alias, nombre in ALIAS_JURISDICCIONES.items():
            destino = catalogo.get(_clave(nombre))
            if destino is not None:
                catalogo[_clave(alias)] = destino
        return catalogo

    def _jurisdiccion(self, listada: str | None) -> str | None:
        """La jurisdicción del rótulo, si el catálogo la reconoce.

        No se adivina: una jurisdicción inventada ubica una oficina donde no
        está y manda a alguien a otra provincia.
        """
        if not listada:
            return None
        return self._jurisdicciones.get(_clave(listada))

    def _avisos(self, resultado: ResultadoDpn, sin_mapear: set[str]) -> None:
        if resultado.propias_de_la_dpn:
            resultado.avisos.append(
                f"«{resultado.seccion}»: {resultado.oficinas} oficina(s) de la Defensoría del "
                "Pueblo de la Nación."
            )
        else:
            resultado.avisos.append(
                f"«{resultado.seccion}»: {resultado.oficinas} organismo(s) autónomo(s) que la "
                "DPN lista y que no son oficinas suyas. Quedan con su propio organismo titular "
                "y con la DPN como quien los publica: responder «te atiende la Defensoría de la "
                "Nación» mandaría a la gente al organismo equivocado."
            )
            self.conexion.execute(
                text(
                    "INSERT INTO incidencias_revision (tipo, severidad, estado, source_id, "
                    " descripcion, responsable_rol) "
                    "VALUES (:t, :s, 'ABIERTA', :src, :d, 'curador de datos') "
                ),
                {
                    "t": TipoIncidencia.CONFLICTO_DE_FUENTES.value,
                    "s": Severidad.MEDIUM.value,
                    "src": SOURCE_ID,
                    "d": (
                        f"{resultado.oficinas} defensorías provinciales y municipales se "
                        "cargaron desde el directorio de la DPN. Su competencia y sus horarios "
                        "los publica cada organismo, no la DPN: hay que contrastar con la "
                        "fuente propia de cada uno antes de servir estos datos."
                    ),
                },
            )
        if resultado.alcance_sin_declarar:
            resultado.avisos.append(
                f"{resultado.alcance_sin_declarar} organismo(s) no declaran en su nombre si son "
                "provinciales o municipales, y quedan con el alcance sin declarar. «Defensor "
                "del Pueblo de Salta» puede ser el provincial o el de la capital: responder el "
                "equivocado manda a alguien a un organismo sin competencia sobre su reclamo."
            )
        if resultado.correos_no_tomados:
            resultado.avisos.append(
                f"{resultado.correos_no_tomados} dirección(es) de correo vienen ofuscadas por "
                "una protección contra recolección automática. Se registra que el canal existe "
                "y no se decodifica el valor."
            )
        if resultado.sin_direccion:
            resultado.avisos.append(
                f"{resultado.sin_direccion} oficina(s) no publican dirección. Quedan sin ella: "
                "una dirección que el directorio no da no se completa con la de la sede central."
            )
        if sin_mapear:
            resultado.avisos.append(
                f"Jurisdicción no reconocida en el catálogo: {', '.join(sorted(sin_mapear))}. "
                "Esas oficinas quedan bajo la jurisdicción nacional en vez de una provincia "
                "adivinada."
            )

    def _organismo(self, nombre: str, jurisdiccion_id: str) -> uuid.UUID:
        return self.conexion.execute(
            text(
                "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) VALUES (:j, :n, :t) "
                "ON CONFLICT (jurisdiccion_id, nombre, tipo) DO UPDATE SET nombre = :n "
                "RETURNING id"
            ),
            {
                "j": jurisdiccion_id,
                "n": nombre[:300],
                "t": TipoOrganismo.ORGANISMO_CONTROL.value,
            },
        ).scalar_one()

    def _punto(
        self,
        titular_id: uuid.UUID,
        operador_id: uuid.UUID | None,
        oficina: Oficina,
        lectura: Lectura,
        jurisdiccion: str | None,
    ) -> tuple[uuid.UUID, bool]:
        # Una receptoría o una oficina regional son delegaciones de la DPN. La
        # sede de un defensor autónomo es su sede, no la delegación de nadie.
        tipo = (
            TipoPuntoAtencion.DELEGACION
            if lectura.propias_de_la_dpn and _clave(oficina.nombre) != "sede central"
            else TipoPuntoAtencion.SEDE
        )
        # Una oficina de la DPN sirve a todo el país; la de un organismo
        # autónomo sirve a lo que su nombre declare, y muchas veces no lo dice.
        if lectura.propias_de_la_dpn:
            alcance, ambito = AlcanceTerritorial.NACIONAL.value, None
        else:
            alcance, ambito = alcance_de(oficina.nombre)

        ya = self.conexion.execute(
            text(
                "SELECT id FROM puntos_atencion WHERE organismo_id = :o AND nombre = :n "
                "  AND tipo = :t"
            ),
            {"o": titular_id, "n": oficina.nombre, "t": tipo.value},
        ).scalar_one_or_none()
        if ya is not None:
            return ya, False
        creado = self.conexion.execute(
            text(
                "INSERT INTO puntos_atencion (organismo_id, organismo_operador_id, "
                " jurisdiccion_id, nombre, tipo, alcance, ambito) "
                "VALUES (:o, :op, :j, :n, :t, :a, :amb) RETURNING id"
            ),
            {
                "o": titular_id,
                # Quien publica el listado no es quien atiende. La distinción es
                # el punto entero de esta importación.
                "op": operador_id,
                "j": jurisdiccion or JURISDICCION_NACIONAL,
                "n": oficina.nombre,
                "t": tipo.value,
                "a": alcance,
                "amb": ambito,
            },
        ).scalar_one()
        return creado, True

    def _version_de_punto(
        self, punto_id: uuid.UUID, oficina: Oficina, capturado_en: dt.datetime
    ) -> uuid.UUID:
        registro = self._nueva_version(EntidadVersionada.PUNTO_ATENCION, punto_id, capturado_en)
        observaciones = []
        if oficina.codigo_postal:
            observaciones.append(f"Código postal declarado: {oficina.codigo_postal}.")
        if oficina.jurisdiccion_listada:
            observaciones.append(
                f"Agrupada por el directorio bajo «{oficina.jurisdiccion_listada}»."
            )
        self.conexion.execute(
            text(
                "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_cruda, "
                " localidad, es_presencial, observaciones) "
                "VALUES (:rv, :p, :dir, :loc, true, :obs)"
            ),
            {
                "rv": registro,
                "p": punto_id,
                "dir": oficina.direccion,
                "loc": oficina.localidad,
                "obs": " ".join(observaciones) or None,
            },
        )
        return registro

    def _canales(
        self,
        punto_id: uuid.UUID,
        organismo_id: uuid.UUID,
        evidencia_id: uuid.UUID,
        oficina: Oficina,
        capturado_en: dt.datetime,
    ) -> int:
        creados = 0
        for telefono in oficina.telefonos:
            self._canal(
                punto_id,
                organismo_id,
                evidencia_id,
                capturado_en,
                TipoCanal.WHATSAPP if es_whatsapp(telefono) else TipoCanal.TELEFONO,
                telefono,
                normalizado=normalizar_telefono(telefono),
            )
            creados += 1
        for tipo, valor in [
            *([(TipoCanal.WEB, oficina.web)] if oficina.web else []),
            *([(TipoCanal.PRESENCIAL, oficina.direccion)] if oficina.direccion else []),
        ]:
            self._canal(
                punto_id, organismo_id, evidencia_id, capturado_en, tipo, valor, normalizado=None
            )
            creados += 1

        if oficina.correo_ofuscado:
            # El canal existe: la oficina tiene correo. Lo que no se tiene es su
            # valor, y decodificarlo sería sortear una protección deliberada.
            self._canal(
                punto_id,
                organismo_id,
                evidencia_id,
                capturado_en,
                TipoCanal.EMAIL,
                "Correo publicado con protección contra recolección automática; "
                "el valor no se toma. Se consulta en el sitio del organismo.",
                normalizado=None,
                publico=False,
            )
            creados += 1
        return creados

    def _canal(
        self,
        punto_id: uuid.UUID,
        organismo_id: uuid.UUID,
        evidencia_id: uuid.UUID,
        capturado_en: dt.datetime,
        tipo: TipoCanal,
        crudo: str,
        *,
        normalizado: str | None,
        publico: bool = True,
    ) -> None:
        canal_id = uuid.uuid4()
        registro = self._nueva_version(EntidadVersionada.CANAL, canal_id, capturado_en)
        self.conexion.execute(
            text(
                "INSERT INTO canales (registro_version_id, canal_id, organismo_id, "
                " punto_id, evidencia_id, tipo, valor_crudo, valor_normalizado, publico) "
                "VALUES (:rv, :c, :o, :p, :e, :t, :crudo, :norm, :pub)"
            ),
            {
                "rv": registro,
                "c": canal_id,
                "o": organismo_id,
                "p": punto_id,
                "e": evidencia_id,
                "t": tipo.value,
                "crudo": crudo,
                "norm": normalizado,
                "pub": publico,
            },
        )

    def _nueva_version(
        self, entidad: EntidadVersionada, entidad_id: uuid.UUID, capturado_en: dt.datetime
    ) -> uuid.UUID:
        parametros = {"tipo": entidad.value, "eid": entidad_id}
        self.conexion.execute(
            text(
                "UPDATE registro_versiones SET known_hasta = :ahora "
                " WHERE entidad_tipo = :tipo AND entidad_id = :eid AND known_hasta IS NULL"
            ),
            {**parametros, "ahora": capturado_en},
        )
        siguiente = self.conexion.execute(
            text(
                "SELECT coalesce(max(numero_version), 0) + 1 FROM registro_versiones "
                " WHERE entidad_tipo = :tipo AND entidad_id = :eid"
            ),
            parametros,
        ).scalar_one()
        return self.conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo, valid_desde, known_desde) "
                "VALUES (:tipo, :eid, :nv, :estado, :vt, :desde, :ahora) RETURNING id"
            ),
            {
                **parametros,
                "nv": siguiente,
                "estado": EstadoRevision.CANDIDATE.value,
                "vt": ValidTipo.ABIERTO_FIN.value,
                "desde": capturado_en.date(),
                "ahora": capturado_en,
            },
        ).scalar_one()

    def _version_documental(self, captura_id: uuid.UUID, seccion: str) -> uuid.UUID:
        documento_id = self.conexion.execute(
            text(
                "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
                "VALUES (:s, :t, :titulo, :e) "
                "ON CONFLICT (source_id, external_id) DO UPDATE SET titulo = EXCLUDED.titulo "
                "RETURNING id"
            ),
            {
                "s": SOURCE_ID,
                "t": TipoDocumento.DIRECTORIO.value,
                "titulo": f"Directorio DPN — {seccion}",
                "e": f"dpn:{seccion.lower().replace(' ', '-')}",
            },
        ).scalar_one()
        sha = sha_de_la_captura(self.conexion, captura_id)
        ya = version_ya_existente(self.conexion, documento_id, captura_id, sha)
        if ya is not None:
            return ya
        siguiente = proxima_version(self.conexion, documento_id)
        return self.conexion.execute(
            text(
                "INSERT INTO documento_versiones (documento_id, captura_id, version, "
                " tipo_version, tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
                "VALUES (:d, :c, :v, :tv, :tf, :h, :m, :ev) RETURNING id"
            ),
            {
                "d": documento_id,
                "c": captura_id,
                "v": siguiente,
                "tv": TipoVersionDocumento.NO_DETERMINADO.value,
                "tf": TipoFecha.DESCONOCIDA.value,
                "h": sha,
                "m": ModoExtraccion.HTML.value,
                "ev": "dpn@2",
            },
        ).scalar_one()

    def _evidencia(self, doc_version_id: uuid.UUID, oficina: Oficina, seccion: str) -> uuid.UUID:
        partes = [
            f"[{seccion}] {oficina.nombre}",
            oficina.direccion,
            f"({oficina.codigo_postal}) {oficina.localidad}" if oficina.localidad else None,
            " / ".join(oficina.telefonos) or None,
            oficina.web,
        ]
        fragmento = " | ".join(p for p in partes if p)
        # El selector nombra la oficina, no su posición en la página: si mañana
        # el directorio reordena los paneles, la evidencia sigue apuntando a la
        # misma oficina y no a la que quedó en ese lugar.
        selector = f"panel[{oficina.jurisdiccion_listada or '?'}] h4:{oficina.nombre}"
        ya = self.conexion.execute(
            # Puede haber más de una: la evidencia es inmutable y varios
            # curadores citan la misma unidad con el mismo selector. Se toma la
            # más antigua para que la elección no dependa del orden de carga;
            # pedir exactamente una detiene el comando entero por un empate que
            # no cambia nada de lo que se afirma.
            text(
                "SELECT id FROM evidencias WHERE doc_version_id = :d AND selector = :s "
                " ORDER BY creado_en, id LIMIT 1"
            ),
            {"d": doc_version_id, "s": selector},
        ).scalar_one_or_none()
        if ya is not None:
            return ya
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, fragmento, selector, tipo, "
                " hash_fragmento) VALUES (:dv, :f, :s, :t, :h) RETURNING id"
            ),
            {
                "dv": doc_version_id,
                "f": fragmento,
                "s": selector,
                "t": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
            },
        ).scalar_one()
