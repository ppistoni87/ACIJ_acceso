"""HU-039: el diccionario de datos se genera desde los modelos.

Un documento generado que cambia solo por volver a generarlo no se puede
comparar contra el anterior: cada regeneración ensucia el diff y esconde el
cambio real de esquema entre el ruido.
"""

from __future__ import annotations

import re

from backend_normativo.db.diccionario import construir, formatear


def test_dos_corridas_dan_el_mismo_diccionario() -> None:
    """El orden de las restricciones venía de un conjunto y cambiaba por corrida."""
    assert formatear(construir()) == formatear(construir())


def test_ninguna_direccion_de_memoria_llega_al_documento() -> None:
    """Una columna calculada traía el `repr` de su `Computed`, con el id del objeto.

    Además de cambiar en cada corrida, el número no le dice nada a nadie: lo
    que hay que poder leer es la expresión que calcula la columna.
    """
    texto = formatear(construir())
    assert not re.search(r"0x[0-9a-f]{6,}", texto)
    assert "md5(coalesce(dimensiones, '{}'::jsonb)::text)" in texto
