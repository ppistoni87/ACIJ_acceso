"""HU-035 y HU-039: los reportes de entrega se verifican, no se declaran.

Estas pruebas existen porque un mapa de trazabilidad y un estado de backlog
envejecen en silencio: alguien renombra una prueba o mueve un módulo y el
documento sigue diciendo que todo está cubierto. Acá se rompen en ese momento.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import Connection, text

from backend_normativo.calidad import backlog, trazabilidad

pytestmark = pytest.mark.integracion

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def test_el_mapa_de_trazabilidad_cubre_los_ochenta_casos() -> None:
    """El mapa no puede citar casos que el paquete no tiene ni pruebas que no
    existen: `construir` falla en cualquiera de los dos casos."""
    reporte = trazabilidad.construir(raiz=RAIZ)
    assert reporte.total == 80
    assert reporte.cubiertos + reporte.parciales + reporte.no_ejecutados == 80


def test_ningun_caso_no_ejecutado_queda_sin_motivo() -> None:
    """Un caso sin pruebas tiene que decir qué capacidad falta. «Pendiente» no
    es un motivo: no le dice a nadie qué habría que construir."""
    reporte = trazabilidad.construir(raiz=RAIZ)
    sin_motivo = [c.id for c in reporte.casos if c.estado == "NO_EJECUTADO" and not c.motivo]
    assert sin_motivo == []


def test_ningun_caso_parcial_queda_sin_decir_que_le_falta() -> None:
    reporte = trazabilidad.construir(raiz=RAIZ)
    sin_falta = [c.id for c in reporte.casos if c.estado == "CUBIERTO_PARCIAL" and not c.falta]
    assert sin_falta == []


def test_el_backlog_cubre_las_ciento_veintitres_historias(conexion: Connection) -> None:
    """Cada historia transversal declara estado y cada evidencia que declara
    existe; las de fuente salen de la base."""
    reporte = backlog.construir(conexion, raiz=RAIZ)
    assert reporte.total == 123
    assert len(reporte.transversales) == 40
    assert len(reporte.fuentes) == 83


def test_toda_historia_no_cerrada_dice_que_le_falta(conexion: Connection) -> None:
    reporte = backlog.construir(conexion, raiz=RAIZ)
    sin_explicacion = [h.id for h in reporte.transversales if h.estado != "CERRADA" and not h.falta]
    assert sin_explicacion == []


def _repo_espejo(destino: pathlib.Path, salvo: pathlib.Path) -> pathlib.Path:
    """Un árbol enlazado al repositorio con un solo archivo propio.

    Sirve para probar qué hace el reporte con un estado distinto del real sin
    copiar el repositorio entero ni tocar el que está en disco.
    """
    destino.mkdir(parents=True, exist_ok=True)
    reales = set(salvo.parts[:-1])
    for hijo in RAIZ.iterdir():
        if hijo.name.startswith("."):
            continue
        if hijo.name not in reales:
            (destino / hijo.name).symlink_to(hijo)
    rama = destino
    origen = RAIZ
    for parte in salvo.parts[:-1]:
        rama = rama / parte
        origen = origen / parte
        rama.mkdir(exist_ok=True)
        for hijo in origen.iterdir():
            if hijo.name in salvo.parts or (rama / hijo.name).exists():
                continue
            (rama / hijo.name).symlink_to(hijo)
    return destino


def test_toda_historia_bloqueada_dice_quien_la_desbloquea(conexion: Connection) -> None:
    """«Bloqueada» y «no la hicimos» se leen igual si no dice a quién esperar.

    Un backlog que no marca la diferencia deja que «bloqueada» se use como
    excusa: nadie puede reclamar el desbloqueo porque no dice a quién.
    """
    reporte = backlog.construir(conexion, raiz=RAIZ)
    bloqueadas = [h for h in reporte.transversales if h.estado == "BLOQUEADA"]
    assert bloqueadas, "se esperaba al menos una historia bloqueada declarada"
    for historia in bloqueadas:
        assert historia.bloqueador, historia.id
        assert historia.responsable_rol, historia.id
        assert historia.desbloquea_con, historia.id


def test_una_historia_bloqueada_sin_responsable_rompe_el_reporte(
    conexion: Connection, tmp_path
) -> None:
    """No alcanza con pedirlo en la revisión: el reporte tiene que negarse.

    Si sólo lo comprueba una prueba sobre el archivo de hoy, mañana alguien
    declara una historia bloqueada sin responsable y el reporte la publica igual.
    """
    declarado = json.loads((RAIZ / backlog.RUTA_ESTADO).read_text())
    alguna = next(hu for hu, e in declarado["transversales"].items() if e["estado"] == "BLOQUEADA")
    declarado["transversales"][alguna].pop("responsable_rol")

    # La evidencia se verifica contra rutas que existan, así que el árbol real se
    # enlaza y sólo se reemplaza el archivo de estado.
    raiz = _repo_espejo(tmp_path / "repo", backlog.RUTA_ESTADO)
    (raiz / backlog.RUTA_ESTADO).write_text(
        json.dumps(declarado, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(backlog.EvidenciaInexistente, match="sin decir qué las bloquea"):
        backlog.construir(conexion, raiz=raiz)


def test_toda_fuente_detenida_dice_por_que(conexion: Connection) -> None:
    """Una fuente bloqueada sin motivo es indistinguible de una que nadie miró."""
    reporte = backlog.construir(conexion, raiz=RAIZ)
    mudas = [h.id for h in reporte.fuentes if h.estado == "BLOQUEADA" and not h.detencion]
    assert mudas == []


def test_los_estados_declarados_son_del_vocabulario() -> None:
    declarado = json.loads((RAIZ / backlog.RUTA_ESTADO).read_text())["transversales"]
    fuera = {
        hu: entrada["estado"]
        for hu, entrada in declarado.items()
        if entrada["estado"] not in backlog.ESTADOS
    }
    assert fuera == {}


def _metricas(**cambios: object) -> dict:
    """Una fuente que no dio nada: lo que cambia entre casos es por qué."""
    base: dict = {
        "alias_of": None,
        "access_status": "NO_VERIFICADO",
        "estado": "ACTIVE",
        "motivo_estado": None,
        "exclusion_reason": None,
        "responsable_rol": None,
        "urls": 1,
        "capturas": 0,
        "documentos": 0,
        "versiones": 0,
        "unidades": 0,
        "puntos": 0,
        "normas": 0,
        "campos": 0,
        "publicadas": 0,
        "incidencias": 0,
    }
    base.update(cambios)
    return base


_HISTORIA = {
    "id": "HU-FXX",
    "title": "Una fuente cualquiera",
    "source_id": "FXX",
    "owner_capability": "ingesta",
    "priority": "P2",
}


@pytest.mark.parametrize(
    ("estado_catalogo", "esperado"),
    [
        ("RETIRED", backlog.NO_SE_INGESTA),
        ("REFERENCE_ONLY", backlog.NO_SE_INGESTA),
        ("MANUAL", backlog.ESPERA_CARGA_MANUAL),
        ("ACTIVE", "NO_INICIADA"),
    ],
)
def test_una_decision_del_catalogo_no_se_reporta_como_recorrido_pendiente(
    estado_catalogo: str, esperado: str
) -> None:
    """Sin capturas no alcanza para decir «todavía no se recorrió».

    Una fuente retirada, una de referencia y una de carga manual tampoco tienen
    capturas, y llamarlas no iniciadas convierte una decisión ya registrada en
    trabajo pendiente que nadie va a hacer porque no hay nada que hacer. Solo la
    fuente ACTIVE sin capturas es un recorrido que falta.
    """
    historia = backlog._historia_de_fuente(_HISTORIA, _metricas(estado=estado_catalogo))
    assert historia.estado == esperado
    assert historia.detencion


def _decididas_por_el_catalogo(conexion: Connection) -> set[str]:
    """Las fuentes que el catálogo declaró retiradas, de referencia o manuales."""
    estados = [*backlog.ESTADOS_SIN_INGESTA, backlog.ESTADO_MANUAL]
    filas = conexion.execute(
        text("SELECT source_id FROM fuentes WHERE estado = ANY(:estados)"),
        {"estados": estados},
    ).scalars()
    return set(filas)


def test_ninguna_fuente_decidida_por_el_catalogo_figura_no_iniciada(
    conexion: Connection,
) -> None:
    """La misma regla, contra el catálogo real y no contra un diccionario."""
    reporte = backlog.construir(conexion, raiz=RAIZ)
    decididas = _decididas_por_el_catalogo(conexion)
    mal_rotuladas = {
        h.source_id
        for h in reporte.fuentes
        if h.estado == "NO_INICIADA" and h.source_id in decididas
    }
    assert mal_rotuladas == set()
