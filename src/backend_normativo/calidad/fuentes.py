"""P-006 criterio 1: un HTTP 200 no basta.

El manifiesto declara, para cada fuente, en qué tablas tiene que terminar lo que
esa fuente aporta. Nadie lo comprobaba. Una fuente podía capturarse bien,
extraerse bien y no dejar una sola fila donde su historia dice que debería
dejarla, y el catálogo la mostraba igual: `ACTIVE`, `ACCESIBLE`, capturada.

Este informe compara lo declarado con lo que hay. La regla de atribución es la
misma disciplina del proyecto: **una fila es de una fuente cuando su evidencia
lleva de vuelta a un documento de esa fuente**. Donde una tabla no tiene por
dónde atribuirse, se dice, en vez de contar cero y hacerlo pasar por vacío.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# El camino de la evidencia hasta la fuente. Se repite en casi todas las
# consultas, así que se escribe una vez.
POR_EVIDENCIA = (
    "JOIN evidencias ev ON ev.id = {tabla}.evidencia_id "
    "JOIN documento_versiones dv ON dv.id = ev.doc_version_id "
    "JOIN documentos doc ON doc.id = dv.documento_id "
    "WHERE doc.source_id = :sid"
)

# El de la versión documental, para lo que cuelga de un documento sin evidencia
# propia.
POR_DOC_VERSION = (
    "JOIN documento_versiones dv ON dv.id = {tabla}.doc_version_id "
    "JOIN documentos doc ON doc.id = dv.documento_id "
    "WHERE doc.source_id = :sid"
)


def _evidencia(tabla: str) -> str:
    return f"SELECT count(*) FROM {tabla} {POR_EVIDENCIA.format(tabla=tabla)}"


def _doc_version(tabla: str) -> str:
    return f"SELECT count(*) FROM {tabla} {POR_DOC_VERSION.format(tabla=tabla)}"


def _directo(tabla: str, columna: str = "source_id") -> str:
    return f"SELECT count(*) FROM {tabla} WHERE {columna} = :sid"


# Cómo se cuenta lo que cada fuente dejó en cada tabla. `None` significa que no
# hay forma de atribuirla: son tablas de identidades compartidas —una norma no
# es «de» una fuente, es la norma; varias fuentes la publican— y contarlas por
# fuente diría algo falso.
ATRIBUCION: dict[str, str | None] = {
    # Directas: la fila lleva la fuente encima.
    "fuentes": _directo("fuentes"),
    "fuente_urls": _directo("fuente_urls"),
    "documentos": _directo("documentos"),
    "fuentes_candidatas": _directo("fuentes_candidatas", "source_id_origen"),
    # Cuelgan de la versión documental.
    "documento_versiones": (
        "SELECT count(*) FROM documento_versiones dv "
        "  JOIN documentos doc ON doc.id = dv.documento_id WHERE doc.source_id = :sid"
    ),
    "unidades_documentales": _doc_version("unidades_documentales"),
    "norma_versiones": _doc_version("norma_versiones"),
    "tramite_versiones": _doc_version("tramite_versiones"),
    # Cuelgan de su evidencia.
    "canales": _evidencia("canales"),
    "barrios_renabap": _evidencia("barrios_renabap"),
    "parametro_valores": _evidencia("parametro_valores"),
    "plazos": _evidencia("plazos"),
    "equivalencias_unidades": _evidencia("equivalencias_unidades"),
    "reglas": _evidencia("reglas"),
    "tramite_pasos": _evidencia("tramite_pasos"),
    "referencias_pendientes": _evidencia("referencias_pendientes"),
    "relaciones_normativas": _evidencia("relaciones_normativas"),
    "beneficio_versiones": (
        "SELECT count(DISTINCT bn.beneficio_version_id) FROM beneficio_normas bn "
        "  JOIN evidencias ev ON ev.id = bn.evidencia_id "
        "  JOIN documento_versiones dv ON dv.id = ev.doc_version_id "
        "  JOIN documentos doc ON doc.id = dv.documento_id WHERE doc.source_id = :sid"
    ),
    # Un punto de atención no trae evidencia propia; sus canales sí, y un punto
    # sin ningún canal no lo publicó nadie.
    "puntos_atencion": (
        "SELECT count(DISTINCT c.punto_id) FROM canales c "
        "  JOIN evidencias ev ON ev.id = c.evidencia_id "
        "  JOIN documento_versiones dv ON dv.id = ev.doc_version_id "
        "  JOIN documentos doc ON doc.id = dv.documento_id "
        " WHERE doc.source_id = :sid AND c.punto_id IS NOT NULL"
    ),
    "tramites": (
        "SELECT count(DISTINCT tv.tramite_id) FROM tramite_versiones tv "
        "  JOIN documento_versiones dv ON dv.id = tv.doc_version_id "
        "  JOIN documentos doc ON doc.id = dv.documento_id WHERE doc.source_id = :sid"
    ),
    "normas": (
        "SELECT count(DISTINCT nv.norma_id) FROM norma_versiones nv "
        "  JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
        "  JOIN documentos doc ON doc.id = dv.documento_id WHERE doc.source_id = :sid"
    ),
    # Identidades compartidas: no son de nadie en particular.
    "beneficios": None,
    "organismos": None,
    "parametros": None,
    "norma_identificadores": None,
}

# Qué se considera que la fuente «llegó a destino». `fuentes` y `fuente_urls` se
# llenan con solo cargar el catálogo, así que una fuente cuyo único destino sea
# ese no acredita haber traído nada.
SOLO_CATALOGO = frozenset({"fuentes", "fuente_urls", "fuentes_candidatas"})

# `NO_VERIFICADO` no es un bloqueo: es que nadie la tocó todavía. Contarla como
# bloqueada mezcla trece fuentes que están esperando su turno con las dos que sí
# tienen un impedimento real, y esconde a las dos entre las trece.
NO_ES_BLOQUEO = frozenset({"ACCESIBLE", "NO_VERIFICADO"})

SIRVE = "sirve"
SIN_DESTINO = "sin destino"
SIN_EXTRAER = "sin extraer"
BLOQUEADA = "bloqueada"
SIN_CORRER = "sin correr"
SOLO_DESCUBRIMIENTO = "solo descubrimiento"


@dataclass
class FuenteVerificada:
    source_id: str
    nombre: str
    clase: str
    prioridad: str
    estado: str
    access_status: str
    motivo_estado: str | None = None
    capturas: int = 0
    ultimo_http: int | None = None
    doc_versiones: int = 0
    unidades: int = 0
    # Filas que el importador declaró haber cargado (control DQ11). Un dataset
    # no deja evidencia por fila —no hay fragmento que citar en un ZIP de
    # 428.380 renglones— así que su acreditación es la conciliación.
    conciliadas: int | None = None
    incidencias: int = 0
    declaradas: list[str] = field(default_factory=list)
    pobladas: dict[str, int] = field(default_factory=dict)
    vacias: list[str] = field(default_factory=list)
    no_atribuibles: list[str] = field(default_factory=list)

    @property
    def sustantivas(self) -> list[str]:
        """Las tablas declaradas que no se llenan con solo cargar el catálogo."""
        return [t for t in self.declaradas if t not in SOLO_CATALOGO]

    @property
    def veredicto(self) -> str:
        if self.access_status not in NO_ES_BLOQUEO:
            return BLOQUEADA
        if self.capturas == 0:
            return SIN_CORRER
        if not self.sustantivas:
            return SOLO_DESCUBRIMIENTO
        if any(self.pobladas.get(t, 0) > 0 for t in self.sustantivas):
            return SIRVE
        if self.conciliadas:
            # El importador dio cuenta de sus filas aunque la atribución por
            # evidencia no las alcance. Decir que no llegó a destino sería
            # falso: F01 carga 428.380 normas y ninguna trae evidencia propia.
            return SIRVE
        if self.doc_versiones == 0:
            return SIN_EXTRAER
        return SIN_DESTINO

    @property
    def acreditada_por_conciliacion(self) -> bool:
        return self.veredicto == SIRVE and not any(
            self.pobladas.get(t, 0) > 0 for t in self.sustantivas
        )


@dataclass
class ReporteFuentes:
    fuentes: list[FuenteVerificada] = field(default_factory=list)

    def por_veredicto(self, veredicto: str) -> list[FuenteVerificada]:
        return [f for f in self.fuentes if f.veredicto == veredicto]

    @property
    def sin_destino(self) -> list[FuenteVerificada]:
        return self.por_veredicto(SIN_DESTINO)

    @property
    def sin_extraer(self) -> list[FuenteVerificada]:
        return self.por_veredicto(SIN_EXTRAER)


def construir(conexion: Connection) -> ReporteFuentes:
    reporte = ReporteFuentes()
    filas = conexion.execute(
        text(
            "SELECT source_id, nombre, clase, prioridad, estado, access_status, "
            "       motivo_estado, tablas_destino "
            "  FROM fuentes ORDER BY source_id"
        )
    ).mappings()

    for fila in filas:
        fuente = FuenteVerificada(
            source_id=fila["source_id"],
            nombre=fila["nombre"],
            clase=fila["clase"],
            prioridad=fila["prioridad"],
            estado=fila["estado"],
            access_status=fila["access_status"],
            motivo_estado=fila["motivo_estado"],
            declaradas=list(fila["tablas_destino"] or []),
        )
        parametros = {"sid": fuente.source_id}
        fuente.capturas = conexion.execute(
            text(
                "SELECT count(*) FROM capturas c JOIN fuente_urls u ON u.id = c.source_url_id "
                " WHERE u.source_id = :sid"
            ),
            parametros,
        ).scalar_one()
        fuente.ultimo_http = conexion.execute(
            text(
                "SELECT c.http_status FROM capturas c "
                "  JOIN fuente_urls u ON u.id = c.source_url_id "
                " WHERE u.source_id = :sid ORDER BY c.capturado_en DESC LIMIT 1"
            ),
            parametros,
        ).scalar_one_or_none()
        fuente.doc_versiones = conexion.execute(
            text(
                "SELECT count(*) FROM documento_versiones dv "
                "  JOIN capturas c ON c.id = dv.captura_id "
                "  JOIN fuente_urls u ON u.id = c.source_url_id WHERE u.source_id = :sid"
            ),
            parametros,
        ).scalar_one()
        fuente.conciliadas = conexion.execute(
            text(
                "SELECT max((cc.observado->>'nuevas')::int + (cc.observado->>'repetidas')::int) "
                "  FROM controles_calidad cc "
                "  JOIN corridas_ingesta ci ON ci.id = cc.corrida_id "
                " WHERE cc.control_id = 'DQ11' AND ci.source_id = :sid"
            ),
            parametros,
        ).scalar_one_or_none()
        fuente.unidades = conexion.execute(
            text(
                "SELECT count(*) FROM unidades_documentales ud "
                "  JOIN documento_versiones dv ON dv.id = ud.doc_version_id "
                "  JOIN documentos doc ON doc.id = dv.documento_id WHERE doc.source_id = :sid"
            ),
            parametros,
        ).scalar_one()
        fuente.incidencias = conexion.execute(
            text(
                "SELECT count(*) FROM incidencias_revision "
                " WHERE source_id = :sid AND estado IN ('ABIERTA', 'EN_REVISION')"
            ),
            parametros,
        ).scalar_one()

        for tabla in fuente.declaradas:
            consulta = ATRIBUCION.get(tabla, "")
            if consulta is None:
                fuente.no_atribuibles.append(tabla)
                continue
            if not consulta:
                # Una tabla declarada que el esquema no tiene es un error del
                # manifiesto, y se muestra como tal en vez de ignorarse.
                fuente.no_atribuibles.append(f"{tabla} (no existe en el esquema)")
                continue
            cuantas = conexion.execute(text(consulta), parametros).scalar_one()
            fuente.pobladas[tabla] = cuantas
            if cuantas == 0:
                fuente.vacias.append(tabla)

        reporte.fuentes.append(fuente)
    return reporte


def formatear(reporte: ReporteFuentes) -> str:
    total = len(reporte.fuentes)
    conteo = {
        v: len(reporte.por_veredicto(v))
        for v in (SIRVE, SIN_DESTINO, SIN_EXTRAER, SOLO_DESCUBRIMIENTO, BLOQUEADA, SIN_CORRER)
    }
    por_conciliacion = [f for f in reporte.fuentes if f.acreditada_por_conciliacion]
    lineas = [
        "# Fuentes contra su historia",
        "",
        "El manifiesto declara en qué tablas tiene que terminar lo que cada fuente aporta. "
        "Esto compara lo declarado con lo que hay. Una fila se atribuye a una fuente cuando "
        "su evidencia lleva de vuelta a un documento de esa fuente.",
        "",
        f"- Fuentes en el catálogo: {total}",
        f"- **Sirven** (dejaron filas donde su historia dice): {conteo[SIRVE]}"
        + (
            f", de las cuales {len(por_conciliacion)} acreditadas por la conciliación "
            "del importador y no por evidencia por fila"
            if por_conciliacion
            else ""
        ),
        f"- **Capturadas, extraídas y sin destino** (200 y ninguna fila): {conteo[SIN_DESTINO]}",
        f"- **Capturadas y nunca extraídas**: {conteo[SIN_EXTRAER]}",
        f"- Solo descubrimiento (su destino es el catálogo mismo): {conteo[SOLO_DESCUBRIMIENTO]}",
        f"- Bloqueadas: {conteo[BLOQUEADA]}",
        f"- Sin correr: {conteo[SIN_CORRER]}",
        "",
    ]

    if reporte.sin_destino:
        lineas += [
            "## Capturadas y sin llegar a destino",
            "",
            "Estas respondieron, se extrajeron y no dejaron una sola fila donde su historia "
            "dice que deberían. Es exactamente lo que el criterio quiere ver: un HTTP 200 no "
            "acredita nada por sí solo.",
            "",
            "| Fuente | Prioridad | Versiones | Unidades | Tablas declaradas y vacías |",
            "| --- | --- | ---: | ---: | --- |",
        ]
        for fuente in sorted(reporte.sin_destino, key=lambda f: (f.prioridad, f.source_id)):
            vacias = ", ".join(t for t in fuente.vacias if t not in SOLO_CATALOGO)
            lineas.append(
                f"| {fuente.source_id} | {fuente.prioridad} | {fuente.doc_versiones} | "
                f"{fuente.unidades} | {vacias or '—'} |"
            )
        lineas.append("")

    if reporte.sin_extraer:
        lineas += [
            "## Capturadas y nunca extraídas",
            "",
            "Respondieron 200, los bytes están guardados y ninguna versión documental salió "
            "de ellos. No es lo mismo que la anterior: acá el problema está antes, en que "
            "ningún adaptador las procesó.",
            "",
            "| Fuente | Prioridad | Capturas | Último HTTP | Tablas declaradas |",
            "| --- | --- | ---: | ---: | --- |",
        ]
        for fuente in sorted(reporte.sin_extraer, key=lambda f: (f.prioridad, f.source_id)):
            declaradas = ", ".join(fuente.sustantivas)
            lineas.append(
                f"| {fuente.source_id} | {fuente.prioridad} | {fuente.capturas} | "
                f"{fuente.ultimo_http or '—'} | {declaradas or '—'} |"
            )
        lineas.append("")

    bloqueadas = reporte.por_veredicto(BLOQUEADA)
    if bloqueadas:
        lineas += [
            "## Bloqueadas",
            "",
            "El fallo se conserva y la capacidad queda pendiente. No se convierte en «sin datos».",
            "",
            "| Fuente | Estado de acceso | Motivo | Incidencias abiertas |",
            "| --- | --- | --- | ---: |",
        ]
        for fuente in sorted(bloqueadas, key=lambda f: (f.access_status, f.source_id)):
            motivo = (fuente.motivo_estado or "—").replace("|", "/")[:110]
            lineas.append(
                f"| {fuente.source_id} | {fuente.access_status} | {motivo} | {fuente.incidencias} |"
            )
        lineas.append("")

    sin_correr = reporte.por_veredicto(SIN_CORRER)
    if sin_correr:
        lineas += [
            "## Sin correr",
            "",
            "Ninguna captura las tocó. No están bloqueadas —no hay impedimento "
            "registrado— simplemente no llegó su turno, y por eso su estado de acceso "
            "sigue sin verificar: verificarlo es intentarlo.",
            "",
            "- " + ", ".join(f.source_id for f in sin_correr),
            "",
        ]

    lineas += [
        "## Qué no dice",
        "",
        "Que lo que llegó sea correcto ni completo. Dice que llegó algo a la tabla que la "
        "historia declara. Que la paginación se haya recorrido entera, que los anexos estén "
        "y que el contenido sea el esperado lo verifica la prueba de cada familia de "
        "fuentes, no este recuento.",
        "",
        "Tampoco dice que una fuente sin filas esté rota: puede que su aporte ya estuviera "
        "cargado por otra que publica la misma norma. Lo que dice es que su historia, como "
        "está declarada, no se cumplió.",
    ]
    return "\n".join(lineas) + "\n"
