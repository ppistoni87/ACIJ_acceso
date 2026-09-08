"""`GET /v1/beneficios`, `/v1/valores`, `/v1/plazos`, `/v1/puntos-atencion` y
`/v1/barrios-renabap`.

Todo lo operativo se consulta con SQL y tipos. Un monto, una fecha, una
dirección y un horario salen de la misma entidad o no se responden.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend_normativo.api.contratos import (
    Advertencia,
    CodigoError,
    DataStatus,
    ErrorRespuesta,
    Evidencia,
    Pagina,
    Respuesta,
)
from backend_normativo.api.dependencias import Contexto

router = APIRouter(prefix="/v1", tags=["operativo"])


class BeneficioResumen(BaseModel):
    beneficio_id: uuid.UUID
    codigo: str
    nombre: str
    linea: str | None
    familia: str | None
    jurisdiccion: str | None
    naturaleza: str | None
    versiones_publicadas: int


class ValorParametro(BaseModel):
    parametro: str
    concepto: str
    valor: decimal.Decimal
    unidad: str
    moneda: str | None
    periodo: dt.date | None
    territorio: str | None
    segmento: str | None
    vigencia_desde: dt.date | None
    vigencia_hasta: dt.date | None
    evidencia_id: uuid.UUID


class PlazoResumen(BaseModel):
    plazo_id: uuid.UUID
    tipo: str
    inicio: dt.date | None
    fin: dt.date | None
    hora_cierre: dt.time | None
    zona_horaria: str
    cantidad: int | None
    unidad: str | None
    tipo_dia: str
    evento_inicio: str | None
    estado_calculado: str


class PuntoAtencion(BaseModel):
    punto_id: uuid.UUID
    nombre: str
    tipo: str
    organismo: str
    organismo_operador: str | None
    direccion: str | None
    localidad: str | None
    lat: decimal.Decimal | None
    lng: decimal.Decimal | None
    canales: list[dict] = Field(default_factory=list)
    verificado_en: dt.datetime | None


@router.get("/beneficios", response_model=Respuesta[Pagina[BeneficioResumen]])
def listar_beneficios(
    contexto: Contexto = Depends(),
    poblacion: str | None = Query(None, description="Código de población destinataria."),
    territorio: str | None = Query(None, description="Jurisdicción."),
    linea: str | None = Query(None),
    limite: int = Query(25, ge=1, le=100),
    desplazamiento: int = Query(0, ge=0),
) -> Respuesta[Pagina[BeneficioResumen]]:
    """Beneficios candidatos.

    Pertenecer a una población no implica tener derecho: el filtro acota la
    búsqueda, no infiere elegibilidad. Para saber si corresponde hay que evaluar
    las reglas, que es lo que hace `POST /v1/evaluaciones-preliminares`.
    """
    condiciones = ["1 = 1"]
    parametros: dict[str, object] = {}
    if linea:
        condiciones.append("b.linea = :linea")
        parametros["linea"] = linea
    if territorio:
        condiciones.append("bv.jurisdiccion_id = :territorio")
        parametros["territorio"] = territorio
    if poblacion:
        condiciones.append(
            "EXISTS (SELECT 1 FROM beneficio_poblaciones bp "
            "         JOIN poblaciones p ON p.id = bp.poblacion_id "
            "        WHERE bp.beneficio_version_id = bv.registro_version_id "
            "          AND p.codigo = :poblacion)"
        )
        parametros["poblacion"] = poblacion

    donde = " AND ".join(condiciones)
    total = contexto.conexion.execute(
        text(
            "SELECT count(DISTINCT b.id) FROM beneficios b "
            "  LEFT JOIN beneficio_versiones bv ON bv.beneficio_id = b.id "
            f" WHERE {donde}"
        ),
        parametros,
    ).scalar_one()

    filas = (
        contexto.conexion.execute(
            text(
                "SELECT DISTINCT ON (b.id) b.id, b.codigo, b.nombre, b.linea, b.familia, "
                "       bv.jurisdiccion_id, bv.naturaleza, "
                "       (SELECT count(*) FROM beneficio_versiones bv2 "
                "          JOIN registro_versiones rv ON rv.id = bv2.registro_version_id "
                "         WHERE bv2.beneficio_id = b.id "
                "           AND rv.estado_revision = 'PUBLISHED') AS publicadas "
                "  FROM beneficios b "
                "  LEFT JOIN beneficio_versiones bv ON bv.beneficio_id = b.id "
                f" WHERE {donde} ORDER BY b.id, b.codigo LIMIT :limite OFFSET :desp"
            ),
            {**parametros, "limite": limite, "desp": desplazamiento},
        )
        .mappings()
        .all()
    )

    items = [
        BeneficioResumen(
            beneficio_id=fila["id"],
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            linea=fila["linea"],
            familia=fila["familia"],
            jurisdiccion=fila["jurisdiccion_id"],
            naturaleza=fila["naturaleza"],
            versiones_publicadas=fila["publicadas"],
        )
        for fila in filas
    ]

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if items else DataStatus.SIN_RESULTADOS,
        data=Pagina(items=items, total=total, limite=limite, desplazamiento=desplazamiento),
        warnings=[
            Advertencia(
                codigo=CodigoError.UNSUPPORTED_SCOPE,
                detalle=(
                    "Este listado no infiere elegibilidad. Pertenecer a una población no "
                    "implica tener derecho al beneficio."
                ),
            )
        ],
    )


@router.get("/valores", response_model=Respuesta[list[ValorParametro]])
def valores(
    contexto: Contexto = Depends(),
    concepto: str = Query(..., description="Código del parámetro."),
    territorio: str | None = Query(None),
    segmento: str | None = Query(None),
) -> Respuesta[list[ValorParametro]]:
    """Valor de un parámetro para la fecha consultada.

    Nunca se devuelve el último valor por fecha máxima: se devuelve el que se
    aplica a la fecha pedida. Servir el monto de otro período es la forma más
    directa de dar una respuesta incorrecta que parece correcta.
    """
    filas = (
        contexto.conexion.execute(
            text(
                "SELECT p.codigo, p.concepto, pv.valor, pv.unidad, pv.moneda, pv.periodo, "
                "       pv.territorio_id, pv.segmento, rv.valid_desde, rv.valid_hasta, "
                "       pv.evidencia_id "
                "  FROM parametro_valores pv "
                "  JOIN parametros p ON p.id = pv.parametro_id "
                "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                " WHERE p.codigo = :c AND pv.publicable "
                "   AND pv.rango_aplicacion @> CAST(:f AS date) "
                "   AND (CAST(:t AS text) IS NULL OR pv.territorio_id = :t) "
                "   AND (CAST(:s AS text) IS NULL OR pv.segmento = :s) "
                "   AND rv.estado_revision = 'PUBLISHED'"
            ),
            {"c": concepto, "f": contexto.as_of, "t": territorio, "s": segmento},
        )
        .mappings()
        .all()
    )

    if not filas:
        return Respuesta(
            release_id=contexto.release_id,
            as_of=contexto.as_of,
            known_at=contexto.known_at,
            data_status=DataStatus.SIN_RESULTADOS,
            data=[],
            missing_fields=[concepto],
            warnings=[
                Advertencia(
                    codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                    detalle=(
                        f"No hay un valor aprobado de «{concepto}» que se aplique al "
                        f"{contexto.as_of.isoformat()}. No se devuelve el valor de otro "
                        "período."
                    ),
                )
            ],
        )

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO,
        data=[
            ValorParametro(
                parametro=fila["codigo"],
                concepto=fila["concepto"],
                valor=fila["valor"],
                unidad=fila["unidad"],
                moneda=fila["moneda"],
                periodo=fila["periodo"],
                territorio=fila["territorio_id"],
                segmento=fila["segmento"],
                vigencia_desde=fila["valid_desde"],
                vigencia_hasta=fila["valid_hasta"],
                evidencia_id=fila["evidencia_id"],
            )
            for fila in filas
        ],
    )


@router.get("/plazos", response_model=Respuesta[list[PlazoResumen]])
def plazos(
    contexto: Contexto = Depends(),
    beneficio_id: uuid.UUID | None = Query(None),
    tramite_id: uuid.UUID | None = Query(None),
    convocatoria: str | None = Query(None),
    ciclo: int | None = Query(None),
) -> Respuesta[list[PlazoResumen]]:
    """Plazos con su tipo y su estado calculado a la fecha.

    Un plazo relativo sin evento de inicio conocido responde "desconocido", no
    una fecha inventada.
    """
    if beneficio_id is None and tramite_id is None:
        raise HTTPException(
            status_code=400,
            detail=ErrorRespuesta(
                codigo=CodigoError.INVALID_REQUEST,
                detalle="Hay que indicar un beneficio o un trámite.",
                as_of=contexto.as_of,
                known_at=contexto.known_at,
            ).model_dump(mode="json"),
        )

    filas = (
        contexto.conexion.execute(
            text(
                "SELECT pl.plazo_id, pl.tipo, pl.inicio, pl.fin, pl.hora_cierre, pl.zona_horaria, "
                "       pl.cantidad, pl.unidad, pl.tipo_dia, pl.evento_inicio "
                "  FROM plazos pl "
                "  JOIN registro_versiones rv ON rv.id = pl.registro_version_id "
                " WHERE rv.estado_revision = 'PUBLISHED' "
                "   AND (CAST(:b AS uuid) IS NULL "
                "        OR pl.beneficio_version_id IN "
                "           (SELECT registro_version_id FROM beneficio_versiones "
                "             WHERE beneficio_id = :b)) "
                "   AND (CAST(:t AS uuid) IS NULL "
                "        OR pl.tramite_version_id IN "
                "           (SELECT registro_version_id FROM tramite_versiones "
                "             WHERE tramite_id = :t)) "
                "   AND (CAST(:conv AS text) IS NULL OR pl.convocatoria = :conv) "
                "   AND (CAST(:ciclo AS int) IS NULL OR pl.ciclo = :ciclo)"
            ),
            {"b": beneficio_id, "t": tramite_id, "conv": convocatoria, "ciclo": ciclo},
        )
        .mappings()
        .all()
    )

    def estado(fila) -> str:
        if fila["inicio"] is None and fila["fin"] is None:
            # Modalidad relativa: sin el evento que lo dispara no hay fecha.
            return "DESCONOCIDO"
        if fila["inicio"] and contexto.as_of < fila["inicio"]:
            return "NO_INICIADO"
        if fila["fin"] and contexto.as_of > fila["fin"]:
            return "CERRADO"
        return "ABIERTO"

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if filas else DataStatus.SIN_RESULTADOS,
        data=[
            PlazoResumen(
                plazo_id=fila["plazo_id"],
                tipo=fila["tipo"],
                inicio=fila["inicio"],
                fin=fila["fin"],
                hora_cierre=fila["hora_cierre"],
                zona_horaria=fila["zona_horaria"],
                cantidad=fila["cantidad"],
                unidad=fila["unidad"],
                tipo_dia=fila["tipo_dia"],
                evento_inicio=fila["evento_inicio"],
                estado_calculado=estado(fila),
            )
            for fila in filas
        ],
        warnings=(
            []
            if filas
            else [
                Advertencia(
                    codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                    detalle="No hay plazos publicados para ese beneficio o trámite.",
                )
            ]
        ),
    )


@router.get("/puntos-atencion", response_model=Respuesta[list[PuntoAtencion]])
def puntos_atencion(
    contexto: Contexto = Depends(),
    jurisdiccion: str | None = Query(None),
    localidad: str | None = Query(None),
    tipo: str | None = Query(None),
) -> Respuesta[list[PuntoAtencion]]:
    """Puntos de atención con sus canales.

    Sin coordenadas válidas no se afirma cercanía. El horario es por canal: el
    de la mesa presencial no se copia al teléfono.
    """
    filas = (
        contexto.conexion.execute(
            text(
                "SELECT p.id, p.nombre, p.tipo, o.nombre AS organismo, "
                "       oo.nombre AS operador, pv.direccion_legible, pv.direccion_cruda, "
                "       pv.localidad, pv.lat, pv.lng, rv.verificado_en "
                "  FROM puntos_atencion p "
                "  JOIN punto_versiones pv ON pv.punto_id = p.id "
                "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                "  JOIN organismos o ON o.id = p.organismo_id "
                "  LEFT JOIN organismos oo ON oo.id = p.organismo_operador_id "
                " WHERE rv.estado_revision = 'PUBLISHED' "
                "   AND (CAST(:j AS text) IS NULL OR p.jurisdiccion_id = :j) "
                "   AND (CAST(:l AS text) IS NULL OR pv.localidad ILIKE :l) "
                "   AND (CAST(:t AS text) IS NULL OR p.tipo = :t) "
                " ORDER BY p.nombre LIMIT 100"
            ),
            {"j": jurisdiccion, "l": f"%{localidad}%" if localidad else None, "t": tipo},
        )
        .mappings()
        .all()
    )

    puntos: list[PuntoAtencion] = []
    for fila in filas:
        canales = [
            {
                "tipo": canal["tipo"],
                "valor": canal["valor_normalizado"] or canal["valor_crudo"],
                "horario": canal["horario"],
                "publico": canal["publico"],
            }
            for canal in contexto.conexion.execute(
                text(
                    "SELECT c.tipo, c.valor_crudo, c.valor_normalizado, c.horario, c.publico "
                    "  FROM canales c "
                    "  JOIN registro_versiones rv ON rv.id = c.registro_version_id "
                    " WHERE c.punto_id = :p AND rv.estado_revision = 'PUBLISHED'"
                ),
                {"p": fila["id"]},
            ).mappings()
        ]
        puntos.append(
            PuntoAtencion(
                punto_id=fila["id"],
                nombre=fila["nombre"],
                tipo=fila["tipo"],
                organismo=fila["organismo"],
                organismo_operador=fila["operador"],
                direccion=fila["direccion_legible"] or fila["direccion_cruda"],
                localidad=fila["localidad"],
                lat=fila["lat"],
                lng=fila["lng"],
                canales=canales,
                verificado_en=fila["verificado_en"],
            )
        )

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if puntos else DataStatus.SIN_RESULTADOS,
        data=puntos,
        warnings=(
            []
            if puntos
            else [
                Advertencia(
                    codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                    detalle="No hay puntos de atención publicados con esos filtros.",
                )
            ]
        ),
    )


class BarrioRenabapResumen(BaseModel):
    barrio_id: uuid.UUID
    id_renabap: str
    nombre: str
    provincia: str | None
    departamento: str | None
    localidad: str | None
    familias: int | None
    padron_version: str
    fecha_corte: dt.date | None
    evidencia_id: uuid.UUID


@router.get("/barrios-renabap", response_model=Respuesta[list[BarrioRenabapResumen]])
def barrios_renabap(
    contexto: Contexto = Depends(),
    nombre: str | None = Query(None, description="Nombre del barrio, parcial."),
    provincia: str | None = Query(None),
    padron: str | None = Query(None, description="Versión del padrón; por defecto, la última."),
) -> Respuesta[list[BarrioRenabapResumen]]:
    """Barrios del padrón RENABAP en una versión concreta.

    **No figurar en el padrón no es una exclusión jurídica.** Es un dato de ese
    corte. La respuesta siempre dice contra qué versión del padrón se buscó y
    por dónde se consulta oficialmente, para que una ausencia no se lea como
    una conclusión sobre derechos.
    """
    version = (
        padron
        or contexto.conexion.execute(
            text("SELECT max(padron_version) FROM barrios_renabap")
        ).scalar_one_or_none()
    )

    filas = (
        contexto.conexion.execute(
            text(
                "SELECT b.barrio_id, b.id_renabap, b.nombre, b.provincia, b.departamento, "
                "       b.localidad, b.familias, b.padron_version, b.fecha_corte, b.evidencia_id "
                "  FROM barrios_renabap b "
                " WHERE b.padron_version = :v "
                "   AND (CAST(:n AS text) IS NULL OR b.nombre ILIKE :n) "
                "   AND (CAST(:p AS text) IS NULL OR b.provincia ILIKE :p) "
                " ORDER BY b.provincia, b.nombre LIMIT 100"
            ),
            {
                "v": version,
                "n": f"%{nombre}%" if nombre else None,
                "p": f"%{provincia}%" if provincia else None,
            },
        )
        .mappings()
        .all()
    )

    corte = filas[0]["fecha_corte"] if filas else None
    advertencias = [
        Advertencia(
            codigo=CodigoError.INSUFFICIENT_EVIDENCE,
            detalle=(
                f"Consultado contra el padrón {version} "
                f"(fecha de corte declarada por la fuente: {corte or 'ninguna'}). "
                "El padrón es una foto: que un barrio no figure significa que no estaba en "
                "este corte, no que carezca de protección. La inclusión se consulta y se "
                "gestiona ante el RENABAP (Secretaría de Integración Socio Urbana)."
            ),
        )
    ]
    if version is None:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle="No hay ninguna versión del padrón importada; no se puede responder.",
            )
        )
    elif not filas:
        advertencias.append(
            Advertencia(
                codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                detalle=(
                    f"Ningún barrio coincide con lo buscado en el padrón {version}. "
                    "Una ausencia acá no habilita ninguna conclusión sobre derechos."
                ),
            )
        )

    return Respuesta(
        release_id=contexto.release_id,
        as_of=contexto.as_of,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO if filas else DataStatus.SIN_RESULTADOS,
        data=[BarrioRenabapResumen(**dict(f)) for f in filas],
        evidence=[
            Evidencia(
                evidencia_id=fila["evidencia_id"],
                fragmento=(
                    f"{fila['nombre']} ({fila['id_renabap']}), {fila['provincia']}, "
                    f"padrón {fila['padron_version']}"
                ),
                source_id="F39",
            )
            for fila in filas
        ],
        warnings=advertencias,
    )
