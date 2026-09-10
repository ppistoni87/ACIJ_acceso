"""HU-006 y AT-016/AT-017/AT-065: páginas institucionales.

Lo que estas pruebas fijan no es que el adaptador extraiga, sino lo que se
niega a dar por bueno: un contenedor vacío, un bloque escondido y una tabla que
no está.
"""

from __future__ import annotations

import pytest

from backend_normativo.db.vocabularios import RolContenido
from backend_normativo.ingesta.adaptadores.base import CapturaMaterial
from backend_normativo.ingesta.adaptadores.html import esta_oculto, texto_oculto
from backend_normativo.ingesta.adaptadores.pagina_institucional import (
    AdaptadorPaginaInstitucional,
    leer,
)

pytestmark = pytest.mark.aceptacion


def _captura(
    html: str,
    url: str = "https://www.argentina.gob.ar/educacion/progresar/cronograma",
    clase: str | None = "DOCUMENTO",
):
    return CapturaMaterial(
        source_id="F52",
        url_final=url,
        contenido=html.encode("utf-8"),
        mime="text/html; charset=utf-8",
        sha256="a" * 64,
        clase=clase,
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


def test_solo_acepta_html_de_las_clases_institucionales() -> None:
    """Acepta por lo que el catálogo declara que la fuente es, no por su dominio."""
    adaptador = AdaptadorPaginaInstitucional()
    assert adaptador.acepta(_captura(CRONOGRAMA))
    assert adaptador.acepta(
        _captura(CRONOGRAMA, url="https://www.edenor.com/x", clase="DIRECTORIO")
    )
    assert not adaptador.acepta(_captura(CRONOGRAMA, clase="DATASET"))
    captura_pdf = CapturaMaterial(
        source_id="F52",
        url_final="https://www.argentina.gob.ar/x.pdf",
        contenido=b"%PDF-1.4",
        mime="application/pdf",
        sha256="a" * 64,
        clase="DOCUMENTO",
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


# --- AT-016: a qué período corresponde el cronograma -------------------------

# Texto real de la página de cronograma de Progresar (F52).
CRONOGRAMA = """
<html><body><main>
  <h1>Cronograma de pagos y monto</h1>
  <div class="field-item"></div>
  <div class="field-item">
    <p>El cronograma de pagos de la beca Progresar correspondiente a este mes
       inicia el 9 de febrero.</p>
    <p>DNI terminado en 0 y 1: 9 de febrero. 2 y 3: 10 de febrero.</p>
    <p>El monto de la beca Progresar es de $35.000.-</p>
  </div>
</main></body></html>
"""

CRONOGRAMA_FECHADO = CRONOGRAMA.replace(
    "correspondiente a este mes\n       inicia el 9 de febrero",
    "correspondiente a febrero de 2026\n       inicia el 9 de febrero de 2026",
).replace(
    "9 de febrero. 2 y 3: 10 de febrero", "9 de febrero de 2026. 2 y 3: 10 de febrero de 2026"
)


def test_at016_un_cronograma_que_dice_este_mes_no_declara_su_periodo() -> None:
    """«Correspondiente a este mes» se lee entero y parece que dijera algo."""
    lectura = leer(CRONOGRAMA)
    assert lectura.periodo_determinado is False
    assert lectura.periodo_relativo == "este mes"


def test_at016_los_dias_sin_anio_del_cronograma_se_listan() -> None:
    lectura = leer(CRONOGRAMA)
    assert "9 de febrero" in lectura.dias_sin_anio
    assert "10 de febrero" in lectura.dias_sin_anio


def test_at016_el_periodo_no_se_completa_con_la_fecha_de_captura() -> None:
    """Una página sin actualizar publica el cronograma del mes pasado con las
    mismas palabras."""
    lectura = leer(CRONOGRAMA)
    aviso = next(a for a in lectura.avisos if "no dice a qué período" in str(a))
    assert "no se completa con el año de la captura" in str(aviso).lower()
    assert aviso.severidad == "HIGH"


def test_at016_el_contenedor_con_contenido_es_el_que_se_toma() -> None:
    """El primero viene vacío; el segundo trae el cronograma."""
    lectura = leer(CRONOGRAMA)
    assert lectura.contenedores_vacios == 1
    assert "9 de febrero" in lectura.texto
    assert "$35.000" in lectura.texto


def test_un_cronograma_que_declara_su_periodo_no_queda_pendiente() -> None:
    lectura = leer(CRONOGRAMA_FECHADO)
    assert lectura.periodo_determinado is True
    assert not any("no dice a qué período" in str(a) for a in lectura.avisos)


PAGINA_CON_CANALES = """
<html><body><main>
<h1>Canales de asesoramiento y denuncia</h1>
<p>Quienes se notifiquen de un proceso judicial pueden solicitar asesoramiento
por los siguientes canales:</p>
<h2>Centro de Acceso a la Justicia</h2>
<p>0800-222-3245. Atención telefónica para barrios populares.</p>
<h2>WhatsApp para prevención de desalojos</h2>
<p>(54-11) 2771-3385. Sólo mensajes, de 9:00 a 17:00 hs.</p>
<h3>Ver</h3>
</main></body></html>
"""


def test_una_pagina_institucional_deja_secciones_citables() -> None:
    """Sin unidades no hay evidencia, y sin evidencia no hay destino posible.

    Diecisiete fuentes del manifiesto respondían 200, se extraían y no dejaban
    una fila en ninguna tabla. No estaban fallando: el adaptador daba el texto
    de la página y cero unidades, y toda tabla de destino exige una evidencia
    que apunta a una unidad.
    """
    documento = (
        AdaptadorPaginaInstitucional()
        .extraer(
            _captura(PAGINA_CON_CANALES, "https://www.argentina.gob.ar/obras-publicas/canales")
        )
        .documentos[0]
    )

    rotulos = [u.rotulo for u in documento.unidades]
    assert "Centro de Acceso a la Justicia" in rotulos
    assert "WhatsApp para prevención de desalojos" in rotulos

    caj = next(u for u in documento.unidades if u.rotulo == "Centro de Acceso a la Justicia")
    assert "0800-222-3245" in caj.texto, "el canal tiene que quedar dentro de la unidad que lo cita"


def test_las_secciones_no_son_texto_de_la_norma() -> None:
    """Se citan como dicho del organismo, nunca como la ley.

    El publicador arma los fragmentos citables filtrando por DISPOSITIVO, así
    que el rol es lo que impide que una página de sedes entre a un corte como
    si fuera el articulado.
    """
    documento = (
        AdaptadorPaginaInstitucional()
        .extraer(
            _captura(PAGINA_CON_CANALES, "https://www.argentina.gob.ar/obras-publicas/canales")
        )
        .documentos[0]
    )
    assert documento.unidades
    assert all(u.rol_contenido == RolContenido.INFORMATIVO for u in documento.unidades)
    assert all(u.rol_contenido != RolContenido.DISPOSITIVO for u in documento.unidades)


def test_un_rotulo_suelto_no_es_una_seccion() -> None:
    """«Ver», «Compartir», una miga de pan: no sostienen una cita."""
    documento = (
        AdaptadorPaginaInstitucional()
        .extraer(
            _captura(PAGINA_CON_CANALES, "https://www.argentina.gob.ar/obras-publicas/canales")
        )
        .documentos[0]
    )
    assert "Ver" not in [u.rotulo for u in documento.unidades]


def test_una_pagina_con_texto_y_sin_titulos_se_cita_entera() -> None:
    """No se pierde: se cita más grueso y se declara que es más grueso."""
    plana = (
        "<html><body><main><p>"
        + "Un texto largo sin ningún encabezado que lo organice. " * 4
        + "</p></main></body></html>"
    )
    resultado = AdaptadorPaginaInstitucional().extraer(
        _captura(plana, "https://www.argentina.gob.ar/algo")
    )
    unidades = resultado.documentos[0].unidades
    assert len(unidades) == 1
    assert unidades[0].ruta == "pagina"
    assert any("se cita entera" in a.texto for a in resultado.documentos[0].avisos)


INDICE = """
<html><body><main>
<h1>Tramitar el DNI</h1>
<p>El Documento Nacional de Identidad es el documento único de identificación.</p>
<h2>DNI al instante</h2>
<p>Tramitá tu DNI en los Centros de Atención habilitados.
   <a href="/servicio/dni-al-instante">Ver cómo</a></p>
<h2>DNI para argentinos en el país</h2>
<p><a href="/interior/dni/argentinos-residentes-en-el-pais">Ver requisitos</a></p>
<h2>Otros</h2>
<p>
  <a href="/interior/dni">Esta misma página</a>
  <a href="https://otro-sitio.gob.ar/algo">Otro organismo</a>
  <a href="/interior">La sección padre</a>
  <a href="/interior/dni/foto.jpg">Una imagen</a>
</p>
</main></body></html>
"""


def _indice():
    return AdaptadorPaginaInstitucional().extraer(
        _captura(INDICE, "https://www.argentina.gob.ar/interior/dni")
    )


def test_un_indice_descubre_las_paginas_que_tienen_el_contenido() -> None:
    """Curar el índice produciría un trámite sin un solo requisito ni paso.

    El manifiesto lo dice con todas las letras —F66 es «hub /requisitos + 3
    hojas»— y la ingesta nunca las seguía: el contenido vive un clic más allá.
    """
    urls = {u.url for u in _indice().urls_descubiertas}
    assert "https://www.argentina.gob.ar/servicio/dni-al-instante" in urls
    assert "https://www.argentina.gob.ar/interior/dni/argentinos-residentes-en-el-pais" in urls


def test_el_descubrimiento_no_es_un_rastreador() -> None:
    """Sin límites, una página de gobierno lleva a todo el gobierno."""
    urls = {u.url for u in _indice().urls_descubiertas}
    assert "https://otro-sitio.gob.ar/algo" not in urls, "otro host"
    assert "https://www.argentina.gob.ar/interior" not in urls, "la sección padre no es una hoja"
    assert "https://www.argentina.gob.ar/interior/dni" not in urls, "ella misma"
    assert not any(u.endswith(".jpg") for u in urls), "una imagen no es una página"


def test_cada_url_descubierta_dice_de_dónde_salió_y_por_qué() -> None:
    """La relación no es prosa: la promoción la busca por texto."""
    from backend_normativo.ingesta.adaptadores.base import (
        RELACION_FICHA_TRAMITE,
        RELACION_HOJA_INDICE,
    )

    descubiertas = _indice().urls_descubiertas
    ficha = next(u for u in descubiertas if "/servicio/" in u.url)
    hoja = next(u for u in descubiertas if "argentinos-residentes" in u.url)
    assert RELACION_FICHA_TRAMITE in ficha.relacion
    assert RELACION_HOJA_INDICE in hoja.relacion
    assert "argentina.gob.ar/interior/dni" in ficha.relacion, "de dónde salió"


def test_una_pagina_sin_hojas_no_descubre_nada() -> None:
    resultado = AdaptadorPaginaInstitucional().extraer(
        _captura(PAGINA_CON_CANALES, "https://www.argentina.gob.ar/obras-publicas/canales")
    )
    assert resultado.urls_descubiertas == []


SIN_ENCABEZADOS = """
<html><body><main>
<p>Responsable del área: Dr. Francisco Finger</p>
<p>Dirección: Bartolomé Mitre 648, Piso 2º frente, C1036AAL, CABA</p>
<p>Horario de atención: lunes a viernes de 9 a 15 hs.</p>
<p>Teléfono: +54911 7090-4975</p>
</main></body></html>
"""


def test_una_pagina_sin_encabezados_se_cita_entera() -> None:
    """Sin encabezados no es sin contenido.

    La página de una defensoría zonal dice dirección, horario y teléfono sin un
    solo título, y es exactamente lo que su historia promete. Citarla entera es
    menos preciso que citar una sección, y mucho más que no poder citar nada.
    """
    resultado = AdaptadorPaginaInstitucional().extraer(
        _captura(SIN_ENCABEZADOS, "https://www.mpd.gov.ar/index.php/acceder")
    )
    unidades = resultado.documentos[0].unidades
    assert len(unidades) == 1
    assert unidades[0].ruta == "pagina"
    assert unidades[0].rol_contenido == RolContenido.INFORMATIVO
    assert "+54911 7090-4975" in unidades[0].texto
    assert "Bartolomé Mitre 648" in unidades[0].texto
    # Y se declara que la cita es más gruesa de lo deseable.
    assert any("se cita entera" in a.texto for a in resultado.documentos[0].avisos)


def test_una_pagina_vacia_no_produce_una_unidad_vacia() -> None:
    resultado = AdaptadorPaginaInstitucional().extraer(
        _captura("<html><body><main><p>Ver</p></main></body></html>", "https://www.mpd.gov.ar/x")
    )
    assert not resultado.documentos or not resultado.documentos[0].unidades


def test_el_adaptador_acepta_por_lo_que_la_fuente_es_y_no_por_su_dominio() -> None:
    """Una lista de dominios falla en silencio: nadie acepta y nadie se entera.

    Cuatro fuentes del manifiesto —distribuidoras eléctricas— quedaban con los
    bytes guardados y sin extraer, porque su dominio no estaba en la lista.
    """
    adaptador = AdaptadorPaginaInstitucional()
    assert adaptador.acepta(
        _captura(PAGINA_CON_CANALES, "https://www.edenor.com/tramites", "FICHA_TRAMITE")
    )
    assert not adaptador.acepta(
        _captura(PAGINA_CON_CANALES, "https://www.boletinoficial.gob.ar/", "BOLETIN")
    ), "un boletín no es una página institucional"
    assert not adaptador.acepta(
        _captura(PAGINA_CON_CANALES, "https://www.argentina.gob.ar/algo", None)
    ), "sin clase declarada no se adivina"
