"""Aplicación FastAPI del backend normativo."""

from __future__ import annotations

import pathlib

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse

from backend_normativo import SCHEMA_VERSION, __version__
from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.api.routers import admin, evaluaciones, normas, operativo, recuperacion
from backend_normativo.api.sondas import verificar_abriendo
from backend_normativo.config import get_settings
from backend_normativo.db.session import engine_api

DESCRIPCION = """
API de consulta del corpus normativo de acceso a derechos.

Toda respuesta lleva la misma envoltura: `schema_version`, `release_id`,
`as_of`, `known_at`, `data_status`, `evidence`, `missing_fields` y `warnings`.
Sin `as_of` una respuesta no dice para cuándo vale; sin `release_id` no se puede
reproducir; sin `missing_fields` una abstención sería indistinguible de un "no".

Los errores son tipados. Información insuficiente es un estado de dominio y
nunca se disfraza de 500.

Esta API no otorga, no rechaza y no revoca prestaciones. Devuelve lo que dicen
las normas publicadas, con la evidencia que lo sostiene y lo que falta averiguar.
"""


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Backend normativo de acceso a derechos",
        version=__version__,
        description=DESCRIPCION,
        openapi_tags=[
            {"name": "normas", "description": "Identidad, versiones y siete campos."},
            {"name": "operativo", "description": "Beneficios, valores, plazos y atención."},
            {"name": "evaluación", "description": "Evaluación preliminar de aplicabilidad."},
            {"name": "recuperación", "description": "Fragmentos citables y cobertura."},
            {"name": "administración", "description": "Revisión y publicación."},
        ],
    )

    app.include_router(normas.router)
    app.include_router(operativo.router)
    app.include_router(evaluaciones.router)
    app.include_router(recuperacion.router)
    app.include_router(admin.router)

    # La consola de revisión se sirve desde la misma aplicación y en un solo
    # archivo, sin compilar nada. No es minimalismo: es que quien tiene que
    # firmar 166 reglas necesita una pantalla, no una cadena de herramientas, y
    # un artefacto que viaja en la misma imagen no puede quedar desfasado de la
    # API que consume. La credencial la pone quien entra y vive en su pestaña;
    # el servidor no la guarda ni la conoce hasta que llega en un pedido.
    @app.get("/backoffice/reglas", tags=["administración"], include_in_schema=False)
    def consola_de_reglas() -> HTMLResponse:
        return HTMLResponse(
            (pathlib.Path(__file__).parent / "backoffice" / "consola.html").read_text(
                encoding="utf-8"
            )
        )

    @app.get("/salud", tags=["operativo"])
    def salud() -> dict:
        """Liveness: si el proceso sigue en pie. No toca la base, a propósito.

        Si esta sonda dependiera de la base, una base momentáneamente
        inalcanzable reiniciaría procesos sanos y convertiría una caída parcial
        en una total. Para saber si la instancia puede **servir** está `/listo`.
        """
        return {"estado": "ok", "schema_version": SCHEMA_VERSION, "version": __version__}

    @app.get("/listo", tags=["operativo"])
    def listo(respuesta: Response) -> dict:
        """Readiness: si esta instancia puede contestar.

        Verifica conexión y que el esquema aplicado sea el que este código
        espera. En producción exige además un corte publicado: sin release la
        API contesta abstenciones correctas y vacías, lo que está bien en
        desarrollo y no está bien recibiendo gente que pregunta por sus
        derechos.

        Devuelve 503 cuando no está lista, que es lo que un orquestador lee para
        no mandarle tráfico. El cuerpo dice cuál verificación falló: una sonda
        que solo dice «no» obliga a entrar al contenedor a averiguar por qué.
        """
        estado = verificar_abriendo(lambda: engine_api().connect(), entorno=get_settings().entorno)
        if not estado.listo:
            respuesta.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return estado.a_dict()

    @app.exception_handler(Exception)
    def error_no_previsto(_solicitud: Request, excepcion: Exception) -> JSONResponse:
        """Un fallo real sí es un 500, y no revela detalles internos."""
        return JSONResponse(
            status_code=500,
            content=ErrorRespuesta(
                codigo=CodigoError.SOURCE_UNAVAILABLE,
                detalle=(
                    "La consulta no se pudo resolver por un fallo del servicio. "
                    "El detalle quedó en los registros."
                ),
            ).model_dump(mode="json"),
        )

    return app


app = crear_app()
