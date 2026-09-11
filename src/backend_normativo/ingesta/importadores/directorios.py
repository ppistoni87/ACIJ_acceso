"""HU-019 y HU-020: directorios de atención y canales, sin mezclar entidades.

Un directorio parece el dato más fácil del corpus y es donde más rápido se
afirma algo falso, porque nada avisa. Una dirección mal armada, un teléfono que
dice `N/A` y un punto en el mapa a mil kilómetros se ven exactamente igual que
los correctos.

Tres reglas que este importador existe para sostener:

* **`N/A` no es un teléfono.** Los datasets traen literales de "sin dato" en
  columnas de contacto. Cargarlos hace que alguien marque «N/A» o que el
  sistema conversacional lo lea en voz alta. Se convierten en ausencia y se
  cuentan.
* **Una coordenada sin CRS confirmado no es una coordenada.** El dataset de
  sedes comunales trae `POINT (28615.88 70947.08)`: una grilla local, no
  WGS84. Tomarla como latitud y longitud pondría todas las comunas de Buenos
  Aires en el Golfo de Guinea. Se conserva cruda, con su origen, y `lat`/`lng`
  quedan vacías hasta que alguien confirme la proyección.
* **El piso es parte de la dirección, no un campo aparte que se pueda mezclar.**
  La dirección cruda se conserva textual. Componer una legible a partir de dos
  fuentes que no coinciden produce una dirección que no existe en ninguna.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
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
from backend_normativo.ingesta.almacen import AlmacenObjetos
from backend_normativo.ingesta.conciliacion import Conciliacion, registrar
from backend_normativo.ingesta.versiones import (
    proxima_version,
    sha_del_contenido,
    version_ya_existente,
)

JURISDICCION = "AR-C"

# Literales que los datasets usan para decir "no hay dato". No son valores.
SIN_DATO = frozenset({"", "n/a", "na", "s/d", "sd", "-", "--", "sin datos", "no informa", "null"})

RE_PUNTO = re.compile(r"POINT\s*\(\s*(?P<x>-?\d+(?:\.\d+)?)\s+(?P<y>-?\d+(?:\.\d+)?)\s*\)", re.I)
RE_TELEFONO = re.compile(r"\d[\d\s\-().]{5,}")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Argentina continental, con margen. Sirve para descartar, no para confirmar:
# una coordenada dentro del rango puede seguir estando en otra proyección, así
# que el CRS se declara igual.
LAT_MIN, LAT_MAX = -56.0, -21.0
LNG_MIN, LNG_MAX = -74.0, -53.0


class FormaInesperada(Exception):
    """El dataset no trae las columnas que el contrato declara."""


@dataclass
class Dataset:
    """Contrato de un directorio: qué columnas se esperan y qué significa cada una."""

    source_id: str
    organismo: str
    tipo_punto: TipoPuntoAtencion
    columnas: dict[str, str]
    obligatorias: tuple[str, ...] = ("nombre", "direccion")


COMUNAS = Dataset(
    source_id="F20",
    organismo="Gobierno de la Ciudad Autónoma de Buenos Aires",
    tipo_punto=TipoPuntoAtencion.SEDE,
    columnas={
        "nombre": "fna",
        "clase": "gna",
        "direccion": "dir",
        "barrio": "bar",
        "telefono": "tel",
        "web": "web",
        "geometria": "geometry",
    },
)

EFECTORES = Dataset(
    source_id="F60",
    organismo="Ministerio de Desarrollo Humano y Hábitat (CABA)",
    tipo_punto=TipoPuntoAtencion.CENTRO_COMUNITARIO,
    columnas={
        "nombre": "programa",
        "detalle": "nombre",
        "direccion": "direccion",
        "barrio": "barrio",
        "telefono": "telefono",
        "email": "email",
        "web": "web",
        "horario": "horario_atencion",
        "dias": "dias",
    },
)

DATASETS = {d.source_id: d for d in (COMUNAS, EFECTORES)}


@dataclass
class ResultadoDirectorio:
    source_id: str = ""
    filas_leidas: int = 0
    puntos_creados: int = 0
    puntos_conocidos: int = 0
    canales_creados: int = 0
    literales_sin_dato: int = 0
    coordenadas_sin_crs: int = 0
    coordenadas_usables: int = 0
    avisos: list[str] = field(default_factory=list)


class ImportadorDirectorios:
    def __init__(self, conexion: Connection, almacen: AlmacenObjetos | None = None) -> None:
        self.conexion = conexion
        self.almacen = almacen or AlmacenObjetos()

    def importar_desde_captura(self, captura_id: uuid.UUID) -> ResultadoDirectorio:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT c.sha256_raw, c.capturado_en, u.source_id "
                    "  FROM capturas c JOIN fuente_urls u ON u.id = c.source_url_id "
                    " WHERE c.id = :c"
                ),
                {"c": captura_id},
            )
            .mappings()
            .one()
        )
        dataset = DATASETS.get(fila["source_id"])
        if dataset is None:
            raise FormaInesperada(
                f"No hay contrato declarado para {fila['source_id']}. Importar un directorio "
                "sin saber qué significa cada columna es cargar datos a ciegas."
            )
        resultado = self.importar(
            self.almacen.leer(fila["sha256_raw"]),
            dataset=dataset,
            captura_id=captura_id,
            capturado_en=fila["capturado_en"],
        )
        registrar(self.conexion, captura_id, self._conciliacion(resultado))
        return resultado

    @staticmethod
    def _conciliacion(resultado: ResultadoDirectorio) -> Conciliacion:
        """`literales_sin_dato` no es un rechazo: cuenta campos vacíos de filas
        que sí entraron como punto de atención."""
        return Conciliacion(
            importador="directorio",
            source_id=resultado.source_id,
            leidas=resultado.filas_leidas,
            nuevas=resultado.puntos_creados,
            repetidas=resultado.puntos_conocidos,
            observaciones={
                "literales_sin_dato": resultado.literales_sin_dato,
                "coordenadas_sin_crs": resultado.coordenadas_sin_crs,
            },
            avisos=resultado.avisos,
        )

    def importar(
        self,
        contenido: bytes,
        *,
        dataset: Dataset,
        captura_id: uuid.UUID,
        capturado_en: dt.datetime,
    ) -> ResultadoDirectorio:
        resultado = ResultadoDirectorio(source_id=dataset.source_id)
        lector = csv.DictReader(io.StringIO(contenido.decode("utf-8-sig", "replace")))
        columnas = set(lector.fieldnames or ())
        faltan = [
            c
            for clave in dataset.obligatorias
            if (c := dataset.columnas.get(clave)) and c not in columnas
        ]
        if faltan:
            raise FormaInesperada(
                f"{dataset.source_id} no trae las columnas {faltan}. Llegaron: {sorted(columnas)}."
            )

        doc_version_id = self._version_documental(
            dataset, captura_id, capturado_en, contenido.decode("utf-8-sig", "replace")
        )
        organismo_id = self._organismo(dataset.organismo)

        for numero, fila in enumerate(lector, start=1):
            resultado.filas_leidas += 1
            nombre = _valor(fila.get(dataset.columnas["nombre"]))
            if nombre is None:
                resultado.literales_sin_dato += 1
                continue
            detalle = _valor(fila.get(dataset.columnas.get("detalle", "")))
            etiqueta = f"{nombre} — {detalle}" if detalle else nombre

            evidencia_id = self._evidencia(doc_version_id, numero, fila)
            punto_id, nuevo = self._punto(organismo_id, etiqueta, dataset.tipo_punto)
            resultado.puntos_creados += int(nuevo)
            resultado.puntos_conocidos += int(not nuevo)

            self._version_de_punto(punto_id, fila, dataset, capturado_en, resultado)
            resultado.canales_creados += self._canales(
                punto_id, organismo_id, evidencia_id, fila, dataset, capturado_en, resultado
            )

        self._avisos(dataset, resultado)
        return resultado

    # --- Internos -----------------------------------------------------------

    def _avisos(self, dataset: Dataset, resultado: ResultadoDirectorio) -> None:
        if resultado.literales_sin_dato:
            resultado.avisos.append(
                f"{resultado.literales_sin_dato} campo(s) traían un literal de «sin dato» "
                "(N/A, S/D, guion). Se guardaron como ausencia: cargarlos haría que alguien "
                "marque «N/A» creyendo que es un teléfono."
            )
        if resultado.coordenadas_sin_crs:
            resultado.avisos.append(
                f"{resultado.coordenadas_sin_crs} coordenada(s) vienen en una grilla que no es "
                "WGS84 y el dataset no declara su CRS. Se conservan crudas y `lat`/`lng` quedan "
                "vacías: tomarlas como latitud y longitud pondría estas sedes a miles de "
                "kilómetros. No se responde por cercanía hasta que alguien confirme la "
                "proyección."
            )
            self.conexion.execute(
                text(
                    "INSERT INTO incidencias_revision (tipo, severidad, estado, source_id, "
                    " descripcion, responsable_rol) "
                    "VALUES (:t, :s, 'ABIERTA', :src, :d, 'curador de datos')"
                ),
                {
                    "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                    "s": Severidad.HIGH.value,
                    "src": dataset.source_id,
                    "d": (
                        f"{resultado.coordenadas_sin_crs} punto(s) de {dataset.source_id} tienen "
                        "geometría en una grilla local sin CRS declarado. Hace falta confirmar la "
                        "proyección con el organismo antes de usarlas para filtros territoriales."
                    ),
                },
            )

    def _organismo(self, nombre: str) -> uuid.UUID:
        return self.conexion.execute(
            text(
                "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) VALUES (:j, :n, :t) "
                "ON CONFLICT (jurisdiccion_id, nombre, tipo) DO UPDATE SET nombre = :n "
                "RETURNING id"
            ),
            {"j": JURISDICCION, "n": nombre, "t": TipoOrganismo.PRESTADOR.value},
        ).scalar_one()

    def _punto(
        self, organismo_id: uuid.UUID, nombre: str, tipo: TipoPuntoAtencion
    ) -> tuple[uuid.UUID, bool]:
        ya = self.conexion.execute(
            text(
                "SELECT id FROM puntos_atencion "
                " WHERE organismo_id = :o AND nombre = :n AND tipo = :t"
            ),
            {"o": organismo_id, "n": nombre, "t": tipo.value},
        ).scalar_one_or_none()
        if ya is not None:
            return ya, False
        creado = self.conexion.execute(
            text(
                "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo) "
                "VALUES (:o, :j, :n, :t) RETURNING id"
            ),
            {"o": organismo_id, "j": JURISDICCION, "n": nombre, "t": tipo.value},
        ).scalar_one()
        return creado, True

    def _version_de_punto(
        self,
        punto_id: uuid.UUID,
        fila: dict,
        dataset: Dataset,
        capturado_en: dt.datetime,
        resultado: ResultadoDirectorio,
    ) -> uuid.UUID:
        cruda = _valor(fila.get(dataset.columnas["direccion"]))
        geometria = _valor(fila.get(dataset.columnas.get("geometria", "")))
        lat, lng, crs, observacion = _coordenadas(geometria)
        if geometria and lat is None:
            resultado.coordenadas_sin_crs += 1
        elif lat is not None:
            resultado.coordenadas_usables += 1

        registro = self._nueva_version(EntidadVersionada.PUNTO_ATENCION, punto_id, capturado_en)
        self.conexion.execute(
            text(
                "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_cruda, "
                " localidad, lat, lng, coordenadas_origen, crs, es_presencial, observaciones) "
                "VALUES (:rv, :p, :cruda, :loc, CAST(:lat AS numeric), CAST(:lng AS numeric), "
                "        CAST(:origen AS jsonb), :crs, true, :obs)"
            ),
            {
                "rv": registro,
                "p": punto_id,
                # La dirección legible no se compone acá: se conserva la cruda
                # tal como la fuente la escribió, con el piso adentro si es que
                # viene adentro.
                "cruda": cruda,
                "loc": _valor(fila.get(dataset.columnas.get("barrio", ""))),
                "lat": lat,
                "lng": lng,
                # De dónde salieron las coordenadas y en qué formato. Sin esto,
                # una lat/lng vacía no se distingue de una que nunca vino.
                "origen": json.dumps(
                    {
                        "formato": "WKT",
                        "valor": geometria,
                        "columna": dataset.columnas.get("geometria"),
                        "crs_declarado": None,
                    },
                    ensure_ascii=False,
                )
                if geometria
                else None,
                "crs": crs,
                "obs": observacion,
            },
        )
        return registro

    def _canales(
        self,
        punto_id: uuid.UUID,
        organismo_id: uuid.UUID,
        evidencia_id: uuid.UUID,
        fila: dict,
        dataset: Dataset,
        capturado_en: dt.datetime,
        resultado: ResultadoDirectorio,
    ) -> int:
        horario = _valor(fila.get(dataset.columnas.get("horario", "")))
        dias = _valor(fila.get(dataset.columnas.get("dias", "")))
        # El horario es del canal presencial: no se copia al teléfono ni al mail.
        horario_sede = " ".join(p for p in (dias, horario) if p) or None

        creados = 0
        for clave, tipo, validador, con_horario in (
            ("telefono", TipoCanal.TELEFONO, RE_TELEFONO, False),
            ("email", TipoCanal.EMAIL, RE_EMAIL, False),
            ("web", TipoCanal.WEB, None, False),
            ("direccion", TipoCanal.PRESENCIAL, None, True),
        ):
            columna = dataset.columnas.get(clave)
            crudo = _valor(fila.get(columna)) if columna else None
            if crudo is None:
                if columna and (fila.get(columna) or "").strip():
                    resultado.literales_sin_dato += 1
                continue
            normalizado = None
            if validador is not None:
                coincidencia = validador.search(crudo)
                if coincidencia is None:
                    # El valor está pero no tiene la forma que dice tener. Se
                    # conserva crudo y sin normalizar: adivinar produciría un
                    # teléfono que nadie publicó.
                    resultado.literales_sin_dato += 1
                else:
                    normalizado = coincidencia.group(0).strip()

            canal_id = uuid.uuid4()
            registro = self._nueva_version(EntidadVersionada.CANAL, canal_id, capturado_en)
            self.conexion.execute(
                text(
                    "INSERT INTO canales (registro_version_id, canal_id, organismo_id, punto_id, "
                    " evidencia_id, tipo, valor_crudo, valor_normalizado, horario, publico) "
                    "VALUES (:rv, :c, :o, :p, :e, :t, :crudo, :norm, :hor, true)"
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
                    "hor": horario_sede if con_horario else None,
                },
            )
            creados += 1
        return creados

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

    def _version_documental(
        self,
        dataset: Dataset,
        captura_id: uuid.UUID,
        capturado_en: dt.datetime,
        contenido: str,
    ) -> uuid.UUID:
        external_id = f"directorio:{dataset.source_id}"
        documento_id = self.conexion.execute(
            text(
                "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
                "VALUES (:s, :t, :titulo, :e) "
                "ON CONFLICT (source_id, external_id) DO UPDATE SET titulo = EXCLUDED.titulo "
                "RETURNING id"
            ),
            {
                "s": dataset.source_id,
                "t": TipoDocumento.DIRECTORIO.value,
                "titulo": f"Directorio {dataset.source_id}",
                "e": external_id,
            },
        ).scalar_one()
        # La huella sale del CSV ya decodificado y no de los bytes: la marca de
        # orden de bytes o un cambio de codificación no son un directorio nuevo.
        sha = sha_del_contenido([dataset.source_id, contenido])
        ya = version_ya_existente(self.conexion, documento_id, captura_id, sha)
        if ya is not None:
            return ya
        siguiente = proxima_version(self.conexion, documento_id)
        return self.conexion.execute(
            text(
                # `fecha_documento` queda vacía a propósito: la fecha de captura
                # dice cuándo se miró el dataset, no de cuándo es. El esquema lo
                # impide igual —una fecha con `tipo_fecha` desconocida es una
                # fecha que nadie puede interpretar—.
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
                "ev": "directorios@1",
            },
        ).scalar_one()

    def _evidencia(self, doc_version_id: uuid.UUID, numero: int, fila: dict) -> uuid.UUID:
        fragmento = " | ".join(
            f"{k}={(v or '').strip()}" for k, v in fila.items() if (v or "").strip()
        )
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


def _valor(bruto: str | None) -> str | None:
    """Un literal de «sin dato» es ausencia, no un valor."""
    limpio = " ".join((bruto or "").split())
    return None if limpio.lower() in SIN_DATO else limpio


def _coordenadas(
    geometria: str | None,
) -> tuple[float | None, float | None, str | None, str | None]:
    """Latitud y longitud solo si el par es plausible como WGS84.

    El dataset de sedes comunales trae `POINT (28615.88 70947.08)`. Interpretado
    como longitud y latitud eso está fuera del planeta; interpretado con los ejes
    invertidos, en el Golfo de Guinea. Es una grilla local, y el CSV no dice
    cuál.
    """
    if not geometria:
        return None, None, None, None
    punto = RE_PUNTO.search(geometria)
    if punto is None:
        return None, None, None, "La geometría no tiene la forma POINT (x y); se conserva cruda."
    x, y = float(punto.group("x")), float(punto.group("y"))
    if LNG_MIN <= x <= LNG_MAX and LAT_MIN <= y <= LAT_MAX:
        return y, x, "EPSG:4326", None
    return (
        None,
        None,
        None,
        (
            f"Geometría en grilla local sin CRS declarado ({x}, {y}). No se usa como "
            "latitud/longitud ni se reproyecta: reproyectar sin saber el origen es inventar "
            "una ubicación."
        ),
    )
