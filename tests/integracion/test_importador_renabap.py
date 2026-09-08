"""HU-021 y AT-064: el padrón RENABAP como snapshot versionado.

El padrón es una foto. Lo que estas pruebas fijan no es que la importación
funcione sino que la ausencia de un barrio siga siendo lo que es —un dato de un
corte— y no se convierta en una conclusión sobre derechos.
"""

from __future__ import annotations

import datetime as dt
import io
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.importadores.renabap import (
    FormaInesperada,
    ImportadorRenabap,
)

pytestmark = pytest.mark.integracion

ENCABEZADO = (
    '"ID Renabap ID Renabap","Barrio Barrio","filtro-provincia Provincia",'
    '"Departamento Departamento","Localidad Localidad","Familias Familias","Mapa Mapa"'
)


def _planilla(filas: list[tuple[str, str, str, str, str, str]]) -> bytes:
    salida = io.StringIO()
    salida.write(ENCABEZADO + "\n")
    for fila in filas:
        campos = ",".join(f'"{c}"' for c in fila)
        salida.write(f"{campos},\"<a href='mapa#x'>Ver en el mapa</a>\"\n")
    return salida.getvalue().encode("utf-8")


FILAS = [
    (
        "2552",
        "Rodrigo Bueno",
        "Ciudad Autónoma de Buenos Aires",
        "Comuna 1",
        "Puerto Madero",
        "1364",
    ),
    ("2553", "Padre Mugica", "Ciudad Autónoma de Buenos Aires", "Comuna 1", "Retiro", "14300"),
]


@pytest.fixture
def captura(conexion: Connection) -> uuid.UUID:
    cargar_catalogo(conexion)
    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES ('F39', :u, 'DETALLE', 'DESCARGA_ARCHIVO') "
            "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'DETALLE' RETURNING id"
        ),
        {"u": "https://docs.google.com/spreadsheets/d/prueba/gviz/tq?tqx=out:csv"},
    ).scalar_one()
    config = conexion.execute(
        text(
            "SELECT id FROM fuente_config_versiones WHERE source_id = 'F39' "
            " ORDER BY version DESC LIMIT 1"
        )
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            " extractor_version, solicitadas, descargadas, procesadas, fin) "
            "VALUES ('F39', :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
        ),
        {"c": config},
    ).scalar_one()
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    return conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
            " bytes, sha256_raw, objeto_uri) "
            "VALUES (:co, :u, :url, 200, 'text/csv', 100, :sha, :uri) RETURNING id"
        ),
        {
            "co": corrida,
            "u": url_id,
            "url": "https://docs.google.com/spreadsheets/d/prueba/gviz/tq?tqx=out:csv",
            "sha": sha,
            "uri": f"objeto://sha256/{sha}",
        },
    ).scalar_one()


def _importar(conexion: Connection, captura: uuid.UUID, filas=FILAS, *, dia=(2026, 3, 1)):
    return ImportadorRenabap(conexion).importar(
        _planilla(filas),
        captura_id=captura,
        capturado_en=dt.datetime(*dia, tzinfo=dt.UTC),
    )


def test_el_padron_se_importa_con_su_version(conexion: Connection, captura) -> None:
    resultado = _importar(conexion, captura)
    assert resultado.barrios_nuevos == 2
    assert resultado.padron_version == "renabap-2026-03-01"
    filas = conexion.execute(
        text(
            "SELECT nombre, provincia, familias, padron_version FROM barrios_renabap "
            " ORDER BY nombre"
        )
    ).all()
    assert [f.nombre for f in filas] == ["Padre Mugica", "Rodrigo Bueno"]
    assert filas[0].familias == 14300


def test_no_se_inventa_una_fecha_de_corte(conexion: Connection, captura) -> None:
    """La planilla no declara corte. Poner la fecha de captura ahí haría creer
    que el padrón se cerró ese día."""
    resultado = _importar(conexion, captura)
    cortes = (
        conexion.execute(text("SELECT DISTINCT fecha_corte FROM barrios_renabap")).scalars().all()
    )
    assert cortes == [None]
    assert any("fecha_corte` queda vacía" in a for a in resultado.avisos)


def test_cada_barrio_nace_con_la_evidencia_de_su_fila(conexion: Connection, captura) -> None:
    """«Figura en el padrón» sin evidencia remite al archivo entero; con
    evidencia, a la fila que lo dice."""
    _importar(conexion, captura)
    filas = conexion.execute(
        text(
            "SELECT b.nombre, e.fragmento, e.selector, e.tipo "
            "  FROM barrios_renabap b JOIN evidencias e ON e.id = b.evidencia_id "
            " ORDER BY e.selector"
        )
    ).all()
    assert len(filas) == 2
    assert all(f.tipo == "CAMPO_CSV" for f in filas)
    assert filas[0].selector == "fila:1"
    assert "Rodrigo Bueno" in filas[0].fragmento


def test_dos_corridas_del_mismo_padron_no_duplican(conexion: Connection, captura) -> None:
    primera = _importar(conexion, captura)
    segunda = _importar(conexion, captura)
    assert primera.barrios_nuevos == 2
    assert segunda.barrios_nuevos == 0
    assert segunda.barrios_conocidos == 2
    assert conexion.execute(text("SELECT count(*) FROM barrios_renabap")).scalar_one() == 2


def test_volver_a_capturar_la_misma_planilla_no_crea_otra_version(
    conexion: Connection, captura
) -> None:
    """Reejecutar la población recaptura la planilla y la importa de nuevo.

    La captura es otra fila —es otra descarga— pero los bytes son los mismos, y
    los mismos bytes son la misma versión del documento. El importador
    reconocía la repetición solo por la captura, así que en la segunda corrida
    intentaba insertar una versión con el hash que ya estaba y chocaba contra la
    restricción que impide duplicarla: la población, documentada como
    idempotente, se caía al reejecutarla sobre una base ya poblada.
    """
    primero = _importar(conexion, captura)
    sha = conexion.execute(
        text("SELECT sha256_raw FROM capturas WHERE id = :c"), {"c": captura}
    ).scalar_one()
    # La misma planilla, descargada otra vez: captura nueva, mismos bytes.
    otra = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
            " bytes, sha256_raw, objeto_uri) "
            "SELECT corrida_id, source_url_id, url_final, 200, mime, bytes, sha256_raw, "
            "  objeto_uri FROM capturas WHERE id = :c RETURNING id"
        ),
        {"c": captura},
    ).scalar_one()

    segundo = _importar(conexion, otra)
    assert segundo.barrios_nuevos == 0
    versiones = conexion.execute(
        text(
            "SELECT count(*) FROM documento_versiones dv JOIN documentos d ON d.id = "
            " dv.documento_id WHERE d.source_id = 'F39' AND dv.hash_texto = :h"
        ),
        {"h": sha},
    ).scalar_one()
    assert versiones == 1
    assert primero.padron_version == segundo.padron_version


def test_un_barrio_que_sale_del_padron_no_se_borra(conexion: Connection, captura) -> None:
    """La versión vieja sigue diciendo que ese día estaba. Borrarlo haría
    imposible responder qué decía el padrón anterior."""
    _importar(conexion, captura, dia=(2026, 3, 1))
    _importar(conexion, captura, filas=FILAS[:1], dia=(2026, 6, 1))

    por_padron = dict(
        conexion.execute(
            text("SELECT padron_version, count(*) FROM barrios_renabap GROUP BY 1")
        ).all()
    )
    assert por_padron == {"renabap-2026-03-01": 2, "renabap-2026-06-01": 1}

    # El barrio que salió conserva su identidad lógica en la versión vieja.
    mugica = (
        conexion.execute(
            text("SELECT padron_version FROM barrios_renabap WHERE nombre = 'Padre Mugica'")
        )
        .scalars()
        .all()
    )
    assert mugica == ["renabap-2026-03-01"]


def test_el_mismo_barrio_conserva_su_identidad_entre_padrones(
    conexion: Connection, captura
) -> None:
    _importar(conexion, captura, dia=(2026, 3, 1))
    _importar(conexion, captura, dia=(2026, 6, 1))
    ids = (
        conexion.execute(
            text("SELECT DISTINCT barrio_id FROM barrios_renabap WHERE id_renabap = '2552'")
        )
        .scalars()
        .all()
    )
    assert len(ids) == 1, "Un barrio no cambia de identidad porque cambie el padrón."


def test_una_fila_sin_identificador_queda_registrada(conexion: Connection, captura) -> None:
    """Sin identificador no se puede seguir al barrio entre versiones. Cargarlo
    igual crearía un barrio nuevo en cada corrida."""
    filas = [*FILAS, ("", "Barrio Sin Id", "Chaco", "San Fernando", "Resistencia", "40")]
    resultado = _importar(conexion, captura, filas=filas)
    assert resultado.sin_id == 1
    assert resultado.barrios_nuevos == 2
    incidencia = conexion.execute(
        text(
            "SELECT descripcion, severidad FROM incidencias_revision "
            " WHERE source_id = 'F39' AND tipo = 'DATO_FALTANTE_CRITICO'"
        )
    ).one()
    assert "no traen identificador RENABAP" in incidencia.descripcion


def test_una_planilla_con_otras_columnas_no_se_importa(conexion: Connection, captura) -> None:
    with pytest.raises(FormaInesperada, match="id_renabap"):
        ImportadorRenabap(conexion).importar(
            b'"Otra","Cosa"\n"1","2"\n',
            captura_id=captura,
            capturado_en=dt.datetime(2026, 3, 1, tzinfo=dt.UTC),
        )


def test_el_html_de_la_celda_no_entra_como_dato(conexion: Connection, captura) -> None:
    """La planilla trae un enlace al mapa dentro de una celda. Ese marcado no es
    parte del nombre del barrio."""
    _importar(conexion, captura)
    nombres = conexion.execute(text("SELECT nombre FROM barrios_renabap")).scalars().all()
    assert all("<a" not in n and "href" not in n for n in nombres)
