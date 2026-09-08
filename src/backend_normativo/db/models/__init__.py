"""Modelo relacional del backend normativo.

Importar este paquete registra las 53 tablas en `Base.metadata`. El orden de
importación no expresa dependencias: las claves foráneas se declaran por nombre
de tabla y SQLAlchemy resuelve el grafo al crear el esquema.
"""

from backend_normativo.db.base import Base
from backend_normativo.db.models.beneficios import (
    Beneficio,
    BeneficioCuantia,
    BeneficioNorma,
    BeneficioPoblacion,
    BeneficioVersion,
    CuantiaParametro,
    Parametro,
    ParametroValor,
    Poblacion,
    Regla,
    ReglaDependencia,
    ReglaParametro,
)
from backend_normativo.db.models.calidad import ControlCalidad, IncidenciaRevision
from backend_normativo.db.models.captura import (
    Captura,
    CorridaIngesta,
    Documento,
    DocumentoVersion,
    Evidencia,
    UnidadDocumental,
)
from backend_normativo.db.models.catalogo import (
    Fuente,
    FuenteCandidata,
    FuenteConfigVersion,
    FuenteUrl,
    Jurisdiccion,
    Organismo,
)
from backend_normativo.db.models.hechos import (
    Afirmacion,
    CompletitudAfirmacion,
    Derivacion,
    DerivacionInsumo,
    EvaluacionCompletitud,
)
from backend_normativo.db.models.normas import (
    EquivalenciaUnidad,
    Norma,
    NormaIdentificador,
    NormaVersion,
    ReferenciaPendiente,
    RegistroVersion,
    RelacionNormativa,
)
from backend_normativo.db.models.operativo import (
    BarrioRenabap,
    Canal,
    PuntoAtencion,
    PuntoVersion,
    Tramite,
    TramitePaso,
    TramiteVersion,
)
from backend_normativo.db.models.plazos import Calendario, CalendarioExcepcion, Plazo
from backend_normativo.db.models.publicacion import (
    AuditoriaEvento,
    Chunk,
    ConsultaAuditada,
    EventoOutbox,
    Release,
)

__all__ = [
    "Afirmacion",
    "AuditoriaEvento",
    "BarrioRenabap",
    "Base",
    "Beneficio",
    "BeneficioCuantia",
    "BeneficioNorma",
    "BeneficioPoblacion",
    "BeneficioVersion",
    "Calendario",
    "CalendarioExcepcion",
    "Canal",
    "Captura",
    "Chunk",
    "CompletitudAfirmacion",
    "ConsultaAuditada",
    "ControlCalidad",
    "CorridaIngesta",
    "CuantiaParametro",
    "Derivacion",
    "DerivacionInsumo",
    "Documento",
    "DocumentoVersion",
    "EquivalenciaUnidad",
    "EvaluacionCompletitud",
    "EventoOutbox",
    "Evidencia",
    "Fuente",
    "FuenteCandidata",
    "FuenteConfigVersion",
    "FuenteUrl",
    "IncidenciaRevision",
    "Jurisdiccion",
    "Norma",
    "NormaIdentificador",
    "NormaVersion",
    "Organismo",
    "Parametro",
    "ParametroValor",
    "Plazo",
    "Poblacion",
    "PuntoAtencion",
    "PuntoVersion",
    "ReferenciaPendiente",
    "RegistroVersion",
    "Regla",
    "ReglaDependencia",
    "ReglaParametro",
    "RelacionNormativa",
    "Release",
    "Tramite",
    "TramitePaso",
    "TramiteVersion",
    "UnidadDocumental",
]
