"""Reglas de integridad que no caben en una restricción de columna.

Agrupa lo que PostgreSQL solo expresa con funciones, triggers, vistas o roles:

* pertenencia real del supertipo `registro_versiones` a cada subtipo;
* coherencia entre evidencia, unidad documental y versión;
* jerarquías acíclicas (jurisdicciones, alias de fuentes, dependencias de
  reglas y cadenas de derivación);
* espejo del intervalo de aplicación en `parametro_valores`, que es lo que hace
  ejecutable la restricción de exclusión creada en 0001;
* inmutabilidad de bytes, evidencias y bitácora;
* búsqueda textual en español;
* `v_hechos_servibles(fecha, known_at, capacidad)`;
* roles separados y sus permisos.

Revision ID: 0002_reglas_de_integridad
Revises: 0001_esquema_inicial
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_reglas_de_integridad"
down_revision: str | None = "0001_esquema_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Subtipos del supertipo `registro_versiones`: tabla, valor de `entidad_tipo` y
# columna que guarda la identidad lógica de la entidad versionada.
SUBTIPOS: tuple[tuple[str, str, str], ...] = (
    ("norma_versiones", "norma", "norma_id"),
    ("beneficio_versiones", "beneficio", "beneficio_id"),
    ("parametro_valores", "parametro_valor", "hecho_id"),
    ("plazos", "plazo", "plazo_id"),
    ("tramite_versiones", "tramite", "tramite_id"),
    ("punto_versiones", "punto_atencion", "punto_id"),
    ("canales", "canal", "canal_id"),
    ("barrios_renabap", "barrio_renabap", "barrio_id"),
)

# Tablas cuyas filas no se modifican ni se borran una vez escritas.
INMUTABLES: tuple[str, ...] = ("capturas", "evidencias", "auditoria_eventos")


SQL_UPGRADE = r"""
-- =========================================================================
-- 1. Supertipo controlado
-- =========================================================================
-- Las afirmaciones apuntan a `registro_versiones`, no a cada tabla concreta.
-- Para que esa FK no sea polimórfica sin control, cada subtipo declara a qué
-- `entidad_tipo` pertenece y sobre qué entidad lógica versiona.

CREATE FUNCTION bn_verificar_subtipo_version() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_tipo_esperado   text := TG_ARGV[0];
    v_columna         text := TG_ARGV[1];
    v_entidad_local   uuid;
    v_tipo_registro   text;
    v_entidad_registro uuid;
BEGIN
    EXECUTE format('SELECT ($1).%I', v_columna) INTO v_entidad_local USING NEW;

    SELECT entidad_tipo, entidad_id
      INTO v_tipo_registro, v_entidad_registro
      FROM registro_versiones
     WHERE id = NEW.registro_version_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'La fila de %I referencia una versión inexistente (%)',
            TG_TABLE_NAME, NEW.registro_version_id;
    END IF;

    IF v_tipo_registro IS DISTINCT FROM v_tipo_esperado THEN
        RAISE EXCEPTION
            'La versión % es de tipo "%" y % solo admite "%"',
            NEW.registro_version_id, v_tipo_registro, TG_TABLE_NAME, v_tipo_esperado;
    END IF;

    IF v_entidad_registro IS DISTINCT FROM v_entidad_local THEN
        RAISE EXCEPTION
            'La versión % versiona la entidad % pero la fila de % declara %',
            NEW.registro_version_id, v_entidad_registro, TG_TABLE_NAME, v_entidad_local;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION bn_verificar_subtipo_version() IS
    'Asegura que una fila de subtipo corresponda al tipo y a la entidad que '
    'declara su fila de registro_versiones.';

-- =========================================================================
-- 2. Coherencia entre documento, unidad y evidencia
-- =========================================================================
-- Un fragmento citado tiene que pertenecer a la versión documental que se
-- invoca. Sin esto, una cita "de la misma norma" podría apuntar a otra versión
-- y sostener una afirmación que ese texto no dice.

CREATE FUNCTION bn_verificar_evidencia_coherente() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_version_de_la_unidad uuid;
BEGIN
    IF NEW.unidad_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT doc_version_id INTO v_version_de_la_unidad
      FROM unidades_documentales WHERE id = NEW.unidad_id;

    IF v_version_de_la_unidad IS DISTINCT FROM NEW.doc_version_id THEN
        RAISE EXCEPTION
            'La evidencia cita la unidad % (versión %) pero declara la versión %',
            NEW.unidad_id, v_version_de_la_unidad, NEW.doc_version_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_evidencias_coherentes
    AFTER INSERT OR UPDATE ON evidencias
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION bn_verificar_evidencia_coherente();

-- Una unidad y su unidad madre pertenecen a la misma versión: la jerarquía de
-- un texto no cruza versiones.
CREATE FUNCTION bn_verificar_unidad_misma_version() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_version_padre uuid;
BEGIN
    IF NEW.parent_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT doc_version_id INTO v_version_padre
      FROM unidades_documentales WHERE id = NEW.parent_id;

    IF v_version_padre IS DISTINCT FROM NEW.doc_version_id THEN
        RAISE EXCEPTION
            'La unidad % pertenece a la versión % y no puede colgar de una unidad de la versión %',
            NEW.id, NEW.doc_version_id, v_version_padre;
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_unidades_misma_version
    AFTER INSERT OR UPDATE ON unidades_documentales
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION bn_verificar_unidad_misma_version();

-- =========================================================================
-- 3. Jerarquías acíclicas
-- =========================================================================
-- Los ciclos entre normas que se citan son legítimos y se navegan con conjunto
-- de visitados. Estos otros ciclos no lo son: un municipio dentro de sí mismo,
-- un alias que apunta a su propia cadena, una regla que se excepciona a sí
-- misma o un cálculo que se alimenta de su propio resultado.

CREATE FUNCTION bn_verificar_jurisdiccion_aciclica() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_actual text := NEW.parent_id;
    v_pasos  int  := 0;
BEGIN
    WHILE v_actual IS NOT NULL LOOP
        IF v_actual = NEW.id THEN
            RAISE EXCEPTION 'La jurisdicción % cerraría un ciclo en la jerarquía', NEW.id;
        END IF;
        v_pasos := v_pasos + 1;
        IF v_pasos > 64 THEN
            RAISE EXCEPTION 'Jerarquía de jurisdicciones demasiado profunda desde %', NEW.id;
        END IF;
        SELECT parent_id INTO v_actual FROM jurisdicciones WHERE id = v_actual;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_jurisdicciones_aciclicas
    AFTER INSERT OR UPDATE OF parent_id ON jurisdicciones
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION bn_verificar_jurisdiccion_aciclica();

CREATE FUNCTION bn_verificar_alias_aciclico() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_actual text := NEW.alias_of;
    v_pasos  int  := 0;
BEGIN
    WHILE v_actual IS NOT NULL LOOP
        IF v_actual = NEW.source_id THEN
            RAISE EXCEPTION 'El alias de la fuente % cerraría un ciclo', NEW.source_id;
        END IF;
        v_pasos := v_pasos + 1;
        IF v_pasos > 16 THEN
            RAISE EXCEPTION 'Cadena de alias demasiado larga desde %', NEW.source_id;
        END IF;
        SELECT alias_of INTO v_actual FROM fuentes WHERE source_id = v_actual;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_fuentes_alias_aciclico
    AFTER INSERT OR UPDATE OF alias_of ON fuentes
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION bn_verificar_alias_aciclico();

CREATE FUNCTION bn_verificar_reglas_aciclicas() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        WITH RECURSIVE alcanzables(id) AS (
            SELECT NEW.regla_referida_id
            UNION
            SELECT d.regla_referida_id
              FROM regla_dependencias d
              JOIN alcanzables a ON d.regla_id = a.id
        )
        SELECT 1 FROM alcanzables WHERE id = NEW.regla_id
    ) THEN
        RAISE EXCEPTION
            'La dependencia % -> % cerraría un ciclo entre reglas',
            NEW.regla_id, NEW.regla_referida_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_regla_dependencias_aciclicas
    AFTER INSERT OR UPDATE ON regla_dependencias
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION bn_verificar_reglas_aciclicas();

-- Una derivación se alimenta de afirmaciones; una afirmación puede provenir de
-- otra derivación. Esa cadena tiene que ser reproducible, y un ciclo la
-- volvería irreproducible.
CREATE FUNCTION bn_verificar_derivaciones_aciclicas() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        WITH RECURSIVE aguas_arriba(derivacion_id) AS (
            SELECT a.derivacion_id
              FROM afirmaciones a
             WHERE a.id = NEW.afirmacion_id AND a.derivacion_id IS NOT NULL
            UNION
            SELECT a.derivacion_id
              FROM derivacion_insumos i
              JOIN afirmaciones a ON a.id = i.afirmacion_id
              JOIN aguas_arriba u ON i.derivacion_id = u.derivacion_id
             WHERE a.derivacion_id IS NOT NULL
        )
        SELECT 1 FROM aguas_arriba WHERE derivacion_id = NEW.derivacion_id
    ) THEN
        RAISE EXCEPTION
            'El insumo % cerraría un ciclo de cálculo en la derivación %',
            NEW.afirmacion_id, NEW.derivacion_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_derivacion_insumos_aciclicos
    AFTER INSERT OR UPDATE ON derivacion_insumos
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION bn_verificar_derivaciones_aciclicas();

-- =========================================================================
-- 4. Espejo del intervalo de aplicación en parametro_valores
-- =========================================================================
-- La restricción de exclusión de 0001 necesita el rango y el estado en la misma
-- tabla. Estas dos funciones los mantienen sincronizados con
-- `registro_versiones`, en las dos direcciones.
--
-- `valid_tipo = 'DESCONOCIDO'` no produce un rango: un límite temporal
-- desconocido no se vuelve infinito aplicable por defecto, y por eso ese valor
-- queda fuera de la vista servible en vez de bloquear a otro.

CREATE FUNCTION bn_rango_aplicacion(
    p_valid_tipo text, p_desde date, p_hasta date
) RETURNS daterange
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN p_valid_tipo = 'DESCONOCIDO' THEN NULL
        WHEN p_valid_tipo = 'CONDICIONADO' THEN NULL
        WHEN p_desde IS NULL AND p_hasta IS NULL THEN NULL
        -- `[]` conserva la inclusividad de ambos extremos tal como la declara
        -- la fuente; PostgreSQL la normaliza a `[inicio, fin+1)`.
        ELSE daterange(p_desde, p_hasta, '[]')
    END;
$$;

CREATE FUNCTION bn_sincronizar_parametro_valor() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v registro_versiones%ROWTYPE;
BEGIN
    SELECT * INTO v FROM registro_versiones WHERE id = NEW.registro_version_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Versión % inexistente', NEW.registro_version_id;
    END IF;

    NEW.rango_aplicacion := bn_rango_aplicacion(v.valid_tipo, v.valid_desde, v.valid_hasta);
    NEW.publicable := v.estado_revision IN ('APPROVED', 'PUBLISHED')
                      AND v.known_hasta IS NULL
                      AND NEW.rango_aplicacion IS NOT NULL;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_parametro_valores_sincronizar
    BEFORE INSERT OR UPDATE ON parametro_valores
    FOR EACH ROW EXECUTE FUNCTION bn_sincronizar_parametro_valor();

CREATE FUNCTION bn_propagar_registro_a_parametro_valor() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.entidad_tipo <> 'parametro_valor' THEN
        RETURN NEW;
    END IF;
    -- El UPDATE dispara `trg_parametro_valores_sincronizar`, que recalcula el
    -- espejo y vuelve a evaluar la exclusión.
    UPDATE parametro_valores
       SET registro_version_id = registro_version_id
     WHERE registro_version_id = NEW.id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_registro_versiones_propagar
    AFTER UPDATE OF estado_revision, valid_tipo, valid_desde, valid_hasta, known_hasta
    ON registro_versiones
    FOR EACH ROW EXECUTE FUNCTION bn_propagar_registro_a_parametro_valor();

-- =========================================================================
-- 5. Inmutabilidad
-- =========================================================================
-- Los bytes capturados, las evidencias y la bitácora no se editan: un cambio se
-- registra como una fila nueva. El borrado físico queda fuera del flujo normal
-- y de los permisos de la API y de la ingesta.

CREATE FUNCTION bn_rechazar_modificacion() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        '% es inmutable: registrá una fila nueva en lugar de % la existente',
        TG_TABLE_NAME,
        CASE TG_OP WHEN 'DELETE' THEN 'borrar' ELSE 'modificar' END;
END;
$$;

-- =========================================================================
-- 6. Búsqueda textual en español
-- =========================================================================

CREATE INDEX ix_unidades_documentales_fts
    ON unidades_documentales USING gin (to_tsvector('spanish', texto));

CREATE INDEX ix_chunks_fts ON chunks USING gin (to_tsvector('spanish', texto));

CREATE INDEX ix_normas_titulo_fts ON normas USING gin (to_tsvector('spanish', titulo));

-- =========================================================================
-- 7. Hechos servibles
-- =========================================================================
-- Una capacidad declara sus propios campos críticos: una norma con monto
-- desconocido puede sustentar una explicación general y aun así abstenerse de
-- responder "cuánto cobro". La política vive en esta función versionada.

CREATE FUNCTION bn_campos_criticos(p_capacidad text) RETURNS text[]
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_capacidad
        WHEN 'IDENTIFICACION'        THEN ARRAY[]::text[]
        WHEN 'DESCRIPCION_GENERAL'   THEN ARRAY['beneficio_otorgado']
        WHEN 'REQUISITOS'            THEN ARRAY['poblacion_destinataria', 'criterios_aplicabilidad']
        WHEN 'EVALUACION_PRELIMINAR' THEN ARRAY['criterios_aplicabilidad', 'no_descartar']
        WHEN 'MONTO'                 THEN ARRAY['beneficio_otorgado']
        WHEN 'PLAZO'                 THEN ARRAY['plazos']
        WHEN 'CANAL'                 THEN ARRAY[]::text[]
        WHEN 'EXPLICACION_HISTORICA' THEN ARRAY['interdependencias']
        ELSE NULL
    END;
$$;

COMMENT ON FUNCTION bn_campos_criticos(text) IS
    'Campos de los siete pedidos que una capacidad necesita respaldados para '
    'poder responder. Devuelve NULL si la capacidad no está declarada.';

-- Diagnóstico: por qué una versión no es servible. Devuelve una fila por
-- motivo, de modo que la abstención se pueda explicar en vez de solo ocurrir.
CREATE FUNCTION bn_motivos_no_servible(
    p_registro_version_id uuid,
    p_fecha date,
    p_known_at timestamptz,
    p_capacidad text
) RETURNS SETOF text
LANGUAGE plpgsql STABLE AS $$
DECLARE
    v registro_versiones%ROWTYPE;
    v_rango daterange;
    v_criticos text[];
BEGIN
    SELECT * INTO v FROM registro_versiones WHERE id = p_registro_version_id;
    IF NOT FOUND THEN
        RETURN NEXT 'UNKNOWN_IDENTITY: la versión no existe';
        RETURN;
    END IF;

    IF v.estado_revision <> 'PUBLISHED' THEN
        RETURN NEXT format('INSUFFICIENT_EVIDENCE: estado de revisión %s', v.estado_revision);
    END IF;

    IF v.release_id IS NULL OR NOT EXISTS (
        SELECT 1 FROM releases r WHERE r.id = v.release_id AND r.estado = 'PUBLICADO'
    ) THEN
        RETURN NEXT 'INSUFFICIENT_EVIDENCE: sin release publicado';
    END IF;

    IF NOT (v.known_desde <= p_known_at
            AND (v.known_hasta IS NULL OR v.known_hasta > p_known_at)) THEN
        RETURN NEXT 'STALE_DATA: fuera del intervalo de conocimiento';
    END IF;

    v_rango := bn_rango_aplicacion(v.valid_tipo, v.valid_desde, v.valid_hasta);
    IF v_rango IS NULL THEN
        RETURN NEXT format(
            'INSUFFICIENT_EVIDENCE: intervalo de aplicación %s sin resolver', v.valid_tipo);
    ELSIF NOT (v_rango @> p_fecha) THEN
        RETURN NEXT 'UNSUPPORTED_SCOPE: la fecha consultada está fuera del período aplicable';
    END IF;

    IF v.verificado_en IS NULL THEN
        RETURN NEXT 'STALE_DATA: sin verificación registrada';
    ELSIF v.reverificar_antes_de IS NOT NULL AND v.reverificar_antes_de <= p_known_at THEN
        RETURN NEXT 'STALE_DATA: venció la frescura declarada';
    END IF;

    IF EXISTS (
        SELECT 1 FROM incidencias_revision i
         WHERE i.registro_version_id = v.id
           AND i.estado IN ('ABIERTA', 'EN_REVISION')
           AND i.severidad IN ('CRITICAL', 'HIGH')
    ) THEN
        RETURN NEXT 'CONFLICT: hay un conflicto abierto de severidad alta';
    END IF;

    v_criticos := bn_campos_criticos(p_capacidad);
    IF v_criticos IS NULL THEN
        RETURN NEXT format('UNSUPPORTED_SCOPE: capacidad %s no declarada', p_capacidad);
    ELSIF v.entidad_tipo = 'norma' AND array_length(v_criticos, 1) > 0 THEN
        -- Un campo evaluado sin información no cuenta como valor sustantivo.
        RETURN QUERY
            SELECT format('INSUFFICIENT_EVIDENCE: campo crítico %s en estado %s',
                          e.campo_solicitado, e.estado)
              FROM evaluaciones_completitud e
             WHERE e.norma_version_id = v.id
               AND e.campo_solicitado = ANY (v_criticos)
               AND e.estado <> 'INFORMADO';
        RETURN QUERY
            SELECT format('INSUFFICIENT_EVIDENCE: campo crítico %s sin evaluar', c)
              FROM unnest(v_criticos) AS c
             WHERE NOT EXISTS (
                 SELECT 1 FROM evaluaciones_completitud e
                  WHERE e.norma_version_id = v.id AND e.campo_solicitado = c
             );
    END IF;

    RETURN;
END;
$$;

CREATE FUNCTION v_hechos_servibles(
    fecha date,
    known_at timestamptz DEFAULT now(),
    capacidad text DEFAULT 'IDENTIFICACION'
)
RETURNS TABLE (
    registro_version_id uuid,
    entidad_tipo text,
    entidad_id uuid,
    release_id uuid,
    valid_desde date,
    valid_hasta date,
    verificado_en timestamptz
)
LANGUAGE sql STABLE AS $$
    SELECT v.id, v.entidad_tipo, v.entidad_id, v.release_id,
           v.valid_desde, v.valid_hasta, v.verificado_en
      FROM registro_versiones v
     WHERE NOT EXISTS (
         SELECT 1 FROM bn_motivos_no_servible(v.id, fecha, known_at, capacidad)
     );
$$;

COMMENT ON FUNCTION v_hechos_servibles(date, timestamptz, text) IS
    'Versiones que pueden servirse para una fecha, un instante de conocimiento '
    'y una capacidad: evalúa release, vigencia, frescura, conflicto y campos '
    'críticos. No depende de que un proceso periódico borre registros a tiempo.';

-- =========================================================================
-- 8. Roles separados
-- =========================================================================
-- Roles de grupo sin login: las identidades con contraseña las crea quien
-- opera, y se les concede el grupo que corresponda. Ningún secreto vive acá.
--
-- `lector_api` no ve staging: solo lo publicado y los catálogos de referencia.

DO $$
DECLARE
    r text;
BEGIN
    FOREACH r IN ARRAY ARRAY[
        'bn_migrador', 'bn_ingestor', 'bn_revisor',
        'bn_publicador', 'bn_lector_api', 'bn_auditor'
    ] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
    END LOOP;
END;
$$;

GRANT USAGE ON SCHEMA public TO
    bn_ingestor, bn_revisor, bn_publicador, bn_lector_api, bn_auditor;
"""


# Tablas que la API puede leer: proyecciones publicables y catálogos de
# referencia. Deliberadamente no incluye capturas, corridas, afirmaciones ni
# incidencias: el lector conversacional no accede a staging.
TABLAS_LECTURA_API: tuple[str, ...] = (
    "jurisdicciones",
    "organismos",
    "fuentes",
    "normas",
    "norma_identificadores",
    "registro_versiones",
    "norma_versiones",
    "relaciones_normativas",
    "beneficios",
    "beneficio_versiones",
    "beneficio_normas",
    "poblaciones",
    "beneficio_poblaciones",
    "reglas",
    "regla_dependencias",
    "regla_parametros",
    "parametros",
    "parametro_valores",
    "beneficio_cuantias",
    "cuantia_parametros",
    "plazos",
    "calendarios",
    "calendario_excepciones",
    "tramites",
    "tramite_versiones",
    "tramite_pasos",
    "puntos_atencion",
    "punto_versiones",
    "canales",
    "barrios_renabap",
    "evaluaciones_completitud",
    "documentos",
    "documento_versiones",
    "unidades_documentales",
    "evidencias",
    "chunks",
    "releases",
)

# El ingestor escribe descubrimiento y candidatos; no publica ni resuelve.
TABLAS_ESCRITURA_INGESTOR: tuple[str, ...] = (
    "corridas_ingesta",
    "capturas",
    "documentos",
    "documento_versiones",
    "unidades_documentales",
    "evidencias",
    "fuente_urls",
    "fuentes_candidatas",
    "fuente_config_versiones",
    "afirmaciones",
    "controles_calidad",
    "incidencias_revision",
)

# El revisor decide sobre candidatos y deja constancia; no crea releases.
TABLAS_ESCRITURA_REVISOR: tuple[str, ...] = (
    "afirmaciones",
    "evaluaciones_completitud",
    "completitud_afirmaciones",
    "incidencias_revision",
    "referencias_pendientes",
    "relaciones_normativas",
    "equivalencias_unidades",
    "reglas",
    "regla_dependencias",
    "regla_parametros",
    "beneficio_poblaciones",
    "beneficio_normas",
    "beneficio_cuantias",
    "cuantia_parametros",
)


def _grants() -> str:
    lineas: list[str] = []

    lineas.append(
        "-- La API solo lee, y solo proyecciones y catálogos: nada de staging.\n"
        f"GRANT SELECT ON {', '.join(TABLAS_LECTURA_API)} TO bn_lector_api;"
    )
    lineas.append(
        "-- La API registra su propia traza mínima de consultas.\n"
        "GRANT INSERT ON consultas_auditadas TO bn_lector_api;"
    )
    lineas.append(
        "GRANT SELECT ON ALL TABLES IN SCHEMA public TO bn_ingestor, bn_revisor, "
        "bn_publicador, bn_auditor;"
    )
    lineas.append(f"GRANT INSERT, UPDATE ON {', '.join(TABLAS_ESCRITURA_INGESTOR)} TO bn_ingestor;")
    lineas.append(f"GRANT INSERT, UPDATE ON {', '.join(TABLAS_ESCRITURA_REVISOR)} TO bn_revisor;")
    lineas.append(
        "-- Publicar es crear el release, marcar versiones y emitir el evento,\n"
        "-- todo en la misma transacción.\n"
        "GRANT INSERT, UPDATE ON releases, registro_versiones, chunks, eventos_outbox "
        "TO bn_publicador;"
    )
    lineas.append(
        "-- Todos dejan rastro; nadie edita la bitácora (además del trigger de\n"
        "-- inmutabilidad, no se otorga UPDATE ni DELETE sobre ella).\n"
        "GRANT INSERT ON auditoria_eventos TO bn_ingestor, bn_revisor, bn_publicador;"
    )
    lineas.append("GRANT USAGE ON SCHEMA public TO bn_migrador;")
    return "\n".join(lineas)


def upgrade() -> None:
    op.execute(SQL_UPGRADE)

    for tabla, entidad_tipo, columna in SUBTIPOS:
        op.execute(
            f"CREATE CONSTRAINT TRIGGER trg_{tabla}_subtipo "
            f"AFTER INSERT OR UPDATE ON {tabla} "
            "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
            "EXECUTE FUNCTION bn_verificar_subtipo_version("
            f"'{entidad_tipo}', '{columna}')"
        )

    for tabla in INMUTABLES:
        op.execute(
            f"CREATE TRIGGER trg_{tabla}_inmutable "
            f"BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION bn_rechazar_modificacion()"
        )

    op.execute(_grants())


def downgrade() -> None:
    for tabla in INMUTABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_inmutable ON {tabla}")
    for tabla, _tipo, _columna in SUBTIPOS:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_subtipo ON {tabla}")

    op.execute("DROP TRIGGER IF EXISTS trg_registro_versiones_propagar ON registro_versiones")
    op.execute("DROP TRIGGER IF EXISTS trg_parametro_valores_sincronizar ON parametro_valores")
    op.execute("DROP TRIGGER IF EXISTS trg_derivacion_insumos_aciclicos ON derivacion_insumos")
    op.execute("DROP TRIGGER IF EXISTS trg_regla_dependencias_aciclicas ON regla_dependencias")
    op.execute("DROP TRIGGER IF EXISTS trg_fuentes_alias_aciclico ON fuentes")
    op.execute("DROP TRIGGER IF EXISTS trg_jurisdicciones_aciclicas ON jurisdicciones")
    op.execute("DROP TRIGGER IF EXISTS trg_unidades_misma_version ON unidades_documentales")
    op.execute("DROP TRIGGER IF EXISTS trg_evidencias_coherentes ON evidencias")

    op.execute("DROP INDEX IF EXISTS ix_normas_titulo_fts")
    op.execute("DROP INDEX IF EXISTS ix_chunks_fts")
    op.execute("DROP INDEX IF EXISTS ix_unidades_documentales_fts")

    for funcion in (
        "v_hechos_servibles(date, timestamptz, text)",
        "bn_motivos_no_servible(uuid, date, timestamptz, text)",
        "bn_campos_criticos(text)",
        "bn_rechazar_modificacion()",
        "bn_propagar_registro_a_parametro_valor()",
        "bn_sincronizar_parametro_valor()",
        "bn_rango_aplicacion(text, date, date)",
        "bn_verificar_derivaciones_aciclicas()",
        "bn_verificar_reglas_aciclicas()",
        "bn_verificar_alias_aciclico()",
        "bn_verificar_jurisdiccion_aciclica()",
        "bn_verificar_unidad_misma_version()",
        "bn_verificar_evidencia_coherente()",
        "bn_verificar_subtipo_version()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {funcion}")

    # Los roles son objetos del clúster y pueden tener identidades concedidas
    # por quien opera: revocar sus permisos es reversible, borrarlos no.
    op.execute(
        "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "
        "bn_ingestor, bn_revisor, bn_publicador, bn_lector_api, bn_auditor"
    )
