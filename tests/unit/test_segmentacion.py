"""HU-008: segmentar sin perder jerarquía ni confundir citas con dispositivo."""

from __future__ import annotations

from backend_normativo.curacion.segmentacion import Parrafo, Segmentador, unir_renglones
from backend_normativo.db.vocabularios import RolContenido, TipoUnidad


def _parrafos(*textos: str, entrecomillados: set[int] = frozenset()) -> list[Parrafo]:
    parrafos: list[Parrafo] = []
    cursor = 0
    for indice, texto in enumerate(textos):
        parrafos.append(
            Parrafo(
                texto=texto,
                inicio=cursor,
                fin=cursor + len(texto),
                entrecomillado=indice in entrecomillados,
            )
        )
        cursor += len(texto) + 1
    return parrafos


def test_reconoce_articulos_y_su_orden() -> None:
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 1°- Se instituye el régimen.",
            "ARTICULO 2°.- Quedan comprendidos los trabajadores.",
            "ART. 3 - Deróganse las normas anteriores.",
        )
    )
    articulos = resultado.articulos_dispositivos
    assert [a.numero for a in articulos] == ["1", "2", "3"]
    assert all(a.tipo is TipoUnidad.ARTICULO for a in articulos)


def test_conserva_el_sufijo_como_parte_de_la_identidad() -> None:
    """F33: separar artículos con sufijos. El 14 bis no es el 14."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 14.- Prestación por hijo.",
            "ARTICULO 14 bis.- Prestación por hijo con discapacidad.",
            "ARTÍCULO 14 ter.- Complemento.",
        )
    )
    articulos = resultado.articulos_dispositivos
    assert [(a.numero, a.sufijo) for a in articulos] == [
        ("14", None),
        ("14", "bis"),
        ("14", "ter"),
    ]
    # Rutas distintas: el sufijo entra en la identidad.
    assert len({a.ruta for a in articulos}) == 3


def test_un_articulo_sustituido_no_es_una_raiz() -> None:
    """F23: la Ley 547 sustituye artículos y transcribe su texto. Ese texto
    comparte número pero cuelga del artículo que lo introduce."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 1°.- Sustitúyese el artículo 10 de la Ordenanza 43.478 por el siguiente:",
            "ARTICULO 10.- El beneficio se otorgará a las familias que acrediten residencia.",
            "ARTICULO 2°.- Comuníquese al Poder Ejecutivo.",
            entrecomillados={1},
        )
    )
    raices = resultado.articulos_dispositivos
    assert [a.numero for a in raices] == ["1", "2"]

    sustituido = [u for u in resultado.unidades if u.rol_contenido is RolContenido.SUSTITUTIVO]
    assert len(sustituido) == 1
    assert sustituido[0].numero == "10"
    # Cuelga del artículo 1, que es el que lo sustituye.
    assert resultado.unidades[sustituido[0].padre_indice].numero == "1"
    assert sustituido[0].ruta.startswith(raices[0].ruta)


def test_un_numero_que_retrocede_sin_verbo_queda_marcado_como_ambiguo() -> None:
    """El parser no adivina: informa y deja la decisión a la revisión."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 5°.- Primera disposición.",
            "ARTICULO 3°.- Texto que aparece fuera de secuencia.",
        )
    )
    ambiguas = [u for u in resultado.unidades if u.ambigua]
    assert len(ambiguas) == 1
    assert ambiguas[0].numero == "3"
    assert ambiguas[0].rol_contenido is RolContenido.CITADO
    assert resultado.avisos


def test_la_jerarquia_de_titulos_y_capitulos_se_conserva() -> None:
    resultado = Segmentador().segmentar(
        _parrafos(
            "TITULO I - Disposiciones generales",
            "CAPITULO I - Del ámbito de aplicación",
            "ARTICULO 1°.- Ámbito.",
            "CAPITULO II - De los beneficiarios",
            "ARTICULO 2°.- Beneficiarios.",
            "TITULO II - Del procedimiento",
            "ARTICULO 3°.- Procedimiento.",
        )
    )
    por_numero = {a.numero: a for a in resultado.articulos_dispositivos}
    assert "titulo-I/capitulo-I" in por_numero["1"].ruta
    assert "titulo-I/capitulo-II" in por_numero["2"].ruta
    assert "titulo-II" in por_numero["3"].ruta
    assert "capitulo" not in por_numero["3"].ruta


def test_un_anexo_reinicia_la_numeracion_sin_marcar_ambiguedad() -> None:
    """El artículo 1 de un anexo no retrocede respecto del cuerpo principal."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 1°.- Apruébase el anexo.",
            "ARTICULO 2°.- Comuníquese.",
            "ANEXO I",
            "ARTICULO 1°.- Objeto del anexo.",
        )
    )
    assert not [u for u in resultado.unidades if u.ambigua]
    del_anexo = [
        u for u in resultado.articulos_dispositivos if "anexo" in u.ruta and u.numero == "1"
    ]
    assert len(del_anexo) == 1


def test_los_incisos_cuelgan_de_su_articulo() -> None:
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 1°.- Se instituye el régimen basado en:",
            "a) Un subsistema contributivo.",
            "b) Un subsistema no contributivo.",
        )
    )
    incisos = [u for u in resultado.unidades if u.tipo is TipoUnidad.INCISO]
    assert [i.numero for i in incisos] == ["a", "b"]
    assert all(resultado.unidades[i.padre_indice].numero == "1" for i in incisos)


def test_visto_considerando_y_transitorias_se_conservan() -> None:
    """La especificación pide preservar preámbulo, transitorias y anexos: no
    son ruido descartable."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "VISTO las Leyes Nros. 22.431 y 24.714, y",
            "CONSIDERANDO:",
            "Que es necesario concentrar la asistencia.",
            "ARTICULO 1°.- Créase el sistema.",
            "DISPOSICIONES TRANSITORIAS",
            "El régimen anterior se mantiene hasta el cierre del ejercicio.",
        )
    )
    tipos = {u.tipo for u in resultado.unidades}
    assert TipoUnidad.VISTO in tipos
    assert TipoUnidad.CONSIDERANDO in tipos
    assert TipoUnidad.TRANSITORIA in tipos


def test_una_nota_editorial_no_es_texto_dispositivo() -> None:
    """F33: la nota del boletín lleva información de vigencia, pero no es la
    norma. Se conserva con su propio rol."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "(Nota Infoleg: norma abrogada por art. 26 del Decreto N° 1382/01 y "
            "restablecida su vigencia por Decreto N° 1604/2001)",
            "ARTICULO 1°.- Se instituye el régimen.",
        )
    )
    notas = [u for u in resultado.unidades if u.rol_contenido is RolContenido.NOTA]
    assert len(notas) == 1
    assert "abrogada" in notas[0].texto
    assert notas[0] not in resultado.articulos_dispositivos


def test_el_texto_no_clasificado_queda_visible() -> None:
    """Los segmentos no reconocidos detienen la publicación afectada: no pueden
    desaparecer en silencio."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "Bs. As., 1/11/2001",
            "Encabezado sin estructura reconocible",
            "ARTICULO 1°.- Disposición.",
        )
    )
    assert len(resultado.sin_clasificar) == 2
    assert 0.0 < resultado.cobertura < 1.0


def test_las_rutas_dispositivas_no_se_repiten() -> None:
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 1°.- Sustitúyese el artículo 1° por el siguiente:",
            "ARTICULO 1°.- Texto nuevo del artículo sustituido.",
            "ARTICULO 2°.- Vigencia.",
            entrecomillados={1},
        )
    )
    rutas = [u.ruta for u in resultado.articulos_dispositivos]
    assert len(rutas) == len(set(rutas))
    todas = [u.ruta for u in resultado.unidades]
    assert len(todas) == len(set(todas))


def test_el_texto_dice_que_articulo_sustituye_y_eso_alcanza() -> None:
    """F23: cuando el artículo nombra el número que sustituye, no hay nada que
    inferir ni que confirmar."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "Artículo 1° - Sustitúyese el artículo 10 de la Ordenanza N° 43.478 "
            "por el siguiente texto:",
            "Artículo 10 - El Poder Ejecutivo brindará un servicio de desayuno.",
            "Artículo 2° - Sustitúyese el artículo 16 de la Ordenanza N° 43.478.",
            "Artículo 16 - La Comisión para el otorgamiento de las becas.",
            "Artículo 3° - Comuníquese.",
        )
    )
    assert [a.numero for a in resultado.articulos_dispositivos] == ["1", "2", "3"]
    sustituidos = [u for u in resultado.unidades if u.rol_contenido is RolContenido.SUSTITUTIVO]
    assert [u.numero for u in sustituidos] == ["10", "16"]
    # Sin ambigüedad: el texto nombró los artículos que sustituye.
    assert not [u for u in resultado.unidades if u.ambigua]
    assert resultado.avisos == []


def test_varios_articulos_en_una_sola_sustitucion() -> None:
    resultado = Segmentador().segmentar(
        _parrafos(
            "ARTICULO 1°.- Sustitúyense los artículos 4 y 5 de la Ley 1234 por los siguientes:",
            "ARTICULO 4°.- Primer texto sustituido.",
            "ARTICULO 5°.- Segundo texto sustituido.",
            "ARTICULO 2°.- De forma.",
        )
    )
    assert [a.numero for a in resultado.articulos_dispositivos] == ["1", "2"]
    assert not [u for u in resultado.unidades if u.ambigua]


def test_dos_bloques_sin_numero_no_comparten_ruta() -> None:
    """Un PDF que encabeza dos bloques con la palabra «ANEXO» a secas produce
    dos unidades. Si la ruta no las separa, la segunda pisa a la primera y el
    documento pierde la mitad de su contenido sin que nadie se entere."""
    resultado = Segmentador().segmentar(
        _parrafos(
            "ANEXO",
            "Se aprueban los formularios de inscripción.",
            "ANEXO",
            "Se aprueba el instructivo de revisión.",
        )
    )
    rutas = [u.ruta for u in resultado.unidades if u.tipo is TipoUnidad.ANEXO]
    assert len(rutas) == len(set(rutas)), f"Rutas repetidas: {rutas}"


# --- Renglones cortados por el ancho de la página -------------------------------


def test_une_los_renglones_de_un_parrafo_cortado() -> None:
    """Varios boletines publican el PDF convertido con un `<p>` por línea.

    Sin unirlos, una regla que cita una oración entera no cabe en ninguna unidad
    y su evidencia queda apuntando a media frase.
    """
    unidos = unir_renglones(
        _parrafos(
            "a) Acreditar identidad y residencia en la Ciudad Autónoma de Buenos Aires con una",
            "antigüedad mínima de dos (2) años. Quedan exceptuadas de este requisito las",
            "personas víctimas de trata de personas o violencia de género, debidamente",
            "acreditadas por los organismos competentes.",
        )
    )
    assert len(unidos) == 1
    assert "con una antigüedad mínima" in unidos[0].texto
    assert unidos[0].texto.endswith("competentes.")
    assert (unidos[0].inicio, unidos[0].fin) == (0, len(unidos[0].texto))


def test_no_une_dos_incisos_distintos() -> None:
    """El renglón anterior no cerró oración, pero el siguiente abre un inciso.

    Unirlos metería dos requisitos en una sola unidad y cualquier cita del
    segundo quedaría respaldada por el texto del primero.
    """
    unidos = unir_renglones(
        _parrafos(
            "b) No alcanzar el ingreso total de las familias para cubrir la Canasta Básica",
            "c) No ser titular de bienes inmuebles",
        )
    )
    assert len(unidos) == 2


def test_no_une_las_filas_de_un_directorio() -> None:
    """Una guía de oficinas tampoco cierra oración y no está cortada en renglones.

    El teléfono, el correo y la localidad son datos distintos: pegarlos haría
    que el mail de una oficina quedara adentro del interno de otra.
    """
    unidos = unir_renglones(
        _parrafos(
            "Teléfono: 5030-9714 - Interno 6185",
            "defensoriacomuna1sur@buenosaires.gob.ar",
            "Avellaneda",
        )
    )
    assert len(unidos) == 3


def test_une_aunque_el_renglon_siguiente_empiece_con_mayuscula() -> None:
    """«...para cubrir la» no puede terminar una oración, empiece como empiece
    el renglón de abajo. Un nombre propio partido por el ancho de la página se
    reconoce por dónde cortó el de arriba, no por la mayúscula del de abajo."""
    unidos = unir_renglones(
        _parrafos(
            "b) No alcanzar el ingreso total de las familias, para cubrir la",
            "Canasta Básica Total (CBT) fijada por el INDEC.",
        )
    )
    assert len(unidos) == 1
    assert "para cubrir la Canasta Básica Total" in unidos[0].texto


def test_une_un_parentesis_corto_y_no_una_nota_del_boletin() -> None:
    """«(INDEC), u organismo…» continúa la oración; «(Artículo sustituido por…)»
    es lo que el boletín dice sobre la norma y no forma parte de ella."""
    continuacion = unir_renglones(
        _parrafos(
            "fijada por el Instituto Nacional de Estadísticas y Censos",
            "(INDEC), u organismo que en el futuro lo reemplace;",
        )
    )
    assert len(continuacion) == 1

    nota = unir_renglones(
        _parrafos(
            "ARTICULO 14 bis.- La asignación se abona a uno solo de los padres",
            "(Artículo sustituido por art. 1º del Decreto Nº 840/2020 B.O. 4/11/2020)",
        )
    )
    assert len(nota) == 2


def test_un_subinciso_abre_unidad_propia() -> None:
    """`j.2)` es un ítem, no la continuación del anterior. `RE_INCISO` no lo
    reconoce, así que sin su propia marca quedaría pegado al párrafo de arriba."""
    unidos = unir_renglones(
        _parrafos(
            "j.1) Asignación por Hijo: la suma de PESOS CIEN ($ 100) para los beneficiarios",
            "j.2) Asignación por Hijo con Discapacidad: la suma de PESOS CUATROCIENTOS",
        )
    )
    assert len(unidos) == 2


def test_unir_no_toca_un_texto_que_ya_venia_en_parrafos() -> None:
    """Si cada bloque es un párrafo de verdad, unir no tiene nada que hacer y no
    lo hace: los desplazamientos de todo lo que ya estaba bien no se mueven."""
    parrafos = _parrafos(
        "ARTICULO 1°- Se instituye el régimen con alcance nacional.",
        "ARTICULO 2°- Quedan comprendidos los trabajadores en relación de dependencia.",
    )
    unidos = unir_renglones(parrafos)
    assert [p.texto for p in unidos] == [p.texto for p in parrafos]
    assert [(p.inicio, p.fin) for p in unidos] == [(p.inicio, p.fin) for p in parrafos]


def test_un_renglon_entrecomillado_marca_todo_el_parrafo() -> None:
    """Si un renglón venía entrecomillado, el párrafo unido queda marcado así.

    Tratar como disposición propia un texto que la norma está citando es el
    error caro de los dos: hace que una norma afirme lo que solo transcribe.
    """
    unidos = unir_renglones(_parrafos("La norma citada dice que el plazo", "es de diez días."))
    assert len(unidos) == 1
    unidos = unir_renglones(
        _parrafos("La norma citada dice que el plazo", "es de diez días.", entrecomillados={1})
    )
    assert unidos[0].entrecomillado
