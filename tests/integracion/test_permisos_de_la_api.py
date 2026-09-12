"""Cada endpoint público, con los permisos que va a tener en producción.

Las demás pruebas de API sustituyen `conexion_lectura` por la conexión del caso,
que es de superusuario: ven todo y por eso no pueden notar que una ruta lee una
tabla que el lector no alcanza. Así pasó `GET /v1/cobertura`, que consultaba
`capturas` y devolvía 500 en cuanto se desplegaba con roles de verdad —1.124
pruebas en verde y el defecto apareció al levantar el servicio a mano—.

Acá la conexión de lectura hace `SET ROLE bn_lector_api`, que es exactamente lo
que el despliegue usa. No se prepara corpus: lo que se mira no son los datos
sino que ninguna ruta se caiga por permisos. Un 200 vacío está bien; un 500 no.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Engine, text

pytestmark = pytest.mark.integracion

ROL_DE_PRODUCCION = "bn_lector_api"

# Rutas con parámetro: se les pasa un identificador que no existe. La respuesta
# correcta es 404, y lo que importa es que llegue a decidirlo en vez de romper.
INEXISTENTE = str(uuid.uuid4())


@pytest.fixture
def cliente_con_permisos_de_produccion(engine_pruebas: Engine):
    from fastapi.testclient import TestClient

    from backend_normativo.api.app import crear_app
    from backend_normativo.api.dependencias import conexion_lectura
    from backend_normativo.api.routers.devoluciones import conexion_devolucion
    from backend_normativo.api.routers.sesiones import conexion_sesion

    conexion = engine_pruebas.connect()
    conexion.execute(text(f"SET ROLE {ROL_DE_PRODUCCION}"))

    app = crear_app()
    app.dependency_overrides[conexion_lectura] = lambda: conexion
    # La escritura de la devolución también va con el rol de producción: si
    # faltara el GRANT, el frente ciudadano recibiría 500 al agradecer.
    app.dependency_overrides[conexion_devolucion] = lambda: conexion
    app.dependency_overrides[conexion_sesion] = lambda: conexion
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        conexion.close()


def _rutas_publicas() -> list[str]:
    """Los GET de `/v1` que no son de administración."""
    from backend_normativo.api.app import crear_app

    # Del contrato OpenAPI y no de `app.routes`: los routers se montan de forma
    # que varias rutas quedan sin `path` en esa lista, y una lista vacía haría
    # que esta prueba pasara sin comprobar nada.
    esquema = crear_app().openapi()
    rutas = [
        camino
        for camino, operaciones in esquema["paths"].items()
        if "get" in operaciones and camino.startswith("/v1") and "/admin/" not in camino
    ]
    assert rutas, "No se encontró ninguna ruta pública: la prueba estaría vacía."
    return sorted(rutas)


def _rutas_publicas_post() -> list[str]:
    """Los POST de `/v1` que no son de administración.

    Esta mitad faltaba, y por el hueco pasó un defecto real: la recuperación
    híbrida hacía `JOIN` contra `capturas` para traer la URL de la fuente, y el
    lector no puede leer esa tabla. `POST /v1/recuperacion` devolvía 500 en
    cualquier despliegue con roles de verdad, igual que la cobertura en D-86, y
    una prueba que sólo mira GET no lo podía ver.
    """
    from backend_normativo.api.app import crear_app

    esquema = crear_app().openapi()
    rutas = [
        camino
        for camino, operaciones in esquema["paths"].items()
        if "post" in operaciones and camino.startswith("/v1") and "/admin/" not in camino
    ]
    assert rutas, "No se encontró ninguna ruta POST pública: la prueba estaría vacía."
    return sorted(rutas)


@pytest.mark.parametrize("camino", _rutas_publicas())
def test_ninguna_ruta_publica_se_cae_por_permisos(
    cliente_con_permisos_de_produccion, camino: str
) -> None:
    """Un 500 acá significa que la ruta toca algo que el lector no puede leer.

    El lector accede únicamente a proyecciones servibles: si una ruta necesita
    staging, el problema no es el permiso que falta sino la ruta, y la salida es
    pedir el rol que corresponda —como se hizo con la cobertura— y no ampliar lo
    que el lector alcanza.
    """
    respuesta = cliente_con_permisos_de_produccion.get(camino.format(**_parametros(camino)))
    assert respuesta.status_code != 500, (
        f"{camino} devolvió 500 con los permisos de producción: {respuesta.text[:300]}"
    )


def _parametros(camino: str) -> dict[str, str]:
    return {
        nombre.strip("{}"): INEXISTENTE
        for nombre in camino.split("/")
        if nombre.startswith("{") and nombre.endswith("}")
    }


@pytest.mark.parametrize("camino", _rutas_publicas_post())
def test_ningun_post_publico_se_cae_por_permisos(
    cliente_con_permisos_de_produccion, camino: str
) -> None:
    """Un cuerpo vacío basta: lo que se mira es que no reviente por permisos.

    Un 422 por validación está perfecto —significa que la ruta llegó a mirar el
    cuerpo— y un 500 no.
    """
    respuesta = cliente_con_permisos_de_produccion.post(
        camino.format(**_parametros(camino)), json={"consulta": "vivienda"}
    )
    assert respuesta.status_code != 500, (
        f"{camino} devolvió 500 con los permisos de producción: {respuesta.text[:300]}"
    )


# --- Las consultas de recuperación, contra los permisos reales ----------------
#
# La prueba de POST de arriba no alcanza para esto: sin release publicado la
# ruta corta antes de ejecutar el SQL, así que pasaba con el defecto puesto.
# `EXPLAIN` resuelve el problema: verifica los permisos de cada tabla sin
# necesitar una sola fila de datos.


@pytest.mark.parametrize("nombre", ["CONSULTA", "SOLO_LEXICA"])
def test_las_consultas_de_recuperacion_no_tocan_staging(
    engine_pruebas: Engine, nombre: str
) -> None:
    """El lector accede únicamente a proyecciones servibles.

    La recuperación híbrida hacía `JOIN` contra `capturas` y `fuente_urls` para
    traer la URL de la fuente. Las dos son staging y el lector no las alcanza,
    así que `POST /v1/recuperacion` devolvía 500 en cualquier despliegue con
    roles de verdad. Se quitó el join: la cita identifica norma y ruta, que sí
    son del corpus publicado.
    """
    from backend_normativo.recuperacion import busqueda

    consulta = getattr(busqueda, nombre)
    parametros = {
        "consulta": "vivienda",
        "release": uuid.uuid4(),
        "limite": 5,
        "jurisdiccion": None,
        "beneficio": None,
        "as_of": "2026-01-01",
        "known_at": "2026-01-01T00:00:00+00:00",
        "k": 60,
        "vector": None,
    }
    conexion = engine_pruebas.connect()
    try:
        conexion.execute(text(f"SET ROLE {ROL_DE_PRODUCCION}"))
        try:
            conexion.execute(text(f"EXPLAIN {consulta}"), parametros)
        except Exception as error:
            if "permission denied" in str(error).lower():
                pytest.fail(f"{nombre} toca una tabla que el lector no puede leer: {error}")
            # Otros errores —un parámetro que no aplica a esta variante— no son
            # lo que esta prueba mira.
    finally:
        conexion.close()


def test_la_devolucion_se_puede_escribir_con_el_rol_de_produccion(
    cliente_con_permisos_de_produccion,
) -> None:
    """El GRANT de `devoluciones`, ejercido y no supuesto.

    La prueba de POST de arriba manda `{"consulta": ...}` a todas las rutas y
    esta contesta 422 antes de tocar la base, así que pasaría igual sin el
    permiso. Es el mismo hueco por el que se coló la cobertura en D-86: una
    prueba que verifica que no hay 500 sin llegar nunca a ejecutar el SQL.
    """
    respuesta = cliente_con_permisos_de_produccion.post(
        "/v1/devoluciones",
        json={"request_id": "permiso-de-produccion", "senal": "NO_SIRVIO"},
    )
    assert respuesta.status_code == 202, respuesta.text
    assert respuesta.json()["registrada"] is True
