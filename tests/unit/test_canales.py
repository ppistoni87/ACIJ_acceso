"""Qué cuenta como un canal y qué no (P-006)."""

from __future__ import annotations

import pytest

from backend_normativo.curacion.canales import candidatos_de, normalizar_telefono
from backend_normativo.db.vocabularios import TipoCanal


@pytest.mark.parametrize(
    "crudo, esperado",
    [
        ("0800-222-3245", "08002223245"),
        ("(11) 6536-6767", "1165366767"),
        ("11-4024-0764", "1140240764"),
        ("+54 11 2771 3385", "+541127713385"),
        ("(011) 4971-7181", "01149717181"),
    ],
)
def test_un_telefono_publicado_se_normaliza(crudo: str, esperado: str) -> None:
    assert normalizar_telefono(crudo) == esperado


@pytest.mark.parametrize(
    "crudo",
    [
        "1999 1998 1997",
        "2002 2001 2000",
        "1234",
        "12",
        "123456789012345",
    ],
)
def test_lo_que_parece_un_telefono_y_no_lo_es_se_descarta(crudo: str) -> None:
    """«1999 1998 1997» tiene la forma de un teléfono y es una lista de años."""
    assert normalizar_telefono(crudo) is None


def test_no_se_completa_una_caracteristica_que_falta() -> None:
    """Un número sin característica es uno al que no se puede llamar de afuera.

    Completarlo con la de Buenos Aires sería fabricar el dato: el canal se
    guarda tal como lo publicaron o no se guarda.
    """
    assert normalizar_telefono("4024-0764") == "40240764"
    assert not normalizar_telefono("4024-0764").startswith("11")


def test_el_tipo_lo_dice_la_pagina_y_no_el_numero() -> None:
    """Un número puede ser teléfono o WhatsApp, y eso lo declara el rótulo."""
    telefono = candidatos_de("Atención 0800-222-3245", "Centro de Acceso a la Justicia")
    whatsapp = candidatos_de("(54-11) 2771-3385", "WhatsApp para prevención de desalojos")
    assert telefono[0][0] == TipoCanal.TELEFONO
    assert whatsapp[0][0] == TipoCanal.WHATSAPP


def test_un_formulario_no_es_una_web_cualquiera() -> None:
    formulario = candidatos_de(
        "Completá https://www.argentina.gob.ar/aviso", "Formulario de aviso de desalojo"
    )
    generica = candidatos_de("Más info en https://www.argentina.gob.ar/enre", "Contacto")
    assert formulario[0][0] == TipoCanal.FORMULARIO_WEB
    assert generica[0][0] == TipoCanal.WEB


def test_una_seccion_puede_traer_varios_canales() -> None:
    hallazgos = candidatos_de(
        "Oficinas NUEVA BALVANERA (11) 6536-6767 oad-balvanera@mptutelar.gob.ar", "Oficinas"
    )
    tipos = {t for t, _, _ in hallazgos}
    assert TipoCanal.TELEFONO in tipos
    assert TipoCanal.EMAIL in tipos


def test_un_correo_se_guarda_en_minusculas() -> None:
    hallazgos = candidatos_de("Escribí a Consultas@MPTutelar.GOB.ar", "Contacto")
    assert hallazgos[0][2] == "consultas@mptutelar.gob.ar"
    assert hallazgos[0][1] == "Consultas@MPTutelar.GOB.ar", "el crudo conserva lo publicado"


def test_una_seccion_sin_canales_no_inventa_ninguno() -> None:
    texto = "El programa acompaña a las familias en situación de calle."
    assert candidatos_de(texto, "Objeto") == []
