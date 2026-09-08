"""Entrega de eventos del outbox.

Crear un evento no es entregarlo. `entregado_en` solo se completa cuando un
consumidor responde que lo recibió; hasta entonces el evento sigue pendiente y
la cantidad de intentos queda registrada.

Web Push ciudadano no está supuesto. Esto entrega a un webhook configurado; si
no hay ninguno, los eventos se acumulan y el reporte lo dice, en vez de
declarar entregas que no ocurrieron.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field

import httpx
from sqlalchemy import Connection, text

from backend_normativo.config import get_settings

VARIABLE_CONSUMIDOR = "BN_OUTBOX_WEBHOOK"

# Un evento que falló muchas veces deja de reintentarse solo: pasa a ser trabajo
# de operación en vez de ruido en cada corrida.
INTENTOS_MAXIMOS = 8


@dataclass
class ResultadoEntrega:
    pendientes: int = 0
    entregados: int = 0
    fallidos: int = 0
    en_cola_de_fallos: int = 0
    consumidor: str | None = None
    avisos: list[str] = field(default_factory=list)


def entregar_pendientes(
    conexion: Connection, *, limite: int = 50, cliente: httpx.Client | None = None
) -> ResultadoEntrega:
    resultado = ResultadoEntrega(consumidor=os.environ.get(VARIABLE_CONSUMIDOR) or None)

    resultado.pendientes = conexion.execute(
        text("SELECT count(*) FROM eventos_outbox WHERE entregado_en IS NULL")
    ).scalar_one()
    resultado.en_cola_de_fallos = conexion.execute(
        text(
            "SELECT count(*) FROM eventos_outbox  WHERE entregado_en IS NULL AND intentos >= :max"
        ),
        {"max": INTENTOS_MAXIMOS},
    ).scalar_one()

    if not resultado.consumidor:
        resultado.avisos.append(
            f"No hay consumidor configurado en {VARIABLE_CONSUMIDOR}: "
            f"{resultado.pendientes} evento(s) quedan pendientes. No se declara ninguna "
            "entrega."
        )
        return resultado

    eventos = (
        conexion.execute(
            text(
                "SELECT id, tipo, aggregate_id, payload, idempotency_key, intentos "
                "  FROM eventos_outbox "
                " WHERE entregado_en IS NULL AND intentos < :max "
                " ORDER BY creado_en LIMIT :limite"
            ),
            {"max": INTENTOS_MAXIMOS, "limite": limite},
        )
        .mappings()
        .all()
    )

    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=get_settings().http_timeout_s)
    try:
        for evento in eventos:
            entregado, detalle = _entregar(cliente, resultado.consumidor, dict(evento))
            if entregado:
                conexion.execute(
                    text(
                        "UPDATE eventos_outbox SET entregado_en = :ahora, "
                        "  intentos = intentos + 1, ultimo_error = NULL WHERE id = :id"
                    ),
                    {"ahora": dt.datetime.now(dt.UTC), "id": evento["id"]},
                )
                resultado.entregados += 1
            else:
                conexion.execute(
                    text(
                        "UPDATE eventos_outbox SET intentos = intentos + 1, "
                        "  ultimo_error = :error WHERE id = :id"
                    ),
                    {"error": detalle, "id": evento["id"]},
                )
                resultado.fallidos += 1
    finally:
        if propio:
            cliente.close()

    return resultado


def _entregar(cliente: httpx.Client, destino: str, evento: dict) -> tuple[bool, str | None]:
    """Entrega un evento. El consumidor tiene que ser idempotente.

    La clave de idempotencia viaja en una cabecera para que el consumidor pueda
    descartar duplicados: la entrega es al menos una vez, no exactamente una.
    """
    try:
        respuesta = cliente.post(
            destino,
            json={
                "tipo": evento["tipo"],
                "aggregate_id": evento["aggregate_id"],
                "payload": evento["payload"],
            },
            headers={"Idempotency-Key": evento["idempotency_key"]},
        )
    except httpx.HTTPError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if respuesta.status_code >= 300:
        return False, f"HTTP {respuesta.status_code}"
    return True, None
