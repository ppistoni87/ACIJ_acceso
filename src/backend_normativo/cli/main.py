"""Interfaz de línea de comandos del backend normativo."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.catalogo.manifiesto import cargar_manifiesto
from backend_normativo.catalogo.reconciliacion import construir_reporte, formatear
from backend_normativo.db.session import engine_migrador

app = typer.Typer(help="Backend normativo de acceso a derechos.", no_args_is_help=True)
catalogo = typer.Typer(help="Catálogo de fuentes.", no_args_is_help=True)
ingesta = typer.Typer(help="Captura de fuentes.", no_args_is_help=True)
app.add_typer(catalogo, name="catalogo")
curacion = typer.Typer(help="Curación jurídica.", no_args_is_help=True)
app.add_typer(ingesta, name="ingesta")
calidad = typer.Typer(help="Calidad y cobertura.", no_args_is_help=True)
app.add_typer(curacion, name="curacion")
revision = typer.Typer(help="Revisión de dominio.", no_args_is_help=True)
publicacion = typer.Typer(help="Publicación de releases.", no_args_is_help=True)
app.add_typer(calidad, name="calidad")
app.add_typer(revision, name="revision")
api = typer.Typer(help="API de consulta.", no_args_is_help=True)
app.add_typer(publicacion, name="publicacion")
monitoreo = typer.Typer(help="Monitoreo y eventos.", no_args_is_help=True)
app.add_typer(api, name="api")
app.add_typer(monitoreo, name="monitoreo")


@catalogo.command("validar")
def catalogo_validar(
    manifiesto: Path | None = typer.Option(None, help="Ruta al manifiesto de fuentes."),
) -> None:
    """Verifica la coherencia interna del manifiesto sin tocar la base."""
    m = cargar_manifiesto(manifiesto)
    problemas = m.validar_coherencia()
    typer.echo(f"Fuentes declaradas: {m.source_count} · leídas: {len(m.sources)}")
    if problemas:
        for p in problemas:
            typer.echo(f"  - {p}")
        raise typer.Exit(code=1)
    typer.echo("Sin contradicciones internas.")


@catalogo.command("cargar")
def catalogo_cargar(
    manifiesto: Path | None = typer.Option(None, help="Ruta al manifiesto de fuentes."),
) -> None:
    """Carga o actualiza el catálogo. Reejecutarla no duplica filas."""
    m = cargar_manifiesto(manifiesto)
    with engine_migrador().begin() as conexion:
        resultado = cargar_catalogo(conexion, m)
    typer.echo(
        f"Jurisdicciones nuevas: {resultado.jurisdicciones_creadas}\n"
        f"Fuentes creadas: {resultado.fuentes_creadas} · "
        f"actualizadas: {resultado.fuentes_actualizadas}\n"
        f"URLs nuevas: {resultado.urls_creadas}\n"
        f"Configuraciones nuevas: {resultado.configuraciones_creadas}\n"
        f"Brechas registradas como incidencia: {resultado.incidencias_creadas}"
    )
    for advertencia in resultado.advertencias:
        typer.echo(f"  advertencia: {advertencia}")


@catalogo.command("conciliar")
def catalogo_conciliar(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
    formato: str = typer.Option("markdown", help="markdown o json."),
) -> None:
    """Emite el reporte de conciliación del inventario."""
    with engine_migrador().connect() as conexion:
        reporte = construir_reporte(conexion)
    texto = (
        json.dumps(reporte.a_dict(), ensure_ascii=False, indent=2)
        if formato == "json"
        else formatear(reporte)
    )
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Reporte escrito en {salida}")
    else:
        typer.echo(texto)


@ingesta.command("capturar")
def ingesta_capturar(
    fuentes: list[str] = typer.Argument(..., help="Identificadores de fuente (F01, D03, ...)."),
) -> None:
    """Corre una captura por fuente y deja los bytes originales en el almacén."""
    from backend_normativo.ingesta.capturador import Capturador, PermisoDePoliticaDenegado
    from backend_normativo.ingesta.cliente import ClienteCaptura

    with ClienteCaptura() as cliente:
        for source_id in fuentes:
            with engine_migrador().begin() as conexion:
                capturador = Capturador(conexion, cliente=cliente)
                try:
                    resultado = capturador.capturar_fuente(source_id)
                except (PermisoDePoliticaDenegado, LookupError) as exc:
                    typer.echo(f"{source_id}: {exc}")
                    continue
            typer.echo(
                f"{source_id}: {resultado.estado.value} · "
                f"solicitadas {resultado.solicitadas} · descargadas {resultado.descargadas} · "
                f"sin cambios {resultado.no_modificadas} · rechazadas {resultado.rechazadas}"
            )
            for incidencia in resultado.incidencias:
                typer.echo(f"    incidencia: {incidencia}")


@ingesta.command("importar-infoleg")
def ingesta_importar_infoleg(
    captura: str = typer.Argument(..., help="Id de la captura del dataset F01."),
    limite: int | None = typer.Option(None, help="Importar solo las primeras N filas."),
) -> None:
    """Importa el catálogo nacional de InfoLEG como metadatos.

    Trabaja sobre bytes ya capturados, nunca sobre la red: la captura entra por
    `bn ingesta capturar F01` y esto la lee del almacén por su SHA-256.
    """
    import uuid as _uuid

    from backend_normativo.ingesta.importadores.infoleg import (
        FormaInesperada,
        ImportadorInfoleg,
    )

    with engine_migrador().begin() as conexion:
        try:
            resultado = ImportadorInfoleg(conexion).importar_desde_captura(
                _uuid.UUID(captura), limite=limite
            )
        except FormaInesperada as exc:
            raise typer.Exit(1) from exc
    typer.echo(
        f"Filas leídas: {resultado.filas_leidas}\n"
        f"Normas creadas: {resultado.normas_creadas} · "
        f"ya presentes: {resultado.normas_existentes}\n"
        f"Sin número (S/N): {resultado.sin_numero}\n"
        f"Identidad incierta: {resultado.sin_clave_canonica} por tipo con numeración por "
        f"organismo · {resultado.homonimas} por clave repetida\n"
        f"Normas conjuntas (una fila por firmante): {resultado.coemitidas} fila(s) "
        f"plegadas en su norma\n"
        f"Metadata-only (sin URL de texto): {resultado.sin_texto}\n"
        f"Con texto actualizado: {resultado.con_texto_actualizado}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@ingesta.command("extraer")
def ingesta_extraer(
    fuente: str | None = typer.Option(None, help="Limitar a una fuente."),
) -> None:
    """Extrae documentos y unidades de las capturas todavía sin procesar."""
    from backend_normativo.ingesta.extraccion import Extractor

    with engine_migrador().begin() as conexion:
        resultado = Extractor(conexion).extraer_pendientes(fuente)
    typer.echo(
        f"Documentos nuevos: {resultado.documentos_creados}\n"
        f"Versiones nuevas: {resultado.versiones_creadas} · "
        f"sin cambios: {resultado.versiones_repetidas}\n"
        f"Unidades: {resultado.unidades_creadas}\n"
        f"URLs candidatas: {resultado.candidatas_creadas}\n"
        f"Incidencias: {resultado.incidencias_creadas}"
    )
    for aviso in resultado.avisos[:20]:
        typer.echo(f"  aviso: {aviso}")


@ingesta.command("descubrir")
def ingesta_descubrir(
    fuente: str = typer.Argument(..., help="Fuente cuyas candidatas se promueven."),
    limite: int = typer.Option(20, help="Máximo de candidatas a promover."),
) -> None:
    """Promueve URLs candidatas de una fuente a URLs de esa misma fuente.

    Solo promueve las que son vistas de la propia fuente (por ejemplo, el texto
    de una norma cuya ficha ya está en el catálogo). Las demás quedan como
    candidatas para que alguien decida si entran al alcance.
    """
    from sqlalchemy import text as sql

    with engine_migrador().begin() as conexion:
        promovidas = (
            conexion.execute(
                sql(
                    "WITH elegibles AS ("
                    "  SELECT c.id, c.url FROM fuentes_candidatas c "
                    "   WHERE c.source_id_origen = :s AND c.estado = 'NUEVA' "
                    "     AND c.relacion LIKE '%de la misma norma%' "
                    "   ORDER BY c.descubierta_en LIMIT :lim"
                    "), insertadas AS ("
                    "  INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                    "  SELECT :s, e.url, 'DETALLE', 'HTTP_GET_PUBLICO' FROM elegibles e "
                    "  ON CONFLICT (source_id, url) DO NOTHING RETURNING url"
                    ") UPDATE fuentes_candidatas SET estado = 'PROMOVIDA' "
                    "  WHERE id IN (SELECT id FROM elegibles) RETURNING url"
                ),
                {"s": fuente, "lim": limite},
            )
            .scalars()
            .all()
        )
    typer.echo(f"{fuente}: {len(promovidas)} URLs promovidas")
    for url in promovidas:
        typer.echo(f"  {url}")


@curacion.command("identidad")
def curacion_identidad(
    fuente: str | None = typer.Option(None, help="Limitar a una fuente."),
) -> None:
    """Resuelve la identidad de las normas extraídas y crea sus versiones."""
    from backend_normativo.curacion.identidad import ResolutorIdentidad

    with engine_migrador().begin() as conexion:
        resultado = ResolutorIdentidad(conexion).resolver_pendientes(fuente)
    typer.echo(
        f"Normas creadas: {resultado.normas_creadas} · "
        f"vinculadas a una existente: {resultado.normas_vinculadas}\n"
        f"Identificadores oficiales nuevos: {resultado.identificadores_creados}\n"
        f"Versiones normativas creadas: {resultado.versiones_creadas}\n"
        f"En identidad incierta: {resultado.inciertas}\n"
        f"Incidencias abiertas: {resultado.incidencias_creadas}"
    )
    for aviso in resultado.avisos[:20]:
        typer.echo(f"  aviso: {aviso}")


@curacion.command("relaciones")
def curacion_relaciones(
    fuente: str | None = typer.Option(None, help="Limitar a una fuente."),
) -> None:
    """Construye relaciones normativas candidatas y registra las pendientes."""
    from backend_normativo.curacion.relaciones import ConstructorRelaciones

    with engine_migrador().begin() as conexion:
        resultado = ConstructorRelaciones(conexion).construir(fuente)
    typer.echo(
        f"Unidades analizadas: {resultado.unidades_analizadas}\n"
        f"Citas detectadas: {resultado.citas_detectadas}\n"
        f"Relaciones candidatas nuevas: {resultado.relaciones_creadas} · "
        f"ya registradas: {resultado.relaciones_existentes}\n"
        f"Referencias pendientes de resolver: {resultado.pendientes_creadas}\n"
        f"Autorreferencias omitidas: {resultado.autorreferencias_omitidas}"
    )


@curacion.command("campos")
def curacion_campos(
    fuente: str | None = typer.Option(None, help="Limitar a una fuente."),
) -> None:
    """Evalúa los siete campos pedidos y propone candidatos con evidencia."""
    from backend_normativo.curacion.campos import EvaluadorDeCampos

    with engine_migrador().begin() as conexion:
        resultado = EvaluadorDeCampos(conexion).evaluar(fuente)
    typer.echo(
        f"Versiones evaluadas: {resultado.versiones_evaluadas}\n"
        f"Filas de evaluación: {resultado.evaluaciones_creadas}\n"
        f"Afirmaciones candidatas: {resultado.afirmaciones_creadas}"
    )
    for estado, cantidad in sorted(resultado.por_estado.items()):
        typer.echo(f"  {estado}: {cantidad}")


@calidad.command("cobertura")
def calidad_cobertura(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
    formato: str = typer.Option("markdown", help="markdown o json."),
) -> None:
    """Mide cobertura y calidad, con las métricas separadas."""
    from backend_normativo.calidad.cobertura import formatear as formatear_cobertura
    from backend_normativo.calidad.cobertura import medir

    with engine_migrador().connect() as conexion:
        metricas = medir(conexion)
    texto = (
        json.dumps(metricas.a_dict(), ensure_ascii=False, indent=2)
        if formato == "json"
        else formatear_cobertura(metricas)
    )
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Reporte escrito en {salida}")
    else:
        typer.echo(texto)


@calidad.command("trazabilidad")
def calidad_trazabilidad(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
    formato: str = typer.Option("markdown", help="markdown o json."),
    ejecutar: bool = typer.Option(
        False, help="Correr las pruebas citadas además de verificar que existan."
    ),
) -> None:
    """Traza los 80 casos de aceptación contra las pruebas que los ejercen."""
    from dataclasses import asdict

    from backend_normativo.calidad.trazabilidad import MapaInconsistente, construir
    from backend_normativo.calidad.trazabilidad import formatear as formatear_trazabilidad

    try:
        reporte = construir(ejecutar=ejecutar)
    except MapaInconsistente as exc:
        typer.echo(str(exc))
        raise typer.Exit(1) from exc
    texto = (
        json.dumps(asdict(reporte), ensure_ascii=False, indent=2)
        if formato == "json"
        else formatear_trazabilidad(reporte)
    )
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(
            f"Reporte escrito en {salida} · cubiertos {reporte.cubiertos} · "
            f"parciales {reporte.parciales} · no ejecutados {reporte.no_ejecutados}"
        )
    else:
        typer.echo(texto)
    if reporte.fallidas:
        raise typer.Exit(1)


@calidad.command("backlog")
def calidad_backlog(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
    formato: str = typer.Option("markdown", help="markdown o json."),
) -> None:
    """Estado de las 123 historias, con la evidencia de cierre de cada una."""
    from dataclasses import asdict

    from backend_normativo.calidad.backlog import EvidenciaInexistente, construir
    from backend_normativo.calidad.backlog import formatear as formatear_backlog

    with engine_migrador().connect() as conexion:
        try:
            reporte = construir(conexion)
        except EvidenciaInexistente as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    texto = (
        json.dumps(asdict(reporte), ensure_ascii=False, indent=2)
        if formato == "json"
        else formatear_backlog(reporte)
    )
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        cerradas = sum(1 for h in reporte.fuentes if h.estado == "CERRADA")
        typer.echo(
            f"Reporte escrito en {salida} · fuentes cerradas {cerradas}/{len(reporte.fuentes)}"
        )
    else:
        typer.echo(texto)


@calidad.command("diccionario")
def calidad_diccionario(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el diccionario."),
) -> None:
    """Diccionario de datos generado desde los modelos, no escrito a mano."""
    from backend_normativo.db.diccionario import construir
    from backend_normativo.db.diccionario import formatear as formatear_diccionario

    texto = formatear_diccionario(construir())
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Diccionario escrito en {salida}")
    else:
        typer.echo(texto)


@calidad.command("ensayo-actualizacion")
def calidad_ensayo_actualizacion(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir la evidencia."),
    base: str = typer.Option(
        "backend_normativo_ensayo", help="Base descartable donde correr el ensayo."
    ),
) -> None:
    """Ejercita diff, impacto y evento sobre una actualización controlada.

    Crea la base desde cero, la migra, corre el ensayo y la deja. Nunca toca la
    base de producción: los datos del ensayo no se mezclan con el corpus.
    """
    import os

    from sqlalchemy import create_engine
    from sqlalchemy import text as sql

    from backend_normativo.calidad.ensayo import correr
    from backend_normativo.calidad.ensayo import formatear as formatear_ensayo
    from backend_normativo.config import get_settings

    url_actual = str(get_settings().database_url)
    url_ensayo = url_actual.rsplit("/", 1)[0] + "/" + base

    admin = create_engine(url_actual.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conexion:
        conexion.execute(sql(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)'))
        conexion.execute(sql(f'CREATE DATABASE "{base}"'))
    admin.dispose()

    previo = os.environ.get("BN_DATABASE_URL")
    os.environ["BN_DATABASE_URL"] = url_ensayo
    get_settings.cache_clear()
    try:
        from alembic import command
        from alembic.config import Config

        command.upgrade(Config("alembic.ini"), "head")
        motor = create_engine(url_ensayo, future=True)
        with motor.begin() as conexion:
            resultado = correr(conexion)
        motor.dispose()
    finally:
        if previo is None:
            os.environ.pop("BN_DATABASE_URL", None)
        else:
            os.environ["BN_DATABASE_URL"] = previo
        get_settings.cache_clear()

    texto = formatear_ensayo(resultado)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(
            f"Evidencia escrita en {salida} · cambios {resultado.resumen} · "
            f"eventos {resultado.eventos_tras_repetir}"
        )
    else:
        typer.echo(texto)


@curacion.command("vigencia")
def curacion_vigencia(
    fuente: str | None = typer.Option(None, help="Limitar a una fuente."),
) -> None:
    """Resuelve la vigencia por política versionada y deriva el resto a revisión."""
    from backend_normativo.curacion.vigencia import ResolutorVigencia
    from backend_normativo.politicas import vigencia as politica

    with engine_migrador().begin() as conexion:
        resultado = ResolutorVigencia(conexion).resolver(source_id=fuente)
    typer.echo(
        f"Política aplicada: {politica.VERSION}\n"
        f"Versiones consideradas: {resultado.versiones}\n"
        f"Resueltas por política: {resultado.resueltas_por_politica}\n"
        f"Derivadas a revisión de dominio: {resultado.derivadas_a_revision}\n"
        f"Incidencias abiertas: {resultado.incidencias_creadas}"
    )


@revision.command("pendientes")
def revision_pendientes(
    tipo: str | None = typer.Option(None, help="Filtrar por tipo de incidencia."),
    limite: int = typer.Option(20, help="Máximo de incidencias a listar."),
) -> None:
    """Lista las incidencias abiertas que esperan decisión."""
    from sqlalchemy import text as sql

    with engine_migrador().connect() as conexion:
        filas = (
            conexion.execute(
                sql(
                    "SELECT i.id, i.tipo, i.severidad, i.source_id, "
                    "       coalesce(n.tipo || ' ' || n.numero || '/' || n.anio, '-') AS norma, "
                    "       left(i.descripcion, 110) AS descripcion "
                    "  FROM incidencias_revision i "
                    "  LEFT JOIN registro_versiones rv ON rv.id = i.registro_version_id "
                    "  LEFT JOIN normas n ON n.id = rv.entidad_id "
                    " WHERE i.estado = 'ABIERTA' "
                    "   AND (CAST(:t AS text) IS NULL OR i.tipo = :t) "
                    " ORDER BY i.severidad, i.creado_en LIMIT :lim"
                ),
                {"t": tipo, "lim": limite},
            )
            .mappings()
            .all()
        )
    if not filas:
        typer.echo("No hay incidencias abiertas con ese filtro.")
        return
    for fila in filas:
        typer.echo(
            f"{fila['id']}  [{fila['severidad']}] {fila['tipo']}  "
            f"{fila['source_id'] or '-'}  {fila['norma']}\n    {fila['descripcion']}"
        )


@revision.command("resolver-vigencia")
def revision_resolver_vigencia(
    incidencia: str = typer.Argument(..., help="Identificador de la incidencia."),
    actor: str = typer.Option(..., help="Quién decide. Queda en la bitácora."),
    decision: str = typer.Option(..., help="Qué se decidió y con qué fundamento."),
    valid_tipo: str = typer.Option(..., help="CERRADO, ABIERTO_FIN, PUNTUAL, ..."),
    desde: str | None = typer.Option(None, help="Fecha de inicio (AAAA-MM-DD)."),
    hasta: str | None = typer.Option(None, help="Fecha de fin (AAAA-MM-DD)."),
    estado_legal: str = typer.Option("VIGENTE", help="Estado legal validado."),
    evidencia: str | None = typer.Option(
        None, help="Evidencia que fundamenta el estado. Si se omite, se usa la de la ficha."
    ),
) -> None:
    """Registra una decisión de vigencia con su actor y su fundamento."""
    import uuid as _uuid

    from sqlalchemy import text as sql

    from backend_normativo.curacion.revision import Revisor

    with engine_migrador().begin() as conexion:
        evidencia_id = _uuid.UUID(evidencia) if evidencia else None
        if evidencia_id is None:
            evidencia_id = conexion.execute(
                sql(
                    "SELECT e.id FROM evidencias e "
                    "  JOIN documento_versiones dv ON dv.id = e.doc_version_id "
                    "  JOIN norma_versiones nv ON nv.doc_version_id = dv.id "
                    "  JOIN incidencias_revision i "
                    "    ON i.registro_version_id = nv.registro_version_id "
                    " WHERE i.id = :i ORDER BY e.creado_en LIMIT 1"
                ),
                {"i": incidencia},
            ).scalar_one_or_none()
        resultado = Revisor(conexion).resolver(
            _uuid.UUID(incidencia),
            decision=decision,
            actor=actor,
            fundamento_evidencia_id=evidencia_id,
            vigencia={
                "valid_tipo": valid_tipo,
                "valid_desde": desde,
                "valid_hasta": hasta,
                "estado_legal": estado_legal,
            },
        )
    typer.echo(
        f"Incidencia {resultado.incidencia_id} resuelta por {actor}. "
        f"Vigencia aplicada: {resultado.aplico_vigencia}"
    )


@revision.command("aprobar-campos")
def revision_aprobar_campos(
    version: str = typer.Argument(..., help="Identificador de la versión."),
    actor: str = typer.Option(..., help="Quién aprueba."),
    campos: list[str] = typer.Option(None, help="Campos a aprobar. Por omisión, todos."),
) -> None:
    """Aprueba las afirmaciones candidatas de una versión."""
    import uuid as _uuid

    from backend_normativo.curacion.campos import EvaluadorDeCampos
    from backend_normativo.curacion.revision import Revisor
    from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS

    objetivo = list(campos) if campos else list(CAMPOS_SOLICITADOS)
    with engine_migrador().begin() as conexion:
        revisor = Revisor(conexion)
        total = sum(
            revisor.aprobar_afirmaciones(_uuid.UUID(version), campo, actor=actor)
            for campo in objetivo
        )
        EvaluadorDeCampos(conexion).evaluar()
    typer.echo(f"{total} afirmación(es) aprobadas por {actor}.")


@publicacion.command("estado")
def publicacion_estado() -> None:
    """Muestra qué se puede publicar y qué queda en cuarentena, con motivos."""
    from backend_normativo.publicacion.gates import evaluar_gates
    from backend_normativo.publicacion.release import Publicador

    with engine_migrador().connect() as conexion:
        publicador = Publicador(conexion)
        candidatos = publicador.candidatos()
        gates = evaluar_gates(conexion, candidatos)
        cuarentena = publicador.cuarentena()
    typer.echo(f"Candidatos a publicar: {len(candidatos)}")
    for gate in gates.gates:
        marca = "ok " if gate.pasa else "FALLA"
        typer.echo(f"  [{marca}] {gate.id}: {gate.descripcion} · {gate.observado}")
    typer.echo(f"En cuarentena: {len(cuarentena)}")
    for fila in cuarentena[:15]:
        typer.echo(
            f"  {fila['entidad_tipo']} {fila['registro_version_id']}: {', '.join(fila['motivos'])}"
        )


@publicacion.command("publicar")
def publicacion_publicar(
    actor: str = typer.Option(..., help="Quién aprueba la publicación."),
    motivo: str = typer.Option(..., help="Por qué se publica este corte."),
) -> None:
    """Publica un release con todo lo que está en condiciones."""
    from backend_normativo.publicacion.release import PublicacionRechazada, Publicador

    try:
        with engine_migrador().begin() as conexion:
            resultado = Publicador(conexion).publicar(actor=actor, motivo=motivo)
    except PublicacionRechazada as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"Release {resultado.release_id}\n"
        f"Versiones publicadas: {resultado.versiones_publicadas}\n"
        f"Fragmentos citables: {resultado.chunks_creados}\n"
        f"Eventos en outbox: {resultado.eventos_emitidos}\n"
        f"En cuarentena: {len(resultado.en_cuarentena)}"
    )


@api.command("servir")
def api_servir(
    host: str = typer.Option("127.0.0.1", help="Interfaz donde escuchar."),
    puerto: int = typer.Option(8000, help="Puerto."),
    recargar: bool = typer.Option(False, help="Recargar al cambiar el código."),
) -> None:
    """Levanta la API de consulta."""
    import uvicorn

    uvicorn.run("backend_normativo.api.app:app", host=host, port=puerto, reload=recargar)


@api.command("openapi")
def api_openapi(
    salida: Path = typer.Option(
        Path("docs/openapi.json"), help="Archivo donde escribir el contrato."
    ),
) -> None:
    """Escribe el contrato OpenAPI a un archivo versionable."""
    from backend_normativo.api.app import crear_app

    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"Contrato escrito en {salida}")


@monitoreo.command("correr")
def monitoreo_correr(
    limite: int | None = typer.Option(None, help="Máximo de fuentes a revisar."),
) -> None:
    """Revalida las fuentes vencidas, compara textos y propaga el impacto."""
    from backend_normativo.ingesta.capturador import Capturador
    from backend_normativo.ingesta.cliente import ClienteCaptura
    from backend_normativo.ingesta.extraccion import Extractor
    from backend_normativo.monitoreo.novedades import correr

    with ClienteCaptura() as cliente, engine_migrador().begin() as conexion:
        resultado = correr(
            conexion,
            capturador=Capturador(conexion, cliente=cliente),
            extractor=Extractor(conexion),
            limite=limite,
        )
    typer.echo(
        f"Fuentes revisadas: {resultado.fuentes_revisadas}\n"
        f"Con cambios: {resultado.con_cambios} · sin cambios: {resultado.sin_cambios} · "
        f"bloqueadas: {resultado.bloqueadas}\n"
        f"Versiones nuevas: {resultado.versiones_nuevas}\n"
        f"Normas impactadas: {resultado.normas_impactadas}\n"
        f"Eventos emitidos: {resultado.eventos_emitidos}"
    )
    for fuente in resultado.detalle:
        typer.echo(f"  {fuente['source_id']}:")
        for cambio in fuente["cambios"]:
            typer.echo(f"    {cambio['resumen']}")
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@monitoreo.command("entregar")
def monitoreo_entregar(
    limite: int = typer.Option(50, help="Máximo de eventos a entregar."),
) -> None:
    """Entrega los eventos pendientes al consumidor configurado."""
    from backend_normativo.monitoreo.outbox import entregar_pendientes

    with engine_migrador().begin() as conexion:
        resultado = entregar_pendientes(conexion, limite=limite)
    typer.echo(
        f"Consumidor: {resultado.consumidor or 'sin configurar'}\n"
        f"Pendientes: {resultado.pendientes}\n"
        f"Entregados: {resultado.entregados} · fallidos: {resultado.fallidos}\n"
        f"En cola de fallos: {resultado.en_cola_de_fallos}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


if __name__ == "__main__":
    app()
