"""Reporte de conciliación del inventario.

Los denominadores se informan por separado y con su nombre: 83 fuentes no son 83
leyes, y una fuente puede producir muchas normas, ninguna, o ser un alias. Una
cobertura que mezcle esas cantidades no dice nada.

El reporte se calcula sobre la base, no sobre el manifiesto: es lo que hay
cargado, no lo que se esperaba cargar.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlalchemy import Connection, text


@dataclass
class Denominadores:
    """Cantidades que no son sinónimos entre sí."""

    fuentes: int = 0
    fuentes_canonicas: int = 0
    alias: int = 0
    urls_registradas: int = 0
    documentos: int = 0
    normas: int = 0
    beneficios: int = 0
    dependencias_pendientes: int = 0


@dataclass
class ReporteConciliacion:
    denominadores: Denominadores = field(default_factory=Denominadores)
    fuentes_por_estado: dict[str, int] = field(default_factory=dict)
    fuentes_por_acceso: dict[str, int] = field(default_factory=dict)
    fuentes_por_prioridad: dict[str, int] = field(default_factory=dict)
    fuentes_por_clase: dict[str, int] = field(default_factory=dict)
    fuentes_por_adaptador: dict[str, int] = field(default_factory=dict)
    alias_resueltos: list[dict[str, str]] = field(default_factory=list)
    brechas_sin_url: list[dict[str, str]] = field(default_factory=list)
    ids_originales_presentes: int = 0
    ids_incorporados: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def _conteo(conexion: Connection, sql: str) -> dict[str, int]:
    return {fila[0]: fila[1] for fila in conexion.execute(text(sql))}


def construir_reporte(conexion: Connection) -> ReporteConciliacion:
    reporte = ReporteConciliacion()
    d = reporte.denominadores

    d.fuentes = conexion.execute(text("SELECT count(*) FROM fuentes")).scalar_one()
    d.alias = conexion.execute(
        text("SELECT count(*) FROM fuentes WHERE alias_of IS NOT NULL")
    ).scalar_one()
    d.fuentes_canonicas = d.fuentes - d.alias
    d.urls_registradas = conexion.execute(text("SELECT count(*) FROM fuente_urls")).scalar_one()
    d.documentos = conexion.execute(text("SELECT count(*) FROM documentos")).scalar_one()
    d.normas = conexion.execute(text("SELECT count(*) FROM normas")).scalar_one()
    d.beneficios = conexion.execute(text("SELECT count(*) FROM beneficios")).scalar_one()
    d.dependencias_pendientes = conexion.execute(
        text("SELECT count(*) FROM referencias_pendientes WHERE estado = 'PENDIENTE'")
    ).scalar_one()

    reporte.fuentes_por_estado = _conteo(
        conexion, "SELECT estado, count(*) FROM fuentes GROUP BY estado ORDER BY estado"
    )
    reporte.fuentes_por_acceso = _conteo(
        conexion,
        "SELECT access_status, count(*) FROM fuentes GROUP BY access_status ORDER BY access_status",
    )
    reporte.fuentes_por_prioridad = _conteo(
        conexion, "SELECT prioridad, count(*) FROM fuentes GROUP BY prioridad ORDER BY prioridad"
    )
    reporte.fuentes_por_clase = _conteo(
        conexion, "SELECT clase, count(*) FROM fuentes GROUP BY clase ORDER BY clase"
    )
    reporte.fuentes_por_adaptador = _conteo(
        conexion,
        "SELECT adaptador, count(*) FROM fuente_config_versiones "
        "GROUP BY adaptador ORDER BY adaptador",
    )

    reporte.alias_resueltos = [
        {"alias": fila[0], "canonica": fila[1], "nombre_canonica": fila[2]}
        for fila in conexion.execute(
            text(
                "SELECT a.source_id, c.source_id, c.nombre "
                "FROM fuentes a JOIN fuentes c ON c.source_id = a.alias_of "
                "ORDER BY a.source_id"
            )
        )
    ]

    reporte.brechas_sin_url = [
        {
            "source_id": fila[0],
            "nombre": fila[1],
            "prioridad": fila[2],
            "responsable_rol": fila[3] or "sin asignar",
            "incidencia": fila[4],
        }
        for fila in conexion.execute(
            text(
                "SELECT f.source_id, f.nombre, f.prioridad, f.responsable_rol, "
                "       coalesce(i.estado, 'SIN_INCIDENCIA') "
                "FROM fuentes f "
                "LEFT JOIN incidencias_revision i "
                "  ON i.source_id = f.source_id AND i.tipo = 'ACCESO_BLOQUEADO' "
                " AND i.estado <> 'RESUELTA' "
                "WHERE f.access_status = 'SIN_URL_CONOCIDA' "
                "ORDER BY f.source_id"
            )
        )
    ]

    ids = [fila[0] for fila in conexion.execute(text("SELECT source_id FROM fuentes ORDER BY 1"))]
    originales = {f"F{n:02d}" for n in range(1, 68)}
    reporte.ids_originales_presentes = len(originales & set(ids))
    reporte.ids_incorporados = sorted(set(ids) - originales)

    faltantes = sorted(originales - set(ids))
    if faltantes:
        reporte.advertencias.append(
            "Faltan identificadores originales del manual: " + ", ".join(faltantes)
        )
    if d.fuentes and not reporte.brechas_sin_url:
        reporte.advertencias.append(
            "No hay brechas de URL registradas: verificá que la carga las haya conservado."
        )
    huerfanos = conexion.execute(
        text(
            "SELECT count(*) FROM fuentes a "
            "WHERE a.alias_of IS NOT NULL "
            "  AND NOT EXISTS (SELECT 1 FROM fuentes c WHERE c.source_id = a.alias_of)"
        )
    ).scalar_one()
    if huerfanos:
        reporte.advertencias.append(f"{huerfanos} alias apuntan a una fuente inexistente")

    return reporte


def formatear(reporte: ReporteConciliacion) -> str:
    """Reporte legible para revisión humana."""
    d = reporte.denominadores
    lineas: list[str] = []
    a = lineas.append

    a("# Conciliación del inventario de fuentes")
    a("")
    a("## Denominadores")
    a("")
    a("Estas cantidades no son sinónimos: una fuente puede producir muchas normas,")
    a("ninguna, o ser un alias de otra.")
    a("")
    a("| Concepto | Cantidad |")
    a("|---|---:|")
    a(f"| Fuentes en el catálogo | {d.fuentes} |")
    a(f"| Fuentes canónicas (sin alias) | {d.fuentes_canonicas} |")
    a(f"| Alias | {d.alias} |")
    a(f"| URLs registradas | {d.urls_registradas} |")
    a(f"| Documentos capturados | {d.documentos} |")
    a(f"| Normas identificadas | {d.normas} |")
    a(f"| Beneficios registrados | {d.beneficios} |")
    a(f"| Dependencias normativas pendientes | {d.dependencias_pendientes} |")
    a("")
    a(f"Identificadores originales F01–F67 presentes: {reporte.ids_originales_presentes} de 67.")
    a(
        f"Incorporaciones al inventario: {len(reporte.ids_incorporados)} "
        f"({', '.join(reporte.ids_incorporados) or 'ninguna'})."
    )
    a("")

    for titulo, conteo in (
        ("Estado de la fuente", reporte.fuentes_por_estado),
        ("Disponibilidad observada", reporte.fuentes_por_acceso),
        ("Prioridad", reporte.fuentes_por_prioridad),
        ("Clase", reporte.fuentes_por_clase),
        ("Adaptador configurado", reporte.fuentes_por_adaptador),
    ):
        a(f"## {titulo}")
        a("")
        a("| Valor | Fuentes |")
        a("|---|---:|")
        for clave, valor in conteo.items():
            a(f"| {clave} | {valor} |")
        a("")

    a("## Alias resueltos")
    a("")
    a("Cada par conserva un solo contenido canónico y su alias; el alias no se")
    a("vuelve a abrir como una fuente nueva.")
    a("")
    a("| Alias | Canónica | Nombre de la canónica |")
    a("|---|---|---|")
    for fila in reporte.alias_resueltos:
        a(f"| {fila['alias']} | {fila['canonica']} | {fila['nombre_canonica']} |")
    a("")

    a("## Brechas de URL")
    a("")
    a("Estas fuentes no tienen dirección inequívoca en el manual. Se conservan en")
    a("el catálogo con su brecha abierta: no se inventa una URL ni se las quita")
    a("del denominador de cobertura.")
    a("")
    a("| Fuente | Prioridad | Responsable | Incidencia | Nombre |")
    a("|---|---|---|---|---|")
    for fila in reporte.brechas_sin_url:
        a(
            f"| {fila['source_id']} | {fila['prioridad']} | {fila['responsable_rol']} "
            f"| {fila['incidencia']} | {fila['nombre']} |"
        )
    a("")

    if reporte.advertencias:
        a("## Advertencias")
        a("")
        for advertencia in reporte.advertencias:
            a(f"- {advertencia}")
        a("")

    a("## Qué no dice este reporte")
    a("")
    a("Ninguna fuente figura como cargada: este reporte concilia el inventario, no")
    a("acredita ingesta. La cobertura sustantiva se mide sobre datos efectivamente")
    a("capturados y validados, y se informa por separado.")

    return "\n".join(lineas)
