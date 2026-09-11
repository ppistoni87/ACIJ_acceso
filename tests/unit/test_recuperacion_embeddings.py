"""Lo que un vector tiene que conservar de su origen (P-012 criterio 1)."""

from __future__ import annotations

import math

import pytest

from backend_normativo.recuperacion.embeddings import (
    DIMENSION,
    EmbebedorDeterminista,
    en_lotes,
    hash_de,
    normalizar,
)


def test_el_hash_identifica_el_texto_embebido() -> None:
    """Sin el hash, un vector calculado sobre un texto viejo es indistinguible."""
    assert hash_de("Art. 2°.- Beneficiarios") == hash_de("Art. 2°.- Beneficiarios")
    assert hash_de("Art. 2°.- Beneficiarios") != hash_de("Art. 3°.- Beneficiarios")
    assert len(hash_de("x")) == 64


def test_normalizar_deja_norma_uno() -> None:
    vector = normalizar([3.0, 4.0] + [0.0] * (DIMENSION - 2))
    assert math.isclose(math.sqrt(sum(c * c for c in vector)), 1.0, rel_tol=1e-9)


def test_un_vector_de_norma_cero_no_es_un_vector() -> None:
    """No se normaliza en silencio a algo: no representa ningún texto."""
    with pytest.raises(ValueError, match="norma cero"):
        normalizar([0.0] * DIMENSION)


def test_el_embebedor_declara_su_modelo_y_su_dimension() -> None:
    embebedor = EmbebedorDeterminista()
    assert embebedor.modelo
    assert embebedor.dimension == DIMENSION
    vectores = embebedor.embeber(["primero", "segundo"])
    assert len(vectores) == 2
    assert all(len(v) == DIMENSION for v in vectores)


def test_el_mismo_texto_da_el_mismo_vector() -> None:
    embebedor = EmbebedorDeterminista()
    uno = embebedor.embeber(["situación de calle efectiva"])[0]
    otro = embebedor.embeber(["situación de calle efectiva"])[0]
    assert uno == otro


def test_textos_que_comparten_palabras_quedan_mas_cerca() -> None:
    embebedor = EmbebedorDeterminista()
    a, b, c = embebedor.embeber(
        [
            "prestación económica mensual para el hogar",
            "prestación económica mensual del programa",
            "dispositivos de abordaje territorial",
        ]
    )
    similar = sum(x * y for x, y in zip(a, b, strict=True))
    distinto = sum(x * y for x, y in zip(a, c, strict=True))
    assert similar > distinto


def test_un_texto_vacio_no_rompe_la_indexacion() -> None:
    """Se le da dirección fija: el error tiene que salir al validar, no al dividir."""
    vector = EmbebedorDeterminista().embeber([""])[0]
    assert math.isclose(math.sqrt(sum(c * c for c in vector)), 1.0, rel_tol=1e-9)


def test_los_lotes_cubren_todo_sin_repetir() -> None:
    textos = [f"t{i}" for i in range(10)]
    lotes = list(en_lotes(textos, 3))
    assert [len(x) for x in lotes] == [3, 3, 3, 1]
    assert [t for lote in lotes for t in lote] == textos


def test_el_modelo_se_carga_una_sola_vez_aunque_lleguen_juntas() -> None:
    """Veinte consultas concurrentes no pueden cargar veinte veces 220 MB.

    Con `lru_cache` pasaba: la caché guarda el resultado **después** de que la
    función termina, así que las veinte encuentran el hueco vacío y entran las
    veinte. Lo encontró el ensayo de carga —las peticiones a `/v1/respuestas`
    expiraban a los treinta segundos y arrastraban al resto de las rutas—, y por
    eso la prueba está acá y no en la historia que lo descubrió.
    """
    import threading
    import time

    from backend_normativo.recuperacion import embeddings

    cargas = []

    class _Lento:
        def __init__(self, modelo: str, **_kwargs) -> None:
            self.modelo = modelo

        def precargar(self) -> None:
            cargas.append(1)
            time.sleep(0.05)

    embeddings.olvidar_embebedor()
    original = embeddings.EmbebedorFastEmbed
    embeddings.EmbebedorFastEmbed = _Lento  # type: ignore[misc]
    try:
        hilos = [threading.Thread(target=embeddings.embebedor_compartido) for _ in range(20)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=10)
        assert len(cargas) == 1, f"se cargó {len(cargas)} veces"
    finally:
        embeddings.EmbebedorFastEmbed = original  # type: ignore[misc]
        embeddings.olvidar_embebedor()
