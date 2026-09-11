"""El informe de decisiones humanas pendientes.

«5.397 afirmaciones» no es una tarea: es un número que desalienta y no dice por
dónde agarrarlo. Lo que hace útil a este informe es que las cuenta por versión
—que es la unidad en la que se decide— y separa las que respaldan beneficios ya
firmados.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import Connection, text

from backend_normativo.calidad import pendientes_de_firma

pytestmark = pytest.mark.integracion


def _suma_de_tabla(fragmento: str) -> int:
    return sum(int(x) for x in re.findall(r"\| (\d+) \|", fragmento))


def test_las_afirmaciones_del_informe_cuadran_con_la_base(conexion: Connection) -> None:
    """El defecto que esta prueba fija: el LEFT JOIN a beneficios multiplicaba filas.

    Una norma con veinte beneficios colgando informaba veinte veces sus
    afirmaciones, y el informe decía 27.120 sobre un total real de 5.397. Un
    informe que exagera el trabajo pendiente desalienta tanto como uno que lo
    esconde.
    """
    esperado = conexion.execute(
        text("SELECT count(*) FROM afirmaciones WHERE estado_revision = 'CANDIDATE'")
    ).scalar_one()
    informe = pendientes_de_firma.construir(conexion)
    parte = informe.split("## Versiones sin intervalo")[0]
    assert _suma_de_tabla(parte) == esperado


def test_las_vigencias_del_informe_cuadran_con_la_base(conexion: Connection) -> None:
    esperado = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones "
            " WHERE release_id IS NULL AND valid_tipo = 'DESCONOCIDO'"
        )
    ).scalar_one()
    informe = pendientes_de_firma.construir(conexion)
    parte = informe.split("## Versiones sin intervalo")[1]
    assert _suma_de_tabla(parte) == esperado


def test_el_informe_cuenta_versiones_y_no_solo_afirmaciones(conexion: Connection) -> None:
    """La unidad de decisión es la versión: `aprobar-campos` se invoca por versión."""
    informe = pendientes_de_firma.construir(conexion)
    assert "versiones**" in informe
    assert "aprobar-campos" in informe or "Sin afirmaciones" in informe


def test_el_informe_no_trae_cifras_escritas_a_mano(conexion: Connection) -> None:
    """Se genera dos veces y da lo mismo: nada depende del momento en que corrió."""
    uno = pendientes_de_firma.construir(conexion)
    otro = pendientes_de_firma.construir(conexion)
    assert uno == otro
