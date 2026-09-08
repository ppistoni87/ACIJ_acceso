"""Política de acceso a fuentes públicas.

Implementa el ADR 0003: solo lectura pública, TLS validado siempre, respeto de
`robots.txt`, presupuesto por dominio y reintentos únicamente ante fallos
transitorios.

Ninguna de estas reglas es negociable desde la configuración de una fuente: la
configuración puede hacer el acceso más conservador, nunca menos.
"""

from __future__ import annotations

import threading
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from backend_normativo.config import get_settings

# Códigos que ameritan reintentar: el servidor no respondió o falló de forma
# transitoria. Un 403 o un 404 no se reintentan: no cambian por insistir.
ESTADOS_TRANSITORIOS = frozenset({408, 500, 502, 503, 504})

# Códigos que significan "acceso limitado" y pausan la fuente. No se rotan
# identidades ni se reintenta con otra apariencia.
ESTADOS_ACCESO_LIMITADO = frozenset({401, 403, 429, 451})


class AccesoNoPermitido(Exception):
    """La política prohíbe esta solicitud. No es un fallo de red."""


@dataclass(frozen=True)
class Presupuesto:
    """Cuánto se le puede pedir a un dominio."""

    delay_dominio_s: float = 2.0
    concurrencia: int = 1
    reintentos_max: int = 3
    respetar_robots: bool = True

    @classmethod
    def desde_config(cls, config: dict | None) -> Presupuesto:
        ajustes = get_settings()
        config = config or {}
        # El máximo lo fija la política, no la fuente: una configuración puede
        # ser más conservadora, nunca más agresiva.
        concurrencia = min(
            int(config.get("concurrencia", ajustes.concurrencia_dominio_default)),
            ajustes.concurrencia_dominio_max,
        )
        delay = max(
            float(config.get("delay_dominio_s", ajustes.delay_dominio_s_default)),
            ajustes.delay_dominio_s_default,
        )
        return cls(
            delay_dominio_s=delay,
            concurrencia=max(1, concurrencia),
            reintentos_max=min(
                int(config.get("reintentos_max", ajustes.reintentos_max)), ajustes.reintentos_max
            ),
            respetar_robots=bool(config.get("respetar_robots", ajustes.respetar_robots)),
        )


class LimitadorPorDominio:
    """Espacia las solicitudes a un mismo dominio.

    El estado es por proceso. Con varios procesos, el espaciado real es el de
    cada uno: el presupuesto se reparte configurando menos concurrencia, no
    asumiendo coordinación que no existe.
    """

    def __init__(self) -> None:
        self._ultimo: dict[str, float] = {}
        self._candados: dict[str, threading.Lock] = {}
        self._candado_global = threading.Lock()

    def _candado(self, dominio: str) -> threading.Lock:
        with self._candado_global:
            return self._candados.setdefault(dominio, threading.Lock())

    def esperar(self, url: str, delay_s: float) -> float:
        dominio = urlparse(url).netloc
        with self._candado(dominio):
            ahora = time.monotonic()
            anterior = self._ultimo.get(dominio)
            espera = 0.0
            if anterior is not None:
                espera = max(0.0, delay_s - (ahora - anterior))
                if espera:
                    time.sleep(espera)
            self._ultimo[dominio] = time.monotonic()
            return espera


class Robots:
    """Cachea `robots.txt` por dominio.

    Si el archivo no se puede leer, se permite el acceso: la ausencia de reglas
    no es una prohibición. Si se lee y prohíbe, se respeta.
    """

    def __init__(self, user_agent: str, cliente: httpx.Client) -> None:
        self.user_agent = user_agent
        self._cliente = cliente
        self._cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def permite(self, url: str) -> bool:
        parser = self._parser_de(url)
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        """Espera que el sitio pide entre solicitudes, si la declara.

        Se respeta como piso: si el sitio pide más que nuestro presupuesto,
        manda el sitio.
        """
        parser = self._parser_de(url)
        if parser is None:
            return None
        try:
            valor = parser.crawl_delay(self.user_agent)
        except (AttributeError, ValueError):
            return None
        return float(valor) if valor is not None else None

    def _parser_de(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        partes = urlparse(url)
        origen = f"{partes.scheme}://{partes.netloc}"
        if origen not in self._cache:
            self._cache[origen] = self._descargar(origen)
        return self._cache[origen]

    def _descargar(self, origen: str) -> urllib.robotparser.RobotFileParser | None:
        try:
            respuesta = self._cliente.get(f"{origen}/robots.txt", timeout=10.0)
        except httpx.HTTPError:
            return None
        if respuesta.status_code >= 400:
            return None
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(respuesta.text.splitlines())
        return parser


def verificar_url_permitida(url: str) -> None:
    """Rechaza lo que la política no permite pedir."""
    partes = urlparse(url)
    if partes.scheme not in ("http", "https"):
        raise AccesoNoPermitido(
            f"Solo se descargan recursos HTTP(S); {url!r} usa {partes.scheme!r}."
        )
    if not partes.netloc:
        raise AccesoNoPermitido(f"{url!r} no tiene host.")
    if "{" in url or "}" in url:
        raise AccesoNoPermitido(f"{url!r} es una plantilla sin resolver, no una dirección.")
    if partes.username or partes.password:
        raise AccesoNoPermitido("La URL incluye credenciales. No se reutilizan claves de terceros.")
