"""P-006 criterio 3: un importe histórico no es el importe de hoy.

El error que el criterio nombra es tomar el último renglón de la descarga más
reciente y servirlo como el monto vigente. La tabla del Consejo del Salario lo
hace evidente: en septiembre de 2026 publica tres importes y los tres empiezan
a regir en octubre o después.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import Connection, text

from backend_normativo.curacion.montos import CuradorDeMontos

pytestmark = pytest.mark.integracion

POLITICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"

TABLA = """Fecha Salario Mínimo, Vital y Móvil Prestación por Desempleo monto mínimo
a partir del 1/10/2026 $ 391.200 $ 195.600
a partir del 1/11/2026 $ 398.800 $ 199.400"""

COLUMNAS = ["SMVM", "PRESTACION_DESEMPLEO_MINIMO"]


def _fuente_con_texto(
    conexion: Connection,
    source_id: str,
    texto: str,
    *,
    columnas: list[str] | None = None,
) -> None:
    import json

    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso) VALUES (:s, :n, 'PORTAL_NORMATIVO', 'ACTIVE', "
            "'ACCESIBLE', 'P0', :p)"
        ),
        {"s": source_id, "n": f"Fuente {source_id}", "p": POLITICA},
    )
    conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador, "
            "selector_config) VALUES (:s, 1, 'HTML_ESTATICO', CAST(:c AS jsonb))"
        ),
        {
            "s": source_id,
            "c": json.dumps({"montos": {"columnas": columnas}} if columnas else {}),
        },
    )
    url = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"s": source_id, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text("SELECT id FROM fuente_config_versiones WHERE source_id = :s"), {"s": source_id}
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES (:s, :c, 'EN_CURSO', 'prueba') RETURNING id"
        ),
        {"s": source_id, "c": cfg},
    ).scalar_one()
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri) "
            "VALUES (:c, :u, :h, :o) RETURNING id"
        ),
        {
            "c": corrida,
            "u": url,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://var/objetos/{uuid.uuid4()}",
        },
    ).scalar_one()
    documento = conexion.execute(
        text("INSERT INTO documentos (source_id, tipo) VALUES (:s, 'GUIA') RETURNING id"),
        {"s": source_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            "tipo_fecha, hash_texto, modo_extraccion, extractor_version, texto_extraido) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML', 'prueba', :t)"
        ),
        {
            "d": documento,
            "c": captura,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "t": texto,
        },
    )


def _valores(conexion: Connection, codigo: str) -> list[dict]:
    return [
        dict(f)
        for f in conexion.execute(
            text(
                "SELECT pv.valor, rv.valid_desde, rv.valid_hasta, rv.valid_tipo, "
                "       rv.estado_revision, pv.publicable, pv.rango_aplicacion "
                "  FROM parametro_valores pv "
                "  JOIN parametros p ON p.id = pv.parametro_id "
                "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                " WHERE p.codigo = :c ORDER BY rv.valid_desde"
            ),
            {"c": codigo},
        ).mappings()
    ]


def _incidencias(conexion: Connection, source_id: str) -> list[str]:
    return [
        f[0]
        for f in conexion.execute(
            text(
                "SELECT descripcion FROM incidencias_revision "
                " WHERE source_id = :s AND estado = 'ABIERTA'"
            ),
            {"s": source_id},
        )
    ]


def test_cada_importe_entra_con_el_periodo_que_la_tabla_declara(conexion: Connection) -> None:
    _fuente_con_texto(conexion, "TM1", TABLA, columnas=COLUMNAS)

    resultado = CuradorDeMontos(conexion).cargar("TM1")

    assert resultado.filas_leidas == 2
    assert resultado.valores_creados == 4
    valores = _valores(conexion, "SMVM")
    assert [v["valor"] for v in valores] == [Decimal("391200"), Decimal("398800")]
    assert valores[0]["valid_hasta"] == dt.date(2026, 10, 31), "cierra el día anterior"
    assert valores[1]["valid_hasta"] is None
    assert valores[1]["valid_tipo"] == "ABIERTO_FIN"


def test_el_ultimo_descargado_no_rige_si_su_periodo_todavia_no_empezo(
    conexion: Connection,
) -> None:
    """El corazón del criterio.

    Se descarga en septiembre una tabla cuyos tres importes empiezan en octubre.
    Ninguno rige hoy, y el más nuevo no gana por ser el más nuevo.
    """
    _fuente_con_texto(conexion, "TM2", TABLA, columnas=COLUMNAS)
    CuradorDeMontos(conexion).cargar("TM2")

    rigen_hoy = conexion.execute(
        text(
            "SELECT count(*) FROM parametro_valores pv "
            "  JOIN parametros p ON p.id = pv.parametro_id "
            " WHERE p.codigo = 'SMVM' AND pv.rango_aplicacion @> DATE '2026-09-10'"
        )
    ).scalar_one()
    rigen_en_octubre = conexion.execute(
        text(
            "SELECT count(*) FROM parametro_valores pv "
            "  JOIN parametros p ON p.id = pv.parametro_id "
            " WHERE p.codigo = 'SMVM' AND pv.rango_aplicacion @> DATE '2026-10-15'"
        )
    ).scalar_one()

    assert rigen_hoy == 0, "en septiembre no rige ninguno de los tres"
    assert rigen_en_octubre == 1, "y en octubre rige exactamente uno"


def test_cargar_un_importe_no_es_aprobarlo(conexion: Connection) -> None:
    """Entra como candidato y no publicable: publicarlo es una decisión."""
    _fuente_con_texto(conexion, "TM3", TABLA, columnas=COLUMNAS)
    CuradorDeMontos(conexion).cargar("TM3")

    valores = _valores(conexion, "SMVM")
    assert all(v["estado_revision"] == "CANDIDATE" for v in valores)
    assert all(v["publicable"] is False for v in valores)


def test_un_renglon_con_otra_cantidad_de_importes_se_rechaza(conexion: Connection) -> None:
    """Acomodarlo sería inventar a qué concepto pertenece cada número."""
    _fuente_con_texto(
        conexion,
        "TM4",
        "a partir del 1/10/2026 $ 391.200 $ 195.600 $ 400.000",
        columnas=COLUMNAS,
    )

    resultado = CuradorDeMontos(conexion).cargar("TM4")

    assert resultado.valores_creados == 0
    assert len(resultado.rechazadas) == 1
    assert any("declara 2 columna(s)" in i for i in _incidencias(conexion, "TM4"))


def test_un_importe_sin_fecha_no_se_carga_y_se_registra(conexion: Connection) -> None:
    """Tomar la fecha de descarga como su período es justo lo que se prohíbe."""
    _fuente_con_texto(
        conexion,
        "TM5",
        "El monto de la beca Progresar es de $35.000.-",
        columnas=["BECA_PROGRESAR"],
    )

    resultado = CuradorDeMontos(conexion).cargar("TM5")

    assert resultado.valores_creados == 0
    assert resultado.sin_periodo == 1
    assert any("sin declarar desde cuándo rigen" in i for i in _incidencias(conexion, "TM5"))


def test_sin_columnas_declaradas_no_se_adivina(conexion: Connection) -> None:
    _fuente_con_texto(conexion, "TM6", TABLA)

    resultado = CuradorDeMontos(conexion).cargar("TM6")

    assert resultado.valores_creados == 0
    assert any("sería adivinarlo" in i for i in _incidencias(conexion, "TM6"))


def test_cargar_dos_veces_no_duplica(conexion: Connection) -> None:
    _fuente_con_texto(conexion, "TM7", TABLA, columnas=COLUMNAS)

    primera = CuradorDeMontos(conexion).cargar("TM7")
    segunda = CuradorDeMontos(conexion).cargar("TM7")

    assert primera.valores_creados == 4
    assert segunda.valores_creados == 0
    assert segunda.valores_existentes == 4


def test_dos_importes_publicables_no_pueden_pisarse_en_el_tiempo(
    conexion: Connection, viola_restriccion
) -> None:
    """Lo cuida el esquema, no el cargador: la restricción de exclusión de
    `parametro_valores` es lo que impide que un importe histórico aprobado
    conviva con el actual sobre la misma fecha."""
    _fuente_con_texto(conexion, "TM8", TABLA, columnas=COLUMNAS)
    CuradorDeMontos(conexion).cargar("TM8")

    versiones = [
        f[0]
        for f in conexion.execute(
            text(
                "SELECT rv.id FROM parametro_valores pv "
                "  JOIN parametros p ON p.id = pv.parametro_id "
                "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                " WHERE p.codigo = 'SMVM' ORDER BY rv.valid_desde"
            )
        )
    ]
    # Aprobar el primero lo vuelve publicable. Aprobar el segundo con un período
    # que lo pisa tiene que fallar, y falla en la misma sentencia: un disparador
    # propaga el cambio a `parametro_valores` y ahí la exclusión lo rechaza.
    conexion.execute(
        text("UPDATE registro_versiones SET estado_revision = 'APPROVED' WHERE id = :id"),
        {"id": versiones[0]},
    )
    with viola_restriccion("sin_solapamiento"):
        conexion.execute(
            text(
                "UPDATE registro_versiones SET estado_revision = 'APPROVED', "
                "  valid_desde = '2026-10-15' WHERE id = :id"
            ),
            {"id": versiones[1]},
        )
