"""Cliente HTTP de captura.

Hace exactamente una cosa: pedir un recurso público con `GET` y devolver lo que
llegó, con sus cabeceras y redirecciones. No interpreta el contenido, no lo
extrae y no decide si es útil.

Nunca envía formularios, no inicia sesión y no reintenta con otra identidad
cuando lo rechazan.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from backend_normativo.config import get_settings
from backend_normativo.ingesta.politica import (
    ESTADOS_ACCESO_LIMITADO,
    ESTADOS_TRANSITORIOS,
    AccesoNoPermitido,
    LimitadorPorDominio,
    Presupuesto,
    Robots,
    verificar_url_permitida,
)

# Cabeceras que vale la pena conservar: describen el recurso y permiten
# revalidarlo. Se excluyen deliberadamente `set-cookie` y cualquier cabecera de
# sesión o autorización.
CABECERAS_CONSERVADAS = (
    "content-type",
    "content-length",
    "content-disposition",
    "content-language",
    "etag",
    "last-modified",
    "date",
    "cache-control",
    "expires",
    "location",
)


@dataclass
class Descarga:
    """Lo que devolvió una solicitud, sin interpretar."""

    url_solicitada: str
    url_final: str
    http_status: int | None
    contenido: bytes
    mime: str | None
    etag: str | None
    last_modified: str | None
    cabeceras: dict[str, str]
    redirecciones: list[dict[str, object]] = field(default_factory=list)
    capturado_en: datetime = field(default_factory=lambda: datetime.now(UTC))
    intentos: int = 1
    error: str | None = None
    acceso_limitado: bool = False
    error_tls: bool = False

    @property
    def no_modificado(self) -> bool:
        return self.http_status == 304

    @property
    def exitosa(self) -> bool:
        return self.error is None and self.http_status is not None and self.http_status < 400


class ClienteCaptura:
    """Cliente con la política del ADR 0003 aplicada.

    La verificación de TLS está siempre activa. Lo único configurable es qué
    paquete de certificados usar: mantener la verificación con un bundle propio
    es distinto de apagarla.
    """

    def __init__(self, presupuesto: Presupuesto | None = None) -> None:
        ajustes = get_settings()
        self.ajustes = ajustes
        self.presupuesto = presupuesto or Presupuesto.desde_config(None)
        self.limitador = LimitadorPorDominio()

        contexto = ssl.create_default_context(
            cafile=str(ajustes.ca_bundle) if ajustes.ca_bundle else None
        )
        contexto.check_hostname = True
        contexto.verify_mode = ssl.CERT_REQUIRED

        self._cliente = httpx.Client(
            headers={
                "User-Agent": ajustes.user_agent,
                "Accept-Language": "es-AR,es;q=0.9",
            },
            timeout=httpx.Timeout(ajustes.http_timeout_s),
            follow_redirects=True,
            verify=contexto,
        )
        self.robots = Robots(ajustes.user_agent, self._cliente)

    def __enter__(self) -> ClienteCaptura:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.cerrar()

    def cerrar(self) -> None:
        self._cliente.close()

    def descargar(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        presupuesto: Presupuesto | None = None,
    ) -> Descarga:
        """Pide el recurso. Con `etag` o `last_modified` hace una solicitud
        condicional: si el servidor responde 304, no hubo transferencia."""
        verificar_url_permitida(url)
        presupuesto = presupuesto or self.presupuesto

        if presupuesto.respetar_robots and not self.robots.permite(url):
            return Descarga(
                url_solicitada=url,
                url_final=url,
                http_status=None,
                contenido=b"",
                mime=None,
                etag=None,
                last_modified=None,
                cabeceras={},
                error="robots.txt no permite esta ruta para nuestro agente",
                acceso_limitado=True,
            )

        cabeceras: dict[str, str] = {}
        if etag:
            cabeceras["If-None-Match"] = etag
        if last_modified:
            cabeceras["If-Modified-Since"] = last_modified

        # Si el sitio declara `Crawl-delay`, manda el sitio: nuestro presupuesto
        # es un mínimo, no un permiso para ir más rápido.
        espera = presupuesto.delay_dominio_s
        if presupuesto.respetar_robots:
            declarada = self.robots.crawl_delay(url)
            if declarada is not None:
                espera = max(espera, declarada)

        ultimo_error: str | None = None
        for intento in range(1, presupuesto.reintentos_max + 1):
            self.limitador.esperar(url, espera)
            try:
                respuesta = self._cliente.get(url, headers=cabeceras)
            except ssl.SSLError as exc:
                # No se relaja la validación: se registra y se busca una fuente
                # oficial equivalente o carga manual trazada.
                return self._fallo(url, f"Fallo de validación TLS: {exc}", intento, error_tls=True)
            except httpx.HTTPError as exc:
                ultimo_error = f"{type(exc).__name__}: {exc}"
                if intento >= presupuesto.reintentos_max:
                    return self._fallo(url, ultimo_error, intento)
                continue

            if respuesta.status_code in ESTADOS_TRANSITORIOS and (
                intento < presupuesto.reintentos_max
            ):
                ultimo_error = f"HTTP {respuesta.status_code}"
                continue

            return self._desde_respuesta(url, respuesta, intento)

        return self._fallo(url, ultimo_error or "Sin respuesta", presupuesto.reintentos_max)

    def _desde_respuesta(self, url: str, respuesta: httpx.Response, intentos: int) -> Descarga:
        conservadas = {
            nombre: valor
            for nombre, valor in respuesta.headers.items()
            if nombre.lower() in CABECERAS_CONSERVADAS
        }
        redirecciones = [
            {
                "url": str(previa.url),
                "status": previa.status_code,
                "location": previa.headers.get("location"),
            }
            for previa in respuesta.history
        ]
        limitado = respuesta.status_code in ESTADOS_ACCESO_LIMITADO
        return Descarga(
            url_solicitada=url,
            url_final=str(respuesta.url),
            http_status=respuesta.status_code,
            contenido=respuesta.content if respuesta.status_code != 304 else b"",
            mime=(respuesta.headers.get("content-type") or "").split(";")[0].strip() or None,
            etag=respuesta.headers.get("etag"),
            last_modified=respuesta.headers.get("last-modified"),
            cabeceras=conservadas,
            redirecciones=redirecciones,
            intentos=intentos,
            error=(f"HTTP {respuesta.status_code}" if respuesta.status_code >= 400 else None),
            acceso_limitado=limitado,
        )

    @staticmethod
    def _fallo(url: str, error: str, intentos: int, *, error_tls: bool = False) -> Descarga:
        return Descarga(
            url_solicitada=url,
            url_final=url,
            http_status=None,
            contenido=b"",
            mime=None,
            etag=None,
            last_modified=None,
            cabeceras={},
            intentos=intentos,
            error=error,
            error_tls=error_tls,
        )


__all__ = ["AccesoNoPermitido", "ClienteCaptura", "Descarga", "Presupuesto"]
