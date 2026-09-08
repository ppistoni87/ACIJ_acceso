"""Configuración del backend normativo.

Los secretos se leen del entorno, nunca del código. `.env.example` documenta las
variables sin valores reales.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ca_bundle_del_entorno() -> Path | None:
    """Paquete de certificados del entorno, si hay uno declarado."""
    import os

    for variable in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        valor = os.environ.get(variable)
        if valor and Path(valor).is_file():
            return Path(valor)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    entorno: str = "local"

    # --- Base de datos -------------------------------------------------
    # Rol `migrador`: única identidad que aplica DDL.
    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/backend_normativo"
    )
    # Rol `lector_api`: sin escritura ni acceso a staging.
    database_url_api: PostgresDsn | None = None
    # Rol `ingestor`: escribe capturas y candidatos, no publica.
    database_url_ingesta: PostgresDsn | None = None
    sql_echo: bool = False

    # --- Almacenamiento de objetos (capturas inmutables) ----------------
    # La base guarda `objeto_uri` y hashes; nunca una ruta que solo exista en
    # la máquina de un agente. En local el esquema es `file://`.
    objetos_base_uri: str = "file://var/objetos"
    objetos_dir: Path = REPO_ROOT / "var" / "objetos"

    # --- Política de acceso a fuentes -----------------------------------
    user_agent: str = (
        "ACIJ-BackendNormativo/0.1 (+https://github.com/ppistoni87/ACIJ_acceso) "
        "acceso-a-derechos; contacto en el repositorio"
    )
    http_timeout_s: float = 30.0
    # Presupuesto inicial de la especificación (sección 6).
    delay_dominio_s_default: float = 2.0
    concurrencia_dominio_default: int = 1
    concurrencia_dominio_max: int = 2
    reintentos_max: int = 3
    respetar_robots: bool = True
    # La validación TLS completa no es configurable: desactivarla está prohibido
    # por la especificación. Se expone solo el paquete de certificados a usar,
    # que por defecto es el del entorno (`SSL_CERT_FILE`). Un bundle propio que
    # mantiene la verificación es distinto de apagar la verificación.
    ca_bundle: Path | None = Field(default_factory=lambda: _ca_bundle_del_entorno())

    # --- Frescura --------------------------------------------------------
    ttl_defecto_dias: int = 30

    @property
    def url_api(self) -> str:
        return str(self.database_url_api or self.database_url)

    @property
    def url_ingesta(self) -> str:
        return str(self.database_url_ingesta or self.database_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
