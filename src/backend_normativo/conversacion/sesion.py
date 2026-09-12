"""El estado mínimo de una conversación (P-025) y su caducidad (P-037).

Tres reglas gobiernan este módulo y las tres están puestas para que no se pueda
mentir sobre lo que la persona dijo:

* **Ausencia no es falso.** Un hecho que no está es DESCONOCIDO. Un hecho que la
  persona eligió no contestar queda `rehusado`, que tampoco es falso. El motor
  de reglas ya distingue los tres estados; lo que faltaba era que el estado de
  la conversación no los aplastara en dos.
* **El último dato confirmado reemplaza al anterior e invalida lo que dependía
  de él.** Cada corrección sube `version`. Una respuesta lleva la versión con la
  que se calculó, y cualquiera anterior queda marcada como reemplazada en vez de
  convivir con la nueva en la misma pantalla.
* **Todo caduca.** Treinta minutos de inactividad, dos horas de vida como
  máximo. Una sesión vencida no se lee: es como si no existiera, y se borra.

No se guarda ningún mensaje. La base lo hace cumplir con un `CHECK` sobre las
claves de `estado`, y no un comentario: si alguien quisiera guardar el historial
tendría que cambiar la migración, que es exactamente la conversación que hay que
tener antes de hacerlo.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# Los dos plazos de P-037, criterio 1. Van acá y no en una variable de entorno:
# son una promesa que la pantalla le hace a la persona, no un parámetro de
# despliegue que alguien pueda subir sin que nadie se entere.
INACTIVIDAD = dt.timedelta(minutes=30)
VIDA_MAXIMA = dt.timedelta(hours=2)

# Lo que una conversación puede recordar. El mismo conjunto que el CHECK.
CLAVES = ("intencion", "jurisdiccion", "fecha", "hechos", "version")

ORIGENES = ("declarado", "inferido")


class SesionInvalida(Exception):
    """Lo pedido no se puede guardar sin dejar el estado en algo que no es."""


@dataclass(frozen=True)
class Sesion:
    id: uuid.UUID
    creada_en: dt.datetime
    ultima_actividad_en: dt.datetime
    estado: dict = field(default_factory=dict)

    @property
    def version(self) -> int:
        return int(self.estado.get("version", 0))

    @property
    def hechos(self) -> dict:
        return dict(self.estado.get("hechos") or {})

    def vence_en(self) -> dt.datetime:
        """Lo que pase primero: la inactividad o el techo de vida."""
        return min(self.ultima_actividad_en + INACTIVIDAD, self.creada_en + VIDA_MAXIMA)

    def vencida(self, ahora: dt.datetime | None = None) -> bool:
        return (ahora or dt.datetime.now(dt.UTC)) >= self.vence_en()

    def a_dict(self) -> dict:
        """Lo que el frente necesita. El identificador ya lo tiene quien pregunta."""
        return {
            "sesion_id": str(self.id),
            "vence_en": self.vence_en().isoformat(),
            "version": self.version,
            "intencion": self.estado.get("intencion"),
            "jurisdiccion": self.estado.get("jurisdiccion"),
            "fecha": self.estado.get("fecha"),
            "hechos": self.hechos,
        }


def _fila_a_sesion(fila) -> Sesion:
    return Sesion(
        id=fila["id"],
        creada_en=fila["creada_en"],
        ultima_actividad_en=fila["ultima_actividad_en"],
        estado=dict(fila["estado"] or {}),
    )


def abrir(conexion: Connection) -> Sesion:
    """Una conversación nueva, sin nada adentro."""
    fila = (
        conexion.execute(
            text(
                "INSERT INTO sesiones_conversacion (estado) VALUES ('{\"version\": 0}'::jsonb) "
                "RETURNING id, creada_en, ultima_actividad_en, estado"
            )
        )
        .mappings()
        .one()
    )
    return _fila_a_sesion(fila)


def leer(conexion: Connection, sesion_id: uuid.UUID, *, ahora: dt.datetime | None = None):
    """La sesión, o `None` si venció.

    Una sesión vencida no se devuelve ni se resucita: se borra ahí mismo. Dejarla
    disponible «un ratito más» convierte un plazo en una sugerencia.
    """
    ahora = ahora or dt.datetime.now(dt.UTC)
    fila = (
        conexion.execute(
            text(
                "SELECT id, creada_en, ultima_actividad_en, estado "
                "  FROM sesiones_conversacion WHERE id = :id"
            ),
            {"id": sesion_id},
        )
        .mappings()
        .one_or_none()
    )
    if fila is None:
        return None
    sesion = _fila_a_sesion(fila)
    if sesion.vencida(ahora):
        borrar(conexion, sesion_id)
        return None
    return sesion


def tocar(conexion: Connection, sesion_id: uuid.UUID, *, ahora: dt.datetime | None = None):
    """Marca actividad. Corre la inactividad, nunca el techo de las dos horas."""
    sesion = leer(conexion, sesion_id, ahora=ahora)
    if sesion is None:
        return None
    conexion.execute(
        text("UPDATE sesiones_conversacion SET ultima_actividad_en = :a WHERE id = :id"),
        {"a": ahora or dt.datetime.now(dt.UTC), "id": sesion_id},
    )
    return leer(conexion, sesion_id, ahora=ahora)


def _validar(clave: str, valor, origen: str, rehusado: bool) -> None:
    if not clave or not clave.replace("_", "").isalnum():
        raise SesionInvalida(
            f"«{clave}» no parece el nombre de un hecho. Son los que las reglas piden, "
            "en minúsculas y con guiones bajos."
        )
    if origen not in ORIGENES:
        raise SesionInvalida(
            f"El origen «{origen}» no existe. Un hecho lo declaró la persona o lo infirió "
            "el sistema, y la diferencia importa: lo inferido no se muestra como dicho."
        )
    if rehusado and valor is not None:
        raise SesionInvalida(
            "Un hecho rehusado no lleva valor. Rehusar es no contestar, no contestar que no."
        )


def confirmar(
    conexion: Connection,
    sesion_id: uuid.UUID,
    *,
    clave: str,
    valor=None,
    origen: str = "declarado",
    rehusado: bool = False,
    ahora: dt.datetime | None = None,
):
    """Guarda un hecho confirmado y sube la versión del estado.

    Reemplaza el anterior: la última corrección es la que vale. Subir la versión
    es lo que permite marcar como reemplazada cualquier respuesta que se hubiera
    calculado con el dato viejo, en vez de dejar dos conclusiones distintas
    conviviendo.
    """
    _validar(clave, valor, origen, rehusado)
    ahora = ahora or dt.datetime.now(dt.UTC)
    sesion = leer(conexion, sesion_id, ahora=ahora)
    if sesion is None:
        return None

    hecho = {"en": ahora.isoformat()}
    if rehusado:
        hecho["rehusado"] = True
    else:
        hecho["valor"] = valor
        hecho["origen"] = origen

    hechos = sesion.hechos
    hechos[clave] = hecho
    estado = dict(sesion.estado)
    estado["hechos"] = hechos
    estado["version"] = sesion.version + 1
    return _guardar(conexion, sesion_id, estado, ahora)


def olvidar(conexion: Connection, sesion_id: uuid.UUID, *, clave: str, ahora=None):
    """Saca un hecho. Vuelve a DESCONOCIDO, que no es lo mismo que falso."""
    ahora = ahora or dt.datetime.now(dt.UTC)
    sesion = leer(conexion, sesion_id, ahora=ahora)
    if sesion is None:
        return None
    hechos = sesion.hechos
    if clave not in hechos:
        return sesion
    hechos.pop(clave)
    estado = dict(sesion.estado)
    estado["hechos"] = hechos
    estado["version"] = sesion.version + 1
    return _guardar(conexion, sesion_id, estado, ahora)


def anotar_contexto(
    conexion: Connection,
    sesion_id: uuid.UUID,
    *,
    intencion: str | None = None,
    jurisdiccion: str | None = None,
    fecha: str | None = None,
    ahora: dt.datetime | None = None,
):
    """Intención, jurisdicción y fecha: lo que acota la orientación."""
    ahora = ahora or dt.datetime.now(dt.UTC)
    sesion = leer(conexion, sesion_id, ahora=ahora)
    if sesion is None:
        return None
    estado = dict(sesion.estado)
    cambios = {"intencion": intencion, "jurisdiccion": jurisdiccion, "fecha": fecha}
    if all(valor is None for valor in cambios.values()):
        return sesion
    for campo, valor in cambios.items():
        if valor is not None:
            estado[campo] = valor
    estado["version"] = sesion.version + 1
    return _guardar(conexion, sesion_id, estado, ahora)


def _guardar(conexion: Connection, sesion_id: uuid.UUID, estado: dict, ahora: dt.datetime):
    import json

    sobrantes = set(estado) - set(CLAVES)
    if sobrantes:
        # La base también lo rechaza; acá el mensaje explica por qué.
        raise SesionInvalida(
            f"El estado de una conversación no guarda {sorted(sobrantes)}. Guarda intención, "
            "jurisdicción, fecha y hechos confirmados: agregarle el texto la convierte en un "
            "historial, que es otra cosa y tiene otra política de retención."
        )
    fila = (
        conexion.execute(
            text(
                "UPDATE sesiones_conversacion "
                "   SET estado = CAST(:e AS jsonb), ultima_actividad_en = :a "
                " WHERE id = :id RETURNING id, creada_en, ultima_actividad_en, estado"
            ),
            {"e": json.dumps(estado, ensure_ascii=False), "a": ahora, "id": sesion_id},
        )
        .mappings()
        .one()
    )
    return _fila_a_sesion(fila)


def borrar(conexion: Connection, sesion_id: uuid.UUID) -> bool:
    """Lo que la persona pide cuando aprieta «borrar conversación»."""
    resultado = conexion.execute(
        text("DELETE FROM sesiones_conversacion WHERE id = :id"), {"id": sesion_id}
    )
    return bool(resultado.rowcount)


def purgar(conexion: Connection, *, ahora: dt.datetime | None = None) -> int:
    """Borra las vencidas. Que `leer` también las borre no alcanza.

    Una sesión que nadie vuelve a mirar no se borraría nunca sola, y quedaría
    en la base con los hechos de alguien mucho más allá del plazo que la
    pantalla prometió.
    """
    ahora = ahora or dt.datetime.now(dt.UTC)
    resultado = conexion.execute(
        text(
            "DELETE FROM sesiones_conversacion "
            " WHERE ultima_actividad_en <= :inactivas OR creada_en <= :viejas"
        ),
        {"inactivas": ahora - INACTIVIDAD, "viejas": ahora - VIDA_MAXIMA},
    )
    return resultado.rowcount or 0
