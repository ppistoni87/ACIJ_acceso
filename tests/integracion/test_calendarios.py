"""HU-016: el calendario entra con evidencia, como el resto del corpus.

Un feriado sin evidencia es un día no laborable inventado, y con eso se calculan
vencimientos que después alguien pierde. El esquema lo impide; estas pruebas
fijan que el importador no busque la vuelta.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.plazos import calendarios
from backend_normativo.plazos.computo import calcular_vencimiento

pytestmark = pytest.mark.integracion


def _archivo(feriados: list[tuple[str, str, str]]) -> bytes:
    """Con la forma del archivo oficial: `mainEntity.itemListElement`."""
    return json.dumps(
        {
            "additionalProperty": {"name": "timezone", "value": "America/Argentina/Buenos_Aires"},
            "mainEntity": {
                "itemListElement": [
                    {
                        "position": i,
                        "item": {
                            "name": nombre,
                            "startDate": fecha,
                            "additionalProperty": {"name": "tipo", "value": clase},
                        },
                    }
                    for i, (fecha, nombre, clase) in enumerate(feriados, start=1)
                ]
            },
        },
        ensure_ascii=False,
    ).encode()


FERIADOS = [
    ("2026-01-01", "Año Nuevo.", "inamovible"),
    ("2026-03-24", "Día Nacional de la Memoria.", "inamovible"),
    ("2026-05-01", "Día del Trabajador.", "inamovible"),
]


@pytest.fixture
def captura(conexion: Connection) -> uuid.UUID:
    cargar_catalogo(conexion)
    url_id = calendarios.registrar_url(conexion, 2026)
    config = conexion.execute(
        text(
            "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
            " ORDER BY version DESC LIMIT 1"
        ),
        {"s": calendarios.SOURCE_ID},
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            " extractor_version, solicitadas, descargadas, procesadas, fin) "
            "VALUES (:s, :c, 'COMPLETA', 'prueba', 1, 1, 1, now()) RETURNING id"
        ),
        {"s": calendarios.SOURCE_ID, "c": config},
    ).scalar_one()
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    return conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
            " bytes, sha256_raw, objeto_uri) "
            "VALUES (:co, :u, :url, 200, 'application/json', 100, :sha, :uri) RETURNING id"
        ),
        {
            "co": corrida,
            "u": url_id,
            "url": calendarios.url_del_anio(2026),
            "sha": sha,
            "uri": f"objeto://sha256/{sha}",
        },
    ).scalar_one()


def test_cada_feriado_queda_atado_al_fragmento_que_lo_declara(
    conexion: Connection, captura
) -> None:
    resultado = calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    assert resultado.feriados_nuevos == 3

    filas = conexion.execute(
        text(
            "SELECT ce.fecha, ce.es_habil, ce.motivo, e.fragmento, e.selector, e.tipo "
            "  FROM calendario_excepciones ce JOIN evidencias e ON e.id = ce.evidencia_id "
            " ORDER BY ce.fecha"
        )
    ).all()
    assert len(filas) == 3
    assert all(f.es_habil is False for f in filas)
    assert all(f.tipo == "CAMPO_JSON" for f in filas)
    assert filas[0].selector.startswith("itemListElement[")
    assert "Año Nuevo" in filas[0].fragmento
    # La clase del feriado se conserva: no todos se computan igual en todos los
    # regímenes y perderla obligaría a volver a la fuente.
    assert "inamovible" in filas[0].motivo


def test_la_cobertura_declarada_es_el_año_entero(conexion: Connection, captura) -> None:
    calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    fila = conexion.execute(
        text("SELECT fecha_desde, fecha_hasta, fuente_id FROM calendarios")
    ).one()
    assert (fila.fecha_desde, fila.fecha_hasta) == (dt.date(2026, 1, 1), dt.date(2026, 12, 31))
    assert fila.fuente_id == calendarios.SOURCE_ID


def test_importar_dos_veces_no_duplica_feriados(conexion: Connection, captura) -> None:
    primera = calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    segunda = calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    assert primera.feriados_nuevos == 3
    assert segunda.feriados_nuevos == 0
    assert segunda.feriados_conocidos == 3
    assert conexion.execute(text("SELECT count(*) FROM calendario_excepciones")).scalar_one() == 3


def test_un_archivo_vacio_no_produce_un_calendario_sin_feriados(
    conexion: Connection, captura
) -> None:
    """Cargar un calendario vacío haría que todos los plazos se computen como si
    no hubiera feriados: peor que no tener calendario, porque parece que sí."""
    with pytest.raises(calendarios.CalendarioInvalido, match="ningún feriado"):
        calendarios.importar(conexion, _archivo([]), captura_id=captura, anio=2026)


def test_un_archivo_con_otra_forma_no_se_importa(conexion: Connection, captura) -> None:
    with pytest.raises(calendarios.CalendarioInvalido, match=r"[Cc]ambió de forma"):
        calendarios.importar(conexion, b'{"otra": "cosa"}', captura_id=captura, anio=2026)


def test_los_feriados_de_otro_año_no_entran(conexion: Connection, captura) -> None:
    """El archivo de un año puede traer fechas del anterior o del siguiente; el
    calendario declara cubrir uno solo."""
    mezclados = [*FERIADOS, ("2027-01-01", "Año Nuevo.", "inamovible")]
    resultado = calendarios.importar(conexion, _archivo(mezclados), captura_id=captura, anio=2026)
    assert resultado.feriados_nuevos == 3
    fechas = conexion.execute(text("SELECT fecha FROM calendario_excepciones")).scalars().all()
    assert all(f.year == 2026 for f in fechas)


def test_el_calendario_cargado_computa_el_vencimiento(conexion: Connection, captura) -> None:
    """De punta a punta: se importa, se carga y se calcula contra él."""
    calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    calendario = calendarios.cargar(conexion, para=dt.date(2026, 3, 20))
    assert calendario is not None

    resultado = calcular_vencimiento(
        inicio=dt.date(2026, 3, 20),
        cantidad=5,
        unidad="dias",
        tipo_dia="HABIL_ADMINISTRATIVO",
        calendario=calendario,
    )
    assert resultado.vencimiento == dt.date(2026, 3, 30)
    assert "Día Nacional de la Memoria" in resultado.fundamento


def test_sin_calendario_para_esa_fecha_no_se_devuelve_otro(conexion: Connection, captura) -> None:
    """Devolver el calendario de otro año porque es el único que hay produciría
    un vencimiento calculado con feriados que no son los de ese año."""
    calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    assert calendarios.cargar(conexion, para=dt.date(2028, 3, 20)) is None


def test_la_fuente_del_calendario_no_entra_al_inventario_del_corpus(
    conexion: Connection,
) -> None:
    """El manifiesto relevó 83 fuentes del corpus jurídico y ninguna es un
    calendario. Mezclarlas haría que el inventario diga algo que el manual no
    dice."""
    cargar_catalogo(conexion)
    assert conexion.execute(text("SELECT count(*) FROM fuentes")).scalar_one() == 83

    calendarios.registrar_fuente(conexion)
    fila = conexion.execute(
        text("SELECT origen, alcance FROM fuentes WHERE source_id = :s"),
        {"s": calendarios.SOURCE_ID},
    ).one()
    assert fila.origen == "operativa"
    assert "integra el inventario del corpus" in fila.alcance


# --- Calendarios jurisdiccionales derivados -------------------------------------


def test_deriva_el_calendario_local_de_los_feriados_nacionales(
    conexion: Connection, captura
) -> None:
    """Los feriados nacionales rigen en todo el país, así que repetirlos en un
    calendario local es cierto en lo que dice. Lo que le falta son las ferias
    administrativas que fija la propia jurisdicción."""
    calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)

    derivado = calendarios.derivar_jurisdiccional(conexion, jurisdiccion="AR-C", anio=2026)

    assert derivado is not None
    nombre, feriados = conexion.execute(
        text(
            "SELECT c.nombre, count(e.id) FROM calendarios c "
            "  LEFT JOIN calendario_excepciones e ON e.calendario_id = c.id "
            " WHERE c.id = :c GROUP BY c.nombre"
        ),
        {"c": derivado},
    ).one()
    # La limitación viaja en el nombre porque el nombre viaja en el fundamento de
    # cada cómputo: un calendario incompleto que dice qué le falta es mejor que
    # ninguno, y uno que no lo dice es peor que ninguno.
    assert "sin ferias administrativas locales" in nombre
    assert feriados == len(FERIADOS)


def test_derivar_deja_abierta_la_incidencia_de_lo_que_falta(conexion: Connection, captura) -> None:
    """Que el calendario se derive solo no significa que esté completo. Sin la
    incidencia, un plazo computado de menos parecería computado bien."""
    calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    calendarios.derivar_jurisdiccional(conexion, jurisdiccion="AR-C", anio=2026)

    abiertas = (
        conexion.execute(
            text(
                "SELECT descripcion FROM incidencias_revision "
                " WHERE estado = 'ABIERTA' AND descripcion LIKE '%ferias administrativas%'"
            )
        )
        .scalars()
        .all()
    )
    assert len(abiertas) == 1
    assert "puede vencer más tarde de lo calculado" in abiertas[0]


def test_derivar_dos_veces_devuelve_el_mismo_calendario(conexion: Connection, captura) -> None:
    """Poblar es idempotente: la segunda corrida no puede dejar dos calendarios
    de la misma jurisdicción compitiendo por el mismo año."""
    calendarios.importar(conexion, _archivo(FERIADOS), captura_id=captura, anio=2026)
    primero = calendarios.derivar_jurisdiccional(conexion, jurisdiccion="AR-C", anio=2026)
    segundo = calendarios.derivar_jurisdiccional(conexion, jurisdiccion="AR-C", anio=2026)
    assert primero == segundo


def test_sin_calendario_nacional_no_se_deriva_nada(conexion: Connection) -> None:
    """No hay de dónde copiar los feriados. Inventar un calendario vacío diría
    que ese año no tuvo ninguno."""
    calendarios.registrar_fuente(conexion)
    assert calendarios.derivar_jurisdiccional(conexion, jurisdiccion="AR-C", anio=2026) is None
