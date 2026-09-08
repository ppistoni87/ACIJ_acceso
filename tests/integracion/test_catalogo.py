"""HU-001: conciliación del alcance y conservación de cada fuente."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo import derivacion as der
from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.catalogo.manifiesto import cargar_manifiesto
from backend_normativo.catalogo.reconciliacion import construir_reporte, formatear

pytestmark = pytest.mark.integracion

# Parejas que el manual dejó duplicadas y que el catálogo tiene que resolver con
# un solo contenido canónico y su alias.
PAREJAS_ALIAS = {("F65", "F17"), ("F55", "F24"), ("F29", "F27"), ("F28", "F31")}

# Identificadores del anexo que el manual no acompaña con una URL inequívoca.
SIN_URL = {
    "F08",
    "F13",
    "F14",
    "F15",
    "F21",
    "F22",
    "F26",
    "F30",
    "F34",
    "F35",
    "F37",
    "F42",
    "F57",
    "F58",
    "F59",
}


@pytest.fixture
def catalogo_cargado(conexion: Connection):
    return cargar_catalogo(conexion)


def test_el_manifiesto_es_internamente_coherente() -> None:
    """Se valida antes de cargar: un cambio de forma tiene que verse acá y no a
    mitad de una ingesta."""
    assert cargar_manifiesto().validar_coherencia() == []


def test_se_conservan_los_83_identificadores(conexion: Connection, catalogo_cargado) -> None:
    ids = {fila[0] for fila in conexion.execute(text("SELECT source_id FROM fuentes"))}
    assert len(ids) == 83
    # Los 67 originales del manual, enteros.
    assert {f"F{n:02d}" for n in range(1, 68)} <= ids
    # Las 16 incorporaciones, con su prefijo propio.
    assert {f"D{n:02d}" for n in range(1, 11)} <= ids
    assert {f"M{n:02d}" for n in range(1, 7)} <= ids


def test_las_52_fichas_se_distinguen_de_las_15_excluidas(
    conexion: Connection, catalogo_cargado
) -> None:
    """La procedencia documental separa lo relevado en el manual de lo que solo
    figura en el anexo de excluidas."""
    por_origen = {
        fila[0]: fila[1]
        for fila in conexion.execute(text("SELECT origen, count(*) FROM fuentes GROUP BY origen"))
    }
    assert por_origen["manual_2026-08-31"] == 53
    assert por_origen["anexo_excluidas_manual_2026-08-31"] == 15
    assert por_origen["referencias_revisadas_2026-09-07"] == 15


def test_los_alias_apuntan_a_una_sola_fuente_canonica(
    conexion: Connection, catalogo_cargado
) -> None:
    """F17/F65, F24/F55, F27/F29 y F28/F31 son parejas, no fuentes nuevas."""
    parejas = {
        (fila[0], fila[1])
        for fila in conexion.execute(
            text("SELECT source_id, alias_of FROM fuentes WHERE alias_of IS NOT NULL")
        )
    }
    assert parejas == PAREJAS_ALIAS

    # Ninguna fuente canónica es a su vez alias: la cadena tiene un solo salto.
    canonicas = {canonica for _, canonica in parejas}
    alias = {a for a, _ in parejas}
    assert canonicas & alias == set()


def test_un_alias_no_esta_necesariamente_caido(conexion: Connection, catalogo_cargado) -> None:
    """`alias_of` y `access_status` son independientes: F65 duplica a F17, y eso
    no dice nada sobre si responde."""
    estado = conexion.execute(
        text("SELECT estado, access_status FROM fuentes WHERE source_id = 'F65'")
    ).one()
    assert estado == ("REFERENCE_ONLY", "NO_VERIFICADO")


def test_las_fuentes_sin_url_conservan_su_brecha(conexion: Connection, catalogo_cargado) -> None:
    """No se fabrica una dirección ni se declara la pérdida como resuelta."""
    sin_url = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT source_id FROM fuentes WHERE access_status = 'SIN_URL_CONOCIDA'")
        )
    }
    assert sin_url == SIN_URL

    urls_de_esas_fuentes = conexion.execute(
        text("SELECT count(*) FROM fuente_urls WHERE source_id = ANY(:ids)"),
        {"ids": sorted(SIN_URL)},
    ).scalar_one()
    assert urls_de_esas_fuentes == 0


def test_cada_brecha_tiene_incidencia_abierta_con_responsable(
    conexion: Connection, catalogo_cargado
) -> None:
    filas = conexion.execute(
        text(
            "SELECT f.source_id, i.estado, i.responsable_rol "
            "FROM fuentes f JOIN incidencias_revision i ON i.source_id = f.source_id "
            "WHERE f.access_status = 'SIN_URL_CONOCIDA' AND i.tipo = 'ACCESO_BLOQUEADO'"
        )
    ).all()
    assert {f[0] for f in filas} == SIN_URL
    assert all(estado == "ABIERTA" for _, estado, _ in filas)
    assert all(rol for *_, rol in filas)


def test_ninguna_fuente_arranca_como_activa(conexion: Connection, catalogo_cargado) -> None:
    """Activo significa que la ingesta corrió y funcionó. Este paquete no
    ingirió nada."""
    activas = conexion.execute(
        text("SELECT count(*) FROM fuentes WHERE estado = 'ACTIVE'")
    ).scalar_one()
    assert activas == 0


def test_una_fuente_retirada_explica_por_que(conexion: Connection, catalogo_cargado) -> None:
    """F06 y F09 son fuentes muertas: el catálogo conserva el motivo y la brecha
    de cobertura que dejan."""
    retiradas = conexion.execute(
        text("SELECT source_id, motivo_estado FROM fuentes WHERE estado = 'RETIRED' ORDER BY 1")
    ).all()
    assert [f[0] for f in retiradas] == ["F06", "F09"]
    assert all(motivo and len(motivo) > 20 for _, motivo in retiradas)


def test_la_carga_es_idempotente(conexion: Connection) -> None:
    """Reejecutarla no duplica fuentes, URLs, configuraciones ni incidencias."""
    primera = cargar_catalogo(conexion)
    conteos_1 = _conteos(conexion)
    segunda = cargar_catalogo(conexion)
    conteos_2 = _conteos(conexion)

    assert conteos_1 == conteos_2
    assert primera.fuentes_creadas == 83
    assert segunda.fuentes_creadas == 0
    assert segunda.fuentes_actualizadas == 83
    assert segunda.urls_creadas == 0
    assert segunda.incidencias_creadas == 0


def _conteos(conexion: Connection) -> dict[str, int]:
    return {
        tabla: conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()
        for tabla in (
            "fuentes",
            "fuente_urls",
            "fuente_config_versiones",
            "incidencias_revision",
            "jurisdicciones",
        )
    }


def test_cada_fuente_tiene_configuracion_con_adaptador_y_presupuesto(
    conexion: Connection, catalogo_cargado
) -> None:
    faltantes = conexion.execute(
        text(
            "SELECT count(*) FROM fuentes f "
            "WHERE NOT EXISTS (SELECT 1 FROM fuente_config_versiones c "
            "                  WHERE c.source_id = f.source_id)"
        )
    ).scalar_one()
    assert faltantes == 0

    sin_presupuesto = conexion.execute(
        text("SELECT count(*) FROM fuente_config_versiones WHERE presupuesto IS NULL")
    ).scalar_one()
    assert sin_presupuesto == 0


def test_infoleg_se_recorre_de_a_una_solicitud(conexion: Connection, catalogo_cargado) -> None:
    """El presupuesto de la especificación §6: concurrencia 1 para InfoLEG y
    NormativaBA, hasta 2 para el resto."""
    manifiesto = cargar_manifiesto()
    por_id = {f.source_id: f for f in manifiesto.sources}
    assert der.presupuesto_de(por_id["F01"])["delay_dominio_s"] == 2.0

    normativaba = next(
        f
        for f in manifiesto.sources
        if any("boletinoficial.buenosaires.gob.ar" in u for u in f.urls)
    )
    assert der.presupuesto_de(normativaba)["concurrencia"] == 1


def test_el_reporte_no_confunde_fuentes_con_leyes(conexion: Connection, catalogo_cargado) -> None:
    """83 fuentes no son 83 leyes: los denominadores se informan por separado."""
    reporte = construir_reporte(conexion)
    d = reporte.denominadores

    assert d.fuentes == 83
    assert d.alias == 4
    assert d.fuentes_canonicas == 79
    assert d.urls_registradas == 70
    # Nada ingerido todavía: el inventario no acredita corpus.
    assert d.normas == 0
    assert d.documentos == 0
    assert d.beneficios == 0

    assert reporte.ids_originales_presentes == 67
    assert len(reporte.ids_incorporados) == 16
    assert len(reporte.brechas_sin_url) == 15
    assert reporte.advertencias == []

    texto = formatear(reporte)
    assert "no acredita ingesta" in texto.replace("\n", " ")
