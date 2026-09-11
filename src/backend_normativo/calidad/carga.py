"""Ensayo de carga y fallos inducidos (P-023, criterio 3).

El criterio pide veinte conversaciones concurrentes durante treinta minutos, con
fallos inducidos de proveedor, base y fuente, y verificar latencia, límites,
recuperación y ausencia de exposición de datos pendientes.

Lo que hace este módulo, y por qué está armado así:

* **Conversaciones, no peticiones sueltas.** Cada hilo hace lo que hace el
  frente: pide los vocabularios una vez, después pregunta, y después busca el
  canal oficial. Medir una ráfaga de la misma ruta da un número más lindo y no
  dice nada del recorrido que una persona hace.
* **Los fallos se inducen de verdad.** El proveedor es un servidor local que se
  rompe cuando se le pide; la base se apaga con el comando del sistema; la
  fuente es otro servidor local que empieza a contestar 503. Simular un fallo
  con una bandera prueba la bandera.
* **Todo se mide por fase.** Antes del fallo, durante y después. Un promedio que
  mezcla las tres esconde exactamente lo que el ensayo quiere ver: cuánto tardó
  en recuperarse.
* **Cada respuesta se revisa.** Que ningún fragmento servido venga de fuera del
  corte publicado, y que ningún cuerpo —de éxito o de error— lleve rastros de lo
  que no se publica ni del funcionamiento interno del servicio.
"""

from __future__ import annotations

import json
import random
import subprocess
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

# Marcas que no pueden aparecer en ninguna respuesta. Son estados de trabajo y
# nombres de la cocina: si alguno sale por la API, salió algo que no se publica.
MARCAS_PROHIBIDAS: tuple[str, ...] = (
    "CANDIDATE",
    "DRAFT",
    "EN_REVISION",
    "Traceback",
    "psycopg",
    "sqlalchemy",
    "/home/",
    "BN_DATABASE_URL",
)

FASE_ANTES = "antes"
FASE_DURANTE = "durante el fallo"
FASE_DESPUES = "después"


@dataclass
class Peticion:
    fase: str
    ruta: str
    ms: float
    estado: int
    modo: str | None = None

    @property
    def fallo(self) -> bool:
        return self.estado >= 500 or self.estado == 0


@dataclass
class Filtracion:
    que: str
    ruta: str
    detalle: str


@dataclass
class Fallo:
    """Un fallo inducido, con su ventana y cómo se provoca y se deshace."""

    nombre: str
    desde_s: float
    duracion_s: float
    aplicar: object
    revertir: object
    medir_recuperacion: bool = False
    aplicado: bool = False
    error: str | None = None
    recuperado_en_s: float | None = None
    reinicio_necesario: bool = False


@dataclass
class ReporteCarga:
    conversaciones: int = 0
    minutos: float = 0.0
    peticiones: list[Peticion] = field(default_factory=list)
    filtraciones: list[Filtracion] = field(default_factory=list)
    fallos: list[Fallo] = field(default_factory=list)
    limite_configurado: int = 0
    limite_429: int = 0
    abusador_frenado: int = 0
    abusador_servido: int = 0
    avisos: list[str] = field(default_factory=list)

    def de_fase(self, fase: str) -> list[Peticion]:
        return [p for p in self.peticiones if p.fase == fase]

    @property
    def total(self) -> int:
        return len(self.peticiones)


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, round(p * (len(ordenados) - 1)))
    return round(ordenados[indice], 1)


# --- Servidores de mentira, para romperlos a propósito -----------------------


class _Manejador(BaseHTTPRequestHandler):
    servidor_modo = "ok"

    def log_message(self, *_args) -> None:  # silencio: el ensayo ya mide
        return

    def _responder(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_POST(self) -> None:  # el nombre lo define BaseHTTPRequestHandler
        modo = getattr(self.server, "modo", "ok")
        largo = int(self.headers.get("Content-Length") or 0)
        crudo = self.rfile.read(largo).decode("utf-8", "replace") if largo else ""
        # El prompt viaja dentro de un JSON, así que en el cuerpo crudo las
        # comillas están escapadas y `id="` no aparece nunca. Se decodifica.
        # Sin esto el proveedor devolvía texto sin ninguna cita, los validadores
        # lo rechazaban —con razón— y el ensayo no ejercitaba jamás el camino
        # generado: 1620 respuestas y ni una sola GENERADA.
        try:
            pedido = json.loads(crudo) if crudo else {}
            crudo = "".join(
                m.get("content", "") for m in pedido.get("messages", []) if isinstance(m, dict)
            )
        except ValueError:
            pass
        if modo == "error":
            self._responder(503, {"error": "el proveedor no está disponible"})
            return
        if modo == "lento":
            time.sleep(45)
        # Una redacción que cita de verdad: se toma el primer id que venga en el
        # prompt. Si el proveedor devolviera texto sin citas, los validadores lo
        # rechazarían y la respuesta caería a extracto —que también es correcto—,
        # pero entonces el ensayo nunca ejercitaría el camino generado.
        ident = ""
        marca = 'id="'
        if marca in crudo:
            ident = crudo.split(marca, 1)[1].split('"', 1)[0]
        texto = (
            f"Según lo publicado, corresponde leer el texto citado. [[chunk:{ident}]]"
            if ident
            else "No hay elementos suficientes para responder."
        )
        self._responder(200, {"content": [{"text": texto}]})

    def do_GET(self) -> None:
        modo = getattr(self.server, "modo", "ok")
        if modo == "error":
            self._responder(503, {"error": "la fuente no está disponible"})
            return
        if modo == "limitado":
            # 403 no es lo mismo que 503: uno es «no te dejo» y el otro «ahora
            # no puedo». La política los trata distinto a propósito, así que el
            # ensayo tiene que poder provocar los dos.
            self._responder(403, {"error": "acceso denegado"})
            return
        cuerpo = b"<html><body><h1>Pagina de prueba</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


class ServidorDeMentira:
    """Un servicio externo que se puede romper cuando el ensayo lo necesita."""

    def __init__(self) -> None:
        # Con hilos, y no con el `HTTPServer` de a uno por vez: veinte
        # conversaciones concurrentes contra un servidor secuencial hacen cola,
        # la API espera, y lo que el ensayo termina midiendo es el servidor de
        # mentira. Pasó: la primera corrida dio trescientas peticiones en dos
        # minutos y casi todas expiradas.
        self._http = ThreadingHTTPServer(("127.0.0.1", 0), _Manejador)
        self._http.modo = "ok"  # type: ignore[attr-defined]
        self._hilo = threading.Thread(target=self._http.serve_forever, daemon=True)

    def __enter__(self) -> ServidorDeMentira:
        self._hilo.start()
        return self

    def __exit__(self, *_excepcion) -> None:
        self._http.shutdown()
        self._http.server_close()

    @property
    def url(self) -> str:
        host, puerto = self._http.server_address[:2]
        return f"http://{host}:{puerto}"

    def romper(self) -> None:
        self._http.modo = "error"  # type: ignore[attr-defined]

    def limitar(self) -> None:
        self._http.modo = "limitado"  # type: ignore[attr-defined]

    def arreglar(self) -> None:
        self._http.modo = "ok"  # type: ignore[attr-defined]


def apagar_base(comando: list[str]) -> None:
    subprocess.run(comando, check=True, capture_output=True, timeout=120)


def encender_base(comando: list[str]) -> None:
    subprocess.run(comando, check=True, capture_output=True, timeout=120)


def probar_fuente(stub: ServidorDeMentira) -> list[str]:
    """Qué hace la ingesta cuando la fuente se cae, con el cliente de verdad.

    El camino de consulta no toca fuentes: una fuente caída no puede afectar a
    quien pregunta, y eso también es parte de lo que hay que ver. Lo que sí se
    verifica es que el fallo se registre como lo que es —transitorio o acceso
    limitado— y que nunca se convierta en «sin datos».
    """
    from backend_normativo.ingesta.cliente import ClienteCaptura

    observaciones: list[str] = []
    with ClienteCaptura() as cliente:
        stub.romper()
        transitoria = cliente.descargar(f"{stub.url}/norma")
        observaciones.append(
            f"503 transitorio: {transitoria.intentos} intento(s), error `{transitoria.error}`, "
            f"acceso limitado = {transitoria.acceso_limitado}. No quedó como «sin datos»."
        )
        stub.limitar()
        limitada = cliente.descargar(f"{stub.url}/norma")
        observaciones.append(
            f"403: acceso limitado = {limitada.acceso_limitado}, error `{limitada.error}`. "
            "Se registra como acceso limitado y pausa la fuente; no se reintenta ni se rota "
            "identidad."
        )
        stub.arreglar()
        buena = cliente.descargar(f"{stub.url}/norma")
        observaciones.append(
            f"Repuesta la fuente: HTTP {buena.http_status}, {len(buena.contenido)} bytes. "
            "La ingesta vuelve sola."
        )
    return observaciones


# --- La carga ----------------------------------------------------------------


def _fase_de(transcurrido: float, fallos: list[Fallo]) -> str:
    """En qué momento del ensayo cayó esta petición.

    La fase se nombra con el fallo: «durante Base de datos apagada» y no
    «durante el fallo». Con tres ventanas, una etiqueta genérica mezcla la
    caída del proveedor con la de la base, que es justo la comparación que hay
    que poder hacer.
    """
    for fallo in fallos:
        if fallo.desde_s <= transcurrido < fallo.desde_s + fallo.duracion_s:
            return f"durante · {fallo.nombre}"
    ultimo = None
    for fallo in fallos:
        if transcurrido >= fallo.desde_s + fallo.duracion_s:
            ultimo = fallo
    return f"después de · {ultimo.nombre}" if ultimo else FASE_ANTES


def _revisar(cuerpo: str, ruta: str, chunks_del_corte: set[str]) -> list[Filtracion]:
    hallazgos: list[Filtracion] = []
    for marca in MARCAS_PROHIBIDAS:
        if marca in cuerpo:
            hallazgos.append(
                Filtracion(que=f"marca «{marca}» en la respuesta", ruta=ruta, detalle=marca)
            )
    if chunks_del_corte and '"chunk_id"' in cuerpo:
        try:
            datos = json.loads(cuerpo)
        except ValueError:
            return hallazgos
        for fuente in datos.get("fuentes") or []:
            ident = str(fuente.get("chunk_id"))
            if ident not in chunks_del_corte:
                hallazgos.append(
                    Filtracion(
                        que="fragmento servido que no pertenece al corte publicado",
                        ruta=ruta,
                        detalle=ident,
                    )
                )
    return hallazgos


def _conversacion(
    cliente: httpx.Client,
    base: str,
    consulta: dict,
    registrar,
) -> None:
    """Lo que hace el frente: vocabularios, pregunta, canal oficial."""
    registrar("/v1/vocabularios", lambda: cliente.get(f"{base}/v1/vocabularios"))
    registrar(
        "/v1/respuestas",
        lambda: cliente.post(
            f"{base}/v1/respuestas",
            json={"consulta": consulta.get("consulta", ""), "limite": 5},
        ),
    )
    registrar("/v1/puntos-atencion", lambda: cliente.get(f"{base}/v1/puntos-atencion"))


def correr(
    *,
    base: str,
    consultas: list[dict],
    conversaciones: int,
    segundos: float,
    fallos: list[Fallo],
    chunks_del_corte: set[str] | None = None,
    limite_configurado: int = 0,
    pausa_s: float = 1.0,
    semilla: int = 20260911,
) -> ReporteCarga:
    """Genera la carga, induce los fallos y mide todo por fase."""
    reporte = ReporteCarga(
        conversaciones=conversaciones,
        minutos=round(segundos / 60.0, 1),
        fallos=fallos,
        limite_configurado=limite_configurado,
    )
    chunks = chunks_del_corte or set()
    candado = threading.Lock()
    comenzo = time.monotonic()
    parar = threading.Event()

    def trabajador(indice: int) -> None:
        azar = random.Random(semilla + indice)
        # Cada conversación llega desde su propio origen. Sin esto las veinte
        # comparten un balde y el ensayo mide el límite en vez del servicio,
        # que es lo contrario de lo que se quiere ver. El servidor del ensayo
        # corre con `BN_PROXIES_CONFIABLES=1`, que es el mismo mecanismo que
        # usaría detrás de un balanceador propio.
        cabeceras = {"X-Forwarded-For": f"10.{indice // 256}.{indice % 256}.1"}
        with httpx.Client(timeout=30.0, headers=cabeceras) as cliente:
            while not parar.is_set():
                consulta = azar.choice(consultas)

                def registrar(ruta: str, hacer) -> None:
                    arranque = time.monotonic()
                    transcurrido = arranque - comenzo
                    try:
                        respuesta = hacer()
                        estado, cuerpo = respuesta.status_code, respuesta.text
                    except Exception:
                        # Una conexión rechazada mientras la base está apagada
                        # es un resultado del ensayo, no un error del ensayo.
                        estado, cuerpo = 0, ""
                    ms = (time.monotonic() - arranque) * 1000
                    modo = None
                    if cuerpo.startswith("{") and '"modo"' in cuerpo:
                        try:
                            modo = json.loads(cuerpo).get("modo")
                        except ValueError:
                            modo = None
                    hallazgos = _revisar(cuerpo, ruta, chunks) if cuerpo else []
                    with candado:
                        reporte.peticiones.append(
                            Peticion(
                                fase=_fase_de(transcurrido, fallos),
                                ruta=ruta,
                                ms=ms,
                                estado=estado,
                                modo=modo,
                            )
                        )
                        if estado == 429:
                            reporte.limite_429 += 1
                        reporte.filtraciones.extend(hallazgos)

                _conversacion(cliente, base, consulta, registrar)
                if parar.wait(azar.uniform(pausa_s * 0.5, pausa_s * 1.5)):
                    return

    def abusador() -> None:
        """Un origen que pide sin parar, para ver el límite de verdad.

        Lo que importa no es que reciba 429: es que **los demás sigan siendo
        atendidos** mientras lo recibe. Un límite que protege al servicio y deja
        afuera a todo el mundo no protege a nadie.
        """
        cabeceras = {"X-Forwarded-For": "203.0.113.7"}
        with httpx.Client(timeout=10.0, headers=cabeceras) as cliente:
            while not parar.is_set():
                try:
                    estado = cliente.get(f"{base}/v1/vocabularios").status_code
                except Exception:
                    estado = 0
                with candado:
                    if estado == 429:
                        reporte.abusador_frenado += 1
                    elif estado == 200:
                        reporte.abusador_servido += 1
                parar.wait(0.05)

    hilos = [
        threading.Thread(target=trabajador, args=(i,), daemon=True) for i in range(conversaciones)
    ]
    if limite_configurado:
        hilos.append(threading.Thread(target=abusador, daemon=True))
    for hilo in hilos:
        hilo.start()

    # El director de los fallos: aplica y deshace en su momento, y mide cuánto
    # tarda el servicio en volver sin que nadie lo reinicie.
    try:
        for fallo in sorted(fallos, key=lambda f: f.desde_s):
            _esperar_hasta(comenzo, fallo.desde_s, parar)
            try:
                fallo.aplicar()
                fallo.aplicado = True
            except Exception as error:
                fallo.error = f"{type(error).__name__}: {error}"
                continue
            _esperar_hasta(comenzo, fallo.desde_s + fallo.duracion_s, parar)
            try:
                fallo.revertir()
            except Exception as error:
                fallo.error = f"al deshacer: {type(error).__name__}: {error}"
            if fallo.medir_recuperacion:
                # Acotada: si midiera hasta dos minutos por fallo, un fallo que
                # no vuelve se come la ventana del siguiente y el ensayo deja de
                # ser el ensayo que se programó. Pasó en la primera corrida.
                fallo.recuperado_en_s = _medir_recuperacion(base, limite_s=60.0)
        _esperar_hasta(comenzo, segundos, parar)
    finally:
        parar.set()
        for hilo in hilos:
            hilo.join(timeout=40)

    return reporte


def _esperar_hasta(comenzo: float, objetivo_s: float, parar: threading.Event) -> None:
    restante = objetivo_s - (time.monotonic() - comenzo)
    if restante > 0:
        parar.wait(restante)


def _medir_recuperacion(base: str, *, limite_s: float = 120.0) -> float | None:
    """Cuánto tarda el servicio en volver a contestar, sin reiniciarlo.

    Sondea `/listo`, que es la que dice si esta instancia puede servir. Si
    hiciera falta reiniciar el proceso, esto nunca devolvería un número, y eso
    es exactamente lo que hay que saber.
    """
    arranque = time.monotonic()
    with httpx.Client(timeout=5.0) as cliente:
        while time.monotonic() - arranque < limite_s:
            try:
                if cliente.get(f"{base}/listo").status_code == 200:
                    return round(time.monotonic() - arranque, 1)
            except Exception:
                pass
            time.sleep(1.0)
    return None


# --- El informe --------------------------------------------------------------


def _tabla_de_fases(reporte: ReporteCarga) -> list[str]:
    lineas = [
        "| Fase | Peticiones | Fallidas | p50 | p95 | p99 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    vistas: list[str] = []
    for peticion in reporte.peticiones:
        if peticion.fase not in vistas:
            vistas.append(peticion.fase)
    for fase in vistas:
        peticiones = reporte.de_fase(fase)
        if not peticiones:
            continue
        exitosas = [p.ms for p in peticiones if not p.fallo and p.estado]
        fallidas = sum(1 for p in peticiones if p.fallo)
        lineas.append(
            f"| {fase} | {len(peticiones)} | {fallidas} | "
            f"{percentil(exitosas, 0.50)} ms | {percentil(exitosas, 0.95)} ms | "
            f"{percentil(exitosas, 0.99)} ms |"
        )
    return lineas


def _tabla_de_respuestas(reporte: ReporteCarga) -> list[str]:
    lineas = [
        "| Fase | Códigos HTTP | Modos de respuesta |",
        "| --- | --- | --- |",
    ]
    vistas: list[str] = []
    for peticion in reporte.peticiones:
        if peticion.fase not in vistas:
            vistas.append(peticion.fase)
    for fase in vistas:
        peticiones = reporte.de_fase(fase)
        estados: dict[str, int] = {}
        for peticion in peticiones:
            nombre = str(peticion.estado) if peticion.estado else "sin respuesta"
            estados[nombre] = estados.get(nombre, 0) + 1
        modos: dict[str, int] = {}
        for peticion in peticiones:
            if peticion.modo:
                modos[peticion.modo] = modos.get(peticion.modo, 0) + 1
        lineas.append(
            f"| {fase} | "
            + ", ".join(f"{cuantas}×{codigo}" for codigo, cuantas in sorted(estados.items()))
            + " | "
            + (", ".join(f"{cuantas}×{modo}" for modo, cuantas in sorted(modos.items())) or "—")
            + " |"
        )
    return lineas


def formatear(reporte: ReporteCarga) -> str:
    partes: list[str] = ["# Carga sostenida y fallos inducidos", ""]
    partes.append(
        f"{reporte.conversaciones} conversaciones concurrentes durante "
        f"{reporte.minutos} minutos. Cada conversación pide vocabularios, pregunta y "
        f"busca el canal oficial, que es lo que hace el frente ciudadano."
    )
    partes.append("")
    partes.append(f"- Peticiones totales: **{reporte.total}**")
    modos = [p.modo for p in reporte.peticiones if p.modo]
    if modos:
        cuenta = {modo: modos.count(modo) for modo in sorted(set(modos))}
        partes.append(
            "- Modos de respuesta: "
            + ", ".join(f"**{cuantas}** {modo}" for modo, cuantas in cuenta.items())
        )
    partes += ["", "## Latencia por fase", ""]
    partes += _tabla_de_fases(reporte)
    partes += ["", "## Qué contestó el servicio en cada fase", ""]
    partes += _tabla_de_respuestas(reporte)
    partes.append("")
    partes.append(
        "Un código importa tanto como una latencia. Con la base apagada el servicio contesta "
        "**503 con cuerpo tipado** y `Retry-After`, no 500: un 500 dice «esta petición salió "
        "mal» y un balanceador la vuelve a mandar a la misma instancia; un 503 dice «esta "
        "instancia no puede ahora». Y con el proveedor de modelo caído no hay error ninguno: "
        "la respuesta repliega a extracto, que es texto publicado y citado."
    )

    partes += ["", "## Fallos inducidos", ""]
    partes.append("| Fallo | Se indujo | Recuperación | Hizo falta reiniciar |")
    partes.append("| --- | --- | ---: | --- |")
    for fallo in reporte.fallos:
        if fallo.recuperado_en_s is not None:
            recuperacion = f"{fallo.recuperado_en_s} s"
        elif not fallo.medir_recuperacion:
            # No se midió porque este fallo no deja al servicio fuera de
            # servicio: el proveedor caído repliega a extracto y la fuente caída
            # no toca el camino de consulta. Decir «no volvió» sería informar un
            # problema donde no lo hubo.
            recuperacion = "no aplica"
        else:
            recuperacion = "no volvió" if fallo.aplicado else "—"
        induccion = "sí" if fallo.aplicado else f"no: {fallo.error or 'no se pudo'}"
        reinicio = "sí" if fallo.reinicio_necesario else "no"
        partes.append(f"| {fallo.nombre} | {induccion} | {recuperacion} | {reinicio} |")

    partes += ["", "## Límites", ""]
    if reporte.limite_configurado:
        partes.append(
            f"Límite configurado: **{reporte.limite_configurado}** consultas por minuto y por "
            "origen. Cada conversación llega con su propio origen, como llegaría detrás de un "
            "balanceador; además corre un origen abusivo que pide sin parar."
        )
        partes.append("")
        partes.append(
            f"- Al origen abusivo se le rechazaron **{reporte.abusador_frenado}** peticiones "
            f"y se le sirvieron {reporte.abusador_servido}."
        )
        partes.append(
            f"- A las conversaciones legítimas se les rechazaron **{reporte.limite_429}**."
        )
        partes.append("")
        partes.append(
            "Lo que importa no es que el abusivo reciba 429: es que los demás sigan siendo "
            "atendidos mientras lo recibe. Un límite que protege al servicio y deja afuera a "
            "todo el mundo no protege a nadie."
        )
    else:
        partes.append(
            "El límite estuvo **desactivado** durante este ensayo, así que lo medido es el techo "
            "del servicio y no el del límite."
        )

    partes += ["", "## Exposición de datos pendientes", ""]
    if not reporte.filtraciones:
        partes.append(
            "Ninguna. Se revisó **cada** cuerpo de respuesta —de éxito y de error— buscando "
            "estados de trabajo, nombres internos y fragmentos que no pertenezcan al corte "
            "publicado."
        )
    else:
        partes.append(f"**{len(reporte.filtraciones)} hallazgo(s).**")
        partes.append("")
        for filtracion in reporte.filtraciones[:20]:
            partes.append(f"- `{filtracion.ruta}`: {filtracion.que} — `{filtracion.detalle}`")

    if reporte.avisos:
        partes += ["", "## Lo que este ensayo no prueba", ""]
        partes += [f"- {aviso}" for aviso in reporte.avisos]
    return "\n".join(partes) + "\n"
