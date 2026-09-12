"""La otra mitad de la conversación: qué contesta la persona (P-015).

El sistema medía todo de sí mismo y nada de si a alguien le sirvió. Estas
pruebas cubren la señal que cierra el ciclo y, sobre todo, los dos límites que
la hacen aceptable: que no entra texto libre y que no se puede inflar.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.api.devoluciones import Senal, borrar_anteriores, registrar, resumen
from backend_normativo.api.observabilidad import Anotacion, purgar
from backend_normativo.api.observabilidad import registrar as registrar_traza

pytestmark = pytest.mark.integracion


# Lo que la tabla puede guardar, escrito acá para que agregar una columna sea
# una decisión y no un descuido. Es el mismo guardián que `COLUMNAS_DE_LA_TRAZA`
# y existe por la misma razón, sólo que acá el riesgo tiene nombre propio: una
# columna `comentario` debajo de una respuesta sobre desalojos es donde alguien
# escribe su caso completo, y ninguna política escrita en un documento lo
# impide.
COLUMNAS_DE_LA_DEVOLUCION = {"id", "request_id", "senal", "ocurrido_en"}


def _columnas(conexion: Connection) -> set[str]:
    return {
        fila[0]
        for fila in conexion.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                " WHERE table_name = 'devoluciones'"
            )
        ).all()
    }


def test_la_tabla_no_tiene_donde_guardar_un_relato(conexion: Connection) -> None:
    assert _columnas(conexion) == COLUMNAS_DE_LA_DEVOLUCION


def test_se_registra_la_senal(conexion: Connection) -> None:
    assert registrar(conexion, request_id="r-1", senal=Senal.SIRVIO) is True
    fila = (
        conexion.execute(
            text("SELECT request_id, senal FROM devoluciones WHERE request_id = 'r-1'")
        )
        .mappings()
        .one()
    )
    assert fila["senal"] == "SIRVIO"


def test_apretar_dos_veces_no_cuenta_dos_veces(conexion: Connection) -> None:
    """Una tasa de satisfacción que se puede inflar con el clic no mide nada."""
    assert registrar(conexion, request_id="r-2", senal=Senal.SIRVIO) is True
    assert registrar(conexion, request_id="r-2", senal=Senal.SIRVIO) is False
    cuantas = conexion.execute(
        text("SELECT count(*) FROM devoluciones WHERE request_id = 'r-2'")
    ).scalar_one()
    assert cuantas == 1


def test_cambiar_de_opinion_deja_las_dos_senales(conexion: Connection) -> None:
    """No se corrige una devolución: se agrega otra.

    Que convivan «no me sirvió» y «quiero hablar con una persona» sobre la misma
    respuesta no es una contradicción; es la secuencia más informativa que hay.
    """
    registrar(conexion, request_id="r-3", senal=Senal.NO_SIRVIO)
    registrar(conexion, request_id="r-3", senal=Senal.QUIERE_PERSONA)
    senales = {
        fila[0]
        for fila in conexion.execute(
            text("SELECT senal FROM devoluciones WHERE request_id = 'r-3'")
        ).all()
    }
    assert senales == {"NO_SIRVIO", "QUIERE_PERSONA"}


def test_la_base_rechaza_una_senal_inventada(conexion: Connection) -> None:
    """El vocabulario cerrado se hace cumplir en la base, no en el cliente."""
    with pytest.raises(Exception, match=r"(?i)ck_devoluciones_senal|check"):
        conexion.execute(
            text("INSERT INTO devoluciones (request_id, senal) VALUES ('r-4', 'MAS O MENOS')")
        )
    conexion.execute(text("ROLLBACK"))


def test_el_resumen_dice_contra_cuantas_consultas(conexion: Connection) -> None:
    """Sin denominador, «el 80 % dijo que sirvió» no es un dato.

    Cuatro de cinco y cuatro de mil son hallazgos distintos: el segundo dice que
    el mecanismo de devolución no se está usando, que también hay que saberlo.
    """
    for numero in range(5):
        registrar_traza(
            conexion,
            Anotacion(
                request_id=f"c-{numero}",
                ruta="/v1/respuestas",
                resultado="SIN_RESULTADOS",
                latencia_ms=3,
                motivo="INSUFFICIENT_EVIDENCE",
            ),
        )
    registrar(conexion, request_id="c-0", senal=Senal.NO_SIRVIO)
    registrar(conexion, request_id="c-1", senal=Senal.NO_SIRVIO)

    medido = resumen(conexion, desde_horas=24)
    assert medido["devoluciones"] == 2
    assert medido["consultas"] >= 5
    assert medido["por_senal"]["NO_SIRVIO"] == 2
    assert medido["por_senal"]["SIRVIO"] == 0
    # Y lo que hace accionable el «no me sirvió»: con qué clase de respuesta se
    # encontró. Acá, con abstenciones por falta de evidencia: el problema está
    # en el corpus y no en cómo está redactada la respuesta.
    contra_abstenciones = [
        fila
        for fila in medido["por_resultado"]
        if fila["senal"] == "NO_SIRVIO" and fila["resultado"] == "SIN_RESULTADOS"
    ]
    assert contra_abstenciones and contra_abstenciones[0]["motivo"] == "INSUFFICIENT_EVIDENCE"
    assert contra_abstenciones[0]["cuantas"] == 2


def test_una_devolucion_sin_traza_no_se_pierde_ni_se_inventa(conexion: Connection) -> None:
    """Si no hay traza que le corresponda, se cuenta y se dice que no la hay."""
    registrar(conexion, request_id="sin-traza", senal=Senal.SIRVIO)
    medido = resumen(conexion, desde_horas=24)
    assert any(
        fila["resultado"] == "SIN_TRAZA" and fila["senal"] == "SIRVIO"
        for fila in medido["por_resultado"]
    )


def _envejecer(conexion: Connection, rid: str, dias: int) -> None:
    conexion.execute(
        text(
            "UPDATE devoluciones SET ocurrido_en = now() - make_interval(days => :d) "
            " WHERE request_id = :r"
        ),
        {"d": dias, "r": rid},
    )


def test_la_devolucion_caduca_con_la_traza(conexion: Connection) -> None:
    """Una señal suelta, sin la consulta a la que se refería, ya no se interpreta."""
    registrar(conexion, request_id="vieja-devolucion", senal=Senal.SIRVIO)
    _envejecer(conexion, "vieja-devolucion", 200)
    registrar(conexion, request_id="nueva-devolucion", senal=Senal.SIRVIO)

    resultado = purgar(conexion, dias=90)
    assert resultado.devoluciones_borradas >= 1
    quedan = {
        fila[0]
        for fila in conexion.execute(
            text(
                "SELECT request_id FROM devoluciones "
                " WHERE request_id IN ('vieja-devolucion', 'nueva-devolucion')"
            )
        ).all()
    }
    assert quedan == {"nueva-devolucion"}


def test_simular_no_borra_devoluciones(conexion: Connection) -> None:
    registrar(conexion, request_id="simulada", senal=Senal.SIRVIO)
    _envejecer(conexion, "simulada", 200)
    resultado = purgar(conexion, dias=90, simular=True)
    assert resultado.devoluciones_candidatas >= 1
    assert resultado.devoluciones_borradas == 0
    assert borrar_anteriores(conexion, dias=90, simular=True) >= 1, (
        "la simulación no puede haber borrado nada"
    )


# --- La ruta -----------------------------------------------------------------


def test_la_ruta_registra_y_acusa(cliente_api, conexion: Connection) -> None:
    respuesta = cliente_api.post(
        "/v1/devoluciones", json={"request_id": "por-la-ruta", "senal": "SIRVIO"}
    )
    assert respuesta.status_code == 202, respuesta.text
    assert respuesta.json() == {"registrada": True, "senal": "SIRVIO"}
    assert (
        conexion.execute(
            text("SELECT count(*) FROM devoluciones WHERE request_id = 'por-la-ruta'")
        ).scalar_one()
        == 1
    )


def test_la_ruta_no_acepta_un_comentario(cliente_api) -> None:
    """Es la prueba de la decisión, no de la validación.

    Si alguna vez esto pasa a 202, alguien habilitó texto libre debajo de una
    respuesta sobre desalojos o pensiones. Que falle acá obliga a que esa
    decisión se tome mirándola.
    """
    respuesta = cliente_api.post(
        "/v1/devoluciones",
        json={
            "request_id": "con-relato",
            "senal": "NO_SIRVIO",
            "comentario": "me llamo X y me quieren echar de mi casa en la calle Y",
        },
    )
    assert respuesta.status_code == 422


def test_la_ruta_rechaza_una_senal_inventada(cliente_api) -> None:
    respuesta = cliente_api.post(
        "/v1/devoluciones", json={"request_id": "r", "senal": "MAS O MENOS"}
    )
    assert respuesta.status_code == 422


def test_la_ruta_exige_a_que_respuesta_se_refiere(cliente_api) -> None:
    """Sin `request_id` la señal no se puede cruzar con nada y no sirve."""
    assert cliente_api.post("/v1/devoluciones", json={"senal": "SIRVIO"}).status_code == 422
    assert (
        cliente_api.post("/v1/devoluciones", json={"request_id": "", "senal": "SIRVIO"}).status_code
        == 422
    )


def test_la_respuesta_dice_a_que_consulta_pertenece(cliente_api) -> None:
    """El frente no puede devolver nada si la respuesta no viene identificada."""
    respuesta = cliente_api.post("/v1/respuestas", json={"consulta": "vivienda"})
    assert respuesta.headers.get("X-Request-Id")


def _trazas_de(ruta: str) -> int:
    from backend_normativo.db.session import engine_api

    with engine_api().begin() as conexion:
        return conexion.execute(
            text("SELECT count(*) FROM consultas_auditadas WHERE intencion = :r"), {"r": ruta}
        ).scalar_one()


def test_una_devolucion_no_infla_el_denominador(cliente_api) -> None:
    """La traza mide consultas. Contar los clics en «me sirvió» como consultas
    haría que la tasa de respuesta se midiera contra sí misma.

    Se verifica en la misma corrida que la traza de una consulta de verdad sí se
    escribe: sin eso, la prueba pasaría también si la medición estuviera muerta.
    """
    from backend_normativo.db.session import engine_api

    antes_consultas = _trazas_de("/v1/respuestas")
    antes_devoluciones = _trazas_de("/v1/devoluciones")

    respuesta = cliente_api.post("/v1/respuestas", json={"consulta": "vivienda"})
    cliente_api.post(
        "/v1/devoluciones",
        json={"request_id": respuesta.headers["X-Request-Id"], "senal": "SIRVIO"},
    )

    try:
        assert _trazas_de("/v1/respuestas") == antes_consultas + 1, (
            "la traza de la consulta no se escribió: la prueba no estaría midiendo nada"
        )
        assert _trazas_de("/v1/devoluciones") == antes_devoluciones
    finally:
        # La traza se escribe en su propia transacción y no se revierte con el
        # caso. Se limpia lo que este dejó.
        with engine_api().begin() as conexion:
            conexion.execute(
                text("DELETE FROM consultas_auditadas WHERE request_id = :r"),
                {"r": respuesta.headers["X-Request-Id"]},
            )
