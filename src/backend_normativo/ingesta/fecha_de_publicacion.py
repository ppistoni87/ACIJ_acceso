"""Traer la fecha de publicación que falta, de la fuente oficial que sí contesta.

Cuarenta y seis versiones de norma quedaron fuera de todo corte con el intervalo
de aplicación en `DESCONOCIDO`. No es un problema de criterio jurídico: es que a
sus documentos les falta el dato más básico, **cuándo se publicaron**. Sin esa
fecha no se puede aplicar el artículo 5 del Código Civil y Comercial —una norma
rige a los ocho días corridos de su publicación oficial si no fija otra fecha—,
así que la vigencia no se puede determinar y el texto no se sirve.

**Por qué faltaba.** Treinta y ocho de esos documentos se capturaron de InfoLeg,
que sirve el texto pero no la ficha con los metadatos. Al pedirle la ficha hoy
responde 403: eso se registra como acceso limitado y la fuente se pausa. No se
rota identidad, no se reintenta con otro agente y no se busca la vuelta.

**De dónde sale entonces.** Del portal oficial de normativa nacional, que publica
las mismas normas con su fecha y responde 200. No es esquivar el bloqueo: es
otra fuente oficial, con su propia URL, su propia captura y su propio hash. El
identificador de InfoLeg está en la URL del documento que ya tenemos y es el
mismo que usa el portal, así que la correspondencia es exacta y no se adivina.

**Lo que este módulo no hace.** No infiere una fecha cuando la ficha no la trae:
la cuenta como no resuelta y sigue. No toca los tres documentos de CABA, que
vienen del Boletín Oficial de la Ciudad y necesitan otra fuente. Y no decide
vigencias: sólo deja el dato para que el resolvedor haga su trabajo.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.ingesta.cliente import ClienteCaptura

# La ficha oficial de una norma nacional. El número es el identificador de
# InfoLeg, que el portal reusa tal cual.
FICHA = "https://www.argentina.gob.ar/normativa/nacional/norma-{id}"

# De la URL del documento que ya tenemos al identificador. Las dos formas que
# aparecen en el corpus: la de InfoLeg y la del propio portal.
DE_INFOLEG = re.compile(r"/(\d{4,7})/(?:norma|texact|texactley)\.htm", re.I)
DEL_PORTAL = re.compile(r"norma-(\d+)")

# La ficha enlaza el boletín del día en que salió. Ese enlace es el dato.
FECHA_EN_LA_FICHA = re.compile(r"fecha_publicacion=(\d{2})-(\d{2})-(\d{4})")

SOURCE_DEL_PORTAL = "D01"

# Con qué se hizo la corrida. Va versionado como el resto: si mañana la ficha
# cambia de forma y el patrón deja de encontrar la fecha, se sabe qué corridas
# usaron cuál lector.
VERSION = "ficha-normativa@1"


class SinConfiguracion(Exception):
    """La fuente no tiene configuración vigente con la que capturar."""


@dataclass
class Resultado:
    resueltas: int = 0
    sin_fecha_en_la_ficha: list[str] = field(default_factory=list)
    sin_identificador: list[str] = field(default_factory=list)
    no_alcanzadas: list[str] = field(default_factory=list)
    simulado: bool = False


PENDIENTES = """
SELECT DISTINCT dv.id AS doc_version_id, cap.url_final,
       n.tipo || ' ' || coalesce(n.numero, '?') || '/' || coalesce(n.anio::text, '?') AS norma
  FROM registro_versiones rv
  JOIN norma_versiones nv ON nv.registro_version_id = rv.id
  JOIN normas n ON n.id = nv.norma_id
  JOIN documento_versiones dv ON dv.id = nv.doc_version_id
  JOIN capturas cap ON cap.id = dv.captura_id
 WHERE rv.entidad_tipo = 'norma'
   AND rv.valid_tipo = 'DESCONOCIDO'
   AND dv.fecha_documento IS NULL
 ORDER BY 3
"""


def identificador(url: str | None) -> str | None:
    """El número de InfoLeg que el portal oficial reusa, o nada."""
    for patron in (DE_INFOLEG, DEL_PORTAL):
        encontrado = patron.search(url or "")
        if encontrado:
            return encontrado.group(1)
    return None


def fecha_de(html: str) -> dt.date | None:
    """La fecha de publicación que declara la ficha. Sin ella, nada."""
    encontrada = FECHA_EN_LA_FICHA.search(html)
    if not encontrada:
        return None
    dia, mes, anio = (int(parte) for parte in encontrada.groups())
    try:
        return dt.date(anio, mes, dia)
    except ValueError:
        # Una fecha imposible en la fuente no se corrige ni se aproxima.
        return None


def _url_de_la_fuente(conexion: Connection, url: str) -> uuid.UUID:
    """La `fuente_url` de la ficha, creada la primera vez que se la pide."""
    existente = conexion.execute(
        text("SELECT id FROM fuente_urls WHERE url = :u LIMIT 1"), {"u": url}
    ).scalar_one_or_none()
    if existente is not None:
        return existente
    return conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso, es_canonica) "
            "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO', false) RETURNING id"
        ),
        {"s": SOURCE_DEL_PORTAL, "u": url},
    ).scalar_one()


def _abrir_corrida(conexion: Connection) -> uuid.UUID:
    """La corrida va contra la configuración vigente de la fuente.

    La base la exige y tiene razón: una captura sin decir con qué configuración
    se hizo no se puede reproducir después.
    """
    config = conexion.execute(
        text(
            "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
            " ORDER BY version DESC LIMIT 1"
        ),
        {"s": SOURCE_DEL_PORTAL},
    ).scalar_one_or_none()
    if config is None:
        raise SinConfiguracion(
            f"La fuente {SOURCE_DEL_PORTAL} no tiene configuración vigente: sin ella la "
            "captura no se puede reproducir y no se hace."
        )
    return conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, extractor_version, "
            " estado, solicitadas) VALUES (:s, :c, :v, 'EN_CURSO', 0) RETURNING id"
        ),
        {"s": SOURCE_DEL_PORTAL, "c": config, "v": VERSION},
    ).scalar_one()


def completar(
    conexion: Connection,
    *,
    actor: str,
    limite: int | None = None,
    simular: bool = False,
    cliente: ClienteCaptura | None = None,
) -> Resultado:
    """Captura la ficha oficial de cada norma sin fecha y le pone la que declara."""
    pendientes = conexion.execute(text(PENDIENTES)).mappings().all()
    if limite is not None:
        pendientes = pendientes[:limite]

    resultado = Resultado(simulado=simular)
    if simular:
        for fila in pendientes:
            if identificador(fila["url_final"]):
                resultado.resueltas += 1
            else:
                resultado.sin_identificador.append(fila["norma"])
        return resultado

    corrida = _abrir_corrida(conexion)
    propio = cliente is None
    cliente = cliente or ClienteCaptura()
    try:
        for fila in pendientes:
            numero = identificador(fila["url_final"])
            if numero is None:
                # Los de CABA vienen del Boletín de la Ciudad y necesitan otra
                # fuente. No se los fuerza contra un portal que no los tiene.
                resultado.sin_identificador.append(fila["norma"])
                continue

            url = FICHA.format(id=numero)
            descarga = cliente.descargar(url)
            if not descarga.exitosa:
                resultado.no_alcanzadas.append(
                    f"{fila['norma']} ({descarga.error or 'sin cuerpo'})"
                )
                continue

            cuerpo = descarga.contenido.decode("utf-8", errors="replace")
            fecha = fecha_de(cuerpo)
            if fecha is None:
                resultado.sin_fecha_en_la_ficha.append(fila["norma"])
                continue

            _registrar(conexion, corrida, url, descarga, cuerpo, fila, fecha, actor)
            resultado.resueltas += 1
    finally:
        if propio:
            cliente.cerrar()
        # Los contadores cierran o la corrida no es COMPLETA: la base exige que
        # procesadas + rechazadas = solicitadas, y tiene razón —una corrida que
        # no cuadra es una que perdió algo sin decirlo—. Lo descargado no
        # incluye lo que ni se pidió: los documentos de CABA no tienen ficha en
        # este portal y se cuentan como rechazados, no como bajados.
        rechazadas = (
            len(resultado.sin_identificador)
            + len(resultado.sin_fecha_en_la_ficha)
            + len(resultado.no_alcanzadas)
        )
        descargadas = len(pendientes) - len(resultado.sin_identificador)
        completa = resultado.resueltas + rechazadas == len(pendientes)
        conexion.execute(
            text(
                "UPDATE corridas_ingesta SET estado = :estado, fin = now(), "
                "       solicitadas = :n, descargadas = :d, procesadas = :p, "
                "       rechazadas = :x WHERE id = :c"
            ),
            {
                "c": corrida,
                "estado": "COMPLETA" if completa else "PARCIAL",
                "n": len(pendientes),
                "d": descargadas,
                "p": resultado.resueltas,
                "x": rechazadas,
            },
        )
    return resultado


def _registrar(
    conexion: Connection,
    corrida: uuid.UUID,
    url: str,
    descarga,
    cuerpo: str,
    fila,
    fecha: dt.date,
    actor: str,
) -> None:
    """La captura, la evidencia y la fecha. En ese orden y con ese respaldo."""
    import json

    sha = hashlib.sha256(descarga.contenido).hexdigest()
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, "
            " capturado_en, mime, bytes, sha256_raw, objeto_uri, cabeceras, redirecciones) "
            "VALUES (:c, :u, :final, :st, :cuando, :mime, :bytes, :sha, :obj, "
            "        CAST(:cab AS jsonb), CAST(:red AS jsonb)) RETURNING id"
        ),
        {
            "c": corrida,
            "u": _url_de_la_fuente(conexion, url),
            "final": descarga.url_final,
            "st": descarga.http_status,
            "cuando": descarga.capturado_en,
            "mime": descarga.mime,
            "bytes": len(descarga.contenido),
            "sha": sha,
            "obj": f"sha256://{sha}",
            "cab": json.dumps(descarga.cabeceras, ensure_ascii=False),
            "red": json.dumps(descarga.redirecciones, ensure_ascii=False),
        },
    ).scalar_one()

    # La evidencia cita el trozo exacto de la ficha que declara la fecha, no la
    # página entera: que se pueda comprobar es la mitad del trabajo. Cuelga del
    # documento de la norma —que es donde alguien la va a buscar— y el
    # `selector` dice de qué captura salió, porque no salió de ahí: el texto
    # vino de InfoLeg y la fecha de la ficha del portal.
    fragmento = f"fecha_publicacion={fecha.strftime('%d-%m-%Y')}"
    conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, fragmento, selector, hash_fragmento, tipo) "
            "VALUES (:dv, :f, :sel, :h, 'FRAGMENTO_TEXTO')"
        ),
        {
            "dv": fila["doc_version_id"],
            "f": fragmento,
            "sel": f"captura:{captura} · {url}",
            "h": hashlib.sha256(fragmento.encode()).hexdigest(),
        },
    )
    conexion.execute(
        text(
            "UPDATE documento_versiones SET fecha_documento = :f, tipo_fecha = 'PUBLICACION' "
            " WHERE id = :dv"
        ),
        {"f": fecha, "dv": fila["doc_version_id"]},
    )
    conexion.execute(
        text(
            "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, "
            " despues_hash, motivo) "
            "VALUES (:a, 'FECHAR_PUBLICACION', 'documento_version', :o, :h, :m)"
        ),
        {
            "a": actor,
            "o": str(fila["doc_version_id"]),
            "h": sha,
            "m": (
                f"Fecha de publicación {fecha.isoformat()} tomada de la ficha oficial {url}, "
                f"capturada con sha256 {sha[:16]}. InfoLeg no sirve la ficha (403) y quedó "
                "registrada como acceso limitado."
            ),
        },
    )
