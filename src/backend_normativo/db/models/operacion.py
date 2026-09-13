"""Tablas de operación: conversación, credenciales revocadas y arrendamientos.

No son corpus ni proyecciones: son el estado que necesita el sistema para
funcionar. Están acá y no en `operativo.py`, que es la puerta de atención al
público —trámites, sedes, canales—: una sesión de conversación y un
arrendamiento de corrida no tienen nada que ver con eso.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend_normativo.db.base import Base, pk_uuid, ts_creacion


class SesionConversacion(Base):
    """El estado mínimo de una conversación. **Ningún mensaje.**

    El `CHECK` sobre las claves de `estado` no es una convención: es lo que
    impide que alguien agregue el texto de la conversación sin decidirlo.
    Guardar el historial exige cambiar la migración, que es la conversación que
    hay que tener antes de hacerlo.
    """

    __tablename__ = "sesiones_conversacion"

    id: Mapped[uuid.UUID] = pk_uuid()
    creada_en: Mapped[dt.datetime] = ts_creacion()
    ultima_actividad_en: Mapped[dt.datetime] = ts_creacion()
    estado: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment=(
            "hechos = {clave: {valor, origen, en}} o {clave: {rehusado: true, en}}. La "
            "ausencia de una clave es DESCONOCIDO y nunca se lee como falso; rehusado "
            "dice que la persona eligió no contestar, que tampoco es falso."
        ),
    )

    __table_args__ = (
        CheckConstraint(
            "(estado - ARRAY['intencion', 'jurisdiccion', 'fecha', 'hechos', 'version']) "
            "= '{}'::jsonb",
            name="solo_estado_estructurado",
        ),
        Index("ix_sesiones_actividad", "ultima_actividad_en"),
        Index("ix_sesiones_creada", "creada_en"),
        {
            "comment": (
                "Estado mínimo de una conversación: intención, jurisdicción, fecha y "
                "hechos confirmados con su procedencia. No guarda mensajes ni identidad, "
                "caduca a los 30 minutos de inactividad y vive dos horas como máximo. El "
                "CHECK sobre las claves impide que alguien agregue el texto de la "
                "conversación sin decidirlo: sería convertir esto en un historial, que es "
                "otra cosa y tiene otra política."
            )
        },
    )


class CredencialRevocada(Base):
    """Una credencial que dejó de valer, con quién la revocó y por qué.

    Es inmutable por disparador: una revocación que se pueda borrar no es una
    revocación.
    """

    __tablename__ = "credenciales_revocadas"

    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    revocada_por: Mapped[str] = mapped_column(Text, nullable=False)
    revocada_en: Mapped[dt.datetime] = ts_creacion()

    __table_args__ = (
        {
            "comment": (
                "Credenciales que dejaron de valer antes de su vencimiento. No se "
                "borran: que una credencial haya sido revocada es parte de la historia "
                "de quién pudo hacer qué y cuándo dejó de poder."
            )
        },
    )


class Arrendamiento(Base):
    """Quién tiene tomado un recurso y hasta cuándo.

    El vencimiento libera el recurso aunque el titular siga vivo: una corrida
    que se pasa de su arrendamiento se entera al soltarlo y lo declara, porque
    otra pudo haber empezado en paralelo.
    """

    __tablename__ = "arrendamientos"

    recurso: Mapped[str] = mapped_column(String(64), primary_key=True)
    titular: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment=(
            "Quién lo tomó: máquina, proceso y un identificador de corrida. Sirve para "
            "saber qué instancia quedó colgada cuando un arrendamiento no se soltó."
        ),
    )
    tomado_en: Mapped[dt.datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    vence_en: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment=(
            "Tope máximo de la corrida. Pasado esto el recurso queda libre aunque el "
            "titular siga vivo: una corrida que se pasa de su arrendamiento se entera al "
            "soltarlo y lo declara, porque otra pudo haber empezado en paralelo."
        ),
    )
    corridas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __table_args__ = (
        CheckConstraint("corridas > 0", name="corridas_positivas"),
        CheckConstraint("vence_en >= tomado_en", name="vence_despues_de_tomarse"),
        {
            "comment": (
                "Derecho de uso exclusivo con vencimiento sobre un recurso que no admite "
                "dos procesos a la vez. La fila sobrevive al fin de la corrida como "
                "constancia."
            )
        },
    )
