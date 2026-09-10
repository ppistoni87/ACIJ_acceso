"""Vocabularios controlados del corpus normativo.

Se declaran como `StrEnum` de Python y se materializan en la base como
restricciones `CHECK`, no como tipos `ENUM` de PostgreSQL: agregar un valor a un
vocabulario es una migración de datos revisable y no bloquea la tabla.

Cada vocabulario proviene de la especificación funcional (secciones 2, 3 y 5) o
del diccionario relacional. Ningún valor se inventa acá.
"""

from __future__ import annotations

from enum import StrEnum


def valores(enum_cls: type[StrEnum]) -> tuple[str, ...]:
    """Valores de un vocabulario, para construir el `CHECK` de una columna."""
    return tuple(miembro.value for miembro in enum_cls)


# --- Fuentes (especificación §5) ---------------------------------------------


class EstadoFuente(StrEnum):
    DISCOVERY = "DISCOVERY"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    MANUAL = "MANUAL"
    RETIRED = "RETIRED"


class AccessStatus(StrEnum):
    """Disponibilidad técnica observada. Es independiente de `EstadoFuente`:
    un alias no está necesariamente caído y una fuente activa puede estar
    temporalmente limitada."""

    NO_VERIFICADO = "NO_VERIFICADO"
    ACCESIBLE = "ACCESIBLE"
    ACCESO_LIMITADO = "ACCESO_LIMITADO"  # 403/429 o restricción de robots
    BLOQUEADA = "BLOQUEADA"
    ERROR_TLS = "ERROR_TLS"
    NO_ENCONTRADA = "NO_ENCONTRADA"
    SIN_URL_CONOCIDA = "SIN_URL_CONOCIDA"


class ClaseFuente(StrEnum):
    DATASET = "DATASET"
    BOLETIN = "BOLETIN"
    PORTAL_NORMATIVO = "PORTAL_NORMATIVO"
    FICHA_TRAMITE = "FICHA_TRAMITE"
    DIRECTORIO = "DIRECTORIO"
    DOCUMENTO = "DOCUMENTO"
    PADRON = "PADRON"
    CANAL_ATENCION = "CANAL_ATENCION"
    ALIAS = "ALIAS"
    OTRA = "OTRA"


class PoliticaAcceso(StrEnum):
    """Qué se permite hacer con una fuente. Es una política, no una capacidad
    técnica: una fuente puede estar disponible y aun así no automatizarse."""

    PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS = (
        "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"
    )
    NO_AUTOMATION_UNTIL_IDENTIFIED_AND_PUBLIC = "NO_AUTOMATION_UNTIL_IDENTIFIED_AND_PUBLIC"
    MANUAL_ONLY = "MANUAL_ONLY"


class Prioridad(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class RolUrl(StrEnum):
    ENTRADA = "ENTRADA"
    LISTADO = "LISTADO"
    DETALLE = "DETALLE"
    DESCARGA = "DESCARGA"
    API = "API"
    ANEXO = "ANEXO"
    ALTERNATIVA = "ALTERNATIVA"


class TipoAcceso(StrEnum):
    HTTP_GET_PUBLICO = "HTTP_GET_PUBLICO"
    API_PUBLICA = "API_PUBLICA"
    DESCARGA_ARCHIVO = "DESCARGA_ARCHIVO"
    CARGA_MANUAL = "CARGA_MANUAL"


class Adaptador(StrEnum):
    """Familia técnica del extractor. Un adaptador por familia; los contratos
    específicos por fuente viven en `selector_config`."""

    DATASET_ABIERTO = "DATASET_ABIERTO"
    HTML_ESTATICO = "HTML_ESTATICO"
    API_JSON = "API_JSON"
    PDF = "PDF"
    CARGA_MANUAL = "CARGA_MANUAL"
    SIN_ADAPTADOR = "SIN_ADAPTADOR"


# --- Ingesta -----------------------------------------------------------------


class EstadoCorrida(StrEnum):
    EN_CURSO = "EN_CURSO"
    COMPLETA = "COMPLETA"
    PARCIAL = "PARCIAL"
    FALLIDA = "FALLIDA"
    CANCELADA = "CANCELADA"


class ModoExtraccion(StrEnum):
    HTML = "HTML"
    JSON = "JSON"
    CSV = "CSV"
    PDF_TEXTO = "PDF_TEXTO"
    PDF_OCR = "PDF_OCR"
    MANUAL = "MANUAL"


# --- Documentos y normas -----------------------------------------------------


class TipoDocumento(StrEnum):
    NORMA = "NORMA"
    ANEXO = "ANEXO"
    GUIA = "GUIA"
    FAQ = "FAQ"
    DATASET = "DATASET"
    PROCEDIMIENTO = "PROCEDIMIENTO"
    DIRECTORIO = "DIRECTORIO"
    PADRON = "PADRON"
    OTRO = "OTRO"


class TipoVersionDocumento(StrEnum):
    ORIGINAL = "ORIGINAL"
    ACTUALIZADO = "ACTUALIZADO"
    CONSOLIDADO = "CONSOLIDADO"
    NO_DETERMINADO = "NO_DETERMINADO"


class TipoFecha(StrEnum):
    """Fecha de firma, publicación y cabecera no son equivalentes."""

    SANCION = "SANCION"
    PROMULGACION = "PROMULGACION"
    PUBLICACION = "PUBLICACION"
    FIRMA = "FIRMA"
    CABECERA = "CABECERA"
    ACTUALIZACION_SITIO = "ACTUALIZACION_SITIO"
    DESCONOCIDA = "DESCONOCIDA"


class TipoUnidad(StrEnum):
    PREAMBULO = "PREAMBULO"
    VISTO = "VISTO"
    CONSIDERANDO = "CONSIDERANDO"
    LIBRO = "LIBRO"
    TITULO = "TITULO"
    CAPITULO = "CAPITULO"
    SECCION = "SECCION"
    ARTICULO = "ARTICULO"
    INCISO = "INCISO"
    PARRAFO = "PARRAFO"
    ANEXO = "ANEXO"
    TRANSITORIA = "TRANSITORIA"
    FIRMA = "FIRMA"
    TABLA = "TABLA"
    NO_RECONOCIDO = "NO_RECONOCIDO"


class RolContenido(StrEnum):
    """Distingue una unidad raíz de un texto citado o sustituido dentro de otra.
    Un artículo citado dentro de un artículo no es un artículo raíz.

    `INFORMATIVO` es de otra clase que las demás: no es una parte de una norma
    sino lo que un organismo publica **sobre** un derecho —una página de sedes,
    un cronograma, los canales de atención—. Se cita como «el organismo dice X
    en su página», nunca como «la norma dice X», y por eso el publicador, que
    arma los fragmentos citables con `rol_contenido = 'DISPOSITIVO'`, lo deja
    afuera solo.
    """

    DISPOSITIVO = "DISPOSITIVO"
    CITADO = "CITADO"
    SUSTITUTIVO = "SUSTITUTIVO"
    INCORPORADO = "INCORPORADO"
    HISTORICO = "HISTORICO"
    NOTA = "NOTA"
    INFORMATIVO = "INFORMATIVO"


class TipoEvidencia(StrEnum):
    FRAGMENTO_TEXTO = "FRAGMENTO_TEXTO"
    CELDA_TABLA = "CELDA_TABLA"
    CAMPO_JSON = "CAMPO_JSON"
    CAMPO_CSV = "CAMPO_CSV"
    REGION_PDF = "REGION_PDF"
    CARGA_MANUAL = "CARGA_MANUAL"


class TipoNorma(StrEnum):
    LEY = "LEY"
    DECRETO = "DECRETO"
    RESOLUCION = "RESOLUCION"
    DISPOSICION = "DISPOSICION"
    ORDENANZA = "ORDENANZA"
    DECRETO_LEY = "DECRETO_LEY"
    ACORDADA = "ACORDADA"
    CONVENIO = "CONVENIO"
    CONSTITUCION = "CONSTITUCION"
    TRATADO = "TRATADO"
    OTRO = "OTRO"


class EstadoLegal(StrEnum):
    VIGENTE = "VIGENTE"
    VIGENCIA_PARCIAL = "VIGENCIA_PARCIAL"
    CONDICIONADA = "CONDICIONADA"
    NO_VIGENTE = "NO_VIGENTE"
    NO_DETERMINADA = "NO_DETERMINADA"


class TipoRelacionNormativa(StrEnum):
    CITA = "CITA"
    MODIFICA = "MODIFICA"
    SUSTITUYE = "SUSTITUYE"
    INCORPORA = "INCORPORA"
    DEROGA = "DEROGA"
    ABROGA = "ABROGA"
    RESTABLECE = "RESTABLECE"
    REGLAMENTA = "REGLAMENTA"
    COMPLEMENTA = "COMPLEMENTA"
    CONSOLIDA = "CONSOLIDA"
    PRORROGA = "PRORROGA"
    SUSPENDE = "SUSPENDE"
    TRANSITORIA = "TRANSITORIA"


class TipoEquivalenciaUnidad(StrEnum):
    RENUMERACION = "RENUMERACION"
    SUSTITUCION = "SUSTITUCION"
    DIVISION = "DIVISION"
    FUSION = "FUSION"
    INCORPORACION = "INCORPORACION"


# --- Versiones y revisión ----------------------------------------------------


class EntidadVersionada(StrEnum):
    """Subtipos permitidos del supertipo `registro_versiones`."""

    NORMA = "norma"
    BENEFICIO = "beneficio"
    PARAMETRO_VALOR = "parametro_valor"
    PLAZO = "plazo"
    TRAMITE = "tramite"
    PUNTO_ATENCION = "punto_atencion"
    CANAL = "canal"
    BARRIO_RENABAP = "barrio_renabap"


class EstadoRevision(StrEnum):
    CANDIDATE = "CANDIDATE"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    QUARANTINED = "QUARANTINED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class ValidTipo(StrEnum):
    """Naturaleza del intervalo de aplicación.

    `DESCONOCIDO` nunca se interpreta como vigencia abierta: la ausencia de
    límite conocido no equivale a un límite infinito.
    """

    CERRADO = "CERRADO"  # inicio y fin respaldados
    ABIERTO_FIN = "ABIERTO_FIN"  # la fuente respalda que no hay fin
    ABIERTO_INICIO = "ABIERTO_INICIO"
    PUNTUAL = "PUNTUAL"
    CONDICIONADO = "CONDICIONADO"
    DESCONOCIDO = "DESCONOCIDO"


class EstadoCampo(StrEnum):
    """Estados de un dato sustantivo (especificación §3.3).

    `NO_INFORMADO_EN_FUENTES_REVISADAS` nunca significa `NO_EXISTE`.
    """

    PENDIENTE = "PENDIENTE"
    INFORMADO = "INFORMADO"
    NO_INFORMADO_EN_FUENTES_REVISADAS = "NO_INFORMADO_EN_FUENTES_REVISADAS"
    NO_APLICA_JUSTIFICADO = "NO_APLICA_JUSTIFICADO"
    EN_CONFLICTO = "EN_CONFLICTO"


CAMPOS_SOLICITADOS: tuple[str, ...] = (
    "poblacion_destinataria",
    "criterios_aplicabilidad",
    "plazos",
    "criterios_revocacion",
    "interdependencias",
    "beneficio_otorgado",
    "no_descartar",
)
"""Los siete campos pedidos. Se evalúan por norma y, cuando corresponde, por
beneficio/versión: la relación muchos-a-muchos no se reduce a un texto único."""


# --- Beneficios y reglas -----------------------------------------------------


class NaturalezaBeneficio(StrEnum):
    PRESTACION_MONETARIA = "PRESTACION_MONETARIA"
    PRESTACION_EN_ESPECIE = "PRESTACION_EN_ESPECIE"
    SERVICIO = "SERVICIO"
    EXENCION = "EXENCION"
    PROTECCION = "PROTECCION"
    ACCESO_A_PROCEDIMIENTO = "ACCESO_A_PROCEDIMIENTO"
    OTRO_EFECTO = "OTRO_EFECTO"
    NO_INFORMADA = "NO_INFORMADA"


class RolPersona(StrEnum):
    TITULAR = "TITULAR"
    CAUSANTE = "CAUSANTE"
    SOLICITANTE = "SOLICITANTE"
    REPRESENTANTE = "REPRESENTANTE"
    CONVIVIENTE = "CONVIVIENTE"
    GRUPO_FAMILIAR = "GRUPO_FAMILIAR"


class RolBeneficioNorma(StrEnum):
    CREA = "CREA"
    REGLAMENTA = "REGLAMENTA"
    FINANCIA = "FINANCIA"
    MODIFICA = "MODIFICA"
    INTERPRETA = "INTERPRETA"
    APLICA = "APLICA"


class CategoriaRegla(StrEnum):
    APLICABILIDAD = "APLICABILIDAD"
    EXCLUSION = "EXCLUSION"
    EXCEPCION = "EXCEPCION"
    PRIORIDAD = "PRIORIDAD"
    SALVAGUARDA = "SALVAGUARDA"
    REVOCACION = "REVOCACION"
    SUSPENSION = "SUSPENSION"
    CESE = "CESE"
    SUBSANACION = "SUBSANACION"
    REHABILITACION = "REHABILITACION"
    COMPATIBILIDAD = "COMPATIBILIDAD"


class TipoDependenciaRegla(StrEnum):
    EXCEPCION_DE = "EXCEPCION_DE"
    PRECEDE_A = "PRECEDE_A"
    REQUIERE = "REQUIERE"
    INCOMPATIBLE_CON = "INCOMPATIBLE_CON"


class TipoCuantia(StrEnum):
    FIJO = "FIJO"
    FORMULA = "FORMULA"
    ESPECIE = "ESPECIE"
    NO_INFORMADO = "NO_INFORMADO"


# --- Plazos ------------------------------------------------------------------


class TipoPlazo(StrEnum):
    """Cada tipo tiene identidad propia; no se colapsan en una sola fecha."""

    VIGENCIA_JURIDICA = "VIGENCIA_JURIDICA"
    CONVOCATORIA = "CONVOCATORIA"
    DURACION_BENEFICIO = "DURACION_BENEFICIO"
    RENOVACION = "RENOVACION"
    PRESENTACION_DOCUMENTAL = "PRESENTACION_DOCUMENTAL"
    RESPUESTA_ORGANISMO = "RESPUESTA_ORGANISMO"
    SUBSANACION = "SUBSANACION"
    RECURSO = "RECURSO"
    FECHA_PAGO = "FECHA_PAGO"


class TipoDia(StrEnum):
    CORRIDO = "CORRIDO"
    HABIL_ADMINISTRATIVO = "HABIL_ADMINISTRATIVO"
    HABIL_JUDICIAL = "HABIL_JUDICIAL"
    NO_INFORMADO = "NO_INFORMADO"


# --- Operativo ---------------------------------------------------------------


class PublicoTramite(StrEnum):
    CIUDADANO = "CIUDADANO"
    INSTITUCIONAL = "INSTITUCIONAL"
    AMBOS = "AMBOS"
    NO_INFORMADO = "NO_INFORMADO"


class EstadoOperativo(StrEnum):
    DISPONIBLE = "DISPONIBLE"
    SIN_TURNOS = "SIN_TURNOS"
    SUSPENDIDO = "SUSPENDIDO"
    NO_INFORMADO = "NO_INFORMADO"


class CaracterDeFuente(StrEnum):
    """Con qué autoridad habla una fuente sobre lo que publica.

    Una ONG puede afirmar algo cierto y relevante que el organismo no publica.
    Eso se conserva con su atribución: presentarlo como dicho por el organismo
    le da una autoridad que no tiene, y descartarlo pierde información que a
    alguien le sirve.
    """

    OFICIAL = "OFICIAL"
    SECUNDARIA = "SECUNDARIA"


class AlcanceTerritorial(StrEnum):
    """Hasta dónde llega lo que atiende un punto.

    La jurisdicción dice dónde está; el alcance dice a quién sirve. Una
    defensoría municipal y la provincial comparten provincia y no son
    intercambiables: responder la provincial a quien pregunta por el servicio de
    su municipio lo manda a un organismo sin competencia sobre su reclamo.
    """

    NACIONAL = "NACIONAL"
    PROVINCIAL = "PROVINCIAL"
    MUNICIPAL = "MUNICIPAL"
    NO_DECLARADO = "NO_DECLARADO"


class TipoPuntoAtencion(StrEnum):
    SEDE = "SEDE"
    DELEGACION = "DELEGACION"
    OFICINA_MOVIL = "OFICINA_MOVIL"
    CENTRO_COMUNITARIO = "CENTRO_COMUNITARIO"
    JUZGADO = "JUZGADO"
    OTRO = "OTRO"


class TipoCanal(StrEnum):
    PRESENCIAL = "PRESENCIAL"
    TELEFONO = "TELEFONO"
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    WEB = "WEB"
    FORMULARIO_WEB = "FORMULARIO_WEB"
    REDES_SOCIALES = "REDES_SOCIALES"
    CORREO_POSTAL = "CORREO_POSTAL"


class TipoOrganismo(StrEnum):
    EMISOR = "EMISOR"
    AUTORIDAD_APLICACION = "AUTORIDAD_APLICACION"
    PRESTADOR = "PRESTADOR"
    ORGANISMO_CONTROL = "ORGANISMO_CONTROL"
    ONG = "ONG"
    OTRO = "OTRO"


class NivelJurisdiccion(StrEnum):
    NACIONAL = "NACIONAL"
    PROVINCIAL = "PROVINCIAL"
    CIUDAD_AUTONOMA = "CIUDAD_AUTONOMA"
    MUNICIPAL = "MUNICIPAL"
    COMUNAL = "COMUNAL"
    SUPRANACIONAL = "SUPRANACIONAL"


# --- Calidad, publicación y eventos -----------------------------------------


class ResultadoControl(StrEnum):
    PASA = "PASA"
    FALLA = "FALLA"
    ADVERTENCIA = "ADVERTENCIA"
    NO_APLICA = "NO_APLICA"


class Severidad(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class TipoIncidencia(StrEnum):
    CONFLICTO_DE_FUENTES = "CONFLICTO_DE_FUENTES"
    IDENTIDAD_AMBIGUA = "IDENTIDAD_AMBIGUA"
    DISCREPANCIA_NUMERACION = "DISCREPANCIA_NUMERACION"
    VIGENCIA_INDETERMINADA = "VIGENCIA_INDETERMINADA"
    COBERTURA_EXTRACCION = "COBERTURA_EXTRACCION"
    ACCESO_BLOQUEADO = "ACCESO_BLOQUEADO"
    CAMBIO_DE_ESQUEMA = "CAMBIO_DE_ESQUEMA"
    DATO_FALTANTE_CRITICO = "DATO_FALTANTE_CRITICO"
    # El original detrás de una afirmación ya no se puede recuperar: falta del
    # almacén o sus bytes no hashean a lo que la captura declara.
    EVIDENCIA_NO_RECUPERABLE = "EVIDENCIA_NO_RECUPERABLE"


class EstadoIncidencia(StrEnum):
    ABIERTA = "ABIERTA"
    EN_REVISION = "EN_REVISION"
    RESUELTA = "RESUELTA"
    DIFERIDA = "DIFERIDA"


class EstadoRelease(StrEnum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    REVERTIDO = "REVERTIDO"


class Capacidad(StrEnum):
    """Capacidades publicables (especificación §5). Cada una declara sus campos
    críticos: una norma con monto desconocido puede sustentar una explicación
    general y aun así abstenerse de responder "cuánto cobro"."""

    IDENTIFICACION = "IDENTIFICACION"
    DESCRIPCION_GENERAL = "DESCRIPCION_GENERAL"
    REQUISITOS = "REQUISITOS"
    EVALUACION_PRELIMINAR = "EVALUACION_PRELIMINAR"
    MONTO = "MONTO"
    PLAZO = "PLAZO"
    CANAL = "CANAL"
    EXPLICACION_HISTORICA = "EXPLICACION_HISTORICA"


class TipoChunk(StrEnum):
    UNIDAD_NORMATIVA = "UNIDAD_NORMATIVA"
    PROCEDIMIENTO = "PROCEDIMIENTO"
    FAQ = "FAQ"
    ANEXO = "ANEXO"


class TipoEventoOutbox(StrEnum):
    RELEASE_PUBLICADO = "RELEASE_PUBLICADO"
    NORMA_ACTUALIZADA = "NORMA_ACTUALIZADA"
    VALOR_ACTUALIZADO = "VALOR_ACTUALIZADO"
    PLAZO_ACTUALIZADO = "PLAZO_ACTUALIZADO"
    CANAL_ACTUALIZADO = "CANAL_ACTUALIZADO"
    CONFLICTO_ABIERTO = "CONFLICTO_ABIERTO"
    FUENTE_DEGRADADA = "FUENTE_DEGRADADA"


class EstadoFuenteCandidata(StrEnum):
    NUEVA = "NUEVA"
    EN_EVALUACION = "EN_EVALUACION"
    PROMOVIDA = "PROMOVIDA"
    DESCARTADA = "DESCARTADA"
    DUPLICADA = "DUPLICADA"


class EstadoReferenciaPendiente(StrEnum):
    PENDIENTE = "PENDIENTE"
    RESUELTA = "RESUELTA"
    IRRESOLUBLE = "IRRESOLUBLE"
