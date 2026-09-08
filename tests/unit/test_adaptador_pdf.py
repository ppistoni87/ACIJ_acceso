"""HU-007: extracción de PDF con control de cobertura.

Las fixtures son PDF construidos acá, no descargados: cada uno reproduce
exactamente el caso que el manual describe, sin depender de que una URL siga
respondiendo lo mismo.
"""

from __future__ import annotations

import datetime as dt
import io
import zlib

import pytest

from backend_normativo.db.vocabularios import TipoFecha
from backend_normativo.ingesta.adaptadores.base import CapturaMaterial
from backend_normativo.ingesta.adaptadores.pdf import (
    MINIMO_CHARS_PAGINA,
    AdaptadorPdf,
    PdfInvalido,
    _avisos_de_tablas,
    _periodos_en_orden,
    _tablas_de,
    leer,
    validar,
)


def _pdf(paginas: list[str], *, con_imagen: set[int] = frozenset()) -> bytes:
    """Un PDF mínimo pero legítimo, con una página por texto.

    Se arma a mano en vez de con una biblioteca de generación para que la
    fixture sea el archivo exacto que se quiere probar y no lo que otra
    dependencia decida emitir.
    """
    objetos: list[bytes] = []

    def agregar(cuerpo: bytes) -> int:
        objetos.append(cuerpo)
        return len(objetos)

    fuente = agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    imagen = None
    if con_imagen:
        datos = zlib.compress(bytes([200, 200, 200] * 4))
        imagen = agregar(
            b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB "
            b"/BitsPerComponent 8 /Filter /FlateDecode /Length "
            + str(len(datos)).encode()
            + b" >>\nstream\n"
            + datos
            + b"\nendstream"
        )

    ids_paginas: list[int] = []
    contenidos: list[int] = []
    for numero, texto in enumerate(paginas, start=1):
        lineas = b"".join(
            b"BT /F1 11 Tf 40 "
            + str(760 - 16 * i).encode()
            + b" Td ("
            + _escapar(linea)
            + b") Tj ET\n"
            for i, linea in enumerate(texto.splitlines())
        )
        if numero in con_imagen:
            lineas += b"q 200 0 0 200 40 400 cm /Im1 Do Q\n"
        contenidos.append(
            agregar(
                b"<< /Length "
                + str(len(lineas)).encode()
                + b" >>\nstream\n"
                + lineas
                + b"endstream"
            )
        )
        ids_paginas.append(0)  # se completa abajo

    recursos = b"<< /Font << /F1 " + str(fuente).encode() + b" 0 R >>"
    if imagen:
        recursos += b" /XObject << /Im1 " + str(imagen).encode() + b" 0 R >>"
    recursos += b" >>"

    padre_id = len(objetos) + len(paginas) + 1
    for indice, contenido in enumerate(contenidos):
        ids_paginas[indice] = agregar(
            b"<< /Type /Page /Parent "
            + str(padre_id).encode()
            + b" 0 R /MediaBox [0 0 612 792] /Resources "
            + recursos
            + b" /Contents "
            + str(contenido).encode()
            + b" 0 R >>"
        )
    kids = b" ".join(str(i).encode() + b" 0 R" for i in ids_paginas)
    padre = agregar(
        b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(paginas)).encode() + b" >>"
    )
    assert padre == padre_id
    catalogo = agregar(b"<< /Type /Catalog /Pages " + str(padre).encode() + b" 0 R >>")

    salida = io.BytesIO()
    salida.write(b"%PDF-1.4\n")
    posiciones = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(salida.tell())
        salida.write(str(numero).encode() + b" 0 obj\n" + cuerpo + b"\nendobj\n")
    inicio_xref = salida.tell()
    salida.write(b"xref\n0 " + str(len(objetos) + 1).encode() + b"\n")
    salida.write(b"0000000000 65535 f \n")
    for posicion in posiciones:
        salida.write(f"{posicion:010d} 00000 n \n".encode())
    salida.write(
        b"trailer\n<< /Size "
        + str(len(objetos) + 1).encode()
        + b" /Root "
        + str(catalogo).encode()
        + b" 0 R >>\nstartxref\n"
        + str(inicio_xref).encode()
        + b"\n%%EOF\n"
    )
    return salida.getvalue()


def _escapar(texto: str) -> bytes:
    return (texto.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")).encode(
        "latin-1", "replace"
    )


def _captura(contenido: bytes, *, mime: str = "application/pdf", url: str = "https://x/a.pdf"):
    return CapturaMaterial(
        source_id="F62", url_final=url, contenido=contenido, mime=mime, sha256="a" * 64
    )


# --- AT-018: un 200 con application/pdf que no es un PDF ----------------------


def test_una_pagina_de_error_con_encabezado_de_pdf_no_es_un_documento() -> None:
    """Tratarla como PDF y hacerle OCR convertiría un fallo en contenido."""
    html = b"<html><body><h1>Servicio no disponible</h1>" + b"<p>x</p>" * 500 + b"</body></html>"
    with pytest.raises(PdfInvalido, match="no es un documento"):
        validar(html)

    resultado = AdaptadorPdf().extraer(_captura(html))
    assert resultado.documentos == []
    assert any("no se extrae ni se hace ocr" in str(a).lower() for a in resultado.avisos)
    assert resultado.avisos[0].severidad == "HIGH"


# --- AT-019: prefijo de basura antes del magic --------------------------------


def test_un_prefijo_de_advertencia_se_recorta_y_queda_registrado() -> None:
    """Los bytes crudos no se editan: la reparación produce un derivado y dice
    exactamente cuántos bytes descartó."""
    crudo = b"<!-- warning: legacy endpoint -->\n" + _pdf(
        ["Articulo 1. El objeto de la presente norma es regular el acceso."]
    )
    utiles, reparacion = validar(crudo)
    assert utiles.startswith(b"%PDF-")
    assert reparacion is not None
    assert reparacion.desplazamiento == 34
    assert "warning" in reparacion.descripcion

    lectura = leer(crudo)
    assert lectura.paginas_con_texto == 1
    assert any("byte(s) antes del encabezado PDF" in str(a) for a in lectura.avisos)


def test_un_prefijo_desmedido_no_se_repara() -> None:
    """Un PDF escondido dentro de megabytes de otra cosa no es un PDF con
    prefijo: es otra cosa, y adivinarlo sería inventar."""
    crudo = b"x" * 9000 + _pdf(["Articulo 1."])
    with pytest.raises(PdfInvalido):
        validar(crudo)


# --- AT-020: página gráfica sin vaciar el documento ---------------------------


def test_una_pagina_grafica_no_vacia_el_documento() -> None:
    contenido = _pdf(
        [
            "Articulo 1. Se aprueba el reglamento general de becas para el periodo.",
            "Articulo 2. Los montos se actualizan segun la formula del anexo.",
            "",
        ],
        con_imagen={3},
    )
    lectura = leer(contenido)
    assert len(lectura.paginas) == 3
    assert lectura.paginas_con_texto == 2
    assert [p.clase for p in lectura.paginas] == ["TEXTO", "TEXTO", "GRAFICA"]
    assert lectura.cobertura == pytest.approx(0.6667, abs=1e-4)
    assert any("no se hace ocr" in str(a).lower() for a in lectura.avisos)


def test_un_documento_sin_texto_dice_que_no_sustenta_nada() -> None:
    lectura = leer(_pdf(["", ""], con_imagen={1, 2}))
    assert lectura.paginas_con_texto == 0
    assert any("no sustenta ninguna capacidad" in str(a) for a in lectura.avisos)
    assert any(a.severidad == "HIGH" for a in lectura.avisos)


def test_el_umbral_de_pagina_distingue_texto_de_folio() -> None:
    """Una página con solo el número de folio no es una página de texto."""
    lectura = leer(_pdf(["12"]))
    assert lectura.paginas[0].caracteres < MINIMO_CHARS_PAGINA
    assert lectura.paginas[0].clase == "VACIA"


# --- AT-021 y AT-056: períodos de las tablas ----------------------------------

# La detección de tablas es de pdfplumber; lo que se prueba acá es la decisión
# propia: con qué período se asocia cada tabla. Por eso la página es un doble
# que devuelve tablas conocidas, en vez de un PDF cuya grilla dependa de que la
# biblioteca la reconozca igual entre versiones.


class _PaginaConTablas:
    def __init__(self, tablas: list[list[list[str]]]) -> None:
        self._tablas = tablas

    def extract_tables(self):
        return self._tablas


TABLA_MONTOS = [["Nivel", "Monto"], ["Inicial", "10000"], ["Primario", "12000"]]
TABLA_MONOTRIBUTO = [["Categoria", "Tope"], ["A", "5000"]]


def test_una_tabla_con_un_solo_periodo_declarado_lo_toma() -> None:
    tablas = _tablas_de(
        _PaginaConTablas([TABLA_MONTOS]), 1, "Topes de ingresos marzo 2025\nNivel Monto"
    )
    assert len(tablas) == 1
    assert tablas[0].periodo == "marzo 2025"
    assert tablas[0].periodo_ambiguo is False


def test_una_tabla_sin_periodo_declarado_no_lo_hereda_del_archivo() -> None:
    """Tomar el año del nombre del archivo o de la fecha de subida es la forma
    más común de fechar mal una tabla de montos."""
    tablas = _tablas_de(_PaginaConTablas([TABLA_MONTOS]), 1, "Nivel Monto\nInicial 10000")
    assert tablas[0].periodo is None
    assert tablas[0].periodo_ambiguo is True
    assert "no se toma del nombre del archivo" in tablas[0].motivo_ambiguedad

    avisos = _avisos_de_tablas(tablas)
    assert avisos and avisos[0].severidad == "HIGH"


def test_dos_periodos_en_la_misma_pagina_dejan_la_asociacion_en_revision() -> None:
    """Asociar por cercanía haría que la tabla de monotributo herede el período
    de la de ingresos, que es de otro mes y de otro año."""
    texto = (
        "Topes de ingresos marzo 2025\nNivel Monto\nInicial 10000\n"
        "Monotributo enero 2024\nCategoria Tope\nA 5000"
    )
    tablas = _tablas_de(_PaginaConTablas([TABLA_MONTOS, TABLA_MONOTRIBUTO]), 3, texto)
    assert len(tablas) == 2
    assert all(t.periodo is None and t.periodo_ambiguo for t in tablas)
    assert all("herede el período de otra" in t.motivo_ambiguedad for t in tablas)

    avisos = _avisos_de_tablas(tablas)
    assert "2 tabla(s) sin período inequívoco" in str(avisos[0])
    assert "página 3" in str(avisos[0])


def test_el_ciclo_lectivo_se_reconoce_como_periodo() -> None:
    """El PDF de montos de becas fecha sus tablas por ciclo lectivo, no por mes."""
    assert _periodos_en_orden("Marco legal - ciclo lectivo 2026") == ["ciclo lectivo 2026"]


def test_un_epigrafe_posterior_no_alcanza_para_fechar_dos_tablas() -> None:
    """Una sola tabla y un solo período se asocian; agregar una segunda tabla
    rompe esa certeza aunque el período siga siendo uno."""
    una = _tablas_de(_PaginaConTablas([TABLA_MONTOS]), 1, "Nivel Monto\nVigencia 2025")
    assert una[0].periodo == "2025"

    dos = _tablas_de(
        _PaginaConTablas([TABLA_MONTOS, TABLA_MONOTRIBUTO]), 1, "Nivel Monto\nVigencia 2025"
    )
    assert all(t.periodo_ambiguo for t in dos)


# --- AT-075: la ruta no fecha el documento ------------------------------------


def test_la_carpeta_del_archivo_no_fecha_el_documento() -> None:
    captura = _captura(
        _pdf(["Anexo I. Reglamento general de becas."]),
        url="https://x/archivos/2019/anexo-i.pdf",
    )
    resultado = AdaptadorPdf().extraer(captura)
    documento = resultado.documentos[0]
    assert documento.fecha_documento is None
    assert documento.tipo_fecha is TipoFecha.DESCONOCIDA
    aviso = next(a for a in documento.avisos if "ruta sugiere" in str(a))
    assert "2019" in str(aviso)
    assert "dónde lo guardaron, no cuándo lo firmaron" in str(aviso)


def test_un_documento_que_declara_su_fecha_la_toma() -> None:
    """La ruta dice 2019 y el documento dice 2025: manda el documento."""
    captura = _captura(
        _pdf(["Buenos Aires, 14 de marzo de 2025", "Anexo I. Reglamento general de becas."]),
        url="https://x/archivos/2019/anexo-i.pdf",
    )
    documento = AdaptadorPdf().extraer(captura).documentos[0]
    assert documento.fecha_documento == dt.date(2025, 3, 14)
    assert documento.tipo_fecha is TipoFecha.SANCION


def test_las_fechas_de_las_notas_de_consolidacion_no_fechan_el_documento() -> None:
    """El Decreto 690/06 consolidado trae 34 fechas y ninguna es la suya."""
    captura = _captura(
        _pdf(
            [
                "Artículo 1° - Créase el programa.",
                "(Artículo 1° sustituido por el artículo 2° del Decreto 155/2023, "
                "publicado en el Boletín Oficial 6625 del 19/05/2023)",
            ]
        ),
        url="https://x/util/imagen.php?idn=86704",
    )
    documento = AdaptadorPdf().extraer(captura).documentos[0]
    assert documento.fecha_documento is None
    assert any("notas de consolidación" in str(a) for a in documento.avisos)
    # El acto que modificó sí queda identificado: es un dato aparte y útil.
    assert any("Decreto 155/2023" in str(a) for a in documento.avisos)


# --- Contrato del adaptador ---------------------------------------------------


def test_acepta_por_contenido_aunque_el_mime_mienta() -> None:
    adaptador = AdaptadorPdf()
    assert adaptador.acepta(_captura(_pdf(["Articulo 1."]), mime="text/html"))
    assert adaptador.acepta(_captura(b"<html/>", mime=None, url="https://x/guia.pdf"))
    assert not adaptador.acepta(_captura(b"<html/>", mime="text/html", url="https://x/pagina"))


def test_la_extraccion_informa_paginas_y_cobertura_por_pagina() -> None:
    contenido = _pdf(
        [
            "Articulo 1. El presente reglamento regula el otorgamiento de becas.",
            "Articulo 2. Los beneficiarios deberan acreditar residencia.",
        ]
    )
    documento = AdaptadorPdf().extraer(_captura(contenido)).documentos[0]
    assert documento.modo_extraccion == "PDF_TEXTO"
    assert documento.paginas == 2
    assert sorted(documento.chars_por_pagina) == ["1", "2"]
    assert documento.extraccion_score and documento.extraccion_score > 0
    assert len(documento.unidades) >= 2


# --- AT-019 con los bytes reales de la fuente ---------------------------------


def test_el_prefijo_real_del_boletin_de_caba_se_repara() -> None:
    """El caso no es hipotético. El endpoint legacy del Boletín Oficial de CABA
    antepone 231 bytes de una advertencia de PHP al PDF, con
    `Content-Type: application/pdf`. Aparece igual en D08, D09 y F40. La fixture
    son los bytes que devolvió la fuente, no una imitación."""
    import json
    import pathlib

    datos = json.loads(
        (
            pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "prefijo_boletin_caba.json"
        ).read_text()
    )
    crudo = datos["prefijo"].encode("utf-8") + _pdf(["Articulo 1. El objeto de esta norma."])

    utiles, reparacion = validar(crudo)
    assert utiles.startswith(b"%PDF-")
    assert reparacion is not None
    assert reparacion.desplazamiento == datos["desplazamiento"] == 231
    assert "POSTGRES_VERSION" in reparacion.descripcion
    assert datos["magic_siguiente"].startswith("%PDF-")
