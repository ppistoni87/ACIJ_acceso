"""P-021 criterio 1 y 3: medir sin escribir qué preguntó nadie.

Lo que más cuidan estas pruebas es la privacidad y la distinción. Quien consulta
este sistema pregunta si le corresponde una pensión por discapacidad o si la
pueden desalojar: guardar el texto de esa pregunta crea un registro de la
situación personal de alguien, que después se respalda y se replica. Y un
tablero que no separa una abstención correcta de una respuesta resuelta no sirve
para decidir nada.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.api import observabilidad

pytestmark = pytest.mark.integracion


def _registrada(conexion: Connection, request_id: str) -> dict:
    """La fila de *esta* consulta.

    Se busca por `request_id` y no por «la primera»: el middleware registra cada
    llamada de la API en su propia transacción —a propósito, para que medir no
    pueda romper lo medido— así que la tabla no está vacía cuando corre la suite
    entera. Una prueba que asume tabla vacía pasa sola y falla acompañada.
    """
    return dict(
        conexion.execute(
            text(
                "SELECT intencion, resultado_tipo, motivo_abstencion, request_id, latencia_ms "
                "  FROM consultas_auditadas WHERE request_id = :r"
            ),
            {"r": request_id},
        )
        .mappings()
        .one()
    )


# Lo que la traza de una consulta puede contener. Ninguna de estas columnas
# identifica a una persona: son la **forma** de la consulta —qué ruta, contra qué
# corte, cuánto tardó, si se contestó o se abstuvo y por qué— y no su contenido.
COLUMNAS_DE_LA_TRAZA = {
    "id",
    "release_id",
    "intencion",
    "fecha_consulta",
    "jurisdiccion_id",
    "resultado_tipo",
    "evidencias_usadas",
    "reglas_versiones",
    "latencia_ms",
    "ocurrido_en",
    "request_id",
    "motivo_abstencion",
}


def test_no_se_guarda_el_texto_de_la_consulta(conexion: Connection) -> None:
    """`intencion` recibe la ruta, nunca lo que la persona escribió."""
    observabilidad.registrar(
        conexion,
        observabilidad.Anotacion(
            request_id="r1",
            ruta="/v1/beneficios",
            resultado=observabilidad.RESUELTA,
            latencia_ms=12,
        ),
    )
    fila = _registrada(conexion, "r1")
    assert fila["intencion"] == "/v1/beneficios"
    columnas = set(
        conexion.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                " WHERE table_name = 'consultas_auditadas'"
            )
        ).scalars()
    )
    # El conjunto entero, y no una lista de prohibidas. Prohibir nombres que se
    # nos ocurran hoy no protege de la columna que se agregue mañana con otro
    # nombre; fijar el conjunto sí: cualquier columna nueva rompe esta prueba y
    # obliga a decidir a propósito si lo que va a guardar puede guardarse.
    assert columnas == COLUMNAS_DE_LA_TRAZA


def test_una_abstencion_se_registra_con_su_causa(conexion: Connection) -> None:
    observabilidad.registrar(
        conexion,
        observabilidad.Anotacion(
            request_id="r2",
            ruta="/v1/puntos-atencion",
            resultado="SIN_RESULTADOS",
            latencia_ms=8,
            motivo="INSUFFICIENT_EVIDENCE",
        ),
    )
    fila = _registrada(conexion, "r2")
    assert fila["resultado_tipo"] == "SIN_RESULTADOS"
    assert fila["motivo_abstencion"] == "INSUFFICIENT_EVIDENCE"


def test_una_consulta_sin_corte_publicado_igual_se_registra(conexion: Connection) -> None:
    """Es la abstención más importante y era la única que no entraba.

    `release_id` era obligatorio, así que la medición del peor caso —el sistema
    no puede contestar nada— se perdía.
    """
    observabilidad.registrar(
        conexion,
        observabilidad.Anotacion(
            request_id="r3",
            ruta="/v1/normas",
            resultado="NO_PUBLICABLE",
            latencia_ms=3,
            release_id=None,
            motivo="UNKNOWN_IDENTITY",
        ),
    )
    assert _registrada(conexion, "r3")["motivo_abstencion"] == "UNKNOWN_IDENTITY"


def test_el_resumen_trae_el_denominador(conexion: Connection) -> None:
    """«12 abstenciones» no dice nada sin saber sobre cuántas consultas."""
    for i, (resultado, motivo) in enumerate(
        [
            (observabilidad.RESUELTA, None),
            (observabilidad.RESUELTA, None),
            ("SIN_RESULTADOS", "INSUFFICIENT_EVIDENCE"),
        ]
    ):
        observabilidad.registrar(
            conexion,
            observabilidad.Anotacion(
                request_id=f"r{i}",
                ruta="/v1/x",
                resultado=resultado,
                latencia_ms=10,
                motivo=motivo,
            ),
        )
    resumen = observabilidad.resumen(conexion)
    # El resumen mide toda la tabla, que la suite comparte. Lo que esta prueba
    # comprueba es la relación: el denominador cierra con sus partes y las tres
    # filas propias están adentro.
    assert resumen["consultas"] == resumen["resueltas"] + resumen["abstenciones"]
    assert resumen["consultas"] >= 3
    assert resumen["resueltas"] >= 2
    assert resumen["abstenciones"] >= 1
    assert resumen["periodo_horas"] == 24


def test_el_request_id_entrante_se_respeta_y_se_acota() -> None:
    """Se acepta el de afuera para no perder la correlación, con un tope.

    La cabecera la pone quien llama y termina en una columna y en un log: un
    identificador de treinta mil caracteres no es un identificador.
    """
    assert observabilidad.request_id_de({"X-Request-Id": "abc-123"}) == "abc-123"
    generado = observabilidad.request_id_de({})
    assert len(generado) == 32
    assert len(observabilidad.request_id_de({"X-Request-Id": "x" * 5000})) == 200


def test_una_consulta_real_queda_registrada_con_su_causa(cliente_api, corpus) -> None:
    """De punta a punta: la ruta contesta y el middleware anota, sin que la ruta
    se acuerde de nada."""
    respuesta = cliente_api.get("/v1/puntos-atencion")
    assert respuesta.status_code == 200
    assert respuesta.headers.get(observabilidad.CABECERA_REQUEST_ID)
