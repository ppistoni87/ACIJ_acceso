"""`POST /v1/evaluaciones-preliminares`.

La operación más delicada del contrato: la que una persona va a leer como si
dijera si le corresponde un derecho. No lo dice. Devuelve qué condiciones se
cumplen con lo que declaró, cuáles no, cuáles quedan sin saber, qué salvaguardas
hay que tener en cuenta y qué falta preguntar.

El cuerpo de la solicitud no se persiste. Los hechos que declara una persona
sobre su edad, sus ingresos o su hogar son datos sensibles y no forman parte del
corpus normativo.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text

from backend_normativo.api.contratos import (
    Advertencia,
    CodigoError,
    DataStatus,
    ErrorRespuesta,
    Evidencia,
    Respuesta,
)
from backend_normativo.api.dependencias import Contexto
from backend_normativo.db.vocabularios import CategoriaRegla
from backend_normativo.reglas.beneficio import ReglaEvaluable, evaluar_beneficio
from backend_normativo.reglas.evaluacion import Evaluador, HechosDeclarados

router = APIRouter(prefix="/v1/evaluaciones-preliminares", tags=["evaluación"])


class SolicitudEvaluacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beneficio_id: uuid.UUID
    # Hechos mínimos que la persona decide declarar. Lo que no declare queda
    # como desconocido, no como negativo.
    hechos: dict[str, object] = Field(default_factory=dict)
    fecha: dt.date | None = None


class CondicionRespuesta(BaseModel):
    texto_literal: str
    categoria: str
    resultado: str
    explicacion: str | None = None
    alcance: str | None = None


class ResultadoEvaluacion(BaseModel):
    resultado: str
    condiciones_cumplidas: list[CondicionRespuesta] = Field(default_factory=list)
    condiciones_no_cumplidas: list[CondicionRespuesta] = Field(default_factory=list)
    condiciones_desconocidas: list[CondicionRespuesta] = Field(default_factory=list)
    salvaguardas: list[CondicionRespuesta] = Field(default_factory=list)
    reglas_posteriores: list[CondicionRespuesta] = Field(default_factory=list)
    preguntas_faltantes: list[str] = Field(default_factory=list)
    reglas_evaluadas: list[str] = Field(default_factory=list)
    aclaracion: str = (
        "Esta es una orientación preliminar sobre lo que dicen las normas publicadas. "
        "No otorga, no rechaza y no revoca ninguna prestación: la decisión la toma el "
        "organismo competente."
    )


def _resolver_parametro(conexion: Connection, release_id: uuid.UUID | None):
    """Valor aprobado de un parámetro a una fecha, o nada.

    Nunca devuelve el último valor por fecha máxima sin verificar que se aplique
    a la fecha consultada: servir el monto de otro período es la forma más
    directa de dar una respuesta incorrecta que parece correcta.
    """

    def resolver(codigo: str, fecha: dt.date) -> decimal.Decimal | None:
        return conexion.execute(
            text(
                "SELECT pv.valor FROM parametro_valores pv "
                "  JOIN parametros p ON p.id = pv.parametro_id "
                "  JOIN registro_versiones rv ON rv.id = pv.registro_version_id "
                " WHERE p.codigo = :c AND pv.publicable "
                "   AND pv.rango_aplicacion @> :f "
                "   AND (:r::uuid IS NULL OR rv.release_id = :r) "
                " LIMIT 1"
            ),
            {"c": codigo, "f": fecha, "r": release_id},
        ).scalar_one_or_none()

    return resolver


def _reglas_publicadas(conexion: Connection, beneficio_id: uuid.UUID) -> list[ReglaEvaluable]:
    filas = (
        conexion.execute(
            text(
                "SELECT r.id, r.categoria, r.texto_literal, r.ast, r.requiere_revision, r.alcance "
                "  FROM reglas r "
                "  JOIN beneficio_versiones bv "
                "    ON bv.registro_version_id = r.beneficio_version_id "
                "  JOIN registro_versiones rv ON rv.id = bv.registro_version_id "
                " WHERE bv.beneficio_id = :b AND rv.estado_revision = 'PUBLISHED'"
            ),
            {"b": beneficio_id},
        )
        .mappings()
        .all()
    )

    dependencias: dict[uuid.UUID, list[uuid.UUID]] = {}
    for fila in conexion.execute(
        text(
            "SELECT regla_id, regla_referida_id FROM regla_dependencias "
            " WHERE tipo = 'EXCEPCION_DE'"
        )
    ):
        dependencias.setdefault(fila[0], []).append(fila[1])

    return [
        ReglaEvaluable(
            id=fila["id"],
            categoria=CategoriaRegla(fila["categoria"]),
            texto_literal=fila["texto_literal"],
            ast=fila["ast"],
            requiere_revision=fila["requiere_revision"],
            alcance=fila["alcance"],
            excepcion_de=tuple(dependencias.get(fila["id"], ())),
        )
        for fila in filas
    ]


def _condiciones(evaluadas) -> list[CondicionRespuesta]:
    return [
        CondicionRespuesta(
            texto_literal=c.texto_literal,
            categoria=c.categoria.value,
            resultado=c.resultado.value,
            explicacion=(
                c.motivo_no_ejecutable
                if c.motivo_no_ejecutable
                else (c.detalle.descripcion if c.detalle else None)
            ),
            alcance=c.alcance,
        )
        for c in evaluadas
    ]


@router.post("", response_model=Respuesta[ResultadoEvaluacion])
def evaluar(
    solicitud: SolicitudEvaluacion, contexto: Contexto = Depends()
) -> Respuesta[ResultadoEvaluacion]:
    beneficio = (
        contexto.conexion.execute(
            text("SELECT codigo, nombre FROM beneficios WHERE id = :b"),
            {"b": solicitud.beneficio_id},
        )
        .mappings()
        .first()
    )
    if beneficio is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorRespuesta(
                codigo=CodigoError.UNKNOWN_IDENTITY,
                detalle=f"No hay ningún beneficio con el identificador {solicitud.beneficio_id}.",
                as_of=contexto.as_of,
                known_at=contexto.known_at,
            ).model_dump(mode="json"),
        )

    reglas = _reglas_publicadas(contexto.conexion, solicitud.beneficio_id)
    if not reglas:
        # Sin reglas publicadas no hay evaluación posible. Se dice, no se
        # devuelve un resultado vacío que parezca una negativa.
        return Respuesta(
            release_id=contexto.release_id,
            as_of=solicitud.fecha or contexto.as_of,
            known_at=contexto.known_at,
            data_status=DataStatus.NO_PUBLICABLE,
            data=ResultadoEvaluacion(resultado="REQUIERE_REVISION"),
            warnings=[
                Advertencia(
                    codigo=CodigoError.INSUFFICIENT_EVIDENCE,
                    detalle=(
                        f"El beneficio «{beneficio['nombre']}» no tiene reglas publicadas: "
                        "no se puede evaluar la aplicabilidad todavía."
                    ),
                )
            ],
        )

    fecha = solicitud.fecha or contexto.as_of
    hechos = HechosDeclarados(valores=solicitud.hechos, fecha=fecha)
    evaluador = Evaluador(
        resolver_parametro=_resolver_parametro(contexto.conexion, contexto.release_id)
    )
    dictamen = evaluar_beneficio(reglas, hechos, evaluador)

    evidencias = [
        Evidencia(evidencia_id=fila[0], fragmento=fila[1])
        for fila in contexto.conexion.execute(
            text(
                "SELECT e.id, e.fragmento FROM reglas r "
                "  JOIN evidencias e ON e.id = r.evidencia_id "
                " WHERE r.id = ANY(:ids)"
            ),
            {"ids": [r.id for r in reglas]},
        )
    ]

    return Respuesta(
        release_id=contexto.release_id,
        as_of=fecha,
        known_at=contexto.known_at,
        data_status=DataStatus.PUBLICADO,
        data=ResultadoEvaluacion(
            resultado=dictamen.resultado.value,
            condiciones_cumplidas=_condiciones(dictamen.cumplidas),
            condiciones_no_cumplidas=_condiciones(dictamen.no_cumplidas),
            condiciones_desconocidas=_condiciones(dictamen.desconocidas + dictamen.no_ejecutables),
            salvaguardas=_condiciones(dictamen.salvaguardas),
            reglas_posteriores=_condiciones(dictamen.posteriores),
            preguntas_faltantes=dictamen.preguntas_faltantes,
            reglas_evaluadas=[str(r.id) for r in reglas],
        ),
        evidence=evidencias,
        missing_fields=dictamen.preguntas_faltantes,
        warnings=[
            Advertencia(codigo=CodigoError.INSUFFICIENT_EVIDENCE, detalle=a)
            for a in dictamen.advertencias
        ],
    )
