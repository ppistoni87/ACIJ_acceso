"""Un derecho de uso exclusivo, con vencimiento, sobre un recurso que no admite
dos procesos a la vez.

P-020, criterio 2. El ciclo de monitoreo lo va a disparar un planificador cada
hora, y los planificadores reintentan: dos vueltas simultáneas capturarían la
misma fuente, crearían la misma versión y emitirían el mismo evento.

Por qué un arrendamiento y no un candado consultivo de PostgreSQL. El candado
(`pg_advisory_lock`) se suelta solo cuando muere la sesión, que es cómodo, pero
no se puede mirar: no dice quién lo tiene, desde cuándo ni hasta cuándo, y un
proceso que quedó *colgado* —vivo, sin avanzar— lo retiene para siempre. Acá lo
que se necesita es un tope máximo de corrida que se pueda consultar con un
`SELECT` cuando alguien pregunta por qué el ciclo no corrió anoche.

Por qué no se renueva mientras se trabaja. Renovar convierte el vencimiento en
una promesa vacía: un proceso trabado que sigue renovando bloquea el recurso
igual que un candado sin vencimiento, y el «tiempo máximo» deja de existir. El
arrendamiento dura lo que dura y una corrida que se pasa se entera al soltarlo,
porque otra pudo haber empezado en paralelo. Eso es un dato, no un detalle.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import os
import socket
import uuid
from collections.abc import Iterator

from sqlalchemy import Connection, Engine, text

DURACION_POR_OMISION = dt.timedelta(minutes=30)

# Una vuelta completa del ciclo sobre el corpus real tarda minutos, no media
# hora. El margen es holgado a propósito: el vencimiento existe para destrabar
# una caída, no para cortar una corrida lenta.

TOMAR = text("""
INSERT INTO arrendamientos (recurso, titular, tomado_en, vence_en, corridas)
VALUES (:recurso, :titular, clock_timestamp(), clock_timestamp() + :duracion, 1)
ON CONFLICT (recurso) DO UPDATE
   SET titular   = excluded.titular,
       tomado_en = excluded.tomado_en,
       vence_en  = excluded.vence_en,
       corridas  = arrendamientos.corridas + 1
 WHERE arrendamientos.vence_en <= clock_timestamp()
RETURNING recurso, titular, tomado_en, vence_en, corridas
""")

SOLTAR = text("""
UPDATE arrendamientos SET vence_en = clock_timestamp()
 WHERE recurso = :recurso AND titular = :titular AND vence_en > clock_timestamp()
RETURNING recurso
""")

VIGENTE = text("""
SELECT recurso, titular, tomado_en, vence_en, corridas FROM arrendamientos
 WHERE recurso = :recurso AND vence_en > clock_timestamp()
""")


@dataclasses.dataclass(frozen=True)
class Tenencia:
    """Un arrendamiento vigente, con quién lo tiene y hasta cuándo."""

    recurso: str
    titular: str
    tomado_en: dt.datetime
    vence_en: dt.datetime
    corridas: int

    @property
    def duracion(self) -> dt.timedelta:
        return self.vence_en - self.tomado_en


def titular_de_esta_corrida() -> str:
    """Máquina, proceso y corrida.

    Los tres hacen falta: la máquina para saber qué instancia quedó colgada, el
    proceso para encontrarlo ahí, y la corrida porque un mismo proceso puede
    tomar el recurso más de una vez y hay que poder distinguir las veces.
    """
    return f"{socket.gethostname()}/{os.getpid()}/{uuid.uuid4().hex[:8]}"[:200]


def _tenencia(fila) -> Tenencia:
    return Tenencia(
        recurso=fila.recurso,
        titular=fila.titular,
        tomado_en=fila.tomado_en,
        vence_en=fila.vence_en,
        corridas=fila.corridas,
    )


class Arrendador:
    """Toma y suelta el arrendamiento de un recurso sobre una conexión dada.

    La conexión tiene que confirmar cada sentencia por su cuenta. Un
    arrendamiento tomado dentro de la transacción del trabajo no es visible para
    nadie más hasta que esa transacción confirma, que es justo cuando ya no
    sirve para nada. Por eso `arrendar()` abre la suya en AUTOCOMMIT.
    """

    def __init__(
        self,
        conexion: Connection,
        recurso: str,
        *,
        duracion: dt.timedelta = DURACION_POR_OMISION,
        titular: str | None = None,
    ) -> None:
        self.conexion = conexion
        self.recurso = recurso
        self.duracion = duracion
        self.titular = titular or titular_de_esta_corrida()

    def tomar(self) -> Tenencia | None:
        """Devuelve la tenencia si el recurso estaba libre o vencido; `None` si no.

        Una sola sentencia, sin reintentos: si otro lo tiene, esta vuelta no
        corre y la siguiente la disparará el planificador. Reintentar acá sería
        poner a dos procesos a esperarse cuando lo correcto es que uno se vaya.
        """
        fila = self.conexion.execute(
            TOMAR,
            {"recurso": self.recurso, "titular": self.titular, "duracion": self.duracion},
        ).one_or_none()
        return _tenencia(fila) if fila is not None else None

    def soltar(self) -> bool:
        """Adelanta el vencimiento. `False` si ya no era nuestro.

        No borra la fila: queda como constancia de quién corrió la última
        vuelta. Un `False` significa que el arrendamiento venció mientras
        trabajábamos, y eso importa: otra corrida pudo haber empezado en
        paralelo sobre las mismas fuentes.
        """
        fila = self.conexion.execute(
            SOLTAR, {"recurso": self.recurso, "titular": self.titular}
        ).one_or_none()
        return fila is not None

    def quien_lo_tiene(self) -> Tenencia | None:
        fila = self.conexion.execute(VIGENTE, {"recurso": self.recurso}).one_or_none()
        return _tenencia(fila) if fila is not None else None


@dataclasses.dataclass
class Turno:
    """El resultado de pedir el turno, y cómo terminó."""

    tenencia: Tenencia | None = None
    ocupado_por: Tenencia | None = None
    se_paso: bool = False

    @property
    def tomado(self) -> bool:
        return self.tenencia is not None

    def por_que_no(self) -> str:
        if self.tomado:
            return ""
        if self.ocupado_por is None:
            return (
                "Otra corrida tomó el turno entre que este proceso lo pidió y lo consultó. "
                "Esta vuelta no hace nada, que es lo correcto."
            )
        vence = self.ocupado_por.vence_en.isoformat(timespec="seconds")
        return (
            f"Otra corrida tiene el turno: `{self.ocupado_por.titular}`, hasta {vence}. "
            "Esta vuelta no hace nada. Si esa corrida se cayó, el turno queda libre solo "
            "a esa hora y la vuelta siguiente lo toma."
        )

    def advertencia(self) -> str:
        if not self.se_paso:
            return ""
        return (
            "Esta corrida duró más que su arrendamiento y lo perdió mientras trabajaba: "
            "otra pudo haber empezado en paralelo sobre las mismas fuentes. Revisá si hubo "
            "capturas o eventos repetidos, y subí la duración del turno o bajá el límite de "
            "fuentes por vuelta."
        )


@contextlib.contextmanager
def arrendar(
    engine: Engine,
    recurso: str,
    *,
    duracion: dt.timedelta = DURACION_POR_OMISION,
    titular: str | None = None,
) -> Iterator[Turno]:
    """Pide el turno sobre `recurso` y lo suelta al salir.

    Entrega siempre un `Turno`, incluso cuando no lo consiguió: quien llama
    decide qué hacer con eso. No conseguirlo no es un error —es la respuesta
    correcta a dos disparos simultáneos— y por eso no levanta excepción.

    La conexión va en AUTOCOMMIT y es propia: separada de la del trabajo, para
    que el turno quede tomado desde el momento en que se toma y no cuando el
    trabajo confirma, y para que siga tomado si el trabajo revierte.
    """
    turno = Turno()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conexion:
        arrendador = Arrendador(conexion, recurso, duracion=duracion, titular=titular)
        turno.tenencia = arrendador.tomar()
        if turno.tenencia is None:
            turno.ocupado_por = arrendador.quien_lo_tiene()
            yield turno
            return
        try:
            yield turno
        finally:
            turno.se_paso = not arrendador.soltar()
