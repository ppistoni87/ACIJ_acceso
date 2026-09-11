"""Límites de uso en servidor (P-017, criterio 3).

Dos límites y dos motivos distintos.

El primero acota **cuántas consultas por minuto** acepta el servicio de un mismo
origen. No está para castigar a nadie: está porque sin él una sola dirección
puede ocupar toda la capacidad y dejar sin respuesta a todos los demás, y porque
la medición de escalado mostró que este sistema, saturado, **encola en vez de
rechazar** —una petición que expira consume igual y no devuelve nada—. Poner el
límite antes es más barato que repartir mal lo que hay.

El segundo cuenta **autenticaciones administrativas fallidas**. Una credencial
firmada no se adivina, pero un token compartido sí se prueba, y probar mil veces
no debería costar lo mismo que probar una vez.

Tres cosas que este módulo deliberadamente **no** hace:

* **No guarda direcciones.** La clave del balde es un hash con sal aleatoria del
  proceso: sirve para contar y no para saber de quién. La sal muere con el
  proceso, así que ni siquiera es estable entre reinicios.
* **No confía en `X-Forwarded-For` por defecto.** Esa cabecera la pone quien
  llama; tomarla sin más convierte el límite en un adorno, porque cualquiera
  cambia de identidad escribiendo otro número. Se usa sólo si el despliegue
  declara cuántos proxies suyos hay delante (`BN_PROXIES_CONFIABLES`), y se lee
  la posición que corresponde a ese salto y no la primera de la lista.
* **No se comparte entre procesos.** El balde vive en memoria del proceso. Con
  cuatro instancias el límite efectivo es cuatro veces el configurado, y eso hay
  que tenerlo en cuenta al elegir el número. Un límite compartido necesita un
  almacén común, que este despliegue todavía no tiene; se dice acá y en el
  informe de carga en vez de dejar que el número engañe.
"""

from __future__ import annotations

import hashlib
import math
import os
import secrets
import threading
import time
from dataclasses import dataclass, field

# Sal del proceso. No se configura: una sal en el entorno sería un secreto más
# que administrar y no agrega nada, porque lo que protege es que el valor no
# sobreviva al proceso que lo usa.
_SAL = secrets.token_bytes(16)

# El límite general, por origen y por minuto. En 0 queda desactivado, que es lo
# que necesita una medición de caudal: un límite puesto mientras se mide el
# techo mide el límite y no el techo.
VARIABLE_LIMITE = "BN_LIMITE_CONSULTAS_POR_MINUTO"
LIMITE_DEFECTO = 120

# Autenticaciones administrativas fallidas admitidas antes de frenar, y en
# cuánto tiempo se recupera el cupo.
VARIABLE_LIMITE_AUTENTICACION = "BN_LIMITE_AUTENTICACIONES_FALLIDAS"
LIMITE_AUTENTICACION_DEFECTO = 10
VENTANA_AUTENTICACION_S = 300.0

VARIABLE_PROXIES = "BN_PROXIES_CONFIABLES"

# Cada cuántas decisiones se barren los baldes que ya no hacen falta. Un
# diccionario que sólo crece es una fuga de memoria, y una fuga de memoria en el
# componente que defiende del abuso es una forma de abuso.
CADA_CUANTO_SE_BARRE = 512


@dataclass
class Veredicto:
    permitido: bool
    espera_s: float = 0.0
    restantes: int = 0

    @property
    def retry_after(self) -> int:
        return max(1, math.ceil(self.espera_s))


@dataclass
class _Balde:
    fichas: float
    visto_en: float


class Limitador:
    """Balde de fichas: `cupo` fichas que se reponen a lo largo de `ventana_s`.

    Un balde y no un contador por ventana fija: con ventanas fijas alguien puede
    gastar el cupo entero al final de una y el cupo entero al principio de la
    siguiente, que es el doble de lo configurado en el peor momento posible.
    """

    def __init__(self, *, cupo: int, ventana_s: float = 60.0) -> None:
        self.cupo = cupo
        self.ventana_s = ventana_s
        self._baldes: dict[str, _Balde] = {}
        self._candado = threading.Lock()
        self._decisiones = 0

    @property
    def activo(self) -> bool:
        return self.cupo > 0

    def _balde(self, clave: str, ahora: float) -> _Balde:
        balde = self._baldes.get(clave)
        if balde is None:
            balde = _Balde(fichas=float(self.cupo), visto_en=ahora)
            self._baldes[clave] = balde
            return balde
        transcurrido = max(0.0, ahora - balde.visto_en)
        balde.fichas = min(
            float(self.cupo), balde.fichas + transcurrido * self.cupo / self.ventana_s
        )
        balde.visto_en = ahora
        return balde

    def _barrer(self, ahora: float) -> None:
        """Tira los baldes que ya no dicen nada.

        El criterio es la inactividad y nada más. Mirar también `fichas` parece
        más prolijo y está mal: las fichas de un balde que nadie tocó están sin
        reponer —la reposición se calcula al usarlo—, así que un balde ocioso y
        lleno figura con las fichas de la última vez y no se barre nunca. Se
        probó con seiscientos orígenes y no se barrió ninguno. Alcanza con la
        inactividad: pasada una ventana entera, la reposición llega al cupo por
        aritmética, y un balde lleno es indistinguible de uno que no existe.
        """
        vencidos = [
            clave
            for clave, balde in self._baldes.items()
            if ahora - balde.visto_en > self.ventana_s
        ]
        for clave in vencidos:
            del self._baldes[clave]

    def permitir(self, clave: str, *, ahora: float | None = None) -> Veredicto:
        """Consume una ficha si hay. Si no hay, dice cuánto falta para la próxima."""
        if not self.activo:
            return Veredicto(permitido=True)
        ahora = time.monotonic() if ahora is None else ahora
        with self._candado:
            self._decisiones += 1
            if self._decisiones % CADA_CUANTO_SE_BARRE == 0:
                self._barrer(ahora)
            balde = self._balde(clave, ahora)
            if balde.fichas < 1.0:
                faltan = (1.0 - balde.fichas) * self.ventana_s / self.cupo
                return Veredicto(permitido=False, espera_s=faltan)
            balde.fichas -= 1.0
            return Veredicto(permitido=True, restantes=int(balde.fichas))

    def hay_cupo(self, clave: str, *, ahora: float | None = None) -> bool:
        """Mira sin consumir. Para frenar antes de trabajar, no después."""
        if not self.activo:
            return True
        ahora = time.monotonic() if ahora is None else ahora
        with self._candado:
            return self._balde(clave, ahora).fichas >= 1.0

    @property
    def origenes(self) -> int:
        """Cuántos baldes vivos hay. Es un número, no una lista de nadie."""
        return len(self._baldes)

    def reiniciar(self) -> None:
        with self._candado:
            self._baldes.clear()


def _entero_del_entorno(variable: str, defecto: int) -> int:
    crudo = (os.environ.get(variable) or "").strip()
    if not crudo:
        return defecto
    try:
        valor = int(crudo)
    except ValueError:
        # Una variable mal escrita no puede quedar en «sin límite» en silencio:
        # el modo inseguro se pide a propósito poniendo 0, no equivocándose.
        return defecto
    return max(0, valor)


_consultas: Limitador | None = None
_autenticaciones: Limitador | None = None
_candado_global = threading.Lock()


def limitador_de_consultas() -> Limitador:
    global _consultas
    with _candado_global:
        if _consultas is None:
            _consultas = Limitador(cupo=_entero_del_entorno(VARIABLE_LIMITE, LIMITE_DEFECTO))
        return _consultas


def limitador_de_autenticaciones() -> Limitador:
    global _autenticaciones
    with _candado_global:
        if _autenticaciones is None:
            _autenticaciones = Limitador(
                cupo=_entero_del_entorno(
                    VARIABLE_LIMITE_AUTENTICACION, LIMITE_AUTENTICACION_DEFECTO
                ),
                ventana_s=VENTANA_AUTENTICACION_S,
            )
        return _autenticaciones


def reiniciar_limitadores() -> None:
    """Vuelve a leer el entorno. La usan las pruebas; en servicio no hace falta."""
    global _consultas, _autenticaciones
    with _candado_global:
        _consultas = None
        _autenticaciones = None


def origen_de(solicitud) -> str:
    """De dónde viene la petición, según cuántos proxies propios haya delante.

    Con `BN_PROXIES_CONFIABLES=0` —el valor por omisión— se usa el par de la
    conexión y se ignora `X-Forwarded-For` entera. Con `n` mayor que cero se
    toma el elemento `n`-ésimo desde el final, que es el que escribió el proxy
    propio más externo: los de más a la izquierda los puede haber puesto quien
    llama, y tomarlos es dejar que elija su propia identidad.
    """
    proxies = _entero_del_entorno(VARIABLE_PROXIES, 0)
    if proxies > 0:
        reenviado = solicitud.headers.get("X-Forwarded-For") or ""
        saltos = [parte.strip() for parte in reenviado.split(",") if parte.strip()]
        if len(saltos) >= proxies:
            return saltos[-proxies]
    cliente = getattr(solicitud, "client", None)
    return getattr(cliente, "host", None) or "desconocido"


def clave_de(solicitud) -> str:
    """La identidad del balde: un hash con sal, no una dirección."""
    return hashlib.blake2b(
        origen_de(solicitud).encode("utf-8"), key=_SAL, digest_size=16
    ).hexdigest()


@dataclass
class Estado:
    """Lo que se puede contar sobre los límites sin contar sobre las personas."""

    limite_por_minuto: int = 0
    limite_autenticaciones: int = 0
    origenes_vigilados: int = 0
    proxies_confiables: int = 0
    avisos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {
            "limite_por_minuto": self.limite_por_minuto,
            "limite_autenticaciones_fallidas": self.limite_autenticaciones,
            "origenes_vigilados": self.origenes_vigilados,
            "proxies_confiables": self.proxies_confiables,
            "avisos": self.avisos,
        }


def estado() -> Estado:
    consultas = limitador_de_consultas()
    autenticaciones = limitador_de_autenticaciones()
    avisos: list[str] = []
    if not consultas.activo:
        avisos.append(
            f"El límite de consultas está desactivado ({VARIABLE_LIMITE}=0). Sirve para "
            "medir el techo real del servicio y no para servir a nadie."
        )
    avisos.append(
        "El límite es por proceso: el balde vive en memoria y no se comparte. Con varias "
        "instancias el límite efectivo se multiplica por la cantidad de instancias."
    )
    return Estado(
        limite_por_minuto=consultas.cupo,
        limite_autenticaciones=autenticaciones.cupo,
        origenes_vigilados=consultas.origenes,
        proxies_confiables=_entero_del_entorno(VARIABLE_PROXIES, 0),
        avisos=avisos,
    )
