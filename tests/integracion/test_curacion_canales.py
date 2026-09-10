"""El curador de canales contra la base (P-006).

Lo que se prueba es la regla que gobierna el módulo: el organismo se declara y
no se adivina. Una fuente sin declaración no carga canales y deja constancia con
cuántos encontró, porque un teléfono bajo el organismo equivocado es alguien
marcando el número equivocado.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion.canales import (
    ORGANISMOS_POR_FUENTE,
    CuradorDeCanales,
    DeclaracionOrganismo,
)

pytestmark = pytest.mark.integracion

TEXTO = (
    "Oficinas NUEVA BALVANERA - SAN CRISTÓBAL (11) 6536-6767 "
    "oad-balvanera-sancristobal@mptutelar.gob.ar"
)


@pytest.fixture
def seccion(conexion: Connection, corpus):
    """Una sección informativa colgada de una fuente del catálogo."""
    del corpus

    def _crear(source_id: str, texto: str = TEXTO, rotulo: str = "Oficinas"):
        doc_version = conexion.execute(
            text(
                "SELECT dv.id FROM documento_versiones dv "
                "  JOIN capturas cap ON cap.id = dv.captura_id "
                "  JOIN fuente_urls fu ON fu.id = cap.source_url_id "
                " WHERE fu.source_id = :s LIMIT 1"
            ),
            {"s": source_id},
        ).scalar_one_or_none()
        if doc_version is None:
            pytest.skip(f"el corpus mínimo no trae capturas de {source_id}")
        return conexion.execute(
            text(
                "INSERT INTO unidades_documentales (doc_version_id, tipo, texto, orden, "
                " rol_contenido, ruta, rotulo) "
                "VALUES (:dv, 'SECCION', :t, 5000, 'INFORMATIVO', 'seccion-1', :r) RETURNING id"
            ),
            {"dv": doc_version, "t": texto, "r": rotulo},
        ).scalar_one()

    return _crear


def _fuente_del_corpus(conexion: Connection) -> str:
    return conexion.execute(
        text(
            "SELECT fu.source_id FROM fuente_urls fu "
            "  JOIN capturas cap ON cap.source_url_id = fu.id "
            "  JOIN documento_versiones dv ON dv.captura_id = cap.id LIMIT 1"
        )
    ).scalar_one()


def test_una_fuente_declarada_carga_sus_canales(conexion: Connection, seccion, monkeypatch) -> None:
    fuente = _fuente_del_corpus(conexion)
    monkeypatch.setitem(
        ORGANISMOS_POR_FUENTE, fuente, DeclaracionOrganismo("Organismo de prueba", "AR-C")
    )
    seccion(fuente)

    resultado = CuradorDeCanales(conexion).cargar(fuente)
    assert resultado.creados == 2, "el teléfono y el correo de la sección"

    filas = conexion.execute(
        text(
            "SELECT c.tipo, c.valor_normalizado, o.nombre, e.fragmento "
            "  FROM canales c JOIN organismos o ON o.id = c.organismo_id "
            "  JOIN evidencias e ON e.id = c.evidencia_id "
            " WHERE o.nombre = 'Organismo de prueba' ORDER BY c.tipo"
        )
    ).all()
    assert {f.tipo for f in filas} == {"EMAIL", "TELEFONO"}
    assert "1165366767" in {f.valor_normalizado for f in filas}
    # Cada canal cita la sección entera: un teléfono suelto no dice para qué es.
    assert all("NUEVA BALVANERA" in f.fragmento for f in filas)


def test_una_fuente_sin_organismo_declarado_no_carga_nada(
    conexion: Connection, seccion, monkeypatch
) -> None:
    fuente = _fuente_del_corpus(conexion)
    monkeypatch.delitem(ORGANISMOS_POR_FUENTE, fuente, raising=False)
    seccion(fuente)

    resultado = CuradorDeCanales(conexion).cargar(fuente)
    assert resultado.creados == 0
    assert resultado.fuentes_sin_organismo[fuente] == 2

    incidencia = conexion.execute(
        text(
            "SELECT descripcion FROM incidencias_revision "
            " WHERE source_id = :s AND tipo = 'DATO_FALTANTE_CRITICO' AND estado = 'ABIERTA' "
            " ORDER BY creado_en DESC LIMIT 1"
        ),
        {"s": fuente},
    ).scalar_one()
    assert "no declara a qué organismo" in incidencia
    assert "ORGANISMOS_POR_FUENTE" in incidencia, "la incidencia dice dónde se arregla"


def test_correr_dos_veces_no_duplica(conexion: Connection, seccion, monkeypatch) -> None:
    fuente = _fuente_del_corpus(conexion)
    monkeypatch.setitem(
        ORGANISMOS_POR_FUENTE, fuente, DeclaracionOrganismo("Organismo de prueba", "AR-C")
    )
    seccion(fuente)

    curador = CuradorDeCanales(conexion)
    primera = curador.cargar(fuente)
    segunda = curador.cargar(fuente)
    assert primera.creados == 2
    assert segunda.creados == 0
    assert segunda.repetidos == 2


def test_un_valor_que_no_normaliza_no_entra(conexion: Connection, seccion, monkeypatch) -> None:
    """La sección publica una tira de años; ninguna se guarda como teléfono."""
    fuente = _fuente_del_corpus(conexion)
    monkeypatch.setitem(
        ORGANISMOS_POR_FUENTE, fuente, DeclaracionOrganismo("Organismo de prueba", "AR-C")
    )
    seccion(fuente, texto="Buscador histórico 1999 1998 1997 2002 2001 2000", rotulo="Histórico")

    resultado = CuradorDeCanales(conexion).cargar(fuente)
    assert resultado.creados == 0
    assert resultado.descartados >= 1
    assert (
        conexion.execute(
            text("SELECT count(*) FROM canales WHERE valor_normalizado ~ '^(19|20)[0-9]{2}$'")
        ).scalar_one()
        == 0
    )
