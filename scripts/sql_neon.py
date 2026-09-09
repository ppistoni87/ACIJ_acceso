#!/usr/bin/env python3
"""Ejecuta SQL contra Neon por su endpoint HTTPS `/sql`.

Por qué existe. El contenedor donde corre el agente no tiene egreso TCP al
puerto 5432: la política del proxy declara las bases por TCP crudo como no
soportadas. Neon publica además un endpoint HTTP oficial sobre el mismo
motor, en 443 y con TLS validado de punta a punta. Este script lo usa para
aplicar migraciones y verificar el esquema desde ese entorno. No desactiva
ninguna verificación de certificados ni rota identidades.

Donde haya conexión TCP —Cloud Run, una laptop, el runner de CI— se usa
`alembic upgrade head` y `psql` como siempre; este camino no los reemplaza.

Uso:
    NEON_DSN='postgresql://usuario:clave@host/base?sslmode=require' \
        python scripts/sql_neon.py archivo.sql [--transaccion]
    NEON_DSN=... python scripts/sql_neon.py -c "select 1"

`NEON_DSN` se lee del entorno: ninguna credencial vive en este archivo.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

TIEMPO_SENTENCIA_S = 120
TIEMPO_TRANSACCION_S = 600
NO_TRANSACCIONALES = {"BEGIN", "COMMIT", "END", "ROLLBACK"}


def _endpoint(dsn: str) -> str:
    coincidencia = re.search(r"@([^/@]+)/", dsn)
    if not coincidencia:
        raise SystemExit("NEON_DSN no tiene la forma postgresql://usuario:clave@host/base")
    return f"https://{coincidencia.group(1)}/sql"


def separar(sql: str) -> list[str]:
    """Parte un script en sentencias respetando comentarios, comillas y $tag$.

    No alcanza con partir por `;`: los cuerpos de función van entre `$$` y
    contienen puntos y coma propios. Partirlos rompería la migración 0002.
    """
    sentencias: list[str] = []
    actual: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        caracter = sql[i]
        if sql[i : i + 2] == "--":
            fin = sql.find("\n", i)
            i = n if fin == -1 else fin + 1
            continue
        if caracter == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if sql[j + 1 : j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            actual.append(sql[i : j + 1])
            i = j + 1
            continue
        if caracter == "$":
            marca = re.match(r"\$[A-Za-z_0-9]*\$", sql[i:])
            if marca:
                etiqueta = marca.group(0)
                fin = sql.find(etiqueta, i + len(etiqueta))
                if fin == -1:
                    raise ValueError(f"cuerpo {etiqueta} sin cerrar")
                fin += len(etiqueta)
                actual.append(sql[i:fin])
                i = fin
                continue
        if caracter == ";":
            texto = "".join(actual).strip()
            if texto:
                sentencias.append(texto)
            actual = []
            i += 1
            continue
        actual.append(caracter)
        i += 1
    texto = "".join(actual).strip()
    if texto:
        sentencias.append(texto)
    return sentencias


def _pedir(dsn: str, cuerpo: dict, cabeceras: dict[str, str], espera: int) -> dict:
    pedido = urllib.request.Request(
        _endpoint(dsn),
        data=json.dumps(cuerpo).encode(),
        headers={
            "Neon-Connection-String": dsn,
            "Neon-Raw-Text-Output": "true",
            "Content-Type": "application/json",
            **cabeceras,
        },
        method="POST",
    )
    with urllib.request.urlopen(pedido, timeout=espera) as respuesta:
        return json.loads(respuesta.read())


def ejecutar(dsn: str, consulta: str) -> dict:
    """Una sentencia, en su propia transacción implícita."""
    return _pedir(dsn, {"query": consulta, "params": []}, {}, TIEMPO_SENTENCIA_S)


def en_transaccion(dsn: str, sentencias: list[str]) -> dict:
    """Todas las sentencias o ninguna: un esquema a medio aplicar no sirve."""
    return _pedir(
        dsn,
        {"queries": [{"query": s, "params": []} for s in sentencias]},
        {"Neon-Batch-Isolation-Level": "Serializable"},
        TIEMPO_TRANSACCION_S,
    )


def _detalle(error: urllib.error.HTTPError) -> str:
    crudo = error.read().decode(errors="replace")
    try:
        return json.loads(crudo).get("message", crudo)
    except json.JSONDecodeError:
        return crudo


def main(argumentos: list[str]) -> int:
    dsn = os.environ.get("NEON_DSN", "").strip()
    if not dsn:
        print("Falta NEON_DSN en el entorno.", file=sys.stderr)
        return 2
    atomico = "--transaccion" in argumentos
    argumentos = [a for a in argumentos if a != "--transaccion"]
    if not argumentos:
        print(__doc__, file=sys.stderr)
        return 2
    if argumentos[0] == "-c":
        texto = argumentos[1]
    else:
        with open(argumentos[0], encoding="utf-8") as archivo:
            texto = archivo.read()

    sentencias = separar(texto)
    if atomico:
        sentencias = [s for s in sentencias if s.upper() not in NO_TRANSACCIONALES]
        print(f"{len(sentencias)} sentencias en una transacción", file=sys.stderr)
        try:
            en_transaccion(dsn, sentencias)
        except urllib.error.HTTPError as error:
            print(f"FALLA: {_detalle(error)}", file=sys.stderr)
            return 1
        print("OK: aplicadas", file=sys.stderr)
        return 0

    for numero, sentencia in enumerate(sentencias, 1):
        try:
            resultado = ejecutar(dsn, sentencia)
        except urllib.error.HTTPError as error:
            print(f"FALLA en la sentencia {numero}:\n{sentencia[:400]}", file=sys.stderr)
            print(_detalle(error), file=sys.stderr)
            return 1
        if resultado.get("rows"):
            print(json.dumps(resultado["rows"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
