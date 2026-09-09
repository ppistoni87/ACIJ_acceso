"""Generador de carga. Corre como proceso aparte de la API, a propósito.

Se invoca desde `escalado.py` con `puerto clientes segundos` y escribe una línea
JSON. Vive como archivo separado porque tiene que ser otro proceso: si el
cliente comparte intérprete con el servidor, lo que se mide es cómo se reparten
ese intérprete y no cuánto sostiene la API.
"""

from __future__ import annotations

import json
import statistics
import sys
import threading
import time
import urllib.parse
import urllib.request

CONSULTAS = (
    ("/v1/normas", {"limite": "20"}),
    ("/v1/normas", {"q": "asignación familiar", "limite": "20"}),
    ("/v1/beneficios", {}),
    ("/v1/puntos-atencion", {}),
    ("/v1/cobertura", {}),
)


def main() -> int:
    puerto, clientes, segundos = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    base = f"http://127.0.0.1:{puerto}"
    demoras: list[float] = []
    errores = 0
    candado = threading.Lock()
    fin = time.monotonic() + segundos

    def cliente(indice: int) -> None:
        nonlocal errores
        propias: list[float] = []
        fallas = 0
        vuelta = indice
        while time.monotonic() < fin:
            ruta, params = CONSULTAS[vuelta % len(CONSULTAS)]
            vuelta += 1
            url = base + ruta + ("?" + urllib.parse.urlencode(params) if params else "")
            arranque = time.perf_counter()
            try:
                with urllib.request.urlopen(url, timeout=30) as respuesta:
                    respuesta.read()
                    if not 200 <= respuesta.status < 300:
                        fallas += 1
            except Exception:
                fallas += 1
            propias.append((time.perf_counter() - arranque) * 1000)
        with candado:
            demoras.extend(propias)
            errores += fallas

    arranque = time.perf_counter()
    hilos = [threading.Thread(target=cliente, args=(i,)) for i in range(clientes)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    duracion = time.perf_counter() - arranque

    ordenadas = sorted(demoras)
    p95 = ordenadas[min(len(ordenadas) - 1, int(len(ordenadas) * 0.95))] if ordenadas else 0.0
    print(
        json.dumps(
            {
                "peticiones": len(demoras),
                "errores": errores,
                "duracion_s": round(duracion, 3),
                "p95_ms": round(p95, 2),
                "p50_ms": round(statistics.median(ordenadas), 2) if ordenadas else 0.0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
