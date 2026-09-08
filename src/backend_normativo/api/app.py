"""Aplicación FastAPI del backend normativo."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend_normativo import SCHEMA_VERSION, __version__
from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.api.routers import admin, evaluaciones, normas, operativo, recuperacion

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

    @app.get("/salud", tags=["operativo"])
    def salud() -> dict:
        return {"estado": "ok", "schema_version": SCHEMA_VERSION, "version": __version__}

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
