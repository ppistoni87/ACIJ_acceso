"""Un comando que existe o no según cómo se invoque el CLI.

`if __name__ == "__main__": app()` estaba a mitad del archivo, así que
`python -m backend_normativo.cli.main` levantaba la aplicación antes de que se
registraran los comandos definidos más abajo. Por el entrypoint `bn`
funcionaban, porque ahí el módulo se importa entero primero: el mismo comando
contestaba o no contestaba según con qué se lo llamara, y ninguna prueba lo
miraba.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize("grupo", ["operacion", "recuperacion", "curacion"])
def test_los_comandos_estan_todos_al_ejecutar_el_modulo(grupo: str) -> None:
    from backend_normativo.cli import main as modulo

    esperados = {c.name for c in getattr(modulo, grupo).registered_commands if c.name}
    salida = subprocess.run(
        [sys.executable, "-m", "backend_normativo.cli.main", grupo, "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # La ayuda de Typer corta los nombres largos en la columna; se compara sobre
    # el texto sin saltos ni relleno.
    plano = " ".join(salida.stdout.split())
    faltan = sorted(nombre for nombre in esperados if nombre not in plano)
    assert not faltan, f"{grupo}: no aparecen al correr con `python -m`: {faltan}"
