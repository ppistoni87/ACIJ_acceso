"""HU-037: si el caudal se multiplica al agregar procesos, o si el cuello está abajo.

La medición anterior golpeaba la API desde hilos dentro del mismo proceso de
prueba. Eso dice dónde está el techo de un proceso y no si ese techo se
multiplica, que es la pregunta que hay que contestar antes de decidir cómo se
despliega esto.

Acá se contesta con lo que se puede tener en una máquina: la API corre en varios
procesos de verdad, que comparten un socket de escucha —el reparto lo hace el
núcleo, que es un balanceador real aunque no sea el del despliegue—, y la carga
la genera otro proceso, no el mismo que sirve. La base es la misma PostgreSQL de
siempre, con su pool y su contención reales.

Lo que esto no prueba, y hay que decirlo cada vez: la red es loopback y las
instancias comparten CPU, memoria y disco. En un despliegue real las instancias
están en máquinas distintas y el balanceador es un proceso más en el camino. Lo
que sí prueba es lo otro: si al pasar de uno a cuatro procesos el caudal no
sube, no hace falta buscar la respuesta en la red, porque el cuello ya está en
la base o en el propio trabajo de cada petición.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field

from sqlalchemy import text as sql_text

CONSULTAS: tuple[tuple[str, dict], ...] = (
    ("/v1/normas", {"limite": "20"}),
    ("/v1/normas", {"q": "asignación familiar", "limite": "20"}),
    ("/v1/beneficios", {}),
    ("/v1/puntos-atencion", {}),
    ("/v1/cobertura", {}),
)

ESPERA_ARRANQUE_S = 30.0


@dataclass
class Medida:
    procesos: int
    clientes: int
    peticiones: int = 0
    errores: int = 0
    duracion_s: float = 0.0
    p95_ms: float = 0.0
    cpu_ocupada: float = 0.0
    """Porcentaje de CPU ocupada en la máquina durante la medición."""

    @property
    def por_segundo(self) -> float:
        return round(self.peticiones / self.duracion_s, 1) if self.duracion_s else 0.0


@dataclass
class Pool:
    """Cuántas conexiones puede abrir el despliegue y cuántas admite la base."""

    por_proceso: int = 0
    max_connections: int = 0

    def alcanzan(self, procesos: int) -> bool:
        return self.por_proceso * procesos <= self.max_connections


@dataclass
class ReporteEscalado:
    medidas: list[Medida] = field(default_factory=list)
    barrido: list[Medida] = field(default_factory=list)
    cpus: int = 0
    pool: Pool = field(default_factory=Pool)
    avisos: list[str] = field(default_factory=list)

    def por_procesos(self, procesos: int) -> Medida | None:
        for medida in self.medidas:
            if medida.procesos == procesos:
                return medida
        return None


def _cpu() -> tuple[int, int]:
    """Tics ocupados y totales de la máquina, de `/proc/stat`.

    Distinguir «llegó al techo del procesador» de «llegó al techo de la base» no
    se puede hacer con el caudal solo: los dos se ven igual desde afuera, y la
    respuesta a cada uno es distinta —más CPU en un caso, otra base o mejores
    consultas en el otro—.
    """
    with open("/proc/stat", encoding="utf-8") as archivo:
        campos = [int(x) for x in archivo.readline().split()[1:]]
    total = sum(campos)
    inactivo = campos[3] + (campos[4] if len(campos) > 4 else 0)
    return total - inactivo, total


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar(puerto: int, proceso: subprocess.Popen) -> bool:
    limite = time.monotonic() + ESPERA_ARRANQUE_S
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", puerto), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _generar_carga(puerto: int, clientes: int, segundos: float) -> Medida:
    """La carga la produce otro proceso, no el que sirve.

    Medir desde adentro del servidor mide el servidor midiéndose a sí mismo: el
    cliente y la API se pelean por el mismo intérprete y el número que sale no
    es el caudal, es el reparto.
    """
    guion = os.path.join(os.path.dirname(__file__), "_carga.py")
    ocupada_antes, total_antes = _cpu()
    salida = subprocess.run(
        [sys.executable, guion, str(puerto), str(clientes), str(segundos)],
        capture_output=True,
        text=True,
        check=False,
        timeout=segundos + 120,
    )
    if salida.returncode != 0:
        raise RuntimeError(f"El generador de carga falló: {salida.stderr[-500:]}")
    ocupada_despues, total_despues = _cpu()
    transcurridos = total_despues - total_antes
    cpu = 100.0 * (ocupada_despues - ocupada_antes) / transcurridos if transcurridos else 0.0
    datos = json.loads(salida.stdout.strip().splitlines()[-1])
    return Medida(
        procesos=0,
        clientes=clientes,
        peticiones=datos["peticiones"],
        errores=datos["errores"],
        duracion_s=datos["duracion_s"],
        p95_ms=datos["p95_ms"],
        cpu_ocupada=round(cpu, 1),
    )


def _pool(conexion) -> Pool:
    """El techo de conexiones, que es distinto del techo de caudal.

    Sin este número, un caudal que deja de subir se lee como «llegó al límite
    del hardware» cuando puede ser otra cosa: que el despliegue esté pidiendo
    más conexiones de las que la base admite, y las que sobran se caigan.
    """
    from backend_normativo.config import get_settings

    ajustes = get_settings()
    maximo = conexion.execute(sql_text("SHOW max_connections")).scalar_one()
    return Pool(
        por_proceso=int(ajustes.pool_size) + int(ajustes.pool_max_overflow),
        max_connections=int(maximo),
    )


def medir(
    *,
    procesos: tuple[int, ...] = (1, 2, 4),
    clientes: int = 16,
    segundos: float = 6.0,
    barrido_clientes: tuple[int, ...] = (),
    conexion=None,
) -> ReporteEscalado:
    """Levanta la API con N procesos y le tira carga desde afuera, para cada N.

    `barrido_clientes` repite la medición con el mayor número de procesos y
    distinta concurrencia de clientes. Sirve para dos cosas y las dos hacen
    falta: descartar que el techo lo esté poniendo el generador de carga —si al
    agregar clientes el caudal sube, el que estaba saturado era el cliente— y
    ver qué hace el sistema cuando lo empujan más allá de donde aguanta.
    """
    reporte = ReporteEscalado(cpus=os.cpu_count() or 0)
    if conexion is not None:
        reporte.pool = _pool(conexion)
    for cuantos in procesos:
        puerto = _puerto_libre()
        servidor = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend_normativo.api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto),
                "--workers",
                str(cuantos),
                "--log-level",
                "error",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            if not _esperar(puerto, servidor):
                error = (servidor.stderr.read() or b"").decode()[-400:] if servidor.stderr else ""
                raise RuntimeError(f"La API con {cuantos} proceso(s) no levantó. {error}")
            # Una vuelta corta para que cada proceso abra su conexión antes de
            # medir: el costo de abrir el pool no es el costo de servir.
            _generar_carga(puerto, clientes, 1.0)
            medida = _generar_carga(puerto, clientes, segundos)
            medida.procesos = cuantos
            reporte.medidas.append(medida)
            if barrido_clientes and cuantos == max(procesos):
                for cuantos_clientes in barrido_clientes:
                    otra = _generar_carga(puerto, cuantos_clientes, segundos)
                    otra.procesos = cuantos
                    reporte.barrido.append(otra)
        finally:
            os.killpg(os.getpgid(servidor.pid), signal.SIGTERM)
            try:
                servidor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(servidor.pid), signal.SIGKILL)

    _revisar(reporte)
    return reporte


def _revisar(reporte: ReporteEscalado) -> None:
    """Lo que el número quiere decir, dicho por el que lo midió.

    Un caudal que no sube al agregar procesos no significa lo mismo según dónde
    esté el límite, y las dos lecturas se ven idénticas desde afuera. Si la
    máquina ya estaba con la CPU llena, no sube porque no queda máquina, y esta
    medición no puede decir si escalaría en otra; si sobra CPU y aun así no
    sube, el límite está abajo del proceso y más instancias no lo van a mover.
    Dejar esa diferencia librada a quien lea el reporte sería dejar la
    conclusión abierta justo donde importa.
    """
    uno = reporte.por_procesos(1)
    if uno is None or not uno.peticiones:
        reporte.avisos.append("No hay medición con un proceso: no hay contra qué comparar.")
        return

    tope = max(reporte.medidas + reporte.barrido, key=lambda m: m.por_segundo)
    cpu_llena = tope.cpu_ocupada >= 85
    reporte.avisos.append(
        f"El caudal máximo medido es {tope.por_segundo} peticiones por segundo, con "
        f"{tope.procesos} proceso(s) y {tope.clientes} clientes, y ahí la máquina usa el "
        f"{tope.cpu_ocupada}% de su CPU."
    )

    for medida in reporte.medidas:
        if medida.procesos == 1:
            continue
        factor = medida.por_segundo / uno.por_segundo if uno.por_segundo else 0.0
        if factor >= medida.procesos * 0.7:
            reporte.avisos.append(
                f"Con {medida.procesos} procesos el caudal se multiplica por {factor:.2f}: "
                "escala agregando procesos."
            )
        elif cpu_llena:
            reporte.avisos.append(
                f"Con {medida.procesos} procesos el caudal se multiplica por {factor:.2f} y no "
                f"por {medida.procesos}, y con {uno.cpu_ocupada}% de CPU ya ocupada por un solo "
                "proceso. No queda máquina para repartir: acá la API, la base y el generador de "
                "carga comparten los mismos núcleos, así que esto **no** dice que el sistema no "
                "escale. Dice que esta máquina no tiene con qué mostrarlo, y que la pregunta "
                "sigue necesitando instancias en máquinas separadas."
            )
        else:
            reporte.avisos.append(
                f"Con {medida.procesos} procesos el caudal se multiplica por {factor:.2f} y no "
                f"por {medida.procesos}, con la CPU al {medida.cpu_ocupada}%: sobra procesador y "
                "aun así no sube, así que el límite está abajo del proceso —la base, el disco o "
                "el trabajo de cada consulta—. Ahí agregar instancias no alcanza."
            )

    if reporte.barrido:
        mejor = max(reporte.barrido, key=lambda m: m.por_segundo)
        base = reporte.por_procesos(max(m.procesos for m in reporte.medidas))
        if base and mejor.por_segundo > base.por_segundo * 1.2:
            reporte.avisos.append(
                f"Con {mejor.clientes} clientes el caudal sube a {mejor.por_segundo} pet/s: la "
                "medición base estaba limitada por el generador de carga, no por la API."
            )
        else:
            reporte.avisos.append(
                "Subir la concurrencia de clientes no sube el caudal y sí la demora "
                f"({', '.join(f'{m.clientes} clientes → {m.p95_ms} ms' for m in reporte.barrido)}"
                "): el sistema está saturado y encola en vez de rechazar. Una petición que "
                "expira consume igual y no devuelve nada, así que un despliegue tiene que poner "
                "el límite antes."
            )
        con_errores = [m for m in reporte.barrido if m.errores]
        if con_errores:
            primero = min(con_errores, key=lambda m: m.clientes)
            reporte.avisos.append(
                f"A partir de {primero.clientes} clientes concurrentes aparecen errores "
                f"({primero.errores}): el techo deja de ser un techo y pasa a ser un derrumbe."
            )

    if any(m.errores for m in reporte.medidas):
        reporte.avisos.append(
            "Hubo peticiones con error: un caudal alto con errores no es caudal, es rechazo rápido."
        )
    pool = reporte.pool
    if pool.por_proceso and reporte.medidas:
        mayor = max(m.procesos for m in reporte.medidas)
        if not pool.alcanzan(mayor):
            reporte.avisos.append(
                f"Cada proceso puede abrir hasta {pool.por_proceso} conexiones y la base admite "
                f"{pool.max_connections} en total: con {mayor} procesos el despliegue puede "
                f"pedir {pool.por_proceso * mayor}, que es más de lo que hay. Bajo carga las que "
                "sobran no esperan: la base las rechaza y la petición se cae. Es una cuenta que "
                "hay que hacer antes de agregar instancias, no después."
            )


def formatear(reporte: ReporteEscalado) -> str:
    lineas = [
        "# Escalado por procesos: ¿el caudal se multiplica?",
        "",
        "La medición anterior golpeaba la API desde hilos dentro del mismo proceso de",
        "prueba. Eso dice dónde está el techo de un proceso y no si ese techo se",
        "multiplica, que es lo que hay que saber antes de decidir cómo se despliega.",
        "",
        "Acá la API corre en varios procesos de verdad, que comparten el socket de",
        "escucha —el reparto lo hace el núcleo—, y la carga la genera otro proceso. La",
        "base es la misma PostgreSQL, con su pool y su contención reales.",
        "",
        f"Generado por `bn calidad escalado` sobre una máquina de **{reporte.cpus} CPU**.",
        (
            f"Pool por proceso: **{reporte.pool.por_proceso}** conexiones · "
            f"máximo de la base: **{reporte.pool.max_connections}**."
            if reporte.pool.por_proceso
            else ""
        ),
        "",
        "| Procesos | Clientes | Peticiones | Errores | Caudal (pet/s) | p95 | CPU |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for medida in reporte.medidas:
        lineas.append(
            f"| {medida.procesos} | {medida.clientes} | {medida.peticiones} | {medida.errores} "
            f"| **{medida.por_segundo}** | {medida.p95_ms} ms | {medida.cpu_ocupada}% |"
        )
    if reporte.barrido:
        mayor = max(m.procesos for m in reporte.medidas)
        lineas += [
            "",
            f"## Hasta dónde aguanta, con {mayor} procesos",
            "",
            "Se repite la medición subiendo la concurrencia de clientes. Si el caudal sube al",
            "agregar clientes, el que estaba saturado era el generador de carga y no la API.",
            "Si deja de subir y la demora crece, la API está en su techo. Si además aparecen",
            "errores, el techo no es un techo: es un derrumbe.",
            "",
            "| Clientes | Peticiones | Errores | Caudal (pet/s) | p95 | CPU |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for medida in reporte.barrido:
            lineas.append(
                f"| {medida.clientes} | {medida.peticiones} | {medida.errores} "
                f"| **{medida.por_segundo}** | {medida.p95_ms} ms | {medida.cpu_ocupada}% |"
            )
    lineas += ["", "## Qué dice", ""]
    lineas += [f"- {aviso}" for aviso in reporte.avisos]
    lineas += [
        "",
        "## Qué no dice",
        "",
        "La red es loopback y todo comparte la misma máquina: la API, PostgreSQL y el",
        "generador de carga se pelean por los mismos núcleos. Cuando la CPU llega al",
        "tope, esta medición deja de poder distinguir el costo de la API del de la base",
        "del generador, y ahí la pregunta de si el caudal se multiplica al agregar",
        "instancias solo la contesta un despliegue con máquinas separadas.",
        "",
        "Lo que sí queda medido, y no dependía de eso, es todo lo demás: dónde está el",
        "techo de esta máquina, qué le pasa al sistema cuando lo empujan más allá —encola",
        "y la demora crece, en vez de rechazar—, y que el pool de cada proceso por la",
        "cantidad de procesos puede pedirle a la base más conexiones de las que admite,",
        "que es una cuenta que hay que hacer antes de agregar instancias y no después.",
    ]
    return "\n".join(lineas) + "\n"
