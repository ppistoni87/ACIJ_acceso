"""Interfaz de línea de comandos del backend normativo."""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer
from sqlalchemy import text as sql_text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.catalogo.manifiesto import cargar_manifiesto
from backend_normativo.catalogo.reconciliacion import construir_reporte, formatear
from backend_normativo.db.session import engine_migrador

# El nombre de una base no se puede pasar como parámetro a `CREATE DATABASE`:
# va interpolado en la sentencia. Como estos comandos además hacen `DROP`, el
# nombre se valida antes de tocar el motor.
RE_NOMBRE_DE_BASE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _base_valida(base: str) -> str:
    if not RE_NOMBRE_DE_BASE.match(base):
        raise typer.BadParameter(
            f"«{base}» no es un nombre de base válido. Se admiten letras, dígitos y guion "
            "bajo, empezando por letra o guion bajo. El nombre se interpola en un "
            "CREATE/DROP DATABASE y no puede llevar comillas ni separadores."
        )
    return base


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
operacion = typer.Typer(help="Respaldo, restauración y operación.", no_args_is_help=True)
app.add_typer(operacion, name="operacion")
objetos = typer.Typer(help="Almacén de originales.", no_args_is_help=True)
app.add_typer(objetos, name="objetos")
plazos = typer.Typer(help="Calendarios y cómputo de plazos.", no_args_is_help=True)
app.add_typer(plazos, name="plazos")
recuperacion = typer.Typer(help="Índice semántico y búsqueda híbrida.", no_args_is_help=True)
app.add_typer(recuperacion, name="recuperacion")


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


@catalogo.command("anclas")
def catalogo_anclas(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
) -> None:
    """Comprueba que el fragmento de cada alias exista en su destino.

    Una página carga igual cuando el ancla no existe: el error no se ve hasta
    que alguien sigue la referencia y no llega a la pregunta que se citó.
    """
    from backend_normativo.catalogo.anclas import formatear as formatear_anclas
    from backend_normativo.catalogo.anclas import verificar

    with engine_migrador().begin() as conexion:
        reporte = verificar(conexion)
    texto = formatear_anclas(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(
            f"Reporte escrito en {salida} · resueltas {len(reporte.resueltas)} · "
            f"rotas {len(reporte.rotas)} · sin captura {len(reporte.sin_captura)}"
        )
    else:
        typer.echo(texto)


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
            # Confirmando URL por URL, y no al final de la fuente: si toda la
            # fuente fuera una transacción, un corte la revertiría entera y el
            # checkpoint se iría con ella, que es justo lo que no puede pasar.
            with engine_migrador().connect() as conexion:
                capturador = Capturador(conexion, cliente=cliente, confirmar=conexion.commit)
                try:
                    resultado = capturador.capturar_fuente(source_id)
                except (PermisoDePoliticaDenegado, LookupError) as exc:
                    conexion.rollback()
                    typer.echo(f"{source_id}: {exc}")
                    continue
                conexion.commit()
            reanudacion = f" · reanudadas {resultado.reanudadas}" if resultado.reanudada else ""
            typer.echo(
                f"{source_id}: {resultado.estado.value} · "
                f"solicitadas {resultado.solicitadas} · descargadas {resultado.descargadas} · "
                f"sin cambios {resultado.no_modificadas} · "
                f"rechazadas {resultado.rechazadas}{reanudacion}"
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


@ingesta.command("descubrir-renabap")
def ingesta_descubrir_renabap(
    captura: str = typer.Argument(..., help="Id de la captura de la página de F39."),
) -> None:
    """Registra la planilla del padrón como URL de F39, leyéndola de la página.

    El listado no viaja en el HTML: la página lo renderiza desde una planilla
    publicada cuyo identificador declara su propio script. Sin este paso, F39
    queda con la página capturada y sin padrón.
    """
    import uuid as _uuid

    from backend_normativo.ingesta.importadores.renabap import descubrir_planilla

    with engine_migrador().begin() as conexion:
        resultado = descubrir_planilla(conexion, _uuid.UUID(captura))
    if resultado.url is None:
        for aviso in resultado.avisos:
            typer.echo(f"  aviso: {aviso}")
        raise typer.Exit(1)
    typer.echo(
        f"Planilla de F39: {resultado.url}\n"
        f"Candidata registrada: {resultado.registrada} · "
        f"URL de la fuente creada: {resultado.promovida}"
    )


@ingesta.command("ampliar")
def ingesta_ampliar(
    limite: int = typer.Option(0, "--limite", help="Cuántas normas traer como máximo; 0, todas."),
    en_seco: bool = typer.Option(False, "--en-seco", help="Mostrar qué se traería, sin registrar."),
    detalle: bool = typer.Option(False, "--detalle", help="Listar también lo que se descarta."),
    informe_salida: str | None = typer.Option(
        None, "--informe", help="Escribir el informe de qué se trajo y qué se curó."
    ),
) -> None:
    """Registra el texto de las normas que el corpus cita y no tiene.

    Una referencia pendiente es una pregunta escrita: esta norma dice que
    depende de aquella y aquella no está. El catálogo nacional, que ya se
    importó, sabe la URL del texto consolidado de buena parte de ellas.

    Solo se amplía lo que resuelve a una y una sola norma con texto. Lo demás se
    informa con su motivo: elegir una de tres por orden de aparición sería
    inventar la cita que la referencia dejó abierta.
    """
    from backend_normativo.ingesta.ampliacion import SOURCE_ID, ampliar, candidatas, informe

    if informe_salida:
        with engine_migrador().connect() as conexion:
            Path(informe_salida).write_text(informe(conexion), encoding="utf-8")
        typer.echo(f"Informe escrito en {informe_salida}")
        return

    tope = limite or None
    with engine_migrador().begin() as conexion:
        resultado = candidatas(conexion, tope) if en_seco else ampliar(conexion, tope)

    for candidata in resultado.agregadas:
        typer.echo(
            f"{candidata.tipo} {candidata.numero}/{candidata.anio} "
            f"· la citan {candidata.citas} referencia(s) · {candidata.titulo[:50]}"
        )
    if resultado.ya_estaban:
        typer.echo(f"Ya registradas: {len(resultado.ya_estaban)}")
    if detalle:
        for descartada in resultado.descartadas:
            anio = descartada.anio or "sin año"
            typer.echo(
                f"  descartada: {descartada.tipo} {descartada.numero}/{anio} — {descartada.motivo}"
            )
    typer.echo(
        f"Normas nuevas en {SOURCE_ID}: {len(resultado.agregadas)} · "
        f"ya estaban: {len(resultado.ya_estaban)} · "
        f"no se pueden traer sin adivinar: {len(resultado.descartadas)}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@ingesta.command("importar-renabap")
def ingesta_importar_renabap(
    captura: str = typer.Argument(..., help="Id de la captura de la planilla de F39."),
) -> None:
    """Importa el padrón RENABAP como snapshot versionado.

    Cada importación crea una versión nueva del padrón en vez de actualizar
    filas: preguntar si un barrio figura solo tiene sentido contra un corte
    concreto.
    """
    import uuid as _uuid

    from backend_normativo.ingesta.importadores.renabap import (
        FormaInesperada,
        ImportadorRenabap,
    )

    with engine_migrador().begin() as conexion:
        try:
            resultado = ImportadorRenabap(conexion).importar_desde_captura(_uuid.UUID(captura))
        except FormaInesperada as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(
        f"Padrón: {resultado.padron_version}\n"
        f"Filas leídas: {resultado.filas_leidas}\n"
        f"Barrios nuevos: {resultado.barrios_nuevos} · "
        f"ya en este padrón: {resultado.barrios_conocidos}\n"
        f"Sin identificador RENABAP: {resultado.sin_id}\n"
        f"Sin cantidad de familias: {resultado.sin_familias}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@ingesta.command("importar-directorio")
def ingesta_importar_directorio(
    captura: str = typer.Argument(..., help="Id de la captura del dataset (F20 o F60)."),
) -> None:
    """Importa un directorio de atención con sus canales.

    Un literal de «sin dato» se guarda como ausencia y una coordenada sin CRS
    confirmado no se usa como latitud y longitud.
    """
    import uuid as _uuid

    from backend_normativo.ingesta.importadores.directorios import (
        FormaInesperada,
        ImportadorDirectorios,
    )

    with engine_migrador().begin() as conexion:
        try:
            resultado = ImportadorDirectorios(conexion).importar_desde_captura(_uuid.UUID(captura))
        except FormaInesperada as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(
        f"Fuente: {resultado.source_id}\n"
        f"Filas leídas: {resultado.filas_leidas}\n"
        f"Puntos nuevos: {resultado.puntos_creados} · "
        f"ya conocidos: {resultado.puntos_conocidos}\n"
        f"Canales: {resultado.canales_creados}\n"
        f"Literales de «sin dato» descartados: {resultado.literales_sin_dato}\n"
        f"Coordenadas usables: {resultado.coordenadas_usables} · "
        f"sin CRS confirmado: {resultado.coordenadas_sin_crs}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@ingesta.command("importar-dpn")
def ingesta_importar_dpn(
    captura: str = typer.Argument(..., help="Id de la captura de una sección de F44."),
) -> None:
    """Importa una sección del directorio de la Defensoría del Pueblo de la Nación.

    Las dos primeras secciones son oficinas de la DPN. La tercera lista
    defensorías provinciales y municipales, que son organismos autónomos: se
    cargan con su propio organismo titular y con la DPN como operadora del
    listado, no como oficinas suyas.
    """
    import uuid as _uuid

    from backend_normativo.ingesta.importadores.dpn import FormaInesperada, ImportadorDpn

    with engine_migrador().begin() as conexion:
        try:
            resultado = ImportadorDpn(conexion).importar_desde_captura(_uuid.UUID(captura))
        except FormaInesperada as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    titular = "la DPN" if resultado.propias_de_la_dpn else "cada organismo listado"
    typer.echo(
        f"Sección: {resultado.seccion}\n"
        f"Oficinas leídas: {resultado.oficinas} · titular: {titular}\n"
        f"Puntos nuevos: {resultado.puntos_creados} · ya conocidos: "
        f"{resultado.puntos_conocidos}\n"
        f"Canales: {resultado.canales}\n"
        f"Correos no tomados por venir ofuscados: {resultado.correos_no_tomados}\n"
        f"Sin dirección publicada: {resultado.sin_direccion}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@ingesta.command("cargar-manual")
def ingesta_cargar_manual(
    fuente: str = typer.Argument(..., help="Identificador de la fuente (F42, M05, ...)."),
    archivo: Path = typer.Argument(..., help="Archivo obtenido por una vía legítima."),
    actor: str = typer.Option(..., help="Quién carga, con rol. Ej: 'ingesta:persona'."),
    procedencia: str = typer.Option(..., help="De dónde salió, con detalle para rebuscarlo."),
    obtenido: str = typer.Option(..., help="Cuándo se obtuvo (AAAA-MM-DD), no cuándo se carga."),
    mime: str | None = typer.Option(None, help="Tipo de contenido, si se conoce."),
    url: str | None = typer.Option(None, help="URL de origen, si la hay."),
) -> None:
    """Incorpora un archivo a una fuente que no se puede recorrer.

    Entra por la misma cadena que una captura de red —corrida, captura inmutable
    y de ahí documentos y evidencia—: lo que cambia es que hay que declarar
    quién lo consiguió, de dónde y cuándo. Sin eso no se carga.
    """
    import datetime as _dt

    from backend_normativo.ingesta.manual import CargaManual, ProcedenciaInsuficiente

    with engine_migrador().begin() as conexion:
        try:
            resultado = CargaManual(conexion).cargar(
                fuente,
                archivo,
                actor=actor,
                procedencia=procedencia,
                obtenido_en=_dt.date.fromisoformat(obtenido),
                mime=mime,
                url_declarada=url,
            )
        except (ProcedenciaInsuficiente, LookupError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(
        f"Captura: {resultado.captura_id}\n"
        f"SHA-256: {resultado.sha256}\n"
        f"Bytes: {resultado.bytes}"
        + (" (el contenido ya estaba en el almacén)" if resultado.ya_existia else "")
        + f"\nLa fuente {resultado.source_id} queda en estado MANUAL: que alguien haya "
        "conseguido el archivo no significa que el sistema pueda recorrerla."
    )


@ingesta.command("bloqueadas")
def ingesta_bloqueadas() -> None:
    """Las fuentes que hoy necesitan carga manual, con su motivo."""
    from backend_normativo.ingesta.manual import fuentes_bloqueadas

    with engine_migrador().connect() as conexion:
        filas = fuentes_bloqueadas(conexion)
    typer.echo(f"{len(filas)} fuente(s) bloqueada(s):")
    for fila in filas:
        typer.echo(
            f"  {fila['source_id']} · {fila['access_status']} · "
            f"responsable: {fila['responsable_rol'] or 'sin asignar'}"
        )
        if fila["motivo_estado"]:
            typer.echo(f"      {fila['motivo_estado'][:160]}")


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

    from backend_normativo.ingesta.adaptadores.base import RELACIONES_PROMOVIBLES

    with engine_migrador().begin() as conexion:
        promovidas = (
            conexion.execute(
                sql(
                    "WITH elegibles AS ("
                    "  SELECT c.id, c.url FROM fuentes_candidatas c "
                    "   WHERE c.source_id_origen = :s AND c.estado = 'NUEVA' "
                    "     AND EXISTS (SELECT 1 FROM unnest(CAST(:relaciones AS text[])) r "
                    "                  WHERE c.relacion LIKE '%' || r || '%') "
                    "   ORDER BY c.descubierta_en LIMIT :lim"
                    "), insertadas AS ("
                    "  INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                    "  SELECT :s, e.url, 'DETALLE', 'HTTP_GET_PUBLICO' FROM elegibles e "
                    "  ON CONFLICT (source_id, url) DO NOTHING RETURNING url"
                    ") UPDATE fuentes_candidatas SET estado = 'PROMOVIDA' "
                    "  WHERE id IN (SELECT id FROM elegibles) RETURNING url"
                ),
                {"s": fuente, "lim": limite, "relaciones": list(RELACIONES_PROMOVIBLES)},
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


@operacion.command("respaldar")
def operacion_respaldar(
    destino: Path = typer.Argument(..., help="Directorio donde dejar el volcado y el manifiesto."),
) -> None:
    """Vuelca la base y deja el inventario del almacén de objetos junto a ella."""
    from backend_normativo.config import get_settings
    from backend_normativo.operacion.respaldo import RespaldoInvalido, respaldar

    ajustes = get_settings()
    with engine_migrador().connect() as conexion:
        try:
            manifiesto = respaldar(
                conexion,
                destino,
                url_base=str(ajustes.database_url),
                directorio_objetos=ajustes.objetos_dir,
            )
        except RespaldoInvalido as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(
        f"Respaldo en {destino}\n"
        f"Objetos inventariados: {len(manifiesto.objetos)}\n"
        f"Capturas: {manifiesto.capturas} · releases publicados: {manifiesto.releases}\n"
        f"Evidencias: {manifiesto.evidencias} · "
        f"eventos ya entregados: {manifiesto.eventos_entregados}\n"
        f"Hash del inventario: {manifiesto.hash}"
    )


@operacion.command("restaurar")
def operacion_restaurar(
    origen: Path = typer.Argument(..., help="Directorio del respaldo."),
    base: str = typer.Option("backend_normativo_restaurado", help="Base destino, se recrea."),
    salida: Path | None = typer.Option(None, help="Archivo donde escribir la verificación."),
) -> None:
    """Restaura en una base aislada y verifica que lo restaurado sirva.

    No basta con que la restauración termine: se comprueba que cada captura
    tenga sus bytes, que el release traiga sus fragmentos y evidencias, y que
    los eventos ya entregados no se vuelvan a enviar.
    """
    from sqlalchemy import create_engine
    from sqlalchemy import text as sql

    from backend_normativo.config import get_settings
    from backend_normativo.operacion.respaldo import (
        RespaldoInvalido,
        formatear,
        leer_manifiesto,
        restaurar,
        verificar,
    )

    ajustes = get_settings()
    url_actual = str(ajustes.database_url)
    url_destino = url_actual.rsplit("/", 1)[0] + "/" + _base_valida(base)

    try:
        manifiesto = leer_manifiesto(origen)
    except RespaldoInvalido as exc:
        typer.echo(str(exc))
        raise typer.Exit(1) from exc

    admin = create_engine(url_actual.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conexion:
        conexion.execute(sql(f'DROP DATABASE IF EXISTS "{base}" WITH (FORCE)'))
        conexion.execute(sql(f'CREATE DATABASE "{base}"'))
    admin.dispose()

    try:
        restaurar(origen, url_destino=url_destino)
    except RespaldoInvalido as exc:
        typer.echo(str(exc))
        raise typer.Exit(1) from exc

    motor = create_engine(url_destino, future=True)
    with motor.connect() as conexion:
        verificacion = verificar(conexion, manifiesto, ajustes.objetos_dir)
    motor.dispose()

    texto = formatear(manifiesto, verificacion)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(
            f"Verificación escrita en {salida} · "
            f"{'íntegro' if verificacion.integra else 'CON PROBLEMAS'}"
        )
    else:
        typer.echo(texto)
    if not verificacion.integra:
        raise typer.Exit(1)


@curacion.command("montos")
def curacion_montos(
    fuentes: list[str] = typer.Argument(..., help="Fuentes de montos (F12, ...)."),
) -> None:
    """Carga los importes publicados por una fuente, cada uno con su período.

    El período sale de la tabla —«a partir del X» rige hasta el día anterior al
    siguiente— y no de cuándo se descargó. Un importe sin fecha desde la que
    rija no se carga: se registra como faltante.
    """
    from backend_normativo.curacion.montos import CuradorDeMontos

    for source_id in fuentes:
        with engine_migrador().begin() as conexion:
            resultado = CuradorDeMontos(conexion).cargar(source_id)
        typer.echo(
            f"{source_id}: {resultado.filas_leidas} renglón(es) leído(s) · "
            f"valores nuevos {resultado.valores_creados} · "
            f"ya estaban {resultado.valores_existentes} · "
            f"rechazados {len(resultado.rechazadas)} · "
            f"sin período {resultado.sin_periodo}"
        )
        for aviso in resultado.avisos:
            typer.echo(f"    {aviso}")


@calidad.command("plazos")
def calidad_plazos(
    salida: Path | None = typer.Option(None, "--salida", help="Archivo donde escribir."),
) -> None:
    """Comprueba que cada plazo pueda señalar su número en el texto que cita.

    Falla si alguno declara una cantidad que su cita no contiene, ni en cifras
    ni en letras: una cita que solo comparte tema no respalda un número.
    """
    from backend_normativo.calidad.plazos import construir, formatear

    with engine_migrador().connect() as conexion:
        reporte = construir(conexion)
    texto = formatear(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(
            f"Verificación de plazos escrita en {salida} · "
            f"{len(reporte.no_sostenidos)} sin respaldo de {len(reporte.plazos)}"
        )
    else:
        typer.echo(texto)
    if reporte.no_sostenidos:
        raise typer.Exit(1)


@calidad.command("fuentes")
def calidad_fuentes(
    salida: Path | None = typer.Option(None, "--salida", help="Archivo donde escribir."),
    estricto: bool = typer.Option(
        False,
        "--estricto",
        help="Salir con error si alguna fuente capturó bien y no llegó a destino.",
    ),
) -> None:
    """Compara cada fuente con la historia que el manifiesto le declara.

    Informa y sale bien por defecto: hoy hay fuentes que no llegan a destino y
    hacer fallar la población por eso trabaría un trabajo que no es el mismo.
    Con `--estricto` falla, que es como tiene que quedar cuando esas fuentes se
    resuelvan.
    """
    from backend_normativo.calidad.fuentes import construir, formatear

    with engine_migrador().connect() as conexion:
        reporte = construir(conexion)
    texto = formatear(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(
            f"Verificación de fuentes escrita en {salida} · "
            f"{len(reporte.sin_destino)} capturada(s) sin llegar a destino"
        )
    else:
        typer.echo(texto)
    if estricto and (reporte.sin_destino or reporte.sin_extraer):
        raise typer.Exit(1)


@calidad.command("grafo")
def calidad_grafo(
    profundidad: int = typer.Option(4, "--profundidad", help="Tope de saltos al buscar ciclos."),
    salida: Path | None = typer.Option(None, "--salida", help="Archivo donde escribir."),
) -> None:
    """Informa cómo está conectado el grafo de relaciones y cuántos ciclos tiene.

    No falla por haber ciclos: son legítimos. Falla si hay autorreferencias, que
    el esquema no admite desde la migración 0010.
    """
    from backend_normativo.calidad.grafo import construir, formatear

    with engine_migrador().connect() as conexion:
        reporte = construir(conexion, profundidad)
    texto = formatear(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(
            f"Informe del grafo escrito en {salida} · "
            f"{reporte.relaciones} relaciones, {reporte.ciclos} ciclo(s)"
        )
    else:
        typer.echo(texto)
    if reporte.autorreferencias:
        raise typer.Exit(1)


@ingesta.command("conciliar")
def ingesta_conciliar(
    salida: Path | None = typer.Option(None, "--salida", help="Archivo donde escribir."),
) -> None:
    """Comprueba que cada fila que un importador leyó haya terminado en algún lado.

    Falla si alguna conciliación no cierra, si hay rechazos sin motivo o si
    quedó una corrida a medias: dar por cerrada una carga que tiene una corrida
    interrumpida la deja incompleta sin decirlo.
    """
    from backend_normativo.ingesta.conciliacion import conciliar, formatear

    with engine_migrador().connect() as conexion:
        reporte = conciliar(conexion)
    texto = formatear(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(
            f"Conciliación escrita en {salida} · "
            f"{len(reporte.filas)} importación(es), "
            f"{'todo cierra' if reporte.todo_cierra else 'CON PENDIENTES'}"
        )
    else:
        typer.echo(texto)
    if not reporte.todo_cierra:
        raise typer.Exit(1)


@objetos.command("verificar")
def objetos_verificar(
    desde: Path | None = typer.Option(
        None,
        "--desde",
        help=(
            "Directorio de otro almacén. Sirve para ensayar la recuperación del "
            "original desde una instancia distinta de la que lo capturó."
        ),
    ),
    sin_incidencias: bool = typer.Option(
        False,
        "--sin-incidencias",
        help="Informa sin abrir incidencias ni bloquear nada. Para inspeccionar.",
    ),
    salida: Path | None = typer.Option(None, "--salida", help="Archivo donde escribir."),
) -> None:
    """Comprueba que cada captura siga teniendo sus bytes detrás.

    Si un objeto falta o su hash difiere, abre una incidencia CRITICAL sobre
    cada versión que dependa de él: eso la deja fuera de lo servible hasta que
    alguien recupere el original.
    """
    from backend_normativo.ingesta.almacen import AlmacenObjetos
    from backend_normativo.operacion.objetos import formatear, verificar_almacen

    almacen = (
        AlmacenObjetos(base_uri=f"file://{desde}", directorio=desde) if desde else AlmacenObjetos()
    )
    with engine_migrador().begin() as conexion:
        reporte = verificar_almacen(conexion, almacen, abrir_incidencias=not sin_incidencias)
    texto = formatear(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(
            f"Verificación escrita en {salida} · "
            f"{len(reporte.hallazgos)} objeto(s) con problema de {reporte.referencias}"
        )
    else:
        typer.echo(texto)
    if reporte.hay_problemas:
        raise typer.Exit(1)


@objetos.command("sincronizar")
def objetos_sincronizar(
    hacia: Path = typer.Argument(
        ...,
        help="Directorio del almacén que sobrevive al contenedor (volumen o bucket montado).",
    ),
    salida: Path | None = typer.Option(None, "--salida", help="Archivo donde escribir."),
) -> None:
    """Lleva los originales fuera del contenedor y los verifica en el destino.

    Copia solo lo que la base referencia y relee cada objeto desde el destino:
    una copia que nadie volvió a leer no es un respaldo.
    """
    from backend_normativo.ingesta.almacen import AlmacenObjetos
    from backend_normativo.operacion.objetos import formatear_sincronizacion, sincronizar

    destino = AlmacenObjetos(base_uri=f"file://{hacia}", directorio=hacia)
    with engine_migrador().begin() as conexion:
        reporte = sincronizar(conexion, destino)
    texto = formatear_sincronizacion(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(
            f"Sincronización escrita en {salida} · "
            f"{reporte.copiados} copiado(s), {'completa' if reporte.completa else 'INCOMPLETA'}"
        )
    else:
        typer.echo(texto)
    if not reporte.completa:
        raise typer.Exit(1)


@plazos.command("calendario")
def plazos_calendario(
    anio: int = typer.Argument(..., help="Año del calendario de feriados a cargar."),
) -> None:
    """Captura e importa el calendario de feriados nacionales de un año.

    Cada feriado queda atado al fragmento del archivo oficial que lo declara: un
    feriado sin evidencia es un día no laborable inventado, y con eso se
    calculan vencimientos que después alguien pierde.
    """
    from backend_normativo.ingesta.capturador import Capturador
    from backend_normativo.ingesta.cliente import ClienteCaptura
    from backend_normativo.plazos import calendarios

    with engine_migrador().begin() as conexion:
        calendarios.registrar_url(conexion, anio)

    with ClienteCaptura() as cliente, engine_migrador().begin() as conexion:
        resultado = Capturador(conexion, cliente=cliente).capturar_fuente(calendarios.SOURCE_ID)
    typer.echo(
        f"Captura: {resultado.estado.value} · descargadas {resultado.descargadas} · "
        f"rechazadas {resultado.rechazadas}"
    )
    for incidencia in resultado.incidencias:
        typer.echo(f"    incidencia: {incidencia}")
    if not resultado.capturas:
        raise typer.Exit(1)

    with engine_migrador().begin() as conexion:
        sha = conexion.execute(
            sql_text("SELECT sha256_raw FROM capturas WHERE id = :c"),
            {"c": resultado.capturas[-1]},
        ).scalar_one()
        contenido = calendarios.almacen_por_defecto().leer(sha)
        try:
            cargado = calendarios.importar(
                conexion, contenido, captura_id=resultado.capturas[-1], anio=anio
            )
        except calendarios.CalendarioInvalido as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc

    typer.echo(
        f"Calendario: {cargado.nombre}@{cargado.version}\n"
        f"Cobertura: {cargado.desde} a {cargado.hasta}\n"
        f"Feriados nuevos: {cargado.feriados_nuevos} · ya cargados: {cargado.feriados_conocidos}"
    )
    for aviso in cargado.avisos:
        typer.echo(f"  aviso: {aviso}")


@plazos.command("calcular")
def plazos_calcular(
    inicio: str = typer.Argument(..., help="Fecha del evento de inicio (AAAA-MM-DD)."),
    cantidad: int = typer.Argument(..., help="Cantidad de días o semanas."),
    unidad: str = typer.Option("dias", help="dias o semanas."),
    tipo_dia: str = typer.Option("HABIL_ADMINISTRATIVO", help="CORRIDO o HABIL_*."),
    jurisdiccion: str = typer.Option("AR", help="Jurisdicción del calendario."),
    inclusivo: bool = typer.Option(False, help="El día del evento cuenta como el primero."),
) -> None:
    """Calcula un vencimiento y muestra con qué calendario lo hizo."""
    import datetime as _dt

    from backend_normativo.plazos import calendarios
    from backend_normativo.plazos.computo import calcular_vencimiento

    fecha = _dt.date.fromisoformat(inicio)
    with engine_migrador().connect() as conexion:
        calendario = calendarios.cargar(conexion, jurisdiccion=jurisdiccion, para=fecha)

    resultado = calcular_vencimiento(
        inicio=fecha,
        cantidad=cantidad,
        unidad=unidad,
        tipo_dia=tipo_dia,
        calendario=calendario,
        inclusivo_desde=inclusivo,
    )
    if resultado.determinado:
        typer.echo(f"Vencimiento: {resultado.vencimiento}")
    else:
        typer.echo("Vencimiento: no determinado")
        if resultado.requiere:
            typer.echo(f"Falta: {resultado.requiere}")
    typer.echo(resultado.fundamento)


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
    url_ensayo = url_actual.rsplit("/", 1)[0] + "/" + _base_valida(base)

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


@calidad.command("escalado")
def calidad_escalado(
    salida: str | None = typer.Option(None, help="Archivo donde escribir el reporte."),
    procesos: str = typer.Option("1,2,4", help="Cuántos procesos probar, separados por coma."),
    clientes: int = typer.Option(16, help="Clientes concurrentes del generador de carga."),
    barrido: str = typer.Option(
        "4,32,64", "--barrido", help="Concurrencias extra a probar con el mayor N de procesos."
    ),
    segundos: float = typer.Option(6.0, help="Cuánto dura cada medición."),
) -> None:
    """Mide si el caudal se multiplica al agregar procesos de API.

    Levanta la API con N procesos de verdad, que comparten el socket de escucha,
    y le tira carga desde otro proceso. Contesta la pregunta que la medición por
    hilos no podía contestar: si el techo de un proceso es el techo del sistema.
    """
    from backend_normativo.calidad.escalado import formatear, medir

    cuantos = tuple(int(p) for p in procesos.split(",") if p.strip())
    # La conexión se usa solo para leer el techo de conexiones de la base: sin
    # eso, un caudal que no sube se puede leer como «llegó al límite» cuando en
    # realidad el despliegue está pidiendo más conexiones de las que hay.
    with engine_migrador().connect() as conexion:
        reporte = medir(
            procesos=cuantos,
            clientes=clientes,
            segundos=segundos,
            barrido_clientes=tuple(int(b) for b in barrido.split(",") if b.strip()),
            conexion=conexion,
        )
    texto = formatear(reporte)
    if salida:
        Path(salida).write_text(texto, encoding="utf-8")
        typer.echo(f"Reporte escrito en {salida}")
    else:
        typer.echo(texto)
    for aviso in reporte.avisos:
        typer.echo(f"  {aviso}")


@calidad.command("rendimiento")
def calidad_rendimiento(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
    repeticiones: int = typer.Option(12, help="Repeticiones por consulta."),
) -> None:
    """Mide cuánto tarda cada consulta sobre el corpus que hay.

    El reporte lleva el tamaño del corpus al lado de los números: una latencia
    sin decir sobre cuántas filas se midió no significa nada.
    """
    from fastapi.testclient import TestClient

    from backend_normativo.api.app import crear_app
    from backend_normativo.api.dependencias import conexion_lectura
    from backend_normativo.calidad.rendimiento import correr
    from backend_normativo.calidad.rendimiento import formatear as formatear_rendimiento

    motor = engine_migrador()
    with motor.connect() as conexion:
        app = crear_app()
        app.dependency_overrides[conexion_lectura] = lambda: conexion
        with TestClient(app) as cliente:
            reporte = correr(conexion, cliente, repeticiones=repeticiones)

    texto = formatear_rendimiento(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        peor = reporte.peor
        typer.echo(
            f"Reporte escrito en {salida} · consultas {len(reporte.mediciones)} · "
            + (f"peor p95 {peor.p95_ms} ms ({peor.nombre})" if peor else "sin mediciones")
        )
    else:
        typer.echo(texto)


@calidad.command("carga")
def calidad_carga(
    minutos: float = typer.Option(30.0, help="Duración del ensayo."),
    conversaciones: int = typer.Option(20, help="Conversaciones concurrentes."),
    limite: int = typer.Option(
        120, help="Límite de consultas por minuto del servicio durante el ensayo."
    ),
    salida: Path = typer.Option(
        None, help="Archivo donde escribir el informe. Por omisión, a la salida estándar."
    ),
    parar_base: str = typer.Option(
        "pg_ctlcluster 16 main stop", help="Comando para apagar la base durante el fallo."
    ),
    arrancar_base: str = typer.Option(
        "pg_ctlcluster 16 main start", help="Comando para volver a encenderla."
    ),
) -> None:
    """Carga sostenida y fallos inducidos de proveedor, base y fuente (P-023, criterio 3).

    Levanta un servidor de verdad en su propio proceso, un proveedor de modelo
    de mentira y una fuente de mentira, y los rompe a propósito en ventanas
    programadas. Simular un fallo con una bandera prueba la bandera.
    """
    import json as _json
    import os as _os
    import shlex
    import socket
    import subprocess
    import sys
    import time as _time

    import httpx
    from sqlalchemy import text as _text

    from backend_normativo.calidad import carga as mod

    consultas = _json.loads(
        Path("docs/calidad/consultas_conversacionales.json").read_text(encoding="utf-8")
    )["consultas"]

    with engine_migrador().connect() as conexion:
        release = conexion.execute(
            _text(
                "SELECT id FROM releases WHERE estado = 'PUBLICADO' "
                " ORDER BY publicado_en DESC LIMIT 1"
            )
        ).scalar_one_or_none()
        if release is None:
            typer.echo("No hay corte publicado: el ensayo mediría abstenciones vacías.", err=True)
            raise typer.Exit(code=1)
        chunks = {
            str(fila[0])
            for fila in conexion.execute(
                _text("SELECT id FROM chunks WHERE release_id = :r"), {"r": release}
            ).all()
        }

    segundos = minutos * 60.0
    with mod.ServidorDeMentira() as proveedor, mod.ServidorDeMentira() as fuente:
        entorno = dict(_os.environ)
        entorno["BN_MODELO_CLAVE"] = "clave-de-ensayo-sin-valor"
        entorno["BN_MODELO_URL"] = f"{proveedor.url}/v1/messages"
        entorno["BN_MODELO_NOMBRE"] = "modelo-de-ensayo"
        entorno["BN_MODELO_TIMEOUT"] = "10"
        entorno["BN_LIMITE_CONSULTAS_POR_MINUTO"] = str(limite)
        # El generador de carga manda un origen por conversación; el servicio lo
        # lee porque acá el «proxy» es el propio ensayo.
        entorno["BN_PROXIES_CONFIABLES"] = "1"
        # El modelo se carga al arrancar y no en medio de la primera consulta.
        entorno["BN_PRECARGAR_MODELO"] = "1"

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        proceso = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend_normativo.api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto),
                "--log-level",
                "warning",
            ],
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{puerto}"
        limite_arranque = _time.monotonic() + 60
        while _time.monotonic() < limite_arranque:
            try:
                if httpx.get(f"{base}/salud", timeout=2).status_code == 200:
                    break
            except Exception:
                _time.sleep(0.4)
        else:
            proceso.terminate()
            typer.echo("El servidor del ensayo no llegó a contestar.", err=True)
            raise typer.Exit(code=1)

        observaciones_fuente: list[str] = []

        def fallo_de_fuente() -> None:
            observaciones_fuente.extend(mod.probar_fuente(fuente))

        # Tres ventanas, repartidas para que haya carga normal antes, entre y
        # después de cada una. Con el ensayo corto se achican solas.
        tercio = segundos / 4
        fallos = [
            mod.Fallo(
                nombre="Proveedor de modelo caído (503)",
                desde_s=tercio,
                duracion_s=min(60.0, tercio / 2),
                aplicar=proveedor.romper,
                revertir=proveedor.arreglar,
            ),
            mod.Fallo(
                nombre="Fuente caída (503 transitorio y 403 de acceso limitado)",
                desde_s=tercio * 2,
                duracion_s=min(30.0, tercio / 2),
                aplicar=fallo_de_fuente,
                revertir=fuente.arreglar,
            ),
            mod.Fallo(
                nombre="Base de datos apagada",
                desde_s=tercio * 3,
                duracion_s=min(60.0, tercio / 2),
                aplicar=lambda: mod.apagar_base(shlex.split(parar_base)),
                revertir=lambda: mod.encender_base(shlex.split(arrancar_base)),
                medir_recuperacion=True,
            ),
        ]

        try:
            reporte = mod.correr(
                base=base,
                consultas=consultas,
                conversaciones=conversaciones,
                segundos=segundos,
                fallos=fallos,
                chunks_del_corte=chunks,
                limite_configurado=limite,
            )
            # Si el proceso de la API murió, el servicio no se recuperó solo.
            for fallo in reporte.fallos:
                fallo.reinicio_necesario = proceso.poll() is not None
        finally:
            proceso.terminate()
            try:
                proceso.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proceso.kill()

    if observaciones_fuente:
        reporte.avisos.append(
            "Fuente caída, con el cliente de ingesta de verdad: " + " · ".join(observaciones_fuente)
        )
    reporte.avisos.append(
        "El proveedor de modelo es local y contesta al instante: lo que este ensayo mide de él "
        "es el camino de fallo y el repliegue a extracto, no la latencia de un modelo real."
    )
    reporte.avisos.append(
        "La carga se genera desde la misma máquina que sirve y que hospeda la base. Los números "
        "de latencia incluyen esa contención y no son los de un despliegue con instancias "
        "separadas."
    )

    texto = mod.formatear(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto, encoding="utf-8")
        typer.echo(f"Informe escrito en {salida}")
    else:
        typer.echo(texto)
    if reporte.filtraciones:
        raise typer.Exit(code=1)


@calidad.command("consultas")
def calidad_consultas(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
) -> None:
    """Corre el conjunto experto de consultas conversacionales (DQ18)."""
    from fastapi.testclient import TestClient

    from backend_normativo.api.app import crear_app
    from backend_normativo.api.dependencias import conexion_administracion, conexion_lectura
    from backend_normativo.calidad.conversacional import ConjuntoInsuficiente, correr
    from backend_normativo.calidad.conversacional import formatear as formatear_consultas

    with engine_migrador().connect() as conexion:
        app = crear_app()
        app.dependency_overrides[conexion_lectura] = lambda: conexion
        app.dependency_overrides[conexion_administracion] = lambda: conexion
        with TestClient(app) as cliente:
            try:
                reporte = correr(conexion, cliente)
            except ConjuntoInsuficiente as exc:
                typer.echo(str(exc))
                raise typer.Exit(1) from exc
    texto = formatear_consultas(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(
            f"Reporte escrito en {salida} · {reporte.pasan}/{reporte.total} pasan · "
            f"críticas {reporte.criticas_que_pasan}/{reporte.criticas} · "
            f"gate {'cumple' if reporte.cumple_la_gate else 'NO cumple'}"
        )
    else:
        typer.echo(texto)


@curacion.command("tramites")
def curacion_tramites(
    fuente: str | None = typer.Option(None, help="Limitar a una fuente."),
) -> None:
    """Arma trámites y pasos a partir de las fichas ya extraídas.

    Lo que la ficha no dice no se completa: una duración vacía no es
    «inmediato» y un costo vacío no es «gratuito».
    """
    from backend_normativo.curacion.tramites import CargadorTramites

    with engine_migrador().begin() as conexion:
        resultado = CargadorTramites(conexion).cargar(fuente)
    typer.echo(
        f"Fichas leídas: {resultado.fichas_leidas}\n"
        f"Trámites nuevos: {resultado.tramites_creados} · "
        f"ya conocidos: {resultado.tramites_conocidos}\n"
        f"Pasos: {resultado.pasos_creados}\n"
        f"Sin costo informado: {resultado.sin_costo} · "
        f"sin duración: {resultado.sin_duracion} · sin pasos: {resultado.sin_pasos}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@curacion.command("beneficios")
def curacion_beneficios(
    archivo: Path | None = typer.Option(None, help="Una lectura curada; por defecto, todas."),
) -> None:
    """Carga los beneficios desde las lecturas curadas de `docs/curaduria/`.

    Todo entra como candidato: la evaluación de un beneficio decide si alguien
    puede pedir algo, y que lo haya escrito una curaduría no lo vuelve derecho
    aplicable.
    """
    from backend_normativo.curacion.beneficios import (
        CuradorDeBeneficios,
        LecturaInvalida,
        cargar_todas,
    )

    with engine_migrador().begin() as conexion:
        try:
            resultados = (
                [CuradorDeBeneficios(conexion).cargar(archivo)]
                if archivo
                else cargar_todas(conexion)
            )
        except LecturaInvalida as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc

    if not resultados:
        typer.echo("No hay lecturas curadas en docs/curaduria/.")
        return
    for resultado in resultados:
        typer.echo(
            f"Beneficio {resultado.beneficio_id}\n"
            f"Poblaciones: {resultado.poblaciones} · reglas: {resultado.reglas} "
            f"(sin formalizar: {resultado.reglas_sin_formalizar})\n"
            f"Cuantías: {resultado.cuantias} · plazos: {resultado.plazos}\n"
            f"Campos no informados: {resultado.campos_no_informados} · "
            f"vacíos declarados: {resultado.vacios} · "
            f"conflictos abiertos: {resultado.conflictos} · "
            f"dependencias abiertas: {resultado.dependencias}"
        )
        for aviso in resultado.avisos:
            typer.echo(f"  aviso: {aviso}")

    # Una lectura que no cargó tiene que verse en la última línea, no perdida
    # entre los avisos de las que sí: quien corre esto en una población entera
    # filtra la salida y se queda con los totales.
    sin_cargar = [r for r in resultados if r.no_cargada]
    if sin_cargar:
        typer.echo(
            f"Lecturas que no cargaron: {len(sin_cargar)} "
            f"({', '.join(r.no_cargada or '' for r in sin_cargar)})"
        )
    defectuosas = [r for r in sin_cargar if not r.falta_la_norma]
    if defectuosas:
        # Que a una lectura le falte su norma es una fuente que no entregó y se
        # informa. Que la lectura esté mal es un defecto, y terminar en cero lo
        # deja pasar en cualquier procedimiento que mire el código de salida.
        raise typer.Exit(1)


@curacion.command("anexos")
def curacion_anexos(
    norma: str = typer.Argument(..., help="Id de la norma cuyo cuerpo aprueba anexos."),
) -> None:
    """Detecta las remisiones a anexos y bloquea los campos que dependen de ellos.

    Un cuerpo que aprueba un anexo con el procedimiento no informa los plazos:
    los fija en otro documento. Publicar «no informa» sería decir menos de lo
    que la norma dice.
    """
    import uuid as _uuid

    from backend_normativo.curacion.anexos import CuradorDeAnexos

    with engine_migrador().begin() as conexion:
        resultado = CuradorDeAnexos(conexion).revisar(_uuid.UUID(norma))
    typer.echo(
        f"Remisiones a anexo: {resultado.remisiones} · con identificador: "
        f"{resultado.identificadas}\n"
        f"Referencias pendientes abiertas: {resultado.pendientes_abiertas}\n"
        f"Campos bloqueados: {resultado.campos_bloqueados}"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@curacion.command("vincular-anexo")
def curacion_vincular_anexo(
    referencia: str = typer.Argument(..., help="Id de la referencia pendiente."),
    version: str = typer.Option(..., help="Id de la versión documental del anexo."),
    actor: str = typer.Option(..., help="Quién vincula."),
    fundamento: str = typer.Option(..., help="Por qué ese anexo es el que la norma aprobó."),
) -> None:
    """Vincula un anexo capturado con la norma que lo aprueba.

    Que un PDF diga «Anexo» no prueba que sea el anexo de esta resolución.
    """
    import uuid as _uuid

    from backend_normativo.curacion.anexos import CuradorDeAnexos

    with engine_migrador().begin() as conexion:
        try:
            relacion = CuradorDeAnexos(conexion).resolver(
                _uuid.UUID(referencia),
                doc_version_anexo=_uuid.UUID(version),
                actor=actor,
                fundamento=fundamento,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(f"Anexo vinculado. Relación {relacion} (COMPLEMENTA).")


@curacion.command("equivalencias")
def curacion_equivalencias(
    norma: str = typer.Argument(..., help="Id de la norma con dos versiones de texto."),
) -> None:
    """Deriva a qué unidad de la versión nueva corresponde cada una de la vieja.

    Quedan como candidatas: una correspondencia sin aprobar no redirige ninguna
    cita. Aprobar es una decisión con nombre y fundamento.
    """
    import uuid as _uuid

    from backend_normativo.curacion.equivalencias import (
        CuradorDeEquivalencias,
        NormaSinDosVersiones,
    )

    with engine_migrador().begin() as conexion:
        try:
            resultado = CuradorDeEquivalencias(conexion).derivar_para_norma(_uuid.UUID(norma))
        except NormaSinDosVersiones as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(
        f"Origen: {resultado.origen_version_id}\n"
        f"Destino: {resultado.destino_version_id}\n"
        f"Renumeraciones: {resultado.renumeraciones} · sustituciones: "
        f"{resultado.sustituciones}\n"
        f"Cambian de artículo: {resultado.cambian_de_articulo}\n"
        f"Ya registradas: {resultado.ya_registradas}\n"
        f"Sin correspondencia: {resultado.sin_destino} salieron · "
        f"{resultado.sin_origen} entraron"
    )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


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


@revision.command("derivar-vigencia-beneficios")
def revision_derivar_vigencia_beneficios(
    actor: str = typer.Option(..., help="Quién queda registrado en cada derivación."),
    simular: bool = typer.Option(False, "--simular", help="Muestra qué haría y no escribe."),
) -> None:
    """Deriva la vigencia de cada beneficio de la de la norma que lo crea.

    Un beneficio no tiene vigencia propia: existe porque una norma lo crea y
    mientras esa norma rija. Las que lo reglamentan o lo modifican cambian su
    contenido, no su existencia.

    Es conservador: si la norma creadora no tiene vigencia resuelta, el
    beneficio tampoco, y se informa cuál falta.
    """
    from sqlalchemy import text as _text

    from backend_normativo.curacion.vigencia import ResolutorVigenciaDeBeneficios

    with engine_migrador().begin() as conexion:
        resultado = ResolutorVigenciaDeBeneficios(conexion).resolver(actor=actor)
        if simular:
            conexion.execute(_text("ROLLBACK"))

    verbo = "se resolverían" if simular else "resueltos"
    typer.echo(f"Beneficios mirados: {resultado.beneficios} · {verbo}: {resultado.resueltos}")
    for pendiente in resultado.sin_resolver:
        typer.echo(f"  queda sin resolver · {pendiente}")


@revision.command("resolver-vigencia")
def revision_resolver_vigencia(
    incidencia: str = typer.Argument(..., help="Identificador de la incidencia."),
    actor: str = typer.Option(..., help="Quién decide. Queda en la bitácora."),
    decision: str = typer.Option(..., help="Qué se decidió y con qué fundamento."),
    valid_tipo: str = typer.Option(..., help="CERRADO, ABIERTO_FIN, PUNTUAL, ..."),
    desde: str | None = typer.Option(None, help="Fecha de inicio (AAAA-MM-DD)."),
    hasta: str | None = typer.Option(None, help="Fecha de fin (AAAA-MM-DD)."),
    estado_legal: str = typer.Option("VIGENTE", help="Estado legal validado."),
    condicion: str | None = typer.Option(
        None,
        help=(
            "Para CONDICIONADO: de qué depende que rija. Sin esto la base rechaza la "
            "decisión, y con razón: «condicionado» sin condición no dice nada."
        ),
    ),
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
                "condicion_vigencia": condicion,
            },
        )
    typer.echo(
        f"Incidencia {resultado.incidencia_id} resuelta por {actor}. "
        f"Vigencia aplicada: {resultado.aplico_vigencia}"
    )


@revision.command("aprobar-equivalencia")
def revision_aprobar_equivalencia(
    equivalencia: str = typer.Argument(..., help="Id de la equivalencia candidata."),
    actor: str = typer.Option(..., help="Quién aprueba."),
    decision: str = typer.Option(..., help="Por qué esa correspondencia es la correcta."),
) -> None:
    """Aprueba una correspondencia entre unidades de dos versiones.

    Sólo una aprobada redirige una cita: hasta entonces la cita vieja se
    responde con el texto que efectivamente se citó.
    """
    import uuid as _uuid

    from backend_normativo.curacion.equivalencias import aprobar

    with engine_migrador().begin() as conexion:
        try:
            aprobar(conexion, _uuid.UUID(equivalencia), actor=actor, decision=decision)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from exc
    typer.echo(f"Equivalencia {equivalencia} aprobada por {actor}.")


@revision.command("reglas")
def revision_reglas(
    salida: str | None = typer.Option(None, help="Archivo donde escribir el expediente."),
    estado: str = typer.Option("CANDIDATE", help="Estado a listar; «todos» para no filtrar."),
    beneficio: str | None = typer.Option(None, help="Limitar a un código de beneficio."),
) -> None:
    """Arma el expediente de revisión: qué hay que decidir, regla por regla.

    Sin esto, «revisar 154 reglas» es una tarea sin forma. Con esto es una lista
    de preguntas concretas, cada una con el texto de la norma al lado.
    """
    from backend_normativo.curacion.revision_reglas import expediente, formatear

    with engine_migrador().connect() as conexion:
        resultado = expediente(
            conexion,
            estado=None if estado.lower() == "todos" else estado,
            beneficio=beneficio,
        )
    texto = formatear(resultado)
    if salida:
        Path(salida).write_text(texto, encoding="utf-8")
        typer.echo(
            f"Expediente escrito en {salida} · {len(resultado.reglas)} regla(s) · "
            f"sin condición ejecutable {resultado.sin_condicion} · "
            f"sin ubicar en el texto {resultado.sin_ubicar}"
        )
    else:
        typer.echo(texto)


@revision.command("aprobar-regla")
def revision_aprobar_regla(
    regla: str = typer.Argument(..., help="Id de la regla."),
    actor: str = typer.Option(..., help="Quién aprueba. Queda en la bitácora."),
    fundamento: str = typer.Option(..., help="Por qué. Queda en la bitácora."),
) -> None:
    """Habilita una regla para la evaluación.

    Es la transición que convierte una lectura curada en derecho aplicable, y la
    única que este sistema no hace solo: exige quién y por qué.
    """
    import uuid as _uuid

    from backend_normativo.curacion.revision_reglas import RevisionInvalida, aprobar

    try:
        with engine_migrador().begin() as conexion:
            aprobar(conexion, _uuid.UUID(regla), actor=actor, fundamento=fundamento)
    except RevisionInvalida as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
    typer.echo(f"Regla {regla} aprobada por {actor}.")


@revision.command("aprobar-reglas")
def revision_aprobar_reglas(
    beneficio: str = typer.Argument(..., help="Código del beneficio cuyas reglas se aprueban."),
    actor: str = typer.Option(..., help="Quién aprueba. Queda en la bitácora."),
    fundamento: str = typer.Option(..., help="Por qué. Queda en la bitácora."),
) -> None:
    """Aprueba de una vez las reglas de un beneficio, tras revisarlo entero.

    Las reglas de un beneficio se leen juntas porque se aplican juntas. Cada una
    deja igual su propio evento: lo que se firma una vez tiene que poder
    auditarse una por una.
    """
    from backend_normativo.curacion.revision_reglas import RevisionInvalida, aprobar_beneficio

    try:
        with engine_migrador().begin() as conexion:
            aprobadas = aprobar_beneficio(conexion, beneficio, actor=actor, fundamento=fundamento)
    except RevisionInvalida as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
    typer.echo(f"{len(aprobadas)} regla(s) de {beneficio} aprobadas por {actor}.")


@revision.command("pendientes-de-firma")
def revision_pendientes_de_firma(
    salida: Path = typer.Option(
        Path("docs/revision/pendientes.md"), help="Dónde escribir el informe."
    ),
) -> None:
    """Qué decisiones humanas quedan, ordenadas por dónde conviene empezar.

    «5.397 afirmaciones pendientes» no es una tarea: es un número que desalienta
    y no dice por dónde agarrarlo. Son 54 versiones, y catorce respaldan los
    beneficios que ya tienen sus reglas firmadas.
    """
    from backend_normativo.calidad.pendientes_de_firma import construir

    with engine_migrador().connect() as conexion:
        contenido = construir(conexion)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(contenido, encoding="utf-8")
    typer.echo(f"Informe escrito en {salida}.")


@revision.command("aprobar-versiones")
def revision_aprobar_versiones(
    tipo: list[str] = typer.Option(
        None, "--tipo", help="Tipos de entidad a aprobar. Sin esto, todos los aprobables."
    ),
    actor: str = typer.Option(..., help="Quién aprueba. Queda en un evento por versión."),
    fundamento: str = typer.Option(..., help="Por qué. Queda en cada evento."),
    confirmar: bool = typer.Option(
        False, "--confirmar", help="Aplicar de verdad. Sin esto solo se muestra qué pasaría."
    ),
) -> None:
    """Aprueba versiones de dato operativo en bloque.

    Un canal es un teléfono y una dirección transcriptos de un directorio
    oficial, con evidencia al fragmento exacto: no afirma qué le corresponde a
    nadie, y por eso se puede aprobar en bloque. Las reglas no.

    Nunca toca una versión con incidencia abierta ni una sin intervalo de
    aplicación, y deja un evento por versión. Sin `--confirmar` solo informa.
    """
    from backend_normativo.curacion.aprobacion_operativa import (
        AprobacionInvalida,
        aprobar,
        formatear,
        revisar,
    )

    tipos = list(tipo) if tipo else None
    try:
        if not confirmar:
            with engine_migrador().connect() as conexion:
                typer.echo(formatear(revisar(conexion, tipos=tipos), aplicado=False))
            return
        with engine_migrador().begin() as conexion:
            seleccion = aprobar(conexion, actor=actor, fundamento=fundamento, tipos=tipos)
    except AprobacionInvalida as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
    typer.echo(formatear(seleccion, aplicado=True))


@revision.command("plantilla-decisiones")
def revision_plantilla_decisiones(
    salida: Path = typer.Option(Path("docs/revision/decisiones.csv"), help="Dónde escribirla."),
    limite: int = typer.Option(0, help="Cuántas reglas incluir. 0 son todas las pendientes."),
) -> None:
    """Genera el CSV que completa quien revisa: una fila por regla pendiente.

    Los identificadores salen de la base y no se escriben a mano, que es de
    donde salen los errores de transcripción. La columna `fundamento` viene
    vacía a propósito: es lo que tiene que escribir la persona que decide.
    """
    from backend_normativo.curacion.transcripcion import plantilla

    with engine_migrador().begin() as conexion:
        contenido = plantilla(conexion, limite or None)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(contenido, encoding="utf-8")
    filas = max(0, contenido.count("\n") - 1)
    typer.echo(f"{filas} regla(s) pendientes escritas en {salida}.")


@revision.command("registrar-decisiones")
def revision_registrar_decisiones(
    archivo: Path = typer.Argument(..., help="CSV o JSON con las decisiones ya tomadas."),
    actor: str = typer.Option(..., help="Quién revisó y firma. Queda en cada evento."),
    confirmar: bool = typer.Option(
        False, "--confirmar", help="Aplicar de verdad. Sin esto solo se valida el archivo."
    ),
) -> None:
    """Registra decisiones que **ya tomó una persona**, una por una.

    No decide nada: transcribe. La firma jurídica ocurre fuera del sistema y
    esto la deja asentada sin deformarla, con el nombre de quien revisó en cada
    evento de la bitácora.

    Sin `--confirmar` solo valida, que es lo que conviene hacer primero: el
    archivo se revisa entero antes de escribir nada, porque media transcripción
    deja el expediente en un estado que nadie sabe leer.
    """
    from backend_normativo.curacion.transcripcion import (
        ArchivoInvalido,
        aplicar,
        desde_archivo,
        formatear,
    )

    try:
        filas = desde_archivo(archivo)
    except ArchivoInvalido as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error

    if not confirmar:
        typer.echo(
            f"{len(filas)} decisión(es) listas para registrar a nombre de {actor}. "
            "Nada se escribió todavía: volvé a correrlo con --confirmar."
        )
        return

    try:
        with engine_migrador().begin() as conexion:
            resultado = aplicar(conexion, filas, actor=actor, fuente=str(archivo))
    except ArchivoInvalido as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
    typer.echo(formatear(resultado))


@revision.command("habilitar-evaluacion")
def revision_habilitar_evaluacion(
    actor: str = typer.Option(..., help="Quién decide que estas reglas empiecen a evaluar."),
    fundamento: str = typer.Option(..., help="Por qué, con todas las letras."),
    beneficio: str | None = typer.Option(None, help="Un beneficio. Por omisión, todos."),
    simular: bool = typer.Option(False, "--simular", help="Cuenta y no habilita nada."),
) -> None:
    """Conecta al motor las reglas ya aprobadas que tienen condición ejecutable.

    No aprueba nada ni decide sobre el contenido de ninguna regla: toma lo que
    alguien ya aprobó y lo vuelve ejecutable. Existe porque las 166 del
    expediente se aprobaron antes de que aprobar bajara la marca de revisión, y
    quedaron aprobadas y sin poder ejecutarse.

    Las que no tienen árbol validado quedan afuera y se informan. Son las que el
    plan manda clasificar entre formalizables, informativas y sin evidencia; ese
    trabajo no lo reemplaza este comando.
    """
    from sqlalchemy import text as _text

    from backend_normativo.curacion.revision_reglas import RevisionInvalida, habilitar_aprobadas

    try:
        with engine_migrador().begin() as conexion:
            resultado = habilitar_aprobadas(
                conexion, actor=actor, fundamento=fundamento, beneficio=beneficio
            )
            if simular:
                conexion.execute(_text("ROLLBACK"))
    except RevisionInvalida as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    verbo = "se habilitarían" if simular else "habilitadas"
    typer.echo(
        f"Reglas {verbo}: {resultado.habilitadas}\n"
        f"Ya estaban habilitadas: {resultado.ya_estaban}\n"
        f"Sin condición ejecutable, quedan afuera: {resultado.sin_condicion}"
    )
    if resultado.sin_condicion:
        typer.echo(
            "Esas últimas siguen sin poder evaluarse y el motor las va a contestar "
            "DESCONOCIDO con su motivo. Clasificarlas entre formalizables, informativas y "
            "sin evidencia es P-010, criterio 2."
        )


@revision.command("rechazar-regla")
def revision_rechazar_regla(
    regla: str = typer.Argument(..., help="Id de la regla."),
    actor: str = typer.Option(..., help="Quién rechaza. Queda en la bitácora."),
    fundamento: str = typer.Option(..., help="Qué estaba mal. Queda en la bitácora."),
) -> None:
    """Descarta una regla: la lectura afirmaba algo que la norma no dice."""
    import uuid as _uuid

    from backend_normativo.curacion.revision_reglas import RevisionInvalida, rechazar

    try:
        with engine_migrador().begin() as conexion:
            rechazar(conexion, _uuid.UUID(regla), actor=actor, fundamento=fundamento)
    except RevisionInvalida as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
    typer.echo(f"Regla {regla} rechazada por {actor}.")


@revision.command("marcar-en-revision")
def revision_marcar_en_revision(
    regla: str = typer.Argument(..., help="Id de la regla."),
    actor: str = typer.Option(..., help="Quién la miró. Queda en la bitácora."),
    fundamento: str = typer.Option(..., help="Qué queda pendiente de decidir."),
) -> None:
    """Deja constancia de que la regla ya fue mirada y espera decisión.

    No aprueba ni sirve nada: separa «candidata» de «analizada y a la espera»,
    que es lo que hace que una revisión larga se pueda retomar.
    """
    import uuid as _uuid

    from backend_normativo.curacion.revision_reglas import RevisionInvalida, marcar_en_revision

    try:
        with engine_migrador().begin() as conexion:
            marcar_en_revision(conexion, _uuid.UUID(regla), actor=actor, fundamento=fundamento)
    except RevisionInvalida as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
    typer.echo(f"Regla {regla} en revisión, anotada por {actor}.")


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
    # Primero el resumen y después los ejemplos. Con catorce mil versiones
    # retenidas, quince identificadores sueltos no dicen qué hay que hacer;
    # «14.390 sin fecha de verificación» sí, y es una sola línea.
    from collections import Counter

    por_motivo: Counter[tuple[str, str]] = Counter()
    for fila in cuarentena:
        for motivo_cuarentena in fila["motivos"]:
            por_motivo[(fila["entidad_tipo"], motivo_cuarentena)] += 1
    for (tipo, motivo_cuarentena), cuantas in por_motivo.most_common():
        typer.echo(f"  {cuantas:>6}  {tipo}: {motivo_cuarentena}")
    if cuarentena:
        typer.echo("Algunas, con nombre y apellido:")
    for fila in cuarentena[:5]:
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
        f"Fragmentos citables: {resultado.chunks_creados} nuevos"
        f" · {resultado.chunks_heredados} heredados del corte anterior"
        f" ({resultado.vectores_heredados} con su vector)\n"
        f"Eventos en outbox: {resultado.eventos_emitidos}\n"
        f"En cuarentena: {len(resultado.en_cuarentena)}"
    )
    for version in resultado.sin_afirmaciones_aprobadas:
        typer.echo(
            f"  aviso: la versión {version} se publicó con todas sus afirmaciones sin "
            "aprobar. La publicación es lo que las promueve, así que aprobarlas ahora ya "
            "no entra en este release y su ficha se sirve sin una sola cita. Se arregla "
            "con `bn revision aprobar-campos` y republicando: `bn publicacion revertir` "
            "deja de servir este corte sin borrar nada."
        )


@publicacion.command("revertir")
def publicacion_revertir(
    release: str = typer.Argument(..., help="Id del release que deja de servirse."),
    actor: str = typer.Option(..., help="Quién revierte."),
    motivo: str = typer.Option(..., help="Por qué se revierte."),
) -> None:
    """Deja de servir un release sin borrar nada.

    Las versiones vuelven a estado aprobado y quedan disponibles para otro
    release; el historial del revertido se conserva. Es la vía para volver atrás
    un corte publicado: borrar el release dejaría a los consumidores citando
    fragmentos que ya no se pueden explicar.
    """
    import uuid as _uuid

    from backend_normativo.publicacion.release import Publicador

    with engine_migrador().begin() as conexion:
        afectadas = Publicador(conexion).revertir(_uuid.UUID(release), actor=actor, motivo=motivo)
    typer.echo(
        f"Release {release} revertido por {actor}.\nVersiones que vuelven a APPROVED: {afectadas}"
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


@monitoreo.command("ciclo")
def monitoreo_ciclo(
    salida: Path | None = typer.Option(None, help="Archivo donde escribir la evidencia."),
    limite: int | None = typer.Option(None, help="Máximo de fuentes por vuelta."),
    en_seco: bool = typer.Option(
        False, help="Sólo planificar: dice a quién le toca sin salir a la red."
    ),
    minutos_de_turno: int = typer.Option(
        30,
        help="Tope máximo de la corrida. Pasado esto el turno queda libre aunque siga viva.",
    ),
) -> None:
    """Una vuelta del ciclo: planificar y revalidar a quien le toca.

    Está pensado para que un planificador del sistema lo llame cada hora. Una
    corrida sin trabajo no es una corrida fallida: es la frecuencia haciendo lo
    suyo.

    Dos disparos simultáneos no procesan lo mismo dos veces: cada vuelta pide un
    turno con vencimiento y la que no lo consigue se va sin tocar nada. Salir sin
    hacer nada por ese motivo es un éxito, no un fallo, y termina en cero: si
    devolviera error, el planificador reintentaría justo lo que no hay que
    repetir.
    """
    import datetime as dt

    from backend_normativo.ingesta.capturador import Capturador
    from backend_normativo.ingesta.cliente import ClienteCaptura
    from backend_normativo.ingesta.extraccion import Extractor
    from backend_normativo.monitoreo.ciclo import RECURSO, ResultadoCiclo
    from backend_normativo.monitoreo.ciclo import correr as correr_ciclo
    from backend_normativo.monitoreo.ciclo import formatear as formatear_ciclo
    from backend_normativo.monitoreo.novedades import correr as correr_monitor
    from backend_normativo.operacion.arrendamiento import arrendar

    def _revalidar(fuentes: list[str]) -> dict[str, int]:
        # `novedades.correr` ya encadena captura, extracción y comparación: el
        # ciclo planifica y delega, no repite el trabajo.
        del fuentes
        with ClienteCaptura() as cliente, engine_migrador().begin() as conexion:
            monitoreo = correr_monitor(
                conexion,
                capturador=Capturador(conexion, cliente=cliente),
                extractor=Extractor(conexion),
                limite=limite,
            )
        return {
            "revisadas": monitoreo.fuentes_revisadas,
            "con_cambios": monitoreo.con_cambios,
            "versiones": monitoreo.versiones_nuevas,
            "impactadas": monitoreo.normas_impactadas,
            "eventos": monitoreo.eventos_emitidos,
            "bloqueadas": monitoreo.bloqueadas,
        }

    with arrendar(
        engine_migrador(), RECURSO, duracion=dt.timedelta(minutes=minutos_de_turno)
    ) as turno:
        if not turno.tomado:
            resultado = ResultadoCiclo(
                ahora=dt.datetime.now(dt.UTC), salteada=True, avisos=[turno.por_que_no()]
            )
        else:
            with engine_migrador().connect() as conexion:
                resultado = correr_ciclo(
                    conexion, limite=limite, revalidar=None if en_seco else _revalidar
                )

    # Se pregunta después del `with`, que es donde se suelta: hasta ahí no se
    # sabe si la corrida se pasó de su turno.
    if turno.se_paso:
        resultado.avisos.append(turno.advertencia())

    texto = formatear_ciclo(resultado)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Evidencia escrita en {salida} · pendientes {len(resultado.pendientes)}")
    else:
        typer.echo(texto)


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


@recuperacion.command("indexar")
def recuperacion_indexar(
    release: str | None = typer.Option(None, help="Corte a indexar. Por omisión, el último."),
    modelo: str | None = typer.Option(None, help="Modelo de embeddings."),
    salida: Path | None = typer.Option(None, help="Archivo donde escribir la evidencia."),
) -> None:
    """Construye el índice semántico del corte publicado.

    Reconstruir es barato y es lo que hace: compara el hash del texto de cada
    fragmento contra el que su vector embebió y solo recalcula lo que cambió.
    """
    import uuid as _uuid

    from backend_normativo.recuperacion.embeddings import EmbebedorFastEmbed
    from backend_normativo.recuperacion.indice import Indexador
    from backend_normativo.recuperacion.indice import formatear as formatear_indice

    embebedor = EmbebedorFastEmbed(modelo) if modelo else EmbebedorFastEmbed()
    with engine_migrador().begin() as conexion:
        resultado = Indexador(conexion, embebedor).construir(
            _uuid.UUID(release) if release else None
        )

    texto = formatear_indice(resultado)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Evidencia escrita en {salida} · fragmentos {resultado.fragmentos}")
    else:
        typer.echo(texto)
    if resultado.release_id is None:
        raise typer.Exit(code=1)


@recuperacion.command("buscar")
def recuperacion_buscar(
    consulta: str = typer.Argument(..., help="Lo que se busca, en palabras de quien pregunta."),
    limite: int = typer.Option(5, help="Cuántos fragmentos devolver."),
    jurisdiccion: str | None = typer.Option(None, help="Filtrar por jurisdicción."),
    beneficio: str | None = typer.Option(None, help="Filtrar por código de beneficio."),
    solo_lexica: bool = typer.Option(False, help="Sin la mitad vectorial, para comparar."),
) -> None:
    """Busca en el corte publicado combinando texto y significado."""
    from sqlalchemy import text as _text

    from backend_normativo.recuperacion.busqueda import buscar as buscar_fragmentos
    from backend_normativo.recuperacion.embeddings import EmbebedorFastEmbed

    with engine_migrador().connect() as conexion:
        release = conexion.execute(
            _text(
                "SELECT id FROM releases WHERE estado = 'PUBLICADO' "
                "ORDER BY publicado_en DESC LIMIT 1"
            )
        ).scalar_one_or_none()
        if release is None:
            typer.echo("No hay ningún corte publicado. No se busca en staging.")
            raise typer.Exit(code=1)
        resultado = buscar_fragmentos(
            conexion,
            consulta,
            release_id=release,
            embebedor=None if solo_lexica else EmbebedorFastEmbed(),
            limite=limite,
            jurisdiccion=jurisdiccion,
            beneficio=beneficio,
        )

    for fragmento in resultado.fragmentos:
        typer.echo(
            f"[{fragmento.encontrado_por:10s}] {fragmento.puntaje:.4f}  "
            f"{fragmento.norma} · {fragmento.unidad}"
        )
        typer.echo(f"    {fragmento.texto[:180].strip()}")
    if not resultado.fragmentos:
        typer.echo("Sin resultados en el corte publicado.")
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@recuperacion.command("evaluar")
def recuperacion_evaluar(
    conjunto: Path = typer.Option(
        Path("docs/calidad/recuperacion.json"), help="Conjunto congelado de evaluación."
    ),
    salida: Path | None = typer.Option(None, help="Archivo donde escribir el reporte."),
) -> None:
    """Mide Recall@k sobre el conjunto congelado, léxica contra híbrida.

    Falla si el conjunto cambió sin que se actualice su hash: un conjunto de
    evaluación que se puede editar después de ver el resultado no evalúa nada.
    """
    from backend_normativo.recuperacion.evaluacion import correr as correr_evaluacion
    from backend_normativo.recuperacion.evaluacion import formatear as formatear_evaluacion

    with engine_migrador().connect() as conexion:
        reporte = correr_evaluacion(conexion, conjunto)

    texto = formatear_evaluacion(reporte)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Reporte escrito en {salida} · Recall@5 híbrido {reporte.recall_hibrido:.1%}")
    else:
        typer.echo(texto)


@operacion.command("emitir-credencial")
def operacion_emitir_credencial(
    actor: str = typer.Option(..., help="Quién es. Queda en la bitácora de todo lo que firme."),
    rol: list[str] = typer.Option(
        ..., "--rol", help="Rol de la credencial. Se puede repetir: revisor, publicador, auditor."
    ),
    dias: int = typer.Option(30, help="Cuántos días vale. Máximo 90."),
) -> None:
    """Emite una credencial firmada para una persona.

    El token se imprime una sola vez y no se guarda: lo que la base conoce es su
    identificador, para poder revocarlo. Entregalo por un canal que no lo deje
    escrito donde no corresponde.
    """
    import datetime as dt

    from backend_normativo.seguridad.credenciales import CredencialInvalida, emitir

    try:
        token, identidad = emitir(actor, set(rol), duracion=dt.timedelta(days=dias))
    except CredencialInvalida as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"actor      {identidad.actor}")
    typer.echo(f"roles      {', '.join(sorted(identidad.roles))}")
    typer.echo(f"vence      {identidad.vence_en.isoformat(timespec='seconds')}")
    typer.echo(f"id         {identidad.jti}   (con esto se revoca)")
    typer.echo("")
    typer.echo(token)


@operacion.command("revocar-credencial")
def operacion_revocar_credencial(
    identificador: str = typer.Argument(..., help="El id que devolvió `emitir-credencial`."),
    actor: str = typer.Option(..., help="Quién la revoca."),
    motivo: str = typer.Option(..., help="Por qué. Queda escrito y no se borra."),
) -> None:
    """Deja sin efecto una credencial antes de su vencimiento.

    No se puede deshacer: que una credencial haya sido revocada es parte de la
    historia de quién pudo hacer qué y cuándo dejó de poder.
    """
    from sqlalchemy import text as _text

    with engine_migrador().begin() as conexion:
        anterior = conexion.execute(
            _text("SELECT actor, revocada_en FROM credenciales_revocadas WHERE jti = :j"),
            {"j": identificador},
        ).one_or_none()
        if anterior is not None:
            typer.echo(
                f"Ya estaba revocada el {anterior.revocada_en.isoformat(timespec='seconds')}."
            )
            return
        conexion.execute(
            _text(
                "INSERT INTO credenciales_revocadas (jti, actor, motivo, revocada_por) "
                "VALUES (:j, :a, :m, :p)"
            ),
            {"j": identificador, "a": actor, "m": motivo, "p": actor},
        )
    typer.echo(f"Credencial {identificador} revocada. Deja de valer en el próximo pedido.")


@operacion.command("credenciales-revocadas")
def operacion_credenciales_revocadas() -> None:
    """Lista las credenciales que dejaron de valer antes de vencer."""
    from sqlalchemy import text as _text

    with engine_migrador().connect() as conexion:
        filas = (
            conexion.execute(
                _text(
                    "SELECT jti, actor, motivo, revocada_por, revocada_en "
                    "  FROM credenciales_revocadas ORDER BY revocada_en DESC"
                )
            )
            .mappings()
            .all()
        )
    if not filas:
        typer.echo("Ninguna credencial revocada.")
        return
    for fila in filas:
        typer.echo(
            f"{fila['jti']}  {fila['actor']}  "
            f"{fila['revocada_en'].isoformat(timespec='seconds')}  "
            f"por {fila['revocada_por']}: {fila['motivo']}"
        )


@operacion.command("purgar-consultas")
def operacion_purgar_consultas(
    dias: int = typer.Option(
        None,
        help="Días de retención. Por omisión, los de BN_RETENCION_CONSULTAS_DIAS.",
    ),
    simular: bool = typer.Option(
        False, "--simular", help="Cuenta lo que borraría y no borra nada."
    ),
) -> None:
    """Aplica la retención de la traza de consultas (P-017, criterio 2).

    Va con el rol de administración: el lector de la API puede insertar su
    traza y no puede borrar la de nadie.
    """
    from backend_normativo.api.observabilidad import purgar

    with engine_migrador().begin() as conexion:
        resultado = purgar(conexion, dias=dias, simular=simular)
    verbo = "se borrarían" if resultado.simulada else "borradas"
    typer.echo(
        f"Retención: {resultado.dias} días · {verbo} {resultado.candidatas} · "
        f"quedan {resultado.quedan}"
    )
    # Las devoluciones caducan en la misma corrida. Se informan aparte porque
    # son otra tabla: si alguna vez este número queda en cero mientras la traza
    # se purga, lo que hay son señales huérfanas quedándose atrás.
    typer.echo(f"Devoluciones: {verbo} {resultado.devoluciones_candidatas}")
    if resultado.mas_antigua:
        typer.echo(f"La más antigua que queda es del {resultado.mas_antigua.date().isoformat()}.")


@operacion.command("purgar-sesiones")
def operacion_purgar_sesiones() -> None:
    """Borra las conversaciones vencidas (P-037, criterio 1).

    Leerlas también las borra, pero eso sólo alcanza para las que alguien vuelve
    a mirar. Una conversación abandonada no se lee nunca más y se quedaría con
    los hechos de una persona mucho más allá del plazo que la pantalla prometió:
    30 minutos de inactividad, dos horas de vida.
    """
    from backend_normativo.conversacion.sesion import INACTIVIDAD, VIDA_MAXIMA, purgar

    with engine_migrador().begin() as conexion:
        borradas = purgar(conexion)
    typer.echo(
        f"Conversaciones vencidas borradas: {borradas} "
        f"(inactividad {int(INACTIVIDAD.total_seconds() // 60)} min · "
        f"vida máxima {int(VIDA_MAXIMA.total_seconds() // 3600)} h)"
    )


@operacion.command("devoluciones")
def operacion_devoluciones(
    horas: int = typer.Option(24, help="Ventana a mirar, en horas."),
) -> None:
    """Qué contestó la gente sobre las respuestas que recibió (P-015).

    Es la única medición del sistema que no es sobre sí mismo. Todo lo demás
    —latencia, abstenciones, evidencias— puede estar en verde mientras cada
    persona que pregunta se va igual de perdida que como llegó.

    El denominador va siempre: cuatro devoluciones sobre cinco consultas y
    cuatro sobre mil son hallazgos distintos, y el segundo dice que el
    mecanismo no se está usando.
    """
    from backend_normativo.api.devoluciones import resumen as resumen_devoluciones

    with engine_migrador().connect() as conexion:
        medido = resumen_devoluciones(conexion, desde_horas=horas)

    typer.echo(
        f"Últimas {medido['periodo_horas']} h · {medido['devoluciones']} devoluciones "
        f"sobre {medido['consultas']} consultas"
    )
    for senal, cuantas in medido["por_senal"].items():
        typer.echo(f"  {senal:<15} {cuantas}")
    if not medido["por_resultado"]:
        typer.echo(
            "Nadie contestó todavía. Un cero acá no dice que las respuestas estén bien: "
            "dice que no se sabe."
        )
        return
    typer.echo("\nCon qué clase de respuesta se encontró cada señal:")
    for fila in medido["por_resultado"]:
        motivo = f" ({fila['motivo']})" if fila["motivo"] else ""
        typer.echo(f"  {fila['senal']:<15} {fila['resultado']}{motivo}: {fila['cuantas']}")


@curacion.command("fechar-verificacion")
def curacion_fechar_verificacion(
    actor: str = typer.Option(..., help="Quién queda registrado en cada versión."),
    tipo: list[str] = typer.Option(
        None, "--tipo", help="Limitar a estas familias. Por omisión, las cuatro."
    ),
    simular: bool = typer.Option(False, "--simular", help="Cuenta y no escribe nada."),
) -> None:
    """Sella `verificado_en` con la fecha de la captura que respalda cada dato.

    Es lo que le falta al dato operativo para poder publicarse: está aprobado
    desde hace tiempo y sin fecha de verificación, y la base se niega —con
    razón— a servir algo cuyo respaldo nadie fechó.

    La fecha significa que **en esa fecha la fuente oficial publicaba esto**. No
    significa que la oficina esté abierta ni que el teléfono atienda, y la
    pantalla lo dice con esas palabras. Lo que no llega a una captura no se
    sella: se cuenta y se informa.
    """
    from sqlalchemy import text as _text

    from backend_normativo.curacion.verificacion import fechar_desde_la_captura

    with engine_migrador().begin() as conexion:
        resultado = fechar_desde_la_captura(
            conexion, actor=actor, tipos=list(tipo) if tipo else None, simular=simular
        )
        if simular:
            conexion.execute(_text("ROLLBACK"))

    typer.echo("Simulación: no se escribió nada." if simular else "Hecho.")
    for familia in sorted(resultado.sellados):
        typer.echo(f"  {familia:<18} {resultado.sellados[familia]:>6} con fecha de captura")
    sin = {k: v for k, v in resultado.sin_captura.items() if v}
    if sin:
        typer.echo("Sin captura que las respalde, no se sellaron:")
        for familia, cuantas in sorted(sin.items()):
            typer.echo(f"  {familia:<18} {cuantas:>6}")
    typer.echo(f"Total: {resultado.total}")


@curacion.command("limpiar-marcado")
def curacion_limpiar_marcado(
    actor: str = typer.Option(..., help="Quién queda registrado en cada unidad."),
    fundamento: str = typer.Option(..., help="Por qué se toca el texto."),
    simular: bool = typer.Option(False, "--simular", help="Cuenta y no escribe nada."),
) -> None:
    """Saca el marcado HTML que quedó dentro de unidades ya extraídas.

    Aplica la misma limpieza que hace el extractor desde `extraccion@15`, así
    que el texto queda igual que si el documento se volviera a extraer. Sólo
    toca unidades de versiones que todavía no se publicaron: el texto de un
    corte publicado no se cambia.

    Las evidencias no se tocan —son inmutables y citan lo que la fuente
    publicó—, así que después de esto el fragmento citado ya no es un calco del
    texto de la unidad. El informe dice cuántas quedan así.
    """
    from sqlalchemy import text as _text

    from backend_normativo.curacion.marcado import limpiar

    try:
        with engine_migrador().begin() as conexion:
            resultado = limpiar(conexion, actor=actor, fundamento=fundamento, simular=simular)
            if simular:
                conexion.execute(_text("ROLLBACK"))
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    verbo = "se limpiarían" if simular else "limpiadas"
    typer.echo(f"Unidades con marcado: {resultado.unidades} · {verbo}: {resultado.limpiadas}")
    if resultado.evidencias_que_quedan_con_marcado:
        typer.echo(
            f"Evidencias que siguen citando el texto con marcado: "
            f"{resultado.evidencias_que_quedan_con_marcado}. Son inmutables y citan lo que "
            f"la fuente publicó; no es un error, es la divergencia esperada."
        )
    for aviso in resultado.avisos:
        typer.echo(f"  aviso: {aviso}")


@curacion.command("canales")
def curacion_canales(
    fuente: str | None = typer.Argument(None, help="Una fuente en particular. Por omisión, todas."),
    salida: Path | None = typer.Option(None, help="Archivo donde escribir la evidencia."),
) -> None:
    """Carga los canales de atención que publican las páginas institucionales.

    Un valor que no normaliza no se carga, y una fuente sin organismo declarado
    tampoco: deja incidencia con cuántos canales encontró.
    """
    from backend_normativo.curacion.canales import CuradorDeCanales
    from backend_normativo.curacion.canales import formatear as formatear_canales

    with engine_migrador().begin() as conexion:
        resultado = CuradorDeCanales(conexion).cargar(fuente)

    texto = formatear_canales(resultado)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n", encoding="utf-8")
        typer.echo(f"Evidencia escrita en {salida} · canales {resultado.creados}")
    else:
        typer.echo(texto)


# Va al final del archivo y no en el medio, que es donde estaba. Con el bloque a
# mitad de camino, `python -m backend_normativo.cli.main` ejecutaba la
# aplicación antes de que se registraran los comandos definidos más abajo —entre
# ellos `operacion purgar-consultas` y `operacion devoluciones`—, que
# contestaban «No such command». Por el entrypoint `bn` funcionaban, porque ahí
# el módulo se importa entero primero. Un comando que existe o no según cómo se
# lo invoque es peor que uno que falta.
if __name__ == "__main__":
    app()
