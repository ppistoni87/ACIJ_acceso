"""HU-035: traer al corpus las normas que el propio corpus cita.

El corpus arranca con las 83 fuentes que relevó el manual, y esas 83 no se
tocan: son el inventario contra el que se concilia. Pero las normas que sí están
citan otras, y esas citas quedan registradas como referencias pendientes. Una
referencia pendiente es una pregunta escrita: «esta norma dice que depende de
aquella y aquella no está».

El catálogo nacional que ya se importó sabe la respuesta para buena parte de
ellas: trae, por cada norma, la URL de su texto consolidado en InfoLEG. Así que
ampliar el corpus no es salir a buscar: es capturar el texto que el catálogo ya
identificó, para las normas que el corpus ya dijo necesitar.

Lo que no se hace acá es adivinar. Una referencia se amplía solo si resuelve a
una y una sola norma nacional, esa norma no está marcada como de identidad
incierta, y el catálogo tiene su texto consolidado. Cualquier otra cosa —una
referencia sin año, un número que en el catálogo aparece tres veces, una norma
cuya numeración por organismo no la distingue— se informa con su motivo y no se
resuelve: elegir una de tres por orden de aparición sería inventar la cita que
la referencia justamente dejó abierta.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    Adaptador,
    ClaseFuente,
    EstadoFuente,
)

SOURCE_ID = "N01"
NOMBRE_FUENTE = "Textos consolidados de normas citadas por el corpus (InfoLEG)"
POLITICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"
ORIGEN = "citada_por_el_corpus"
RUTA_CURADURIA = pathlib.Path("docs/curaduria")

# El catálogo publica dos formas de texto y las dos sirven, pero no dicen lo
# mismo: `texact.htm` es el texto consolidado, con las modificaciones ya
# incorporadas, y `norma.htm` es el texto como se publicó. Una norma
# modificatoria suele tener solo el segundo, y es el que corresponde: lo que
# dice esa norma es lo que publicó. Guardar cuál de los dos se trajo no es un
# detalle: citar un consolidado como si fuera el original, o al revés, cambia
# qué texto respalda una afirmación.
TEXTO_CONSOLIDADO = "texact.htm"
TEXTO_ORIGINAL = "norma.htm"
FORMAS_DE_TEXTO = (TEXTO_CONSOLIDADO, TEXTO_ORIGINAL)


@dataclass
class Candidata:
    tipo: str
    numero: str
    anio: int
    titulo: str
    url: str
    norma_id: uuid.UUID
    citas: int
    """Cuántas referencias pendientes distintas apuntan a esta norma."""
    tipo_texto: str = TEXTO_CONSOLIDADO
    """`texact.htm` si es el consolidado, `norma.htm` si es el texto publicado."""


@dataclass
class Descartada:
    tipo: str
    numero: str
    anio: int | None
    motivo: str


@dataclass
class ResultadoAmpliacion:
    agregadas: list[Candidata] = field(default_factory=list)
    ya_estaban: list[Candidata] = field(default_factory=list)
    descartadas: list[Descartada] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def registrar_fuente(conexion: Connection) -> str:
    """Da de alta la fuente derivada, si no está.

    Se registra con `origen` propio y no como una de las 83 del manual: el
    inventario del corpus tiene que seguir diciendo lo que el manual dice. Una
    norma que entra porque otra la cita es trazable a esa cita, no a un
    relevamiento.
    """
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, prioridad, "
            " politica_acceso, responsable_rol, alcance, origen, tarea) "
            "VALUES (:sid, :nombre, :clase, :estado, 'NO_VERIFICADO', 'P2', :politica, "
            "        'curacion_juridica', :alcance, :origen, :tarea) "
            "ON CONFLICT (source_id) DO NOTHING"
        ),
        {
            "sid": SOURCE_ID,
            "nombre": NOMBRE_FUENTE,
            "clase": ClaseFuente.PORTAL_NORMATIVO.value,
            "estado": EstadoFuente.DISCOVERY.value,
            "politica": POLITICA,
            "origen": ORIGEN,
            "alcance": (
                "Normas que el corpus cita y no tenía. Cada URL entra porque una referencia "
                "pendiente la nombra y el catálogo nacional identifica su texto consolidado. "
                "No integra el inventario de las 83 fuentes del manual."
            ),
            "tarea": (
                "Capturar el texto consolidado de las normas citadas por el corpus, para que "
                "las condiciones que definen dejen de estar declaradas y no evaluables."
            ),
        },
    )
    conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador, frecuencia, "
            " ttl_defecto, presupuesto, politica_version) "
            "VALUES (:s, 1, :a, interval '90 days', interval '90 days', "
            "        CAST(:p AS jsonb), :pol) "
            "ON CONFLICT (source_id, version) DO NOTHING"
        ),
        {
            "s": SOURCE_ID,
            "a": Adaptador.HTML_ESTATICO.value,
            "p": json.dumps(
                {
                    "validar_tls": True,
                    "concurrencia": 1,
                    "reintentos_max": 3,
                    "delay_dominio_s": 2.0,
                    "respetar_robots": True,
                }
            ),
            "pol": "acceso-fuentes-publicas@1",
        },
    )
    return SOURCE_ID


def _identidades_citadas(conexion: Connection) -> list[dict]:
    """Identidades que las referencias pendientes nombran, con cuántas las nombran.

    Solo las que cita una norma nacional. Una ordenanza porteña que cita la
    «Ley 3706» no está citando una ley nacional con ese número, y resolverla
    contra el catálogo nacional traería el texto equivocado con apariencia de
    dato verificado.
    """
    return [
        dict(fila)
        for fila in conexion.execute(
            text(
                "SELECT rp.identidad_candidata->>'tipo' AS tipo, "
                "       rp.identidad_candidata->>'numero' AS numero, "
                "       rp.identidad_candidata->>'anio' AS anio, "
                "       count(*) AS citas "
                "  FROM referencias_pendientes rp "
                "  JOIN normas orig ON orig.id = rp.norma_origen_id "
                " WHERE rp.estado = 'PENDIENTE' AND orig.jurisdiccion_id = 'AR' "
                "   AND rp.identidad_candidata->>'tipo' IS NOT NULL "
                "   AND rp.identidad_candidata->>'numero' IS NOT NULL "
                " GROUP BY 1, 2, 3"
            )
        ).mappings()
    ]


def _resolver(conexion: Connection, tipo: str, numero: str, anio: int) -> tuple[list[dict], str]:
    filas = [
        dict(f)
        for f in conexion.execute(
            text(
                "SELECT n.id, n.titulo, n.identidad_incierta, ni.url_oficial "
                "  FROM normas n "
                "  LEFT JOIN norma_identificadores ni ON ni.norma_id = n.id "
                " WHERE n.jurisdiccion_id = 'AR' AND n.tipo = :t AND n.numero = :n "
                "   AND n.anio = :a"
            ),
            {"t": tipo, "n": numero, "a": anio},
        ).mappings()
    ]
    if not filas:
        return [], "El catálogo nacional no tiene ninguna norma con esa identidad."
    if len({f["id"] for f in filas}) > 1:
        return filas, (
            f"La identidad resuelve a {len({f['id'] for f in filas})} normas del catálogo: el "
            "tipo se numera por organismo y la clave no las distingue. Elegir una sería "
            "inventar la cita."
        )
    if filas[0]["identidad_incierta"]:
        return filas, (
            "La norma está marcada como de identidad incierta en el catálogo: traer su texto "
            "afirmaría que la cita apunta ahí, que es justamente lo que no se sabe."
        )
    return filas, ""


def candidatas(conexion: Connection, limite: int | None = None) -> ResultadoAmpliacion:
    """Qué se puede traer y qué no, con el motivo de cada descarte."""
    resultado = ResultadoAmpliacion()
    ya_registradas = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT url FROM fuente_urls WHERE source_id = :s"), {"s": SOURCE_ID}
        )
    }
    for identidad in sorted(
        _identidades_citadas(conexion),
        key=lambda i: (-i["citas"], i["tipo"], i["numero"]),
    ):
        tipo, numero, anio = identidad["tipo"], identidad["numero"], identidad["anio"]
        if anio is None:
            resultado.descartadas.append(
                Descartada(
                    tipo,
                    numero,
                    None,
                    "La cita no dice el año. Sin año, el número solo no identifica una norma: "
                    "el catálogo tiene decenas con el mismo número en años distintos.",
                )
            )
            continue
        filas, motivo = _resolver(conexion, tipo, numero, int(anio))
        if motivo:
            resultado.descartadas.append(Descartada(tipo, numero, int(anio), motivo))
            continue
        # Se prefiere el consolidado cuando hay los dos: incorpora las
        # modificaciones posteriores, que es lo que hace falta para curar. Una
        # modificatoria normalmente solo tiene el publicado, y ahí ese es el
        # texto correcto: lo que esa norma dice es lo que publicó.
        con_texto = [
            f
            for forma in FORMAS_DE_TEXTO
            for f in filas
            if (f["url_oficial"] or "").endswith(forma)
        ]
        if not con_texto:
            resultado.descartadas.append(
                Descartada(
                    tipo,
                    numero,
                    int(anio),
                    "La norma está en el catálogo como metadato y sin texto publicado. Se sabe "
                    "que existe y no hay qué citar de ella.",
                )
            )
            continue
        # El catálogo publica en http; se pide por https porque la política no
        # admite bajar por un canal sin validación de certificado.
        url = con_texto[0]["url_oficial"].replace("http://", "https://", 1)
        candidata = Candidata(
            tipo=tipo,
            numero=numero,
            anio=int(anio),
            titulo=con_texto[0]["titulo"] or "",
            url=url,
            norma_id=con_texto[0]["id"],
            citas=identidad["citas"],
            tipo_texto=TEXTO_CONSOLIDADO if url.endswith(TEXTO_CONSOLIDADO) else TEXTO_ORIGINAL,
        )
        if url in ya_registradas:
            resultado.ya_estaban.append(candidata)
            continue
        resultado.agregadas.append(candidata)
        if limite is not None and len(resultado.agregadas) >= limite:
            break
    return resultado


def ampliar(conexion: Connection, limite: int | None = None) -> ResultadoAmpliacion:
    """Registra las URLs de las normas citadas que se pueden traer.

    No captura: deja las URLs listas para que las recorra el mismo capturador
    que recorre todo lo demás, con la misma política y el mismo registro de
    corrida. Traerlas por un camino propio dejaría normas en el corpus sin la
    corrida que las explica.
    """
    resultado = candidatas(conexion, limite)
    if not resultado.agregadas:
        return resultado
    registrar_fuente(conexion)
    for candidata in resultado.agregadas:
        conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') "
                "ON CONFLICT (source_id, url) DO NOTHING"
            ),
            {"s": SOURCE_ID, "u": candidata.url},
        )
    resultado.avisos.append(
        f"{len(resultado.agregadas)} URL(s) quedaron registradas y sin capturar. "
        f"`bn ingesta capturar {SOURCE_ID}` las trae y `bn ingesta extraer` las segmenta."
    )
    return resultado


def informe(conexion: Connection, raiz: pathlib.Path | None = None) -> str:
    """Qué se trajo, qué se curó y qué no, con el motivo de cada cosa.

    Traer una norma al corpus no es leerla. Sin este informe, veintiséis normas
    nuevas con texto y sin lectura se ven igual que veintiséis normas leídas:
    el corpus crece y nadie sabe qué parte de ese crecimiento se puede
    responder.
    """
    base = (raiz or pathlib.Path.cwd()) / RUTA_CURADURIA
    curadas = set()
    if base.is_dir():
        for archivo in sorted(base.glob("*.json")):
            lectura = json.loads(archivo.read_text(encoding="utf-8"))
            curadas.add(lectura["norma"]["external_id"])

    filas = [
        dict(f)
        for f in conexion.execute(
            text(
                "SELECT d.external_id, n.tipo || ' ' || n.numero || '/' || n.anio::text AS norma, "
                "       coalesce(n.titulo, '') AS titulo, count(u.id) AS unidades "
                "  FROM documentos d "
                "  JOIN documento_versiones dv ON dv.documento_id = d.id "
                "  JOIN norma_versiones nv ON nv.doc_version_id = dv.id "
                "  JOIN normas n ON n.id = nv.norma_id "
                "  JOIN unidades_documentales u ON u.doc_version_id = dv.id "
                " WHERE d.source_id = :s "
                " GROUP BY 1, 2, 3 ORDER BY 2"
            ),
            {"s": SOURCE_ID},
        ).mappings()
    ]
    lineas = [
        "# Normas que el corpus citaba y ahora tiene",
        "",
        "Las normas del corpus citan otras. Cada cita que no resuelve queda como",
        "referencia pendiente, y el catálogo nacional sabe dónde está el texto de buena",
        "parte de ellas. Esta es la lista de las que se trajeron con `bn ingesta ampliar`.",
        "",
        "Traerlas no es leerlas, y la diferencia importa: una norma con texto y sin",
        "lectura curada está en el corpus y no puede contestar nada. La columna dice",
        "cuál es cuál.",
        "",
        "| Norma | Unidades | Lectura curada |",
        "| --- | ---: | --- |",
    ]
    sin_curar = 0
    for fila in filas:
        tiene = fila["external_id"] in curadas
        sin_curar += int(not tiene)
        lineas.append(
            f"| {fila['norma']} — {fila['titulo'][:44]} | {fila['unidades']} | "
            f"{'sí' if tiene else '—'} |"
        )
    lineas += [
        "",
        f"**{len(filas)}** normas con texto, **{len(filas) - sin_curar}** con lectura curada y "
        f"**{sin_curar}** sin curar.",
        "",
    ]

    # La mayoría de lo que no está curado fija importes para un período, y esos
    # períodos ya pasaron. Decirlo con el dato adelante evita las dos lecturas
    # equivocadas: que falta curarlas por descuido, o que sirven para contestar
    # cuánto se cobra.
    montos = [f for f in filas if _fija_importes(f["titulo"]) and f["external_id"] not in curadas]
    if montos:
        ultimo = max(int(f["norma"].rsplit("/", 1)[1]) for f in montos)
        lineas += [
            "## Por qué la mayoría no está curada",
            "",
            f"De las {sin_curar} sin curar, **{len(montos)}** fijan rangos, topes y montos para un",
            "período determinado. No se curan como cuantía y no es una omisión: son una cadena en",
            "la que cada una reemplaza a la anterior, y la más nueva que el corpus tiene es de",
            f"**{ultimo}**. Servir cualquiera de ellas como el monto de hoy sería dar por vigente",
            "un importe de hace años, que es peor que decir que no se sabe. Los montos vigentes",
            "salen de resoluciones de ANSES bajo la fórmula de movilidad, y esas no están en el",
            "corpus: es la dependencia que las lecturas curadas ya declaran.",
            "",
            "Lo que sí aportan es la cadena: sirven para explicar desde cuándo rige cada escala y",
            "para reconstruir un período pasado, que es una pregunta distinta de cuánto se cobra",
            "este mes.",
            "",
            "Las demás sin curar modifican artículos cuyo texto vigente ya está curado desde el",
            "texto consolidado de la Ley 24.714. Curarlas aparte repetiría las mismas reglas sin",
            "agregar nada; lo que aportan es la trazabilidad, que ya da el grafo de relaciones.",
            "",
        ]
    return "\n".join(lineas) + "\n"


# Los títulos del catálogo nacional son escuetos y regulares: cuando una norma
# fija importes, lo dice en el título. No es una clasificación jurídica, es una
# forma de agrupar lo que no se curó para poder explicar por qué.
PALABRAS_DE_IMPORTES = ("RANGOS", "TOPES", "MONTOS", "SUMA", "INCREMENT", "MOVILIDAD", "SUPLEMENTO")


def _fija_importes(titulo: str) -> bool:
    return any(palabra in titulo.upper() for palabra in PALABRAS_DE_IMPORTES)
