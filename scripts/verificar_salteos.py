"""Un salteo se cuenta como éxito, así que tiene que ser una decisión.

Sin base de datos la suite se saltea casi a la mitad y pytest termina en cero.
Eso ya lo impide `tests/conftest.py`, que falla en vez de saltear. Este control
cubre lo otro: que ninguna prueba deje de correr por un motivo que nadie
declaró.

Los únicos salteos admitidos son los que el proyecto declara por marca —red
externa, corridas largas—. Cualquier otro es una prueba que dejó de ejecutarse
sin que se haya decidido, y el trabajo falla con el inventario de cuáles son.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Motivos declarados. Se comparan en minúsculas y por inclusión: el mensaje de
# pytest agrega el archivo y la línea alrededor del texto de la marca.
MOTIVOS_ADMITIDOS = (
    "bn_pruebas_sin_base",
    "requiere red",
    "prueba lenta",
    "necesita red externa",
)


def main(ruta: Path) -> int:
    if not ruta.exists():
        print(f"No hay reporte de pruebas en {ruta}: no se puede verificar qué corrió.")
        return 1

    raiz = ET.parse(ruta).getroot()
    sin_declarar: list[tuple[str, str]] = []
    declarados = 0
    for caso in raiz.iter("testcase"):
        for salteo in caso.findall("skipped"):
            motivo = (salteo.get("message") or "").strip()
            if any(admitido in motivo.lower() for admitido in MOTIVOS_ADMITIDOS):
                declarados += 1
                continue
            nombre = f"{caso.get('classname', '')}::{caso.get('name', '')}"
            sin_declarar.append((nombre, motivo))

    if declarados:
        print(f"{declarados} salteo(s) con motivo declarado.")
    if not sin_declarar:
        print("Ninguna prueba se salteó sin motivo declarado.")
        return 0

    print(f"{len(sin_declarar)} prueba(s) se saltearon sin un motivo declarado:")
    for nombre, motivo in sin_declarar:
        print(f"  {nombre} — {motivo or 'sin mensaje'}")
    print(
        "\nUn salteo se cuenta como éxito. Si la exclusión es deliberada, se declara con una "
        "marca del proyecto y se agrega su motivo a MOTIVOS_ADMITIDOS; si no, es una prueba que "
        "dejó de correr."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "resultados/pruebas.xml")))
