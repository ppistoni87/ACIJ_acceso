"""Credenciales firmadas por persona, con vencimiento y revocación.

P-017 criterio 1: «la identidad validada determina los roles y actor auditado; no
se acepta un X-Actor libre como identidad de producción y se prueba revocación
de sesión».

Qué había y por qué no alcanza. Las rutas de administración pedían un token de
una lista en `BN_ADMIN_TOKENS` y tomaban al actor de la cabecera `X-Actor`. El
token está bien como puerta, pero identifica al **despliegue**, no a la persona:
quien lo tiene puede firmar como cualquiera. Y lo que se firma acá es que una
regla dice lo que dice el derecho. Una bitácora donde el actor lo escribe quien
llama no acredita nada.

Qué hay ahora. Una credencial es un token firmado con HMAC-SHA256 que dice quién
es, qué puede y hasta cuándo. El actor **sale de la credencial**, no de una
cabecera: `X-Actor` deja de ser una identidad. Los roles vienen adentro, así que
un revisor no puede publicar aunque conozca la ruta.

Por qué HMAC y no un proveedor de identidad. Porque no hay ninguno todavía y
porque la decisión de cuál no es de acá. Esto es autoconténido, se emite con un
comando, se revoca con otro y se reemplaza por OIDC sin tocar las rutas: lo que
las rutas piden es una `Identidad`, no un formato de token.
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets

VARIABLE_SECRETO = "BN_CREDENCIAL_SECRETO"
PREFIJO = "bn1"

# Los roles que una credencial puede llevar. Son los de las operaciones, no los
# de la base: un mismo rol de PostgreSQL sirve a varias personas con distinto
# alcance, y lo que se audita acá es qué le está permitido a la persona.
ROL_REVISOR = "revisor"
ROL_PUBLICADOR = "publicador"
ROL_AUDITOR = "auditor"
ROLES = frozenset({ROL_REVISOR, ROL_PUBLICADOR, ROL_AUDITOR})

# Cómo se estableció el actor que queda en la bitácora. Se guarda en cada
# evento porque una firma jurídica hecha con una identidad autodeclarada no es
# lo mismo que una hecha con credencial, y dentro de dos años nadie va a poder
# distinguirlas si no quedó escrito.
IDENTIDAD_CREDENCIAL = "CREDENCIAL_FIRMADA"
IDENTIDAD_AUTODECLARADA = "AUTODECLARADA"
IDENTIDAD_PROCESO_LOCAL = "PROCESO_LOCAL"
IDENTIDAD_NO_REGISTRADA = "NO_REGISTRADA"
PROCEDENCIAS = frozenset(
    {
        IDENTIDAD_CREDENCIAL,
        IDENTIDAD_AUTODECLARADA,
        IDENTIDAD_PROCESO_LOCAL,
        IDENTIDAD_NO_REGISTRADA,
    }
)

DURACION_MAXIMA = dt.timedelta(days=90)


class CredencialInvalida(Exception):
    """La credencial no se puede aceptar. El mensaje dice por qué."""


@dataclasses.dataclass(frozen=True)
class Identidad:
    """Quién hace la operación, qué puede y cómo se estableció."""

    actor: str
    roles: frozenset[str]
    procedencia: str
    jti: str = ""
    vence_en: dt.datetime | None = None

    def puede(self, rol: str) -> bool:
        return rol in self.roles

    @property
    def verificada(self) -> bool:
        return self.procedencia == IDENTIDAD_CREDENCIAL


def _b64(crudo: bytes) -> str:
    return base64.urlsafe_b64encode(crudo).decode().rstrip("=")


def _des_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def secreto() -> bytes | None:
    """El secreto de firma, o `None` si no está configurado.

    Devuelve `None` en vez de inventar uno: un secreto por omisión haría que
    todas las instalaciones compartieran el mismo, y una credencial emitida en
    la máquina de cualquiera valdría en producción.
    """
    valor = os.environ.get(VARIABLE_SECRETO, "").strip()
    return valor.encode() if valor else None


def _firma(secreto_bytes: bytes, cuerpo: str) -> str:
    return _b64(hmac.new(secreto_bytes, cuerpo.encode(), hashlib.sha256).digest())


def emitir(
    actor: str,
    roles: set[str] | frozenset[str],
    *,
    duracion: dt.timedelta,
    secreto_bytes: bytes | None = None,
    ahora: dt.datetime | None = None,
) -> tuple[str, Identidad]:
    """Emite una credencial. Devuelve el token y lo que representa."""
    secreto_bytes = secreto_bytes or secreto()
    if secreto_bytes is None:
        raise CredencialInvalida(
            f"No hay secreto de firma. Configurá {VARIABLE_SECRETO} con un valor "
            "generado al azar y guardalo en el gestor de secretos, no en el código."
        )
    actor = actor.strip()
    if not actor:
        raise CredencialInvalida("Una credencial sin actor no identifica a nadie.")
    desconocidos = set(roles) - ROLES
    if desconocidos:
        raise CredencialInvalida(
            f"Roles que no existen: {', '.join(sorted(desconocidos))}. "
            f"Los que hay son {', '.join(sorted(ROLES))}."
        )
    if not roles:
        raise CredencialInvalida("Una credencial sin roles no autoriza nada.")
    if duracion <= dt.timedelta(0):
        raise CredencialInvalida("Una credencial ya vencida no sirve para nada.")
    if duracion > DURACION_MAXIMA:
        raise CredencialInvalida(
            f"El máximo es {DURACION_MAXIMA.days} días. Una credencial que no vence "
            "es una contraseña que nadie rota."
        )

    ahora = ahora or dt.datetime.now(dt.UTC)
    carga = {
        "act": actor,
        "rol": sorted(roles),
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + duracion).timestamp()),
        "jti": secrets.token_hex(8),
    }
    cuerpo = _b64(json.dumps(carga, sort_keys=True, separators=(",", ":")).encode())
    token = f"{PREFIJO}.{cuerpo}.{_firma(secreto_bytes, cuerpo)}"
    return token, Identidad(
        actor=actor,
        roles=frozenset(carga["rol"]),
        procedencia=IDENTIDAD_CREDENCIAL,
        jti=carga["jti"],
        vence_en=ahora + duracion,
    )


def verificar(
    token: str,
    *,
    secreto_bytes: bytes | None = None,
    ahora: dt.datetime | None = None,
) -> Identidad:
    """Comprueba firma y vencimiento. No comprueba revocación: eso pide la base."""
    secreto_bytes = secreto_bytes or secreto()
    if secreto_bytes is None:
        raise CredencialInvalida(
            f"No hay secreto de firma configurado en {VARIABLE_SECRETO}: "
            "ninguna credencial se puede verificar."
        )
    partes = token.strip().split(".")
    if len(partes) != 3 or partes[0] != PREFIJO:
        raise CredencialInvalida("La credencial no tiene la forma esperada.")
    _, cuerpo, firma = partes

    # Comparación en tiempo constante: comparar con `==` filtra, por el tiempo
    # que tarda, cuántos bytes del principio coinciden.
    if not hmac.compare_digest(firma, _firma(secreto_bytes, cuerpo)):
        raise CredencialInvalida("La firma no corresponde: la credencial fue alterada.")

    try:
        carga = json.loads(_des_b64(cuerpo))
    except (ValueError, json.JSONDecodeError) as error:
        raise CredencialInvalida("El contenido de la credencial no se puede leer.") from error

    ahora = ahora or dt.datetime.now(dt.UTC)
    vence_en = dt.datetime.fromtimestamp(int(carga.get("exp", 0)), dt.UTC)
    if vence_en <= ahora:
        raise CredencialInvalida(
            f"La credencial venció el {vence_en.isoformat(timespec='seconds')}."
        )
    roles = frozenset(carga.get("rol", [])) & ROLES
    if not roles:
        raise CredencialInvalida("La credencial no lleva ningún rol conocido.")
    actor = str(carga.get("act", "")).strip()
    if not actor:
        raise CredencialInvalida("La credencial no identifica a nadie.")

    return Identidad(
        actor=actor,
        roles=roles,
        procedencia=IDENTIDAD_CREDENCIAL,
        jti=str(carga.get("jti", "")),
        vence_en=vence_en,
    )
