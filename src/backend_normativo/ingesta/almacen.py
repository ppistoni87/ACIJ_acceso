"""Almacén de objetos direccionado por contenido.

La base guarda `objeto_uri` y hashes, nunca una ruta que solo funcione en la
máquina de un agente. El URI es estable porque deriva del contenido: dos
capturas idénticas comparten objeto, y una captura nunca pisa a otra.

La implementación local escribe bajo `var/objetos`; la interfaz es la misma que
usaría un almacén de objetos remoto.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from backend_normativo.config import get_settings


def sha256_de(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


@dataclass(frozen=True)
class ObjetoAlmacenado:
    sha256: str
    uri: str
    bytes: int
    ya_existia: bool


class AlmacenObjetos:
    """Guarda bytes por su hash. Escribir dos veces el mismo contenido es una
    operación sin efecto, no una duplicación."""

    def __init__(self, base_uri: str | None = None, directorio: Path | None = None) -> None:
        ajustes = get_settings()
        self.base_uri = (base_uri or ajustes.objetos_base_uri).rstrip("/")
        self.directorio = directorio or ajustes.objetos_dir
        esquema = urlparse(self.base_uri).scheme
        if esquema != "file":
            raise ValueError(
                f"Solo está implementado el esquema file:// y se pidió {esquema!r}. "
                "Un almacén remoto tiene que implementar esta misma interfaz."
            )

    def _ruta(self, sha256: str) -> Path:
        # Dos niveles de prefijo: un directorio con cientos de miles de archivos
        # planos es incómodo de inspeccionar y lento en algunos sistemas.
        return self.directorio / sha256[:2] / sha256[2:4] / sha256

    def uri_de(self, sha256: str) -> str:
        return f"{self.base_uri}/{sha256[:2]}/{sha256[2:4]}/{sha256}"

    def guardar(self, datos: bytes) -> ObjetoAlmacenado:
        sha256 = sha256_de(datos)
        ruta = self._ruta(sha256)
        ya_existia = ruta.exists()
        if not ya_existia:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            # Escritura por archivo temporal y renombrado: una corrida
            # interrumpida no deja un objeto a medias con un hash que promete
            # contenido completo.
            temporal = ruta.with_suffix(".parcial")
            temporal.write_bytes(datos)
            temporal.replace(ruta)
        return ObjetoAlmacenado(
            sha256=sha256, uri=self.uri_de(sha256), bytes=len(datos), ya_existia=ya_existia
        )

    def leer(self, sha256: str) -> bytes:
        ruta = self._ruta(sha256)
        if not ruta.exists():
            raise FileNotFoundError(f"El objeto {sha256} no está en {self.directorio}")
        return ruta.read_bytes()

    def existe(self, sha256: str) -> bool:
        return self._ruta(sha256).exists()
