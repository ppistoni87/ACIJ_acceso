"""Aplicación FastAPI del backend normativo."""

from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.exc import OperationalError

from backend_normativo import SCHEMA_VERSION, __version__
from backend_normativo.api.contratos import CodigoError, ErrorRespuesta
from backend_normativo.api.limites import VENTANA_AUTENTICACION_S
from backend_normativo.api.routers import (
    admin,
    devoluciones,
    evaluaciones,
    normas,
    operativo,
    recuperacion,
    sesiones,
)
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


VARIABLE_PRECARGA = "BN_PRECARGAR_MODELO"


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Paga el costo del modelo al arrancar, si el despliegue lo pide.

    Cargarlo cuesta segundos y unos cientos de megas. Si no se hace acá lo paga
    la primera persona que pregunta, y con varias preguntando a la vez lo pagan
    todas. No se hace siempre porque en desarrollo y en las pruebas ese costo es
    puro estorbo: se enciende con `BN_PRECARGAR_MODELO=1` en el despliegue, que
    es donde importa.
    """
    import os

    if (os.environ.get(VARIABLE_PRECARGA) or "").strip().lower() in {"1", "true", "si", "sí"}:
        from backend_normativo.recuperacion.embeddings import embebedor_compartido

        embebedor_compartido()
    yield


def _demasiadas(detalle: str, espera_s: float) -> JSONResponse:
    """429 con cuerpo tipado y `Retry-After`.

    Un límite que contesta con una página de error no le sirve a un cliente
    automático, y uno que no dice cuánto esperar invita a reintentar en un
    bucle apretado, que es peor que el problema original.
    """
    import math

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorRespuesta(codigo=CodigoError.RATE_LIMITED, detalle=detalle).model_dump(
            mode="json"
        ),
        headers={"Retry-After": str(max(1, math.ceil(espera_s)))},
    )


def crear_app() -> FastAPI:
    app = FastAPI(
        title="Backend normativo de acceso a derechos",
        version=__version__,
        description=DESCRIPCION,
        lifespan=ciclo_de_vida,
        openapi_tags=[
            {"name": "normas", "description": "Identidad, versiones y siete campos."},
            {"name": "operativo", "description": "Beneficios, valores, plazos y atención."},
            {"name": "evaluación", "description": "Evaluación preliminar de aplicabilidad."},
            {"name": "recuperación", "description": "Fragmentos citables y cobertura."},
            {
                "name": "conversación",
                "description": "Lo que la persona contesta sobre la respuesta que recibió.",
            },
            {"name": "administración", "description": "Revisión y publicación."},
        ],
    )

    app.include_router(normas.router)
    app.include_router(operativo.router)
    app.include_router(evaluaciones.router)
    app.include_router(recuperacion.router)
    app.include_router(devoluciones.router)
    app.include_router(sesiones.router)
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

    # El frente ciudadano (P-015) va por el mismo camino y por la misma razón:
    # consume `POST /v1/respuestas` y `GET /v1/vocabularios`, y si viajara por
    # separado podría quedar pidiendo campos que la API ya no devuelve. Acá no
    # puede: sale de la misma imagen que la API que consume.
    @app.get("/consulta", tags=["recuperación"], include_in_schema=False)
    def frente_ciudadano() -> HTMLResponse:
        return HTMLResponse(
            (pathlib.Path(__file__).parent / "ciudadano" / "consulta.html").read_text(
                encoding="utf-8"
            )
        )

    # El orden importa y es al revés de como se lee: el último middleware
    # registrado es el más externo. Los límites se registran **antes** que la
    # observabilidad para que queden adentro, y así un 429 se mide como
    # cualquier otra respuesta. Un límite que frena sin dejar rastro no se puede
    # ajustar: no hay forma de saber si está frenando abuso o gente.
    @app.middleware("http")
    async def aplicar_limites(solicitud: Request, siguiente):
        """Cuántas consultas por minuto, y cuántos intentos de credencial (P-017)."""
        from backend_normativo.api.limites import (
            clave_de,
            limitador_de_autenticaciones,
            limitador_de_consultas,
        )

        ruta = solicitud.url.path
        if not ruta.startswith("/v1"):
            return await siguiente(solicitud)

        clave = clave_de(solicitud)
        autenticaciones = limitador_de_autenticaciones()
        es_admin = "/admin/" in ruta or "/revisiones/" in ruta

        # El cupo de autenticación se mira antes de trabajar: frenar después de
        # verificar la credencial es hacer justo el trabajo que el ataque busca.
        if es_admin and not autenticaciones.hay_cupo(clave):
            return _demasiadas(
                "Demasiados intentos de credencial fallidos desde este origen. El cupo se "
                "repone solo; no hace falta pedir nada.",
                VENTANA_AUTENTICACION_S,
            )

        veredicto = limitador_de_consultas().permitir(clave)
        if not veredicto.permitido:
            return _demasiadas(
                "Estás preguntando muy seguido y tuve que frenarte un momento. Esperá unos "
                "segundos y probá otra vez.",
                veredicto.espera_s,
            )

        respuesta = await siguiente(solicitud)
        # Una credencial rechazada gasta cupo del segundo balde. El primero ya se
        # gastó arriba: un intento fallido cuesta las dos cosas.
        if es_admin and respuesta.status_code in (401, 403):
            autenticaciones.permitir(clave)
        return respuesta

    @app.middleware("http")
    async def registrar_consulta(solicitud: Request, siguiente):
        """Correlación y medición de cada consulta de lectura.

        El registro va en su propia conexión y su propia transacción: si
        escribir la medición fallara, la respuesta ya está dada y no tiene por
        qué caerse por eso. Medir no puede romper lo medido.
        """
        import time
        import uuid as _uuid

        from backend_normativo.api.contratos import abrir_anotacion
        from backend_normativo.api.observabilidad import (
            CABECERA_REQUEST_ID,
            RESUELTA,
            RUTAS_SIN_TRAZA,
            Anotacion,
            registrar,
            request_id_de,
        )

        anotado = abrir_anotacion()
        rid = request_id_de(solicitud.headers)
        solicitud.state.request_id = rid
        comenzo = time.perf_counter()
        respuesta = await siguiente(solicitud)
        latencia = int((time.perf_counter() - comenzo) * 1000)
        respuesta.headers[CABECERA_REQUEST_ID] = rid

        ruta = solicitud.url.path
        # Solo las lecturas de `/v1` que no son de administración: las sondas y
        # la consola no son consultas de nadie, y registrarlas ensucia el
        # denominador con tráfico de infraestructura.
        if not ruta.startswith("/v1") or "/admin/" in ruta:
            return respuesta

        # Una devolución no es una consulta de nadie: es la respuesta de la
        # persona a una que ya se registró. Contarla en la traza inflaría el
        # denominador —«400 consultas» pasaría a incluir los clics en «me
        # sirvió»— y haría que la tasa de respuesta se midiera contra sí misma.
        # Su registro es la tabla `devoluciones`, no esta.
        if ruta in RUTAS_SIN_TRAZA:
            return respuesta

        estado = anotado.get("data_status")
        motivo = anotado.get("motivo")
        if respuesta.status_code >= 400:
            resultado, motivo = "ERROR", motivo or f"HTTP {respuesta.status_code}"
        else:
            resultado = RESUELTA if estado == "PUBLICADO" else (estado or "SIN_CLASIFICAR")
            # Una respuesta resuelta no lleva causa de abstención aunque traiga
            # advertencias: las hay informativas —«los campos evaluados y los que
            # tienen valor se informan por separado»— y guardarlas como motivo
            # haría que el tablero cuente como abstención algo que sí se
            # contestó, que es exactamente la distinción que hay que preservar.
            if resultado == RESUELTA:
                motivo = None

        release = anotado.get("release_id")
        try:
            with engine_api().begin() as conexion:
                registrar(
                    conexion,
                    Anotacion(
                        request_id=rid,
                        ruta=ruta,
                        resultado=resultado,
                        latencia_ms=latencia,
                        release_id=_uuid.UUID(str(release)) if release else None,
                        motivo=motivo,
                        evidencias=int(anotado.get("evidencias") or 0),
                    ),
                )
        except Exception:
            # Nunca convertir un fallo de medición en un fallo de respuesta.
            pass
        return respuesta

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

    @app.exception_handler(OperationalError)
    def base_inalcanzable(_solicitud: Request, _excepcion: OperationalError) -> JSONResponse:
        """La base caída es 503, no 500.

        La diferencia no es cosmética: un 500 dice «esta petición salió mal» y
        un balanceador la vuelve a mandar a la misma instancia; un 503 con
        `Retry-After` dice «esta instancia no puede ahora», que es lo que
        corresponde cuando lo que falta es la base y no la consulta. El detalle
        del fallo no viaja: diría el host, el usuario y el motor.
        """
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorRespuesta(
                codigo=CodigoError.SOURCE_UNAVAILABLE,
                detalle=(
                    "Ahora mismo no puedo entrar a consultar las normas. No es que la "
                    "respuesta sea que no: es que no pude fijarme. Probá de nuevo en un "
                    "minuto."
                ),
            ).model_dump(mode="json"),
            headers={"Retry-After": "5"},
        )

    @app.exception_handler(Exception)
    def error_no_previsto(_solicitud: Request, excepcion: Exception) -> JSONResponse:
        """Un fallo real sí es un 500, y no revela detalles internos."""
        return JSONResponse(
            status_code=500,
            content=ErrorRespuesta(
                codigo=CodigoError.SOURCE_UNAVAILABLE,
                detalle=(
                    "Algo falló de mi lado y no pude contestarte. Ya quedó anotado para que "
                    "lo revisen. Probá de nuevo en un rato."
                ),
            ).model_dump(mode="json"),
        )

    return app


app = crear_app()
