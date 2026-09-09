"""HU-035: traer al corpus las normas que el corpus cita.

Lo que se fija acá es el límite: qué se amplía y qué no. Ampliar de más es peor
que no ampliar, porque una norma traída por el número equivocado entra al corpus
con toda la apariencia de un texto verificado.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.ampliacion import SOURCE_ID, ampliar, candidatas

pytestmark = pytest.mark.integracion

URL_CONSOLIDADA = "http://servicios.infoleg.gob.ar/infolegInternet/anexos/0-4999/639/texact.htm"
URL_PUBLICADA = "http://servicios.infoleg.gob.ar/infolegInternet/anexos/155000-159999/1/norma.htm"


def _norma(
    conexion: Connection,
    *,
    tipo: str,
    numero: str,
    anio: int,
    jurisdiccion: str = "AR",
    incierta: bool = False,
    url: str | None = None,
) -> uuid.UUID:
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo, identidad_incierta) "
            "VALUES (:j, :t, :n, :a, :tit, :i) RETURNING id"
        ),
        {
            "j": jurisdiccion,
            "t": tipo,
            "n": numero,
            "a": anio,
            "tit": f"{tipo} {numero}/{anio}",
            "i": incierta,
        },
    ).scalar_one()
    if url is not None:
        conexion.execute(
            text(
                "INSERT INTO norma_identificadores (norma_id, namespace, valor, url_oficial) "
                "VALUES (:n, 'infoleg', :v, :u)"
            ),
            {"n": norma_id, "v": str(uuid.uuid4())[:8], "u": url},
        )
    return norma_id


def _evidencia(conexion: Connection) -> uuid.UUID:
    """Una cita pendiente sin evidencia no se puede localizar, y el esquema lo impide.

    La cadena mínima es la de siempre: captura, documento, versión, unidad. Se
    arma entera en vez de saltearla porque el punto de la referencia pendiente
    es poder mostrar dónde dice lo que dice.
    """
    from tests.integracion.test_curacion import _documento_norma

    _documento_norma(
        conexion,
        source_id="F33",
        external_id=f"prueba:{uuid.uuid4()}",
        tipo_version="ACTUALIZADO",
        identidad={"jurisdiccion": "AR", "tipo": "LEY", "numero": "99999", "anio": 1990},
        unidades=[("ARTICULO", "1", "Artículo 1º — Texto de prueba.", "DISPOSITIVO")],
        sufijo_url=f"-{uuid.uuid4()}",
    )
    unidad = (
        conexion.execute(
            text(
                "SELECT id, doc_version_id, texto FROM unidades_documentales "
                " ORDER BY id DESC LIMIT 1"
            )
        )
        .mappings()
        .one()
    )
    return conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, tipo, hash_fragmento) "
            "VALUES (:d, :u, :f, 'FRAGMENTO_TEXTO', :h) RETURNING id"
        ),
        {
            "d": unidad["doc_version_id"],
            "u": unidad["id"],
            "f": unidad["texto"],
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
        },
    ).scalar_one()


def _referencia(conexion: Connection, origen: uuid.UUID, identidad: dict) -> None:
    import json

    conexion.execute(
        text(
            "INSERT INTO referencias_pendientes (norma_origen_id, evidencia_id, "
            " identidad_candidata, texto_cita, estado, responsable_rol, motivo) "
            "VALUES (:o, :e, CAST(:i AS jsonb), 'cita de prueba', 'PENDIENTE', "
            "        'curacion juridica', 'sin resolver')"
        ),
        {"o": origen, "e": _evidencia(conexion), "i": json.dumps(identidad)},
    )


@pytest.fixture
def catalogo(conexion: Connection):
    cargar_catalogo(conexion)


def test_una_norma_citada_con_texto_se_puede_traer(conexion: Connection, catalogo) -> None:
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="LEY", numero="24241", anio=1993, url=URL_CONSOLIDADA)
    _referencia(conexion, origen, {"tipo": "LEY", "numero": "24241", "anio": "1993"})

    resultado = ampliar(conexion)
    assert [(c.tipo, c.numero, c.anio) for c in resultado.agregadas] == [("LEY", "24241", 1993)]
    # Se pide por https: la política no admite bajar por un canal sin validación
    # de certificado, y el catálogo publica las URLs en http.
    url = conexion.execute(
        text("SELECT url FROM fuente_urls WHERE source_id = :s"), {"s": SOURCE_ID}
    ).scalar_one()
    assert url.startswith("https://")


def test_el_texto_publicado_sirve_cuando_no_hay_consolidado(conexion: Connection, catalogo) -> None:
    """Una modificatoria no tiene texto consolidado y no le hace falta.

    Lo que esa norma dice es lo que publicó. Descartarla por no tener
    consolidado dejaría afuera justamente a los decretos que modifican la ley,
    que son los que explican por qué la ley dice lo que dice.
    """
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="DECRETO", numero="1602", anio=2009, url=URL_PUBLICADA)
    _referencia(conexion, origen, {"tipo": "DECRETO", "numero": "1602", "anio": "2009"})

    resultado = candidatas(conexion)
    assert [c.tipo_texto for c in resultado.agregadas] == ["norma.htm"]


def test_una_cita_sin_año_no_se_resuelve(conexion: Connection, catalogo) -> None:
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="DECRETO", numero="1667", anio=2012, url=URL_CONSOLIDADA)
    _referencia(conexion, origen, {"tipo": "DECRETO", "numero": "1667"})

    resultado = candidatas(conexion)
    assert resultado.agregadas == []
    assert "no dice el año" in resultado.descartadas[0].motivo


def test_una_identidad_que_resuelve_a_dos_normas_no_se_resuelve(
    conexion: Connection, catalogo
) -> None:
    """El tipo se numera por organismo: la clave no distingue.

    Elegir una de dos por orden de aparición traería un texto al corpus con la
    apariencia de estar verificado, que es lo contrario de lo que la referencia
    pendiente está diciendo.

    Las dos entran marcadas como de identidad incierta porque es la única forma
    en que el esquema deja convivir la misma clave dos veces, y es exactamente
    lo que pasa en el catálogo real: tres resoluciones 75 de 2019, de tres
    organismos distintos.
    """
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="RESOLUCION", numero="75", anio=2019, url=URL_CONSOLIDADA, incierta=True)
    _norma(conexion, tipo="RESOLUCION", numero="75", anio=2019, url=URL_CONSOLIDADA, incierta=True)
    _referencia(conexion, origen, {"tipo": "RESOLUCION", "numero": "75", "anio": "2019"})

    resultado = candidatas(conexion)
    assert resultado.agregadas == []
    assert "2 normas" in resultado.descartadas[0].motivo


def test_una_norma_de_identidad_incierta_no_se_trae(conexion: Connection, catalogo) -> None:
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="DECRETO", numero="292", anio=1995, url=URL_CONSOLIDADA, incierta=True)
    _referencia(conexion, origen, {"tipo": "DECRETO", "numero": "292", "anio": "1995"})

    resultado = candidatas(conexion)
    assert resultado.agregadas == []
    assert "identidad incierta" in resultado.descartadas[0].motivo


def test_una_cita_porteña_no_se_resuelve_contra_el_catalogo_nacional(
    conexion: Connection, catalogo
) -> None:
    """La Ley 3706 de la Ciudad no es la ley nacional con ese número.

    Es el error más fácil de cometer y el más difícil de ver después: el texto
    entra, se segmenta y se cura, y nada dice que es de otra jurisdicción.
    """
    origen = _norma(conexion, tipo="LEY", numero="6935", anio=2025, jurisdiccion="AR-C")
    _norma(conexion, tipo="LEY", numero="3706", anio=2010, url=URL_CONSOLIDADA)
    _referencia(conexion, origen, {"tipo": "LEY", "numero": "3706", "anio": "2010"})

    resultado = candidatas(conexion)
    assert resultado.agregadas == []
    assert resultado.descartadas == []


def test_una_norma_sin_texto_queda_declarada_y_no_se_trae(conexion: Connection, catalogo) -> None:
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="DECRETO", numero="1245", anio=1996)
    _referencia(conexion, origen, {"tipo": "DECRETO", "numero": "1245", "anio": "1996"})

    resultado = candidatas(conexion)
    assert resultado.agregadas == []
    assert "sin texto publicado" in resultado.descartadas[0].motivo


def test_ampliar_dos_veces_no_duplica_la_url(conexion: Connection, catalogo) -> None:
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="LEY", numero="24241", anio=1993, url=URL_CONSOLIDADA)
    _referencia(conexion, origen, {"tipo": "LEY", "numero": "24241", "anio": "1993"})

    ampliar(conexion)
    segunda = ampliar(conexion)
    assert segunda.agregadas == []
    assert len(segunda.ya_estaban) == 1
    urls = conexion.execute(
        text("SELECT count(*) FROM fuente_urls WHERE source_id = :s"), {"s": SOURCE_ID}
    ).scalar_one()
    assert urls == 1


def test_la_fuente_derivada_no_entra_al_inventario_del_manual(
    conexion: Connection, catalogo
) -> None:
    """Las 83 fuentes son las que relevó el manual y tienen que seguir siendo 83.

    Una norma que entra porque otra la cita es trazable a esa cita, no a un
    relevamiento, y mezclarlas haría que el inventario dijera algo que el manual
    no dice.
    """
    origen = _norma(conexion, tipo="LEY", numero="24714", anio=1996)
    _norma(conexion, tipo="LEY", numero="24241", anio=1993, url=URL_CONSOLIDADA)
    _referencia(conexion, origen, {"tipo": "LEY", "numero": "24241", "anio": "1993"})
    ampliar(conexion)

    origen_fuente = conexion.execute(
        text("SELECT origen FROM fuentes WHERE source_id = :s"), {"s": SOURCE_ID}
    ).scalar_one()
    assert origen_fuente == "citada_por_el_corpus"
    del_manual = conexion.execute(
        text("SELECT count(*) FROM fuentes WHERE origen LIKE 'manual_%'")
    ).scalar_one()
    assert del_manual == 53
