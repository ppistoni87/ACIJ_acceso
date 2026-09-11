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

    conexion = engine_pruebas.connect()
    conexion.execute(text(f"SET ROLE {ROL_DE_PRODUCCION}"))

    app = crear_app()
    app.dependency_overrides[conexion_lectura] = lambda: conexion
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
