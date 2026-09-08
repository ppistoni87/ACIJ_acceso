"""HU-019 y HU-020: directorios de atención sin mezclar entidades.

Un directorio es donde más rápido se afirma algo falso sin que nada avise: una
dirección mal armada, un teléfono que dice `N/A` y un punto en el mapa a mil
kilómetros se ven igual que los correctos.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.importadores.directorios import (
    COMUNAS,
    EFECTORES,
    FormaInesperada,
    ImportadorDirectorios,
    _coordenadas,
)

pytestmark = pytest.mark.integracion

# Filas reales de los datasets, recortadas.
CSV_COMUNAS = (
    "fna,gna,nam,dir,bar,com,tel,web,sag,geometry\n"
    "Sede Comunal 1,Sede Comunal,Comunal 1,Humberto 1° 250,San Telmo,1,,"
    "https://buenosaires.gob.ar/comuna-1,Secretaría,"
    "POINT (28615.885145573622 70947.088427481)\n"
    'Subsede Comunal 2,Subsede Comunal,Comunal 2,"Lopez, Vicente 2050, 3 piso",Recoleta,2,'
    "4808-7300,https://buenosaires.gob.ar/comuna-2,Secretaría,"
    "POINT (26375.33632060788 74454.15121550763)\n"
).encode()

CSV_EFECTORES = (
    "programa,nombre,tipo_taller,destinatarios,direccion,barrio,comuna,dias,"
    "horario_atencion,telefono,email,web,archivo_origen\n"
    "Asistencia a víctimas,N/A,N/A,Personas afectadas,Avda. Piedra Buena 3280 - Piso 3,"
    "Villa Lugano,8,Lunes a Viernes,8 a 15,N/A,delitos@buenosaires.gob.ar,"
    "https://buenosaires.gob.ar/x,archivo.csv\n"
    "Centro de día,Centro Norte,Taller,Personas mayores,Av. Corrientes 1234,Balvanera,3,"
    "Lunes a Viernes,9 a 17,4370-9702,centro@buenosaires.gob.ar,"
    "https://buenosaires.gob.ar/y,archivo.csv\n"
).encode()


@pytest.fixture
def captura(conexion: Connection):
    cargar_catalogo(conexion)

    def crear(source_id: str) -> uuid.UUID:
        url_id = conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES (:s, :u, 'DETALLE', 'DESCARGA_ARCHIVO') "
                "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'DETALLE' RETURNING id"
            ),
            {"s": source_id, "u": f"https://cdn.example/{source_id}.csv"},
        ).scalar_one()
        config = conexion.execute(
            text(
                "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
                " ORDER BY version DESC LIMIT 1"
            ),
            {"s": source_id},
        ).scalar_one()
        corrida = conexion.execute(
            text(
                "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
                " extractor_version, solicitadas, descargadas, procesadas, fin) "
                "VALUES (:s, :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
            ),
            {"s": source_id, "c": config},
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
                "url": f"https://cdn.example/{source_id}.csv",
                "sha": sha,
                "uri": f"objeto://sha256/{sha}",
            },
        ).scalar_one()

    return crear


def _importar(conexion: Connection, contenido: bytes, dataset, captura_id):
    return ImportadorDirectorios(conexion).importar(
        contenido,
        dataset=dataset,
        captura_id=captura_id,
        capturado_en=dt.datetime(2026, 3, 1, tzinfo=dt.UTC),
    )


# --- AT-063: coordenadas en grilla local -------------------------------------


def test_at063_una_coordenada_en_grilla_local_no_se_usa_como_wgs84(
    conexion: Connection, captura
) -> None:
    """`POINT (28615.88 70947.08)` interpretado como longitud y latitud está
    fuera del planeta; con los ejes invertidos, en el Golfo de Guinea."""
    resultado = _importar(conexion, CSV_COMUNAS, COMUNAS, captura("F20"))
    assert resultado.coordenadas_sin_crs == 2
    assert resultado.coordenadas_usables == 0

    filas = conexion.execute(
        text("SELECT lat, lng, crs, coordenadas_origen, observaciones FROM punto_versiones")
    ).all()
    assert all(f.lat is None and f.lng is None and f.crs is None for f in filas)
    assert all(f.coordenadas_origen["formato"] == "WKT" for f in filas)
    assert all("inventar una ubicación" in f.observaciones for f in filas)


def test_at063_la_incidencia_dice_que_falta_confirmar_la_proyeccion(
    conexion: Connection, captura
) -> None:
    _importar(conexion, CSV_COMUNAS, COMUNAS, captura("F20"))
    incidencia = conexion.execute(
        text(
            "SELECT descripcion, severidad FROM incidencias_revision "
            " WHERE source_id = 'F20' AND tipo = 'DATO_FALTANTE_CRITICO'"
        )
    ).one()
    assert incidencia.severidad == "HIGH"
    assert "confirmar la proyección" in incidencia.descripcion


def test_una_coordenada_plausible_como_wgs84_si_se_usa() -> None:
    """La regla descarta, no confirma: un par dentro del rango se usa y se
    declara su CRS, pero seguir dentro del rango no prueba la proyección."""
    lat, lng, crs, observacion = _coordenadas("POINT (-58.3816 -34.6037)")
    assert (lat, lng, crs) == (-34.6037, -58.3816, "EPSG:4326")
    assert observacion is None


def test_una_geometria_ilegible_se_conserva_cruda() -> None:
    lat, lng, crs, observacion = _coordenadas("MULTIPOLYGON (((1 2, 3 4)))")
    assert (lat, lng, crs) == (None, None, None)
    assert "se conserva cruda" in observacion


# --- AT-059: N/A no es un teléfono -------------------------------------------


def test_at059_un_literal_de_sin_dato_no_se_carga_como_telefono(
    conexion: Connection, captura
) -> None:
    """Cargar «N/A» hace que alguien lo marque, o que el sistema conversacional
    lo lea en voz alta como si fuera un número."""
    resultado = _importar(conexion, CSV_EFECTORES, EFECTORES, captura("F60"))
    assert resultado.literales_sin_dato >= 1

    valores = conexion.execute(text("SELECT valor_crudo FROM canales")).scalars().all()
    assert not any(v.strip().lower() in {"n/a", "na", "s/d"} for v in valores)

    # El otro canal de la misma fila sí se conserva: perder el mail porque
    # falta el teléfono sería descartar un dato bueno por uno malo.
    correos = (
        conexion.execute(text("SELECT valor_crudo FROM canales WHERE tipo = 'EMAIL'"))
        .scalars()
        .all()
    )
    assert "delitos@buenosaires.gob.ar" in correos


def test_un_nombre_que_dice_na_no_se_pega_al_programa(conexion: Connection, captura) -> None:
    """La columna `nombre` del dataset trae «N/A» en muchas filas. Concatenarlo
    produciría puntos llamados «Asistencia a víctimas — N/A»."""
    _importar(conexion, CSV_EFECTORES, EFECTORES, captura("F60"))
    nombres = conexion.execute(text("SELECT nombre FROM puntos_atencion")).scalars().all()
    assert "Asistencia a víctimas" in nombres
    assert not any("N/A" in n for n in nombres)


# --- AT-060 y AT-061: dirección y horarios -----------------------------------


def test_at060_la_direccion_se_conserva_como_la_escribio_la_fuente(
    conexion: Connection, captura
) -> None:
    """El piso viene dentro del texto de la dirección. Componer una legible a
    partir de dos fuentes que no coinciden produce una dirección que no existe
    en ninguna de las dos."""
    _importar(conexion, CSV_COMUNAS, COMUNAS, captura("F20"))
    filas = conexion.execute(
        text("SELECT direccion_cruda, direccion_legible FROM punto_versiones ORDER BY 1")
    ).all()
    assert "Lopez, Vicente 2050, 3 piso" in [f.direccion_cruda for f in filas]
    assert all(f.direccion_legible is None for f in filas)


def test_at061_el_horario_es_del_canal_presencial_y_no_se_copia(
    conexion: Connection, captura
) -> None:
    """El horario de la sede no es el del teléfono ni el del correo."""
    _importar(conexion, CSV_EFECTORES, EFECTORES, captura("F60"))
    por_tipo = dict(
        conexion.execute(
            text("SELECT tipo, count(*) FILTER (WHERE horario IS NOT NULL) FROM canales GROUP BY 1")
        ).all()
    )
    assert por_tipo.get("PRESENCIAL", 0) >= 1
    assert por_tipo.get("TELEFONO", 0) == 0
    assert por_tipo.get("EMAIL", 0) == 0

    horario = conexion.execute(
        text("SELECT horario FROM canales WHERE tipo = 'PRESENCIAL' LIMIT 1")
    ).scalar_one()
    assert "Lunes a Viernes" in horario


# --- Contrato e idempotencia --------------------------------------------------


def test_cada_punto_nace_con_la_evidencia_de_su_fila(conexion: Connection, captura) -> None:
    _importar(conexion, CSV_EFECTORES, EFECTORES, captura("F60"))
    filas = conexion.execute(
        text(
            "SELECT e.selector, e.tipo, e.fragmento FROM canales c "
            "  JOIN evidencias e ON e.id = c.evidencia_id ORDER BY e.selector LIMIT 1"
        )
    ).one()
    assert filas.tipo == "CAMPO_CSV"
    assert filas.selector.startswith("fila:")
    assert "programa=" in filas.fragmento


def test_dos_corridas_versionan_el_punto_en_vez_de_duplicarlo(
    conexion: Connection, captura
) -> None:
    identificador = captura("F20")
    primera = _importar(conexion, CSV_COMUNAS, COMUNAS, identificador)
    segunda = _importar(conexion, CSV_COMUNAS, COMUNAS, identificador)
    assert primera.puntos_creados == 2
    assert segunda.puntos_creados == 0
    assert segunda.puntos_conocidos == 2
    assert conexion.execute(text("SELECT count(*) FROM puntos_atencion")).scalar_one() == 2
    # La segunda corrida deja una versión nueva y cierra la anterior.
    abiertas = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones "
            " WHERE entidad_tipo = 'punto_atencion' AND known_hasta IS NULL"
        )
    ).scalar_one()
    assert abiertas == 2


def test_un_dataset_sin_las_columnas_declaradas_no_se_importa(
    conexion: Connection, captura
) -> None:
    with pytest.raises(FormaInesperada, match="no trae las columnas"):
        _importar(conexion, b"otra,cosa\n1,2\n", COMUNAS, captura("F20"))
