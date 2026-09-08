"""HU-023, HU-024 y HU-025: vigencia, revisión y publicación atómica."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.campos import EvaluadorDeCampos
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.curacion.revision import (
    ConflictoDeVersion,
    DecisionInvalida,
    Revisor,
)
from backend_normativo.curacion.vigencia import ResolutorVigencia
from backend_normativo.politicas import vigencia as politica
from backend_normativo.publicacion.release import (
    NadaQuePublicar,
    PublicacionRechazada,
    Publicador,
)
from tests.integracion.test_curacion import _documento_norma

pytestmark = pytest.mark.integracion


def _norma(conexion: Connection, **extra) -> uuid.UUID:
    identidad = {
        "jurisdiccion": "AR-C",
        "normativaba_id": extra.pop("normativaba_id", "830431"),
        "tipo": "LEY",
        "numero": extra.pop("numero", "6935"),
        "anio": 2025,
        "titulo": "CREA EL PROGRAMA DE APOYO",
        "fechas": {"PUBLICACION": "2025-12-23"},
    }
    identidad.update(extra.pop("identidad", {}))
    _documento_norma(
        conexion,
        source_id=extra.pop("source_id", "D06"),
        external_id=extra.pop("external_id", "normativaba:830431:original"),
        tipo_version="ORIGINAL",
        identidad=identidad,
        unidades=[
            (
                "ARTICULO",
                "2",
                "Art. 2°.- Beneficiarios - Son beneficiarios del presente programa las "
                "personas en situación de vulnerabilidad habitacional.",
                "DISPOSITIVO",
            ),
            (
                "ARTICULO",
                "6",
                "Art. 6°.- Requisitos de acceso - Para acceder deberán acreditar "
                "residencia, salvo imposibilidad fundada.",
                "DISPOSITIVO",
            ),
        ],
        **extra,
    )
    ResolutorIdentidad(conexion).resolver_pendientes()
    EvaluadorDeCampos(conexion).evaluar()
    return conexion.execute(
        text("SELECT registro_version_id FROM norma_versiones LIMIT 1")
    ).scalar_one()


@pytest.fixture
def version_candidata(conexion: Connection):
    cargar_catalogo(conexion)
    return _norma(conexion)


# --- Vigencia ------------------------------------------------------------------


def test_sin_estado_declarado_la_vigencia_va_a_revision(
    conexion: Connection, version_candidata
) -> None:
    """La ausencia de una derogación registrada no prueba que la norma rija."""
    resultado = ResolutorVigencia(conexion).resolver()
    assert resultado.resueltas_por_politica == 0
    assert resultado.derivadas_a_revision == 1

    incidencia = conexion.execute(
        text("SELECT descripcion FROM incidencias_revision WHERE tipo = 'VIGENCIA_INDETERMINADA'")
    ).scalar_one()
    assert "no prueba que la norma siga rigiendo" in incidencia


def test_una_etiqueta_no_vigente_no_alcanza_para_cerrar_la_vigencia(conexion: Connection) -> None:
    """F23: una norma "no vigente" pudo incorporar disposiciones que siguen
    aplicándose a través de la norma que modificó."""
    dictamen = politica.dictaminar(
        estado_declarado="NO_VIGENTE",
        tiene_fecha_inicio=True,
        cierres_aprobados=0,
        reaperturas_aprobadas=0,
        tiene_evidencia_de_estado=True,
    )
    assert dictamen.automatica is False
    assert dictamen.requiere_revision is True
    assert "siguen aplicándose" in dictamen.fundamento


def test_abrogada_y_restablecida_no_tiene_lectura_automatica() -> None:
    """F33: la Ley 24.714 fue abrogada y su vigencia restablecida con
    excepciones. El grafo no alcanza para deducirlo."""
    dictamen = politica.dictaminar(
        estado_declarado=None,
        tiene_fecha_inicio=True,
        cierres_aprobados=1,
        reaperturas_aprobadas=1,
        tiene_evidencia_de_estado=True,
    )
    assert dictamen.automatica is False
    assert "excepciones" in dictamen.fundamento


def test_la_politica_solo_resuelve_lo_que_la_fuente_declara(conexion: Connection) -> None:
    dictamen = politica.dictaminar(
        estado_declarado="VIGENTE",
        tiene_fecha_inicio=True,
        cierres_aprobados=0,
        reaperturas_aprobadas=0,
        tiene_evidencia_de_estado=True,
    )
    assert dictamen.automatica is True
    assert politica.VERSION in dictamen.fundamento

    # Sin la evidencia de esa declaración, no se aplica.
    sin_evidencia = politica.dictaminar(
        estado_declarado="VIGENTE",
        tiene_fecha_inicio=True,
        cierres_aprobados=0,
        reaperturas_aprobadas=0,
        tiene_evidencia_de_estado=False,
    )
    assert sin_evidencia.automatica is False


# --- Revisión -------------------------------------------------------------------


def _incidencia_de_vigencia(conexion: Connection) -> uuid.UUID:
    ResolutorVigencia(conexion).resolver()
    return conexion.execute(
        text("SELECT id FROM incidencias_revision WHERE tipo = 'VIGENCIA_INDETERMINADA'")
    ).scalar_one()


def _evidencia_cualquiera(conexion: Connection) -> uuid.UUID:
    return conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()


def test_una_decision_de_vigencia_exige_fundamento(conexion: Connection, version_candidata) -> None:
    incidencia = _incidencia_de_vigencia(conexion)
    with pytest.raises(DecisionInvalida, match="evidencia"):
        Revisor(conexion).resolver(
            incidencia,
            decision="Se aprueba como vigente.",
            actor="revisor",
            vigencia={"valid_tipo": "ABIERTO_FIN", "estado_legal": "VIGENTE"},
        )


def test_una_decision_exige_decir_quien_decide(conexion: Connection, version_candidata) -> None:
    incidencia = _incidencia_de_vigencia(conexion)
    with pytest.raises(DecisionInvalida, match="quién decidió"):
        Revisor(conexion).resolver(incidencia, decision="Se aprueba.", actor="  ")


def test_resolver_deja_actor_fundamento_y_bitacora(conexion: Connection, version_candidata) -> None:
    incidencia = _incidencia_de_vigencia(conexion)
    Revisor(conexion).resolver(
        incidencia,
        decision="Publicada el 23/12/2025 sin norma derogatoria registrada.",
        actor="curacion_juridica:persona",
        fundamento_evidencia_id=_evidencia_cualquiera(conexion),
        vigencia={
            "valid_tipo": "ABIERTO_FIN",
            "valid_desde": "2025-12-23",
            "estado_legal": "VIGENTE",
        },
    )
    fila = conexion.execute(
        text(
            "SELECT estado, decidido_por, decision, resuelta_en, fundamento_evidencia_id "
            "FROM incidencias_revision WHERE id = :i"
        ),
        {"i": incidencia},
    ).one()
    assert fila.estado == "RESUELTA"
    assert fila.decidido_por == "curacion_juridica:persona"
    assert fila.resuelta_en is not None
    assert fila.fundamento_evidencia_id is not None

    bitacora = conexion.execute(
        text("SELECT actor, accion FROM auditoria_eventos WHERE accion = 'RESOLVER_INCIDENCIA'")
    ).one()
    assert bitacora.actor == "curacion_juridica:persona"


def test_resolver_dos_veces_falla_por_conflicto_de_version(
    conexion: Connection, version_candidata
) -> None:
    """Es el 409 del contrato de API: alguien más ya la movió."""
    incidencia = _incidencia_de_vigencia(conexion)
    argumentos = {
        "decision": "Se aprueba.",
        "actor": "revisor",
        "fundamento_evidencia_id": _evidencia_cualquiera(conexion),
        "vigencia": {
            "valid_tipo": "ABIERTO_FIN",
            "valid_desde": "2025-12-23",
            "estado_legal": "VIGENTE",
        },
    }
    Revisor(conexion).resolver(incidencia, **argumentos)
    with pytest.raises(ConflictoDeVersion):
        Revisor(conexion).resolver(incidencia, **argumentos)


# --- Publicación ----------------------------------------------------------------


def _aprobar_todo(conexion: Connection, version_id: uuid.UUID) -> None:
    from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS

    incidencia = _incidencia_de_vigencia(conexion)
    revisor = Revisor(conexion)
    revisor.resolver(
        incidencia,
        decision="Publicada el 23/12/2025 sin norma derogatoria registrada.",
        actor="curacion_juridica:persona",
        fundamento_evidencia_id=_evidencia_cualquiera(conexion),
        vigencia={
            "valid_tipo": "ABIERTO_FIN",
            "valid_desde": "2025-12-23",
            "estado_legal": "VIGENTE",
        },
    )
    for campo in CAMPOS_SOLICITADOS:
        revisor.aprobar_afirmaciones(version_id, campo, actor="curacion_juridica:persona")
    EvaluadorDeCampos(conexion).evaluar()


def test_no_se_publica_lo_que_no_paso_por_revision(conexion: Connection, version_candidata) -> None:
    with pytest.raises(PublicacionRechazada):
        Publicador(conexion).publicar(actor="publicador", motivo="intento prematuro")


def test_la_cuarentena_dice_por_que_no_se_publica_cada_cosa(
    conexion: Connection, version_candidata
) -> None:
    """Sin esta lista, "no aparece en la respuesta" y "no existe" serían
    indistinguibles."""
    cuarentena = Publicador(conexion).cuarentena()
    assert cuarentena
    motivos = cuarentena[0]["motivos"]
    assert any("intervalo de aplicación" in m for m in motivos)
    assert any("estado de revisión" in m for m in motivos)


def test_publicar_deja_release_fragmentos_evento_y_bitacora(
    conexion: Connection, version_candidata
) -> None:
    _aprobar_todo(conexion, version_candidata)
    resultado = Publicador(conexion).publicar(
        actor="publicador:equipo", motivo="Primer corte revisado."
    )

    assert resultado.versiones_publicadas == 1
    assert resultado.chunks_creados > 0
    assert resultado.eventos_emitidos == 1

    release = conexion.execute(
        text("SELECT estado, manifest_hash, aprobado_por FROM releases WHERE id = :r"),
        {"r": resultado.release_id},
    ).one()
    assert release.estado == "PUBLICADO"
    assert len(release.manifest_hash) == 64
    assert release.aprobado_por == "publicador:equipo"

    # El evento existe pero nadie lo entregó todavía.
    evento = conexion.execute(text("SELECT tipo, entregado_en, intentos FROM eventos_outbox")).one()
    assert evento.tipo == "RELEASE_PUBLICADO"
    assert evento.entregado_en is None
    assert evento.intentos == 0


def test_solo_se_indexa_texto_dispositivo(conexion: Connection, version_candidata) -> None:
    """Recuperar una nota editorial como si fuera la norma haría que una
    respuesta cite algo que la norma no dice."""
    _aprobar_todo(conexion, version_candidata)
    resultado = Publicador(conexion).publicar(actor="publicador", motivo="corte")

    roles = set(
        conexion.execute(
            text(
                "SELECT DISTINCT u.rol_contenido FROM chunks c "
                "JOIN unidades_documentales u ON u.id = c.unidad_id "
                "WHERE c.release_id = :r"
            ),
            {"r": resultado.release_id},
        ).scalars()
    )
    assert roles == {"DISPOSITIVO"}


def test_una_version_publicada_se_sirve_solo_en_las_capacidades_que_sustenta(
    conexion: Connection, version_candidata
) -> None:
    """Una norma puede sustentar una explicación general y aun así abstenerse de
    responder cuánto se cobra."""
    _aprobar_todo(conexion, version_candidata)
    Publicador(conexion).publicar(actor="publicador", motivo="corte")

    def servibles(capacidad: str) -> int:
        return conexion.execute(
            text("SELECT count(*) FROM v_hechos_servibles(:f, now(), :c)"),
            {"f": dt.date.today(), "c": capacidad},
        ).scalar_one()

    assert servibles("IDENTIFICACION") == 1
    assert servibles("REQUISITOS") == 1
    # `plazos` quedó sin información en esta norma: la capacidad se abstiene.
    assert servibles("PLAZO") == 0


def test_revertir_deja_de_servir_sin_borrar_nada(conexion: Connection, version_candidata) -> None:
    _aprobar_todo(conexion, version_candidata)
    resultado = Publicador(conexion).publicar(actor="publicador", motivo="corte")

    afectadas = Publicador(conexion).revertir(
        resultado.release_id, actor="publicador", motivo="Se detectó un error de curación."
    )
    assert afectadas == 1

    estado = conexion.execute(
        text("SELECT estado FROM releases WHERE id = :r"), {"r": resultado.release_id}
    ).scalar_one()
    assert estado == "REVERTIDO"
    # Los fragmentos siguen existiendo: revertir no borra historial.
    assert conexion.execute(text("SELECT count(*) FROM chunks")).scalar_one() > 0
    assert (
        conexion.execute(
            text("SELECT count(*) FROM v_hechos_servibles(current_date, now(), 'IDENTIFICACION')")
        ).scalar_one()
        == 0
    )


def test_cada_control_queda_atado_a_la_version_que_evaluo(
    conexion: Connection, version_candidata
) -> None:
    _aprobar_todo(conexion, version_candidata)
    Publicador(conexion).publicar(actor="publicador", motivo="corte")

    controles = conexion.execute(
        text(
            "SELECT control_id, resultado, registro_version_id FROM controles_calidad "
            "WHERE version = 'gates@1'"
        )
    ).all()
    assert controles
    assert all(c.resultado == "PASA" for c in controles)
    assert all(c.registro_version_id is not None for c in controles)
    assert {c.control_id for c in controles} >= {"DQ02", "DQ03", "DQ08", "DQ09"}


def test_publicar_sin_candidatos_no_se_confunde_con_un_control_fallido(
    conexion: Connection,
) -> None:
    """No es lo mismo que falten controles a que no haya nada que publicar.

    Decirlo con las palabras de un control fallido —«no pasa los controles de
    calidad:» seguido de nada— manda a buscar un problema de calidad donde lo
    que hay es que ya está todo publicado o que todavía no se aprobó nada.
    """
    cargar_catalogo(conexion)

    with pytest.raises(NadaQuePublicar) as caido:
        Publicador(conexion).publicar(actor="publicacion:prueba", motivo="sin nada que publicar")

    mensaje = str(caido.value)
    assert "No hay ninguna versión para publicar" in mensaje
    assert "no pasa los controles de calidad" not in mensaje
    # Sigue siendo un rechazo: quien captura el caso general lo sigue capturando.
    assert isinstance(caido.value, PublicacionRechazada)


def test_publicar_antes_de_aprobar_los_campos_lo_avisa(
    conexion: Connection, version_candidata
) -> None:
    """Es el orden que se equivoca solo.

    La publicación es lo que promueve las afirmaciones a PUBLISHED. Aprobarlas
    después no entra en ese release: la versión queda publicada y su ficha se
    sirve sin una sola cita, que es indistinguible de una norma sin respaldo.
    Publicar igual está permitido —una versión puede no tener nada informado que
    aprobar— pero no en silencio.
    """
    incidencia = _incidencia_de_vigencia(conexion)
    Revisor(conexion).resolver(
        incidencia,
        decision="Publicada el 23/12/2025 sin norma derogatoria registrada.",
        actor="curacion_juridica:persona",
        fundamento_evidencia_id=_evidencia_cualquiera(conexion),
        vigencia={
            "valid_tipo": "ABIERTO_FIN",
            "valid_desde": "2025-12-23",
            "estado_legal": "VIGENTE",
        },
    )
    EvaluadorDeCampos(conexion).evaluar()

    resultado = Publicador(conexion).publicar(
        actor="publicacion:prueba", motivo="corte publicado sin aprobar los campos"
    )

    assert resultado.versiones_publicadas == 1
    assert len(resultado.sin_afirmaciones_aprobadas) == 1


def test_publicar_con_los_campos_aprobados_no_avisa_nada(
    conexion: Connection, version_candidata
) -> None:
    """El camino correcto no tiene que hacer ruido: aprobar y después publicar."""
    _aprobar_todo(conexion, version_candidata)

    resultado = Publicador(conexion).publicar(
        actor="publicacion:prueba", motivo="corte con los campos aprobados"
    )

    assert resultado.versiones_publicadas == 1
    assert resultado.sin_afirmaciones_aprobadas == []
