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


def _ingestables(conteo: dict[str, int]) -> int:
    """Las fuentes de las que tiene sentido esperar filas hoy.

    No es el catálogo entero: descuenta las que el catálogo declaró que no se
    ingestan, las que la política de acceso no permite tocar y las que esperan
    que una persona suba un archivo. Contra ese denominador, «no sirve»
    significa que algo falta hacer.
    """
    return (
        conteo[SIRVE]
        + conteo[SIN_DESTINO]
        + conteo[SIN_EXTRAER]
        + conteo[SOLO_DESCUBRIMIENTO]
        + conteo[SIN_CORRER]
        + conteo[DECLARA_AUSENCIA]
    )


SIRVE = "sirve"
SIN_DESTINO = "sin destino"
SIN_EXTRAER = "sin extraer"
BLOQUEADA = "bloqueada"
SIN_CORRER = "sin correr"
SOLO_DESCUBRIMIENTO = "solo descubrimiento"
NO_SE_INGESTA = "no se ingesta"
ESPERA_CARGA_MANUAL = "espera carga manual"
DECLARA_AUSENCIA = "declara ausencia"

# Estados del catálogo que dicen que esta fuente no se captura, y por qué.
# Contarlas como «sin correr» las presenta como trabajo pendiente cuando son
# una decisión ya tomada, e infla el denominador de lo que falta.
ESTADOS_SIN_INGESTA: dict[str, str] = {
    "REFERENCE_ONLY": "el catálogo la declara solo de referencia",
    "RETIRED": "el catálogo la declara retirada",
}
ESTADO_MANUAL = "MANUAL"

# Un alias no es una fuente: es otro nombre de una que ya está. Su aporte lo
# hace la canónica, y esperar filas suyas sería contar dos veces.
CLASE_ALIAS = "ALIAS"


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
    # Lo que la página dice cuando dice que no hay nada. «La atención presencial
    # permanecerá cerrada hasta el nuevo período» no es una carga que faltó: es
    # la respuesta, y contarla como fuente que no llegó a destino la convierte
    # en una tarea pendiente que nadie puede completar porque no hay qué cargar.
    cierre_declarado: str | None = None
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
    def por_que_no_se_ingesta(self) -> str | None:
        """Por qué el catálogo decidió que esta fuente no se captura."""
        if self.clase == CLASE_ALIAS:
            return "es un alias de otra fuente; su aporte lo hace la canónica"
        return ESTADOS_SIN_INGESTA.get(self.estado)

    @property
    def veredicto(self) -> str:
        if self.access_status not in NO_ES_BLOQUEO:
            return BLOQUEADA
        # Antes de preguntar si corrió, preguntar si tenía que correr. Una
        # fuente retirada, un alias o una de referencia no están esperando
        # turno: el catálogo ya decidió, y llamarlas «sin correr» convierte una
        # decisión en trabajo pendiente.
        if self.capturas == 0 and self.por_que_no_se_ingesta:
            return NO_SE_INGESTA
        if self.capturas == 0 and self.estado == ESTADO_MANUAL:
            return ESPERA_CARGA_MANUAL
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
        if self.cierre_declarado:
            return DECLARA_AUSENCIA
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
        # Se consulta la estructura que el adaptador dejó, no el texto de una
        # incidencia: un acuerdo por prosa entre dos módulos se rompe en
        # silencio el día que alguien mejora la redacción.
        fuente.cierre_declarado = conexion.execute(
            text(
                "SELECT dv.identidad_candidata->'pagina'->>'cierre_declarado' "
                "  FROM documento_versiones dv "
                "  JOIN capturas c ON c.id = dv.captura_id "
                "  JOIN fuente_urls u ON u.id = c.source_url_id "
                " WHERE u.source_id = :sid "
                "   AND dv.identidad_candidata->'pagina'->>'cierre_declarado' IS NOT NULL "
                " ORDER BY dv.creado_en DESC LIMIT 1"
            ),
            parametros,
        ).scalar_one_or_none()
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
        for v in (
            SIRVE,
            SIN_DESTINO,
            SIN_EXTRAER,
            SOLO_DESCUBRIMIENTO,
            BLOQUEADA,
            DECLARA_AUSENCIA,
            NO_SE_INGESTA,
            ESPERA_CARGA_MANUAL,
            SIN_CORRER,
        )
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
        f"- Declaran que no hay nada que cargar: {conteo[DECLARA_AUSENCIA]}",
        f"- Bloqueadas: {conteo[BLOQUEADA]}",
        f"- No se ingestan (alias, retiradas o de referencia): {conteo[NO_SE_INGESTA]}",
        f"- Esperan carga manual: {conteo[ESPERA_CARGA_MANUAL]}",
        f"- Sin correr: {conteo[SIN_CORRER]}",
        "",
        # HU-001 criterio 4 pide denominadores y pide no usarlos como sinónimos.
        # «44 de 85» mezcla en el mismo denominador nueve fuentes que nadie va a
        # ingestar y diecisiete que la política de acceso no permite tocar.
        f"**Sobre las que se pueden ingestar hoy** —descontadas las {conteo[NO_SE_INGESTA]} "
        f"que no se ingestan, las {conteo[BLOQUEADA]} bloqueadas y las "
        f"{conteo[ESPERA_CARGA_MANUAL]} de carga manual— sirven "
        f"**{conteo[SIRVE]} de {_ingestables(conteo)}**.",
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

    ausencias = reporte.por_veredicto(DECLARA_AUSENCIA)
    if ausencias:
        lineas += [
            "## Declaran que no hay nada que cargar",
            "",
            "Su página dice, con todas las letras, que no hay sedes abiertas, turnos ni "
            "inscripción en curso. Eso **es** el dato: contarlas como fuentes que no "
            "llegaron a destino inventa una tarea que nadie puede completar, porque no hay "
            "qué cargar. Y completarlas con el listado de una captura anterior lo "
            "presentaría como vigente.",
            "",
            "| Fuente | Qué declara |",
            "| --- | --- |",
        ]
        lineas += [
            f"| {f.source_id} | «{(f.cierre_declarado or '')[:110]}» |"
            for f in sorted(ausencias, key=lambda f: f.source_id)
        ]
        lineas.append("")

    no_se_ingestan = reporte.por_veredicto(NO_SE_INGESTA)
    if no_se_ingestan:
        lineas += [
            "## No se ingestan, y está decidido",
            "",
            "Ninguna captura las tocó y ninguna debería: el catálogo ya declaró qué son. "
            "Contarlas como pendientes infla lo que falta con trabajo que nadie va a "
            "hacer, porque no hay nada que hacer.",
            "",
            "| Fuente | Estado | Por qué |",
            "| --- | --- | --- |",
        ]
        lineas += [
            f"| {f.source_id} | {f.estado} | {f.por_que_no_se_ingesta} |"
            for f in sorted(no_se_ingestan, key=lambda f: f.source_id)
        ]
        lineas.append("")

    manuales = reporte.por_veredicto(ESPERA_CARGA_MANUAL)
    if manuales:
        lineas += [
            "## Esperan una carga manual",
            "",
            "El catálogo las declara de carga manual: su contenido no se captura, se "
            "sube. Están pendientes, y lo que falta es que una persona cargue el "
            "archivo con `bn ingesta cargar-manual`, no que corra un capturador.",
            "",
            "- " + ", ".join(sorted(f.source_id for f in manuales)),
            "",
        ]

    sin_correr = reporte.por_veredicto(SIN_CORRER)
    if sin_correr:
        lineas += [
            "## Sin correr",
            "",
            "Activas, sin impedimento registrado y sin una sola captura: acá sí "
            "simplemente no llegó su turno, y por eso su estado de acceso sigue sin "
            "verificar —verificarlo es intentarlo—.",
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
