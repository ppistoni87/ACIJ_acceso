"""Valores, cuantías, plazos y estados de campo.

Estas reglas son las que separan "no lo sabemos" de "no existe" y evitan servir
un monto histórico como si fuera el actual.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integracion

POLITICA_PUBLICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"


def _alta_de_fuente(conexion: Connection, source_id: str) -> str:
    """Fuente mínima del catálogo para colgar capturas y documentos."""
    conexion.execute(
        text(
            "INSERT INTO fuentes (source_id, nombre, clase, estado, access_status, "
            "prioridad, politica_acceso) "
            "VALUES (:sid, :nombre, 'PORTAL_NORMATIVO', 'ACTIVE', 'ACCESIBLE', 'P0', :politica) "
            "ON CONFLICT (source_id) DO NOTHING"
        ),
        {"sid": source_id, "nombre": f"Fuente {source_id}", "politica": POLITICA_PUBLICA},
    )
    return source_id


def _parametro(conexion: Connection, codigo: str = "SMVM") -> uuid.UUID:
    return conexion.execute(
        text(
            "INSERT INTO parametros (codigo, concepto, unidad, moneda) "
            "VALUES (:c, 'Concepto de prueba', 'MONEDA', 'ARS') RETURNING id"
        ),
        {"c": codigo},
    ).scalar_one()


def _evidencia(conexion: Connection, sufijo: str) -> uuid.UUID:
    """Cadena mínima fuente → captura → documento → versión → evidencia."""
    sid = f"FEV{sufijo}"
    _alta_de_fuente(conexion, sid)
    url = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:sid, :u, 'DETALLE', 'HTTP_GET_PUBLICO') RETURNING id"
        ),
        {"sid": sid, "u": f"https://ejemplo.gob.ar/{uuid.uuid4()}"},
    ).scalar_one()
    cfg = conexion.execute(
        text(
            "INSERT INTO fuente_config_versiones (source_id, version, adaptador) "
            "VALUES (:sid, 1, 'HTML_ESTATICO') RETURNING id"
        ),
        {"sid": sid},
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            "extractor_version) VALUES (:sid, :c, 'EN_CURSO', 'test-0') RETURNING id"
        ),
        {"sid": sid, "c": cfg},
    ).scalar_one()
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, sha256_raw, objeto_uri) "
            "VALUES (:c, :u, :h, :o) RETURNING id"
        ),
        {
            "c": corrida,
            "u": url,
            "h": uuid.uuid4().hex + uuid.uuid4().hex,
            "o": f"file://var/objetos/{uuid.uuid4()}",
        },
    ).scalar_one()
    doc = conexion.execute(
        text("INSERT INTO documentos (source_id, tipo) VALUES (:sid, 'NORMA') RETURNING id"),
        {"sid": sid},
    ).scalar_one()
    dv = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            "tipo_fecha, hash_texto, modo_extraccion) "
            "VALUES (:d, :c, 1, 'ORIGINAL', 'PUBLICACION', :h, 'HTML') RETURNING id"
        ),
        {"d": doc, "c": captura, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()
    return conexion.execute(
        text(
            "INSERT INTO evidencias (doc_version_id, fragmento, hash_fragmento, tipo) "
            "VALUES (:dv, 'fragmento citado', :h, 'FRAGMENTO_TEXTO') RETURNING id"
        ),
        {"dv": dv, "h": uuid.uuid4().hex + uuid.uuid4().hex},
    ).scalar_one()


def _valor(
    conexion: Connection,
    *,
    parametro: uuid.UUID,
    evidencia: uuid.UUID,
    hecho_id: uuid.UUID,
    desde: str,
    hasta: str | None,
    valid_tipo: str = "CERRADO",
    estado: str = "APPROVED",
    valor: str = "100.0000",
    segmento: str | None = None,
) -> uuid.UUID:
    rv = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde, valid_hasta) "
            "VALUES ('parametro_valor', :eid, :er, :vt, :vd, :vh) RETURNING id"
        ),
        {"eid": hecho_id, "er": estado, "vt": valid_tipo, "vd": desde, "vh": hasta},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO parametro_valores (registro_version_id, hecho_id, parametro_id, "
            "evidencia_id, valor, unidad, moneda, segmento) "
            "VALUES (:rv, :h, :p, :e, :v, 'MONEDA', 'ARS', :s)"
        ),
        {"rv": rv, "h": hecho_id, "p": parametro, "e": evidencia, "v": valor, "s": segmento},
    )
    return rv


# --- Valores de parámetros ---------------------------------------------------


def test_dos_valores_aprobados_no_pueden_regir_a_la_vez(conexion: Connection) -> None:
    """Si dos montos aprobados cubren la misma fecha, una consulta por fecha
    devuelve dos respuestas incompatibles."""
    p = _parametro(conexion)
    e = _evidencia(conexion, "A")
    _valor(
        conexion,
        parametro=p,
        evidencia=e,
        hecho_id=uuid.uuid4(),
        desde="2026-01-01",
        hasta="2026-06-30",
    )
    with pytest.raises(IntegrityError):
        _valor(
            conexion,
            parametro=p,
            evidencia=e,
            hecho_id=uuid.uuid4(),
            desde="2026-06-01",
            hasta="2026-12-31",
        )


def test_candidatos_en_conflicto_pueden_coexistir(conexion: Connection) -> None:
    """Dos fuentes que discrepan se conservan como afirmaciones distintas: la
    exclusión solo alcanza a lo aprobado."""
    p = _parametro(conexion)
    e = _evidencia(conexion, "B")
    for _ in range(2):
        _valor(
            conexion,
            parametro=p,
            evidencia=e,
            hecho_id=uuid.uuid4(),
            desde="2026-01-01",
            hasta="2026-06-30",
            estado="CANDIDATE",
        )
    total = conexion.execute(
        text("SELECT count(*) FROM parametro_valores WHERE parametro_id = :p"), {"p": p}
    ).scalar_one()
    assert total == 2


def test_segmentos_distintos_no_se_solapan_entre_si(conexion: Connection) -> None:
    """La exclusión es por combinación semántica: dos segmentos distintos pueden
    tener valores simultáneos."""
    p = _parametro(conexion)
    e = _evidencia(conexion, "C")
    for segmento in ("zona_general", "zona_austral"):
        _valor(
            conexion,
            parametro=p,
            evidencia=e,
            hecho_id=uuid.uuid4(),
            desde="2026-01-01",
            hasta="2026-06-30",
            segmento=segmento,
        )
    total = conexion.execute(
        text("SELECT count(*) FROM parametro_valores WHERE publicable")
    ).scalar_one()
    assert total == 2


def test_aprobar_una_version_reevalua_el_solapamiento(conexion: Connection) -> None:
    """Un candidato que se aprueba después no puede colarse encima de un valor
    ya aprobado: el espejo se recalcula al cambiar el estado."""
    p = _parametro(conexion)
    e = _evidencia(conexion, "D")
    _valor(
        conexion,
        parametro=p,
        evidencia=e,
        hecho_id=uuid.uuid4(),
        desde="2026-01-01",
        hasta="2026-06-30",
    )
    candidato = _valor(
        conexion,
        parametro=p,
        evidencia=e,
        hecho_id=uuid.uuid4(),
        desde="2026-03-01",
        hasta="2026-09-30",
        estado="CANDIDATE",
    )
    with pytest.raises(IntegrityError):
        conexion.execute(
            text("UPDATE registro_versiones SET estado_revision = 'APPROVED' WHERE id = :id"),
            {"id": candidato},
        )


def test_un_valor_de_vigencia_desconocida_no_se_publica(conexion: Connection) -> None:
    """Sin período resuelto no hay valor servible, aunque esté aprobado."""
    p = _parametro(conexion)
    e = _evidencia(conexion, "E")
    _valor(
        conexion,
        parametro=p,
        evidencia=e,
        hecho_id=uuid.uuid4(),
        desde=None,
        hasta=None,
        valid_tipo="DESCONOCIDO",
    )
    publicable = conexion.execute(
        text("SELECT publicable FROM parametro_valores WHERE parametro_id = :p"), {"p": p}
    ).scalar_one()
    assert publicable is False


# --- Cuantías ----------------------------------------------------------------


def _beneficio_version(conexion: Connection, codigo: str, jurisdiccion: str) -> uuid.UUID:
    beneficio = conexion.execute(
        text("INSERT INTO beneficios (codigo, nombre) VALUES (:c, :c) RETURNING id"),
        {"c": codigo},
    ).scalar_one()
    rv = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde) "
            "VALUES ('beneficio', :b, 'CANDIDATE', 'ABIERTO_FIN', '2020-01-01') RETURNING id"
        ),
        {"b": beneficio},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            "jurisdiccion_id, naturaleza, descripcion) "
            "VALUES (:rv, :b, :j, 'PRESTACION_MONETARIA', 'Descripción')"
        ),
        {"rv": rv, "b": beneficio, "j": jurisdiccion},
    )
    return rv


def test_cuantia_fija_exige_valor_moneda_y_evidencia(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    bv = _beneficio_version(conexion, "B_FIJO", jurisdiccion_nacion)
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO beneficio_cuantias (beneficio_version_id, tipo, valor_fijo) "
                "VALUES (:bv, 'FIJO', 1000)"
            ),
            {"bv": bv},
        )


def test_cuantia_no_informada_no_necesita_inventar_un_monto(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """Que la fuente no publique el monto es un estado válido, no un cero."""
    bv = _beneficio_version(conexion, "B_SIN_MONTO", jurisdiccion_nacion)
    conexion.execute(
        text(
            "INSERT INTO beneficio_cuantias (beneficio_version_id, tipo) "
            "VALUES (:bv, 'NO_INFORMADO')"
        ),
        {"bv": bv},
    )
    tipo = conexion.execute(
        text("SELECT tipo FROM beneficio_cuantias WHERE beneficio_version_id = :bv"), {"bv": bv}
    ).scalar_one()
    assert tipo == "NO_INFORMADO"


def test_no_se_puede_declarar_monto_fijo_y_formula_a_la_vez(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    bv = _beneficio_version(conexion, "B_AMBIGUO", jurisdiccion_nacion)
    e = _evidencia(conexion, "F")
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO beneficio_cuantias (beneficio_version_id, evidencia_id, tipo, "
                "valor_fijo, moneda, formula_ast, formula_version) "
                "VALUES (:bv, :e, 'FIJO', 1000, 'ARS', '{}'::jsonb, '1.0')"
            ),
            {"bv": bv, "e": e},
        )


# --- Plazos ------------------------------------------------------------------


def _plazo(conexion: Connection, **campos: object) -> None:
    plazo_id = uuid.uuid4()
    rv = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde) "
            "VALUES ('plazo', :p, 'CANDIDATE', 'ABIERTO_FIN', '2020-01-01') RETURNING id"
        ),
        {"p": plazo_id},
    ).scalar_one()
    columnas = ", ".join(campos)
    valores = ", ".join(f":{c}" for c in campos)
    conexion.execute(
        text(
            f"INSERT INTO plazos (registro_version_id, plazo_id, {columnas}) "
            f"VALUES (:rv, :plazo_id, {valores})"
        ),
        {"rv": rv, "plazo_id": plazo_id, **campos},
    )


def test_un_plazo_tiene_un_solo_propietario_principal(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    e = _evidencia(conexion, "G")
    with pytest.raises(IntegrityError):
        _plazo(
            conexion,
            evidencia_id=e,
            tipo="CONVOCATORIA",
            tipo_dia="CORRIDO",
            inicio="2026-01-01",
            fin="2026-02-01",
        )


def test_dias_habiles_sin_calendario_no_producen_una_fecha(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    """Contar días hábiles sin cobertura confirmada inventaría un vencimiento."""
    e = _evidencia(conexion, "H")
    bv = _beneficio_version(conexion, "B_PLAZO", jurisdiccion_nacion)
    with pytest.raises(IntegrityError):
        _plazo(
            conexion,
            beneficio_version_id=bv,
            evidencia_id=e,
            tipo="SUBSANACION",
            tipo_dia="HABIL_ADMINISTRATIVO",
            cantidad=10,
            unidad="DIAS",
            evento_inicio="NOTIFICACION",
        )


def test_plazo_relativo_exige_unidad_y_evento_de_inicio(
    conexion: Connection, jurisdiccion_nacion: str
) -> None:
    e = _evidencia(conexion, "I")
    bv = _beneficio_version(conexion, "B_PLAZO2", jurisdiccion_nacion)
    with pytest.raises(IntegrityError):
        _plazo(
            conexion,
            beneficio_version_id=bv,
            evidencia_id=e,
            tipo="RECURSO",
            tipo_dia="CORRIDO",
            cantidad=15,
        )


# --- Estados de campo --------------------------------------------------------


def test_informado_exige_valor_y_evidencia(conexion: Connection) -> None:
    rv = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde) "
            "VALUES ('norma', gen_random_uuid(), 'CANDIDATE', 'ABIERTO_FIN', '2020-01-01') "
            "RETURNING id"
        )
    ).scalar_one()
    with pytest.raises(IntegrityError):
        conexion.execute(
            text(
                "INSERT INTO afirmaciones (registro_version_id, campo_path, estado_campo, "
                "estado_revision) VALUES (:rv, 'beneficio_otorgado', 'INFORMADO', 'CANDIDATE')"
            ),
            {"rv": rv},
        )


def test_no_informado_exige_decir_que_fuentes_se_revisaron(
    conexion: Connection, viola_restriccion
) -> None:
    """ "No lo encontramos" solo es una afirmación si se dice dónde se buscó; no
    es una prueba negativa inventada."""
    rv = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, estado_revision, "
            "valid_tipo, valid_desde) "
            "VALUES ('norma', gen_random_uuid(), 'CANDIDATE', 'ABIERTO_FIN', '2020-01-01') "
            "RETURNING id"
        )
    ).scalar_one()
    with viola_restriccion():
        conexion.execute(
            text(
                "INSERT INTO afirmaciones (registro_version_id, campo_path, estado_campo, "
                "estado_revision) "
                "VALUES (:rv, 'plazos', 'NO_INFORMADO_EN_FUENTES_REVISADAS', 'CANDIDATE')"
            ),
            {"rv": rv},
        )

    conexion.execute(
        text(
            "INSERT INTO afirmaciones (registro_version_id, campo_path, estado_campo, "
            "estado_revision, fuentes_revisadas) "
            "VALUES (:rv, 'plazos', 'NO_INFORMADO_EN_FUENTES_REVISADAS', 'CANDIDATE', "
            ":fuentes)"
        ),
        {"rv": rv, "fuentes": '["F19", "F23"]'},
    )
    estado = conexion.execute(
        text("SELECT estado_campo FROM afirmaciones WHERE registro_version_id = :rv"), {"rv": rv}
    ).scalar_one()
    assert estado == "NO_INFORMADO_EN_FUENTES_REVISADAS"
