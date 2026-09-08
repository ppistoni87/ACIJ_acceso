"""Gates de publicación.

Los umbrales vienen de `04_Calidad_y_Pruebas.json`. Un gate que falla bloquea la
capacidad afectada, no el release entero: una norma con monto desconocido puede
sustentar una explicación general aunque no pueda responder cuánto se cobra.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# Umbrales declarados en el paquete funcional.
FALLOS_CRITICOS_PERMITIDOS = 0
FKS_HUERFANAS_PERMITIDAS = 0
DUPLICADOS_CANONICOS_PERMITIDOS = 0
AFIRMACIONES_PUBLICADAS_CON_EVIDENCIA_PCT = 100


@dataclass
class ResultadoGate:
    id: str
    descripcion: str
    pasa: bool
    observado: dict = field(default_factory=dict)
    esperado: dict = field(default_factory=dict)


@dataclass
class ResultadoGates:
    gates: list[ResultadoGate] = field(default_factory=list)

    @property
    def pasa(self) -> bool:
        return all(g.pasa for g in self.gates)

    @property
    def fallidos(self) -> list[ResultadoGate]:
        return [g for g in self.gates if not g.pasa]


def evaluar_gates(conexion: Connection, candidatos: list[uuid.UUID]) -> ResultadoGates:
    """Controles que un conjunto de versiones tiene que pasar para publicarse."""
    resultado = ResultadoGates()

    # DQ02: toda afirmación que se publica tiene evidencia verificable.
    sin_evidencia = conexion.execute(
        text(
            "SELECT count(*) FROM afirmaciones "
            " WHERE registro_version_id = ANY(:v) "
            "   AND estado_revision IN ('APPROVED', 'PUBLISHED') "
            "   AND estado_campo = 'INFORMADO' AND evidencia_id IS NULL"
        ),
        {"v": candidatos},
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ02",
            descripcion="Toda afirmación aprobada e informada tiene evidencia.",
            pasa=sin_evidencia == 0,
            observado={"afirmaciones_sin_evidencia": sin_evidencia},
            esperado={"afirmaciones_sin_evidencia": 0},
        )
    )

    # DQ03: los siete campos evaluados en cada versión de norma que se publica.
    sin_evaluar = conexion.execute(
        text(
            "SELECT count(*) FROM norma_versiones nv "
            " WHERE nv.registro_version_id = ANY(:v) "
            "   AND (SELECT count(*) FROM evaluaciones_completitud e "
            "         WHERE e.norma_version_id = nv.registro_version_id) < 7"
        ),
        {"v": candidatos},
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ03",
            descripcion="Cada versión de norma tiene los siete campos evaluados.",
            pasa=sin_evaluar == 0,
            observado={"versiones_con_campos_sin_evaluar": sin_evaluar},
            esperado={"versiones_con_campos_sin_evaluar": 0},
        )
    )

    # DQ05: sin referencias entre versiones equivocadas.
    evidencias_cruzadas = conexion.execute(
        text(
            "SELECT count(*) FROM evidencias e "
            "  JOIN unidades_documentales u ON u.id = e.unidad_id "
            " WHERE u.doc_version_id <> e.doc_version_id"
        )
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ05",
            descripcion="Ninguna evidencia cita una unidad de otra versión.",
            pasa=evidencias_cruzadas == 0,
            observado={"evidencias_cruzadas": evidencias_cruzadas},
            esperado={"evidencias_cruzadas": 0},
        )
    )

    # DQ08: nada se publica sin intervalo de aplicación resuelto.
    sin_vigencia = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones "
            " WHERE id = ANY(:v) AND valid_tipo IN ('DESCONOCIDO', 'CONDICIONADO')"
        ),
        {"v": candidatos},
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ08",
            descripcion="Toda versión candidata tiene su intervalo de aplicación resuelto.",
            pasa=sin_vigencia == 0,
            observado={"versiones_sin_vigencia_resuelta": sin_vigencia},
            esperado={"versiones_sin_vigencia_resuelta": 0},
        )
    )

    # DQ09: sin conflictos críticos abiertos sobre lo que se publica.
    conflictos = conexion.execute(
        text(
            "SELECT count(*) FROM incidencias_revision "
            " WHERE registro_version_id = ANY(:v) "
            "   AND estado IN ('ABIERTA', 'EN_REVISION') AND severidad IN ('CRITICAL', 'HIGH')"
        ),
        {"v": candidatos},
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ09",
            descripcion="No hay conflictos abiertos de severidad alta sobre lo que se publica.",
            pasa=conflictos == 0,
            observado={"conflictos_abiertos": conflictos},
            esperado={"conflictos_abiertos": 0},
        )
    )

    # DQ01: sin duplicados canónicos indebidos.
    duplicados = conexion.execute(
        text(
            "SELECT count(*) FROM ("
            "  SELECT jurisdiccion_id, tipo, numero, anio FROM normas "
            "   WHERE identidad_incierta = false AND numero IS NOT NULL AND anio IS NOT NULL "
            "   GROUP BY 1,2,3,4 HAVING count(*) > 1"
            ") AS d"
        )
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ01",
            descripcion="No hay dos normas con la misma clave canónica.",
            pasa=duplicados == 0,
            observado={"claves_duplicadas": duplicados},
            esperado={"claves_duplicadas": 0},
        )
    )

    # DQ10: la versión candidata está aprobada, no en borrador.
    sin_aprobar = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones "
            " WHERE id = ANY(:v) AND estado_revision NOT IN ('APPROVED', 'PUBLISHED')"
        ),
        {"v": candidatos},
    ).scalar_one()
    resultado.gates.append(
        ResultadoGate(
            id="DQ10",
            descripcion="Toda versión candidata pasó por revisión.",
            pasa=sin_aprobar == 0,
            observado={"versiones_sin_aprobar": sin_aprobar},
            esperado={"versiones_sin_aprobar": 0},
        )
    )

    return resultado
