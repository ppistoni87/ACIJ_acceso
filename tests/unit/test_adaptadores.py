"""HU-005 a HU-007: extracción por familia técnica.

Las fixtures son sintéticas y reproducen la estructura de cada sitio, no su
contenido real: fijan lo que el adaptador tiene que reconocer sin afirmar que
una norma dice hoy lo que dice la fixture.
"""

from __future__ import annotations

import datetime as dt

from backend_normativo.db.vocabularios import RolContenido, TipoVersionDocumento
from backend_normativo.ingesta.adaptadores.base import CapturaMaterial
from backend_normativo.ingesta.adaptadores.html import decodificar_html
from backend_normativo.ingesta.adaptadores.infoleg_legacy import AdaptadorInfolegLegacy
from backend_normativo.ingesta.adaptadores.normativa_ba import AdaptadorNormativaBA
from backend_normativo.ingesta.adaptadores.normativa_nacional import AdaptadorNormativaNacional


def _material(url: str, html: str, *, codificacion: str = "utf-8", mime: str = "text/html"):
    return CapturaMaterial(
        source_id="FTEST",
        url_final=url,
        contenido=html.encode(codificacion),
        mime=mime,
        sha256="0" * 64,
    )


# --- Portal nacional ---------------------------------------------------------

FICHA_NACIONAL = """
<html><body><article>
  <h1 class="h5">Decreto DNU 1382 / 2001</h1>
  <p class="lead">PODER EJECUTIVO NACIONAL (P.E.N.)</p>
  <h2 class="h3">SISTEMA INTEGRADO DE PROTECCION A LA FAMILIA</h2>
  <div class="row small"><dl class="normativa">
    <div><dt>Sanción:</dt><dd><time datetime="2001-11-01">01-11-2001</time></dd></div>
    <div><dt>Publicada en el Boletín Oficial:</dt>
         <dd><time datetime="2001-11-02">02-11-2001</time></dd></div>
  </dl></div>
  <a href="/normativa/nacional/norma-69649/texto">Ver norma original</a>
  <a href="/normativa/nacional/norma-69649/actualizacion">Ver texto actualizado</a>
  <a href="/normativa/buscar-boletin?s=1&amp;numero_boletin=29766">Boletín 29766</a>
</article></body></html>
"""

TEXTO_NACIONAL = """
<html><body><div class="infoleg-norma-body infoleg-mode-actualizado">
  <p>(<strong>Nota Infoleg</strong>: norma abrogada por art. 26 del Decreto N° 1382/01
     y restablecida su vigencia por
     <a href="/normativa/nacional/norma-70499">Decreto N° 1604/2001</a>)</p>
  <p><strong>ARTICULO 1°-</strong> Se instituye el régimen.</p>
  <p>a) Un subsistema contributivo.</p>
  <p><strong>ARTICULO 14 bis.-</strong> La Asignación Universal por Hijo.</p>
</div></body></html>
"""


def test_la_ficha_nacional_da_identidad_y_fechas_tipadas() -> None:
    resultado = AdaptadorNormativaNacional().extraer(
        _material("https://www.argentina.gob.ar/normativa/nacional/norma-69649", FICHA_NACIONAL)
    )
    documento = resultado.documentos[0]
    identidad = documento.identidad

    assert identidad["tipo"] == "DECRETO"
    assert identidad["numero"] == "1382"
    assert identidad["anio"] == 2001
    assert identidad["emisor_declarado"] == "PODER EJECUTIVO NACIONAL (P.E.N.)"
    # Sanción y publicación se guardan por separado: no son la misma fecha.
    assert identidad["fechas"] == {"SANCION": "2001-11-01", "PUBLICACION": "2001-11-02"}
    assert documento.fecha_documento == dt.date(2001, 11, 2)
    assert documento.tipo_fecha.value == "PUBLICACION"


def test_la_ficha_descubre_las_vistas_de_texto_y_no_el_buscador() -> None:
    """Seguir los enlaces del buscador convertiría el descubrimiento en un
    rastreo indiscriminado."""
    resultado = AdaptadorNormativaNacional().extraer(
        _material("https://www.argentina.gob.ar/normativa/nacional/norma-69649", FICHA_NACIONAL)
    )
    urls = {u.url for u in resultado.urls_descubiertas}
    assert urls == {
        "https://www.argentina.gob.ar/normativa/nacional/norma-69649/texto",
        "https://www.argentina.gob.ar/normativa/nacional/norma-69649/actualizacion",
    }


def test_original_y_actualizado_son_versiones_distintas() -> None:
    """Aplicar una reforma sobre un texto que ya la integra es el error que esta
    separación evita."""
    adaptador = AdaptadorNormativaNacional()
    actualizado = adaptador.extraer(
        _material(
            "https://www.argentina.gob.ar/normativa/nacional/norma-39880/actualizacion",
            TEXTO_NACIONAL,
        )
    ).documentos[0]
    original = adaptador.extraer(
        _material(
            "https://www.argentina.gob.ar/normativa/nacional/norma-39880/texto",
            TEXTO_NACIONAL.replace("infoleg-mode-actualizado", "infoleg-mode-original"),
        )
    ).documentos[0]

    assert actualizado.tipo_version is TipoVersionDocumento.ACTUALIZADO
    assert original.tipo_version is TipoVersionDocumento.ORIGINAL
    assert actualizado.external_id != original.external_id


def test_la_nota_del_boletin_no_se_toma_como_articulado() -> None:
    """F33: la nota dice "abrogada" y también "restablecida su vigencia". No es
    una conclusión: es texto del editor que hay que revisar."""
    documento = (
        AdaptadorNormativaNacional()
        .extraer(
            _material(
                "https://www.argentina.gob.ar/normativa/nacional/norma-39880/actualizacion",
                TEXTO_NACIONAL,
            )
        )
        .documentos[0]
    )

    notas = [u for u in documento.unidades if u.rol_contenido is RolContenido.NOTA]
    assert len(notas) == 1
    assert "abrogada" in notas[0].texto and "restablecida" in notas[0].texto
    # La nota no aportó ningún estado legal: eso lo decide la curación.
    assert "estado_legal_declarado" not in documento.identidad


def test_el_sufijo_del_articulo_sobrevive_a_la_extraccion() -> None:
    documento = (
        AdaptadorNormativaNacional()
        .extraer(
            _material(
                "https://www.argentina.gob.ar/normativa/nacional/norma-39880/actualizacion",
                TEXTO_NACIONAL,
            )
        )
        .documentos[0]
    )
    articulos = [(u.numero, u.sufijo) for u in documento.unidades if u.tipo.value == "ARTICULO"]
    assert ("14", "bis") in articulos


def test_una_estructura_desconocida_no_se_extrae_a_ciegas() -> None:
    resultado = AdaptadorNormativaNacional().extraer(
        _material(
            "https://www.argentina.gob.ar/normativa/nacional/norma-1/texto",
            "<html><body><p>Página de error</p></body></html>",
        )
    )
    assert resultado.documentos == []
    assert any("no se encontró" in a.texto.lower() for a in resultado.avisos)


# --- InfoLEG histórico -------------------------------------------------------

INFOLEG_LEGACY = """
<html><head><title>REGIMEN DE ASIGNACIONES FAMILIARES</title></head><body>
<p>Ley 24.714</p>
<p>Sancionada: Octubre 2 de 1996.</p>
<p>Promulgada Parcialmente: Octubre 16 de 1996.</p>
<p>ARTICULO 1°- Se instituye con alcance nacional y obligatorio.</p>
<p>ARTICULO 2°- Las empleadas del Régimen Especial.</p>
</body></html>
"""


def test_infoleg_historico_lee_identidad_y_fechas_en_castellano() -> None:
    documento = (
        AdaptadorInfolegLegacy()
        .extraer(
            _material(
                "https://servicios.infoleg.gob.ar/infolegInternet/anexos/35000-39999/39880/texact.htm",
                INFOLEG_LEGACY,
            )
        )
        .documentos[0]
    )

    assert documento.identidad["tipo"] == "LEY"
    # El separador de miles es tipográfico, no parte del número.
    assert documento.identidad["numero"] == "24714"
    assert documento.identidad["anio"] == 1996
    assert documento.identidad["fechas"]["SANCION"] == "1996-10-02"
    assert documento.identidad["fechas"]["PROMULGACION"] == "1996-10-16"
    assert documento.tipo_version is TipoVersionDocumento.ACTUALIZADO


def test_la_ruta_de_infoleg_distingue_original_de_actualizado() -> None:
    adaptador = AdaptadorInfolegLegacy()
    base = "https://servicios.infoleg.gob.ar/infolegInternet/anexos/35000-39999/39880/"
    actualizado = adaptador.extraer(_material(base + "texact.htm", INFOLEG_LEGACY)).documentos[0]
    original = adaptador.extraer(_material(base + "texorig.htm", INFOLEG_LEGACY)).documentos[0]
    assert actualizado.tipo_version is TipoVersionDocumento.ACTUALIZADO
    assert original.tipo_version is TipoVersionDocumento.ORIGINAL


def test_una_pagina_en_cp1252_no_pierde_las_tildes() -> None:
    """Una tilde corrompida en "Artículo" hace que el segmentador pierda la
    unidad entera."""
    documento = (
        AdaptadorInfolegLegacy()
        .extraer(
            _material(
                "https://servicios.infoleg.gob.ar/infolegInternet/anexos/1/1/texact.htm",
                INFOLEG_LEGACY.replace("ARTICULO 1°", "Artículo 1°"),
                codificacion="cp1252",
            )
        )
        .documentos[0]
    )
    assert any(u.numero == "1" for u in documento.unidades if u.tipo.value == "ARTICULO")
    assert "Artículo" in documento.texto


def test_decodificar_prefiere_lo_declarado_sobre_adivinar() -> None:
    assert decodificar_html("Artículo".encode("cp1252")) == "Artículo"
    assert decodificar_html("Artículo".encode()) == "Artículo"


# --- NormativaBA -------------------------------------------------------------

NORMATIVA_BA = """
<html><body><main>
<p>LEY 547 2001</p>
<p>Síntesis:</p><p>MODIFICACIÓN DE LA ORDENANZA 43478 - SERVICIO DE DESAYUNO</p>
<p>Publicación:</p><p>24/04/2001</p>
<p>Sanción:</p><p>29/03/2001</p>
<p>Organismo:</p><p>LEGISLATURA DE LA CIUDAD AUTÓNOMA DE BUENOS AIRES</p>
<p>Estado:</p><p>No vigente</p>
<p>Texto original</p>
<p>Artículo 1° - Sustitúyese el artículo 10 de la Ordenanza N° 43.478 por el siguiente:</p>
<p>Artículo 10 - El Poder Ejecutivo brindará un servicio de desayuno.</p>
<p>Artículo 2° - Comuníquese.</p>
</main></body></html>
"""


def test_normativaba_separa_el_estado_declarado_de_la_conclusion() -> None:
    """F23: la ficha dice "No vigente". Eso se conserva como lo que es, una
    etiqueta de la fuente, y no borra los efectos que la norma incorporó."""
    documento = (
        AdaptadorNormativaBA()
        .extraer(
            _material(
                "https://boletinoficial.buenosaires.gob.ar/normativaba/norma/11223", NORMATIVA_BA
            )
        )
        .documentos[0]
    )

    assert documento.identidad["estado_legal_declarado"] == "NO_VIGENTE"
    assert documento.identidad["estado_declarado_literal"] == "No vigente"
    assert documento.identidad["numero"] == "547"
    assert documento.identidad["fechas"]["PUBLICACION"] == "2001-04-24"


def test_normativaba_no_toma_el_articulo_sustituido_como_propio() -> None:
    documento = (
        AdaptadorNormativaBA()
        .extraer(
            _material(
                "https://boletinoficial.buenosaires.gob.ar/normativaba/norma/11223", NORMATIVA_BA
            )
        )
        .documentos[0]
    )
    dispositivos = [
        u.numero
        for u in documento.unidades
        if u.tipo.value == "ARTICULO" and u.rol_contenido is RolContenido.DISPOSITIVO
    ]
    sustitutivos = [
        u.numero for u in documento.unidades if u.rol_contenido is RolContenido.SUSTITUTIVO
    ]
    assert dispositivos == ["1", "2"]
    assert sustitutivos == ["10"]
    assert all("síntesis" not in a.texto for a in documento.avisos)


def test_normativaba_detecta_una_transposicion_de_digitos_en_la_sintesis() -> None:
    """F19: la síntesis dice 1261 y el encabezado 1621. No son dos normas."""
    html = NORMATIVA_BA.replace("LEY 547 2001", "RESOLUCIÓN 1621 2025 MINISTERIO DE EDUCACION")
    html = html.replace("MODIFICACIÓN DE LA ORDENANZA 43478", "APRUEBASE EL LLAMADO 1261")
    resultado = AdaptadorNormativaBA().extraer(
        _material("https://boletinoficial.buenosaires.gob.ar/normativaba/norma/829906", html)
    )
    documento = resultado.documentos[0]
    assert documento.identidad["numero"] == "1621"
    assert documento.identidad["numeros_discrepantes_en_sintesis"] == ["1261"]
    assert any("otro orden" in a.texto for a in documento.avisos)


def test_una_cita_normal_a_otra_norma_no_se_reporta_como_discrepancia() -> None:
    """Que una norma modificatoria nombre a la que modifica es lo esperable."""
    documento = (
        AdaptadorNormativaBA()
        .extraer(
            _material(
                "https://boletinoficial.buenosaires.gob.ar/normativaba/norma/11223", NORMATIVA_BA
            )
        )
        .documentos[0]
    )
    assert "numeros_discrepantes_en_sintesis" not in documento.identidad


NORMATIVA_BA_CON_PANEL = """
<html><body><main>
<p>LEY 547 2001</p>
<p>Síntesis:</p><p>MODIFICACIÓN DE LA ORDENANZA 43478 - SERVICIO DE DESAYUNO</p>
<p>Publicación:</p><p>24/04/2001</p>
<p>Estado:</p><p>Vigente</p>
<p>Texto original</p>
<p>Artículo 1° - El Poder Ejecutivo brindará un servicio de desayuno.</p>
<p>Artículo 2° - Comuníquese.</p>
<p>Relaciones</p>
<p>Tipo de relación</p>
<p>Norma relacionada</p>
<p>Detalle</p>
<p>INTEGRA</p>
<p>ORDENANZA 43478 1989</p>
<p>PROMULGADA POR DECRETO 495 2025</p>
</main></body></html>
"""


def test_normativaba_no_publica_el_panel_de_relaciones_como_articulado() -> None:
    """El adaptador sabía dónde empieza el texto y no dónde termina.

    Todo lo que la ficha muestra debajo del articulado —el panel de
    «Relaciones», sus encabezados de tabla, los tipos de vínculo— entraba como
    si fuera la norma y se publicaba como texto citable: una respuesta podía
    citar «Tipo de relación» como si fuera la ley.
    """
    resultado = AdaptadorNormativaBA().extraer(
        _material(
            "https://boletinoficial.buenosaires.gob.ar/normativaba/norma/11223",
            NORMATIVA_BA_CON_PANEL,
        )
    )
    documento = resultado.documentos[0]
    textos = " ".join(unidad.texto for unidad in documento.unidades)

    assert "servicio de desayuno" in textos
    for intruso in ("Tipo de relación", "Norma relacionada", "INTEGRA", "PROMULGADA POR"):
        assert intruso not in textos, f"«{intruso}» es de la página, no de la norma"

    # Y el recorte no es silencioso: si la maquetación cambia y el corte se come
    # articulado, el número de descartados lo dice.
    assert any("se descartaron 7 párrafo(s)" in aviso.texto for aviso in resultado.avisos)
