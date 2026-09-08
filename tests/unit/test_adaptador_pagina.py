"""HU-006 y AT-016/AT-017/AT-065: páginas institucionales.

Lo que estas pruebas fijan no es que el adaptador extraiga, sino lo que se
niega a dar por bueno: un contenedor vacío, un bloque escondido y una tabla que
no está.
"""

from __future__ import annotations

import pytest

from backend_normativo.ingesta.adaptadores.base import CapturaMaterial
from backend_normativo.ingesta.adaptadores.html import esta_oculto, texto_oculto
from backend_normativo.ingesta.adaptadores.pagina_institucional import (
    AdaptadorPaginaInstitucional,
    leer,
)

pytestmark = pytest.mark.aceptacion


def _captura(html: str, url: str = "https://www.argentina.gob.ar/educacion/progresar/cronograma"):
    return CapturaMaterial(
        source_id="F52",
        url_final=url,
        contenido=html.encode("utf-8"),
        mime="text/html; charset=utf-8",
        sha256="a" * 64,
    )


# --- AT-016: el primer contenedor puede venir vacío ---------------------------

CRONOGRAMA = """
<html><body><main>
  <h1>Cronograma de pagos</h1>
  <div class="field-item"></div>
  <div class="field-item">
    <p>El cronograma de pagos correspondiente a este mes inicia el 9 de febrero.</p>
    <p>DNI terminado en 0 y 1: 9 de febrero. DNI terminado en 2 y 3: 10 de febrero.</p>
  </div>
</main></body></html>
"""


def test_at016_un_contenedor_vacio_no_se_toma_como_el_contenido() -> None:
    """Tomar el primero porque es el primero deja una carga exitosa sin datos:
    el período que todavía no arrancó viene con la estructura y sin nada."""
    lectura = leer(CRONOGRAMA)
    assert lectura.contenedores_vacios == 1
    assert "9 de febrero" in lectura.texto
    assert any("no el primero" in str(a) for a in lectura.avisos)


def test_at016_una_pagina_sin_contenedores_vacios_no_avisa_de_nada() -> None:
    """La contracara: si avisara siempre, el aviso no diría nada."""
    lectura = leer(CRONOGRAMA.replace('<div class="field-item"></div>', ""))
    assert lectura.contenedores_vacios == 0
    assert not any("contenedor" in str(a) for a in lectura.avisos)


# --- AT-017: el ciclo viejo escondido no es el vigente ------------------------

INSCRIPCION = """
<html><body><main>
  <h1>Inscripción escolar</h1>
  <div class="ciclo d-none">
    <p>Inscripción para el ciclo lectivo 2025: del 1 al 30 de septiembre de 2024.</p>
  </div>
  <div class="ciclo">
    <p>Inscripción para el ciclo lectivo 2026: del 1 al 30 de septiembre de 2025.</p>
  </div>
</main></body></html>
"""


def test_at017_el_bloque_oculto_no_entra_como_contenido_vigente() -> None:
    """Los dos textos son legítimos; lo que los distingue es que solo uno está
    publicado hoy. Extraer el oculto sirve información del año pasado."""
    lectura = leer(INSCRIPCION)
    assert "ciclo lectivo 2026" in lectura.texto
    assert "ciclo lectivo 2025" not in lectura.texto


def test_at017_los_dos_contextos_quedan_separados_no_descartados() -> None:
    """Que la página tenga el ciclo viejo escondido es información: permite
    responder «esa inscripción es del ciclo anterior» en vez de no responder."""
    lectura = leer(INSCRIPCION)
    assert any("ciclo lectivo 2025" in o for o in lectura.ocultos)
    assert any("existir es un dato" in str(a) for a in lectura.avisos)


def test_las_formas_de_ocultar_que_usan_los_portales_se_reconocen() -> None:
    from selectolax.parser import HTMLParser

    for marcado in (
        '<div class="d-none">x</div>',
        "<div hidden>x</div>",
        '<div aria-hidden="true">x</div>',
        '<div style="display:none">x</div>',
        '<div style="visibility: hidden">x</div>',
        '<div class="sr-only">x</div>',
    ):
        nodo = HTMLParser(marcado).css_first("div")
        assert esta_oculto(nodo), marcado
    visible = HTMLParser('<div class="card">x</div>').css_first("div")
    assert not esta_oculto(visible)


def test_una_clase_que_solo_contiene_la_palabra_no_cuenta_como_oculta() -> None:
    """`d-none-lg` no es `d-none`: la comparación es por clase entera."""
    from selectolax.parser import HTMLParser

    nodo = HTMLParser('<div class="hidden-print-only">x</div>').css_first("div")
    assert not esta_oculto(nodo)


def test_el_texto_oculto_se_devuelve_sin_repetir_anidados() -> None:
    html = '<main><div class="d-none"><p>Ciclo viejo</p></div></main>'
    assert texto_oculto(html, selector="main") == ["Ciclo viejo"]


# --- AT-065: una tabla que no está no es una tabla vacía ----------------------

SEDES_CERRADAS = """
<html><body><main>
  <h1>Sedes - Puntos presenciales</h1>
  <p>Conocé las sedes donde podés realizar el trámite de forma presencial.</p>
  <p>Recordá que la atención presencial de las sedes permanecerá cerrada hasta el
     comienzo del nuevo periodo de inscripción.</p>
</main></body></html>
"""


def test_at065_una_sede_cerrada_es_el_dato_no_una_falta_de_datos() -> None:
    """Rescatar el listado de la captura anterior lo presentaría como vigente."""
    lectura = leer(SEDES_CERRADAS, url="https://buenosaires.gob.ar/sedes")
    assert lectura.cierre_declarado is not None
    assert "cerrada" in lectura.cierre_declarado
    assert any("no se completa con el listado" in str(a) for a in lectura.avisos)


def test_at065_el_fragmento_del_cierre_no_arranca_a_mitad_de_palabra() -> None:
    """Alguien lo va a leer para decidir si viaja hasta una sede."""
    lectura = leer(SEDES_CERRADAS)
    normalizado = " ".join(lectura.texto.split())
    posicion = normalizado.find(lectura.cierre_declarado)
    assert posicion >= 0, "El fragmento tiene que salir del texto, no reescribirlo."
    assert posicion == 0 or normalizado[posicion - 1] == " ", (
        f"El fragmento arranca a mitad de palabra: {lectura.cierre_declarado[:40]!r}"
    )
    fin = posicion + len(lectura.cierre_declarado)
    assert fin == len(normalizado) or normalizado[fin] == " "


def test_una_pagina_con_sedes_abiertas_no_declara_cierre() -> None:
    abierta = SEDES_CERRADAS.replace(
        "Recordá que la atención presencial de las sedes permanecerá cerrada hasta el",
        "Sede Central: Bolívar 191. Sede Norte: Av. Cabildo 3061. Atienden desde el",
    ).replace("comienzo del nuevo periodo de inscripción.", "lunes.")
    assert leer(abierta).cierre_declarado is None


# --- Contrato del adaptador ---------------------------------------------------


def test_solo_acepta_html_de_los_portales_del_corpus() -> None:
    adaptador = AdaptadorPaginaInstitucional()
    assert adaptador.acepta(_captura(CRONOGRAMA))
    assert not adaptador.acepta(_captura(CRONOGRAMA, url="https://ejemplo.com/pagina"))
    captura_pdf = CapturaMaterial(
        source_id="F52",
        url_final="https://www.argentina.gob.ar/x.pdf",
        contenido=b"%PDF-1.4",
        mime="application/pdf",
        sha256="a" * 64,
    )
    assert not adaptador.acepta(captura_pdf)


def test_una_pagina_sin_texto_no_produce_documento() -> None:
    """Un documento vacío es peor que ninguno: parece que la fuente se cargó."""
    resultado = AdaptadorPaginaInstitucional().extraer(
        _captura("<html><body><main></main></body></html>")
    )
    assert resultado.documentos == []
    assert any("No se publica nada sobre ella" in str(a) for a in resultado.avisos)


def test_lo_observado_viaja_como_identidad_candidata() -> None:
    documento = AdaptadorPaginaInstitucional().extraer(_captura(INSCRIPCION)).documentos[0]
    pagina = documento.identidad["pagina"]
    assert pagina["ocultos"]
    assert pagina["contenedores"] >= 0
