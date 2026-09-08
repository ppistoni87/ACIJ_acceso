"""HU-005: importar el catálogo nacional de InfoLEG como metadatos.

La especificación lo habilita expresamente y también marca sus límites: importar
metadatos globales sí, rastrear todos los textos del país no. Las filas sin URL
de texto se conservan igual, marcadas como metadata-only: saber que una norma
existe y que no tenemos su texto es información, y descartarlas haría creer que
no existen.

Dos cuidados que el manual señala para esta fuente:

* Las columnas `modificada_por` y `modifica_a` son **contadores**, no aristas.
  Que una norma diga "3" no permite construir tres relaciones: no dice con
  cuáles. Se conservan como observación y no se convierten en grafo.
* `S/N` en el número no es un número. Una norma sin número no tiene clave
  canónica y se identifica por su identificador oficial.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import pathlib
import uuid
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoIncidencia,
    Severidad,
    TipoIncidencia,
    TipoNorma,
    TipoOrganismo,
)
from backend_normativo.ingesta.almacen import AlmacenObjetos

# Contrato de forma del dataset. Si cambia, la importación se detiene: cargar a
# ciegas un CSV con otras columnas produce datos silenciosamente equivocados.
COLUMNAS_ESPERADAS: tuple[str, ...] = (
    "id_norma",
    "tipo_norma",
    "numero_norma",
    "clase_norma",
    "organismo_origen",
    "fecha_sancion",
    "numero_boletin",
    "fecha_boletin",
    "pagina_boletin",
    "titulo_resumido",
    "titulo_sumario",
    "texto_resumido",
    "observaciones",
    "texto_original",
    "texto_actualizado",
    "modificada_por",
    "modifica_a",
)

NAMESPACE = "infoleg"
SOURCE_ID = "F01"
JURISDICCION = "AR"
TAMANO_LOTE = 5000

# El catálogo completo pesa ~256 MB expandidos. El presupuesto deja margen de
# crecimiento sin habilitar una bomba de descompresión.
PRESUPUESTO_EXPANSION = 2 * 1024**3

TIPOS: dict[str, TipoNorma] = {
    "ley": TipoNorma.LEY,
    "decreto": TipoNorma.DECRETO,
    "decreto/ley": TipoNorma.DECRETO_LEY,
    "decreto ley": TipoNorma.DECRETO_LEY,
    "resolución": TipoNorma.RESOLUCION,
    "resolucion": TipoNorma.RESOLUCION,
    "disposición": TipoNorma.DISPOSICION,
    "disposicion": TipoNorma.DISPOSICION,
    "acordada": TipoNorma.ACORDADA,
    "acta": TipoNorma.OTRO,
    "decisión administrativa": TipoNorma.OTRO,
    "decision administrativa": TipoNorma.OTRO,
}

# La numeración de leyes y decretos es jurisdiccional: "Ley 24.714" identifica
# una norma. La de resoluciones y disposiciones es por organismo: en el catálogo
# hay 123 normas cuya clave es ("Resolución", "1", 2023), emitidas por 123
# organismos distintos. Esa clave no identifica, así que esas normas se cargan
# con `identidad_incierta` y se las referencia por su identificador oficial.
CLAVE_JURISDICCIONAL: frozenset[TipoNorma] = frozenset(
    {TipoNorma.LEY, TipoNorma.DECRETO, TipoNorma.DECRETO_LEY}
)

# Marcadores de "sin número" que usa la fuente.
SIN_NUMERO = frozenset({"", "s/n", "s/nº", "s/n°", "sn"})


class FormaInesperada(Exception):
    """El dataset no tiene las columnas que declara el contrato."""


class ArchivoInseguro(Exception):
    """El contenedor no se procesa: rutas fuera del árbol o expansión desmedida."""


@dataclass
class ResultadoImportacion:
    filas_leidas: int = 0
    normas_creadas: int = 0
    normas_existentes: int = 0
    organismos_creados: int = 0
    sin_numero: int = 0
    sin_clave_canonica: int = 0
    homonimas: int = 0
    sin_texto: int = 0
    con_texto_actualizado: int = 0
    contadores_conservados: int = 0
    coemitidas: int = 0
    avisos: list[str] = field(default_factory=list)


def _fecha(valor: str) -> dt.date | None:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return dt.date.fromisoformat(valor)
    except ValueError:
        return None


def _entero(valor: str) -> int | None:
    valor = (valor or "").strip()
    return int(valor) if valor.isdigit() else None


def _numero(valor: str) -> str | None:
    """`S/N` no es un número: es la ausencia de número."""
    limpio = (valor or "").strip()
    return None if limpio.lower() in SIN_NUMERO else limpio


def _tipo(valor: str) -> TipoNorma:
    return TIPOS.get((valor or "").strip().lower(), TipoNorma.OTRO)


def abrir_csv(contenido: bytes) -> io.TextIOWrapper:
    """Abre en streaming el único miembro CSV del ZIP.

    El ZIP nunca se extrae al filesystem: se lee el miembro como flujo. Aun así
    se validan dos cosas antes de abrirlo, porque el archivo viene de la red y
    su tamaño declarado no es una promesa:

    * ningún nombre de miembro absoluto ni con `..` (no hay extracción que
      pueda desviar, pero un nombre así es señal de que el archivo no es el que
      se espera y se prefiere frenar);
    * la expansión declarada no supera el presupuesto, y la lectura tampoco lo
      supera de hecho —el tamaño declarado en el índice de un ZIP puede mentir.
    """
    archivo = zipfile.ZipFile(io.BytesIO(contenido))
    for miembro in archivo.infolist():
        nombre = miembro.filename
        if nombre.startswith("/") or ".." in pathlib.PurePosixPath(nombre).parts:
            raise ArchivoInseguro(f"El ZIP trae una ruta fuera del árbol: {nombre!r}.")
    miembros = [n for n in archivo.namelist() if n.lower().endswith(".csv")]
    if len(miembros) != 1:
        raise FormaInesperada(
            f"El ZIP trae {len(miembros)} archivos CSV y se esperaba exactamente uno."
        )
    declarado = sum(m.file_size for m in archivo.infolist())
    if declarado > PRESUPUESTO_EXPANSION:
        raise ArchivoInseguro(
            f"El ZIP declara {declarado} bytes expandidos y el presupuesto es "
            f"{PRESUPUESTO_EXPANSION}. No se procesa."
        )
    return io.TextIOWrapper(
        _FlujoAcotado(archivo.open(miembros[0]), PRESUPUESTO_EXPANSION),
        encoding="utf-8",
        errors="replace",
    )


class _FlujoAcotado(io.RawIOBase):
    """Corta la lectura si el miembro se expande por encima del presupuesto."""

    def __init__(self, flujo: io.BufferedIOBase, presupuesto: int) -> None:
        self._flujo = flujo
        self._presupuesto = presupuesto
        self._leidos = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:  # type: ignore[override]
        datos = self._flujo.read(len(buffer))
        self._leidos += len(datos)
        if self._leidos > self._presupuesto:
            raise ArchivoInseguro(
                f"El miembro del ZIP superó el presupuesto de {self._presupuesto} bytes "
                "durante la lectura: el tamaño declarado en el índice no era cierto."
            )
        buffer[: len(datos)] = datos
        return len(datos)

    def close(self) -> None:
        self._flujo.close()
        super().close()


class ImportadorInfoleg:
    def __init__(self, conexion: Connection, almacen: AlmacenObjetos | None = None) -> None:
        self.conexion = conexion
        self.almacen = almacen or AlmacenObjetos()
        self._organismos: dict[str, uuid.UUID] = {}
        self._existentes: set[str] = set()
        self._claves: set[tuple[str, str, int]] = set()
        self._homonimas: set[tuple[str, str, int]] = set()
        self._importados: set[str] = set()

    def importar_desde_captura(
        self, captura_id: uuid.UUID, *, limite: int | None = None
    ) -> ResultadoImportacion:
        sha = self.conexion.execute(
            text("SELECT sha256_raw FROM capturas WHERE id = :c"), {"c": captura_id}
        ).scalar_one()
        return self.importar(self.almacen.leer(sha), limite=limite)

    def importar(self, contenido: bytes, *, limite: int | None = None) -> ResultadoImportacion:
        resultado = ResultadoImportacion()
        homonimas = self._claves_repetidas(contenido, limite=limite)
        self._precargar(homonimas)

        with abrir_csv(contenido) as archivo:
            lector = self._lector(archivo)
            lote: list[dict] = []
            for fila in lector:
                resultado.filas_leidas += 1
                lote.append(self._preparar(fila, resultado))
                if len(lote) >= TAMANO_LOTE:
                    self._insertar(lote, resultado)
                    lote.clear()
                if limite and resultado.filas_leidas >= limite:
                    break
            if lote:
                self._insertar(lote, resultado)

        resultado.avisos.append(
            "Las columnas `modificada_por` y `modifica_a` son contadores, no aristas: "
            "dicen cuántas normas intervienen, no cuáles. Se conservan como observación y "
            "no se convierten en relaciones."
        )
        resultado.avisos.append(
            f"{resultado.sin_texto} norma(s) quedaron como metadata-only: el dataset no "
            "trae una URL de texto. No se descartan; que una norma exista sin texto "
            "accesible es información."
        )
        resultado.avisos.append(
            f"{resultado.sin_clave_canonica} norma(s) se cargaron con identidad incierta "
            "porque su tipo se numera por organismo y la clave (tipo, número, año) no las "
            f"distingue; otras {resultado.homonimas} porque comparten clave canónica con "
            "una homónima del propio catálogo. Ninguna resuelve citas por número."
        )
        return resultado

    # --- Internos -----------------------------------------------------------

    def _lector(self, archivo: io.TextIOWrapper) -> csv.DictReader:
        """Valida el contrato de forma antes de leer una sola fila."""
        lector = csv.DictReader(archivo)
        if tuple(lector.fieldnames or ()) != COLUMNAS_ESPERADAS:
            raise FormaInesperada(
                "El dataset cambió de forma. Se esperaban las columnas "
                f"{COLUMNAS_ESPERADAS} y llegaron {tuple(lector.fieldnames or ())}. "
                "No se importa a ciegas."
            )
        return lector

    def _claves_repetidas(
        self, contenido: bytes, *, limite: int | None
    ) -> set[tuple[str, str, int]]:
        """Primera pasada: qué claves canónicas están repetidas dentro del propio
        catálogo.

        Hace falta recorrer el archivo dos veces. La alternativa —quedarse con la
        primera fila de cada clave y marcar incierta la segunda— haría que el
        Decreto 1/2001 que aparece primero se quede con la clave canónica por
        orden de archivo, y que una cita a "Decreto 1/2001" resolviera con
        confianza a una de las cuatro normas que llevan ese número. Ninguna de
        las cuatro tiene mejor derecho que las otras: las cuatro quedan
        inciertas.
        """
        conteo: Counter[tuple[str, str, int]] = Counter()
        leidas = 0
        with abrir_csv(contenido) as archivo:
            for fila in self._lector(archivo):
                leidas += 1
                clave = _clave_canonica(fila)
                if clave is not None:
                    conteo[clave] += 1
                if limite and leidas >= limite:
                    break
        return {clave for clave, veces in conteo.items() if veces > 1}

    def _precargar(self, homonimas: set[tuple[str, str, int]]) -> None:
        self._homonimas = homonimas
        self._existentes = {
            fila[0]
            for fila in self.conexion.execute(
                text("SELECT valor FROM norma_identificadores WHERE namespace = :ns"),
                {"ns": NAMESPACE},
            )
        }
        # Claves canónicas ya ocupadas en la base: una norma cargada por la
        # curación fina no se duplica desde el catálogo masivo.
        self._claves = {
            (fila[0], fila[1], fila[2])
            for fila in self.conexion.execute(
                text(
                    "SELECT tipo, numero, anio FROM normas "
                    " WHERE jurisdiccion_id = :j AND identidad_incierta = false "
                    "   AND numero IS NOT NULL AND anio IS NOT NULL"
                ),
                {"j": JURISDICCION},
            )
        }

    def _organismo(self, nombre: str) -> uuid.UUID | None:
        nombre = (nombre or "").strip()
        if not nombre:
            return None
        if nombre in self._organismos:
            return self._organismos[nombre]
        encontrado = self.conexion.execute(
            text(
                "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
                "VALUES (:j, :n, :t) "
                "ON CONFLICT (jurisdiccion_id, nombre, tipo) DO UPDATE SET nombre = :n "
                "RETURNING id"
            ),
            {"j": JURISDICCION, "n": nombre, "t": TipoOrganismo.EMISOR.value},
        ).scalar_one()
        self._organismos[nombre] = encontrado
        return encontrado

    def _preparar(self, fila: dict, resultado: ResultadoImportacion) -> dict:
        tipo = _tipo(fila["tipo_norma"])
        numero = _numero(fila["numero_norma"])
        if numero is None:
            resultado.sin_numero += 1
        sancion = _fecha(fila["fecha_sancion"])
        publicacion = _fecha(fila["fecha_boletin"])
        anio = sancion.year if sancion else (publicacion.year if publicacion else None)

        texto_original = (fila["texto_original"] or "").strip()
        texto_actualizado = (fila["texto_actualizado"] or "").strip()
        if not texto_original and not texto_actualizado:
            resultado.sin_texto += 1
        if texto_actualizado:
            resultado.con_texto_actualizado += 1
        if _entero(fila["modificada_por"]) or _entero(fila["modifica_a"]):
            resultado.contadores_conservados += 1

        incierta = False
        if numero is not None and anio is not None:
            if tipo not in CLAVE_JURISDICCIONAL:
                incierta = True
                resultado.sin_clave_canonica += 1
            elif (tipo.value, numero, anio) in self._homonimas:
                incierta = True
                resultado.homonimas += 1

        titulo = (
            (fila["titulo_resumido"] or "").strip()
            or (fila["titulo_sumario"] or "").strip()
            or f"Norma InfoLEG {fila['id_norma']}"
        )
        materias = [m for m in [(fila["titulo_sumario"] or "").strip()] if m]

        return {
            "id": str(uuid.uuid4()),
            "infoleg_id": (fila["id_norma"] or "").strip(),
            "tipo": tipo.value,
            "numero": numero,
            "anio": anio,
            "titulo": titulo[:2000],
            "materias": materias,
            "sancion": sancion,
            "publicacion": publicacion,
            "emisor_id": self._organismo(fila["organismo_origen"]),
            "organismo_nombre": (fila["organismo_origen"] or "").strip(),
            "url_oficial": texto_actualizado or texto_original or None,
            "identidad_incierta": incierta,
        }

    def _insertar(self, lote: list[dict], resultado: ResultadoImportacion) -> None:
        nuevos: list[dict] = []
        coemisiones: dict[str, list[str]] = {}
        for fila in lote:
            identificador = fila["infoleg_id"]
            if not identificador:
                resultado.normas_existentes += 1
                continue
            if identificador in self._importados:
                # El catálogo desnormaliza las normas conjuntas: una fila por
                # organismo firmante, con el mismo id oficial. Es una norma, no
                # dos. El id oficial manda; los demás firmantes se registran como
                # incidencia, porque el modelo admite un solo emisor y perderlos
                # en silencio sería inventar una autoría única que la fuente no
                # afirma.
                coemisiones.setdefault(identificador, []).append(fila["organismo_nombre"])
                resultado.coemitidas += 1
                continue
            if identificador in self._existentes:
                resultado.normas_existentes += 1
                continue
            self._importados.add(identificador)
            nuevos.append(fila)

        if nuevos:
            self._resolver_homonimas(nuevos, resultado)
            self._insertar_normas(nuevos)
            resultado.normas_creadas += len(nuevos)
            self._existentes.update(f["infoleg_id"] for f in nuevos)
        self._registrar_coemisiones(coemisiones)

    def _resolver_homonimas(self, nuevos: list[dict], resultado: ResultadoImportacion) -> None:
        for fila in nuevos:
            if fila["identidad_incierta"] or fila["numero"] is None or fila["anio"] is None:
                continue
            clave = (fila["tipo"], fila["numero"], fila["anio"])
            if clave in self._claves:
                # Colisión con una norma ya cargada por la curación fina: esa
                # tiene texto y evidencia, así que conserva la clave canónica.
                fila["identidad_incierta"] = True
                resultado.homonimas += 1
            else:
                self._claves.add(clave)

    def _insertar_normas(self, nuevos: list[dict]) -> None:
        # El id se genera acá y no en la base: correlacionar el `RETURNING` del
        # INSERT con las filas de entrada por `row_number()` supone un orden de
        # salida que PostgreSQL no garantiza. Con el id explícito no hay nada que
        # correlacionar.
        self.conexion.execute(
            text(
                "WITH entrada AS ("
                "  SELECT * FROM json_to_recordset(CAST(:filas AS json)) AS x("
                "    id uuid, infoleg_id text, tipo text, numero text, anio int, titulo text, "
                "    materias text[], sancion date, publicacion date, emisor_id uuid, "
                "    url_oficial text, identidad_incierta boolean)"
                "), insertadas AS ("
                "  INSERT INTO normas (id, jurisdiccion_id, emisor_id, tipo, numero, anio, "
                "                      titulo, materias, sancion, publicacion, identidad_incierta) "
                "  SELECT e.id, :j, e.emisor_id, e.tipo, e.numero, e.anio, e.titulo, e.materias, "
                "         e.sancion, e.publicacion, e.identidad_incierta "
                "    FROM entrada e"
                ") "
                "INSERT INTO norma_identificadores (norma_id, namespace, valor, url_oficial) "
                "SELECT e.id, :ns, e.infoleg_id, e.url_oficial FROM entrada e "
                "ON CONFLICT (namespace, valor) DO NOTHING"
            ),
            {"filas": _json(nuevos), "j": JURISDICCION, "ns": NAMESPACE},
        )

    def _registrar_coemisiones(self, coemisiones: dict[str, list[str]]) -> None:
        """Deja constancia de cada norma conjunta, con el emisor que quedó
        cargado y los firmantes que el modelo no puede alojar todavía."""
        if not coemisiones:
            return
        cargados = {
            fila[0]: fila[1]
            for fila in self.conexion.execute(
                text(
                    "SELECT i.valor, o.nombre FROM norma_identificadores i "
                    "  JOIN normas n ON n.id = i.norma_id "
                    "  LEFT JOIN organismos o ON o.id = n.emisor_id "
                    " WHERE i.namespace = :ns AND i.valor = ANY(:vs)"
                ),
                {"ns": NAMESPACE, "vs": list(coemisiones)},
            )
        }
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "  (tipo, severidad, estado, source_id, descripcion, candidatos, responsable_rol) "
                "SELECT :tipo, :sev, :estado, :src, x.descripcion, x.candidatos, :rol "
                "  FROM json_to_recordset(CAST(:filas AS json)) "
                "       AS x(descripcion text, candidatos jsonb)"
            ),
            {
                "tipo": TipoIncidencia.IDENTIDAD_AMBIGUA.value,
                "sev": Severidad.INFO.value,
                "estado": EstadoIncidencia.ABIERTA.value,
                "src": SOURCE_ID,
                "rol": "curador de datos",
                "filas": json.dumps(
                    [
                        {
                            "descripcion": (
                                f"La norma InfoLEG {identificador} aparece en "
                                f"{len(firmantes) + 1} filas del catálogo, una por organismo "
                                "firmante. Se cargó una sola norma; el modelo admite un emisor "
                                "y los demás firmantes quedan acá para que alguien decida cómo "
                                "representarlos."
                            ),
                            "candidatos": {
                                "emisor_cargado": cargados.get(identificador),
                                "otros_firmantes": firmantes,
                            },
                        }
                        for identificador, firmantes in coemisiones.items()
                    ],
                    ensure_ascii=False,
                ),
            },
        )


def _clave_canonica(fila: dict) -> tuple[str, str, int] | None:
    """Clave canónica de una fila cruda, o `None` si el tipo no la usa."""
    tipo = _tipo(fila["tipo_norma"])
    if tipo not in CLAVE_JURISDICCIONAL:
        return None
    numero = _numero(fila["numero_norma"])
    if numero is None:
        return None
    sancion = _fecha(fila["fecha_sancion"]) or _fecha(fila["fecha_boletin"])
    return None if sancion is None else (tipo.value, numero, sancion.year)


def _json(filas: list[dict]) -> str:
    return json.dumps(
        [
            {
                **{k: v for k, v in fila.items() if k != "organismo_nombre"},
                "sancion": fila["sancion"].isoformat() if fila["sancion"] else None,
                "publicacion": fila["publicacion"].isoformat() if fila["publicacion"] else None,
                "emisor_id": str(fila["emisor_id"]) if fila["emisor_id"] else None,
            }
            for fila in filas
        ],
        ensure_ascii=False,
    )
