"""Sondas de readiness y liveness (P-019, criterio 2).

Están separadas a propósito, y la diferencia no es cosmética: **liveness**
contesta si el proceso sigue vivo y **readiness** si esta instancia puede
servir. Mezclarlas hace que una base momentáneamente inalcanzable reinicie
procesos sanos, que es la forma más rápida de convertir una caída de la base en
una caída total.

Por eso liveness no toca la base. Y por eso readiness sí: una sonda que
devuelve `ok` sin mirar nada —como la que había— declara sana a una instancia
que no puede contestar una sola consulta, y el orquestador le manda tráfico.

En producción readiness exige además que haya un corte publicado. Sin release,
la API no puede servir ninguna proyección: contesta abstenciones correctas y
vacías. Eso está bien en desarrollo y no está bien como instancia recibiendo
gente que pregunta por sus derechos.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo import SCHEMA_VERSION, __version__

# El entorno donde la exigencia es máxima. El nombre viene de `BN_ENTORNO`.
ENTORNO_PRODUCCION = "produccion"


@dataclass
class Verificacion:
    nombre: str
    pasa: bool
    detalle: str


@dataclass
class Readiness:
    listo: bool
    entorno: str
    schema_version: str = SCHEMA_VERSION
    version: str = __version__
    verificaciones: list[Verificacion] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {
            "listo": self.listo,
            "entorno": self.entorno,
            "schema_version": self.schema_version,
            "version": self.version,
            "verificaciones": [
                {"nombre": v.nombre, "pasa": v.pasa, "detalle": v.detalle}
                for v in self.verificaciones
            ],
        }


def cabeza_esperada() -> str | None:
    """La revisión de migraciones que este código sabe aplicar.

    Sale de los archivos de migración que viajan en la imagen, no de una
    constante escrita a mano: una constante envejece en silencio, y este
    proyecto ya se tropezó una vez con un número de migración desactualizado.
    """
    import pathlib
    import re

    directorio = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "versions"
    if not directorio.is_dir():
        return None

    revisiones: dict[str, str | None] = {}
    for archivo in directorio.glob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        revision = re.search(r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)", texto, re.M)
        anterior = re.search(r"^down_revision(?::\s*[^=]+)?\s*=\s*['\"]([^'\"]+)", texto, re.M)
        if revision:
            revisiones[revision.group(1)] = anterior.group(1) if anterior else None

    if not revisiones:
        return None
    # La cabeza es la revisión a la que ninguna otra apunta como anterior.
    apuntadas = {a for a in revisiones.values() if a}
    cabezas = [r for r in revisiones if r not in apuntadas]
    return cabezas[0] if len(cabezas) == 1 else None


def verificar_abriendo(abrir, *, entorno: str) -> Readiness:
    """Readiness incluyendo la apertura de la conexión.

    La apertura entra acá y no en una dependencia del framework porque una base
    inalcanzable hace fallar la dependencia **antes** de que la sonda corra: el
    servicio devolvía 500 y no alcanzaba a decir qué estaba mal, que es
    justamente lo que un readiness tiene que contestar. Un orquestador lee 503
    como «no le mandes tráfico» y 500 como «algo se rompió»; acá lo correcto es
    lo primero.
    """
    try:
        with abrir() as conexion:
            return verificar(conexion, entorno=entorno)
    except Exception as error:
        return Readiness(
            listo=False,
            entorno=entorno,
            verificaciones=[
                Verificacion(
                    "conexion",
                    False,
                    f"No se pudo abrir una conexión a la base: {type(error).__name__}.",
                )
            ],
        )


def verificar(conexion: Connection, *, entorno: str) -> Readiness:
    """Si esta instancia puede servir, y por qué no cuando no puede."""
    verificaciones: list[Verificacion] = []

    try:
        conexion.execute(text("SELECT 1"))
        verificaciones.append(Verificacion("conexion", True, "La base responde."))
    except Exception as error:  # la excepción es el resultado de la sonda
        verificaciones.append(
            Verificacion("conexion", False, f"La base no responde: {type(error).__name__}.")
        )
        return Readiness(listo=False, entorno=entorno, verificaciones=verificaciones)

    esperada = cabeza_esperada()
    # «No hay migración» y «no pude leer cuál hay» son diagnósticos opuestos y
    # se informan distinto. Cuando esto atrapaba todo y devolvía `None`, la
    # sonda dijo que la base no tenía ninguna migración cuando lo que pasaba era
    # que el rol de lectura no alcanza `alembic_version`: mandaba a revisar la
    # base cuando el problema era un permiso.
    aplicada: str | None = None
    fallo_lectura: str | None = None
    try:
        aplicada = conexion.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    except Exception as error:
        fallo_lectura = type(error).__name__

    if fallo_lectura is not None:
        verificaciones.append(
            Verificacion(
                "esquema",
                False,
                f"No se pudo leer `alembic_version` ({fallo_lectura}): la instancia no puede "
                "comprobar contra qué esquema está sirviendo. Suele ser un permiso que falta, "
                "no una migración que falta.",
            )
        )
    elif esperada is None:
        verificaciones.append(
            Verificacion(
                "esquema",
                False,
                "No se pudo determinar qué migración espera este código.",
            )
        )
    elif aplicada == esperada:
        verificaciones.append(Verificacion("esquema", True, f"En {aplicada}."))
    else:
        verificaciones.append(
            Verificacion(
                "esquema",
                False,
                f"La base está en {aplicada or 'ninguna migración'} y este código espera "
                f"{esperada}. Servir con el esquema equivocado devuelve errores que parecen "
                "datos faltantes.",
            )
        )

    if entorno == ENTORNO_PRODUCCION:
        publicados = conexion.execute(
            text("SELECT count(*) FROM releases WHERE estado = 'PUBLICADO'")
        ).scalar_one()
        if publicados:
            verificaciones.append(
                Verificacion("corte", True, f"{publicados} corte(s) publicado(s).")
            )
        else:
            verificaciones.append(
                Verificacion(
                    "corte",
                    False,
                    "No hay ningún corte publicado. La instancia contestaría abstenciones "
                    "correctas y vacías a todo el mundo.",
                )
            )

    return Readiness(
        listo=all(v.pasa for v in verificaciones),
        entorno=entorno,
        verificaciones=verificaciones,
    )
