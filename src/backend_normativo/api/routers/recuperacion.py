"""`POST /v1/recuperacion` y `GET /v1/cobertura`.

La recuperación devuelve unidades citables del release autorizado. Sirve para
explicar y citar, nunca para reemplazar una consulta estructurada: un monto, una
fecha o un teléfono se consultan con SQL y tipos, no mezclando fragmentos.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from backend_normativo.api.contratos import (
    Advertencia,
    CodigoError,
    DataStatus,
    Respuesta,
)
from backend_normativo.api.dependencias import Administracion, Contexto, exigir_rol
from backend_normativo.calidad.cobertura import medir
from backend_normativo.recuperacion.busqueda import buscar as buscar_fragmentos
from backend_normativo.recuperacion.embeddings import embebedor_compartido
from backend_normativo.seguridad.credenciales import ROL_AUDITOR

router = APIRouter(prefix="/v1", tags=["recuperación"])


class SolicitudRecuperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consulta: str
    jurisdiccion: str | None = None
    beneficio: str | None = None
    limite: int = Field(10, ge=1, le=50)


class Fragmento(BaseModel):
    chunk_id: uuid.UUID
    texto: str
    norma: str
    unidad: str | None
    url_fuente: str | None
    relevancia: float
    # De qué mitad salió. Sirve para leer el resultado: un fragmento que
    # encontró solo la búsqueda semántica no comparte ninguna palabra con la
    # consulta, y eso conviene saberlo antes de citarlo.
    encontrado_por: str = "lexica"


class ResultadoRecuperacion(BaseModel):
    fragmentos: list[Fragmento] = Field(default_factory=list)
    conflictos_pertinentes: list[dict] = Field(default_factory=list)
    aclaracion: str = (
        "Los fragmentos sirven para explicar y citar. Los montos, las fechas y los datos "
        "de contacto se consultan con las operaciones tipadas, no combinando fragmentos."
    )


@router.post("/recuperacion", response_model=Respuesta[ResultadoRecuperacion])
def recuperar(
    solicitud: SolicitudRecuperacion, contexto: Contexto = Depends()
) -> Respuesta[ResultadoRecuperacion]:
    if not contexto.hay_release:
        return Respuesta(
            release_id=None,
            as_of=contexto.as_of,
            known_at=contexto.known_at,
            data_status=DataStatus.NO_PUBLICABLE,
            data=ResultadoRecuperacion(),
            warnings=[
                Advertencia(
                    codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                    detalle=(
                        "No hay ningún release publicado. No se recupera de staging: "
                        "el corpus servible es solo lo publicado."
                    ),
                )
            ],
        )

    # La búsqueda vive en `recuperacion.busqueda`: la mitad léxica y la
    # vectorial comparten los mismos filtros, y compartirlos importa más que
    # tenerlos cerca. Si una se olvidara de uno, la fusión metería de vuelta lo
    # que la otra descartó.
    # Sin el extra de recuperación instalado, `embebedor_compartido` devuelve
    # `None`, la mitad léxica sirve sola y la respuesta lo declara. No se cae:
    # una consulta contestada peor es mejor que una no contestada, siempre que
    # quien la lee sepa que fue peor.
    hallazgo = buscar_fragmentos(
        contexto.conexion,
        solicitud.consulta,
        release_id=contexto.release_id,
        embebedor=embebedor_compartido(),
        limite=solicitud.limite,
        jurisdiccion=solicitud.jurisdiccion,
        beneficio=solicitud.beneficio,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
    )
    filas = hallazgo.fragmentos

    # Esta ruta leía `incidencias_revision` para advertir sobre conflictos
    # abiertos. Dos problemas. Uno: es staging, el lector no la puede leer y la
    # consulta devolvía 500 en cualquier despliegue con roles de verdad. Dos: la
    # advertencia era global —conflictos en cualquier parte del corpus— y no
    # sobre los fragmentos devueltos, así que alarmaba sin decir de qué.
    #
    # Y era redundante: el control DQ09 impide publicar con conflictos abiertos
    # de severidad alta **sobre lo que se publica**, así que por construcción un
    # fragmento servido no tiene uno. La garantía está en el momento de
    # publicar, que es donde corresponde, y no en cada consulta.
    conflictos: list[dict] = []

    advertencias: list[Advertencia] = [
        Advertencia(codigo=CodigoError.INSUFFICIENT_EVIDENCE, detalle=aviso)
        for aviso in hallazgo.avisos
    ]
    if conflictos:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.CONFLICT,
                detalle=(
                    f"Hay {len(conflictos)} conflicto(s) abiertos de severidad alta en el "
                    "corpus. Se informan junto con los fragmentos."
                ),
            )
        )

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if filas else DataStatus.SIN_RESULTADOS,
        data=ResultadoRecuperacion(
            fragmentos=[
                Fragmento(
                    chunk_id=fragmento.chunk_id,
                    texto=fragmento.texto,
                    norma=fragmento.norma,
                    unidad=fragmento.unidad,
                    url_fuente=fragmento.url_fuente,
                    relevancia=fragmento.puntaje,
                    encontrado_por=fragmento.encontrado_por,
                )
                for fragmento in filas
            ],
            conflictos_pertinentes=conflictos,
        ),
        warnings=advertencias,
    )


@router.get("/cobertura", response_model=Respuesta[dict])
def cobertura(
    contexto: Contexto = Depends(),
    admin: Administracion = Depends(exigir_rol(ROL_AUDITOR)),
) -> Respuesta[dict]:
    """Denominadores y pendientes, separados de lo validado y publicable.

    Va con credencial de auditoría porque `medir()` lee el estado operativo
    —fuentes, capturas, incidencias— y no una proyección publicada. El contrato
    ya lo declaraba de «alcance autorizado»; la implementación lo servía abierto
    y con la conexión del lector, que no tiene permiso sobre `capturas`: en
    cualquier despliegue con roles de verdad esto devolvía 500, y darle el
    permiso al lector hubiera consagrado que el lector lea staging.
    """
    metricas = medir(admin.conexion)
    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO,
        data=metricas.a_dict(),
        warnings=[
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    "Los campos evaluados y los campos con valor sustantivo se informan por "
                    "separado. Un campo revisado sin información no cuenta como completo."
                ),
            )
        ],
    )


# --- P-013: respuesta con citas, o el límite explicado ------------------------


class SolicitudRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consulta: str
    jurisdiccion: str | None = None
    beneficio: str | None = None
    limite: int = Field(default=5, ge=1, le=10)


class FuenteCitada(BaseModel):
    """Una cita que se puede abrir.

    El endpoint devolvía las citas como identificadores sueltos —`[[chunk:uuid]]`
    en el texto y la lista de uuids al lado—, que sirve para un sistema y no para
    una persona: nadie verifica un uuid. El criterio 2 de P-015 pide «fuentes
    abribles», así que la cita viaja con de qué norma es, de qué unidad y a qué
    URL oficial lleva. Cuando no hay URL se dice; no se fabrica una.
    """

    chunk_id: uuid.UUID
    norma: str
    unidad: str | None = None
    url_fuente: str | None = None
    jurisdiccion: str | None = None
    encontrado_por: str = "lexica"


# Qué normas cubre cada corte. Se calcula una vez por corte y se guarda: un
# release es inmutable, así que volver a preguntarlo en cada consulta sería
# pagar una consulta más para obtener siempre lo mismo.
_cobertura_por_corte: dict[str, list[dict]] = {}


def cobertura_del_corte(conexion, release_id) -> list[dict]:
    """Las normas que el corte publicado contiene.

    Sirve para algo que el sistema sabía y no estaba diciendo: si alguien
    pregunta por la asignación universal por hijo y lo único publicado es una
    ley de vivienda de CABA, decirle qué hay publicado es más útil que
    devolverle los párrafos más parecidos y callarse.
    """
    clave = str(release_id)
    if clave in _cobertura_por_corte:
        return _cobertura_por_corte[clave]
    filas = conexion.execute(
        text(
            "SELECT DISTINCT n.tipo || ' ' || coalesce(n.numero, '?') || '/' || "
            "       coalesce(n.anio::text, '?') AS norma, n.jurisdiccion_id, n.titulo "
            "  FROM chunks c "
            "  JOIN norma_versiones nv ON nv.registro_version_id = c.registro_version_id "
            "  JOIN normas n ON n.id = nv.norma_id "
            " WHERE c.release_id = :r ORDER BY 1"
        ),
        {"r": release_id},
    ).all()
    cobertura = [{"norma": fila[0], "jurisdiccion": fila[1], "titulo": fila[2]} for fila in filas]
    _cobertura_por_corte[clave] = cobertura
    return cobertura


@router.post("/respuestas")
def responder_consulta(solicitud: SolicitudRespuesta, contexto: Contexto = Depends()) -> dict:
    """Recupera y arma la respuesta, declarando con qué se armó.

    Tres modos y la diferencia no se borra: `GENERADA` si un proveedor redactó y
    los validadores aprobaron, `EXTRACTO` si no hubo proveedor o lo que devolvió
    no se sostiene, `ABSTENCION` si no hay evidencia. El plan lo pide con esas
    palabras: «un extracto de respaldo no se presenta como generación activa».

    Hoy no hay proveedor configurado, así que contesta en modo extracto: texto
    publicado, literal y citado. No puede alucinar, y se declara.
    """
    from backend_normativo.api.contratos import anotar
    from backend_normativo.generacion.proveedores import configurado as proveedor_configurado
    from backend_normativo.generacion.respuesta import ModoRespuesta, responder

    if not contexto.hay_release:
        salida = responder(solicitud.consulta, [])
        anotar(
            data_status=DataStatus.NO_PUBLICABLE.value,
            release_id=None,
            motivo=salida.motivo.value if salida.motivo else None,
        )
        return {
            "release_id": None,
            "as_of": contexto.as_of.isoformat(),
            "known_at": contexto.known_at.isoformat(),
            "data_status": DataStatus.NO_PUBLICABLE.value,
            "fuentes": [],
            "solo_parecidos": False,
            "cobertura": [],
            **salida.a_dict(),
        }

    hallazgo = buscar_fragmentos(
        contexto.conexion,
        solicitud.consulta,
        release_id=contexto.release_id,
        embebedor=embebedor_compartido(),
        limite=solicitud.limite,
        jurisdiccion=solicitud.jurisdiccion,
        beneficio=solicitud.beneficio,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
    )
    # El proveedor sale del entorno: con `BN_MODELO_CLAVE` puesta redacta, sin
    # ella el orquestador cae al extracto. Ninguna de las dos ramas cambia los
    # validadores ni la política de modo, que es lo que protege a quien
    # consulta.
    salida = responder(solicitud.consulta, hallazgo.fragmentos, proveedor=proveedor_configurado())

    fuentes = [
        FuenteCitada(
            chunk_id=fragmento.chunk_id,
            norma=fragmento.norma,
            unidad=fragmento.unidad,
            url_fuente=fragmento.url_fuente,
            jurisdiccion=fragmento.jurisdiccion,
            encontrado_por=fragmento.encontrado_por,
        ).model_dump(mode="json")
        for fragmento in hallazgo.fragmentos
    ]
    estado = (
        DataStatus.SIN_RESULTADOS
        if salida.modo is ModoRespuesta.ABSTENCION
        else DataStatus.PUBLICADO
    )
    # Sin esto la ruta más usada del sistema no dejaba rastro medible: no pasa
    # por la envoltura `Respuesta`, que es la que anota sola.
    anotar(
        data_status=estado.value,
        release_id=contexto.release_id,
        motivo=salida.motivo.value if salida.motivo else None,
        evidencias=len(fuentes),
    )
    return {
        "release_id": str(contexto.release_id),
        "as_of": contexto.as_of.isoformat(),
        "known_at": contexto.known_at.isoformat(),
        "data_status": estado.value,
        "fuentes": fuentes,
        "avisos": hallazgo.avisos,
        # Ningún fragmento servido comparte una palabra con la consulta: los
        # eligió sólo el parecido de significado. El frente lo usa para no
        # presentarlos como la respuesta.
        "solo_parecidos": hallazgo.solo_parecidos,
        "cobertura": cobertura_del_corte(contexto.conexion, contexto.release_id),
        **salida.a_dict(),
    }


# --- P-015: lo que el frente necesita para dejar elegir ----------------------


class Vocabularios(BaseModel):
    """Las opciones que una persona puede elegir, tal como están cargadas.

    El frente no las puede tener escritas adentro: una jurisdicción que se
    agrega al corpus quedaría invisible, y una que se saca seguiría ofreciéndose
    para filtrar por algo que no existe. Salen de la base, que es donde están.
    """

    jurisdicciones: list[dict] = Field(default_factory=list)
    lineas_de_beneficio: list[str] = Field(default_factory=list)


@router.get("/vocabularios", response_model=Respuesta[Vocabularios])
def vocabularios(contexto: Contexto = Depends()) -> Respuesta[Vocabularios]:
    """Jurisdicciones y líneas de beneficio para los selectores del frente."""
    jurisdicciones = [
        {"id": fila.id, "nombre": fila.nombre, "nivel": fila.nivel}
        for fila in contexto.conexion.execute(
            text("SELECT id, nombre, nivel FROM jurisdicciones ORDER BY nivel, nombre")
        ).all()
    ]
    lineas = [
        fila[0]
        for fila in contexto.conexion.execute(
            text("SELECT DISTINCT linea FROM beneficios WHERE linea IS NOT NULL ORDER BY linea")
        ).all()
    ]
    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if jurisdicciones else DataStatus.SIN_RESULTADOS,
        data=Vocabularios(jurisdicciones=jurisdicciones, lineas_de_beneficio=lineas),
    )
