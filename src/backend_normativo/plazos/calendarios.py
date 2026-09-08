"""HU-016: calendarios jurisdiccionales cargados desde su fuente oficial.

Un feriado sin evidencia es un día no laborable inventado, y con eso se calculan
vencimientos que después alguien pierde. El esquema lo impide —cada excepción de
calendario exige su evidencia—, así que el calendario entra por el mismo camino
que el resto del corpus: se captura la fuente, se guarda la captura inmutable y
cada feriado queda atado al fragmento que lo declara.

La fuente es operativa, no normativa. El manifiesto inventarió 83 fuentes del
corpus jurídico y ninguna es un calendario; el catálogo se carga igual y sigue
teniendo 83. Esta se registra aparte, con prefijo propio, cuando se pide cargar
un calendario: mezclarla con las del manual haría que el inventario del corpus
dijera algo que el manual no dice.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    Adaptador,
    ClaseFuente,
    EstadoFuente,
    ModoExtraccion,
    Severidad,
    TipoDocumento,
    TipoEvidencia,
    TipoFecha,
    TipoIncidencia,
    TipoVersionDocumento,
)
from backend_normativo.ingesta.almacen import AlmacenObjetos
from backend_normativo.plazos.computo import Calendario, Excepcion

SOURCE_ID = "C01"
NOMBRE_FUENTE = "Feriados nacionales (Ministerio del Interior, vía datos.gob.ar)"
POLITICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"
URL_PLANTILLA = "https://www.argentina.gob.ar/sites/default/files/holidays-{anio}-es.json"
JURISDICCION = "AR"


class CalendarioInvalido(Exception):
    """El archivo no tiene la forma que el contrato declara."""


@dataclass
class ResultadoCalendario:
    calendario_id: uuid.UUID | None = None
    nombre: str = ""
    version: str = ""
    desde: dt.date | None = None
    hasta: dt.date | None = None
    feriados_nuevos: int = 0
    feriados_conocidos: int = 0
    avisos: list[str] = field(default_factory=list)


def url_del_anio(anio: int) -> str:
    return URL_PLANTILLA.format(anio=anio)


def registrar_fuente(conexion: Connection) -> str:
    """Da de alta la fuente operativa del calendario, si no está.

    Se hace acá y no en `cargar_catalogo` para que el inventario del corpus siga
    teniendo exactamente las 83 fuentes que el manual relevó.
    """
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, prioridad, "
            " politica_acceso, responsable_rol, alcance, origen, tarea) "
            "VALUES (:sid, :nombre, :clase, :estado, 'NO_VERIFICADO', 'P1', :politica, "
            "        'ingesta', :alcance, 'operativa', :tarea) "
            "ON CONFLICT (source_id) DO NOTHING"
        ),
        {
            "sid": SOURCE_ID,
            "nombre": NOMBRE_FUENTE,
            "clase": ClaseFuente.DATASET.value,
            "estado": EstadoFuente.DISCOVERY.value,
            "politica": POLITICA,
            "alcance": (
                "Fuente operativa, no normativa: aporta el calendario que hace falta para "
                "computar plazos en días hábiles. No integra el inventario del corpus."
            ),
            "tarea": "Cargar feriados nacionales por año para el cómputo de plazos hábiles.",
        },
    )
    # La configuración de captura es parte del alta: una fuente sin ella no se
    # puede recorrer, y el capturador lo rechaza antes de pedir nada.
    conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador, frecuencia, "
            " ttl_defecto, presupuesto, politica_version) "
            "VALUES (:s, 1, :a, interval '365 days', interval '365 days', "
            "        CAST(:p AS jsonb), :pol) "
            "ON CONFLICT (source_id, version) DO NOTHING"
        ),
        {
            "s": SOURCE_ID,
            "a": Adaptador.DATASET_ABIERTO.value,
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


def registrar_url(conexion: Connection, anio: int) -> uuid.UUID:
    registrar_fuente(conexion)
    return conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'DESCARGA_ARCHIVO') "
            "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'DETALLE' RETURNING id"
        ),
        {"s": SOURCE_ID, "u": url_del_anio(anio)},
    ).scalar_one()


def importar(
    conexion: Connection,
    contenido: bytes,
    *,
    captura_id: uuid.UUID,
    anio: int,
    jurisdiccion: str = JURISDICCION,
) -> ResultadoCalendario:
    """Carga el calendario de un año, con una evidencia por feriado."""
    feriados = _leer(contenido, anio)
    version = str(anio)
    nombre = f"Feriados nacionales {anio}"
    resultado = ResultadoCalendario(
        nombre=nombre,
        version=version,
        desde=dt.date(anio, 1, 1),
        hasta=dt.date(anio, 12, 31),
    )

    calendario_id = conexion.execute(
        text(
            "INSERT INTO calendarios (jurisdiccion_id, nombre, version, fecha_desde, "
            " fecha_hasta, fuente_id) VALUES (:j, :n, :v, :desde, :hasta, :f) "
            "ON CONFLICT (jurisdiccion_id, nombre, version) DO UPDATE SET fuente_id = :f "
            "RETURNING id"
        ),
        {
            "j": jurisdiccion,
            "n": nombre,
            "v": version,
            "desde": resultado.desde,
            "hasta": resultado.hasta,
            "f": SOURCE_ID,
        },
    ).scalar_one()
    resultado.calendario_id = calendario_id

    doc_version_id = _version_documental(conexion, captura_id, anio)
    ya = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT fecha FROM calendario_excepciones WHERE calendario_id = :c"),
            {"c": calendario_id},
        )
    }

    for numero, (fecha, motivo) in enumerate(sorted(feriados.items()), start=1):
        if fecha in ya:
            resultado.feriados_conocidos += 1
            continue
        evidencia_id = _evidencia(conexion, doc_version_id, numero, fecha, motivo)
        conexion.execute(
            text(
                "INSERT INTO calendario_excepciones (calendario_id, evidencia_id, fecha, "
                " es_habil, motivo) VALUES (:c, :e, :f, false, :m)"
            ),
            {"c": calendario_id, "e": evidencia_id, "f": fecha, "m": motivo},
        )
        resultado.feriados_nuevos += 1

    resultado.avisos.append(
        f"El calendario cubre {resultado.desde.isoformat()} a {resultado.hasta.isoformat()}. "
        "Un plazo que se pase de ese rango queda no determinado hasta que se cargue el año "
        "siguiente: extrapolar feriados es inventarlos."
    )
    resultado.avisos.append(
        "Son feriados nacionales. Las ferias administrativas y judiciales, y los feriados "
        "provinciales, son otros calendarios: computar un plazo judicial con este daría una "
        "fecha equivocada."
    )
    resultado.avisos.append(
        "El archivo mezcla feriados inamovibles, trasladables, días no laborables y días no "
        "laborables con fines turísticos. Todos entran como no hábiles y conservan su clase en "
        "el motivo, porque no todos se computan igual en todos los regímenes: si una norma "
        "dispone otra cosa, es una decisión de revisión y no un ajuste silencioso del "
        "calendario."
    )
    return resultado


def cargar(
    conexion: Connection,
    *,
    jurisdiccion: str = JURISDICCION,
    para: dt.date | None = None,
    calendario_id: uuid.UUID | None = None,
) -> Calendario | None:
    """Trae el calendario que corresponde a una fecha, listo para computar."""
    if calendario_id is not None:
        condicion = "c.id = :cid"
        parametros: dict = {"cid": calendario_id}
    else:
        condicion = (
            "c.jurisdiccion_id = :j AND (CAST(:f AS date) IS NULL "
            "  OR :f BETWEEN c.fecha_desde AND c.fecha_hasta)"
        )
        parametros = {"j": jurisdiccion, "f": para}

    fila = (
        conexion.execute(
            text(
                "SELECT c.id, c.jurisdiccion_id, c.nombre, c.version, c.fecha_desde, "
                "       c.fecha_hasta FROM calendarios c "
                f" WHERE {condicion} ORDER BY c.fecha_desde DESC LIMIT 1"
            ),
            parametros,
        )
        .mappings()
        .first()
    )
    if fila is None:
        return None

    calendario = Calendario(
        id=str(fila["id"]),
        jurisdiccion=fila["jurisdiccion_id"],
        nombre=fila["nombre"],
        version=fila["version"],
        desde=fila["fecha_desde"],
        hasta=fila["fecha_hasta"],
    )
    for excepcion in conexion.execute(
        text(
            "SELECT fecha, es_habil, motivo FROM calendario_excepciones  WHERE calendario_id = :c"
        ),
        {"c": fila["id"]},
    ).mappings():
        calendario.excepciones[excepcion["fecha"]] = Excepcion(
            fecha=excepcion["fecha"],
            es_habil=excepcion["es_habil"],
            motivo=excepcion["motivo"],
        )
    return calendario


# --- Internos ---------------------------------------------------------------


def _leer(contenido: bytes, anio: int) -> dict[dt.date, str]:
    """Extrae fecha y motivo de cada feriado del archivo oficial."""
    try:
        datos = json.loads(contenido.decode("utf-8", "replace"))
    except json.JSONDecodeError as exc:
        raise CalendarioInvalido(f"El archivo no es JSON válido: {exc}") from exc

    elementos = (datos.get("mainEntity") or {}).get("itemListElement")
    # Una lista vacía es una forma válida sin feriados; que falte la lista es
    # otra cosa, y se distinguen porque el remedio es distinto.
    if not isinstance(elementos, list):
        raise CalendarioInvalido(
            "El archivo no trae `mainEntity.itemListElement`. Cambió de forma y no se "
            "importa a ciegas: un calendario mal leído produce vencimientos equivocados."
        )

    feriados: dict[dt.date, str] = {}
    for elemento in elementos:
        item = elemento.get("item") or {}
        crudo = (item.get("startDate") or "").strip()
        if not crudo:
            continue
        try:
            fecha = dt.date.fromisoformat(crudo)
        except ValueError:
            continue
        if fecha.year != anio:
            continue
        nombre = (item.get("name") or "Feriado").strip().rstrip(".")
        clase = ((item.get("additionalProperty") or {}).get("value") or "").strip()
        feriados[fecha] = f"{nombre} ({clase})" if clase else nombre

    if not feriados:
        raise CalendarioInvalido(
            f"El archivo no trae ningún feriado de {anio}. Cargar un calendario vacío haría "
            "que todos los plazos se computen como si no hubiera feriados."
        )
    return feriados


def _version_documental(conexion: Connection, captura_id: uuid.UUID, anio: int) -> uuid.UUID:
    documento_id = conexion.execute(
        text(
            "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
            "VALUES (:s, :t, :titulo, :e) "
            "ON CONFLICT (source_id, external_id) DO UPDATE SET titulo = EXCLUDED.titulo "
            "RETURNING id"
        ),
        {
            "s": SOURCE_ID,
            "t": TipoDocumento.DATASET.value,
            "titulo": f"Feriados nacionales {anio}",
            "e": f"feriados:{anio}",
        },
    ).scalar_one()
    ya = conexion.execute(
        text("SELECT id FROM documento_versiones WHERE documento_id = :d AND captura_id = :c"),
        {"d": documento_id, "c": captura_id},
    ).scalar_one_or_none()
    if ya is not None:
        return ya
    siguiente = conexion.execute(
        text(
            "SELECT coalesce(max(version), 0) + 1 FROM documento_versiones WHERE documento_id = :d"
        ),
        {"d": documento_id},
    ).scalar_one()
    sha = conexion.execute(
        text("SELECT sha256_raw FROM capturas WHERE id = :c"), {"c": captura_id}
    ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            " tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, :v, :tv, :tf, :h, :m, :ev) RETURNING id"
        ),
        {
            "d": documento_id,
            "c": captura_id,
            "v": siguiente,
            "tv": TipoVersionDocumento.NO_DETERMINADO.value,
            "tf": TipoFecha.DESCONOCIDA.value,
            "h": sha,
            "m": ModoExtraccion.JSON.value,
            "ev": "feriados@1",
        },
    ).scalar_one()


def _evidencia(
    conexion: Connection, doc_version_id: uuid.UUID, numero: int, fecha: dt.date, motivo: str
) -> uuid.UUID:
    fragmento = f"{fecha.isoformat()}: {motivo}"
    return conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, fragmento, selector, tipo, hash_fragmento) "
            "VALUES (:dv, :f, :s, :t, :h) RETURNING id"
        ),
        {
            "dv": doc_version_id,
            "f": fragmento,
            "s": f"itemListElement[{numero}]",
            "t": TipoEvidencia.CAMPO_JSON.value,
            "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
        },
    ).scalar_one()


def almacen_por_defecto() -> AlmacenObjetos:
    return AlmacenObjetos()


def derivar_jurisdiccional(
    conexion: Connection, *, jurisdiccion: str, anio: int
) -> uuid.UUID | None:
    """Un calendario local con los feriados nacionales, y nada más que eso.

    Los feriados nacionales rigen en todo el país, así que un calendario local
    que los repita es cierto en lo que dice. Lo que no tiene son las ferias
    administrativas que cada jurisdicción fija por su cuenta, y ésas alargan el
    plazo: contarlas de menos adelanta el vencimiento y hace perder el plazo.

    Por eso el nombre del calendario declara la limitación —viaja en el
    fundamento de cada cómputo— y la carga abre una incidencia con responsable.
    Un calendario incompleto que dice qué le falta es mejor que ninguno; uno que
    no lo dice es peor que ninguno.
    """
    nacional = (
        conexion.execute(
            text(
                "SELECT id, version, fecha_desde, fecha_hasta FROM calendarios "
                " WHERE jurisdiccion_id = :n AND version = :v LIMIT 1"
            ),
            {"n": JURISDICCION, "v": str(anio)},
        )
        .mappings()
        .first()
    )
    if nacional is None:
        return None

    nombre = (
        f"Feriados nacionales {anio} aplicables en {jurisdiccion} — "
        "sin ferias administrativas locales"
    )
    ya = conexion.execute(
        text("SELECT id FROM calendarios WHERE jurisdiccion_id = :j AND version = :v"),
        {"j": jurisdiccion, "v": str(anio)},
    ).scalar_one_or_none()
    if ya is not None:
        return ya

    derivado = conexion.execute(
        text(
            "INSERT INTO calendarios (jurisdiccion_id, nombre, version, fecha_desde, "
            " fecha_hasta, fuente_id) VALUES (:j, :n, :v, :d, :h, :f) RETURNING id"
        ),
        {
            "j": jurisdiccion,
            "n": nombre,
            "v": str(anio),
            "d": nacional["fecha_desde"],
            "h": nacional["fecha_hasta"],
            "f": SOURCE_ID,
        },
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO calendario_excepciones (calendario_id, evidencia_id, fecha, es_habil, "
            " motivo) SELECT :nuevo, e.evidencia_id, e.fecha, e.es_habil, e.motivo "
            "  FROM calendario_excepciones e WHERE e.calendario_id = :origen"
        ),
        {"nuevo": derivado, "origen": nacional["id"]},
    )
    descripcion = (
        f"El calendario de {jurisdiccion} para {anio} se derivó de los feriados nacionales: "
        "son ciertos, porque rigen en todo el país, y están incompletos, porque no incluyen "
        "las ferias administrativas que fija la propia jurisdicción. Un plazo hábil computado "
        "con él puede vencer más tarde de lo calculado. Hay que conseguir el calendario "
        "administrativo local y reemplazarlo."
    )
    if not conexion.execute(
        text("SELECT 1 FROM incidencias_revision WHERE descripcion = :d"), {"d": descripcion}
    ).first():
        conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, source_id, "
                " descripcion, responsable_rol) "
                "VALUES (:t, :s, 'ABIERTA', :src, :d, 'ingesta')"
            ),
            {
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "s": Severidad.HIGH.value,
                "src": SOURCE_ID,
                "d": descripcion,
            },
        )
    return derivado
