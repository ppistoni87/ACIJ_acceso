"""P-006 criterio 3: un importe histórico no es el importe de hoy.

La página del Consejo del Salario publica una tabla como esta:

    a partir del 1/10/2026  $ 391.200  $ 195.600  $ 391.200
    a partir del 1/11/2026  $ 398.800  $ 199.400  $ 398.800
    a partir del 1/12/2026  $ 406.400  $ 203.200  $ 406.400

Tres importes, cada uno con su fecha de entrada en vigencia. El error que el
criterio nombra —«un importe histórico nunca reemplaza el actual por ser el
último descargado»— es tomar el último renglón de la descarga más reciente y
servirlo como el monto vigente. Acá, en septiembre de 2026, **ninguno de los
tres rige todavía**: los tres son futuros.

Por eso cada importe entra con su período, y el período sale de la tabla y no de
cuándo se descargó: «a partir del 1/10» rige hasta el día anterior al «a partir
del» siguiente, y el último queda abierto. Lo que el esquema hace con eso ya
estaba: la restricción de exclusión de `parametro_valores` impide que dos
importes publicables del mismo parámetro se pisen en el tiempo, y el disparador
deja fuera de lo publicable cualquier valor sin rango.

**Las columnas se declaran, no se adivinan.** El encabezado de esa tabla es
«Fecha Salario Mínimo, Vital y Móvil Prestación por Desempleo monto mínimo…»,
sin separadores: partirlo por heurística es inventar a qué concepto pertenece
cada número. La fuente declara en su configuración qué parámetros trae y en qué
orden; si un renglón no tiene esa cantidad de importes, se rechaza y se abre
incidencia en vez de acomodarlo.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoRevision,
    Severidad,
    TipoIncidencia,
    ValidTipo,
)

# «a partir del 1/10/2026 $ 391.200 $ 195.600 $ 391.200»
RE_FILA = re.compile(
    r"a partir del\s+(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<anio>\d{4})\s+(?P<importes>.+)",
    re.IGNORECASE,
)
RE_IMPORTE = re.compile(r"\$\s*(?P<monto>\d[\d.]*(?:,\d{1,2})?)")

# Un importe suelto, sin fecha desde la que rija.
RE_IMPORTE_SUELTO = re.compile(r"\$\s*\d[\d.]*(?:,\d{1,2})?")

MONEDA_POR_DEFECTO = "ARS"
UNIDAD_MONEDA = "MONEDA"


def _a_decimal(texto: str) -> Decimal:
    """«391.200» y «391.200,50» a la notación que entiende Decimal."""
    return Decimal(texto.replace(".", "").replace(",", "."))


@dataclass
class FilaDeMontos:
    desde: dt.date
    importes: list[Decimal]
    linea: str


@dataclass
class ResultadoMontos:
    source_id: str = ""
    filas_leidas: int = 0
    valores_creados: int = 0
    valores_existentes: int = 0
    parametros_creados: int = 0
    rechazadas: list[str] = field(default_factory=list)
    sin_periodo: int = 0
    incidencias: int = 0
    avisos: list[str] = field(default_factory=list)


def leer_tabla(texto: str) -> list[FilaDeMontos]:
    """Los renglones «a partir del …» del texto, en el orden en que aparecen."""
    filas: list[FilaDeMontos] = []
    for linea in texto.splitlines():
        coincidencia = RE_FILA.search(linea)
        if coincidencia is None:
            continue
        importes = [
            _a_decimal(m.group("monto")) for m in RE_IMPORTE.finditer(coincidencia["importes"])
        ]
        if not importes:
            continue
        filas.append(
            FilaDeMontos(
                desde=dt.date(
                    int(coincidencia["anio"]), int(coincidencia["mes"]), int(coincidencia["dia"])
                ),
                importes=importes,
                linea=linea.strip(),
            )
        )
    return sorted(filas, key=lambda f: f.desde)


def periodos(filas: list[FilaDeMontos]) -> list[tuple[FilaDeMontos, dt.date, dt.date | None]]:
    """«A partir del X» rige hasta el día anterior al siguiente «a partir del».

    El último queda abierto. Es lo que la tabla dice; no hay que suponer nada.
    """
    tramos = []
    for indice, fila in enumerate(filas):
        siguiente = filas[indice + 1].desde if indice + 1 < len(filas) else None
        hasta = siguiente - dt.timedelta(days=1) if siguiente else None
        tramos.append((fila, fila.desde, hasta))
    return tramos


class CuradorDeMontos:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def cargar(self, source_id: str) -> ResultadoMontos:
        resultado = ResultadoMontos(source_id=source_id)
        version = self._ultima_version(source_id)
        if version is None:
            resultado.avisos.append(f"{source_id} no tiene una versión documental para leer.")
            return resultado

        columnas = self._columnas_declaradas(source_id)
        filas = leer_tabla(version["texto_extraido"] or "")
        resultado.filas_leidas = len(filas)

        if not columnas:
            if filas or RE_IMPORTE_SUELTO.search(version["texto_extraido"] or ""):
                self._incidencia(
                    source_id,
                    f"{source_id} publica importes y su configuración no declara qué "
                    "parámetros trae ni en qué orden. Sin esa declaración, asignar cada "
                    "número a un concepto sería adivinarlo.",
                    resultado,
                )
            return resultado

        parametros = [self._parametro(codigo, resultado) for codigo in columnas]

        for fila, desde, hasta in periodos(filas):
            if len(fila.importes) != len(columnas):
                resultado.rechazadas.append(fila.linea)
                self._incidencia(
                    source_id,
                    f"{source_id}: el renglón «{fila.linea[:120]}» trae "
                    f"{len(fila.importes)} importe(s) y la fuente declara {len(columnas)} "
                    "columna(s). No se carga: acomodarlo sería inventar a qué concepto "
                    "pertenece cada número.",
                    resultado,
                )
                continue
            for parametro_id, importe in zip(parametros, fila.importes, strict=True):
                self._guardar(version, parametro_id, importe, desde, hasta, fila, resultado)

        self._avisar_importes_sin_periodo(source_id, version, filas, resultado)
        return resultado

    # --- Lectura -----------------------------------------------------------

    def _ultima_version(self, source_id: str) -> dict | None:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT dv.id, dv.texto_extraido FROM documento_versiones dv "
                    "  JOIN documentos d ON d.id = dv.documento_id "
                    " WHERE d.source_id = :sid ORDER BY dv.creado_en DESC LIMIT 1"
                ),
                {"sid": source_id},
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    def _columnas_declaradas(self, source_id: str) -> list[str]:
        config = self.conexion.execute(
            text(
                "SELECT selector_config FROM fuente_config_versiones "
                " WHERE source_id = :sid ORDER BY version DESC LIMIT 1"
            ),
            {"sid": source_id},
        ).scalar_one_or_none()
        montos = (config or {}).get("montos") or {}
        return list(montos.get("columnas") or [])

    # --- Escritura ---------------------------------------------------------

    def _parametro(self, codigo: str, resultado: ResultadoMontos) -> uuid.UUID:
        existente = self.conexion.execute(
            text("SELECT id FROM parametros WHERE codigo = :c"), {"c": codigo}
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        resultado.parametros_creados += 1
        return self.conexion.execute(
            text(
                "INSERT INTO parametros (codigo, concepto, unidad, moneda) "
                "VALUES (:c, :concepto, :u, :m) RETURNING id"
            ),
            {
                "c": codigo,
                "concepto": codigo.replace("_", " ").title(),
                "u": UNIDAD_MONEDA,
                "m": MONEDA_POR_DEFECTO,
            },
        ).scalar_one()

    def _evidencia(self, doc_version_id: uuid.UUID, fila: FilaDeMontos) -> uuid.UUID:
        hash_fragmento = hashlib.sha256(fila.linea.encode("utf-8")).hexdigest()
        existente = self.conexion.execute(
            text(
                "SELECT id FROM evidencias WHERE doc_version_id = :dv AND hash_fragmento = :h "
                " ORDER BY creado_en, id LIMIT 1"
            ),
            {"dv": doc_version_id, "h": hash_fragmento},
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, fragmento, hash_fragmento, tipo) "
                "VALUES (:dv, :f, :h, 'FRAGMENTO_TEXTO') RETURNING id"
            ),
            {"dv": doc_version_id, "f": fila.linea, "h": hash_fragmento},
        ).scalar_one()

    def _hecho_id(self, parametro_id: uuid.UUID) -> uuid.UUID:
        """La identidad del hecho «valor de este parámetro», estable entre corridas.

        Cada período es una versión del mismo hecho, no un hecho distinto: por eso
        comparten `hecho_id` y la restricción de exclusión puede compararlos.
        """
        existente = self.conexion.execute(
            text("SELECT hecho_id FROM parametro_valores WHERE parametro_id = :p LIMIT 1"),
            {"p": parametro_id},
        ).scalar_one_or_none()
        return existente or uuid.uuid4()

    def _guardar(
        self,
        version: dict,
        parametro_id: uuid.UUID,
        importe: Decimal,
        desde: dt.date,
        hasta: dt.date | None,
        fila: FilaDeMontos,
        resultado: ResultadoMontos,
    ) -> None:
        hecho_id = self._hecho_id(parametro_id)
        ya_esta = self.conexion.execute(
            text(
                "SELECT 1 FROM parametro_valores pv "
                "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                " WHERE pv.parametro_id = :p AND rv.valid_desde = :desde "
                "   AND pv.valor = :valor LIMIT 1"
            ),
            {"p": parametro_id, "desde": desde, "valor": importe},
        ).first()
        if ya_esta:
            resultado.valores_existentes += 1
            return

        siguiente = self.conexion.execute(
            text(
                "SELECT coalesce(max(numero_version), 0) + 1 FROM registro_versiones "
                " WHERE entidad_tipo = 'parametro_valor' AND entidad_id = :e"
            ),
            {"e": hecho_id},
        ).scalar_one()
        registro_id = self.conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo, valid_desde, valid_hasta) "
                "VALUES ('parametro_valor', :e, :nv, :estado, :vt, :desde, :hasta) RETURNING id"
            ),
            {
                "e": hecho_id,
                "nv": siguiente,
                # Candidato: cargar un importe no es aprobarlo. Publicarlo es una
                # decisión de revisión, y el disparador de la tabla deja fuera de
                # lo publicable todo lo que no esté aprobado.
                "estado": EstadoRevision.CANDIDATE.value,
                # El último renglón queda ABIERTO_FIN y no DESCONOCIDO: un piso
                # salarial rige desde su fecha hasta que otra resolución lo
                # cambie, y publicar el cronograma es respaldar eso. DESCONOCIDO
                # lo dejaría fuera de lo publicable, que es lo contrario de lo
                # que la fuente dice.
                "vt": (ValidTipo.CERRADO if hasta else ValidTipo.ABIERTO_FIN).value,
                "desde": desde,
                "hasta": hasta,
            },
        ).scalar_one()
        self.conexion.execute(
            text(
                "INSERT INTO parametro_valores (registro_version_id, hecho_id, parametro_id, "
                " evidencia_id, valor, unidad, moneda) "
                "VALUES (:rv, :h, :p, :ev, :valor, :u, :m)"
            ),
            {
                "rv": registro_id,
                "h": hecho_id,
                "p": parametro_id,
                "ev": self._evidencia(version["id"], fila),
                "valor": importe,
                "u": UNIDAD_MONEDA,
                "m": MONEDA_POR_DEFECTO,
            },
        )
        resultado.valores_creados += 1

    # --- Lo que no se carga ------------------------------------------------

    def _avisar_importes_sin_periodo(
        self,
        source_id: str,
        version: dict,
        filas: list[FilaDeMontos],
        resultado: ResultadoMontos,
    ) -> None:
        """Un importe sin fecha desde la que rija no se puede servir como actual.

        «El monto de la beca es de $35.000» no dice desde cuándo, y tomar la
        fecha de descarga como su período sería exactamente el error que este
        criterio prohíbe. Se registra como faltante, no se carga.
        """
        texto = version["texto_extraido"] or ""
        con_fecha = {fila.linea for fila in filas}
        sueltos = [
            linea.strip()
            for linea in texto.splitlines()
            if RE_IMPORTE_SUELTO.search(linea) and linea.strip() not in con_fecha
        ]
        if not sueltos:
            return
        resultado.sin_periodo = len(sueltos)
        self._incidencia(
            source_id,
            f"{source_id} publica {len(sueltos)} importe(s) sin declarar desde cuándo "
            f"rigen —por ejemplo «{sueltos[0][:120]}»—. No se cargan: tomar la fecha de "
            "descarga como su período sería servir un importe histórico como el actual.",
            resultado,
            severidad=Severidad.MEDIUM,
        )

    def _incidencia(
        self,
        source_id: str,
        descripcion: str,
        resultado: ResultadoMontos,
        severidad: Severidad = Severidad.HIGH,
    ) -> None:
        ya_abierta = self.conexion.execute(
            text(
                "SELECT 1 FROM incidencias_revision "
                " WHERE source_id = :s AND estado = 'ABIERTA' AND descripcion = :d LIMIT 1"
            ),
            {"s": source_id, "d": descripcion},
        ).first()
        if ya_abierta:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(source_id, tipo, severidad, estado, descripcion, responsable_rol) "
                "VALUES (:s, :t, :sev, 'ABIERTA', :d, 'curacion_juridica')"
            ),
            {
                "s": source_id,
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "sev": severidad.value,
                "d": descripcion,
            },
        )
        resultado.incidencias += 1
        resultado.avisos.append(descripcion)
