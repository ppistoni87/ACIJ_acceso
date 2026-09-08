"""HU-026: el ciclo periódico encadenado, de la planificación al evento.

Monitorear no es correr un comando: es que cada fuente se vuelva a mirar cuando
le toca. Lo que estas pruebas fijan es que el ciclo respete la frecuencia
declarada —no revisar de más ni dejar de revisar— y que una corrida sin trabajo
se distinga de una corrida fallida.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.monitoreo.ciclo import correr, formatear

pytestmark = pytest.mark.integracion


def _corrida(conexion: Connection, source_id: str, cuando: dt.datetime) -> None:
    config = conexion.execute(
        text(
            "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
            " ORDER BY version DESC LIMIT 1"
        ),
        {"s": source_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            " extractor_version, solicitadas, descargadas, procesadas, inicio, fin) "
            "VALUES (:s, :c, 'COMPLETA', 'prueba', 1, 1, 1, :i, :i)"
        ),
        {"s": source_id, "c": config, "i": cuando},
    )


@pytest.fixture
def catalogo(conexion: Connection):
    cargar_catalogo(conexion)


# --- La frecuencia decide a quién le toca ------------------------------------


def test_una_fuente_recien_corrida_no_vuelve_a_la_cola(conexion: Connection, catalogo) -> None:
    """Revisar de más gasta la cuota de la fuente y no aporta nada."""
    ahora = dt.datetime.now(dt.UTC)
    for boletin in ("M01", "M02", "M03", "M04"):
        _corrida(conexion, boletin, ahora)

    resultado = correr(conexion, ahora=ahora)
    # Sólo los cuatro que se corrieron: M05 y M06 siguen pendientes con razón.
    assert not {"M01", "M02", "M03", "M04"} & set(resultado.pendientes)


def test_pasada_la_frecuencia_los_boletines_vuelven_a_la_cola(
    conexion: Connection, catalogo
) -> None:
    """Los boletines se monitorean a diario: a las veinticuatro horas les toca."""
    ahora = dt.datetime.now(dt.UTC)
    for boletin in ("M01", "M02", "M03", "M04"):
        _corrida(conexion, boletin, ahora)

    manana = ahora + dt.timedelta(days=1, minutes=1)
    resultado = correr(conexion, ahora=manana)
    assert {"M01", "M02", "M03", "M04"} <= set(resultado.pendientes)


def test_una_corrida_sin_trabajo_no_es_una_corrida_fallida(conexion: Connection, catalogo) -> None:
    """La frecuencia haciendo lo suyo se tiene que poder distinguir de un fallo."""
    ahora = dt.datetime.now(dt.UTC)
    # Sólo las que tienen configuración entran al planificador; las demás
    # quedan afuera por su cuenta.
    configuradas = conexion.execute(
        text("SELECT DISTINCT source_id FROM fuente_config_versiones")
    ).scalars()
    for source_id in configuradas:
        _corrida(conexion, source_id, ahora)

    resultado = correr(conexion, ahora=ahora)
    assert not resultado.hubo_trabajo
    assert any("no es una corrida fallida" in a for a in resultado.avisos)
    assert resultado.paso("planificacion").cuantos == 0


# --- El ciclo encadena y reporta cada paso -----------------------------------


def test_el_ciclo_encadena_la_revalidacion_y_cuenta_cada_paso(
    conexion: Connection, catalogo
) -> None:
    """El ciclo planifica y delega: no repite la captura ni la extracción."""
    llamadas: list[list[str]] = []

    def revalidar(fuentes: list[str]) -> dict[str, int]:
        llamadas.append(fuentes)
        return {
            "revisadas": len(fuentes),
            "versiones": 2,
            "con_cambios": 1,
            "impactadas": 3,
            "eventos": 1,
            "bloqueadas": 0,
        }

    resultado = correr(conexion, ahora=dt.datetime.now(dt.UTC), revalidar=revalidar)

    assert len(llamadas) == 1, "la revalidación se llama una sola vez por vuelta"
    assert llamadas[0] == resultado.pendientes
    assert resultado.paso("cambios").cuantos == 1
    assert resultado.paso("impacto").cuantos == 3
    assert resultado.paso("eventos").cuantos == 1


def test_en_seco_planifica_y_no_sale_a_la_red(conexion: Connection, catalogo) -> None:
    """Sirve para saber a quién le toca antes de gastar una petición."""
    resultado = correr(conexion, ahora=dt.datetime.now(dt.UTC))

    assert resultado.hubo_trabajo
    assert [p.nombre for p in resultado.pasos] == ["planificacion"]
    assert any("no se salió a la red" in a for a in resultado.avisos)


def test_el_limite_acota_cuantas_fuentes_entran_por_vuelta(conexion: Connection, catalogo) -> None:
    """Una vuelta que intenta con todas tarda lo que tarda la más lenta por la
    cantidad de fuentes; acotarla deja que el planificador la llame más seguido."""
    resultado = correr(conexion, ahora=dt.datetime.now(dt.UTC), limite=3)
    assert len(resultado.pendientes) <= 3


# --- La evidencia dice qué falta ---------------------------------------------


def test_la_evidencia_dice_que_el_ciclo_no_se_dispara_solo(conexion: Connection, catalogo) -> None:
    """Es una decisión de despliegue, no código que falte, y conviene que el
    reporte no deje creer que el corpus se actualiza solo."""
    texto = formatear(correr(conexion, ahora=dt.datetime.now(dt.UTC)))
    assert "no hace es" in texto
    assert "dispararse solo" in texto
    assert "bn monitoreo ciclo" in texto
