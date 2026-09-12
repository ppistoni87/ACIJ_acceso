"""Un corte nuevo no puede dejar afuera lo que el anterior ya publicaba.

`release_vigente` devuelve el release publicado más reciente, y la búsqueda
filtra los fragmentos por ese release. La publicación, en cambio, sólo creaba
fragmentos para las versiones **candidatas** de esa corrida. Publicar un
segundo corte —por ejemplo, para incorporar los puntos de atención ya
aprobados— dejaba a la API sirviendo un corte sin una sola unidad normativa: el
frente contestaba «no tengo nada publicado» sobre un corpus que seguía ahí.

Y no fallaba nada. `bn publicacion publicar` terminaba bien, con los ocho gates
en verde y «14.390 versiones publicadas» en pantalla. La única señal era que la
gente dejaba de recibir respuestas.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Connection, text

from tests.conftest import construir_corpus, publicar_corpus

pytestmark = pytest.mark.integracion


def _punto_aprobado(conexion: Connection, nombre: str) -> None:
    """Un punto de atención aprobado y sin publicar, como los 1.842 reales."""
    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'PRESTADOR') "
            "ON CONFLICT (jurisdiccion_id, nombre, tipo) DO UPDATE SET nombre = EXCLUDED.nombre "
            "RETURNING id"
        ),
        {"n": f"Organismo de {nombre}"},
    ).scalar_one()
    punto = conexion.execute(
        text(
            "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, alcance) "
            "VALUES (:o, 'AR-C', :n, 'SEDE', 'PROVINCIAL') RETURNING id"
        ),
        {"o": organismo, "n": nombre},
    ).scalar_one()
    version = conexion.execute(
        text(
            # Con fecha de verificación: sin ella la base no deja publicarla, y
            # eso se prueba aparte, en `test_publicacion_verificada.py`.
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            "  estado_revision, valid_tipo, valid_desde, verificado_en) "
            "VALUES ('punto_atencion', :p, 1, 'APPROVED', 'ABIERTO_FIN', DATE '2025-01-01', "
            "        now()) RETURNING id"
        ),
        {"p": punto},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_legible, "
            "  localidad, es_presencial) VALUES (:v, :p, 'Av. Siempreviva 742', 'CABA', true)"
        ),
        {"v": version, "p": punto},
    )


def release_vigente_ahora(conexion: Connection):
    from backend_normativo.api.dependencias import release_vigente

    return release_vigente(conexion, dt.datetime.now(dt.UTC))


def _fragmentos_del_corte_vigente(conexion: Connection) -> int:
    corte = release_vigente_ahora(conexion)
    assert corte is not None, "tiene que haber un corte publicado"
    return conexion.execute(
        text("SELECT count(*) FROM chunks WHERE release_id = :r"), {"r": corte}
    ).scalar_one()


def test_el_segundo_corte_sigue_sirviendo_las_normas_del_primero(conexion: Connection) -> None:
    """El caso real: publicar los puntos de atención no puede callar las leyes."""
    from backend_normativo.publicacion.release import Publicador

    publicar_corpus(conexion, construir_corpus(conexion))
    antes = _fragmentos_del_corte_vigente(conexion)
    assert antes > 0, "el primer corte publica las unidades de la norma"

    _punto_aprobado(conexion, "Sede de prueba")
    Publicador(conexion).publicar(
        actor="publicador:equipo", motivo="Incorporar los puntos de atención."
    )

    despues = _fragmentos_del_corte_vigente(conexion)
    assert despues >= antes, (
        f"el corte nuevo sirve {despues} fragmentos y el anterior servía {antes}: "
        "publicar dejó a la API sin corpus que citar"
    )


def test_el_corte_nuevo_no_pierde_la_cobertura(conexion: Connection) -> None:
    """Y lo que la respuesta dice que hay publicado sigue siendo lo que hay."""
    from backend_normativo.api.routers.recuperacion import (
        _cobertura_por_corte,
        cobertura_del_corte,
    )
    from backend_normativo.publicacion.release import Publicador

    publicar_corpus(conexion, construir_corpus(conexion))
    primero = release_vigente_ahora(conexion)
    _cobertura_por_corte.clear()
    cubria = cobertura_del_corte(conexion, primero)
    assert cubria, "el primer corte cubre alguna norma"

    _punto_aprobado(conexion, "Otra sede")
    Publicador(conexion).publicar(actor="publicador:equipo", motivo="Puntos de atención.")

    segundo = release_vigente_ahora(conexion)
    assert segundo != primero
    _cobertura_por_corte.clear()
    assert cobertura_del_corte(conexion, segundo) == cubria


def test_una_version_nueva_reemplaza_a_la_vieja_y_no_convive(conexion: Connection) -> None:
    """Lo que esta corrida reemplaza no se arrastra.

    Si el corte heredara todo, una norma reformada quedaría servida dos veces
    —el texto viejo y el nuevo— dentro del mismo corte, y una respuesta podría
    citar los dos como si dijeran lo mismo. Es el caso que hace que «arrastrar
    lo anterior» no pueda ser un simple copiar todo.
    """
    from backend_normativo.publicacion.release import Publicador

    corpus = publicar_corpus(conexion, construir_corpus(conexion))
    vieja = conexion.execute(
        text(
            "SELECT rv.id, nv.norma_id, nv.doc_version_id, rv.entidad_id "
            "  FROM registro_versiones rv "
            "  JOIN norma_versiones nv ON nv.registro_version_id = rv.id "
            " WHERE rv.id = :v"
        ),
        {"v": corpus.registro_version_id},
    ).one()

    nueva = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            "  estado_revision, valid_tipo, valid_desde, verificado_en) "
            "VALUES ('norma', :e, 2, 'APPROVED', 'ABIERTO_FIN', DATE '2026-01-01', now()) "
            "RETURNING id"
        ),
        {"e": vieja.entidad_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO norma_versiones (registro_version_id, norma_id, doc_version_id, "
            "  tipo_version) VALUES (:v, :n, :d, 'ACTUALIZADO')"
        ),
        {"v": nueva, "n": vieja.norma_id, "d": vieja.doc_version_id},
    )
    # Los siete campos, que DQ03 exige de toda versión de norma que se publica.
    conexion.execute(
        text(
            "INSERT INTO evaluaciones_completitud (norma_version_id, campo_solicitado, estado, "
            "  motivo) "
            "SELECT :v, campo_solicitado, estado, motivo FROM evaluaciones_completitud "
            " WHERE norma_version_id = :vieja"
        ),
        {"v": nueva, "vieja": vieja.id},
    )

    Publicador(conexion).publicar(actor="publicador:equipo", motivo="Texto actualizado.")

    corte = release_vigente_ahora(conexion)
    filas = (
        conexion.execute(
            text("SELECT unidad_id, registro_version_id FROM chunks WHERE release_id = :r"),
            {"r": corte},
        )
        .mappings()
        .all()
    )
    assert filas, "el corte nuevo tiene el texto de la norma"
    assert len({f["unidad_id"] for f in filas}) == len(filas), (
        "una unidad aparece dos veces en el mismo corte"
    )
    assert {f["registro_version_id"] for f in filas} == {nueva}, (
        "el corte sirve el texto de la versión vieja además del de la nueva"
    )


def test_el_indice_semantico_viaja_con_lo_heredado(conexion: Connection) -> None:
    """Sin esto el corte nuevo buscaría sólo por palabra y nadie lo notaría.

    La búsqueda híbrida no falla cuando le falta el índice: devuelve lo que
    encuentra la mitad léxica y se ve igual de sana. Se nota midiendo la
    recuperación, semanas después.
    """
    from backend_normativo.publicacion.release import Publicador
    from backend_normativo.recuperacion.embeddings import DIMENSION

    publicar_corpus(conexion, construir_corpus(conexion))
    primero = release_vigente_ahora(conexion)
    indice = conexion.execute(
        text(
            "INSERT INTO indices_semanticos (release_id, modelo, dimension, normalizacion) "
            "VALUES (:r, 'modelo-de-prueba', :d, 'L2') RETURNING id"
        ),
        {"r": primero, "d": DIMENSION},
    ).scalar_one()
    vector = "[" + ",".join(["0.1"] * DIMENSION) + "]"
    conexion.execute(
        text(
            "INSERT INTO fragmento_vectores (indice_id, chunk_id, hash_texto, vector) "
            "SELECT :i, c.id, c.hash, CAST(:vec AS vector) FROM chunks c WHERE c.release_id = :r"
        ),
        {"i": indice, "r": primero, "vec": vector},
    )
    cuantos = conexion.execute(
        text("SELECT count(*) FROM fragmento_vectores WHERE indice_id = :i"), {"i": indice}
    ).scalar_one()
    assert cuantos > 0

    _punto_aprobado(conexion, "Sede con índice")
    Publicador(conexion).publicar(actor="publicador:equipo", motivo="Puntos de atención.")

    segundo = release_vigente_ahora(conexion)
    heredados = conexion.execute(
        text(
            "SELECT count(*) FROM fragmento_vectores v "
            "  JOIN indices_semanticos i ON i.id = v.indice_id "
            " WHERE i.release_id = :r AND i.modelo = 'modelo-de-prueba'"
        ),
        {"r": segundo},
    ).scalar_one()
    assert heredados == cuantos, "el corte nuevo se quedó sin índice semántico"
    # Y el contador del índice dice lo que el índice tiene.
    assert (
        conexion.execute(
            text(
                "SELECT fragmentos FROM indices_semanticos "
                " WHERE release_id = :r AND modelo = 'modelo-de-prueba'"
            ),
            {"r": segundo},
        ).scalar_one()
        == cuantos
    )


# --- Un nivel más arriba: las versiones, no sólo los fragmentos ---------------
#
# El agujero de arriba se tapó para los fragmentos y quedó abierto para las
# versiones. `registro_versiones.release_id` es el corte que **publicó** la
# versión, no los cortes en los que se sirve, así que un corte nuevo dejaba
# fuera de servicio todo lo que el anterior había publicado. Se cobró una
# publicación real: 14.390 versiones operativas entraron y los 15 beneficios y
# las 8 normas del corte anterior se quedaron apuntando al viejo. La orientación
# y la evaluación quedaron muertas con el informe en verde.


def _beneficio_publicable(conexion: Connection, corpus, nombre: str) -> None:
    """Un beneficio aprobado y sin publicar, colgado de la norma del corpus."""
    import uuid as _uuid

    beneficio = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre, linea, familia) "
            "VALUES (:c, :n, 'SUBSIDIO', 'HABITACIONAL') RETURNING id"
        ),
        {"c": f"AR.CORTE-{_uuid.uuid4().hex[:8].upper()}", "n": nombre},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde, verificado_en) "
            "VALUES ('beneficio', :b, 1, 'APPROVED', 'ABIERTO_FIN', DATE '2025-12-23', now()) "
            "RETURNING id"
        ),
        {"b": beneficio},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            " jurisdiccion_id, naturaleza, descripcion) "
            "VALUES (:rv, :b, 'AR-C', 'PRESTACION_MONETARIA', 'Prestación de prueba.')"
        ),
        {"rv": version, "b": beneficio},
    )


def _beneficios_del_corte(conexion: Connection) -> int:
    from backend_normativo.conversacion.necesidades import disponibles

    return sum(n.cuantos for n in disponibles(conexion, release_vigente_ahora(conexion)))


def test_el_segundo_corte_sigue_sirviendo_los_beneficios_del_primero(
    conexion: Connection,
) -> None:
    """El caso que se cobró una publicación de verdad.

    Publicar el dato operativo no puede dejar de servir los programas: sin
    ellos no hay orientación, no hay evaluación y la pantalla no tiene qué
    ofrecer, todo con el corte en verde.
    """
    from backend_normativo.publicacion.release import Publicador

    corpus = construir_corpus(conexion)
    _beneficio_publicable(conexion, corpus, "Apoyo habitacional")
    publicar_corpus(conexion, corpus)
    antes = _beneficios_del_corte(conexion)
    assert antes > 0, "el primer corte publica el beneficio"

    _punto_aprobado(conexion, "Sede que llega después")
    Publicador(conexion).publicar(actor="publicador:equipo", motivo="Puntos de atención.")

    despues = _beneficios_del_corte(conexion)
    assert despues == antes, (
        f"el corte nuevo sirve {despues} beneficios y el anterior servía {antes}: "
        "publicar dejó a la orientación sin nada que ofrecer"
    )


def test_la_publicacion_avisa_cuando_deja_de_servir_algo(conexion: Connection) -> None:
    """La red que faltaba, y que es lo que hace que esto no vuelva a pasar callado.

    Con herencia esto tiene que dar vacío. Que exista el informe importa igual:
    si mañana una versión sale de servicio por otro motivo —cuarentena, un
    reemplazo que no se publicó—, se ve en la publicación y no en la pantalla
    vacía de alguien.
    """
    from backend_normativo.publicacion.release import Publicador

    corpus = construir_corpus(conexion)
    _beneficio_publicable(conexion, corpus, "Apoyo habitacional")
    publicar_corpus(conexion, corpus)

    _punto_aprobado(conexion, "Otra sede más")
    resultado = Publicador(conexion).publicar(
        actor="publicador:equipo", motivo="Puntos de atención."
    )

    assert resultado.dejo_de_servir == [], f"el corte dejó de servir {resultado.dejo_de_servir}"
    assert resultado.versiones_heredadas > 0, "algo tenía que heredarse del corte anterior"


def test_revertir_no_desatiende_lo_que_publico_el_corte_anterior(conexion: Connection) -> None:
    """Heredar no puede convertir a un corte en dueño de lo ajeno.

    Si al revertir el corte nuevo se despublicara también lo heredado, revertir
    una corrida de puntos de atención apagaría las leyes que venían de antes.
    """
    from backend_normativo.publicacion.release import Publicador

    corpus = construir_corpus(conexion)
    _beneficio_publicable(conexion, corpus, "Apoyo habitacional")
    publicar_corpus(conexion, corpus)
    antes = _beneficios_del_corte(conexion)

    _punto_aprobado(conexion, "Sede efímera")
    segundo = Publicador(conexion).publicar(actor="publicador:equipo", motivo="Puntos.")
    Publicador(conexion).revertir(
        segundo.release_id, actor="publicador:equipo", motivo="Se revierte."
    )

    assert _beneficios_del_corte(conexion) == antes, (
        "revertir el corte nuevo apagó lo que servía el anterior"
    )


def test_ninguna_consulta_filtra_versiones_por_release_id(conexion: Connection) -> None:
    """«Qué sirve un corte» se define en un solo lugar: la membresía.

    El mismo error apareció dos veces en dos niveles distintos —los fragmentos
    y las versiones— porque cada consulta lo resolvía por su cuenta. Esta prueba
    es la que evita la tercera.
    """
    import pathlib
    import re

    raiz = pathlib.Path(__file__).resolve().parents[2] / "src" / "backend_normativo"
    culpables = []
    for archivo in raiz.rglob("*.py"):
        if "migrations" in archivo.parts:
            continue
        for numero, linea in enumerate(archivo.read_text().splitlines(), 1):
            if re.search(r"\brv\.release_id\s*=\s*:", linea):
                culpables.append(f"{archivo.relative_to(raiz)}:{numero}")

    assert not culpables, (
        "filtrar versiones por `rv.release_id` pregunta qué corte las publicó, no en cuáles "
        f"se sirven: {culpables}. Se une contra `release_versiones`."
    )
