"""El balde de fichas y la identidad del origen (P-017, criterio 3).

Sin base y sin servidor: lo que se prueba acá es la aritmética del límite y de
quién se cuenta. Que la API lo aplique se prueba en integración.
"""

from __future__ import annotations

import pytest

from backend_normativo.api.limites import (
    LIMITE_DEFECTO,
    VARIABLE_LIMITE,
    VARIABLE_PROXIES,
    Limitador,
    clave_de,
    limitador_de_consultas,
    origen_de,
    reiniciar_limitadores,
)


class _Cliente:
    def __init__(self, host: str) -> None:
        self.host = host


class _Solicitud:
    def __init__(self, host: str = "10.0.0.1", cabeceras: dict | None = None) -> None:
        self.client = _Cliente(host)
        self.headers = cabeceras or {}


def test_el_cupo_se_gasta_y_despues_frena() -> None:
    limitador = Limitador(cupo=3)
    assert [limitador.permitir("a", ahora=0.0).permitido for _ in range(3)] == [True] * 3
    veredicto = limitador.permitir("a", ahora=0.0)
    assert not veredicto.permitido
    assert veredicto.espera_s > 0
    assert veredicto.retry_after >= 1


def test_el_cupo_se_repone_con_el_tiempo() -> None:
    limitador = Limitador(cupo=60, ventana_s=60.0)
    for _ in range(60):
        assert limitador.permitir("a", ahora=0.0).permitido
    assert not limitador.permitir("a", ahora=0.0).permitido
    # Un segundo repone una ficha: 60 por minuto es una por segundo.
    assert limitador.permitir("a", ahora=1.0).permitido


def test_un_origen_no_gasta_el_cupo_de_otro() -> None:
    """Si el balde fuera uno solo, una dirección abusiva dejaría afuera a todos."""
    limitador = Limitador(cupo=2)
    assert limitador.permitir("a", ahora=0.0).permitido
    assert limitador.permitir("a", ahora=0.0).permitido
    assert not limitador.permitir("a", ahora=0.0).permitido
    assert limitador.permitir("b", ahora=0.0).permitido


def test_el_balde_no_acumula_mas_que_su_cupo() -> None:
    """Con ventanas fijas se puede gastar el doble en el peor momento posible."""
    limitador = Limitador(cupo=5, ventana_s=60.0)
    limitador.permitir("a", ahora=0.0)
    # Una hora después el balde está lleno, no rebosado.
    permitidas = sum(1 for _ in range(20) if limitador.permitir("a", ahora=3600.0).permitido)
    assert permitidas == 5


def test_mirar_no_gasta() -> None:
    limitador = Limitador(cupo=1)
    assert limitador.hay_cupo("a", ahora=0.0)
    assert limitador.hay_cupo("a", ahora=0.0)
    assert limitador.permitir("a", ahora=0.0).permitido
    assert not limitador.hay_cupo("a", ahora=0.0)


def test_en_cero_no_hay_limite() -> None:
    """Desactivarlo se pide a propósito: sirve para medir el techo del servicio."""
    limitador = Limitador(cupo=0)
    assert all(limitador.permitir("a", ahora=0.0).permitido for _ in range(1000))
    assert not limitador.activo


def test_los_baldes_llenos_y_viejos_se_barren() -> None:
    """Un diccionario que sólo crece es una fuga en el componente que defiende."""
    limitador = Limitador(cupo=5, ventana_s=1.0)
    for i in range(600):
        limitador.permitir(f"origen-{i}", ahora=float(i))
    assert limitador.origenes < 600


def test_la_clave_no_es_la_direccion() -> None:
    """Sirve para contar, no para saber de quién."""
    clave = clave_de(_Solicitud("192.168.1.44"))
    assert "192.168.1.44" not in clave
    assert clave == clave_de(_Solicitud("192.168.1.44"))
    assert clave != clave_de(_Solicitud("192.168.1.45"))


def test_sin_proxies_declarados_no_se_cree_la_cabecera(monkeypatch) -> None:
    """Creerle a `X-Forwarded-For` convierte el límite en un adorno."""
    monkeypatch.delenv(VARIABLE_PROXIES, raising=False)
    solicitud = _Solicitud("10.0.0.1", {"X-Forwarded-For": "1.2.3.4"})
    assert origen_de(solicitud) == "10.0.0.1"


def test_con_un_proxie_declarado_se_lee_el_salto_que_corresponde(monkeypatch) -> None:
    """El de más a la izquierda lo puede haber escrito quien llama."""
    monkeypatch.setenv(VARIABLE_PROXIES, "1")
    solicitud = _Solicitud("10.0.0.1", {"X-Forwarded-For": "9.9.9.9, 200.1.1.1"})
    assert origen_de(solicitud) == "200.1.1.1"


def test_una_cabecera_mas_corta_de_lo_declarado_no_se_usa(monkeypatch) -> None:
    """Faltan saltos: la petición no pasó por los proxies que el despliegue dice."""
    monkeypatch.setenv(VARIABLE_PROXIES, "2")
    solicitud = _Solicitud("10.0.0.1", {"X-Forwarded-For": "9.9.9.9"})
    assert origen_de(solicitud) == "10.0.0.1"


@pytest.mark.parametrize("valor", ["", "no-es-un-numero", "   "])
def test_una_variable_mal_escrita_no_deja_el_servicio_sin_limite(monkeypatch, valor) -> None:
    """El modo sin límite se pide poniendo 0, no equivocándose al escribir."""
    monkeypatch.setenv(VARIABLE_LIMITE, valor)
    reiniciar_limitadores()
    try:
        assert limitador_de_consultas().cupo == LIMITE_DEFECTO
    finally:
        monkeypatch.delenv(VARIABLE_LIMITE, raising=False)
        reiniciar_limitadores()
