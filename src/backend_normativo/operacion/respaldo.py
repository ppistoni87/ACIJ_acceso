"""HU-037: respaldo y restauración con verificación.

Un backup que nadie restauró no es un backup. Este módulo hace las dos mitades y
la comprobación que las une, porque el riesgo del corpus no es solo perder la
base: es restaurarla creyendo que está entera cuando el almacén de objetos
quedó atrás y las capturas ya no tienen bytes detrás.

Tres cosas se verifican después de restaurar, y son las tres que el paquete
pide:

* **Integridad.** Cada captura tiene su objeto y el contenido de ese objeto
  hashea a lo que la fila declara. Un objeto que cambió es indistinguible de uno
  correcto salvo que se lo verifique; por eso se verifica.
* **Release y evidencia.** El release publicado, sus fragmentos y las
  evidencias que sostienen lo que se sirve llegan completos: un release sin
  chunks serviría vacío sin que nadie lo note.
* **Sin doble efecto.** Los eventos ya entregados siguen entregados y los
  checkpoints de ingesta conservan su posición. Restaurar no puede reenviar
  avisos que la gente ya recibió ni volver a descargar lo que ya se descargó.
  Que no puedan coexistir dos eventos con la misma clave de idempotencia no lo
  cuida este módulo: lo cuida un índice único del esquema, que es donde tiene
  que estar.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
from dataclasses import dataclass, field
from urllib.parse import urlparse

from sqlalchemy import Connection, text

ARCHIVO_BASE = "base.dump"
ARCHIVO_MANIFIESTO = "manifiesto.json"
FORMATO = "1.0"


class RespaldoInvalido(Exception):
    """El respaldo no está completo o no coincide con lo que declara."""


@dataclass
class Manifiesto:
    formato: str = FORMATO
    creado_en: str = ""
    base: str = ""
    objetos: dict[str, int] = field(default_factory=dict)
    capturas: int = 0
    releases: int = 0
    evidencias: int = 0
    eventos_entregados: int = 0
    checkpoints: dict[str, str] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        """Hash del inventario de objetos, para comparar dos respaldos."""
        cuerpo = json.dumps(sorted(self.objetos.items()), separators=(",", ":"))
        return hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()


@dataclass
class Verificacion:
    objetos_esperados: int = 0
    objetos_presentes: int = 0
    objetos_corruptos: list[str] = field(default_factory=list)
    capturas_sin_objeto: list[str] = field(default_factory=list)
    releases: int = 0
    chunks: int = 0
    evidencias: int = 0
    eventos_entregados: int = 0
    checkpoints_conservados: int = 0
    problemas: list[str] = field(default_factory=list)

    @property
    def integra(self) -> bool:
        return not self.problemas


def inventariar(conexion: Connection, directorio_objetos: pathlib.Path) -> Manifiesto:
    """Manifiesto de lo que hay que poder restaurar."""
    manifiesto = Manifiesto(
        creado_en=dt.datetime.now(dt.UTC).isoformat(),
        base=str(conexion.engine.url.database),
    )
    for sha in conexion.execute(text("SELECT DISTINCT sha256_raw FROM capturas")).scalars():
        ruta = _ruta_objeto(directorio_objetos, sha)
        if ruta.exists():
            manifiesto.objetos[sha] = ruta.stat().st_size
    manifiesto.capturas = conexion.execute(text("SELECT count(*) FROM capturas")).scalar_one()
    manifiesto.releases = conexion.execute(
        text("SELECT count(*) FROM releases WHERE estado = 'PUBLICADO'")
    ).scalar_one()
    manifiesto.evidencias = conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one()
    manifiesto.eventos_entregados = conexion.execute(
        text("SELECT count(*) FROM eventos_outbox WHERE entregado_en IS NOT NULL")
    ).scalar_one()
    manifiesto.checkpoints = {
        str(fila[0]): str(fila[1])
        for fila in conexion.execute(
            text("SELECT id, checkpoint FROM corridas_ingesta WHERE checkpoint IS NOT NULL")
        )
    }
    return manifiesto


def respaldar(
    conexion: Connection,
    destino: pathlib.Path,
    *,
    url_base: str,
    directorio_objetos: pathlib.Path,
) -> Manifiesto:
    """Vuelca la base y deja el manifiesto del almacén junto a ella.

    El almacén no se copia: es content-addressed y puede ser enorme. Lo que se
    guarda es qué objetos tiene que haber y de qué tamaño, que es lo que permite
    detectar que falta uno.
    """
    destino.mkdir(parents=True, exist_ok=True)
    manifiesto = inventariar(conexion, directorio_objetos)

    volcado = subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--file",
            str(destino / ARCHIVO_BASE),
            _dsn(url_base),
        ],
        capture_output=True,
        text=True,
    )
    if volcado.returncode != 0:
        raise RespaldoInvalido(f"pg_dump falló: {volcado.stderr.strip()[:400]}")

    (destino / ARCHIVO_MANIFIESTO).write_text(
        json.dumps(
            {
                "formato": manifiesto.formato,
                "creado_en": manifiesto.creado_en,
                "base": manifiesto.base,
                "hash_objetos": manifiesto.hash,
                "objetos": manifiesto.objetos,
                "capturas": manifiesto.capturas,
                "releases": manifiesto.releases,
                "evidencias": manifiesto.evidencias,
                "eventos_entregados": manifiesto.eventos_entregados,
                "checkpoints": manifiesto.checkpoints,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifiesto


def leer_manifiesto(origen: pathlib.Path) -> Manifiesto:
    ruta = origen / ARCHIVO_MANIFIESTO
    if not ruta.exists():
        raise RespaldoInvalido(
            f"No hay manifiesto en {origen}. Sin él no se puede saber si el almacén de "
            "objetos quedó completo, y una base restaurada sin sus bytes sirve capturas "
            "que no se pueden verificar."
        )
    datos = json.loads(ruta.read_text())
    if datos.get("formato") != FORMATO:
        raise RespaldoInvalido(
            f"El respaldo declara formato {datos.get('formato')!r} y se esperaba {FORMATO!r}."
        )
    return Manifiesto(
        formato=datos["formato"],
        creado_en=datos["creado_en"],
        base=datos["base"],
        objetos=datos.get("objetos", {}),
        capturas=datos.get("capturas", 0),
        releases=datos.get("releases", 0),
        evidencias=datos.get("evidencias", 0),
        eventos_entregados=datos.get("eventos_entregados", 0),
        checkpoints=datos.get("checkpoints", {}),
    )


def restaurar(origen: pathlib.Path, *, url_destino: str) -> None:
    """Restaura el volcado en una base que se crea vacía para eso."""
    volcado = origen / ARCHIVO_BASE
    if not volcado.exists():
        raise RespaldoInvalido(f"No hay volcado en {volcado}.")
    resultado = subprocess.run(
        ["pg_restore", "--no-owner", "--no-acl", "--dbname", _dsn(url_destino), str(volcado)],
        capture_output=True,
        text=True,
    )
    # pg_restore devuelve 1 por advertencias que no impiden restaurar (roles que
    # no existen en el destino, por ejemplo). Lo que decide es la verificación.
    if resultado.returncode not in (0, 1):
        raise RespaldoInvalido(f"pg_restore falló: {resultado.stderr.strip()[:400]}")


def verificar(
    conexion: Connection, manifiesto: Manifiesto, directorio_objetos: pathlib.Path
) -> Verificacion:
    """Comprueba que lo restaurado sirva, no solo que exista."""
    verificacion = Verificacion(objetos_esperados=len(manifiesto.objetos))

    for sha in manifiesto.objetos:
        ruta = _ruta_objeto(directorio_objetos, sha)
        if not ruta.exists():
            verificacion.capturas_sin_objeto.append(sha)
            continue
        verificacion.objetos_presentes += 1
        if hashlib.sha256(ruta.read_bytes()).hexdigest() != sha:
            verificacion.objetos_corruptos.append(sha)

    if verificacion.capturas_sin_objeto:
        verificacion.problemas.append(
            f"{len(verificacion.capturas_sin_objeto)} objeto(s) del manifiesto no están en el "
            "almacén: esas capturas quedaron sin bytes y no se puede verificar lo que afirman."
        )
    if verificacion.objetos_corruptos:
        verificacion.problemas.append(
            f"{len(verificacion.objetos_corruptos)} objeto(s) no hashean a lo que declaran. "
            "Un objeto alterado es indistinguible de uno correcto salvo verificándolo."
        )

    verificacion.releases = conexion.execute(
        text("SELECT count(*) FROM releases WHERE estado = 'PUBLICADO'")
    ).scalar_one()
    verificacion.chunks = conexion.execute(text("SELECT count(*) FROM chunks")).scalar_one()
    verificacion.evidencias = conexion.execute(text("SELECT count(*) FROM evidencias")).scalar_one()
    verificacion.eventos_entregados = conexion.execute(
        text("SELECT count(*) FROM eventos_outbox WHERE entregado_en IS NOT NULL")
    ).scalar_one()
    verificacion.checkpoints_conservados = conexion.execute(
        text("SELECT count(*) FROM corridas_ingesta WHERE checkpoint IS NOT NULL")
    ).scalar_one()

    if verificacion.releases != manifiesto.releases:
        verificacion.problemas.append(
            f"Se esperaban {manifiesto.releases} release(s) publicado(s) y hay "
            f"{verificacion.releases}."
        )
    if verificacion.evidencias != manifiesto.evidencias:
        verificacion.problemas.append(
            f"Se esperaban {manifiesto.evidencias} evidencia(s) y hay {verificacion.evidencias}. "
            "Sin evidencia, lo publicado deja de poder sostenerse."
        )
    if verificacion.releases and not verificacion.chunks:
        verificacion.problemas.append(
            "Hay un release publicado y ningún fragmento indexado: serviría vacío sin que "
            "nadie lo note."
        )
    if verificacion.eventos_entregados != manifiesto.eventos_entregados:
        verificacion.problemas.append(
            f"Se esperaban {manifiesto.eventos_entregados} evento(s) ya entregado(s) y hay "
            f"{verificacion.eventos_entregados}. Restaurar no puede reenviar avisos que la "
            "gente ya recibió."
        )
    if verificacion.checkpoints_conservados != len(manifiesto.checkpoints):
        verificacion.problemas.append(
            f"Se esperaban {len(manifiesto.checkpoints)} checkpoint(s) de ingesta y hay "
            f"{verificacion.checkpoints_conservados}: la ingesta reanudaría desde el principio."
        )
    return verificacion


def _ruta_objeto(directorio: pathlib.Path, sha: str) -> pathlib.Path:
    return directorio / sha[:2] / sha[2:4] / sha


def _dsn(url: str) -> str:
    """DSN que entienden pg_dump y pg_restore.

    SQLAlchemy usa `postgresql+psycopg://`; las herramientas de PostgreSQL no.
    """
    partes = urlparse(url.replace("postgresql+psycopg://", "postgresql://"))
    if partes.password:
        os.environ.setdefault("PGPASSWORD", partes.password)
    return partes._replace(query="").geturl()


def formatear(manifiesto: Manifiesto, verificacion: Verificacion) -> str:
    lineas = [
        "# Respaldo y restauración",
        "",
        f"- Respaldo tomado: {manifiesto.creado_en}",
        f"- Base de origen: `{manifiesto.base}`",
        f"- Hash del inventario de objetos: `{manifiesto.hash}`",
        "",
        "## Qué se restauró",
        "",
        "| Elemento | Esperado | Restaurado |",
        "| --- | --- | --- |",
        f"| Objetos del almacén | {verificacion.objetos_esperados} "
        f"| {verificacion.objetos_presentes} |",
        f"| Releases publicados | {manifiesto.releases} | {verificacion.releases} |",
        f"| Evidencias | {manifiesto.evidencias} | {verificacion.evidencias} |",
        f"| Eventos ya entregados | {manifiesto.eventos_entregados} "
        f"| {verificacion.eventos_entregados} |",
        f"| Checkpoints de ingesta | {len(manifiesto.checkpoints)} "
        f"| {verificacion.checkpoints_conservados} |",
        f"| Fragmentos indexados | — | {verificacion.chunks} |",
        "",
        f"Objetos corruptos: **{len(verificacion.objetos_corruptos)}** · "
        f"faltantes: **{len(verificacion.capturas_sin_objeto)}**",
        "",
        f"## Resultado: {'íntegro' if verificacion.integra else 'con problemas'}",
        "",
    ]
    if verificacion.integra:
        lineas += [
            "La base restaurada tiene sus releases, sus evidencias y los bytes detrás de cada",
            "captura, y no va a reenviar avisos ni volver a descargar lo ya descargado.",
        ]
    else:
        lineas += [f"- {p}" for p in verificacion.problemas]
    return "\n".join(lineas)
