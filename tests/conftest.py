"""Fixtures compartidas.

Las pruebas de integración corren sobre una base real: las reglas que
verificamos son restricciones, triggers y funciones de PostgreSQL, y un doble no
las ejecutaría.
"""

from __future__ import annotations

import contextlib
import hashlib as _hashlib
import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

URL_ADMIN = os.environ.get(
    "BN_TEST_ADMIN_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres"
)
BASE_PRUEBAS = os.environ.get("BN_TEST_DB", "backend_normativo_test")

# Sin base, casi la mitad de la suite se saltea y pytest termina en cero: «921
# pruebas verdes» pasa a significar «479 corrieron y 442 no», sin que nada lo
# diga. Una integración continua sin servicio de PostgreSQL daría verde sobre un
# sistema mitad sin probar, que es peor que no tener pruebas: tener pruebas que
# mienten.
#
# Así que la ausencia de base es un fallo, no un salteo. Quien quiera correr solo
# las unitarias en una máquina sin PostgreSQL lo pide explícitamente con
# `BN_PRUEBAS_SIN_BASE=1`, y entonces el salteo es una decisión con nombre y no
# un accidente del entorno.
SIN_BASE = os.environ.get("BN_PRUEBAS_SIN_BASE", "").strip().lower() in {"1", "true", "si", "sí"}

MENSAJE_SIN_BASE = (
    "PostgreSQL no está disponible y las pruebas de integración no pueden correr: {error}\n"
    "\n"
    "No se saltean en silencio porque un salteo se cuenta como éxito y estas pruebas son las "
    "que verifican restricciones, disparadores y funciones de la base, que un doble no ejecuta.\n"
    "\n"
    "  Para correrlas:   docker compose up -d db\n"
    "  Para omitirlas:   BN_PRUEBAS_SIN_BASE=1 pytest   (queda dicho que no corrieron)"
)


def _url_pruebas() -> str:
    return URL_ADMIN.rsplit("/", 1)[0] + "/" + BASE_PRUEBAS


@pytest.fixture(scope="session")
def engine_pruebas() -> Iterator[Engine]:
    admin = create_engine(URL_ADMIN, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{BASE_PRUEBAS}" WITH (FORCE)'))
            c.execute(text(f'CREATE DATABASE "{BASE_PRUEBAS}"'))
    except Exception as exc:  # pragma: no cover - entorno sin PostgreSQL
        if SIN_BASE:
            pytest.skip(f"PostgreSQL no disponible y BN_PRUEBAS_SIN_BASE=1: {exc}")
        pytest.fail(MENSAJE_SIN_BASE.format(error=exc), pytrace=False)
    finally:
        admin.dispose()

    os.environ["BN_DATABASE_URL"] = _url_pruebas()

    from alembic import command
    from alembic.config import Config

    from backend_normativo.config import get_settings

    get_settings.cache_clear()
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    engine = create_engine(_url_pruebas(), future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def conexion(engine_pruebas: Engine) -> Iterator[Connection]:
    """Conexión con transacción externa que siempre se revierte: cada prueba ve
    el esquema limpio sin volver a migrar.

    Los triggers de restricción del esquema son `DEFERRABLE INITIALLY DEFERRED`
    porque la carga real inserta grafos completos y necesita cerrarlos antes de
    validarlos. Como las pruebas nunca confirman, se piden inmediatos para que
    la violación aparezca en la sentencia que la produce. El comportamiento
    diferido tiene su propia prueba.
    """
    with engine_pruebas.connect() as conn:
        trans = conn.begin()
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        try:
            yield conn
        finally:
            trans.rollback()


@pytest.fixture
def sesion(conexion: Connection) -> Iterator[Session]:
    with Session(bind=conexion, join_transaction_mode="create_savepoint") as s:
        yield s


@pytest.fixture
def jurisdiccion_nacion(conexion: Connection) -> str:
    conexion.execute(
        text(
            "INSERT INTO jurisdicciones (id, nombre, nivel) "
            "VALUES ('AR', 'República Argentina', 'NACIONAL')"
        )
    )
    return "AR"


@pytest.fixture
def jurisdiccion_caba(conexion: Connection, jurisdiccion_nacion: str) -> str:
    conexion.execute(
        text(
            "INSERT INTO jurisdicciones (id, parent_id, nombre, nivel) "
            "VALUES ('AR-C', :padre, 'Ciudad Autónoma de Buenos Aires', 'CIUDAD_AUTONOMA')"
        ),
        {"padre": jurisdiccion_nacion},
    )
    return "AR-C"


def nuevo_uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def viola_restriccion(conexion: Connection):
    """Espera que el bloque viole una restricción, dejando la transacción usable.

    PostgreSQL aborta la transacción entera ante un error, así que sin un punto
    de retorno una prueba no puede comprobar el rechazo y después el caso
    válido. Este ayudante abre uno y lo revierte.
    """
    import contextlib

    from sqlalchemy.exc import DBAPIError

    @contextlib.contextmanager
    def _ctx(match: str | None = None):
        punto = conexion.begin_nested()
        with pytest.raises(DBAPIError, match=match):
            try:
                yield
            finally:
                punto.rollback()

    return _ctx


POLITICA_PUBLICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"


@pytest.fixture
def crear_fuente(conexion: Connection):
    """Alta de una fuente del catálogo con valores razonables por defecto.

    `politica_acceso` no tiene valor por omisión en el esquema a propósito: una
    fuente sin política declarada no debería existir. Acá se explicita una vez.
    """

    def _crear(
        source_id: str,
        *,
        nombre: str | None = None,
        clase: str = "PORTAL_NORMATIVO",
        estado: str = "ACTIVE",
        access_status: str = "ACCESIBLE",
        prioridad: str = "P0",
        politica_acceso: str = POLITICA_PUBLICA,
        motivo_estado: str | None = None,
    ) -> str:
        conexion.execute(
            text(
                "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
                "prioridad, politica_acceso, motivo_estado) "
                "VALUES (:sid, :nombre, :clase, :estado, :acceso, :prioridad, :politica, :motivo)"
            ),
            {
                "sid": source_id,
                "nombre": nombre or f"Fuente {source_id}",
                "clase": clase,
                "estado": estado,
                "acceso": access_status,
                "prioridad": prioridad,
                "politica": politica_acceso,
                "motivo": motivo_estado,
            },
        )
        return source_id

    return _crear


@pytest.fixture
def cliente_api(engine_pruebas: Engine, conexion: Connection):
    """Cliente de la API atado a la transacción de la prueba.

    Las rutas usan la misma conexión que el resto del caso, así que ven los
    datos que la prueba preparó y todo se revierte al terminar.
    """
    from fastapi.testclient import TestClient

    from backend_normativo.api.app import crear_app
    from backend_normativo.api.dependencias import conexion_administracion, conexion_lectura
    from backend_normativo.api.limites import VARIABLE_LIMITE, reiniciar_limitadores
    from backend_normativo.api.routers.devoluciones import conexion_devolucion
    from backend_normativo.api.routers.recuperacion import abrir_conversacion
    from backend_normativo.api.routers.sesiones import conexion_sesion

    # El límite de consultas queda desactivado para el resto de la suite, a
    # propósito y con nombre. Todas las pruebas comparten el mismo origen
    # («testclient») y el mismo proceso, así que compartirían un solo balde:
    # bastaría con que la suite creciera para que una prueba empezara a fallar
    # por el cupo que gastaron las anteriores, y eso es un fallo que no dice
    # nada de lo que la prueba quería verificar. El límite se prueba donde
    # corresponde, en `tests/integracion/test_limites_de_uso.py`, encendiéndolo.
    anterior = os.environ.get(VARIABLE_LIMITE)
    os.environ[VARIABLE_LIMITE] = "0"
    reiniciar_limitadores()

    app = crear_app()
    app.dependency_overrides[conexion_lectura] = lambda: conexion
    app.dependency_overrides[conexion_administracion] = lambda: conexion
    # La devolución escribe en su propia transacción con el motor de la API.
    # Atada acá a la conexión del caso, la prueba puede verla y se revierte
    # con todo lo demás; los permisos de esa escritura se verifican donde
    # corresponde, en `test_permisos_de_la_api.py`, con el rol de verdad.
    app.dependency_overrides[conexion_devolucion] = lambda: conexion
    app.dependency_overrides[conexion_sesion] = lambda: conexion
    # `/v1/respuestas` abre la conversación en su propia transacción. Atada acá
    # a la conexión del caso, la consulta ve la sesión que la prueba abrió.
    app.dependency_overrides[abrir_conversacion] = lambda: lambda: contextlib.nullcontext(conexion)
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        if anterior is None:
            os.environ.pop(VARIABLE_LIMITE, None)
        else:
            os.environ[VARIABLE_LIMITE] = anterior
        reiniciar_limitadores()


# --- Corpus compartido -------------------------------------------------------
#
# Estas dos fixtures construyen el mismo corpus mínimo que usan las pruebas de
# API, las de aceptación y las de respaldo. Viven acá y no en un módulo de
# pruebas porque importarlas entre módulos hace que la misma fixture quede
# registrada dos veces y el linter no pueda distinguir eso de una redefinición
# por error.


# Son funciones y no solo fixtures porque el recorrido ciudadano (P-015) corre
# contra un servidor de verdad en otro proceso, que no puede ver la transacción
# que una fixture revierte. Necesita el mismo corpus confirmado en su base, y
# «el mismo» tiene que ser literalmente el mismo código: dos corpus parecidos
# que se separan con el tiempo dan una prueba de extremo a extremo que valida un
# sistema que nadie más usa.


def construir_corpus(conexion: Connection):
    from backend_normativo.catalogo.carga import cargar_catalogo
    from backend_normativo.curacion.campos import EvaluadorDeCampos
    from backend_normativo.curacion.identidad import ResolutorIdentidad
    from tests.integracion.test_curacion import _documento_norma

    cargar_catalogo(conexion)
    _documento_norma(
        conexion,
        source_id="D06",
        external_id="normativaba:830431:original",
        tipo_version="ORIGINAL",
        identidad={
            "jurisdiccion": "AR-C",
            "normativaba_id": "830431",
            "tipo": "LEY",
            "numero": "6935",
            "anio": 2025,
            "titulo": "CREA EL PROGRAMA DE APOYO PARA PERSONAS EN VULNERABILIDAD",
            "fechas": {"PUBLICACION": "2025-12-23"},
        },
        unidades=[
            (
                "ARTICULO",
                "2",
                "Art. 2°.- Beneficiarios - Son beneficiarios las personas en situación "
                "de vulnerabilidad habitacional.",
                "DISPOSITIVO",
            ),
            (
                "ARTICULO",
                "3",
                "Art. 3°.- Prestación económica - La prestación consistirá en el pago "
                "de una suma mensual.",
                "DISPOSITIVO",
            ),
        ],
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()
    return conexion.execute(
        text("SELECT norma_id, registro_version_id FROM norma_versiones LIMIT 1")
    ).one()


def publicar_corpus(conexion: Connection, corpus):
    from backend_normativo.curacion.campos import EvaluadorDeCampos
    from backend_normativo.curacion.revision import Revisor
    from backend_normativo.curacion.vigencia import ResolutorVigencia
    from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS
    from backend_normativo.publicacion.release import Publicador

    ResolutorVigencia(conexion).resolver()
    incidencia = conexion.execute(
        text("SELECT id FROM incidencias_revision WHERE tipo = 'VIGENCIA_INDETERMINADA'")
    ).scalar_one()
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    revisor = Revisor(conexion)
    revisor.resolver(
        incidencia,
        decision="Publicada el 23/12/2025, sin norma derogatoria registrada.",
        actor="curacion_juridica:persona",
        fundamento_evidencia_id=evidencia,
        vigencia={
            "valid_tipo": "ABIERTO_FIN",
            "valid_desde": "2025-12-23",
            "estado_legal": "VIGENTE",
        },
    )
    for campo in CAMPOS_SOLICITADOS:
        revisor.aprobar_afirmaciones(corpus.registro_version_id, campo, actor="revisor")
    EvaluadorDeCampos(conexion).evaluar()
    Publicador(conexion).publicar(actor="publicador:equipo", motivo="Primer corte.")
    return corpus


@pytest.fixture
def corpus(conexion: Connection):
    return construir_corpus(conexion)


@pytest.fixture
def corpus_publicado(conexion: Connection, corpus):
    return publicar_corpus(conexion, corpus)


@pytest.fixture
def beneficio_candidato(conexion: Connection, corpus) -> str:
    """Una versión candidata con su fila de subtipo, lista para revisar.

    El corpus mínimo trae normas y no beneficios, así que las pruebas del
    circuito de aprobación se salteaban por falta de material. Un salteo cuenta
    como éxito: seis capacidades del backoffice —aprobar en bloque, comparar
    versiones, el tablero y la transcripción de decisiones— no se estaban
    probando y nadie lo había decidido.
    """
    beneficio = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre, linea, familia) "
            "VALUES ('AR.PRUEBA-REVISION', 'Beneficio de prueba', 'BECA', 'ALIMENTARIA') "
            "RETURNING id"
        )
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde) "
            "VALUES ('beneficio', :b, 1, 'CANDIDATE', 'ABIERTO_FIN', '2025-12-23') RETURNING id"
        ),
        {"b": beneficio},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            " jurisdiccion_id, naturaleza, descripcion) "
            "VALUES (:rv, :b, 'AR-C', 'PRESTACION_MONETARIA', "
            " 'Prestación económica mensual para la prueba del circuito de revisión.')"
        ),
        {"rv": version, "b": beneficio},
    )
    return str(version)


@pytest.fixture
def documento_con_dos_versiones(conexion: Connection, corpus) -> str:
    """El mismo documento capturado dos veces, con el texto cambiado.

    Es lo que el backoffice compara: no dos documentos distintos sino dos
    versiones del mismo, que es donde se ve qué cambió una reforma.
    """
    anterior = conexion.execute(
        text(
            "SELECT id, documento_id, captura_id, version, texto_extraido "
            "  FROM documento_versiones ORDER BY version DESC LIMIT 1"
        )
    ).one()
    texto = (anterior.texto_extraido or "Texto de la versión anterior.").replace(
        "una suma mensual", "una suma mensual actualizada por movilidad"
    )
    conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, "
            " tipo_version, tipo_fecha, texto_extraido, hash_texto, modo_extraccion, "
            " extractor_version) "
            "VALUES (:d, :c, :v, 'ACTUALIZADO', 'PUBLICACION', :t, :h, 'HTML', "
            " 'prueba@1')"
        ),
        {
            "d": anterior.documento_id,
            "c": anterior.captura_id,
            "v": anterior.version + 1,
            "t": texto,
            "h": _hashlib.sha256(texto.encode()).hexdigest(),
        },
    )
    return str(anterior.documento_id)


@pytest.fixture
def regla_candidata(conexion: Connection, corpus, beneficio_candidato) -> str:
    """Una regla candidata con su beneficio, su evidencia y su dependencia.

    El corpus mínimo no trae reglas: las de las otras pruebas entran por las
    lecturas curadas, que son otro camino. Acá hace falta una sola, con lo que
    el expediente tiene que mostrar.
    """
    import uuid as _uuid

    version = beneficio_candidato
    unidad = conexion.execute(
        text(
            "SELECT u.id, u.doc_version_id, u.texto FROM unidades_documentales u "
            " ORDER BY u.orden LIMIT 1"
        )
    ).one()
    evidencia = conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, hash_fragmento, tipo) "
            "VALUES (:dv, :u, :f, :h, 'FRAGMENTO_TEXTO') RETURNING id"
        ),
        {
            "dv": unidad.doc_version_id,
            "u": unidad.id,
            "f": unidad.texto,
            "h": _uuid.uuid4().hex + _uuid.uuid4().hex,
        },
    ).scalar_one()

    def _regla(categoria: str, literal: str) -> str:
        return conexion.execute(
            text(
                "INSERT INTO reglas (beneficio_version_id, evidencia_id, categoria, "
                " texto_literal, descripcion, requiere_revision, estado_revision) "
                "VALUES (:bv, :e, :c, :l, :d, true, 'CANDIDATE') RETURNING id"
            ),
            {
                "bv": version,
                "e": evidencia,
                "c": categoria,
                "l": literal,
                "d": f"Interpretación de {categoria.lower()}.",
            },
        ).scalar_one()

    principal = _regla(
        "APLICABILIDAD",
        "Son beneficiarios las personas en situación de "
        "vulnerabilidad habitacional, conforme el artículo 6.",
    )
    referida = _regla("EXCLUSION", "No accede quien ya perciba otra prestación equivalente.")
    conexion.execute(
        text(
            "INSERT INTO regla_dependencias (regla_id, regla_referida_id, tipo) "
            "VALUES (:a, :b, 'INCOMPATIBLE_CON')"
        ),
        {"a": principal, "b": referida},
    )
    return str(principal)


def version_publicada(conexion: Connection, *, entidad_tipo: str, entidad_id, **campos):
    """Una versión servida por el corte vigente, como la dejaría el publicador.

    Existe porque tres pruebas la armaban a mano y las tres se rompieron el día
    que publicar pasó a registrar la membresía del corte: una versión con
    `release_id` puesto pero sin fila en `release_versiones` está publicada y no
    la sirve nadie. Armarla en un solo lugar es lo que evita que la próxima
    diferencia entre «lo que hace el publicador» y «lo que arma la prueba» se
    descubra con siete pruebas en rojo.
    """
    corte = conexion.execute(
        text(
            "SELECT id FROM releases WHERE estado = 'PUBLICADO'  ORDER BY publicado_en DESC LIMIT 1"
        )
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde, release_id, verificado_en) "
            "VALUES (:t, :e, :n, 'PUBLISHED', 'ABIERTO_FIN', :desde, :r, now()) RETURNING id"
        ),
        {
            "t": entidad_tipo,
            "e": entidad_id,
            "n": campos.get("numero_version", 1),
            "desde": campos.get("valid_desde", "2025-12-23"),
            "r": corte,
        },
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO release_versiones (release_id, registro_version_id, heredada) "
            "VALUES (:r, :v, false)"
        ),
        {"r": corte, "v": version},
    )
    return version
