"""HU-039: estado del backlog con evidencia de cierre.

Las 123 historias del paquete no se cierran declarándolas cerradas. Este módulo
las separa en dos y usa una evidencia distinta para cada una, porque prometen
cosas distintas:

* Las 40 transversales (HU-001..HU-040) prometen una capacidad del sistema. Su
  evidencia es el código que la implementa y las pruebas que la ejercen: el
  reporte verifica que cada ruta declarada exista y falla si alguna se movió.
* Las 83 por fuente prometen que *esa* fuente esté incorporada. Su evidencia no
  se declara: se lee de la base. Cuántas capturas tiene, si produjo documentos,
  si se le resolvió identidad, si alguna versión suya llegó a un release. Una
  historia por fuente no se cierra escribiendo "hecho": se cierra cuando hay
  filas.

Una fuente bloqueada no es una historia incumplida ni una historia cerrada: es
una historia detenida con un motivo, un responsable y una capacidad afectada.
El reporte la muestra así en vez de esconderla en un porcentaje.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.calidad.fuentes import ESTADO_MANUAL, ESTADOS_SIN_INGESTA

RUTA_ESTADO = pathlib.Path("docs/calidad/estado_backlog.json")
RUTA_BACKLOG = pathlib.Path("docs/paquete/06_Backlog.json")

# Orden de peor a mejor: el reporte agrupa por acá.
# Estados de acceso que sí impiden avanzar. `NO_VERIFICADO` no está: significa
# que la fuente no se intentó todavía.
ACCESOS_IMPEDIDOS = frozenset(
    {"ACCESO_LIMITADO", "BLOQUEADA", "ERROR_TLS", "NO_ENCONTRADA", "SIN_URL_CONOCIDA"}
)

# Estados que el catálogo ya decidió: la fuente no espera turno de captura.
# Se importan de `calidad.fuentes` en vez de repetirse acá porque los dos
# reportes tienen que contar lo mismo; cuando esta lista era propia, el backlog
# llamaba «todavía no se recorrió» a nueve fuentes retiradas, de referencia o
# de carga manual, y convertía nueve decisiones registradas en nueve pendientes.
NO_SE_INGESTA = "NO_SE_INGESTA"
ESPERA_CARGA_MANUAL = "ESPERA_CARGA_MANUAL"

ESTADOS = (
    "NO_INICIADA",
    "BLOQUEADA",
    "EN_CURSO",
    ESPERA_CARGA_MANUAL,
    NO_SE_INGESTA,
    "ALIAS_REGISTRADO",
    "CERRADA",
)


class EvidenciaInexistente(Exception):
    """Una historia declara evidencia en una ruta que no existe."""


@dataclass
class HistoriaTransversal:
    id: str
    titulo: str
    capacidad: str
    prioridad: str
    estado: str
    evidencia: list[str] = field(default_factory=list)
    comandos: list[str] = field(default_factory=list)
    falta: str | None = None
    # Una historia bloqueada tiene que decir quién la desbloquea y con qué. Sin
    # eso, «bloqueada» es indistinguible de «no la hicimos»: las dos se leen como
    # trabajo pendiente y sólo una está esperando a alguien.
    bloqueador: str | None = None
    responsable_rol: str | None = None
    desbloquea_con: str | None = None


@dataclass
class HistoriaDeFuente:
    id: str
    titulo: str
    source_id: str
    capacidad: str
    prioridad: str
    estado: str
    access_status: str | None = None
    alias_de: str | None = None
    urls: int = 0
    capturas: int = 0
    documentos: int = 0
    versiones: int = 0
    unidades: int = 0
    puntos: int = 0
    normas: int = 0
    campos_evaluados: int = 0
    versiones_publicadas: int = 0
    incidencias_abiertas: int = 0
    detencion: str | None = None


@dataclass
class ReporteBacklog:
    total: int = 0
    transversales: list[HistoriaTransversal] = field(default_factory=list)
    fuentes: list[HistoriaDeFuente] = field(default_factory=list)

    def conteo(self, historias) -> dict[str, int]:
        conteo = dict.fromkeys(ESTADOS, 0)
        for historia in historias:
            conteo[historia.estado] = conteo.get(historia.estado, 0) + 1
        return conteo


def construir(conexion: Connection, *, raiz: pathlib.Path | None = None) -> ReporteBacklog:
    base = raiz or pathlib.Path.cwd()
    historias = json.loads((base / RUTA_BACKLOG).read_text())["stories"]
    declarado = json.loads((base / RUTA_ESTADO).read_text())["transversales"]

    faltantes = sorted(
        h["id"] for h in historias if not h.get("source_id") and h["id"] not in declarado
    )
    if faltantes:
        raise EvidenciaInexistente(
            f"Estas historias transversales no declaran estado: {faltantes}. "
            "Sin estado declarado no se sabe si están hechas."
        )

    reporte = ReporteBacklog(total=len(historias))
    metricas = _metricas_por_fuente(conexion)

    for historia in historias:
        if historia.get("source_id"):
            reporte.fuentes.append(
                _historia_de_fuente(historia, metricas.get(historia["source_id"], {}))
            )
            continue
        entrada = declarado[historia["id"]]
        for ruta in entrada.get("evidencia", ()):
            if not (base / ruta).exists():
                raise EvidenciaInexistente(
                    f"{historia['id']} declara evidencia en {ruta} y esa ruta no existe."
                )
        reporte.transversales.append(
            HistoriaTransversal(
                id=historia["id"],
                titulo=historia["title"],
                capacidad=historia["owner_capability"],
                prioridad=historia["priority"],
                estado=entrada["estado"],
                evidencia=list(entrada.get("evidencia", ())),
                comandos=list(entrada.get("comandos", ())),
                falta=entrada.get("falta"),
                bloqueador=entrada.get("bloqueador"),
                responsable_rol=entrada.get("responsable_rol"),
                desbloquea_con=entrada.get("desbloquea_con"),
            )
        )
    _verificar_bloqueos(reporte.transversales)
    return reporte


def _verificar_bloqueos(historias: list[HistoriaTransversal]) -> None:
    """Una historia BLOQUEADA declara su bloqueador y su responsable.

    Es la diferencia entre un impedimento y una tarea sin hacer. Un backlog que
    no la marca deja que «bloqueada» se use como excusa: nadie puede reclamar el
    desbloqueo porque no dice a quién.
    """
    incompletas = [
        h.id
        for h in historias
        if h.estado == "BLOQUEADA" and not (h.bloqueador and h.responsable_rol)
    ]
    if incompletas:
        raise EvidenciaInexistente(
            f"Estas historias se declaran BLOQUEADA sin decir qué las bloquea y quién las "
            f"desbloquea: {incompletas}. Una historia bloqueada sin responsable es una "
            "historia sin hacer con mejor nombre."
        )


def _metricas_por_fuente(conexion: Connection) -> dict[str, dict]:
    filas = (
        conexion.execute(
            text(
                "SELECT f.source_id, f.access_status, f.alias_of, f.estado, f.motivo_estado, "
                "       f.exclusion_reason, f.responsable_rol, "
                "  (SELECT count(*) FROM fuente_urls u WHERE u.source_id = f.source_id) AS urls, "
                "  (SELECT count(*) FROM capturas c JOIN fuente_urls u ON u.id = c.source_url_id "
                "     WHERE u.source_id = f.source_id) AS capturas, "
                "  (SELECT count(*) FROM documentos d WHERE d.source_id = f.source_id) "
                "    AS documentos, "
                "  (SELECT count(*) FROM documento_versiones dv JOIN documentos d "
                "     ON d.id = dv.documento_id WHERE d.source_id = f.source_id) AS versiones, "
                "  (SELECT count(*) FROM unidades_documentales ud JOIN documento_versiones dv "
                "     ON dv.id = ud.doc_version_id JOIN documentos d ON d.id = dv.documento_id "
                "    WHERE d.source_id = f.source_id) AS unidades, "
                # Un directorio no produce unidades documentales: produce
                # puntos de atención. Sin esta cuenta el reporte dice que una
                # fuente cargada no dio nada.
                "  (SELECT count(DISTINCT c.punto_id) FROM canales c "
                "     JOIN evidencias e ON e.id = c.evidencia_id "
                "     JOIN documento_versiones dv ON dv.id = e.doc_version_id "
                "     JOIN documentos d ON d.id = dv.documento_id "
                "    WHERE d.source_id = f.source_id AND c.punto_id IS NOT NULL) AS puntos, "
                "  (SELECT count(DISTINCT nv.norma_id) FROM norma_versiones nv "
                "     JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                "     JOIN documentos d ON d.id = dv.documento_id "
                "    WHERE d.source_id = f.source_id) AS normas, "
                "  (SELECT count(*) FROM evaluaciones_completitud ec "
                "     JOIN norma_versiones nv ON nv.registro_version_id = ec.norma_version_id "
                "     JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                "     JOIN documentos d ON d.id = dv.documento_id "
                "    WHERE d.source_id = f.source_id) AS campos, "
                "  (SELECT count(*) FROM registro_versiones rv "
                "     JOIN norma_versiones nv ON nv.registro_version_id = rv.id "
                "     JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                "     JOIN documentos d ON d.id = dv.documento_id "
                "    WHERE d.source_id = f.source_id AND rv.release_id IS NOT NULL) "
                "    AS publicadas, "
                "  (SELECT count(*) FROM incidencias_revision i "
                "     WHERE i.source_id = f.source_id AND i.estado = 'ABIERTA') AS incidencias "
                "  FROM fuentes f"
            )
        )
        .mappings()
        .all()
    )
    return {fila["source_id"]: dict(fila) for fila in filas}


def _historia_de_fuente(historia: dict, metricas: dict) -> HistoriaDeFuente:
    source_id = historia["source_id"]
    if not metricas:
        return HistoriaDeFuente(
            id=historia["id"],
            titulo=historia["title"],
            source_id=source_id,
            capacidad=historia["owner_capability"],
            prioridad=historia["priority"],
            estado="NO_INICIADA",
            detencion="La fuente no está en el catálogo cargado.",
        )

    alias = metricas["alias_of"]
    acceso = metricas["access_status"]
    # `NO_VERIFICADO` no es un bloqueo: es una fuente que todavía no se recorrió.
    # Contarla como bloqueada inflaría los impedimentos y escondería el trabajo
    # que falta detrás de un obstáculo que nadie encontró.
    bloqueada = acceso in ACCESOS_IMPEDIDOS or metricas["urls"] == 0

    if alias:
        estado = "ALIAS_REGISTRADO"
        detencion = (
            f"Alias de {alias}: el contenido canónico vive allí y no se duplica. "
            "La identidad se conserva igual."
        )
    elif metricas["publicadas"]:
        estado = "CERRADA"
        detencion = None
    elif metricas["capturas"]:
        estado = "EN_CURSO"
        detencion = None
    elif bloqueada:
        estado = "BLOQUEADA"
        detencion = _motivo_de_detencion(metricas)
    elif metricas["estado"] in ESTADOS_SIN_INGESTA:
        # Antes de preguntar si se recorrió, preguntar si había que recorrerla.
        estado = NO_SE_INGESTA
        detencion = f"Sin capturas y {ESTADOS_SIN_INGESTA[metricas['estado']]}: no se captura."
    elif metricas["estado"] == ESTADO_MANUAL:
        estado = ESPERA_CARGA_MANUAL
        detencion = (
            "Sin capturas y declarada de carga manual: espera una carga trazada, no un recorrido."
        )
    else:
        estado = "NO_INICIADA"
        detencion = "Sin capturas: la fuente está en el catálogo y todavía no se recorrió."

    return HistoriaDeFuente(
        id=historia["id"],
        titulo=historia["title"],
        source_id=source_id,
        capacidad=historia["owner_capability"],
        prioridad=historia["priority"],
        estado=estado,
        access_status=acceso,
        alias_de=alias,
        urls=metricas["urls"],
        capturas=metricas["capturas"],
        documentos=metricas["documentos"],
        versiones=metricas["versiones"],
        unidades=metricas["unidades"],
        puntos=metricas["puntos"],
        normas=metricas["normas"],
        campos_evaluados=metricas["campos"],
        versiones_publicadas=metricas["publicadas"],
        incidencias_abiertas=metricas["incidencias"],
        detencion=detencion,
    )


def _motivo_de_detencion(metricas: dict) -> str:
    partes = [
        p
        for p in (
            metricas.get("motivo_estado"),
            metricas.get("exclusion_reason"),
            None if metricas["urls"] else "Sin URL inequívoca conocida.",
        )
        if p
    ]
    responsable = metricas.get("responsable_rol")
    texto = " ".join(partes) or f"Acceso {metricas['access_status']}."
    return f"{texto} Responsable: {responsable or 'sin asignar'}."


def formatear(reporte: ReporteBacklog) -> str:
    transversales = reporte.conteo(reporte.transversales)
    fuentes = reporte.conteo(reporte.fuentes)
    lineas = [
        "# Estado del backlog",
        "",
        f"Historias del paquete: **{reporte.total}** "
        f"({len(reporte.transversales)} transversales + {len(reporte.fuentes)} por fuente).",
        "",
        "Las transversales se verifican contra el código y las pruebas que las implementan;",
        "las de fuente, contra las filas que dejaron en la base. `bn calidad backlog` falla",
        "si una historia declara evidencia en una ruta que ya no existe.",
        "",
        "| Estado | Transversales | Por fuente |",
        "| --- | --- | --- |",
    ]
    for estado in ESTADOS:
        lineas.append(f"| {estado} | {transversales.get(estado, 0)} | {fuentes.get(estado, 0)} |")

    lineas += [
        "",
        "## Historias transversales",
        "",
        "| HU | Título | Capacidad | Prioridad | Estado | Evidencia |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for h in reporte.transversales:
        evidencia = "<br>".join(f"`{r}`" for r in h.evidencia)
        if h.comandos:
            evidencia += "<br>" + "<br>".join(f"`{c}`" for c in h.comandos)
        if h.falta:
            evidencia += f"<br>_Falta: {h.falta}_"
        if h.bloqueador:
            evidencia += f"<br>**Bloqueador:** {h.bloqueador}"
        if h.responsable_rol:
            evidencia += f"<br>**Quién lo desbloquea:** {h.responsable_rol}"
        if h.desbloquea_con:
            evidencia += f"<br>**Con qué se desbloquea:** {h.desbloquea_con}"
        lineas.append(
            f"| {h.id} | {h.titulo} | {h.capacidad} | {h.prioridad} | {h.estado} | {evidencia} |"
        )

    lineas += [
        "",
        "## Historias por fuente",
        "",
        "Los números salen de la base, no de una declaración.",
        "",
        "| HU | Fuente | Estado | URLs | Capturas | Versiones | Unidades | Puntos "
        "| Normas | Campos | Publicadas | Detención |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for h in reporte.fuentes:
        lineas.append(
            f"| {h.id} | {h.source_id} | {h.estado} | {h.urls} | {h.capturas} | {h.versiones} "
            f"| {h.unidades} | {h.puntos} | {h.normas} | {h.campos_evaluados} "
            f"| {h.versiones_publicadas} "
            f"| {h.detencion or '—'} |"
        )

    lineas += [
        "",
        "## Cómo leer los estados",
        "",
        "- **CERRADA**: la fuente tiene al menos una versión en un release publicado.",
        "- **EN_CURSO**: hay capturas y contenido extraído, pero nada llegó a publicarse.",
        "- **ALIAS_REGISTRADO**: la fuente es un alias; su contenido canónico vive en otra y",
        "  duplicarlo sería contar dos veces la misma norma.",
        "- **BLOQUEADA**: hay un impedimento concreto —acceso restringido o URL inequívoca",
        "  desconocida— con su motivo y su responsable. No es un pendiente de programación.",
        "- **NO_INICIADA**: la fuente está en el catálogo y todavía no se recorrió.",
        "- **ESPERA_CARGA_MANUAL**: el catálogo la declara de carga manual. Lo que "
        "falta es una carga trazada, no un recorrido.",
        "- **NO_SE_INGESTA**: el catálogo la declara retirada o solo de referencia. "
        "No es un pendiente: es una decisión registrada.",
        "",
        "Una fuente importada como metadatos —F01, el catálogo nacional— figura con sus",
        "capturas y sin versiones de documento: no tiene textos segmentados porque no se",
        "descargaron sus 428.380 textos. Sus números están en",
        "`docs/operacion/poblacion_real.md`.",
    ]
    return "\n".join(lineas)
