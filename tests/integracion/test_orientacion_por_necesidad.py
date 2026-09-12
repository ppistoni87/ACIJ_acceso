"""P-030, criterio 1: orientar desde la situación, no desde el nombre del programa.

Alguien que se quedó sin casa no sabe que lo que busca se llama «Programa de
apoyo para personas en situación de vulnerabilidad habitacional». Lo que se
prueba acá es que pueda llegar igual, que la lista no se presente como completa,
y —lo más delicado— que la necesidad la elija la persona y no la deduzca el
sistema de lo que escribió.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

pytestmark = pytest.mark.integracion


def _beneficio(conexion: Connection, corpus, *, familia: str, nombre: str) -> None:
    """Un beneficio publicado en el corte del corpus, con una regla."""
    sufijo = uuid.uuid4().hex[:8].upper()
    beneficio = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre, linea, familia) "
            "VALUES (:c, :n, 'SUBSIDIO', :f) RETURNING id"
        ),
        {"c": f"AR.NEC-{sufijo}", "n": nombre, "f": familia},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde, release_id, verificado_en) "
            "SELECT 'beneficio', :b, 1, 'PUBLISHED', 'ABIERTO_FIN', '2025-12-23', "
            "       rv.release_id, now() FROM registro_versiones rv WHERE rv.id = :rv "
            "RETURNING id"
        ),
        {"b": beneficio, "rv": corpus.registro_version_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            " jurisdiccion_id, naturaleza, descripcion) "
            "VALUES (:rv, :b, 'AR-C', 'PRESTACION_MONETARIA', 'Una prestación de prueba.')"
        ),
        {"rv": version, "b": beneficio},
    )
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_normas (beneficio_version_id, norma_version_id, rol, "
            " evidencia_id) VALUES (:bv, :nv, 'CREA', :e)"
        ),
        {"bv": version, "nv": corpus.registro_version_id, "e": evidencia},
    )
    conexion.execute(
        text(
            "INSERT INTO reglas (beneficio_version_id, evidencia_id, categoria, texto_literal, "
            " descripcion, requiere_revision, estado_revision) "
            "VALUES (:bv, :e, 'APLICABILIDAD', 'Una condición.', 'Prueba.', true, 'CANDIDATE')"
        ),
        {"bv": version, "e": evidencia},
    )


def test_las_necesidades_salen_del_corte_y_no_de_una_lista_escrita_a_mano(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """Ofrecer «vivienda» sin ninguna norma de vivienda publicada es prometer
    algo que no se tiene."""
    vacio = cliente_api.get("/v1/necesidades").json()
    assert vacio["data"]["necesidades"] == []
    assert vacio["data_status"] == "SIN_RESULTADOS"

    _beneficio(conexion, corpus_publicado, familia="HABITACIONAL", nombre="Apoyo habitacional")
    cuerpo = cliente_api.get("/v1/necesidades").json()["data"]

    [necesidad] = cuerpo["necesidades"]
    assert necesidad["familia"] == "HABITACIONAL"
    assert necesidad["rotulo"] == "Dónde vivir"
    assert necesidad["cuantos"] == 1


def test_ninguna_lista_de_opciones_se_presenta_como_completa(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """Presentarla como el catálogo completo haría que alguien deje de buscar
    donde sí lo hay."""
    _beneficio(conexion, corpus_publicado, familia="HABITACIONAL", nombre="Apoyo habitacional")

    for ruta in ("/v1/necesidades", "/v1/necesidades/HABITACIONAL/opciones"):
        datos = cliente_api.get(ruta).json()["data"]
        assert datos["exhaustivo"] is False, ruta
        assert "no todo lo que existe" in datos["aclaracion"], ruta


def test_una_opcion_dice_de_donde_sale_y_donde_rige(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """Las razones de pertinencia son sobre la norma, nunca sobre la persona."""
    _beneficio(conexion, corpus_publicado, familia="HABITACIONAL", nombre="Apoyo habitacional")

    [opcion] = cliente_api.get("/v1/necesidades/HABITACIONAL/opciones").json()["data"]["opciones"]

    assert opcion["nombre"] == "Apoyo habitacional"
    assert opcion["jurisdiccion"] == "Ciudad Autónoma de Buenos Aires"
    assert opcion["norma"] == "LEY 6935/2025"
    assert opcion["condiciones"] == 1
    # Sin jurisdicción declarada no se afirma ni que coincide ni que no.
    assert opcion["coincide_jurisdiccion"] is None


def test_la_jurisdiccion_marca_pero_no_esconde(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """Esconder un programa de otra jurisdicción le saca a la persona la chance
    de ver que existe algo parecido donde vive."""
    _beneficio(conexion, corpus_publicado, familia="HABITACIONAL", nombre="Apoyo habitacional")

    datos = cliente_api.get("/v1/necesidades/HABITACIONAL/opciones?jurisdiccion=AR-B").json()[
        "data"
    ]

    assert len(datos["opciones"]) == 1, "no se filtra: se marca"
    assert datos["opciones"][0]["coincide_jurisdiccion"] is False


def test_una_necesidad_sin_nada_publicado_lo_dice_en_vez_de_devolver_vacio(
    cliente_api, corpus_publicado
) -> None:
    datos = cliente_api.get("/v1/necesidades/HABITACIONAL/opciones").json()
    assert datos["data"]["opciones"] == []
    assert datos["data_status"] == "SIN_RESULTADOS"
    assert datos["data"]["rotulo"] == "Dónde vivir"


def test_toda_familia_del_corte_tiene_como_decirse_en_castellano(
    cliente_api, conexion: Connection, corpus_publicado
) -> None:
    """La red que avisa cuando el corpus trae una familia que nadie nombró.

    Sin esto, una familia nueva llegaría a la pantalla como `SEGURIDAD_SOCIAL`:
    vocabulario nuestro, no de quien pregunta. La prueba no obliga a nombrarla
    de antemano; obliga a enterarse.
    """
    from backend_normativo.conversacion.necesidades import NECESIDADES

    _beneficio(conexion, corpus_publicado, familia="HABITACIONAL", nombre="Apoyo habitacional")
    familias = {
        n["familia"] for n in cliente_api.get("/v1/necesidades").json()["data"]["necesidades"]
    }

    sin_nombre = sorted(familias - set(NECESIDADES))
    assert not sin_nombre, (
        f"el corte publica familias que nadie nombró en castellano: {sin_nombre}. "
        "Se mostrarían con su código interno."
    )


def test_una_familia_desconocida_no_se_inventa_un_nombre(cliente_api, corpus_publicado) -> None:
    """Se muestra su propio texto, legible, antes que un nombre inventado."""
    datos = cliente_api.get("/v1/necesidades/ALGO_NUEVO/opciones").json()["data"]
    assert datos["rotulo"] == "Algo nuevo"
    assert datos["detalle"] == ""
