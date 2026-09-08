"""El nombre de una base no se puede parametrizar: va interpolado.

`CREATE DATABASE` y `DROP DATABASE` no aceptan un parámetro para el nombre, así
que la sentencia se arma interpolando. Dos comandos del CLI reciben ese nombre
por opción y uno de ellos borra la base antes de crearla: un nombre con comilla
doble cierra el identificador y lo que sigue se ejecuta.
"""

from __future__ import annotations

import pytest
import typer

from backend_normativo.cli.main import _base_valida


@pytest.mark.parametrize(
    "base",
    ["backend_normativo", "bn_ensayo_2026", "_temporal", "A1"],
)
def test_un_nombre_simple_se_acepta(base: str) -> None:
    assert _base_valida(base) == base


@pytest.mark.parametrize(
    "base",
    [
        'mala"; DROP DATABASE backend_normativo; --',
        "con espacio",
        "con-guion",
        "1empieza_con_digito",
        "",
        "punto.compuesto",
        "a" * 64,
    ],
)
def test_un_nombre_que_podria_cerrar_el_identificador_se_rechaza(base: str) -> None:
    with pytest.raises(typer.BadParameter, match="no es un nombre de base válido"):
        _base_valida(base)
