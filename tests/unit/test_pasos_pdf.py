"""HU-F54 · AT-022: los pasos de un instructivo en PDF.

El orden lo fija el número que el documento declara, no la posición en la que el
extractor devuelve el texto. Si un rótulo sale después de su contenido, ordenar
por lectura invierte el trámite y manda a alguien a hacer el paso 4 antes que
el 3.
"""

from __future__ import annotations

from backend_normativo.ingesta.adaptadores.pasos_pdf import encabezado_repetido, leer

# Recorte real del instructivo de becas alimentarias (F54): el paso 4 empieza en
# la página 3 y su documentación necesaria sigue en la 4, sin rótulo propio.
INSTRUCTIVO = [
    ["Becas", "Alimentarias", "Tutorial: cómo revisar una solicitud", "de beca alimentaria"],
    [
        "Becas alimentarias",
        "Paso 1",
        "Para revisar una solicitud deben ingresar al siguiente enlace:",
        "http://sistemas1.buenosaires.edu.ar/wsad/becas.php/",
        "Paso 2",
        "Hacer clic en el botón: Módulo de evaluación y otorgamiento de becas.",
        "1",
    ],
    [
        "Becas alimentarias",
        "Paso 3",
        "Una vez que hayan entrado al sistema, podrán visualizar la lista de becas.",
        "Paso 4",
        "Corroborar que los datos del alumno y la documentación esten cargados.",
        "2",
    ],
    [
        "Becas alimentarias",
        "Documentación necesaria:",
        "DNI del alumno, frente y dorso.",
        "Constancia de alumno regular.",
        "3",
    ],
    [
        "Becas alimentarias",
        "Paso 5",
        "En caso de haber alguna inconsistencia o faltante en la documentación cargada.",
        "4",
    ],
]


# --- AT-022: el orden lo declara el documento --------------------------------


def test_at022_los_pasos_se_ordenan_por_el_numero_que_declaran() -> None:
    """No por la posición en la que el extractor los devolvió."""
    desordenado = [
        [
            "Becas alimentarias",
            "Hacer clic en el botón de evaluación.",
            "Paso 2",
            "Ingresar al enlace del sistema.",
            "Paso 1",
            "1",
        ],
        ["Becas alimentarias", "Paso 3", "Revisar la documentación.", "2"],
        ["Becas alimentarias", "Paso 4", "Enviar la observación.", "3"],
    ]
    lectura = leer(desordenado)
    assert [p.numero for p in lectura.en_orden] == [1, 2, 3, 4]
    # El paso 2 se quedó con lo que vino después de su rótulo, no con lo de antes.
    paso2 = next(p for p in lectura.pasos if p.numero == 2)
    assert paso2.texto == "Ingresar al enlace del sistema."


def test_at022_un_paso_que_cruza_de_pagina_no_se_parte_en_dos() -> None:
    """El paso 4 empieza en la página 3 y su documentación está en la 4, sin
    rótulo propio: es el mismo paso, no uno nuevo sin número."""
    lectura = leer(INSTRUCTIVO)
    paso4 = next(p for p in lectura.pasos if p.numero == 4)

    assert paso4.paginas == [3, 4]
    assert "Documentación necesaria:" in paso4.texto
    assert "DNI del alumno" in paso4.texto
    assert len(lectura.pasos) == 5


def test_at022_los_cinco_pasos_del_instructivo_se_leen_completos() -> None:
    lectura = leer(INSTRUCTIVO)
    assert [p.numero for p in lectura.en_orden] == [1, 2, 3, 4, 5]
    assert lectura.consistente


def test_at022_lo_anterior_al_primer_rotulo_no_es_el_paso_uno() -> None:
    """La portada del instructivo no es una instrucción."""
    lectura = leer(INSTRUCTIVO)
    paso1 = next(p for p in lectura.pasos if p.numero == 1)
    assert "Tutorial" not in paso1.texto
    assert paso1.paginas == [2]


# --- La página se limpia sola ------------------------------------------------


def test_el_encabezado_que_se_repite_se_detecta_y_no_entra_en_ningun_paso() -> None:
    """Cada instructivo tiene el suyo: una lista de encabezados conocidos
    envejece mal."""
    lectura = leer(INSTRUCTIVO)
    assert lectura.encabezado_repetido == "Becas alimentarias"
    assert all("Becas alimentarias" not in p.texto for p in lectura.pasos)


def test_el_folio_de_la_pagina_no_es_contenido() -> None:
    lectura = leer(INSTRUCTIVO)
    paso5 = next(p for p in lectura.pasos if p.numero == 5)
    assert paso5.contenido == [
        "En caso de haber alguna inconsistencia o faltante en la documentación cargada."
    ]


def test_sin_suficientes_paginas_no_se_declara_un_encabezado() -> None:
    """Dos páginas que empiezan igual pueden ser casualidad."""
    assert encabezado_repetido([["Título"], ["Título"]]) is None


# --- Lo que no cierra se dice ------------------------------------------------


def test_un_numero_repetido_se_reporta_en_vez_de_renumerarse() -> None:
    paginas = [
        ["Encabezado", "Paso 1", "Ingresar.", "1"],
        ["Encabezado", "Paso 1", "Otra vez ingresar.", "2"],
        ["Encabezado", "Paso 2", "Revisar.", "3"],
    ]
    lectura = leer(paginas)
    assert len(lectura.pasos) == 3
    assert any("más de una vez" in a for a in lectura.avisos)
    assert not lectura.consistente


def test_un_salto_en_la_serie_se_reporta() -> None:
    """Puede estar en una página que no dejó texto; los que sí están no se
    renumeran para tapar el hueco."""
    paginas = [
        ["Encabezado", "Paso 1", "Ingresar.", "1"],
        ["Encabezado", "Paso 3", "Revisar.", "2"],
        ["Encabezado", "Paso 4", "Enviar.", "3"],
    ]
    lectura = leer(paginas)
    assert [p.numero for p in lectura.en_orden] == [1, 3, 4]
    assert any("Falta(n) el/los paso(s) [2]" in a for a in lectura.avisos)


def test_un_paso_solo_con_captura_de_pantalla_queda_vacio_y_lo_dice() -> None:
    """No hereda el texto del paso anterior."""
    paginas = [
        ["Encabezado", "Paso 1", "Ingresar al sistema.", "1"],
        ["Encabezado", "Paso 2", "2"],
        ["Encabezado", "Paso 3", "Enviar.", "3"],
    ]
    lectura = leer(paginas)
    paso2 = next(p for p in lectura.pasos if p.numero == 2)
    assert paso2.contenido == []
    assert any("sólo muestran una captura de pantalla" in a for a in lectura.avisos)


def test_un_rotulo_con_su_texto_en_la_misma_linea_no_pierde_el_texto() -> None:
    lectura = leer(
        [
            ["Encabezado", "Paso 1: Ingresar al sistema.", "1"],
            ["Encabezado", "Paso 2: Revisar la beca.", "2"],
            ["Encabezado", "Paso 3: Enviar.", "3"],
        ]
    )
    assert [p.texto for p in lectura.en_orden] == [
        "Ingresar al sistema.",
        "Revisar la beca.",
        "Enviar.",
    ]


def test_un_documento_sin_rotulos_no_inventa_pasos() -> None:
    lectura = leer([["Encabezado", "Un texto cualquiera.", "1"]])
    assert lectura.pasos == []
