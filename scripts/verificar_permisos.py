#!/usr/bin/env python3
"""Comprueba, contra la base real, que cada rol pueda lo que debe y nada más.

Los GRANT de la migración 0002 declaran la intención; esto verifica el
resultado. La diferencia importa: un rol puede quedar con más permiso del
declarado por herencia, por un default privilege o por una tabla agregada
después sin revisar los grants.

Cada sonda se escribe de forma que no cambie nada: los `UPDATE` e `INSERT`
llevan `WHERE false`, y PostgreSQL igual verifica el permiso antes de
ejecutar. Así una corrida contra producción es inocua.

Uso:
    python scripts/verificar_permisos.py            # lee el entorno
    python scripts/verificar_permisos.py --transporte http

Lee `BN_DATABASE_URL_API` y `BN_DATABASE_URL_INGESTA` del entorno. Sin
credenciales en el archivo.
"""

from __future__ import annotations

import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PERMITIDO = "permitido"
DENEGADO = "denegado"

# Qué se espera de cada rol. El lector de la API no ve staging: ni capturas,
# ni afirmaciones, ni incidencias, ni corridas. El ingestor ve todo pero solo
# escribe descubrimiento; no publica un release ni aprueba una regla.
SONDAS: dict[str, list[tuple[str, str, str]]] = {
    "BN_DATABASE_URL_API": [
        (PERMITIDO, "leer normas publicadas", "select 1 from norma_versiones where false"),
        (PERMITIDO, "leer reglas", "select 1 from reglas where false"),
        (PERMITIDO, "leer parámetros", "select 1 from parametro_valores where false"),
        (
            PERMITIDO,
            "auditar su consulta",
            "insert into consultas_auditadas (id) select gen_random_uuid() where false",
        ),
        (DENEGADO, "leer capturas (staging)", "select 1 from capturas where false"),
        (DENEGADO, "leer afirmaciones (staging)", "select 1 from afirmaciones where false"),
        (DENEGADO, "leer incidencias (staging)", "select 1 from incidencias_revision where false"),
        (DENEGADO, "leer corridas (staging)", "select 1 from corridas_ingesta where false"),
        (DENEGADO, "escribir normas", "update normas set titulo = titulo where false"),
        (
            DENEGADO,
            "escribir reglas",
            "update reglas set estado_revision = estado_revision where false",
        ),
        (
            DENEGADO,
            "publicar un release",
            "insert into releases (id) select gen_random_uuid() where false",
        ),
        (DENEGADO, "leer los turnos del ciclo", "select 1 from arrendamientos where false"),
    ],
    "BN_DATABASE_URL_INGESTA": [
        (PERMITIDO, "leer capturas", "select 1 from capturas where false"),
        (
            PERMITIDO,
            "escribir capturas",
            "insert into capturas (id) select gen_random_uuid() where false",
        ),
        (
            PERMITIDO,
            "escribir fuentes candidatas",
            "insert into fuentes_candidatas (id) select gen_random_uuid() where false",
        ),
        (
            PERMITIDO,
            "registrar auditoría",
            "insert into auditoria_eventos (id) select gen_random_uuid() where false",
        ),
        (
            DENEGADO,
            "publicar un release",
            "insert into releases (id) select gen_random_uuid() where false",
        ),
        (
            DENEGADO,
            "aprobar una regla",
            "update reglas set estado_revision = estado_revision where false",
        ),
        (
            PERMITIDO,
            "tomar el turno del ciclo",
            "insert into arrendamientos (recurso) select 'x' where false",
        ),
        (
            PERMITIDO,
            "soltar el turno del ciclo",
            "update arrendamientos set vence_en = vence_en where false",
        ),
        (
            DENEGADO,
            "resolver una incidencia",
            "update incidencias_revision set estado = estado where false",
        ),
        (
            DENEGADO,
            "borrar la constancia de un turno",
            "delete from arrendamientos where false",
        ),
    ],
}


def _es_permiso_denegado(mensaje: str) -> bool:
    texto = mensaje.lower()
    return "permission denied" in texto or "permiso denegado" in texto


def _ejecutor_http(url: str):
    import sql_neon

    dsn = url.replace("postgresql+psycopg://", "postgresql://")

    def correr(consulta: str) -> str | None:
        try:
            sql_neon.ejecutar(dsn, consulta)
        except urllib.error.HTTPError as error:
            return sql_neon._detalle(error)
        return None

    return correr


def _ejecutor_tcp(url: str):
    import psycopg

    dsn = url.replace("postgresql+psycopg://", "postgresql://")

    def correr(consulta: str) -> str | None:
        try:
            with psycopg.connect(dsn, connect_timeout=20) as conexion:
                conexion.execute(consulta)
                conexion.rollback()
        except Exception as error:  # el mensaje del motor es el resultado de la sonda
            return str(error)
        return None

    return correr


def main(argumentos: list[str]) -> int:
    transporte = "tcp"
    if "--transporte" in argumentos:
        transporte = argumentos[argumentos.index("--transporte") + 1]
    fabrica = _ejecutor_http if transporte == "http" else _ejecutor_tcp

    fallas = 0
    revisados = 0
    for variable, sondas in SONDAS.items():
        url = os.environ.get(variable, "").strip()
        if not url:
            print(f"{variable}: sin definir — no se verifica.")
            fallas += 1
            continue
        print(f"\n{variable}")
        correr = fabrica(url)
        for esperado, descripcion, consulta in sondas:
            error = correr(consulta)
            if error is None:
                obtenido = PERMITIDO
            elif _es_permiso_denegado(error):
                obtenido = DENEGADO
            else:
                print(f"  ?  {descripcion}: la sonda falló por otra causa: {error.strip()[:160]}")
                fallas += 1
                revisados += 1
                continue
            revisados += 1
            if obtenido == esperado:
                print(f"  ok {descripcion}: {obtenido}")
            else:
                print(f"  MAL {descripcion}: se esperaba {esperado} y quedó {obtenido}")
                fallas += 1

    print(f"\n{revisados} sondas, {fallas} discrepancias.")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
