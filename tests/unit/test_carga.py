"""La mecánica del ensayo de carga: fases, filtraciones y fuentes caídas.

Sin base y sin servidor de la API. Lo que se prueba acá es que el ensayo mida
lo que dice medir; la corrida entera está en `bn calidad carga` y su informe en
`docs/reportes/carga_y_fallos.md`.
"""

from __future__ import annotations

import json

from backend_normativo.calidad.carga import (
    FASE_ANTES,
    Fallo,
    Peticion,
    ReporteCarga,
    ServidorDeMentira,
    _fase_de,
    _revisar,
    formatear,
    percentil,
    probar_fuente,
)


def _fallo(nombre: str, desde: float, duracion: float) -> Fallo:
    return Fallo(
        nombre=nombre,
        desde_s=desde,
        duracion_s=duracion,
        aplicar=lambda: None,
        revertir=lambda: None,
    )


def test_el_percentil_no_se_cae_con_la_lista_vacia() -> None:
    assert percentil([], 0.95) == 0.0
    assert percentil([10.0], 0.95) == 10.0


def test_la_fase_se_nombra_con_el_fallo() -> None:
    """«durante el fallo» mezclaría la caída del proveedor con la de la base."""
    fallos = [_fallo("proveedor", 10, 5), _fallo("base", 30, 5)]
    assert _fase_de(1, fallos) == FASE_ANTES
    assert _fase_de(12, fallos) == "durante · proveedor"
    assert _fase_de(20, fallos) == "después de · proveedor"
    assert _fase_de(31, fallos) == "durante · base"
    assert _fase_de(40, fallos) == "después de · base"


def test_se_detecta_un_estado_de_trabajo_que_se_filtro() -> None:
    hallazgos = _revisar('{"estado": "CANDIDATE"}', "/v1/normas", set())
    assert hallazgos and "CANDIDATE" in hallazgos[0].detalle


def test_se_detecta_el_rastro_interno_en_un_error() -> None:
    hallazgos = _revisar("Traceback (most recent call last)", "/v1/respuestas", set())
    assert hallazgos


def test_se_detecta_un_fragmento_que_no_es_del_corte() -> None:
    """Servir algo que no está publicado es el fallo que este ensayo busca."""
    cuerpo = json.dumps({"fuentes": [{"chunk_id": "ajeno"}, {"chunk_id": "propio"}]})
    hallazgos = _revisar(cuerpo, "/v1/respuestas", {"propio"})
    assert len(hallazgos) == 1
    assert hallazgos[0].detalle == "ajeno"


def test_un_cuerpo_limpio_no_denuncia_nada() -> None:
    cuerpo = json.dumps({"fuentes": [{"chunk_id": "propio"}], "texto": "Art. 2 - Beneficiarios"})
    assert _revisar(cuerpo, "/v1/respuestas", {"propio"}) == []


def test_la_fuente_caida_se_registra_como_lo_que_es() -> None:
    """503 es «ahora no puedo» y 403 es «no te dejo». La política los separa."""
    with ServidorDeMentira() as stub:
        observaciones = probar_fuente(stub)
    assert "acceso limitado = False" in observaciones[0], "un 503 no es acceso limitado"
    assert "acceso limitado = True" in observaciones[1], "un 403 sí lo es"
    assert "HTTP 200" in observaciones[2], "repuesta la fuente, la ingesta vuelve sola"


def test_el_informe_dice_no_aplica_donde_no_se_midio_la_recuperacion() -> None:
    """«No volvió» sería informar un problema donde no lo hubo."""
    sin_medir = _fallo("proveedor", 1, 1)
    sin_medir.aplicado = True
    con_medida = _fallo("base", 2, 1)
    con_medida.aplicado = True
    con_medida.medir_recuperacion = True
    con_medida.recuperado_en_s = 3.2
    reporte = ReporteCarga(
        conversaciones=20, minutos=30.0, fallos=[sin_medir, con_medida], limite_configurado=120
    )
    reporte.peticiones.append(Peticion(fase=FASE_ANTES, ruta="/v1/normas", ms=10.0, estado=200))
    texto = formatear(reporte)
    assert "no aplica" in texto
    assert "3.2 s" in texto
    assert "Ninguna." in texto  # sin filtraciones


def test_el_informe_denuncia_las_filtraciones_que_encontro() -> None:
    reporte = ReporteCarga(conversaciones=1, minutos=1.0)
    reporte.peticiones.append(Peticion(fase=FASE_ANTES, ruta="/v1/normas", ms=1.0, estado=200))
    reporte.filtraciones.extend(_revisar('{"x": "CANDIDATE"}', "/v1/normas", set()))
    texto = formatear(reporte)
    assert "1 hallazgo(s)" in texto
