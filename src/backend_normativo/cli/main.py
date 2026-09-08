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
app.add_typer(calidad, name="calidad")


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


if __name__ == "__main__":
    app()
