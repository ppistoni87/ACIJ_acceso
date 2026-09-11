"""Quién convierte texto en vectores, y qué queda registrado de eso.

P-012 criterio 1: «el embedding conserva modelo, dimensión y hash del texto».
Las tres cosas son la procedencia del vector. Sin el modelo no se sabe con qué
se calculó y dos vectores de modelos distintos no se pueden comparar —el mismo
texto cae en lugares distintos del espacio—. Sin la dimensión no se sabe si
entra en la columna. Sin el hash no se sabe si el texto cambió después, y un
vector viejo sirve una respuesta desactualizada sin que nada avise.

El modelo entra por una interfaz y no por una llamada directa porque el proyecto
va a querer cambiarlo: el que viene por omisión es multilingüe y chico, elegido
para que el CI no tarde diez minutos en instalarlo, y en producción conviene uno
más grande. Cambiarlo es construir otro índice, no reemplazar vectores en su
lugar, y el esquema lo obliga.
"""

from __future__ import annotations

import hashlib
import math
import threading
from collections.abc import Iterable, Sequence
from typing import Protocol

# El modelo por omisión. Multilingüe de verdad —el corpus está en español y las
# consultas también—, 384 dimensiones y unos 220 MB: entra en el CI.
MODELO_POR_OMISION = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSION = 384


def hash_de(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def normalizar(vector: Sequence[float]) -> list[float]:
    """Lleva el vector a norma 1.

    Se guardan normalizados para que la distancia coseno sea un producto
    interno y para que dos vectores del mismo índice sean siempre comparables
    sin acordarse de dividir. Un vector de norma cero no se puede normalizar y
    tampoco se puede comparar con nada: es un error, no un vector válido.
    """
    norma = math.sqrt(sum(c * c for c in vector))
    if norma == 0.0:
        raise ValueError("un vector de norma cero no representa ningún texto")
    return [c / norma for c in vector]


class Embebedor(Protocol):
    """Lo que la indexación y la búsqueda necesitan de un modelo."""

    @property
    def modelo(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        """Vectores normalizados, uno por texto, en el mismo orden."""
        ...

    def embeber_consulta(self, consulta: str) -> list[float]:
        """El vector de una consulta.

        Está separado de `embeber` porque varios modelos de recuperación piden
        que la pregunta y el pasaje lleven prefijos distintos, y usar el mismo
        camino para los dos degrada la búsqueda sin que nada falle.
        """
        ...


class EmbebedorFastEmbed:
    """El modelo real, por ONNX y sin torch.

    Se carga perezosamente: importar este módulo no puede costar diez segundos
    ni bajar 220 MB, porque lo importa el CLI entero para una sola orden.
    """

    def __init__(self, modelo: str = MODELO_POR_OMISION, *, dimension: int = DIMENSION) -> None:
        self._modelo = modelo
        self._dimension = dimension
        self._motor = None

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def dimension(self) -> int:
        return self._dimension

    def _cargar(self):
        if self._motor is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as error:  # pragma: no cover - depende del entorno
                raise RuntimeError(
                    "Falta el extra de recuperación. Se instala con "
                    "`pip install -e '.[rag]'`. No es una dependencia del núcleo: "
                    "el backend sirve datos tipados sin ningún modelo."
                ) from error
            self._motor = TextEmbedding(self._modelo)
        return self._motor

    def _crudos(self, textos: Sequence[str]) -> list[list[float]]:
        vectores = [list(map(float, v)) for v in self._cargar().embed(list(textos))]
        for vector in vectores:
            if len(vector) != self._dimension:
                raise ValueError(
                    f"El modelo {self._modelo} devolvió {len(vector)} dimensiones y el "
                    f"índice espera {self._dimension}. Cambiar de dimensión es una "
                    "migración, no una opción de configuración."
                )
        return vectores

    def precargar(self) -> None:
        """Fuerza la carga ahora.

        Sirve para que la falta del extra se vea al arrancar y no en medio de
        la primera consulta de una persona.
        """
        self._cargar()

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        return [normalizar(v) for v in self._crudos(textos)]

    def embeber_consulta(self, consulta: str) -> list[float]:
        return self.embeber([consulta])[0]


# El modelo cargado, con su candado. No alcanza con `lru_cache`: la caché
# guarda el resultado **después** de que la función termina, así que veinte
# consultas que llegan juntas y encuentran el hueco vacío entran las veinte a
# cargar doscientos veinte megas cada una. Lo encontró el ensayo de carga: con
# veinte conversaciones concurrentes, las peticiones a `/v1/respuestas`
# expiraban a los treinta segundos y arrastraban al resto de las rutas.
_cargado: dict[str, EmbebedorFastEmbed | None] = {}
_candado_carga = threading.Lock()


def embebedor_compartido(modelo: str = MODELO_POR_OMISION) -> EmbebedorFastEmbed | None:
    """El embebedor del proceso, o `None` si el extra no está instalado.

    Cargar el modelo cuesta segundos y unos cientos de megas: uno por proceso,
    no uno por consulta y **no uno por hilo**. Devuelve `None` en vez de
    levantar excepción porque quien pregunta puede contestar igual con la mitad
    léxica y declararlo; caerse sería contestar peor que no tener el modelo.
    """
    if modelo in _cargado:
        return _cargado[modelo]
    with _candado_carga:
        # Se vuelve a mirar adentro del candado: entre el primer vistazo y
        # tomarlo, otro hilo pudo haberlo cargado.
        if modelo in _cargado:
            return _cargado[modelo]
        embebedor: EmbebedorFastEmbed | None = EmbebedorFastEmbed(modelo)
        try:
            embebedor.precargar()
        except (RuntimeError, OSError):
            embebedor = None
        _cargado[modelo] = embebedor
        return embebedor


def olvidar_embebedor() -> None:
    """Descarta el modelo cargado. La usan las pruebas."""
    with _candado_carga:
        _cargado.clear()


class EmbebedorDeterminista:
    """Un embebedor reproducible, sin modelo, para probar la mecánica.

    No mide calidad de recuperación y no pretende hacerlo: el `Recall@5` del
    criterio 3 se mide con el modelo real y está en `bn recuperacion evaluar`.
    Lo que sí prueba, y es la mayor parte de esta historia, es que el índice se
    construya por corte, que los filtros se apliquen antes de entregar nada, que
    la fusión no duplique y que un texto que cambió deje su vector marcado como
    viejo. Nada de eso depende del modelo, y atarlo a una descarga de 220 MB
    haría que se probara poco y tarde.

    Proyecta caracteres a dimensiones por hash: textos parecidos comparten
    caracteres y quedan cerca, que alcanza para ordenar de forma estable.
    """

    def __init__(self, *, dimension: int = DIMENSION) -> None:
        self._dimension = dimension

    @property
    def modelo(self) -> str:
        return "determinista:prueba"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _proyectar(self, texto: str) -> list[float]:
        acumulado = [0.0] * self._dimension
        palabras = texto.lower().split()
        if not palabras:
            # Un texto vacío no tiene dirección. Se le da una fija para que el
            # error salga en la validación del índice y no en una división.
            acumulado[0] = 1.0
            return acumulado
        for palabra in palabras:
            digest = hashlib.sha256(palabra.encode("utf-8")).digest()
            posicion = int.from_bytes(digest[:4], "big") % self._dimension
            signo = 1.0 if digest[4] % 2 == 0 else -1.0
            acumulado[posicion] += signo
        if not any(acumulado):
            acumulado[0] = 1.0
        return acumulado

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        return [normalizar(self._proyectar(t)) for t in textos]

    def embeber_consulta(self, consulta: str) -> list[float]:
        return self.embeber([consulta])[0]


def en_lotes(textos: Sequence[str], tamano: int) -> Iterable[Sequence[str]]:
    for inicio in range(0, len(textos), tamano):
        yield textos[inicio : inicio + tamano]
