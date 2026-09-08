"""Métricas de cobertura, informadas por separado.

La especificación (§7) las pide separadas y no promediadas, porque miden cosas
distintas y mezclarlas produce un número que suena bien y no significa nada:

a. cobertura de fuentes
b. porcentaje de campos evaluados
c. porcentaje de campos con valor sustantivo validado
d. porcentaje de campos críticos frescos
e. conflictos abiertos por severidad
f. dependencias pendientes
g. fidelidad de extracción
h. capacidades publicables

Un 100% de filas en `NO_INFORMADO_EN_FUENTES_REVISADAS` da cobertura de
evaluación completa y valor sustantivo cero. Este módulo hace visible esa
diferencia en vez de esconderla detrás de un promedio.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS


@dataclass
class CoberturaDeFuentes:
    total: int = 0
    por_estado: dict[str, int] = field(default_factory=dict)
    por_disponibilidad: dict[str, int] = field(default_factory=dict)
    con_captura: int = 0
    con_documento: int = 0
    bloqueadas: int = 0
    sin_url_conocida: int = 0

    @property
    def pendientes(self) -> int:
        return self.total - self.con_captura


@dataclass
class CoberturaDeCampos:
    versiones: int = 0
    esperadas: int = 0
    evaluadas: int = 0
    por_estado: dict[str, int] = field(default_factory=dict)

    @property
    def porcentaje_evaluado(self) -> float:
        return round(100 * self.evaluadas / self.esperadas, 2) if self.esperadas else 0.0

    @property
    def con_valor_sustantivo(self) -> int:
        """Solo `INFORMADO` cuenta. Un campo revisado sin información no."""
        return self.por_estado.get("INFORMADO", 0)

    @property
    def porcentaje_sustantivo(self) -> float:
        return round(100 * self.con_valor_sustantivo / self.esperadas, 2) if self.esperadas else 0.0


@dataclass
class Metricas:
    fuentes: CoberturaDeFuentes = field(default_factory=CoberturaDeFuentes)
    campos: CoberturaDeCampos = field(default_factory=CoberturaDeCampos)
    conflictos_por_severidad: dict[str, int] = field(default_factory=dict)
    dependencias_pendientes: int = 0
    extraccion: dict[str, float] = field(default_factory=dict)
    capacidades_publicables: dict[str, int] = field(default_factory=dict)
    corpus: dict[str, int] = field(default_factory=dict)

    def a_dict(self) -> dict:
        datos = asdict(self)
        datos["campos"]["porcentaje_evaluado"] = self.campos.porcentaje_evaluado
        datos["campos"]["porcentaje_sustantivo"] = self.campos.porcentaje_sustantivo
        datos["campos"]["con_valor_sustantivo"] = self.campos.con_valor_sustantivo
        datos["fuentes"]["pendientes"] = self.fuentes.pendientes
        return datos


def _conteo(conexion: Connection, sql: str, parametros: dict | None = None) -> dict[str, int]:
    return {fila[0]: fila[1] for fila in conexion.execute(text(sql), parametros or {})}


def medir(conexion: Connection) -> Metricas:
    metricas = Metricas()

    # (a) Cobertura de fuentes.
    f = metricas.fuentes
    f.total = conexion.execute(text("SELECT count(*) FROM fuentes")).scalar_one()
    f.por_estado = _conteo(conexion, "SELECT estado, count(*) FROM fuentes GROUP BY 1")
    f.por_disponibilidad = _conteo(
        conexion, "SELECT access_status, count(*) FROM fuentes GROUP BY 1"
    )
    f.con_captura = conexion.execute(
        text(
            "SELECT count(DISTINCT u.source_id) FROM capturas c "
            "JOIN fuente_urls u ON u.id = c.source_url_id"
        )
    ).scalar_one()
    f.con_documento = conexion.execute(
        text("SELECT count(DISTINCT source_id) FROM documentos")
    ).scalar_one()
    f.bloqueadas = conexion.execute(
        text(
            "SELECT count(*) FROM fuentes "
            "WHERE access_status IN ('BLOQUEADA', 'ACCESO_LIMITADO', 'ERROR_TLS')"
        )
    ).scalar_one()
    f.sin_url_conocida = conexion.execute(
        text("SELECT count(*) FROM fuentes WHERE access_status = 'SIN_URL_CONOCIDA'")
    ).scalar_one()

    # (b) y (c) Campos evaluados y campos con valor sustantivo.
    c = metricas.campos
    c.versiones = conexion.execute(text("SELECT count(*) FROM norma_versiones")).scalar_one()
    c.esperadas = c.versiones * len(CAMPOS_SOLICITADOS)
    c.evaluadas = conexion.execute(
        text("SELECT count(*) FROM evaluaciones_completitud")
    ).scalar_one()
    c.por_estado = _conteo(
        conexion, "SELECT estado, count(*) FROM evaluaciones_completitud GROUP BY 1"
    )

    # (e) Conflictos abiertos por severidad.
    metricas.conflictos_por_severidad = _conteo(
        conexion,
        "SELECT severidad, count(*) FROM incidencias_revision "
        "WHERE estado IN ('ABIERTA', 'EN_REVISION') GROUP BY 1",
    )

    # (f) Dependencias pendientes.
    metricas.dependencias_pendientes = conexion.execute(
        text("SELECT count(*) FROM referencias_pendientes WHERE estado = 'PENDIENTE'")
    ).scalar_one()

    # (g) Fidelidad de extracción: señal técnica, separada del juicio de vigencia.
    fila = conexion.execute(
        text(
            "SELECT coalesce(avg(extraccion_score), 0), coalesce(min(extraccion_score), 0), "
            "       count(*) FILTER (WHERE extraccion_score < 0.6) "
            "  FROM documento_versiones WHERE extraccion_score IS NOT NULL"
        )
    ).one()
    metricas.extraccion = {
        "score_promedio": round(float(fila[0]), 4),
        "score_minimo": round(float(fila[1]), 4),
        "versiones_bajo_umbral": int(fila[2]),
    }

    # (h) Capacidades publicables: cuántas versiones puede servir cada una hoy.
    capacidades = conexion.execute(
        text(
            "SELECT c, (SELECT count(*) FROM v_hechos_servibles(current_date, now(), c)) "
            "FROM unnest(ARRAY['IDENTIFICACION','DESCRIPCION_GENERAL','REQUISITOS',"
            "'EVALUACION_PRELIMINAR','MONTO','PLAZO','CANAL','EXPLICACION_HISTORICA']) AS c"
        )
    ).all()
    metricas.capacidades_publicables = {fila[0]: fila[1] for fila in capacidades}

    metricas.corpus = {
        tabla: conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()
        for tabla in (
            "capturas",
            "documentos",
            "documento_versiones",
            "unidades_documentales",
            "evidencias",
            "normas",
            "norma_versiones",
            "relaciones_normativas",
            "beneficios",
            "afirmaciones",
            "releases",
        )
    }
    return metricas


def formatear(metricas: Metricas) -> str:
    f, c = metricas.fuentes, metricas.campos
    lineas: list[str] = []
    a = lineas.append

    a("# Cobertura y calidad del corpus")
    a("")
    a("Las métricas se informan por separado porque miden cosas distintas.")
    a("Promediarlas produce un número que suena bien y no significa nada.")
    a("")
    a("## (a) Cobertura de fuentes")
    a("")
    a("| Concepto | Cantidad |")
    a("|---|---:|")
    a(f"| Fuentes en el catálogo | {f.total} |")
    a(f"| Con al menos una captura | {f.con_captura} |")
    a(f"| Con documentos extraídos | {f.con_documento} |")
    a(f"| Sin URL conocida | {f.sin_url_conocida} |")
    a(f"| Con acceso bloqueado o limitado | {f.bloqueadas} |")
    a(f"| Pendientes de capturar | {f.pendientes} |")
    a("")
    a("Una fuente bloqueada no cuenta como poblada.")
    a("")

    a("## (b) y (c) Campos evaluados frente a campos con valor")
    a("")
    a("| Concepto | Valor |")
    a("|---|---:|")
    a(f"| Versiones normativas | {c.versiones} |")
    a(f"| Evaluaciones esperadas (siete campos por versión) | {c.esperadas} |")
    a(f"| Evaluaciones registradas | {c.evaluadas} ({c.porcentaje_evaluado}%) |")
    a(
        f"| Campos con valor sustantivo validado | {c.con_valor_sustantivo} "
        f"({c.porcentaje_sustantivo}%) |"
    )
    a("")
    a("| Estado del campo | Cantidad |")
    a("|---|---:|")
    for estado, cantidad in sorted(c.por_estado.items()):
        a(f"| {estado} | {cantidad} |")
    a("")
    a("Un campo evaluado sin información no cuenta como valor sustantivo. Cien por")
    a("ciento de evaluación con cero valor sustantivo es un resultado posible y")
    a("honesto: significa que se buscó en todas las fichas y todavía no hay nada")
    a("aprobado para publicar.")
    a("")

    a("## (e) Conflictos abiertos por severidad")
    a("")
    a("| Severidad | Abiertos |")
    a("|---|---:|")
    for severidad, cantidad in sorted(metricas.conflictos_por_severidad.items()):
        a(f"| {severidad} | {cantidad} |")
    a("")

    a(
        f"## (f) Dependencias pendientes\n\n{metricas.dependencias_pendientes} referencias "
        "normativas citadas que todavía no se resolvieron contra el corpus."
    )
    a("")

    a("## (g) Fidelidad de extracción")
    a("")
    a("Señal técnica observable, separada del juicio sobre el contenido.")
    a("")
    a("| Métrica | Valor |")
    a("|---|---:|")
    for clave, valor in metricas.extraccion.items():
        a(f"| {clave.replace('_', ' ')} | {valor} |")
    a("")

    a("## (h) Capacidades publicables")
    a("")
    a("Versiones que hoy pueden servirse por capacidad. Una norma con monto")
    a("desconocido puede sustentar una explicación general y aun así abstenerse")
    a("de responder cuánto se cobra.")
    a("")
    a("| Capacidad | Versiones servibles |")
    a("|---|---:|")
    for capacidad, cantidad in metricas.capacidades_publicables.items():
        a(f"| {capacidad} | {cantidad} |")
    a("")

    a("## Corpus cargado")
    a("")
    a("| Tabla | Filas |")
    a("|---|---:|")
    for tabla, cantidad in metricas.corpus.items():
        a(f"| {tabla} | {cantidad} |")
    a("")

    return "\n".join(lineas)
