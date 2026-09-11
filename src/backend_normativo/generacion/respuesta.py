"""Cómo se arma una respuesta, y cómo se dice de qué modo se armó (P-013).

Tres modos, y la diferencia entre ellos es lo que el criterio 3 pide que no se
borre:

* **GENERADA** — un proveedor configurado redactó la respuesta y los validadores
  la aprobaron. Cada afirmación tiene su cita.
* **EXTRACTO** — no hubo proveedor, o el proveedor se cayó, o lo que devolvió no
  pasó los validadores. Se arman los fragmentos recuperados tal como están. Es
  útil y es peor que una explicación, y **se declara como extracto**: el plan lo
  dice con esas palabras, «un extracto de respaldo no se presenta como
  generación activa».
* **ABSTENCION** — no hay evidencia suficiente. Se explica el límite con un
  motivo tipado y se ofrece qué se puede hacer en su lugar.

Sobre el modo extractivo hay algo que conviene decir: **no puede alucinar**. El
texto sale literal de fragmentos publicados. Es menos cómodo de leer que una
explicación redactada y es completamente verificable, así que sirve como piso y
no como un parche vergonzante.

Y sobre las instrucciones maliciosas (criterio 2): los fragmentos entran al
armado como **datos citados**, nunca como instrucciones. El modo extractivo no
tiene dónde obedecer una orden porque no hay nadie interpretando; el modo
generado la lleva delimitada y con la consigna de tratarla como texto. Lo que
cierra el caso no es la consigna sino los validadores: una respuesta que cambió
de tema porque un documento se lo pidió no va a tener citas que la sostengan.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol

from backend_normativo.generacion.validadores import Veredicto, verificar


class ModoRespuesta(enum.StrEnum):
    GENERADA = "GENERADA"
    EXTRACTO = "EXTRACTO"
    ABSTENCION = "ABSTENCION"


class MotivoAbstencion(enum.StrEnum):
    SIN_EVIDENCIA = "SIN_EVIDENCIA"
    CONTEXTO_INSUFICIENTE = "CONTEXTO_INSUFICIENTE"
    RESPUESTA_RECHAZADA = "RESPUESTA_RECHAZADA"


class ProveedorCaido(Exception):
    """El proveedor de modelo no contestó."""


class Proveedor(Protocol):
    """Lo único que el generador necesita de un modelo.

    Deliberadamente mínimo: cambiar de proveedor no puede obligar a tocar los
    validadores ni la política de abstención, que son las partes que cuidan a
    quien consulta.
    """

    nombre: str

    def redactar(self, consulta: str, fragmentos: list) -> str: ...


@dataclass
class RespuestaGenerada:
    modo: ModoRespuesta
    texto: str
    citas: list[str] = field(default_factory=list)
    motivo: MotivoAbstencion | None = None
    alternativa: str | None = None
    proveedor: str | None = None
    veredicto: Veredicto | None = None

    def a_dict(self) -> dict:
        return {
            "modo": self.modo.value,
            "texto": self.texto,
            "citas": self.citas,
            "motivo": self.motivo.value if self.motivo else None,
            "alternativa": self.alternativa,
            "proveedor": self.proveedor,
            "validacion": self.veredicto.a_dict() if self.veredicto else None,
        }


ALTERNATIVA_SIN_EVIDENCIA = (
    "Todavía no hay texto publicado que responda esto. Se puede consultar el punto de "
    "atención del organismo, que sí está cargado con su teléfono y su dirección."
)
ALTERNATIVA_RECHAZADA = (
    "La redacción automática no pasó los controles de cita, así que se muestran los "
    "fragmentos tal como están publicados."
)


def _cita(fragmento) -> str:
    return f"[[chunk:{fragmento.chunk_id}]]"


def extractar(fragmentos: list) -> str:
    """Arma la respuesta con los fragmentos, literales y citados.

    No resume, no conecta, no interpreta: cualquiera de esas tres cosas es
    redacción, y redactar sin modelo es inventar con más pasos.
    """
    partes = []
    for fragmento in fragmentos:
        encabezado = fragmento.norma
        if getattr(fragmento, "unidad", None):
            encabezado = f"{encabezado}, {fragmento.unidad}"
        partes.append(f"**{encabezado}** {_cita(fragmento)}\n\n{(fragmento.texto or '').strip()}")
    return "\n\n---\n\n".join(partes)


def responder(
    consulta: str, fragmentos: list, *, proveedor: Proveedor | None = None
) -> RespuestaGenerada:
    """Arma la mejor respuesta posible y declara con qué se armó."""
    if not fragmentos:
        return RespuestaGenerada(
            modo=ModoRespuesta.ABSTENCION,
            texto=(
                "No hay evidencia publicada para contestar esto. No es que la respuesta sea "
                "que no corresponde: es que el sistema no tiene con qué afirmarlo."
            ),
            motivo=MotivoAbstencion.SIN_EVIDENCIA,
            alternativa=ALTERNATIVA_SIN_EVIDENCIA,
        )

    citas = [str(f.chunk_id) for f in fragmentos]

    if proveedor is None:
        return RespuestaGenerada(
            modo=ModoRespuesta.EXTRACTO,
            texto=extractar(fragmentos),
            citas=citas,
            alternativa=(
                "No hay proveedor de modelo configurado, así que esto es el texto publicado "
                "tal como está, sin redactar."
            ),
        )

    try:
        redactado = proveedor.redactar(consulta, fragmentos)
    except Exception as error:  # la caída del proveedor es un caso previsto
        return RespuestaGenerada(
            modo=ModoRespuesta.EXTRACTO,
            texto=extractar(fragmentos),
            citas=citas,
            proveedor=getattr(proveedor, "nombre", None),
            alternativa=(
                f"El proveedor de modelo no contestó ({type(error).__name__}); se muestran "
                "los fragmentos publicados tal como están."
            ),
        )

    veredicto = verificar(redactado, fragmentos)
    if not veredicto.sirve:
        # Se cae al extracto en vez de servir una redacción que no se sostiene, y
        # se dice que es un extracto: presentar esto como generación sería
        # exactamente lo que el criterio 3 prohíbe.
        return RespuestaGenerada(
            modo=ModoRespuesta.EXTRACTO,
            texto=extractar(fragmentos),
            citas=citas,
            motivo=MotivoAbstencion.RESPUESTA_RECHAZADA,
            alternativa=ALTERNATIVA_RECHAZADA,
            proveedor=getattr(proveedor, "nombre", None),
            veredicto=veredicto,
        )

    return RespuestaGenerada(
        modo=ModoRespuesta.GENERADA,
        texto=redactado,
        citas=citas,
        proveedor=getattr(proveedor, "nombre", None),
        veredicto=veredicto,
    )
