"""HU-021: el padrón RENABAP como snapshot versionado.

El padrón es una foto. Lo que importa del modelo no es la lista de barrios sino
la fecha a la que corresponde: preguntar si un barrio figura solo tiene sentido
contra una versión concreta del padrón.

Por eso cada importación crea una versión nueva en vez de actualizar filas, y
cada barrio conserva su identidad lógica a través de las versiones. Un barrio
que estaba y ya no está no se borra: la versión vieja sigue diciendo que ese
día estaba.

La regla que este importador existe para sostener: **la ausencia de un barrio en
un padrón no es una exclusión jurídica.** Es un dato de ese corte, con esa
fecha y con una vía de consulta. Responder "tu barrio no tiene protección"
porque no aparece en una planilla sería una conclusión que ni el padrón ni el
backend pueden sacar.

El recurso es la planilla publicada que la propia página oficial renderiza: el
listado no viaja en el HTML, así que sin ella la fuente no tiene padrón que
importar. Se descubrió por el `idSpread` que declara el script de la página y
quedó registrada como candidata antes de promoverse.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EntidadVersionada,
    EstadoRevision,
    ModoExtraccion,
    Severidad,
    TipoDocumento,
    TipoEvidencia,
    TipoFecha,
    TipoIncidencia,
    TipoVersionDocumento,
    ValidTipo,
)
from backend_normativo.ingesta.almacen import AlmacenObjetos
from backend_normativo.ingesta.conciliacion import Conciliacion, registrar

SOURCE_ID = "F39"

# Las columnas llegan con el rótulo duplicado ("ID Renabap ID Renabap") porque
# la planilla usa la primera fila como encabezado y como filtro. Se normaliza
# por prefijo en vez de exigir el texto exacto, que cambia cuando alguien edita
# un rótulo.
CAMPOS = {
    "id_renabap": ("id renabap",),
    "nombre": ("barrio",),
    "provincia": ("filtro-provincia", "provincia"),
    "departamento": ("departamento",),
    "localidad": ("localidad",),
    "familias": ("familias",),
    "viviendas": ("viviendas",),
}

RE_ETIQUETA = re.compile(r"<[^>]+>")

# La página no trae el listado: lo renderiza desde una planilla publicada cuyo
# identificador declara su propio script. Este es el fragmento que lo declara.
RE_ID_PLANILLA = re.compile(r"idSpread\"?\s*:\s*\"([A-Za-z0-9_-]{20,})\"")

# La vista CSV de esa misma planilla. Es la que publica el organismo, servida
# por el mismo identificador que su script declara: no se adivina un formato ni
# se busca un espejo.
URL_PLANILLA = "https://docs.google.com/spreadsheets/d/{identificador}/gviz/tq?tqx=out:csv&sheet=1"


@dataclass
class Descubrimiento:
    """El resultado de buscar la planilla en la página de la fuente."""

    url: str | None = None
    identificador: str | None = None
    registrada: bool = False
    promovida: bool = False
    avisos: list[str] = field(default_factory=list)


def descubrir_planilla(
    conexion: Connection, captura_id: uuid.UUID, almacen: AlmacenObjetos | None = None
) -> Descubrimiento:
    """Registra la planilla del padrón como URL de F39, leyéndola de la página.

    Hasta ahora esta URL entró a mano en una sesión de trabajo, y eso hacía que
    repoblar la base desde cero dejara la fuente sin padrón sin que nadie se
    enterara: el importador fallaba con «la planilla no trae columna para
    id_renabap» porque lo que le llegaba era el HTML de la página.

    La promoción está justificada y acotada: el recurso es el dato de la propia
    fuente, declarado por el script de la propia fuente. No es un enlace a un
    tercero ni una URL adivinada, y por eso puede promoverse sola. Cualquier
    otra candidata sigue necesitando que alguien decida.
    """
    resultado = Descubrimiento()
    almacen = almacen or AlmacenObjetos()
    fila = (
        conexion.execute(
            text("SELECT sha256_raw, mime FROM capturas WHERE id = :c"), {"c": captura_id}
        )
        .mappings()
        .one()
    )
    contenido = almacen.leer(fila["sha256_raw"]).decode("utf-8", "replace")
    coincidencia = RE_ID_PLANILLA.search(contenido)
    if coincidencia is None:
        resultado.avisos.append(
            "La página de F39 no declara el identificador de la planilla. Puede haber "
            "cambiado de forma de publicar el listado: sin ese identificador no se "
            "inventa una URL, y el padrón queda sin importar hasta que alguien mire la "
            "página."
        )
        return resultado

    resultado.identificador = coincidencia.group(1)
    resultado.url = URL_PLANILLA.format(identificador=resultado.identificador)
    relacion = (
        "Planilla publicada que la propia página de F39 renderiza: el script de la página "
        f"declara idSpread={resultado.identificador}. El listado no está en el HTML "
        "capturado, así que sin este recurso la fuente no tiene padrón que importar."
    )
    creada = conexion.execute(
        text(
            "INSERT INTO fuentes_candidatas "
            "(source_id_origen, url, relacion, tipo_esperado, estado, prioridad) "
            "VALUES (:s, :u, :rel, 'DATASET', 'PROMOVIDA', 'P1') "
            "ON CONFLICT (source_id_origen, url) DO NOTHING RETURNING id"
        ),
        {"s": SOURCE_ID, "u": resultado.url, "rel": relacion},
    ).scalar_one_or_none()
    resultado.registrada = creada is not None

    promovida = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'DESCARGA_ARCHIVO') "
            "ON CONFLICT (source_id, url) DO NOTHING RETURNING id"
        ),
        {"s": SOURCE_ID, "u": resultado.url},
    ).scalar_one_or_none()
    resultado.promovida = promovida is not None
    return resultado


class FormaInesperada(Exception):
    """La planilla no trae las columnas mínimas para identificar un barrio."""


@dataclass
class ResultadoPadron:
    padron_version: str = ""
    fecha_corte: dt.date | None = None
    filas_leidas: int = 0
    barrios_nuevos: int = 0
    barrios_conocidos: int = 0
    sin_id: int = 0
    sin_familias: int = 0
    avisos: list[str] = field(default_factory=list)


class ImportadorRenabap:
    def __init__(self, conexion: Connection, almacen: AlmacenObjetos | None = None) -> None:
        self.conexion = conexion
        self.almacen = almacen or AlmacenObjetos()

    def importar_desde_captura(self, captura_id: uuid.UUID) -> ResultadoPadron:
        fila = (
            self.conexion.execute(
                text("SELECT sha256_raw, capturado_en FROM capturas WHERE id = :c"),
                {"c": captura_id},
            )
            .mappings()
            .one()
        )
        resultado = self.importar(
            self.almacen.leer(fila["sha256_raw"]),
            captura_id=captura_id,
            capturado_en=fila["capturado_en"],
        )
        registrar(self.conexion, captura_id, self._conciliacion(resultado))
        return resultado

    @staticmethod
    def _conciliacion(resultado: ResultadoPadron) -> Conciliacion:
        """Una fila sin identificador no se puede seguir entre padrones: no entra.

        `sin_familias` no es un rechazo: el barrio se carga igual, sin ese dato.
        """
        return Conciliacion(
            importador="padron_renabap",
            source_id="F39",
            leidas=resultado.filas_leidas,
            nuevas=resultado.barrios_nuevos,
            repetidas=resultado.barrios_conocidos,
            motivos={"sin_id": resultado.sin_id},
            observaciones={"sin_familias": resultado.sin_familias},
            avisos=resultado.avisos,
        )

    def importar(
        self,
        contenido: bytes,
        *,
        captura_id: uuid.UUID,
        capturado_en: dt.datetime,
        padron_version: str | None = None,
    ) -> ResultadoPadron:
        version = padron_version or f"renabap-{capturado_en.date().isoformat()}"
        resultado = ResultadoPadron(padron_version=version)

        filas = list(csv.DictReader(io.StringIO(contenido.decode("utf-8", "replace"))))
        if not filas:
            raise FormaInesperada("La planilla llegó vacía; no se importa un padrón sin filas.")
        indice = _mapear_columnas(filas[0].keys())

        doc_version_id = self._version_documental(captura_id, version)
        conocidos = {
            f[0]: f[1]
            for f in self.conexion.execute(
                text("SELECT id_renabap, barrio_id FROM barrios_renabap")
            )
        }

        # El padrón no declara fecha de corte propia: la planilla no trae esa
        # columna. Se conserva la fecha de captura como lo que es —cuándo se
        # miró— y se dice que no es la fecha de corte oficial.
        resultado.avisos.append(
            "La planilla no declara fecha de corte. Se registra la fecha de captura como "
            f"referencia ({capturado_en.date().isoformat()}) y `fecha_corte` queda vacía: "
            "inventar un corte haría creer que el padrón se cerró ese día."
        )

        for numero, fila in enumerate(filas, start=1):
            resultado.filas_leidas += 1
            identificador = _texto(fila.get(indice["id_renabap"], ""))
            if not identificador:
                resultado.sin_id += 1
                continue
            if identificador in conocidos and self._ya_esta(identificador, version):
                resultado.barrios_conocidos += 1
                continue

            barrio_id = conocidos.get(identificador) or uuid.uuid4()
            # La evidencia de cada barrio es su fila: sin eso, «figura en el
            # padrón» sería una afirmación que remite al archivo entero.
            evidencia_id = self._evidencia_de_fila(doc_version_id, numero, fila)
            familias = _entero(fila.get(indice.get("familias", ""), ""))
            if familias is None:
                resultado.sin_familias += 1

            registro = self._nueva_version(barrio_id, capturado_en)
            self.conexion.execute(
                text(
                    "INSERT INTO barrios_renabap (registro_version_id, barrio_id, evidencia_id, "
                    " id_renabap, nombre, provincia, departamento, localidad, familias, "
                    " padron_version) "
                    "VALUES (:rv, :b, :e, :id, :n, :p, :d, :l, :f, :v)"
                ),
                {
                    "rv": registro,
                    "b": barrio_id,
                    "e": evidencia_id,
                    "id": identificador,
                    "n": _texto(fila.get(indice["nombre"], "")) or f"Barrio {identificador}",
                    "p": _texto(fila.get(indice.get("provincia", ""), "")) or None,
                    "d": _texto(fila.get(indice.get("departamento", ""), "")) or None,
                    "l": _texto(fila.get(indice.get("localidad", ""), "")) or None,
                    "f": familias,
                    "v": version,
                },
            )
            conocidos[identificador] = barrio_id
            resultado.barrios_nuevos += 1

        self._registrar_incidencia_de_lectura(resultado)
        return resultado

    def _nueva_version(self, barrio_id: uuid.UUID, capturado_en: dt.datetime) -> uuid.UUID:
        """Versión nueva del mismo barrio, cerrando lo que se sabía antes.

        El barrio conserva su identidad lógica entre padrones: lo que cambia es
        qué se sabe de él y desde cuándo. Cerrar el intervalo de conocimiento
        anterior es lo que permite reconstruir después qué decía el padrón de
        marzo cuando ya rige el de junio.
        """
        parametros = {
            "tipo": EntidadVersionada.BARRIO_RENABAP.value,
            "eid": barrio_id,
        }
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

    def _ya_esta(self, identificador: str, version: str) -> bool:
        return (
            self.conexion.execute(
                text(
                    "SELECT 1 FROM barrios_renabap  WHERE id_renabap = :i AND padron_version = :v"
                ),
                {"i": identificador, "v": version},
            ).first()
            is not None
        )

    def _version_documental(self, captura_id: uuid.UUID, version: str) -> uuid.UUID:
        """El padrón es un documento con una versión por captura.

        Colgarlo de la misma cadena que el resto del corpus es lo que hace que
        la evidencia de un barrio se pueda localizar igual que la de un
        artículo: captura, versión y fragmento.
        """
        documento_id = self.conexion.execute(
            text(
                "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
                "VALUES (:s, :t, :titulo, :e) "
                "ON CONFLICT (source_id, external_id) DO UPDATE SET titulo = EXCLUDED.titulo "
                "RETURNING id"
            ),
            {
                "s": SOURCE_ID,
                "t": TipoDocumento.PADRON.value,
                "titulo": f"Listado RENABAP ({version})",
                "e": f"renabap:{version}",
            },
        ).scalar_one()
        sha = self.conexion.execute(
            text("SELECT sha256_raw FROM capturas WHERE id = :c"), {"c": captura_id}
        ).scalar_one()
        # La misma planilla, capturada de nuevo, es la misma versión del
        # documento aunque la captura sea otra fila: volver a pedirla no la
        # cambia. Buscar por captura y no por contenido hacía que reejecutar la
        # población intentara insertar una versión con el mismo hash y chocara
        # contra la restricción que justamente impide duplicarla, así que el
        # procedimiento que se documenta como idempotente no lo era.
        ya = self.conexion.execute(
            text(
                "SELECT id FROM documento_versiones "
                " WHERE documento_id = :d AND (captura_id = :c "
                "    OR (hash_texto = :h AND tipo_version = :tv)) "
                " ORDER BY version LIMIT 1"
            ),
            {
                "d": documento_id,
                "c": captura_id,
                "h": sha,
                "tv": TipoVersionDocumento.NO_DETERMINADO.value,
            },
        ).scalar_one_or_none()
        if ya is not None:
            return ya
        siguiente = self.conexion.execute(
            text(
                "SELECT coalesce(max(version), 0) + 1 FROM documento_versiones "
                " WHERE documento_id = :d"
            ),
            {"d": documento_id},
        ).scalar_one()
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
                "m": ModoExtraccion.CSV.value,
                "ev": "renabap@1",
            },
        ).scalar_one()

    def _evidencia_de_fila(self, doc_version_id: uuid.UUID, numero: int, fila: dict) -> uuid.UUID:
        fragmento = " | ".join(f"{k}={_texto(v)}" for k, v in fila.items() if _texto(v))
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, fragmento, selector, tipo, "
                " hash_fragmento) VALUES (:dv, :f, :s, :t, :h) RETURNING id"
            ),
            {
                "dv": doc_version_id,
                "f": fragmento,
                "s": f"fila:{numero}",
                "t": TipoEvidencia.CAMPO_CSV.value,
                "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
            },
        ).scalar_one()

    def _registrar_incidencia_de_lectura(self, resultado: ResultadoPadron) -> None:
        if not resultado.sin_id:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, source_id, "
                " descripcion, responsable_rol) "
                "VALUES (:t, :s, 'ABIERTA', :src, :d, 'curador de datos')"
            ),
            {
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "s": Severidad.MEDIUM.value,
                "src": SOURCE_ID,
                "d": (
                    f"{resultado.sin_id} fila(s) del padrón {resultado.padron_version} no traen "
                    "identificador RENABAP. Sin identificador el barrio no se puede seguir entre "
                    "versiones del padrón, así que quedan afuera y se registran acá."
                ),
            },
        )


def _mapear_columnas(claves) -> dict[str, str]:
    indice: dict[str, str] = {}
    for campo, prefijos in CAMPOS.items():
        for clave in claves:
            normalizada = (clave or "").strip().lower()
            if any(normalizada.startswith(p) for p in prefijos):
                indice[campo] = clave
                break
    faltan = [c for c in ("id_renabap", "nombre") if c not in indice]
    if faltan:
        raise FormaInesperada(
            f"La planilla no trae columna para {faltan}. Sin identificador y nombre no hay "
            f"barrio que registrar. Columnas recibidas: {list(claves)}"
        )
    return indice


def _texto(valor: str | None) -> str:
    limpio = RE_ETIQUETA.sub("", valor or "").strip()
    return " ".join(limpio.split())


def _entero(valor: str | None) -> int | None:
    limpio = _texto(valor).replace(".", "").replace(",", "")
    return int(limpio) if limpio.isdigit() else None
