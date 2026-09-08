# Diccionario de datos

**53 tablas** y **513 columnas**, generadas desde los modelos
con `bn calidad diccionario`. No se edita a mano: si una columna cambia, se regenera.

El propósito de cada tabla es el docstring de su modelo. Las verificaciones que
aparecen acá son las que viven en el esquema; los disparadores y funciones que
sostienen las reglas que una restricción no puede expresar están en la migración
`0002_reglas_de_integridad.py`.

## Índice

- [`afirmaciones`](#afirmaciones)
- [`auditoria_eventos`](#auditoria-eventos)
- [`barrios_renabap`](#barrios-renabap)
- [`beneficio_cuantias`](#beneficio-cuantias)
- [`beneficio_normas`](#beneficio-normas)
- [`beneficio_poblaciones`](#beneficio-poblaciones)
- [`beneficio_versiones`](#beneficio-versiones)
- [`beneficios`](#beneficios)
- [`calendario_excepciones`](#calendario-excepciones)
- [`calendarios`](#calendarios)
- [`canales`](#canales)
- [`capturas`](#capturas)
- [`chunks`](#chunks)
- [`completitud_afirmaciones`](#completitud-afirmaciones)
- [`consultas_auditadas`](#consultas-auditadas)
- [`controles_calidad`](#controles-calidad)
- [`corridas_ingesta`](#corridas-ingesta)
- [`cuantia_parametros`](#cuantia-parametros)
- [`derivacion_insumos`](#derivacion-insumos)
- [`derivaciones`](#derivaciones)
- [`documento_versiones`](#documento-versiones)
- [`documentos`](#documentos)
- [`equivalencias_unidades`](#equivalencias-unidades)
- [`evaluaciones_completitud`](#evaluaciones-completitud)
- [`eventos_outbox`](#eventos-outbox)
- [`evidencias`](#evidencias)
- [`fuente_config_versiones`](#fuente-config-versiones)
- [`fuente_urls`](#fuente-urls)
- [`fuentes`](#fuentes)
- [`fuentes_candidatas`](#fuentes-candidatas)
- [`incidencias_revision`](#incidencias-revision)
- [`jurisdicciones`](#jurisdicciones)
- [`norma_identificadores`](#norma-identificadores)
- [`norma_versiones`](#norma-versiones)
- [`normas`](#normas)
- [`organismos`](#organismos)
- [`parametro_valores`](#parametro-valores)
- [`parametros`](#parametros)
- [`plazos`](#plazos)
- [`poblaciones`](#poblaciones)
- [`punto_versiones`](#punto-versiones)
- [`puntos_atencion`](#puntos-atencion)
- [`referencias_pendientes`](#referencias-pendientes)
- [`registro_versiones`](#registro-versiones)
- [`regla_dependencias`](#regla-dependencias)
- [`regla_parametros`](#regla-parametros)
- [`reglas`](#reglas)
- [`relaciones_normativas`](#relaciones-normativas)
- [`releases`](#releases)
- [`tramite_pasos`](#tramite-pasos)
- [`tramite_versiones`](#tramite-versiones)
- [`tramites`](#tramites)
- [`unidades_documentales`](#unidades-documentales)

## afirmaciones

Un valor observado para un campo de una versión, con su estado y respaldo.

    Reglas de estado (especificación §3.3):

    * `INFORMADO` exige valor y evidencia.
    * `NO_APLICA_JUSTIFICADO` exige motivo y fundamento.
    * `NO_INFORMADO_EN_FUENTES_REVISADAS` exige haber registrado qué fuentes se
      revisaron; nunca significa que el dato no exista.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `evidencia_id` | UUID | sí | — | `evidencias.id` |
| `campo_path` | TEXT | no | — | — |
| `valor` | JSONB | sí | — | — |
| `estado_campo` | VARCHAR(40) | no | — | — |
| `motivo` | TEXT | sí | — | — |
| `fuentes_revisadas` | JSONB | sí | — | — |
| `source_id` | VARCHAR(16) | sí | — | `fuentes.source_id` |
| `estado_revision` | VARCHAR(16) | no | — | — |
| `observado_en` | TIMESTAMP | no | `now()` | — |
| `derivacion_id` | UUID | sí | — | `derivaciones.id` |

**Verificaciones**

- `ck_afirmaciones_no_informado_con_fuentes_revisadas: estado_campo <> 'NO_INFORMADO_EN_FUENTES_REVISADAS' OR (fuentes_revisadas IS NOT NULL AND jsonb_array_length(fuentes_revisadas) > 0)`
- `ck_afirmaciones_campo_path_no_vacio: length(btrim(campo_path)) > 0`
- `ck_afirmaciones_estado_campo_vocabulario: estado_campo IN ('PENDIENTE', 'INFORMADO', 'NO_INFORMADO_EN_FUENTES_REVISADAS', 'NO_APLICA_JUSTIFICADO', 'EN_CONFLICTO')`
- `ck_afirmaciones_no_aplica_con_motivo_y_fundamento: estado_campo <> 'NO_APLICA_JUSTIFICADO' OR (motivo IS NOT NULL AND evidencia_id IS NOT NULL)`
- `ck_afirmaciones_estado_revision_vocabulario: estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')`
- `ck_afirmaciones_informado_con_valor_y_evidencia: estado_campo <> 'INFORMADO' OR (valor IS NOT NULL AND evidencia_id IS NOT NULL)`

**Índices**

- `ix_afirmaciones_estado_campo (índice): (estado_campo)`
- `ix_afirmaciones_evidencia_id (índice): (evidencia_id)`
- `ix_afirmaciones_registro_version_id (índice): (registro_version_id)`
- `ix_afirmaciones_source_id (índice): (source_id)`
- `ix_afirmaciones_version_campo (índice): (registro_version_id, campo_path)`

## auditoria_eventos

Bitácora append-only de acciones sobre el corpus. RBAC restringe su
    lectura y su escritura; no se actualiza ni se borra desde la aplicación.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `actor` | TEXT | no | — | — |
| `accion` | TEXT | no | — | — |
| `objeto` | TEXT | no | — | — |
| `objeto_id` | TEXT | no | — | — |
| `antes_hash` | VARCHAR(64) | sí | — | — |
| `despues_hash` | VARCHAR(64) | sí | — | — |
| `motivo` | TEXT | sí | — | — |
| `ocurrido_en` | TIMESTAMP | no | `now()` | — |

**Índices**

- `ix_auditoria_eventos_objeto (índice): (objeto, objeto_id)`
- `ix_auditoria_eventos_ocurrido (índice): (ocurrido_en)`

## barrios_renabap

Subtipo de `registro_versiones`: un barrio popular en una versión de
    padrón.

    La ausencia de un barrio en un padrón no es una exclusión jurídica
    definitiva; es un dato de ese corte.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `barrio_id` | UUID | no | — | — |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `id_renabap` | TEXT | no | — | — |
| `nombre` | TEXT | no | — | — |
| `provincia` | TEXT | sí | — | — |
| `departamento` | TEXT | sí | — | — |
| `localidad` | TEXT | sí | — | — |
| `viviendas` | BIGINT | sí | — | — |
| `familias` | BIGINT | sí | — | — |
| `datos_habitacionales` | JSONB | sí | — | — |
| `fecha_corte` | DATE | sí | — | — |
| `padron_version` | TEXT | no | — | — |

**Claves únicas**

- `uq_barrios_renabap_padron: (id_renabap, padron_version)`

**Verificaciones**

- `ck_barrios_renabap_viviendas_no_negativas: viviendas IS NULL OR viviendas >= 0`
- `ck_barrios_renabap_familias_no_negativas: familias IS NULL OR familias >= 0`

**Índices**

- `ix_barrios_renabap_barrio_id (índice): (barrio_id)`
- `ix_barrios_renabap_provincia_localidad (índice): (provincia, localidad)`

## beneficio_cuantias

Cuánto otorga el beneficio. Exactamente una modalidad respaldada.

    El monto del beneficio no es el tope de ingreso ni el costo del trámite:
    cada uno es un parámetro distinto y se guarda por separado.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `beneficio_version_id` | UUID | no | — | `beneficio_versiones.registro_version_id` |
| `evidencia_id` | UUID | sí | — | `evidencias.id` |
| `tipo` | VARCHAR(16) | no | — | — |
| `valor_fijo` | NUMERIC(20, 4) | sí | — | — |
| `moneda` | VARCHAR(3) | sí | — | — |
| `formula_ast` | JSONB | sí | — | — |
| `formula_version` | TEXT | sí | — | — |
| `redondeo` | TEXT | sí | — | — |
| `unidad_beneficiaria` | TEXT | sí | — | — |
| `descripcion_especie` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_beneficio_cuantias_cuantia_con_evidencia: tipo = 'NO_INFORMADO' OR evidencia_id IS NOT NULL`
- `ck_beneficio_cuantias_una_modalidad_respaldada: (tipo = 'FIJO' AND valor_fijo IS NOT NULL AND moneda IS NOT NULL   AND formula_ast IS NULL) OR (tipo = 'FORMULA' AND formula_ast IS NOT NULL AND formula_version IS NOT NULL   AND valor_fijo IS NULL) OR (tipo = 'ESPECIE' AND descripcion_especie IS NOT NULL   AND valor_fijo IS NULL AND formula_ast IS NULL) OR (tipo = 'NO_INFORMADO' AND valor_fijo IS NULL AND formula_ast IS NULL)`
- `ck_beneficio_cuantias_tipo_vocabulario: tipo IN ('FIJO', 'FORMULA', 'ESPECIE', 'NO_INFORMADO')`
- `ck_beneficio_cuantias_moneda_iso4217: moneda IS NULL OR moneda ~ '^[A-Z]{3}$'`

**Índices**

- `ix_beneficio_cuantias_beneficio_version_id (índice): (beneficio_version_id)`

## beneficio_normas

Vínculo respaldado entre un beneficio y la versión de norma que lo crea,
    reglamenta, financia, modifica, interpreta o aplica.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `beneficio_version_id` | UUID | no | — | `beneficio_versiones.registro_version_id` |
| `norma_version_id` | UUID | no | — | `norma_versiones.registro_version_id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `rol` | VARCHAR(32) | no | — | — |
| `alcance` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_beneficio_normas_rol: (beneficio_version_id, norma_version_id, rol)`

**Verificaciones**

- `ck_beneficio_normas_rol_vocabulario: rol IN ('CREA', 'REGLAMENTA', 'FINANCIA', 'MODIFICA', 'INTERPRETA', 'APLICA')`

**Índices**

- `ix_beneficio_normas_beneficio_version_id (índice): (beneficio_version_id)`
- `ix_beneficio_normas_norma_version_id (índice): (norma_version_id)`

## beneficio_poblaciones

Titular, causante, representante y conviviente son roles distintos: un
    mismo grupo puede aparecer en varios con alcances diferentes.

    Pertenecer a una categoría no es, por sí solo, un requisito: cuando la
    condición proviene de una regla, `regla_id` la enlaza.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `beneficio_version_id` | UUID | no | — | `beneficio_versiones.registro_version_id` |
| `poblacion_id` | UUID | no | — | `poblaciones.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `rol_persona` | VARCHAR(32) | no | — | — |
| `alcance` | TEXT | sí | — | — |
| `regla_id` | UUID | sí | — | `reglas.id` |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_beneficio_poblaciones_rol: (beneficio_version_id, poblacion_id, rol_persona)`

**Verificaciones**

- `ck_beneficio_poblaciones_rol_persona_vocabulario: rol_persona IN ('TITULAR', 'CAUSANTE', 'SOLICITANTE', 'REPRESENTANTE', 'CONVIVIENTE', 'GRUPO_FAMILIAR')`

**Índices**

- `ix_beneficio_poblaciones_beneficio_version_id (índice): (beneficio_version_id)`
- `ix_beneficio_poblaciones_poblacion_id (índice): (poblacion_id)`

## beneficio_versiones

Subtipo de `registro_versiones`. Un valor desconocido se registra como
    estado en `afirmaciones`, no como un booleano en falso por defecto: por eso
    `requiere_solicitud` admite NULL.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `beneficio_id` | UUID | no | — | `beneficios.id` |
| `jurisdiccion_id` | VARCHAR(32) | no | — | `jurisdicciones.id` |
| `autoridad_id` | UUID | sí | — | `organismos.id` |
| `naturaleza` | VARCHAR(32) | no | — | — |
| `descripcion` | TEXT | no | — | — |
| `unidad_beneficiaria` | TEXT | sí | — | — |
| `modalidad` | TEXT | sí | — | — |
| `frecuencia` | TEXT | sí | — | — |
| `cupo` | TEXT | sí | — | — |
| `requiere_solicitud` | BOOLEAN | sí | — | — |

**Verificaciones**

- `ck_beneficio_versiones_naturaleza_vocabulario: naturaleza IN ('PRESTACION_MONETARIA', 'PRESTACION_EN_ESPECIE', 'SERVICIO', 'EXENCION', 'PROTECCION', 'ACCESO_A_PROCEDIMIENTO', 'OTRO_EFECTO', 'NO_INFORMADA')`

**Índices**

- `ix_beneficio_versiones_autoridad_id (índice): (autoridad_id)`
- `ix_beneficio_versiones_beneficio_id (índice): (beneficio_id)`
- `ix_beneficio_versiones_jurisdiccion_id (índice): (jurisdiccion_id)`

## beneficios

Identidad estable de una prestación. `linea` separa variantes que
    comparten programa (por ejemplo, las líneas de una misma beca) y `familia`
    agrupa regímenes: una asignación no se confunde con otra por pertenecer al
    mismo conjunto.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `codigo` | TEXT | no | — | — |
| `nombre` | TEXT | no | — | — |
| `linea` | TEXT | sí | — | — |
| `familia` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_beneficios_codigo: (codigo)`

**Verificaciones**

- `ck_beneficios_codigo_normalizado: codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'`

**Índices**

- `ix_beneficios_familia_linea (índice): (familia, linea)`

## calendario_excepciones

Día no laborable o día hábil excepcional, con su motivo y evidencia.

    Fuera de la cobertura confirmada del calendario no se calcula un vencimiento
    hábil: se responde "desconocido".

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `calendario_id` | UUID | no | — | `calendarios.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `fecha` | DATE | no | — | — |
| `es_habil` | BOOLEAN | no | — | — |
| `motivo` | TEXT | sí | — | — |

**Claves únicas**

- `uq_calendario_excepciones_fecha: (calendario_id, fecha)`

**Índices**

- `ix_calendario_excepciones_calendario_id (índice): (calendario_id)`

## calendarios

Un calendario administrativo no es universal: pertenece a una
    jurisdicción, tiene versión y cubre un rango de fechas conocido.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `jurisdiccion_id` | VARCHAR(32) | no | — | `jurisdicciones.id` |
| `nombre` | TEXT | no | — | — |
| `version` | TEXT | no | — | — |
| `fecha_desde` | DATE | no | — | — |
| `fecha_hasta` | DATE | no | — | — |
| `fuente_id` | VARCHAR(16) | sí | — | `fuentes.source_id` |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_calendarios_version: (jurisdiccion_id, nombre, version)`

**Verificaciones**

- `ck_calendarios_cobertura_ordenada: fecha_hasta >= fecha_desde`

**Índices**

- `ix_calendarios_jurisdiccion_id (índice): (jurisdiccion_id)`

## canales

Subtipo de `registro_versiones`. El horario es por canal: el de la mesa
    presencial no se copia al teléfono ni al WhatsApp.

    Se guarda el valor tal como fue publicado y, si se pudo normalizar, ambos.
    No se desofusca un correo ni se registran datos de personas usuarias.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `canal_id` | UUID | no | — | — |
| `organismo_id` | UUID | no | — | `organismos.id` |
| `punto_id` | UUID | sí | — | `puntos_atencion.id` |
| `tramite_id` | UUID | sí | — | `tramites.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `valor_crudo` | TEXT | no | — | — |
| `valor_normalizado` | TEXT | sí | — | — |
| `horario` | TEXT | sí | — | — |
| `publico` | TEXT | sí | — | — |
| `requiere_autenticacion` | BOOLEAN | sí | — | — |

**Verificaciones**

- `ck_canales_valor_crudo_no_vacio: length(btrim(valor_crudo)) > 0`
- `ck_canales_presencial_con_punto: tipo <> 'PRESENCIAL' OR punto_id IS NOT NULL`
- `ck_canales_email_normalizado_plausible: tipo <> 'EMAIL' OR valor_normalizado IS NULL OR valor_normalizado LIKE '%@%'`
- `ck_canales_tipo_vocabulario: tipo IN ('PRESENCIAL', 'TELEFONO', 'WHATSAPP', 'EMAIL', 'WEB', 'FORMULARIO_WEB', 'REDES_SOCIALES', 'CORREO_POSTAL')`

**Índices**

- `ix_canales_canal_id (índice): (canal_id)`
- `ix_canales_organismo_id (índice): (organismo_id)`
- `ix_canales_punto_id (índice): (punto_id)`
- `ix_canales_tramite_id (índice): (tramite_id)`

## capturas

Bytes originales de un recurso público, inmutables.

    `objeto_uri` apunta al almacén direccionado por contenido; la base guarda
    URI y hashes, nunca una ruta local de un agente. Las cabeceras conservadas
    excluyen cookies y tokens de sesión.

    Un `304 Not Modified` exige `captura_previa_id` del mismo recurso y reutiliza
    su objeto y su hash: no inventa un cuerpo descargado.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `corrida_id` | UUID | no | — | `corridas_ingesta.id` |
| `source_url_id` | UUID | no | — | `fuente_urls.id` |
| `captura_previa_id` | UUID | sí | — | `capturas.id` |
| `url_final` | TEXT | sí | — | — |
| `http_status` | INTEGER | sí | — | — |
| `capturado_en` | TIMESTAMP | no | `now()` | — |
| `mime` | TEXT | sí | — | — |
| `bytes` | BIGINT | sí | — | — |
| `sha256_raw` | VARCHAR(64) | no | — | — |
| `sha256_semantico` | VARCHAR(64) | sí | — | — |
| `objeto_uri` | TEXT | no | — | — |
| `etag` | TEXT | sí | — | — |
| `last_modified` | TEXT | sí | — | — |
| `cabeceras` | JSONB | sí | — | — |
| `redirecciones` | JSONB | sí | — | — |

**Verificaciones**

- `ck_capturas_sin_autoprevia: captura_previa_id <> id`
- `ck_capturas_sha256_semantico_hex: sha256_semantico IS NULL OR sha256_semantico ~ '^[0-9a-f]{64}$'`
- `ck_capturas_http_status_valido: http_status IS NULL OR (http_status BETWEEN 100 AND 599)`
- `ck_capturas_bytes_no_negativos: bytes IS NULL OR bytes >= 0`
- `ck_capturas_objeto_uri_con_esquema: objeto_uri ~ '^[a-z][a-z0-9+.-]*://'`
- `ck_capturas_revalidacion_304_exige_captura_previa: http_status <> 304 OR captura_previa_id IS NOT NULL`
- `ck_capturas_sha256_raw_hex: sha256_raw ~ '^[0-9a-f]{64}$'`

**Índices**

- `ix_capturas_captura_previa_id (índice): (captura_previa_id)`
- `ix_capturas_corrida_id (índice): (corrida_id)`
- `ix_capturas_sha256_raw (índice): (sha256_raw)`
- `ix_capturas_source_url_id (índice): (source_url_id)`
- `ix_capturas_url_capturado (índice): (source_url_id, capturado_en)`

## chunks

Segmento citable del corpus publicado, anclado a una unidad documental.

    Es una proyección reconstruible: ninguna regla depende de que exista, y un
    duplicado no aumenta la autoridad de una afirmación.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `unidad_id` | UUID | no | — | `unidades_documentales.id` |
| `registro_version_id` | UUID | sí | — | `registro_versiones.id` |
| `release_id` | UUID | no | — | `releases.id` |
| `texto` | TEXT | no | — | — |
| `hash` | VARCHAR(64) | no | — | — |
| `tipo` | VARCHAR(32) | no | — | — |
| `tsv` | TSVECTOR | sí | — | — |
| `modelo_embedding` | TEXT | sí | — | — |
| `embedding_ref` | TEXT | sí | — | — |

**Claves únicas**

- `uq_chunks_release_unidad_hash: (release_id, unidad_id, hash)`

**Verificaciones**

- `ck_chunks_hash_hex: hash ~ '^[0-9a-f]{64}$'`
- `ck_chunks_tipo_vocabulario: tipo IN ('UNIDAD_NORMATIVA', 'PROCEDIMIENTO', 'FAQ', 'ANEXO')`

**Índices**

- `ix_chunks_registro_version_id (índice): (registro_version_id)`
- `ix_chunks_release_id (índice): (release_id)`
- `ix_chunks_unidad_id (índice): (unidad_id)`

## completitud_afirmaciones

Puente entre una evaluación y las afirmaciones que la respaldan. La FK es
    obligatoria: una evaluación no se justifica con una URL suelta.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `evaluacion_id` | UUID | no | — | `evaluaciones_completitud.id` |
| `afirmacion_id` | UUID | no | — | `afirmaciones.id` |
| `rol` | TEXT | sí | — | — |

**Índices**

- `ix_completitud_afirmaciones_afirmacion_id (índice): (afirmacion_id)`

## consultas_auditadas

Traza mínima de una consulta servida, para reproducibilidad y métricas.

    Por defecto no guarda la conversación ni datos de la persona: solo la
    intención normalizada, la fecha consultada, el release y qué evidencias y
    versiones de reglas se usaron. Cualquier persistencia adicional exige un
    contrato de consentimiento y retención separado.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `release_id` | UUID | no | — | `releases.id` |
| `intencion` | TEXT | sí | — | — |
| `fecha_consulta` | DATE | sí | — | — |
| `jurisdiccion_id` | VARCHAR(32) | sí | — | `jurisdicciones.id` |
| `resultado_tipo` | TEXT | sí | — | — |
| `evidencias_usadas` | JSONB | sí | — | — |
| `reglas_versiones` | JSONB | sí | — | — |
| `latencia_ms` | INTEGER | sí | — | — |
| `ocurrido_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_consultas_auditadas_latencia_no_negativa: latencia_ms IS NULL OR latencia_ms >= 0`

**Índices**

- `ix_consultas_auditadas_ocurrido (índice): (ocurrido_en)`
- `ix_consultas_auditadas_release_id (índice): (release_id)`

## controles_calidad

Resultado de un control (DQ01–DQ18) sobre una versión o una corrida.

    Se guardan lo observado y lo esperado: un control que falla debe poder
    explicarse sin volver a ejecutarlo.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `registro_version_id` | UUID | sí | — | `registro_versiones.id` |
| `corrida_id` | UUID | sí | — | `corridas_ingesta.id` |
| `control_id` | VARCHAR(16) | no | — | — |
| `version` | TEXT | sí | — | — |
| `resultado` | VARCHAR(16) | no | — | — |
| `severidad` | VARCHAR(16) | no | — | — |
| `observado` | JSONB | sí | — | — |
| `esperado` | JSONB | sí | — | — |
| `ejecutado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_controles_calidad_severidad_vocabulario: severidad IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')`
- `ck_controles_calidad_control_con_objeto: registro_version_id IS NOT NULL OR corrida_id IS NOT NULL`
- `ck_controles_calidad_falla_con_observado: resultado <> 'FALLA' OR observado IS NOT NULL`
- `ck_controles_calidad_resultado_vocabulario: resultado IN ('PASA', 'FALLA', 'ADVERTENCIA', 'NO_APLICA')`

**Índices**

- `ix_controles_calidad_control_resultado (índice): (control_id, resultado)`
- `ix_controles_calidad_corrida_id (índice): (corrida_id)`
- `ix_controles_calidad_ejecutado (índice): (ejecutado_en)`
- `ix_controles_calidad_registro_version_id (índice): (registro_version_id)`

## corridas_ingesta

Una ejecución del pipeline sobre una fuente, con la versión de
    configuración que usó. Los contadores deben reconciliar: una corrida que no
    procesó lo que descargó no puede figurar como completa.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `source_id` | VARCHAR(16) | no | — | `fuentes.source_id` |
| `config_version_id` | UUID | no | — | `fuente_config_versiones.id` |
| `inicio` | TIMESTAMP | no | `now()` | — |
| `fin` | TIMESTAMP | sí | — | — |
| `estado` | VARCHAR(16) | no | — | — |
| `extractor_version` | TEXT | no | — | — |
| `solicitadas` | INTEGER | no | `0` | — |
| `descargadas` | INTEGER | no | `0` | — |
| `procesadas` | INTEGER | no | `0` | — |
| `rechazadas` | INTEGER | no | `0` | — |
| `checkpoint` | JSONB | sí | — | — |
| `detalle_error` | TEXT | sí | — | — |

**Verificaciones**

- `ck_corridas_ingesta_procesadas_hasta_descargadas: procesadas <= descargadas`
- `ck_corridas_ingesta_fin_posterior_a_inicio: fin IS NULL OR fin >= inicio`
- `ck_corridas_ingesta_estado_vocabulario: estado IN ('EN_CURSO', 'COMPLETA', 'PARCIAL', 'FALLIDA', 'CANCELADA')`
- `ck_corridas_ingesta_resueltas_hasta_solicitadas: procesadas + rechazadas <= solicitadas`
- `ck_corridas_ingesta_contadores_no_negativos: solicitadas >= 0 AND descargadas >= 0 AND procesadas >= 0 AND rechazadas >= 0`
- `ck_corridas_ingesta_completa_reconciliada: estado <> 'COMPLETA' OR (fin IS NOT NULL AND procesadas + rechazadas = solicitadas)`
- `ck_corridas_ingesta_descargadas_hasta_solicitadas: descargadas <= solicitadas`

**Índices**

- `ix_corridas_ingesta_config_version_id (índice): (config_version_id)`
- `ix_corridas_ingesta_source_id (índice): (source_id)`
- `ix_corridas_ingesta_source_inicio (índice): (source_id, inicio)`

## cuantia_parametros

Insumos de una cuantía derivada: permite invalidarla cuando cambia el
    parámetro del que depende.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `cuantia_id` | UUID | no | — | `beneficio_cuantias.id` |
| `parametro_id` | UUID | no | — | `parametros.id` |
| `rol` | VARCHAR(32) | no | — | — |

**Índices**

- `ix_cuantia_parametros_parametro_id (índice): (parametro_id)`

## derivacion_insumos

Puente obligatorio entre una derivación y sus afirmaciones de entrada.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `derivacion_id` | UUID | no | — | `derivaciones.id` |
| `afirmacion_id` | UUID | no | — | `afirmaciones.id` |
| `rol` | TEXT | no | — | — |

**Índices**

- `ix_derivacion_insumos_afirmacion_id (índice): (afirmacion_id)`

## derivaciones

Cálculo reproducible: algoritmo, fórmula, insumos y resultado.

    Los insumos apuntan a la afirmación exacta que se usó, nunca al último valor
    mutable de un parámetro.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `algoritmo_version` | TEXT | no | — | — |
| `formula` | JSONB | no | — | — |
| `resultado` | JSONB | no | — | — |
| `ejecutada_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_derivaciones_algoritmo_version_no_vacia: length(btrim(algoritmo_version)) > 0`

## documento_versiones

Versión textual de un documento, anclada a la captura de la que salió.

    Original, actualizado y consolidado son versiones distintas: no se
    sobrescriben ni se vuelve a aplicar una reforma que el texto ya integra.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `documento_id` | UUID | no | — | `documentos.id` |
| `captura_id` | UUID | no | — | `capturas.id` |
| `version` | INTEGER | no | — | — |
| `tipo_version` | VARCHAR(32) | no | — | — |
| `fecha_documento` | DATE | sí | — | — |
| `tipo_fecha` | VARCHAR(32) | no | — | — |
| `texto_extraido` | TEXT | sí | — | — |
| `hash_texto` | VARCHAR(64) | no | — | — |
| `modo_extraccion` | VARCHAR(16) | no | — | — |
| `extractor_version` | TEXT | no | — | — |
| `paginas` | INTEGER | sí | — | — |
| `chars_por_pagina` | JSONB | sí | — | — |
| `extraccion_score` | NUMERIC(5, 4) | sí | — | — |
| `identidad_candidata` | JSONB | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_documento_versiones_numero: (documento_id, version)`
- `uq_documento_versiones_contenido: (documento_id, hash_texto, tipo_version)`

**Verificaciones**

- `ck_documento_versiones_tipo_version_vocabulario: tipo_version IN ('ORIGINAL', 'ACTUALIZADO', 'CONSOLIDADO', 'NO_DETERMINADO')`
- `ck_documento_versiones_hash_texto_hex: hash_texto ~ '^[0-9a-f]{64}$'`
- `ck_documento_versiones_version_positiva: version >= 1`
- `ck_documento_versiones_tipo_fecha_vocabulario: tipo_fecha IN ('SANCION', 'PROMULGACION', 'PUBLICACION', 'FIRMA', 'CABECERA', 'ACTUALIZACION_SITIO', 'DESCONOCIDA')`
- `ck_documento_versiones_modo_extraccion_vocabulario: modo_extraccion IN ('HTML', 'JSON', 'CSV', 'PDF_TEXTO', 'PDF_OCR', 'MANUAL')`
- `ck_documento_versiones_score_entre_cero_y_uno: extraccion_score IS NULL OR (extraccion_score BETWEEN 0 AND 1)`
- `ck_documento_versiones_fecha_con_tipo_declarado: fecha_documento IS NULL OR tipo_fecha <> 'DESCONOCIDA'`

**Índices**

- `ix_documento_versiones_captura_id (índice): (captura_id)`
- `ix_documento_versiones_documento_id (índice): (documento_id)`
- `ix_documento_versiones_fecha (índice): (fecha_documento)`

## documentos

No todo documento es norma: una guía, una FAQ, un dataset o un
    procedimiento se registran con su propio tipo.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `source_id` | VARCHAR(16) | no | — | `fuentes.source_id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `titulo` | TEXT | sí | — | — |
| `idioma` | VARCHAR(8) | sí | `'es'` | — |
| `external_id` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_documentos_source_external: (source_id, external_id)`

**Verificaciones**

- `ck_documentos_tipo_vocabulario: tipo IN ('NORMA', 'ANEXO', 'GUIA', 'FAQ', 'DATASET', 'PROCEDIMIENTO', 'DIRECTORIO', 'PADRON', 'OTRO')`

**Índices**

- `ix_documentos_source_id (índice): (source_id)`

## equivalencias_unidades

Correspondencia entre unidades de versiones distintas: renumeración,
    sustitución, división o fusión. Sin esto, una reforma se "parchea por
    número" y se aplica sobre el artículo equivocado.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `origen_unidad_id` | UUID | no | — | `unidades_documentales.id` |
| `destino_unidad_id` | UUID | no | — | `unidades_documentales.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `motivo` | TEXT | sí | — | — |
| `estado_revision` | VARCHAR(16) | no | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_equivalencias_par_tipo: (origen_unidad_id, destino_unidad_id, tipo)`

**Verificaciones**

- `ck_equivalencias_unidades_tipo_vocabulario: tipo IN ('RENUMERACION', 'SUSTITUCION', 'DIVISION', 'FUSION', 'INCORPORACION')`
- `ck_equivalencias_unidades_estado_revision_vocabulario: estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')`
- `ck_equivalencias_unidades_origen_distinto_destino: origen_unidad_id <> destino_unidad_id`

**Índices**

- `ix_equivalencias_unidades_destino_unidad_id (índice): (destino_unidad_id)`
- `ix_equivalencias_unidades_origen_unidad_id (índice): (origen_unidad_id)`

## evaluaciones_completitud

Una fila por cada uno de los siete campos pedidos, por ficha evaluada.

    Su existencia prueba que el campo se evaluó; su estado dice con qué
    resultado. Cien por ciento de filas en `NO_INFORMADO...` da cobertura de
    evaluación, nunca "base completa".

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `norma_version_id` | UUID | no | — | `norma_versiones.registro_version_id` |
| `beneficio_version_id` | UUID | sí | — | `beneficio_versiones.registro_version_id` |
| `campo_solicitado` | VARCHAR(40) | no | — | — |
| `estado` | VARCHAR(40) | no | — | — |
| `fuentes_revisadas` | JSONB | sí | — | — |
| `motivo` | TEXT | sí | — | — |
| `revisor_id` | TEXT | sí | — | — |
| `evaluado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_evaluaciones_completitud_estado_vocabulario: estado IN ('PENDIENTE', 'INFORMADO', 'NO_INFORMADO_EN_FUENTES_REVISADAS', 'NO_APLICA_JUSTIFICADO', 'EN_CONFLICTO')`
- `ck_evaluaciones_completitud_campo_solicitado_vocabulario: campo_solicitado IN ('poblacion_destinataria', 'criterios_aplicabilidad', 'plazos', 'criterios_revocacion', 'interdependencias', 'beneficio_otorgado', 'no_descartar')`

**Índices**

- `ix_evaluaciones_completitud_beneficio_version_id (índice): (beneficio_version_id)`
- `ix_evaluaciones_completitud_norma_version_id (índice): (norma_version_id)`
- `uq_evaluaciones_completitud_ficha_campo (único): (norma_version_id, beneficio_version_id, campo_solicitado)`

## eventos_outbox

Evento interno pendiente de entrega a un consumidor configurado.

    Entrega al menos una vez, con consumidores idempotentes. Un evento creado no
    es un mensaje entregado: `entregado_en` solo se completa con entrega
    comprobada. Web Push ciudadano es una integración separada.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `release_id` | UUID | sí | — | `releases.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `aggregate_id` | TEXT | no | — | — |
| `payload` | JSONB | no | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |
| `entregado_en` | TIMESTAMP | sí | — | — |
| `intentos` | INTEGER | no | `0` | — |
| `ultimo_error` | TEXT | sí | — | — |
| `idempotency_key` | TEXT | no | — | — |

**Claves únicas**

- `uq_eventos_outbox_idempotency_key: (idempotency_key)`

**Verificaciones**

- `ck_eventos_outbox_tipo_vocabulario: tipo IN ('RELEASE_PUBLICADO', 'NORMA_ACTUALIZADA', 'VALOR_ACTUALIZADO', 'PLAZO_ACTUALIZADO', 'CANAL_ACTUALIZADO', 'CONFLICTO_ABIERTO', 'FUENTE_DEGRADADA')`
- `ck_eventos_outbox_intentos_no_negativos: intentos >= 0`

**Índices**

- `ix_eventos_outbox_pendientes (índice): (creado_en)`
- `ix_eventos_outbox_release_id (índice): (release_id)`

## evidencias

Localizador verificable de un fragmento dentro de una versión documental.

    Una URL sola no prueba un valor. La unidad citada debe pertenecer a la misma
    versión que el documento referenciado; el control se aplica por trigger.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `doc_version_id` | UUID | no | — | `documento_versiones.id` |
| `unidad_id` | UUID | sí | — | `unidades_documentales.id` |
| `fragmento` | TEXT | no | — | — |
| `selector` | TEXT | sí | — | — |
| `pagina` | INTEGER | sí | — | — |
| `offset_inicio` | INTEGER | sí | — | — |
| `offset_fin` | INTEGER | sí | — | — |
| `hash_fragmento` | VARCHAR(64) | no | — | — |
| `tipo` | VARCHAR(32) | no | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_evidencias_offsets_ordenados: offset_fin IS NULL OR offset_inicio IS NULL OR offset_fin >= offset_inicio`
- `ck_evidencias_fragmento_no_vacio: length(btrim(fragmento)) > 0`
- `ck_evidencias_tipo_vocabulario: tipo IN ('FRAGMENTO_TEXTO', 'CELDA_TABLA', 'CAMPO_JSON', 'CAMPO_CSV', 'REGION_PDF', 'CARGA_MANUAL')`
- `ck_evidencias_hash_fragmento_hex: hash_fragmento ~ '^[0-9a-f]{64}$'`

**Índices**

- `ix_evidencias_doc_version_id (índice): (doc_version_id)`
- `ix_evidencias_hash (índice): (hash_fragmento)`
- `ix_evidencias_unidad_id (índice): (unidad_id)`

## fuente_config_versiones

Configuración de extracción versionada: cada cambio de selector, de
    frecuencia o de presupuesto queda auditable y referenciable desde la corrida
    que lo usó.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `source_id` | VARCHAR(16) | no | — | `fuentes.source_id` |
| `version` | INTEGER | no | — | — |
| `adaptador` | VARCHAR(32) | no | — | — |
| `selector_config` | JSONB | sí | — | — |
| `frecuencia` | DATETIME | sí | — | — |
| `ttl_defecto` | DATETIME | sí | — | — |
| `presupuesto` | JSONB | sí | — | — |
| `politica_version` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_fuente_config_versiones_source_version: (source_id, version)`

**Verificaciones**

- `ck_fuente_config_versiones_adaptador_vocabulario: adaptador IN ('DATASET_ABIERTO', 'HTML_ESTATICO', 'API_JSON', 'PDF', 'CARGA_MANUAL', 'SIN_ADAPTADOR')`
- `ck_fuente_config_versiones_version_positiva: version >= 1`

**Índices**

- `ix_fuente_config_versiones_source_id (índice): (source_id)`

## fuente_urls

URL HTTP(S) concreta. Sin plantillas ni secretos, y sin quitar parámetros
    de consulta que cambian el contenido servido.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `source_id` | VARCHAR(16) | no | — | `fuentes.source_id` |
| `url` | TEXT | no | — | — |
| `rol` | VARCHAR(32) | no | — | — |
| `tipo_acceso` | VARCHAR(32) | no | — | — |
| `es_canonica` | BOOLEAN | no | `false` | — |
| `descubierta_en` | TIMESTAMP | no | `now()` | — |
| `url_padre_id` | UUID | sí | — | `fuente_urls.id` |

**Claves únicas**

- `uq_fuente_urls_source_url: (source_id, url)`

**Verificaciones**

- `ck_fuente_urls_url_sin_plantilla: url !~ '[{}]'`
- `ck_fuente_urls_sin_autopadre: url_padre_id IS NULL OR url_padre_id <> id`
- `ck_fuente_urls_url_concreta: url ~ '^(https?|manual)://'`
- `ck_fuente_urls_tipo_acceso_vocabulario: tipo_acceso IN ('HTTP_GET_PUBLICO', 'API_PUBLICA', 'DESCARGA_ARCHIVO', 'CARGA_MANUAL')`
- `ck_fuente_urls_rol_vocabulario: rol IN ('ENTRADA', 'LISTADO', 'DETALLE', 'DESCARGA', 'API', 'ANEXO', 'ALTERNATIVA')`

**Índices**

- `ix_fuente_urls_source_id (índice): (source_id)`
- `ix_fuente_urls_url_padre_id (índice): (url_padre_id)`

## fuentes

Catálogo del corpus. `source_id` conserva los identificadores del paquete
    (F01–F67, D01–D10, M01–M06): son la clave de trazabilidad con el manual y no
    se renumeran.

    `estado`, `access_status` y `alias_of` son independientes: un alias no está
    necesariamente caído, y una fuente activa puede estar limitada hoy.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `source_id` | VARCHAR(16) | no | — | — |
| `organismo_id` | UUID | sí | — | `organismos.id` |
| `alias_of` | VARCHAR(16) | sí | — | `fuentes.source_id` |
| `nombre` | TEXT | no | — | — |
| `clase` | VARCHAR(32) | no | — | — |
| `caracter` | VARCHAR(16) | no | `OFICIAL` | — |
| `estado` | VARCHAR(32) | no | — | — |
| `access_status` | VARCHAR(32) | no | — | — |
| `prioridad` | VARCHAR(4) | no | — | — |
| `motivo_estado` | TEXT | sí | — | — |
| `exclusion_reason` | TEXT | sí | — | — |
| `responsable_rol` | TEXT | sí | — | — |
| `alcance` | TEXT | sí | — | — |
| `politica_acceso` | VARCHAR(64) | no | — | — |
| `relacionadas` | JSONB | sí | — | — |
| `origen` | TEXT | sí | — | — |
| `manual_pagina` | INTEGER | sí | — | — |
| `origen_url_status` | TEXT | sí | — | — |
| `tarea` | TEXT | sí | — | — |
| `aceptacion_especifica` | JSONB | sí | — | — |
| `tablas_destino` | JSONB | sí | — | — |
| `referencia_selectores` | TEXT | sí | — | — |
| `referencia_campos` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_fuentes_access_status_vocabulario: access_status IN ('NO_VERIFICADO', 'ACCESIBLE', 'ACCESO_LIMITADO', 'BLOQUEADA', 'ERROR_TLS', 'NO_ENCONTRADA', 'SIN_URL_CONOCIDA')`
- `ck_fuentes_prioridad_vocabulario: prioridad IN ('P0', 'P1', 'P2', 'P3')`
- `ck_fuentes_sin_autoalias: alias_of IS NULL OR alias_of <> source_id`
- `ck_fuentes_caracter_vocabulario: caracter IN ('OFICIAL', 'SECUNDARIA')`
- `ck_fuentes_clase_vocabulario: clase IN ('DATASET', 'BOLETIN', 'PORTAL_NORMATIVO', 'FICHA_TRAMITE', 'DIRECTORIO', 'DOCUMENTO', 'PADRON', 'CANAL_ATENCION', 'ALIAS', 'OTRA')`
- `ck_fuentes_politica_acceso_vocabulario: politica_acceso IN ('PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS', 'NO_AUTOMATION_UNTIL_IDENTIFIED_AND_PUBLIC', 'MANUAL_ONLY')`
- `ck_fuentes_estado_excepcional_con_motivo: estado NOT IN ('DEGRADED','QUARANTINED','RETIRED') OR motivo_estado IS NOT NULL`
- `ck_fuentes_estado_vocabulario: estado IN ('DISCOVERY', 'ACTIVE', 'DEGRADED', 'QUARANTINED', 'REFERENCE_ONLY', 'MANUAL', 'RETIRED')`

**Índices**

- `ix_fuentes_alias_of (índice): (alias_of)`
- `ix_fuentes_caracter (índice): (caracter)`
- `ix_fuentes_estado_prioridad (índice): (estado, prioridad)`
- `ix_fuentes_organismo_id (índice): (organismo_id)`

## fuentes_candidatas

Descubrimiento acotado y deduplicado. No es una cola de rastreo
    ilimitada: cada candidata nace de una evidencia concreta.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `source_id_origen` | VARCHAR(16) | no | — | `fuentes.source_id` |
| `evidencia_id` | UUID | sí | — | `evidencias.id` |
| `url` | TEXT | no | — | — |
| `relacion` | TEXT | sí | — | — |
| `tipo_esperado` | VARCHAR(32) | sí | — | — |
| `estado` | VARCHAR(32) | no | — | — |
| `prioridad` | VARCHAR(4) | sí | — | — |
| `alias_detectado` | TEXT | sí | — | — |
| `descubierta_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_fuentes_candidatas_origen_url: (source_id_origen, url)`

**Verificaciones**

- `ck_fuentes_candidatas_prioridad_vocabulario: prioridad IS NULL OR prioridad IN ('P0', 'P1', 'P2', 'P3')`
- `ck_fuentes_candidatas_estado_vocabulario: estado IN ('NUEVA', 'EN_EVALUACION', 'PROMOVIDA', 'DESCARTADA', 'DUPLICADA')`
- `ck_fuentes_candidatas_url_http_concreta: url ~ '^https?://'`

**Índices**

- `ix_fuentes_candidatas_evidencia_id (índice): (evidencia_id)`
- `ix_fuentes_candidatas_source_id_origen (índice): (source_id_origen)`

## incidencias_revision

Conflicto o ambigüedad que necesita decisión humana.

    Resolver una incidencia no borra el conflicto histórico: se conserva quién
    decidió, con qué fundamento y cuándo. "Más reciente" o "más oficial" no es
    un algoritmo universal de desempate.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `registro_version_id` | UUID | sí | — | `registro_versiones.id` |
| `source_id` | VARCHAR(16) | sí | — | `fuentes.source_id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `severidad` | VARCHAR(16) | no | — | — |
| `descripcion` | TEXT | sí | — | — |
| `candidatos` | JSONB | sí | — | — |
| `estado` | VARCHAR(16) | no | — | — |
| `responsable_rol` | TEXT | sí | — | — |
| `decision` | TEXT | sí | — | — |
| `decidido_por` | TEXT | sí | — | — |
| `fundamento_evidencia_id` | UUID | sí | — | `evidencias.id` |
| `resuelta_en` | TIMESTAMP | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_incidencias_revision_severidad_vocabulario: severidad IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')`
- `ck_incidencias_revision_resuelta_con_decision_y_actor: estado <> 'RESUELTA' OR (decision IS NOT NULL AND decidido_por IS NOT NULL AND resuelta_en IS NOT NULL)`
- `ck_incidencias_revision_estado_vocabulario: estado IN ('ABIERTA', 'EN_REVISION', 'RESUELTA', 'DIFERIDA')`
- `ck_incidencias_revision_tipo_vocabulario: tipo IN ('CONFLICTO_DE_FUENTES', 'IDENTIDAD_AMBIGUA', 'DISCREPANCIA_NUMERACION', 'VIGENCIA_INDETERMINADA', 'COBERTURA_EXTRACCION', 'ACCESO_BLOQUEADO', 'CAMBIO_DE_ESQUEMA', 'DATO_FALTANTE_CRITICO')`

**Índices**

- `ix_incidencias_revision_estado_severidad (índice): (estado, severidad)`
- `ix_incidencias_revision_registro_version_id (índice): (registro_version_id)`
- `ix_incidencias_revision_source_id (índice): (source_id)`

## jurisdicciones

Jerarquía acíclica. `id` es un slug estable (`AR`, `AR-C`, `AR-B`, ...)
    para que Nación, CABA, PBA y municipios homónimos no colisionen.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | VARCHAR(32) | no | — | — |
| `parent_id` | VARCHAR(32) | sí | — | `jurisdicciones.id` |
| `nombre` | TEXT | no | — | — |
| `nivel` | VARCHAR(32) | no | — | — |
| `codigo_oficial` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_jurisdicciones_padre_nombre: (parent_id, nombre)`

**Verificaciones**

- `ck_jurisdicciones_sin_autopadre: parent_id IS NULL OR parent_id <> id`
- `ck_jurisdicciones_nivel_vocabulario: nivel IN ('NACIONAL', 'PROVINCIAL', 'CIUDAD_AUTONOMA', 'MUNICIPAL', 'COMUNAL', 'SUPRANACIONAL')`

**Índices**

- `ix_jurisdicciones_parent_id (índice): (parent_id)`

## norma_identificadores

Identificadores oficiales alternativos, cada uno con su espacio de
    nombres. El id de InfoLEG no se mezcla con el de NormativaBA.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `norma_id` | UUID | no | — | `normas.id` |
| `namespace` | VARCHAR(64) | no | — | — |
| `valor` | TEXT | no | — | — |
| `url_oficial` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_norma_identificadores_namespace_valor: (namespace, valor)`

**Verificaciones**

- `ck_norma_identificadores_url_http_concreta: url_oficial IS NULL OR url_oficial ~ '^https?://'`
- `ck_norma_identificadores_namespace_no_vacio: length(btrim(namespace)) > 0`

**Índices**

- `ix_norma_identificadores_norma_id (índice): (norma_id)`

## norma_versiones

Subtipo de `registro_versiones` para una versión de norma.

    `estado_legal_declarado` es lo que dice la fuente; `estado_legal_validado`
    es la conclusión del equipo con su fundamento. Una etiqueta "abrogada" en un
    encabezado no basta para clasificar la norma entera.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `norma_id` | UUID | no | — | `normas.id` |
| `doc_version_id` | UUID | no | — | `documento_versiones.id` |
| `tipo_version` | VARCHAR(32) | no | — | — |
| `estado_legal_declarado` | VARCHAR(32) | sí | — | — |
| `estado_legal_validado` | VARCHAR(32) | no | `'NO_DETERMINADA'` | — |
| `fundamento_estado_evidencia_id` | UUID | sí | — | `evidencias.id` |
| `fecha_consolidacion` | DATE | sí | — | — |

**Verificaciones**

- `ck_norma_versiones_estado_legal_validado_vocabulario: estado_legal_validado IN ('VIGENTE', 'VIGENCIA_PARCIAL', 'CONDICIONADA', 'NO_VIGENTE', 'NO_DETERMINADA')`
- `ck_norma_versiones_estado_legal_declarado_vocabulario: estado_legal_declarado IS NULL OR estado_legal_declarado IN ('VIGENTE', 'VIGENCIA_PARCIAL', 'CONDICIONADA', 'NO_VIGENTE', 'NO_DETERMINADA')`
- `ck_norma_versiones_estado_validado_con_fundamento: estado_legal_validado = 'NO_DETERMINADA' OR fundamento_estado_evidencia_id IS NOT NULL`
- `ck_norma_versiones_tipo_version_vocabulario: tipo_version IN ('ORIGINAL', 'ACTUALIZADO', 'CONSOLIDADO', 'NO_DETERMINADO')`
- `ck_norma_versiones_consolidado_con_fecha: tipo_version <> 'CONSOLIDADO' OR fecha_consolidacion IS NOT NULL`

**Índices**

- `ix_norma_versiones_doc_version_id (índice): (doc_version_id)`
- `ix_norma_versiones_norma_id (índice): (norma_id)`
- `ix_norma_versiones_norma_tipo (índice): (norma_id, tipo_version)`

## normas

Identidad jurídica: jurisdicción + emisor + tipo + número + año.

    Las correcciones de título o de URL no crean otra norma. Una norma cuya
    identidad todavía es incierta se queda sin clave canónica en lugar de
    fusionarse especulativamente con otra.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `jurisdiccion_id` | VARCHAR(32) | no | — | `jurisdicciones.id` |
| `emisor_id` | UUID | sí | — | `organismos.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `numero` | TEXT | sí | — | — |
| `anio` | INTEGER | sí | — | — |
| `titulo` | TEXT | no | — | — |
| `materias` | ARRAY | sí | — | — |
| `sancion` | DATE | sí | — | — |
| `promulgacion` | DATE | sí | — | — |
| `publicacion` | DATE | sí | — | — |
| `identidad_incierta` | BOOLEAN | no | `false` | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_normas_tipo_vocabulario: tipo IN ('LEY', 'DECRETO', 'RESOLUCION', 'DISPOSICION', 'ORDENANZA', 'DECRETO_LEY', 'ACORDADA', 'CONVENIO', 'CONSTITUCION', 'TRATADO', 'OTRO')`
- `ck_normas_anio_plausible: anio IS NULL OR (anio BETWEEN 1810 AND 2200)`

**Índices**

- `ix_normas_emisor_id (índice): (emisor_id)`
- `ix_normas_emisor_tipo_numero_anio (índice): (emisor_id, tipo, numero, anio)`
- `ix_normas_jurisdiccion_id (índice): (jurisdiccion_id)`
- `ix_normas_orden_listado (índice): (numero)`
- `ix_normas_publicacion (índice): (publicacion)`
- `uq_normas_clave_canonica (único): (jurisdiccion_id, tipo, numero, anio)`

## organismos

Emisor, autoridad de aplicación, prestador y ONG se distinguen por `tipo`;
    un mismo nombre puede cumplir varios roles en jurisdicciones distintas.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `jurisdiccion_id` | VARCHAR(32) | no | — | `jurisdicciones.id` |
| `nombre` | TEXT | no | — | — |
| `tipo` | VARCHAR(32) | no | — | — |
| `sigla` | TEXT | sí | — | — |
| `identificador_oficial` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_organismos_jurisdiccion_nombre_tipo: (jurisdiccion_id, nombre, tipo)`

**Verificaciones**

- `ck_organismos_tipo_vocabulario: tipo IN ('EMISOR', 'AUTORIDAD_APLICACION', 'PRESTADOR', 'ORGANISMO_CONTROL', 'ONG', 'OTRO')`

**Índices**

- `ix_organismos_jurisdiccion_id (índice): (jurisdiccion_id)`

## parametro_valores

Subtipo de `registro_versiones`: el valor de un parámetro para un período,
    territorio y segmento.

    La exclusión temporal entre valores aprobados se aplica en la migración con
    un `EXCLUDE` sobre el rango de aplicación; los candidatos en conflicto sí
    pueden coexistir, y quedan fuera de la vista servible.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `hecho_id` | UUID | no | — | — |
| `parametro_id` | UUID | no | — | `parametros.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `valor` | NUMERIC(20, 4) | no | — | — |
| `unidad` | TEXT | no | — | — |
| `moneda` | VARCHAR(3) | sí | — | — |
| `periodo` | DATE | sí | — | — |
| `territorio_id` | VARCHAR(32) | sí | — | `jurisdicciones.id` |
| `segmento` | TEXT | sí | — | — |
| `dimensiones` | JSONB | sí | — | — |
| `dimensiones_hash` | TEXT | no | `Computed(<sqlalchemy.sql.elements.TextClause object at 0x7efdd9c13510>, persisted=True)` | — |
| `rango_aplicacion` | DATERANGE | sí | — | — |
| `publicable` | BOOLEAN | no | `false` | — |

**Verificaciones**

- `ck_parametro_valores_moneda_iso4217: moneda IS NULL OR moneda ~ '^[A-Z]{3}$'`

**Índices**

- `ix_parametro_valores_hecho_id (índice): (hecho_id)`
- `ix_parametro_valores_parametro_id (índice): (parametro_id)`
- `ix_parametro_valores_parametro_periodo (índice): (parametro_id, periodo)`
- `ix_parametro_valores_territorio_id (índice): (territorio_id)`

## parametros

Concepto medible con unidad propia. Los catálogos se mantienen separados:
    un salario mínimo, un salario de convenio, el monto de una prestación y un
    tope de ingreso no son el mismo parámetro aunque coincidan en un período.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `codigo` | TEXT | no | — | — |
| `concepto` | TEXT | no | — | — |
| `unidad` | TEXT | no | — | — |
| `moneda` | VARCHAR(3) | sí | — | — |
| `definicion` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_parametros_codigo: (codigo)`

**Verificaciones**

- `ck_parametros_importe_con_moneda: unidad <> 'MONEDA' OR moneda IS NOT NULL`
- `ck_parametros_moneda_iso4217: moneda IS NULL OR moneda ~ '^[A-Z]{3}$'`
- `ck_parametros_codigo_normalizado: codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'`

## plazos

Subtipo de `registro_versiones`.

    Exactamente un propietario principal entre beneficio, trámite y norma; los
    vínculos adicionales se resuelven navegando sus relaciones.

    Un intervalo fechado (`inicio`/`fin`) y uno relativo (`cantidad` + `unidad` +
    `evento_inicio`) son modalidades distintas y no se mezclan. El cómputo en
    días hábiles exige un calendario con cobertura, versión y jurisdicción.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `plazo_id` | UUID | no | — | — |
| `beneficio_version_id` | UUID | sí | — | `beneficio_versiones.registro_version_id` |
| `tramite_version_id` | UUID | sí | — | `tramite_versiones.registro_version_id` |
| `norma_version_id` | UUID | sí | — | `norma_versiones.registro_version_id` |
| `calendario_id` | UUID | sí | — | `calendarios.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `inicio` | DATE | sí | — | — |
| `fin` | DATE | sí | — | — |
| `hora_cierre` | TIME | sí | — | — |
| `zona_horaria` | TEXT | no | `'America/Argentina/Buenos_Aires'` | — |
| `cantidad` | INTEGER | sí | — | — |
| `unidad` | TEXT | sí | — | — |
| `tipo_dia` | VARCHAR(32) | no | — | — |
| `evento_inicio` | TEXT | sí | — | — |
| `regla_computo` | JSONB | sí | — | — |
| `ciclo` | INTEGER | sí | — | — |
| `convocatoria` | TEXT | sí | — | — |
| `inclusivo_desde` | BOOLEAN | no | `true` | — |
| `inclusivo_hasta` | BOOLEAN | no | `true` | — |

**Verificaciones**

- `ck_plazos_un_solo_propietario_principal: (CASE WHEN beneficio_version_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN tramite_version_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN norma_version_id IS NOT NULL THEN 1 ELSE 0 END) = 1`
- `ck_plazos_fin_tras_inicio: fin IS NULL OR inicio IS NULL OR fin >= inicio`
- `ck_plazos_ciclo_positivo: ciclo IS NULL OR ciclo >= 1`
- `ck_plazos_habil_exige_calendario: tipo_dia NOT IN ('HABIL_ADMINISTRATIVO','HABIL_JUDICIAL') OR calendario_id IS NOT NULL`
- `ck_plazos_fechado_o_relativo_no_ambos: (inicio IS NOT NULL OR fin IS NOT NULL) <> (cantidad IS NOT NULL)`
- `ck_plazos_relativo_con_unidad_y_evento: cantidad IS NULL OR (cantidad >= 0 AND unidad IS NOT NULL AND evento_inicio IS NOT NULL)`
- `ck_plazos_tipo_vocabulario: tipo IN ('VIGENCIA_JURIDICA', 'CONVOCATORIA', 'DURACION_BENEFICIO', 'RENOVACION', 'PRESENTACION_DOCUMENTAL', 'RESPUESTA_ORGANISMO', 'SUBSANACION', 'RECURSO', 'FECHA_PAGO')`
- `ck_plazos_tipo_dia_vocabulario: tipo_dia IN ('CORRIDO', 'HABIL_ADMINISTRATIVO', 'HABIL_JUDICIAL', 'NO_INFORMADO')`

**Índices**

- `ix_plazos_beneficio_version_id (índice): (beneficio_version_id)`
- `ix_plazos_convocatoria (índice): (convocatoria, ciclo)`
- `ix_plazos_norma_version_id (índice): (norma_version_id)`
- `ix_plazos_plazo_id (índice): (plazo_id)`
- `ix_plazos_tipo_inicio_fin (índice): (tipo, inicio, fin)`
- `ix_plazos_tramite_version_id (índice): (tramite_version_id)`

## poblaciones

Vocabulario curado de grupos destinatarios. Describe categorías de una
    disposición, no clasifica personas reales.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `codigo` | TEXT | no | — | — |
| `nombre` | TEXT | no | — | — |
| `definicion` | TEXT | sí | — | — |
| `vocabulario_version` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_poblaciones_codigo: (codigo)`

**Verificaciones**

- `ck_poblaciones_codigo_normalizado: codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'`

## punto_versiones

Subtipo de `registro_versiones`. Coordenadas WGS84 válidas o ninguna: sin
    CRS conocido no se reproyecta, y sin coordenadas no se afirma cercanía.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `punto_id` | UUID | no | — | `puntos_atencion.id` |
| `direccion_cruda` | TEXT | sí | — | — |
| `direccion_legible` | TEXT | sí | — | — |
| `localidad` | TEXT | sí | — | — |
| `lat` | NUMERIC(9, 6) | sí | — | — |
| `lng` | NUMERIC(9, 6) | sí | — | — |
| `coordenadas_origen` | JSONB | sí | — | — |
| `crs` | TEXT | sí | — | — |
| `es_presencial` | BOOLEAN | sí | — | — |
| `observaciones` | TEXT | sí | — | — |

**Verificaciones**

- `ck_punto_versiones_coordenadas_con_crs: lat IS NULL OR crs IS NOT NULL`
- `ck_punto_versiones_coordenadas_en_rango: lat IS NULL OR (lat BETWEEN -90 AND 90 AND lng BETWEEN -180 AND 180)`
- `ck_punto_versiones_coordenadas_completas_o_ausentes: (lat IS NULL) = (lng IS NULL)`

**Índices**

- `ix_punto_versiones_localidad (índice): (localidad)`
- `ix_punto_versiones_punto_id (índice): (punto_id)`

## puntos_atencion

Lugar de atención. El organismo que lista y el que atiende pueden diferir.

    Un barrio del padrón RENABAP no es una oficina: vive en `barrios_renabap`.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `organismo_id` | UUID | no | — | `organismos.id` |
| `jurisdiccion_id` | VARCHAR(32) | no | — | `jurisdicciones.id` |
| `organismo_operador_id` | UUID | sí | — | `organismos.id` |
| `nombre` | TEXT | no | — | — |
| `tipo` | VARCHAR(32) | no | — | — |
| `alcance` | VARCHAR(16) | no | `NO_DECLARADO` | — |
| `ambito` | TEXT | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_puntos_atencion_alcance_vocabulario: alcance IN ('NACIONAL', 'PROVINCIAL', 'MUNICIPAL', 'NO_DECLARADO')`
- `ck_puntos_atencion_tipo_vocabulario: tipo IN ('SEDE', 'DELEGACION', 'OFICINA_MOVIL', 'CENTRO_COMUNITARIO', 'JUZGADO', 'OTRO')`
- `ck_puntos_atencion_ck_puntos_atencion_municipal_declara_su_ambito: alcance <> 'MUNICIPAL' OR ambito IS NOT NULL`

**Índices**

- `ix_puntos_atencion_alcance (índice): (alcance)`
- `ix_puntos_atencion_jurisdiccion_id (índice): (jurisdiccion_id)`
- `ix_puntos_atencion_nombre (índice): (nombre)`
- `ix_puntos_atencion_organismo_id (índice): (organismo_id)`

## referencias_pendientes

Cita cuya norma destino todavía no se pudo identificar. Se conserva el
    texto literal y las identidades candidatas; no se inventa un destino ni se
    la descarta en silencio.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `norma_origen_id` | UUID | no | — | `normas.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `texto_cita` | TEXT | no | — | — |
| `identidad_candidata` | JSONB | sí | — | — |
| `motivo` | TEXT | sí | — | — |
| `estado` | VARCHAR(16) | no | — | — |
| `responsable_rol` | TEXT | sí | — | — |
| `relacion_resultante_id` | UUID | sí | — | `relaciones_normativas.id` |
| `resuelta_en` | TIMESTAMP | sí | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_referencias_pendientes_estado_vocabulario: estado IN ('PENDIENTE', 'RESUELTA', 'IRRESOLUBLE')`
- `ck_referencias_pendientes_resuelta_con_relacion: estado <> 'RESUELTA' OR (relacion_resultante_id IS NOT NULL AND resuelta_en IS NOT NULL)`
- `ck_referencias_pendientes_texto_cita_no_vacio: length(btrim(texto_cita)) > 0`

**Índices**

- `ix_referencias_pendientes_estado (índice): (estado)`
- `ix_referencias_pendientes_norma_origen_id (índice): (norma_origen_id)`

## registro_versiones

Supertipo controlado. Cada subtipo referencia una fila de esta tabla y un
    trigger verifica que `entidad_tipo` corresponda al subtipo real: es la forma
    de tener afirmaciones apuntando a "cualquier versión" sin una FK polimórfica
    sin control.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `entidad_tipo` | VARCHAR(32) | no | — | — |
| `entidad_id` | UUID | no | — | — |
| `numero_version` | INTEGER | no | `1` | — |
| `estado_revision` | VARCHAR(16) | no | — | — |
| `valid_desde` | DATE | sí | — | — |
| `valid_hasta` | DATE | sí | — | — |
| `valid_tipo` | VARCHAR(16) | no | — | — |
| `condicion_vigencia` | TEXT | sí | — | — |
| `known_desde` | TIMESTAMP | no | `now()` | — |
| `known_hasta` | TIMESTAMP | sí | — | — |
| `verificado_en` | TIMESTAMP | sí | — | — |
| `reverificar_antes_de` | TIMESTAMP | sí | — | — |
| `release_id` | UUID | sí | — | `releases.id` |

**Claves únicas**

- `uq_registro_versiones_entidad: (entidad_tipo, entidad_id, numero_version)`

**Verificaciones**

- `ck_registro_versiones_numero_version_positivo: numero_version >= 1`
- `ck_registro_versiones_known_ordenado: known_hasta IS NULL OR known_hasta >= known_desde`
- `ck_registro_versiones_condicionado_con_condicion: valid_tipo <> 'CONDICIONADO' OR condicion_vigencia IS NOT NULL`
- `ck_registro_versiones_cerrado_con_ambos_extremos: valid_tipo <> 'CERRADO' OR (valid_desde IS NOT NULL AND valid_hasta IS NOT NULL)`
- `ck_registro_versiones_valid_tipo_vocabulario: valid_tipo IN ('CERRADO', 'ABIERTO_FIN', 'ABIERTO_INICIO', 'PUNTUAL', 'CONDICIONADO', 'DESCONOCIDO')`
- `ck_registro_versiones_estado_revision_vocabulario: estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')`
- `ck_registro_versiones_entidad_tipo_vocabulario: entidad_tipo IN ('norma', 'beneficio', 'parametro_valor', 'plazo', 'tramite', 'punto_atencion', 'canal', 'barrio_renabap')`
- `ck_registro_versiones_abierto_fin_sin_hasta: valid_tipo <> 'ABIERTO_FIN' OR valid_hasta IS NULL`
- `ck_registro_versiones_publicado_con_release_y_verificacion: estado_revision <> 'PUBLISHED' OR (release_id IS NOT NULL AND verificado_en IS NOT NULL)`
- `ck_registro_versiones_puntual_un_solo_dia: valid_tipo <> 'PUNTUAL' OR (valid_desde IS NOT NULL AND valid_hasta = valid_desde)`
- `ck_registro_versiones_valid_ordenado: valid_hasta IS NULL OR valid_desde IS NULL OR valid_hasta >= valid_desde`

**Índices**

- `ix_registro_versiones_entidad (índice): (entidad_tipo, entidad_id)`
- `ix_registro_versiones_estado (índice): (estado_revision)`
- `ix_registro_versiones_frescura (índice): (reverificar_antes_de)`
- `ix_registro_versiones_publicadas (índice): (release_id)`
- `ix_registro_versiones_release_id (índice): (release_id)`
- `ix_registro_versiones_valid (índice): (valid_desde, valid_hasta)`
- `uq_registro_versiones_known_abierto (único): (entidad_tipo, entidad_id, numero_version)`

## regla_dependencias

Excepciones y precedencias explícitas entre reglas. Una colisión no se
    resuelve por orden de carga.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `regla_id` | UUID | no | — | `reglas.id` |
| `regla_referida_id` | UUID | no | — | `reglas.id` |
| `tipo` | VARCHAR(32) | no | — | — |

**Verificaciones**

- `ck_regla_dependencias_tipo_vocabulario: tipo IN ('EXCEPCION_DE', 'PRECEDE_A', 'REQUIERE', 'INCOMPATIBLE_CON')`
- `ck_regla_dependencias_sin_autodependencia: regla_id <> regla_referida_id`

**Índices**

- `ix_regla_dependencias_regla_referida_id (índice): (regla_referida_id)`

## regla_parametros

Parámetros que usa el AST de una regla. Un cambio de valor dispara la
    reevaluación de las reglas afectadas.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `regla_id` | UUID | no | — | `reglas.id` |
| `parametro_id` | UUID | no | — | `parametros.id` |
| `rol` | VARCHAR(32) | no | — | — |

**Índices**

- `ix_regla_parametros_parametro_id (índice): (parametro_id)`

## reglas

Condición jurídica con su texto literal y, cuando fue validada, su AST.

    El literal se conserva siempre: preserva negaciones, cuantificadores,
    excepciones y unidades que una paráfrasis pierde. El AST solo se ejecuta
    tras validación (`estado_revision` aprobado y `requiere_revision` en falso).

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `beneficio_version_id` | UUID | no | — | `beneficio_versiones.registro_version_id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `categoria` | VARCHAR(32) | no | — | — |
| `texto_literal` | TEXT | no | — | — |
| `descripcion` | TEXT | sí | — | — |
| `ast` | JSONB | sí | — | — |
| `ast_schema_version` | TEXT | sí | — | — |
| `requiere_revision` | BOOLEAN | no | `true` | — |
| `alcance` | TEXT | sí | — | — |
| `estado_revision` | VARCHAR(16) | no | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Verificaciones**

- `ck_reglas_ejecutable_solo_tras_validacion: requiere_revision = true OR (ast IS NOT NULL AND estado_revision IN ('APPROVED','PUBLISHED'))`
- `ck_reglas_estado_revision_vocabulario: estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')`
- `ck_reglas_texto_literal_no_vacio: length(btrim(texto_literal)) > 0`
- `ck_reglas_categoria_vocabulario: categoria IN ('APLICABILIDAD', 'EXCLUSION', 'EXCEPCION', 'PRIORIDAD', 'SALVAGUARDA', 'REVOCACION', 'SUSPENSION', 'CESE', 'SUBSANACION', 'REHABILITACION', 'COMPATIBILIDAD')`
- `ck_reglas_ast_con_version_de_esquema: ast IS NULL OR ast_schema_version IS NOT NULL`

**Índices**

- `ix_reglas_beneficio_categoria (índice): (beneficio_version_id, categoria)`
- `ix_reglas_beneficio_version_id (índice): (beneficio_version_id)`

## relaciones_normativas

Dirección explícita: origen es la norma modificatoria, destino la
    modificada. Citar no prueba modificar, por eso `CITA` es un tipo propio.

    El alcance puede limitarse a un artículo, un inciso, un colectivo o un
    período; los ciclos entre citas son legítimos y la navegación los recorre
    con conjunto de visitados y presupuesto.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `norma_origen_id` | UUID | no | — | `normas.id` |
| `norma_destino_id` | UUID | no | — | `normas.id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `unidad_origen_id` | UUID | sí | — | `unidades_documentales.id` |
| `unidad_destino_id` | UUID | sí | — | `unidades_documentales.id` |
| `alcance` | TEXT | sí | — | — |
| `efecto_desde` | DATE | sí | — | — |
| `efecto_hasta` | DATE | sí | — | — |
| `condicion` | TEXT | sí | — | — |
| `estado_revision` | VARCHAR(16) | no | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_relaciones_normativas_arista: (norma_origen_id, norma_destino_id, tipo, unidad_origen_id, unidad_destino_id)`

**Verificaciones**

- `ck_relaciones_normativas_tipo_vocabulario: tipo IN ('CITA', 'MODIFICA', 'SUSTITUYE', 'INCORPORA', 'DEROGA', 'ABROGA', 'RESTABLECE', 'REGLAMENTA', 'COMPLEMENTA', 'CONSOLIDA', 'PRORROGA', 'SUSPENDE', 'TRANSITORIA')`
- `ck_relaciones_normativas_estado_revision_vocabulario: estado_revision IN ('CANDIDATE', 'IN_REVIEW', 'APPROVED', 'PUBLISHED', 'QUARANTINED', 'SUPERSEDED', 'REJECTED')`
- `ck_relaciones_normativas_efecto_ordenado: efecto_hasta IS NULL OR efecto_desde IS NULL OR efecto_hasta >= efecto_desde`

**Índices**

- `ix_relaciones_normativas_destino_tipo (índice): (norma_destino_id, tipo)`
- `ix_relaciones_normativas_norma_destino_id (índice): (norma_destino_id)`
- `ix_relaciones_normativas_norma_origen_id (índice): (norma_origen_id)`
- `ix_relaciones_normativas_origen_tipo (índice): (norma_origen_id, tipo)`

## releases

Corte publicable de proyecciones. Una consulta nunca mezcla dos releases
    incompatibles; revertir es cambiar de release, no borrar filas.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |
| `publicado_en` | TIMESTAMP | sí | — | — |
| `estado` | VARCHAR(16) | no | — | — |
| `manifest_hash` | VARCHAR(64) | sí | — | — |
| `aprobado_por` | TEXT | sí | — | — |
| `motivo` | TEXT | sí | — | — |

**Verificaciones**

- `ck_releases_estado_vocabulario: estado IN ('BORRADOR', 'PUBLICADO', 'REVERTIDO')`
- `ck_releases_manifest_hash_hex: manifest_hash IS NULL OR manifest_hash ~ '^[0-9a-f]{64}$'`
- `ck_releases_publicado_con_acta: estado <> 'PUBLICADO' OR (publicado_en IS NOT NULL AND aprobado_por IS NOT NULL  AND manifest_hash IS NOT NULL)`

**Índices**

- `ix_releases_estado_publicado (índice): (estado, publicado_en)`

## tramite_pasos

Paso del procedimiento. El orden es un dato de la fuente, no el orden de
    lectura de un PDF: si la fuente no lo establece, no se inventa.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `tramite_version_id` | UUID | no | — | `tramite_versiones.registro_version_id` |
| `evidencia_id` | UUID | no | — | `evidencias.id` |
| `orden` | INTEGER | no | — | — |
| `accion` | TEXT | no | — | — |
| `canal_id` | UUID | sí | — | `canales.registro_version_id` |
| `documentacion` | TEXT | sí | — | — |
| `alternativas` | TEXT | sí | — | — |

**Claves únicas**

- `uq_tramite_pasos_orden: (tramite_version_id, orden)`

**Verificaciones**

- `ck_tramite_pasos_orden_positivo: orden >= 1`

**Índices**

- `ix_tramite_pasos_tramite_version_id (índice): (tramite_version_id)`

## tramite_versiones

Subtipo de `registro_versiones`.

    `estado_operativo` describe la disponibilidad del canal, no el derecho: un
    sistema sin turnos disponibles no elimina el trámite ni revoca el beneficio.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `registro_version_id` | UUID | no | — | `registro_versiones.id` |
| `tramite_id` | UUID | no | — | `tramites.id` |
| `doc_version_id` | UUID | sí | — | `documento_versiones.id` |
| `descripcion` | TEXT | sí | — | — |
| `cta_url` | TEXT | sí | — | — |
| `costo_parametro_id` | UUID | sí | — | `parametros.id` |
| `duracion_texto` | TEXT | sí | — | — |
| `estado_operativo` | VARCHAR(16) | no | — | — |

**Verificaciones**

- `ck_tramite_versiones_estado_operativo_vocabulario: estado_operativo IN ('DISPONIBLE', 'SIN_TURNOS', 'SUSPENDIDO', 'NO_INFORMADO')`
- `ck_tramite_versiones_url_http_concreta: cta_url IS NULL OR cta_url ~ '^https?://'`

**Índices**

- `ix_tramite_versiones_doc_version_id (índice): (doc_version_id)`
- `ix_tramite_versiones_tramite_id (índice): (tramite_id)`

## tramites

Procedimiento con identidad propia. Un botón duplicado en dos páginas no
    crea dos trámites; el público destinatario sí los diferencia.

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `organismo_id` | UUID | no | — | `organismos.id` |
| `beneficio_id` | UUID | sí | — | `beneficios.id` |
| `codigo` | TEXT | no | — | — |
| `titulo` | TEXT | no | — | — |
| `publico` | VARCHAR(16) | no | — | — |
| `creado_en` | TIMESTAMP | no | `now()` | — |

**Claves únicas**

- `uq_tramites_codigo: (codigo)`

**Verificaciones**

- `ck_tramites_codigo_normalizado: codigo ~ '^[A-Z0-9][A-Z0-9_.-]*$'`
- `ck_tramites_publico_vocabulario: publico IN ('CIUDADANO', 'INSTITUCIONAL', 'AMBOS', 'NO_INFORMADO')`

**Índices**

- `ix_tramites_beneficio_id (índice): (beneficio_id)`
- `ix_tramites_organismo_id (índice): (organismo_id)`

## unidades_documentales

Segmento del texto con su lugar en la jerarquía.

    `ruta` es la ruta jerárquica materializada dentro de la versión y sostiene
    la unicidad: dos artículos raíz no comparten ruta, pero un mismo número
    puede aparecer citado dentro de un bloque de sustitución (`rol_contenido`
    distinto de `DISPOSITIVO`).

| Columna | Tipo | Nulo | Defecto | Referencia |
| --- | --- | --- | --- | --- |
| `id` | UUID | no | `gen_random_uuid()` | — |
| `doc_version_id` | UUID | no | — | `documento_versiones.id` |
| `parent_id` | UUID | sí | — | `unidades_documentales.id` |
| `tipo` | VARCHAR(32) | no | — | — |
| `numero` | TEXT | sí | — | — |
| `sufijo` | TEXT | sí | — | — |
| `rotulo` | TEXT | sí | — | — |
| `ruta` | TEXT | no | — | — |
| `orden` | INTEGER | no | — | — |
| `texto` | TEXT | no | — | — |
| `inicio` | INTEGER | sí | — | — |
| `fin` | INTEGER | sí | — | — |
| `pagina_desde` | INTEGER | sí | — | — |
| `pagina_hasta` | INTEGER | sí | — | — |
| `rol_contenido` | VARCHAR(16) | no | — | — |

**Verificaciones**

- `ck_unidades_documentales_tipo_vocabulario: tipo IN ('PREAMBULO', 'VISTO', 'CONSIDERANDO', 'LIBRO', 'TITULO', 'CAPITULO', 'SECCION', 'ARTICULO', 'INCISO', 'PARRAFO', 'ANEXO', 'TRANSITORIA', 'FIRMA', 'TABLA', 'NO_RECONOCIDO')`
- `ck_unidades_documentales_paginas_ordenadas: pagina_hasta IS NULL OR pagina_desde IS NULL OR pagina_hasta >= pagina_desde`
- `ck_unidades_documentales_sin_autopadre: parent_id IS NULL OR parent_id <> id`
- `ck_unidades_documentales_offsets_ordenados: fin IS NULL OR inicio IS NULL OR fin >= inicio`
- `ck_unidades_documentales_rol_contenido_vocabulario: rol_contenido IN ('DISPOSITIVO', 'CITADO', 'SUSTITUTIVO', 'INCORPORADO', 'HISTORICO', 'NOTA')`

**Índices**

- `ix_unidades_documentales_doc_version_id (índice): (doc_version_id)`
- `ix_unidades_documentales_parent_id (índice): (parent_id)`
- `ix_unidades_documentales_version_orden (índice): (doc_version_id, orden)`
- `uq_unidades_documentales_ruta_dispositiva (único): (doc_version_id, ruta)`
