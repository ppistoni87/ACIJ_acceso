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
app.add_typer(ingesta, name="ingesta")


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


if __name__ == "__main__":
    app()
