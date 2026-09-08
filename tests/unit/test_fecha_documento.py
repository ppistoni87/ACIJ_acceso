"""HU-F67 · AT-075: de dónde sale el año de un documento.

Tres formas de equivocarse, las tres presentes en el corpus: leerlo de la
carpeta que aloja el PDF, tomar la primera fecha que aparece en el texto, o
tomar la última. En el Decreto 690/06 consolidado las dos últimas dan 2008 y
2025 respectivamente, y es un decreto de 2006.
"""

from __future__ import annotations

import datetime as dt

import pytest

from backend_normativo.ingesta.adaptadores.fecha_documento import (
    DATA_EL_DOCUMENTO,
    DATA_OTRO_ACTO,
    SIN_CONTEXTO,
    anio_en_la_ruta,
    leer,
)

# Recorte del texto real del Decreto 690/06 consolidado (F40).
CONSOLIDADO = """Visto el Expediente N° 49.368/05, la Constitución de la Ciudad Autónoma
Artículo 1° - Derógase el Decreto N° 895/02 (B.O.C.B.A. N° 1503).
Artículo 2° - Crear el "Programa Apoyo para Personas en Situación de Vulnerabilidad".
(Artículo 2° sustituido del artículo 1° del Decreto 161/2025, publicado en el Boletín Oficial
7104 del 22/04/2025)
Artículo 3° - El programa otorga un apoyo económico.
(Artículo 3° sustituido por el artículo 2° del Decreto 155/2023, publicado en el Boletín Oficial
6625 del 19/05/2023)
(Artículo 4° sustituido por el artículo 1° del Decreto 167/2011, publicado en el Boletín Oficial
3641 del 11/04/2011)
"""

# El mismo patrón con un paréntesis adentro, como los que trae el texto real.
NOTA_ANIDADA = """Artículo 5° - Las prestaciones se abonan por mes vencido.
(Artículo 5° sustituido por el artículo 1° del Decreto 148/2021 (B.O. 6112), publicado
el 29/04/2021. Vigencia: a partir del día siguiente)
"""


# --- AT-075: la ruta no fecha el documento -----------------------------------


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        # Las tres rutas son reales del corpus.
        ("https://www.argentina.gob.ar/sites/default/files/2021/08/guia.pdf", 2021),
        ("https://static.buenosaires.gob.ar/sites/default/files/2025-11/21_instructivo.pdf", 2025),
        ("https://static.buenosaires.gob.ar/sites/default/files/2026-08/Marco_legal.pdf", 2026),
        # `1621-25` es el número de la resolución, no un año: no se inventa uno.
        ("https://documentosboletinoficial.buenosaires.gob.ar/PE-RES-MEDGC-1621-25-ANX.pdf", None),
        ("https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=86704", None),
    ],
)
def test_el_anio_de_la_ruta_se_calcula_para_decir_que_no_se_usa(
    url: str, esperado: int | None
) -> None:
    assert anio_en_la_ruta(url) == esperado


def test_at075_un_anexo_en_carpeta_vieja_no_toma_el_anio_de_la_carpeta() -> None:
    """El caso literal: un anexo firmado después, alojado en una carpeta vieja."""
    lectura = leer(
        "Anexo I. Reglamento general de becas.",
        url="https://x.gob.ar/sites/default/files/2019/08/anexo-i.pdf",
    )
    assert lectura.fecha is None
    assert lectura.anio_en_la_ruta == 2019
    assert "no se usa" in lectura.motivo


def test_at075_el_acto_madre_queda_identificado() -> None:
    """Las notas no fechan este documento pero sí nombran los actos que lo
    modificaron. Eso no se descarta junto con la fecha."""
    lectura = leer(CONSOLIDADO, url="https://x.gob.ar/util/imagen.php?idn=86704")
    assert lectura.actos_citados == [
        "Decreto 161/2025",
        "Decreto 155/2023",
        "Decreto 167/2011",
    ]


def test_at075_ni_la_primera_ni_la_ultima_fecha_del_texto_fechan_el_documento() -> None:
    """Tomar la primera daría 2011; la última, 2025. Es un decreto de 2006."""
    lectura = leer(CONSOLIDADO)
    assert lectura.fecha is None
    assert not lectura.determinada
    fechas = sorted(h.fecha for h in lectura.halladas)
    assert fechas[0].year == 2011
    assert fechas[-1].year == 2025
    assert all(h.clase == DATA_OTRO_ACTO for h in lectura.halladas)


# --- Cuándo sí se toma -------------------------------------------------------


def test_un_encabezado_de_lugar_y_fecha_fecha_el_documento() -> None:
    lectura = leer("Buenos Aires, 14 de marzo de 2025\nVISTO: el expediente...")
    assert lectura.fecha == dt.date(2025, 3, 14)
    assert lectura.tipo_fecha == "SANCION"
    assert lectura.halladas[0].clase == DATA_EL_DOCUMENTO


def test_una_formula_de_sancion_fecha_el_documento() -> None:
    lectura = leer(
        "Dada en la Sala de Sesiones de la Legislatura, a los 12 días del mes de diciembre de 2019."
    )
    assert lectura.fecha == dt.date(2019, 12, 12)


def test_el_documento_le_gana_a_la_ruta() -> None:
    lectura = leer(
        "Buenos Aires, 14 de marzo de 2025\nAnexo I.",
        url="https://x.gob.ar/sites/default/files/2019/08/anexo-i.pdf",
    )
    assert lectura.fecha == dt.date(2025, 3, 14)
    assert lectura.anio_en_la_ruta == 2019


def test_dos_fechas_declaradas_distintas_no_se_desempatan_solas() -> None:
    lectura = leer("Buenos Aires, 14 de marzo de 2025\nCórdoba, 3 de abril de 2024\n")
    assert lectura.fecha is None
    assert "ninguna manda sobre la otra" in lectura.motivo


# --- Lo que no dice qué fecha ------------------------------------------------


def test_una_fecha_suelta_no_fecha_el_documento() -> None:
    lectura = leer("El plazo vence el 30/06/2025 y no hay prórroga.")
    assert lectura.fecha is None
    assert lectura.halladas[0].clase == SIN_CONTEXTO
    assert "una fecha suelta no es la del documento" in lectura.motivo


def test_una_nota_con_parentesis_adentro_se_lee_entera() -> None:
    """Buscar el paréntesis más cercano hacia atrás encuentra el interno y
    pierde el verbo que dice que la fecha es de otro acto."""
    lectura = leer(NOTA_ANIDADA)
    assert lectura.fecha is None
    assert [h.clase for h in lectura.halladas] == [DATA_OTRO_ACTO]
    assert lectura.actos_citados == ["Decreto 148/2021"]


def test_una_fecha_imposible_no_es_una_fecha() -> None:
    """`31/02/2025` es un error de lectura del PDF, no un día."""
    lectura = leer("Buenos Aires, 31 de febrero de 2025\nVISTO:")
    assert lectura.fecha is None
    assert not lectura.halladas


def test_un_documento_sin_texto_lo_dice_en_vez_de_usar_la_ruta() -> None:
    lectura = leer("   ", url="https://x.gob.ar/sites/default/files/2021/08/guia.pdf")
    assert lectura.fecha is None
    assert "La ruta no la reemplaza" in lectura.motivo


# --- Un documento grande no cuelga la ingesta --------------------------------


def test_los_parentesis_se_calculan_una_vez_y_no_por_fecha() -> None:
    """Buscar el paréntesis que envuelve cada fecha recorriendo el texto desde
    el principio vuelve la lectura cuadrática. Un boletín de 240 KB con cuatro
    mil fechas tardaba treinta y un segundos: tiempo de ingesta que una captura
    legítima puede consumir entero."""
    import time

    texto = "Artículo 1. El plazo vence el 30/06/2025 y no hay prórroga. " * 4000
    arranque = time.perf_counter()
    lectura = leer(texto)
    tardanza = time.perf_counter() - arranque

    assert len(lectura.halladas) == 4000
    assert tardanza < 5.0, f"tardó {tardanza:.1f} s: el recorrido volvió a ser cuadrático"


def test_una_nota_con_parentesis_anidados_sigue_leyendose_entera() -> None:
    """El cálculo por lotes tiene que seguir devolviendo el paréntesis externo."""
    texto = (
        "Artículo 5.- Las prestaciones se abonan por mes vencido.\n"
        "(Artículo 5° sustituido por el artículo 1° del Decreto 148/2021 (B.O. 6112), "
        "publicado el 29/04/2021. Vigencia: a partir del día siguiente)"
    )
    lectura = leer(texto)
    assert [h.clase for h in lectura.halladas] == [DATA_OTRO_ACTO]
    assert lectura.actos_citados == ["Decreto 148/2021"]
