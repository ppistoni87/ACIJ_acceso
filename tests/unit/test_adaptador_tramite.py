"""HU-019 y AT-008/AT-022/AT-076: fichas de trámite.

Las fixtures reproducen la estructura real del portal nacional, incluida la
parte que más importa: un campo que existe y está vacío.
"""

from __future__ import annotations

import pytest

from backend_normativo.ingesta.adaptadores.base import CapturaMaterial
from backend_normativo.ingesta.adaptadores.tramite_argentina import (
    AdaptadorTramiteArgentina,
    leer_ficha,
)

pytestmark = pytest.mark.aceptacion

FICHA = """
<html><body><main>
  <h1>Iniciar un reclamo ante Defensa del Consumidor</h1>
  <div class="media-body"><h2>¿A quién está dirigido?</h2>
    <p>A los consumidores que hayan tenido un problema con algún producto.</p></div>
  <div class="media-body"><h2>¿Qué necesito?</h2>
    <ul><li>Tu número de DNI o Pasaporte.</li><li>Un teléfono de contacto.</li></ul></div>
  <div class="media-body"><h2>¿Cómo hago?</h2>
    <ol>
      <li><div class="description"><p>Ingresá a la Ventanilla Federal Única.</p></div></li>
      <li><div class="description"><p>Completá el formulario con:</p>
        <ul><li>Tus datos personales.</li><li>Los datos del reclamo.</li>
            <li>Los datos del proveedor.</li></ul></div></li>
      <li><div class="description"><p>Enviá el formulario.</p></div></li>
    </ol></div>
  <div class="media-body"><h2>¿Cuánto tiempo lleva?</h2>
    <div class="field field-name-field-duracion"></div></div>
  <div class="media-body"><h2>¿Cuál es el costo?</h2>
    <div class="field field-name-field-costo"><div>Gratuito</div></div></div>
  <a class="btn btn-primary" href="https://autogestion.produccion.gob.ar/consumidores">Iniciar</a>
</main></body></html>
"""

PANTALLA_DE_ACCESO = """
<html><body><main>
  <h1>Ingresar</h1>
  <form><label>Usuario y contraseña</label><input name="clave"></form>
  <p>Iniciá sesión con tu Clave Fiscal para continuar.</p>
</main></body></html>
"""


def _captura(html: str, url: str = "https://www.argentina.gob.ar/servicio/reclamo"):
    return CapturaMaterial(
        source_id="F45",
        url_final=url,
        contenido=html.encode("utf-8"),
        mime="text/html; charset=utf-8",
        sha256="a" * 64,
    )


# --- AT-022: los pasos no se ordenan por posición en el documento -------------


def test_at022_un_paso_con_aclaraciones_no_se_convierte_en_cuatro_pasos() -> None:
    """Aplanar la lista haría que el «paso 3» que se le responde a alguien sea
    en realidad una aclaración del paso 2."""
    ficha = leer_ficha(FICHA)
    assert [p.texto for p in ficha.pasos] == [
        "Ingresá a la Ventanilla Federal Única.",
        "Completá el formulario con:",
        "Enviá el formulario.",
    ]


def test_at022_las_aclaraciones_no_se_pierden() -> None:
    """No convertirlas en pasos no significa descartarlas: son el detalle del
    paso que las contiene."""
    ficha = leer_ficha(FICHA)
    assert ficha.pasos[1].detalle == [
        "Tus datos personales.",
        "Los datos del reclamo.",
        "Los datos del proveedor.",
    ]
    assert ficha.pasos[0].detalle == []


def test_los_requisitos_salen_de_su_propia_seccion() -> None:
    ficha = leer_ficha(FICHA)
    assert [r.texto for r in ficha.requisitos] == [
        "Tu número de DNI o Pasaporte.",
        "Un teléfono de contacto.",
    ]


# --- AT-076: lo que la ficha no dice no se completa ---------------------------


def test_at076_una_duracion_vacia_no_es_inmediato() -> None:
    """El campo existe y está vacío. Completarlo con «inmediato» produce una
    respuesta sobre la que alguien planifica."""
    ficha = leer_ficha(FICHA)
    assert ficha.duracion is None
    assert "duracion" in ficha.campos_ausentes
    assert any("no se asigna cero" in str(a) for a in ficha.avisos)


def test_at076_un_costo_declarado_si_se_toma() -> None:
    """La contracara: cuando la ficha lo dice, se usa. Si no, la abstención no
    probaría nada."""
    ficha = leer_ficha(FICHA)
    assert ficha.costo == "Gratuito"
    assert "costo" not in ficha.campos_ausentes


def test_at076_una_ficha_sin_los_dos_campos_los_reporta_a_los_dos() -> None:
    sin_campos = FICHA.replace("<div>Gratuito</div>", "")
    ficha = leer_ficha(sin_campos)
    assert ficha.costo is None
    assert set(ficha.campos_ausentes) >= {"costo", "duracion"}


# --- AT-008: un 200 con formulario de acceso no es la ficha -------------------


def test_at008_una_pantalla_de_acceso_no_se_publica_como_tramite() -> None:
    """Responde 200 y trae HTML, pero no es contenido público del trámite. Se
    registra el acceso y nada más: no se autentica."""
    ficha = leer_ficha(PANTALLA_DE_ACCESO, url="https://www.argentina.gob.ar/servicio/x")
    assert ficha.pasos == []
    assert ficha.requisitos == []
    assert any("pantalla de acceso" in str(a) for a in ficha.avisos)
    assert any(a.severidad == "HIGH" for a in ficha.avisos)

    resultado = AdaptadorTramiteArgentina().extraer(_captura(PANTALLA_DE_ACCESO))
    assert resultado.documentos == []
    assert any("no se autentica" in str(a) for a in resultado.avisos)


# --- Contrato del adaptador ---------------------------------------------------


def test_solo_acepta_fichas_de_servicio_del_portal_nacional() -> None:
    adaptador = AdaptadorTramiteArgentina()
    assert adaptador.acepta(_captura(FICHA))
    assert not adaptador.acepta(
        _captura(FICHA, url="https://www.argentina.gob.ar/educacion/progresar")
    )
    assert not adaptador.acepta(_captura(FICHA, url="https://buenosaires.gob.ar/servicio/x"))


def test_la_ficha_viaja_como_identidad_candidata() -> None:
    documento = AdaptadorTramiteArgentina().extraer(_captura(FICHA)).documentos[0]
    tramite = documento.identidad["tramite"]
    assert tramite["titulo"] == "Iniciar un reclamo ante Defensa del Consumidor"
    assert tramite["costo"] == "Gratuito"
    assert tramite["duracion"] is None
    assert len(tramite["pasos"]) == 3
    assert tramite["cta_url"].startswith("https://")


def test_el_texto_conserva_pasos_y_aclaraciones() -> None:
    """El texto extraído es lo que después se cita: si pierde las aclaraciones,
    la cita queda incompleta."""
    documento = AdaptadorTramiteArgentina().extraer(_captura(FICHA)).documentos[0]
    assert "Paso 2: Completá el formulario con:" in documento.texto
    assert "Los datos del proveedor." in documento.texto


def test_dos_fichas_de_un_portal_son_dos_documentos() -> None:
    """La ficha del DNI y la del pasaporte no son la misma con otro número.

    `tramite:<fuente>` identificaba a todas las fichas de un portal como un solo
    documento, así que cada ficha nueva se apilaba como versión de la anterior.
    """
    adaptador = AdaptadorTramiteArgentina()
    dni = adaptador.extraer(
        _captura(FICHA, url="https://www.argentina.gob.ar/servicio/dni-al-instante")
    ).documentos
    pasaporte = adaptador.extraer(
        _captura(FICHA, url="https://www.argentina.gob.ar/servicio/pasaporte")
    ).documentos
    assert dni and pasaporte
    assert dni[0].external_id != pasaporte[0].external_id
    assert dni[0].external_id == "tramite:F45:/servicio/dni-al-instante"
