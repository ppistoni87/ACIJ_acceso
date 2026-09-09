"""HU-037: la lectura de una medición de escalado.

Correr la medición de verdad tarda minutos y depende de la máquina. Lo que sí se
puede fijar es lo que hace falta que no se pierda: que el mismo número —el
caudal no se multiplica— no se lea igual cuando la máquina está sin CPU que
cuando le sobra. Son dos diagnósticos opuestos y la respuesta a cada uno es
distinta.
"""

from __future__ import annotations

from backend_normativo.calidad.escalado import Medida, Pool, ReporteEscalado, _revisar, formatear


def _reporte(*medidas: Medida, pool: Pool | None = None) -> ReporteEscalado:
    reporte = ReporteEscalado(medidas=list(medidas), cpus=4, pool=pool or Pool())
    _revisar(reporte)
    return reporte


def test_sin_cpu_libre_no_se_concluye_que_no_escala() -> None:
    """Es la conclusión fácil y sería falsa.

    Si un solo proceso ya deja la máquina sin CPU, que agregar procesos no
    mueva el caudal no dice nada del sistema: dice que no queda máquina.
    """
    reporte = _reporte(
        Medida(procesos=1, clientes=16, peticiones=1000, duracion_s=6.0, cpu_ocupada=94.0),
        Medida(procesos=4, clientes=16, peticiones=1050, duracion_s=6.0, cpu_ocupada=99.0),
    )
    dicho = " ".join(reporte.avisos)
    assert "no** dice que el sistema no escale" in dicho
    assert "máquinas separadas" in dicho


def test_con_cpu_de_sobra_sí_se_concluye_que_el_cuello_está_abajo() -> None:
    """Sobra procesador y aun así no sube: el límite no es el proceso."""
    reporte = _reporte(
        Medida(procesos=1, clientes=16, peticiones=1000, duracion_s=6.0, cpu_ocupada=20.0),
        Medida(procesos=4, clientes=16, peticiones=1050, duracion_s=6.0, cpu_ocupada=25.0),
    )
    dicho = " ".join(reporte.avisos)
    assert "el límite está abajo del proceso" in dicho
    assert "agregar instancias no alcanza" in dicho


def test_cuando_multiplica_se_dice_que_escala() -> None:
    reporte = _reporte(
        Medida(procesos=1, clientes=16, peticiones=600, duracion_s=6.0, cpu_ocupada=30.0),
        Medida(procesos=4, clientes=16, peticiones=2200, duracion_s=6.0, cpu_ocupada=95.0),
    )
    assert any("escala agregando procesos" in a for a in reporte.avisos)


def test_el_pool_por_proceso_que_excede_la_base_se_avisa() -> None:
    """Es una multiplicación, y sale mal justo cuando hay carga.

    Cuatro procesos con treinta conexiones cada uno le piden ciento veinte a una
    base que admite cien. No falla al arrancar: falla cuando llega el tráfico.
    """
    reporte = _reporte(
        Medida(procesos=1, clientes=16, peticiones=1000, duracion_s=6.0, cpu_ocupada=40.0),
        Medida(procesos=4, clientes=16, peticiones=1050, duracion_s=6.0, cpu_ocupada=45.0),
        pool=Pool(por_proceso=30, max_connections=100),
    )
    assert any("más de lo que hay" in a for a in reporte.avisos)


def test_un_pool_que_entra_no_avisa_nada() -> None:
    reporte = _reporte(
        Medida(procesos=1, clientes=16, peticiones=1000, duracion_s=6.0, cpu_ocupada=40.0),
        Medida(procesos=4, clientes=16, peticiones=1050, duracion_s=6.0, cpu_ocupada=45.0),
        pool=Pool(por_proceso=10, max_connections=100),
    )
    assert not any("más de lo que hay" in a for a in reporte.avisos)


def test_el_reporte_dice_lo_que_no_puede_decir() -> None:
    """Un reporte de rendimiento sin sus límites se lee como una promesa."""
    reporte = _reporte(
        Medida(procesos=1, clientes=16, peticiones=1000, duracion_s=6.0, cpu_ocupada=94.0),
    )
    texto = formatear(reporte)
    assert "## Qué no dice" in texto
    assert "loopback" in texto
