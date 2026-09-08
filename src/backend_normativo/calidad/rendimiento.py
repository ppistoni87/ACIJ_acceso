"""HU-037: cuánto tarda cada consulta sobre el corpus que hay.

Una latencia sin decir sobre cuántas filas se midió no significa nada: la misma
consulta que responde en 8 ms sobre veinte normas puede tardar segundos sobre
cuatrocientas mil. Por eso el reporte lleva el tamaño del corpus al lado de los
números, y por eso mide sobre la base real y no sobre una de prueba.

Lo que esto **no** mide, y conviene no leerlo como si lo midiera: concurrencia
—las consultas van una después de otra—, latencia de red, y el comportamiento
con la caché fría de un servidor recién arrancado. La primera repetición de cada
consulta se informa aparte justamente porque es la única que se parece a eso.
"""

from __future__ import annotations

import concurrent.futures
import statistics
import time
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# Las consultas que hace el sistema conversacional, con los parámetros que
# devuelven algo sobre el corpus real.
CONSULTAS: tuple[tuple[str, str, dict], ...] = (
    ("normas: listado", "/v1/normas", {"limite": 20}),
    ("normas: búsqueda por texto", "/v1/normas", {"q": "asignación familiar", "limite": 20}),
    ("normas: búsqueda por tipo y año", "/v1/normas", {"q": "beca", "limite": 50}),
    ("beneficios", "/v1/beneficios", {}),
    ("puntos de atención", "/v1/puntos-atencion", {}),
    ("puntos por jurisdicción", "/v1/puntos-atencion", {"jurisdiccion": "AR-B"}),
    ("puntos por alcance municipal", "/v1/puntos-atencion", {"alcance": "MUNICIPAL"}),
    ("barrios RENABAP por nombre", "/v1/barrios-renabap", {"q": "villa"}),
    ("cobertura del release", "/v1/cobertura", {}),
)

TABLAS_DEL_CORPUS = (
    "normas",
    "norma_versiones",
    "unidades_documentales",
    "evidencias",
    "registro_versiones",
    "puntos_atencion",
    "canales",
    "barrios_renabap",
)


@dataclass
class Medicion:
    nombre: str
    ruta: str
    repeticiones: int = 0
    primera_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    max_ms: float = 0.0
    filas: int | None = None
    estado: int = 0

    @property
    def sirvio(self) -> bool:
        return 200 <= self.estado < 300


@dataclass
class Concurrencia:
    """Qué pasa cuando varias personas preguntan a la vez."""

    hilos: int = 0
    consultas: int = 0
    duracion_s: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    max_ms: float = 0.0
    errores: int = 0

    @property
    def por_segundo(self) -> float:
        return round(self.consultas / self.duracion_s, 1) if self.duracion_s else 0.0


@dataclass
class ReporteRendimiento:
    corpus: dict[str, int] = field(default_factory=dict)
    tamano_base: str = ""
    repeticiones: int = 0
    mediciones: list[Medicion] = field(default_factory=list)
    concurrencia: list[Concurrencia] = field(default_factory=list)
    motor_por_segundo: float = 0.0

    @property
    def peor(self) -> Medicion | None:
        return max(self.mediciones, key=lambda m: m.p95_ms, default=None)

    @property
    def fallidas(self) -> list[Medicion]:
        return [m for m in self.mediciones if not m.sirvio]


def _percentil(valores: list[float], fraccion: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, round(fraccion * (len(ordenados) - 1)))
    return round(ordenados[indice], 2)


def medir_corpus(conexion: Connection) -> tuple[dict[str, int], str]:
    """Cuántas filas tiene cada tabla y cuánto pesa la base."""
    corpus = {
        # Los nombres salen de una tupla del módulo, no de la entrada.
        tabla: conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()
        for tabla in TABLAS_DEL_CORPUS
    }
    tamano = conexion.execute(
        text("SELECT pg_size_pretty(pg_database_size(current_database()))")
    ).scalar_one()
    return corpus, tamano


def correr(
    conexion: Connection,
    cliente,
    *,
    repeticiones: int = 12,
    hilos: tuple[int, ...] = (1, 4, 16),
) -> ReporteRendimiento:
    """Mide cada consulta `repeticiones` veces sobre la base ya conectada."""
    corpus, tamano = medir_corpus(conexion)
    reporte = ReporteRendimiento(corpus=corpus, tamano_base=tamano, repeticiones=repeticiones)

    for nombre, ruta, params in CONSULTAS:
        tiempos: list[float] = []
        estado = 0
        filas: int | None = None
        for _ in range(repeticiones):
            arranque = time.perf_counter()
            respuesta = cliente.get(ruta, params=params)
            tiempos.append((time.perf_counter() - arranque) * 1000)
            estado = respuesta.status_code
            if filas is None and 200 <= estado < 300:
                filas = _cuantas(respuesta.json())
        reporte.mediciones.append(
            Medicion(
                nombre=nombre,
                ruta=ruta,
                repeticiones=repeticiones,
                # La primera es la única que se parece a una caché fría.
                primera_ms=round(tiempos[0], 2),
                p50_ms=round(statistics.median(tiempos), 2),
                p95_ms=_percentil(tiempos, 0.95),
                max_ms=round(max(tiempos), 2),
                filas=filas,
                estado=estado,
            )
        )

    for cuantos in hilos:
        reporte.concurrencia.append(medir_concurrencia(cliente, hilos=cuantos))
    # El mismo trabajo contra el motor, sin la API en el medio: dice si el techo
    # de arriba es de la base o del proceso.
    reporte.motor_por_segundo = _caudal_del_motor(conexion, hilos=max(hilos))
    return reporte


def _caudal_del_motor(conexion: Connection, *, hilos: int, por_hilo: int = 10) -> float:
    """Cuántas consultas por segundo sostiene el motor con la misma concurrencia."""
    motor = conexion.engine
    consulta = text("SELECT count(*) FROM normas WHERE anio = 2020")

    def ronda(_: int) -> None:
        with motor.connect() as propia:
            for _ in range(por_hilo):
                propia.execute(consulta).scalar_one()

    arranque = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=hilos) as pool:
        list(pool.map(ronda, range(hilos)))
    duracion = time.perf_counter() - arranque
    return round(hilos * por_hilo / duracion, 1) if duracion else 0.0


def medir_concurrencia(cliente, *, hilos: int, por_hilo: int = 10) -> Concurrencia:
    """Golpea la API desde varios hilos a la vez y mide qué pasa.

    Cada petición toma su propia conexión del pool, así que la contención de
    conexiones y la del motor son reales. Lo que sigue sin ser real es la red y
    el despliegue: esto corre en proceso y contra la misma base.
    """
    resultado = Concurrencia(hilos=hilos)
    tiempos: list[float] = []

    def una_ronda() -> list[tuple[float, int]]:
        medidos: list[tuple[float, int]] = []
        for indice in range(por_hilo):
            nombre, ruta, params = CONSULTAS[indice % len(CONSULTAS)]
            del nombre
            arranque = time.perf_counter()
            respuesta = cliente.get(ruta, params=params)
            medidos.append(((time.perf_counter() - arranque) * 1000, respuesta.status_code))
        return medidos

    arranque = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=hilos) as pool:
        for medidos in pool.map(lambda _: una_ronda(), range(hilos)):
            for demora, estado in medidos:
                tiempos.append(demora)
                resultado.errores += int(not 200 <= estado < 300)
    resultado.duracion_s = round(time.perf_counter() - arranque, 3)
    resultado.consultas = len(tiempos)
    if tiempos:
        resultado.p50_ms = round(statistics.median(tiempos), 2)
        resultado.p95_ms = _percentil(tiempos, 0.95)
        resultado.max_ms = round(max(tiempos), 2)
    return resultado


def _cuantas(cuerpo: dict) -> int | None:
    datos = cuerpo.get("data")
    if isinstance(datos, list):
        return len(datos)
    if isinstance(datos, dict) and isinstance(datos.get("items"), list):
        return len(datos["items"])
    return None


def formatear(reporte: ReporteRendimiento) -> str:
    lineas = [
        "# Rendimiento de las consultas sobre el corpus real",
        "",
        "Una latencia sin decir sobre cuántas filas se midió no significa nada, así que el",
        "tamaño del corpus va primero.",
        "",
        f"- Tamaño de la base: **{reporte.tamano_base}**",
        f"- Repeticiones por consulta: **{reporte.repeticiones}**",
        "",
        "| Tabla | Filas |",
        "| --- | ---: |",
    ]
    lineas += [f"| `{tabla}` | {cuantas:,} |" for tabla, cuantas in reporte.corpus.items()]
    lineas += [
        "",
        "## Latencias",
        "",
        "| Consulta | Ruta | Filas | 1ª (ms) | p50 (ms) | p95 (ms) | máx (ms) | HTTP |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in reporte.mediciones:
        lineas.append(
            f"| {m.nombre} | `{m.ruta}` | {m.filas if m.filas is not None else '—'} "
            f"| {m.primera_ms} | {m.p50_ms} | {m.p95_ms} | {m.max_ms} | {m.estado} |"
        )

    if reporte.concurrencia:
        lineas += [
            "",
            "## Con varias consultas a la vez",
            "",
            "Cada petición toma su propia conexión del pool, así que la contención de",
            "conexiones y la del motor son reales.",
            "",
            "| Hilos | Consultas | Duración (s) | Consultas/s | p50 (ms) | p95 (ms) | máx (ms) "
            "| Errores |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for c in reporte.concurrencia:
            lineas.append(
                f"| {c.hilos} | {c.consultas} | {c.duracion_s} | {c.por_segundo} | {c.p50_ms} "
                f"| {c.p95_ms} | {c.max_ms} | {c.errores} |"
            )

    peor = reporte.peor
    lineas += [
        "",
        "## Qué dicen y qué no dicen estos números",
        "",
        "La primera repetición se informa aparte porque es la única que se parece a un",
        "servidor recién arrancado: las siguientes encuentran la caché del motor caliente.",
        "",
    ]
    if peor is not None:
        lineas.append(
            f"La consulta más lenta es «{peor.nombre}» con {peor.p95_ms} ms en el percentil 95."
        )
    lineas += [
        "",
        "**Esto sigue sin ser una prueba de carga de producción.** Corre en proceso, sin red,",
        "sin balanceador y contra una sola instancia. El número de consultas por segundo es un",
        "techo optimista, no una capacidad comprometida.",
    ]
    if reporte.motor_por_segundo:
        techo = max((c.por_segundo for c in reporte.concurrencia), default=0.0)
        lineas += [
            "",
            "### Dónde está el techo",
            "",
            f"Con la misma concurrencia, el motor sostiene **{reporte.motor_por_segundo} "
            f"consultas por segundo** y la API se queda en **{techo}**. La diferencia dice "
            "dónde está el límite: no en la base ni en las conexiones, sino en el proceso que "
            "arma y serializa cada respuesta.",
            "",
            "Es un dato que cambia qué hacer para escalar. Agrandar el pool o agregar índices "
            "no mueve este número; agregar procesos sí. Medirlo antes de optimizar evita "
            "gastar el trabajo en el lado que no era.",
        ]
    if reporte.fallidas:
        lineas += [
            "",
            "### Consultas que no respondieron",
            "",
        ]
        lineas += [f"- {m.nombre} (`{m.ruta}`): HTTP {m.estado}" for m in reporte.fallidas]
    return "\n".join(lineas)
