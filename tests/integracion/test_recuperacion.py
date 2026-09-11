"""El índice semántico y la búsqueda híbrida sobre un corte real (P-012).

Corre con `EmbebedorDeterminista` y no con el modelo de verdad. Lo que se prueba
acá es la mecánica —que el índice pertenezca al corte, que los filtros se
apliquen antes de entregar nada, que la fusión no duplique y que un texto
cambiado invalide su vector—, y nada de eso depende del modelo. Atar estas
pruebas a una descarga de 220 MB haría que corran poco y tarde. La calidad de la
recuperación se mide aparte, contra el conjunto congelado, con el modelo real.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.recuperacion.busqueda import buscar
from backend_normativo.recuperacion.embeddings import EmbebedorDeterminista
from backend_normativo.recuperacion.indice import Indexador

pytestmark = pytest.mark.integracion


@pytest.fixture
def embebedor() -> EmbebedorDeterminista:
    return EmbebedorDeterminista()


@pytest.fixture
def release_id(conexion: Connection, corpus_publicado):
    del corpus_publicado
    return conexion.execute(
        text(
            "SELECT id FROM releases WHERE estado = 'PUBLICADO' ORDER BY publicado_en DESC LIMIT 1"
        )
    ).scalar_one()


def test_el_indice_se_construye_sobre_el_corte(conexion: Connection, release_id, embebedor) -> None:
    resultado = Indexador(conexion, embebedor).construir()
    assert resultado.release_id == release_id
    assert resultado.fragmentos > 0
    assert resultado.embebidos == resultado.fragmentos
    assert resultado.completo

    # Cada vector declara con qué modelo y sobre qué texto se calculó.
    fila = conexion.execute(
        text(
            "SELECT i.modelo, i.dimension, i.normalizacion, i.fragmentos, "
            "       count(v.chunk_id) AS vectores "
            "  FROM indices_semanticos i "
            "  JOIN fragmento_vectores v ON v.indice_id = i.id "
            " WHERE i.id = :i GROUP BY i.modelo, i.dimension, i.normalizacion, i.fragmentos"
        ),
        {"i": resultado.indice_id},
    ).one()
    assert fila.modelo == embebedor.modelo
    assert fila.dimension == embebedor.dimension
    assert fila.normalizacion == "L2"
    assert fila.vectores == fila.fragmentos


def test_sin_corte_publicado_no_hay_nada_que_indexar(conexion: Connection, embebedor) -> None:
    """Indexar staging serviría como citable algo que todavía no lo es."""
    resultado = Indexador(conexion, embebedor).construir()
    assert resultado.release_id is None
    assert resultado.fragmentos == 0
    assert any("publicado" in a for a in resultado.avisos)


def test_reconstruir_no_recalcula_lo_que_no_cambio(
    conexion: Connection, release_id, embebedor
) -> None:
    del release_id
    indexador = Indexador(conexion, embebedor)
    primera = indexador.construir()
    segunda = indexador.construir()
    assert segunda.fragmentos == primera.fragmentos
    assert segunda.embebidos == 0
    assert segunda.reusados == primera.fragmentos


def test_un_texto_que_cambio_invalida_su_vector(
    conexion: Connection, release_id, embebedor
) -> None:
    """El hash es lo que hace visible que el vector quedó viejo."""
    indexador = Indexador(conexion, embebedor)
    indexador.construir()
    conexion.execute(
        text(
            "UPDATE chunks SET texto = texto || ' — párrafo agregado después.' "
            " WHERE id = (SELECT id FROM chunks WHERE release_id = :r ORDER BY id LIMIT 1)"
        ),
        {"r": release_id},
    )
    resultado = indexador.construir()
    assert resultado.vencidos == 1
    assert resultado.embebidos == 1
    assert any("ya no es el suyo" in a for a in resultado.avisos)


def test_la_busqueda_hibrida_encuentra_por_las_dos_mitades(
    conexion: Connection, release_id, embebedor
) -> None:
    Indexador(conexion, embebedor).construir()
    resultado = buscar(
        conexion, "prestación económica", release_id=release_id, embebedor=embebedor, limite=5
    )
    assert resultado.fragmentos
    assert resultado.indice_id is not None
    assert not resultado.solo_lexica
    assert all(f.encontrado_por in {"lexica", "semantica", "ambas"} for f in resultado.fragmentos)
    # Lo que las dos encuentran tiene que quedar arriba de lo que encuentra una.
    puntajes = [f.puntaje for f in resultado.fragmentos]
    assert puntajes == sorted(puntajes, reverse=True)


def test_sin_indice_la_busqueda_avisa_que_fue_solo_lexica(
    conexion: Connection, release_id, embebedor
) -> None:
    """Una respuesta peor que la que el sistema puede dar tiene que declararse."""
    resultado = buscar(
        conexion, "prestación económica", release_id=release_id, embebedor=embebedor, limite=5
    )
    assert resultado.solo_lexica
    assert any("solo léxica" in a for a in resultado.avisos)


def test_la_fusion_no_devuelve_el_mismo_fragmento_dos_veces(
    conexion: Connection, release_id, embebedor
) -> None:
    Indexador(conexion, embebedor).construir()
    resultado = buscar(
        conexion, "prestación beneficiarios", release_id=release_id, embebedor=embebedor, limite=20
    )
    ids = [f.chunk_id for f in resultado.fragmentos]
    assert len(ids) == len(set(ids))


def test_el_filtro_de_jurisdiccion_se_aplica_antes_de_entregar(
    conexion: Connection, release_id, embebedor
) -> None:
    Indexador(conexion, embebedor).construir()
    porteño = buscar(
        conexion,
        "prestación",
        release_id=release_id,
        embebedor=embebedor,
        limite=10,
        jurisdiccion="AR-C",
    )
    nacional = buscar(
        conexion,
        "prestación",
        release_id=release_id,
        embebedor=embebedor,
        limite=10,
        jurisdiccion="AR",
    )
    assert porteño.fragmentos
    assert all(f.jurisdiccion == "AR-C" for f in porteño.fragmentos)
    assert nacional.fragmentos == []


def test_no_se_recupera_lo_que_el_corte_no_publica(
    conexion: Connection, release_id, embebedor
) -> None:
    """Un vector cuelga de un índice y un índice cuelga de un corte."""
    Indexador(conexion, embebedor).construir()
    otro = conexion.execute(
        text(
            "INSERT INTO releases (id, estado, motivo) "
            "VALUES (gen_random_uuid(), 'BORRADOR', 'corte que no existe') RETURNING id"
        )
    ).scalar_one()
    resultado = buscar(conexion, "prestación", release_id=otro, embebedor=embebedor, limite=10)
    assert resultado.fragmentos == []
    assert resultado.solo_lexica, "sin índice para ese corte, no hay mitad vectorial que usar"


def test_los_vectores_de_fragmentos_que_salieron_del_corte_se_van(
    conexion: Connection, release_id, embebedor
) -> None:
    indexador = Indexador(conexion, embebedor)
    primera = indexador.construir()
    conexion.execute(
        text(
            "DELETE FROM fragmento_vectores WHERE chunk_id IN "
            "  (SELECT id FROM chunks WHERE release_id = :r ORDER BY id LIMIT 1)"
        ),
        {"r": release_id},
    )
    conexion.execute(
        text(
            "DELETE FROM chunks WHERE id = (SELECT id FROM chunks WHERE release_id = :r "
            "ORDER BY id LIMIT 1)"
        ),
        {"r": release_id},
    )
    segunda = indexador.construir()
    assert segunda.fragmentos == primera.fragmentos - 1


def test_una_pregunta_en_castellano_normal_encuentra_el_articulo(
    conexion: Connection, release_id
) -> None:
    """`plainto_tsquery` exige todas las palabras, y eso rompe con quien pregunta.

    «beneficiarios» encontraba el artículo; «quiénes son beneficiarios» no
    encontraba nada, porque `quiénes` normaliza a `quien`, que PostgreSQL no
    trata como palabra vacía y que el texto legal no usa. Cuanto más natural la
    pregunta, peor funcionaba.
    """
    estricta = buscar(conexion, "beneficiarios", release_id=release_id)
    assert estricta.fragmentos, "la consulta de una sola palabra ya encontraba"

    natural = buscar(conexion, "quiénes son beneficiarios del programa", release_id=release_id)
    assert natural.fragmentos, "una pregunta entera tiene que encontrar lo mismo"
    assert {f.chunk_id for f in estricta.fragmentos} <= {f.chunk_id for f in natural.fragmentos}


def test_la_busqueda_ampliada_se_declara(conexion: Connection, release_id) -> None:
    """Aflojar el criterio cambia lo que significa el resultado, así que se dice."""
    natural = buscar(conexion, "quiénes son beneficiarios del programa", release_id=release_id)
    assert any("cualquiera de ellas" in aviso for aviso in natural.avisos)


def test_no_se_afloja_cuando_no_hace_falta(conexion: Connection, release_id) -> None:
    """Mientras la consulta estricta devuelva algo, ese algo es más pertinente."""
    estricta = buscar(conexion, "beneficiarios", release_id=release_id)
    assert not any("cualquiera de ellas" in aviso for aviso in estricta.avisos)


def test_una_consulta_sin_ninguna_palabra_del_corpus_sigue_sin_encontrar(
    conexion: Connection, release_id
) -> None:
    """Ampliar no es encontrar cualquier cosa: sin una sola coincidencia, nada."""
    vacia = buscar(conexion, "zzzz qwrtpxk vvvvv", release_id=release_id)
    assert vacia.fragmentos == []
