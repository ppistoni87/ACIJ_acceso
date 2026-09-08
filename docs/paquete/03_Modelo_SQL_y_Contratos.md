# Modelo SQL y contratos funcionales

Versión 1.0 · Diseño de destino para implementar mediante migraciones. Es un diccionario relacional, no un DDL ejecutado. PostgreSQL es la referencia propuesta; adaptar nombres a convenciones del repositorio sin eliminar semántica ni controles.

## 1. Convenciones

- PK internas `UUID`; identificadores oficiales se guardan como texto, con espacio de nombres y claves únicas. No mezclar el id InfoLEG con un id de NormativaBA.
- Fechas jurídicas de día: `DATE`. Instantes de operación: `TIMESTAMPTZ` en UTC. Plazos ciudadanos: `America/Argentina/Buenos_Aires` salvo que la fuente establezca otra zona.
- Importes: `NUMERIC(20,4)` y moneda/unidad. Coeficientes: `NUMERIC(20,8)`. No usar float para evaluar un derecho.
- `NULL` se acompaña de `estado_campo` cuando es sustantivo. Campo obligatorio en publicación no implica `NOT NULL` durante descubrimiento.
- Las tablas de versión son inmutables; registrar nuevo estado por eventos y cerrar intervalos de conocimiento de manera controlada. Distinguir período de aplicación del dato y período durante el cual el sistema lo conoció.
- `JSONB` solo para árboles de reglas, fórmulas declarativas y extras no centrales, con JSON Schema versionado. No esconder población, monto, plazo ni evidencia en una columna libre.
- Toda FK tiene índice si participa de join frecuente. Borrado por defecto `RESTRICT`; un retiro lógico conserva historial. Datos de ciudadanos no forman parte del corpus normativo.
- Evitar FKs polimórficas sin control: si se implementa un supertipo `registro_versiones`, cada subtipo debe referenciarlo y un trigger/restricción diferida debe asegurar el tipo y la pertenencia. Las afirmaciones apuntan a ese supertipo; una URL no sustituye una FK.
- Las tablas tipadas son la proyección operativa de los hechos aprobados. `afirmaciones` conserva candidatos, estado y respaldo por campo; no es una segunda base editable en paralelo. La publicación actualiza ambas representaciones en una transacción e identifica la afirmación de origen de cada valor proyectado.

## 2. Tablas y campos

`*` indica requisito al publicar cuando corresponda; la ingesta en staging puede desconocerlo.

| Tabla | PK / relaciones | Campos de negocio y tipo SQL | Restricciones y propósito |
|---|---|---|---|
| `jurisdicciones` | `id TEXT PK`, `parent_id FK` | `nombre TEXT*`, `nivel TEXT*`, `codigo_oficial TEXT` | Jerarquía acíclica; Nación, CABA, PBA y municipios sin homonimias. |
| `organismos` | `id UUID PK`, `jurisdiccion_id FK` | `nombre TEXT*`, `tipo TEXT*`, `sigla TEXT`, `identificador_oficial TEXT` | Distinguir emisor, autoridad de aplicación, prestador y ONG. |
| `fuentes` | `source_id TEXT PK`, `organismo_id FK`, `alias_of FK fuentes` | `nombre TEXT*`, `clase TEXT*`, `estado TEXT*`, `access_status TEXT*`, `prioridad TEXT*`, `motivo_estado TEXT`, `responsable_rol TEXT`, `alcance TEXT` | Sin autoalias/ciclos. Conservar los 67 IDs y los adicionales. |
| `fuente_urls` | `id UUID PK`, `source_id FK` | `url TEXT*`, `rol TEXT*`, `es_canonica BOOLEAN`, `descubierta_en TIMESTAMPTZ`, `url_padre_id FK`, `tipo_acceso TEXT*` | URL HTTP(S) concreta, sin plantillas ni secretos. No quitar parámetros que cambian contenido. |
| `fuente_config_versiones` | `id UUID PK`, `source_id FK` | `version INT`, `adaptador TEXT*`, `selector_config JSONB`, `frecuencia INTERVAL`, `ttl_defecto INTERVAL`, `presupuesto JSONB`, `politica_version TEXT` | UNIQUE(source_id,version). Cambio de configuración auditable. |
| `corridas_ingesta` | `id UUID PK`, `source_id FK`, `config_version_id FK` | `inicio/fin TIMESTAMPTZ`, `estado TEXT`, `extractor_version TEXT`, `solicitadas/descargadas/procesadas/rechazadas INT`, `checkpoint JSONB` | Contadores no negativos y reconciliados; ejecución incompleta no aparece exitosa. |
| `capturas` | `id UUID PK`, `corrida_id FK`, `source_url_id FK`, `captura_previa_id FK opcional` | `url_final TEXT`, `http_status INT`, `capturado_en TIMESTAMPTZ*`, `mime TEXT`, `bytes BIGINT`, `sha256_raw TEXT*`, `sha256_semantico TEXT`, `objeto_uri TEXT*`, `etag/last_modified TEXT`, `cabeceras JSONB` | Bytes originales inmutables; cabeceras permitidas sin cookies/tokens de sesión. Un 304 exige captura previa válida del mismo recurso y reutiliza su objeto/hash; no inventa cuerpo descargado. |
| `documentos` | `id UUID PK`, `source_id FK` | `tipo TEXT*`, `titulo TEXT`, `idioma TEXT`, `external_id TEXT` | Norma, anexo, guía, FAQ, dataset o procedimiento; no todo documento es norma. |
| `documento_versiones` | `id UUID PK`, `documento_id FK`, `captura_id FK` | `version INT`, `tipo_version TEXT`, `fecha_documento DATE`, `tipo_fecha TEXT`, `texto_extraido TEXT`, `hash_texto TEXT`, `modo_extraccion TEXT`, `paginas INT`, `chars_por_pagina JSONB`, `extraccion_score NUMERIC` | UNIQUE(documento_id,hash_texto,tipo_version). Fecha de firma, publicación y cabecera no son equivalentes. |
| `unidades_documentales` | `id UUID PK`, `doc_version_id FK`, `parent_id FK misma versión` | `tipo TEXT*`, `numero TEXT`, `sufijo TEXT`, `rotulo TEXT`, `orden INT`, `texto TEXT*`, `inicio/fin INT`, `pagina_desde/hasta INT`, `rol_contenido TEXT*` | Unicidad por ruta jerárquica de versión; artículos citados/sustituidos dentro de otro artículo no son raíces. |
| `evidencias` | `id UUID PK`, `doc_version_id FK`, `unidad_id FK` | `fragmento TEXT*`, `selector TEXT`, `pagina INT`, `offset_inicio/fin INT`, `hash_fragmento TEXT`, `tipo TEXT*` | Fragmento coincide con fuente o transformación trazada; unidad y documento deben pertenecer a misma versión. |
| `normas` | `id UUID PK`, `jurisdiccion_id FK`, `emisor_id FK` | `tipo TEXT*`, `numero TEXT`, `anio INT`, `titulo TEXT*`, `materias TEXT[]`, `sancion/promulgacion/publicacion DATE` | Clave canónica cuando está completa; normas en identidad incierta quedan en staging, sin fusión especulativa. |
| `norma_identificadores` | `id UUID PK`, `norma_id FK` | `namespace TEXT*`, `valor TEXT*`, `url_oficial TEXT` | UNIQUE(namespace,valor); permite InfoLEG, NormativaBA, GEDO y alias. |
| `registro_versiones` | `id UUID PK` | `entidad_tipo TEXT*`, `entidad_id UUID*`, `numero_version INT`, `estado_revision TEXT`, `valid_desde/hasta DATE`, `valid_tipo TEXT*`, `condicion_vigencia TEXT`, `known_desde/hasta TIMESTAMPTZ`, `verificado_en/reverificar_antes_de TIMESTAMPTZ`, `release_id FK` | Supertipo controlado por subtipos. `valid_tipo=DESCONOCIDO` nunca se interpreta como vigencia abierta. Intervalos de conocimiento no se solapan para la misma versión lógica. |
| `norma_versiones` | `registro_version_id PK/FK`, `norma_id FK`, `doc_version_id FK` | `tipo_version TEXT*`, `estado_legal_declarado TEXT`, `estado_legal_validado TEXT`, `fundamento_estado_evidencia_id FK`, `fecha_consolidacion DATE` | Una norma puede tener múltiples versiones simultáneamente válidas para distintos períodos o alcances. |
| `equivalencias_unidades` | `id UUID PK`, `origen_unidad_id FK`, `destino_unidad_id FK`, `evidencia_id FK` | `tipo TEXT*`, `motivo TEXT`, `estado_revision TEXT` | Renumeración/sustitución/división/fusión. No identificar solo por número de artículo. |
| `relaciones_normativas` | `id UUID PK`, `norma_origen_id FK`, `norma_destino_id FK`, `evidencia_id FK` | `tipo TEXT*`, `unidad_origen_id FK`, `unidad_destino_id FK`, `alcance TEXT`, `efecto_desde/hasta DATE`, `condicion TEXT`, `estado_revision TEXT` | Dirección explícita: norma modificatoria → norma modificada. Citas pueden ser cíclicas legítimamente; la navegación usa visited y presupuesto. |
| `referencias_pendientes` | `id UUID PK`, `norma_origen_id FK`, `evidencia_id FK` | `texto_cita TEXT*`, `identidad_candidata JSONB`, `motivo TEXT`, `estado TEXT`, `responsable_rol TEXT` | Resolver sin inventar destino; cuando se resuelve, vincular la relación resultante conservando auditoría. |
| `beneficios` | `id UUID PK` | `codigo TEXT UNIQUE*`, `nombre TEXT*`, `linea TEXT`, `familia TEXT` | AUH y otras asignaciones son distinguibles; líneas Progresar separadas. |
| `beneficio_versiones` | `registro_version_id PK/FK`, `beneficio_id FK`, `jurisdiccion_id FK`, `autoridad_id FK` | `naturaleza TEXT*`, `descripcion TEXT*`, `unidad_beneficiaria TEXT`, `modalidad TEXT`, `frecuencia TEXT`, `cupo TEXT`, `requiere_solicitud BOOLEAN` | Valores desconocidos tipados como estado, no booleanos falsos por defecto. |
| `beneficio_normas` | `id UUID PK`, `beneficio_version_id FK`, `norma_version_id FK`, `evidencia_id FK` | `rol TEXT*`, `alcance TEXT` | Muchos-a-muchos; creación, reglamentación, financiamiento u otro rol respaldado. |
| `poblaciones` | `id UUID PK` | `codigo TEXT UNIQUE*`, `nombre TEXT*`, `definicion TEXT`, `vocabulario_version TEXT` | Vocabulario curado, no clasificación sensible de personas reales. |
| `beneficio_poblaciones` | `id UUID PK`, `beneficio_version_id FK`, `poblacion_id FK`, `evidencia_id FK` | `rol_persona TEXT*`, `alcance TEXT`, `regla_id FK` | Titular, causante, representante y conviviente diferenciados. |
| `reglas` | `id UUID PK`, `beneficio_version_id FK`, `evidencia_id FK` | `categoria TEXT*`, `texto_literal TEXT*`, `descripcion TEXT`, `ast JSONB`, `ast_schema_version TEXT`, `requiere_revision BOOLEAN`, `alcance TEXT`, `estado_revision TEXT` | Categorías: aplicabilidad, exclusión, excepción, prioridad, salvaguarda, revocación, suspensión, cese, subsanación, rehabilitación, compatibilidad. AST ejecutable solo tras validación. |
| `regla_dependencias` | `regla_id FK`, `regla_referida_id FK`; PK compuesta con tipo | `tipo TEXT*` | Relaciones de excepción/precedencia explícitas; no resolver colisiones por orden de carga. |
| `regla_parametros` | `regla_id FK`, `parametro_id FK`; PK compuesta con rol | `rol TEXT*` | Dependencias de parámetros usadas por el AST; un cambio dispara reevaluación de la regla afectada. |
| `parametros` | `id UUID PK` | `codigo TEXT UNIQUE*`, `concepto TEXT*`, `unidad TEXT*`, `moneda CHAR(3)`, `definicion TEXT` | Catálogos separados para SMVM, salario convenio de comercio, montos de prestación y topes. |
| `parametro_valores` | `registro_version_id PK/FK`, `parametro_id FK`, `evidencia_id FK` | `valor NUMERIC(20,4)*`, `unidad TEXT*`, `moneda CHAR(3)`, `periodo DATE`, `territorio_id FK`, `segmento TEXT`, `dimensiones JSONB` | Unicidad y exclusión temporal dentro de la misma combinación semántica, solo para valores aprobados. Candidatos conflictivos pueden coexistir. |
| `beneficio_cuantias` | `id UUID PK`, `beneficio_version_id FK`, `evidencia_id FK` | `tipo TEXT*`, `valor_fijo NUMERIC(20,4)`, `moneda CHAR(3)`, `formula_ast JSONB`, `formula_version TEXT`, `redondeo TEXT`, `unidad_beneficiaria TEXT` | Exactamente una modalidad respaldada (fijo/fórmula/especie/no informado); conservar dependencias a parámetros mediante tabla puente. |
| `cuantia_parametros` | `cuantia_id FK`, `parametro_id FK` | `rol TEXT*` | Permite invalidar cuantías derivadas cuando cambia un parámetro. |
| `plazos` | `registro_version_id PK/FK`, `beneficio_version_id FK opcional`, `tramite_version_id FK opcional`, `norma_version_id FK opcional`, `calendario_id FK opcional`, `evidencia_id FK` | `tipo TEXT*`, `inicio/fin DATE`, `hora_cierre TIME`, `zona_horaria TEXT`, `cantidad INT`, `unidad TEXT`, `tipo_dia TEXT`, `evento_inicio TEXT`, `regla_computo JSONB`, `ciclo INT`, `convocatoria TEXT`, `inclusivo_desde/hasta BOOLEAN` | Exactamente un propietario principal entre beneficio, trámite o norma; los vínculos adicionales se resuelven por sus relaciones. Intervalos fechados y relativos son modalidades distintas. Cómputo hábil exige calendario con cobertura, versión y jurisdicción. |
| `calendarios` | `id UUID PK`, `jurisdiccion_id FK` | `nombre TEXT`, `version TEXT`, `fecha_desde/hasta DATE`, `fuente_id FK` | Un calendario administrativo no es universal. |
| `calendario_excepciones` | `id UUID PK`, `calendario_id FK`, `evidencia_id FK` | `fecha DATE*`, `es_habil BOOLEAN*`, `motivo TEXT` | No calcular vencimiento hábil fuera de la cobertura confirmada. |
| `tramites` | `id UUID PK`, `organismo_id FK`, `beneficio_id FK opcional` | `codigo TEXT UNIQUE*`, `titulo TEXT*`, `publico TEXT*` | Ciudadano/institucional diferenciado. No crear trámite por cada botón duplicado. |
| `tramite_versiones` | `registro_version_id PK/FK`, `tramite_id FK`, `doc_version_id FK` | `descripcion TEXT`, `cta_url TEXT`, `costo_parametro_id FK`, `duracion_texto TEXT`, `estado_operativo TEXT` | Un sistema sin turnos disponibles no elimina el trámite ni revoca el beneficio. |
| `tramite_pasos` | `id UUID PK`, `tramite_version_id FK`, `evidencia_id FK` | `orden INT*`, `accion TEXT*`, `canal_id FK`, `documentacion TEXT`, `alternativas TEXT` | Orden único por versión; no inventar secuencia desde orden de lectura de un PDF. |
| `puntos_atencion` | `id UUID PK`, `organismo_id FK`, `jurisdiccion_id FK` | `nombre TEXT*`, `tipo TEXT*`, `organismo_operador_id FK` | Organismo que lista y organismo que atiende pueden diferir. No incluir barrios RENABAP como oficinas. |
| `punto_versiones` | `registro_version_id PK/FK`, `punto_id FK` | `direccion_cruda/legible TEXT`, `localidad TEXT`, `lat/lng NUMERIC`, `coordenadas_origen JSONB`, `crs TEXT`, `es_presencial BOOLEAN`, `observaciones TEXT` | Coordenadas WGS84 válidas; no reproyectar sin CRS conocido. Canales remotos pueden no tener dirección. |
| `canales` | `registro_version_id PK/FK`, `organismo_id FK`, `punto_id FK opcional`, `tramite_id FK opcional`, `evidencia_id FK` | `tipo TEXT*`, `valor_crudo TEXT*`, `valor_normalizado TEXT`, `horario TEXT`, `publico TEXT`, `requiere_autenticacion BOOLEAN` | Horario por canal; correo institucional cuando esté publicado sin desofuscación. No registrar datos de usuarios. |
| `barrios_renabap` | `registro_version_id PK/FK`, `evidencia_id FK` | `id_renabap TEXT*`, `nombre TEXT*`, `provincia/localidad/departamento TEXT`, `viviendas/familias BIGINT`, `datos_habitacionales JSONB`, `fecha_corte DATE` | UNIQUE(id_renabap,versión de padrón). Ausencia en un padrón no es exclusión jurídica definitiva. |
| `afirmaciones` | `id UUID PK`, `registro_version_id FK`, `evidencia_id FK opcional` | `campo_path TEXT*`, `valor JSONB`, `estado_campo TEXT*`, `motivo TEXT`, `source_id FK`, `estado_revision TEXT`, `observado_en TIMESTAMPTZ`, `derivacion_id FK opcional` | JSON Schema por campo. INFORMADO requiere valor/evidencia; NO_APLICA exige motivo y fundamento; NO_INFORMADO exige fuentes revisadas, no prueba negativa inventada. |
| `evaluaciones_completitud` | `id UUID PK`, `norma_version_id FK`, `beneficio_version_id FK opcional` | `campo_solicitado TEXT*`, `estado TEXT*`, `fuentes_revisadas JSONB`, `motivo TEXT`, `revisor_id TEXT` | Siete filas por ficha evaluada, sin duplicar dimensión dentro de la misma versión/ficha. Vínculos a afirmaciones mediante tabla puente obligatoria. |
| `completitud_afirmaciones` | `evaluacion_id FK`, `afirmacion_id FK`; PK compuesta | `rol TEXT` | Respaldo de la evaluación; controlar que afirmación, campo y ficha correspondan. |
| `derivaciones` | `id UUID PK` | `algoritmo_version TEXT*`, `formula JSONB*`, `resultado JSONB*`, `ejecutada_en TIMESTAMPTZ*` | Cadena reproducible y sin ciclos de cálculo; insumos mediante tabla puente obligatoria. |
| `derivacion_insumos` | `derivacion_id FK`, `afirmacion_id FK`; PK compuesta con rol | `rol TEXT*` | Cada insumo refiere a la afirmación/version exacta usada, nunca al último valor mutable. |
| `controles_calidad` | `id UUID PK`, `registro_version_id FK opcional`, `corrida_id FK opcional` | `control_id TEXT*`, `version TEXT`, `resultado TEXT*`, `severidad TEXT*`, `observado JSONB`, `esperado JSONB`, `ejecutado_en TIMESTAMPTZ` | Evidencia por control; métricas visibles de campos pendientes. |
| `incidencias_revision` | `id UUID PK`, `registro_version_id FK opcional`, `source_id FK` | `tipo TEXT*`, `severidad TEXT*`, `descripcion TEXT`, `estado TEXT`, `responsable_rol TEXT`, `decision TEXT`, `fundamento_evidencia_id FK`, `resuelta_en TIMESTAMPTZ` | Conservar candidatos y quién resolvió; una resolución no borra el conflicto histórico. |
| `fuentes_candidatas` | `id UUID PK`, `source_id_origen FK`, `evidencia_id FK` | `url TEXT*`, `relacion TEXT`, `tipo_esperado TEXT`, `estado TEXT`, `prioridad TEXT`, `alias_detectado TEXT` | Descubrimiento acotado y deduplicado, no cola de rastreo ilimitada. |
| `releases` | `id UUID PK` | `creado_en TIMESTAMPTZ`, `estado TEXT`, `manifest_hash TEXT`, `aprobado_por TEXT`, `motivo TEXT` | Publicación y reversión coherentes de proyecciones. |
| `chunks` | `id UUID PK`, `unidad_id FK`, `registro_version_id FK opcional`, `release_id FK` | `texto TEXT*`, `hash TEXT*`, `tipo TEXT*`, `tsvector TSVECTOR`, `modelo_embedding TEXT`, `embedding_ref TEXT` | Cita localizable, versión y filtros antes de recuperar. Duplicados no aumentan autoridad. |
| `eventos_outbox` | `id UUID PK`, `release_id FK opcional` | `tipo TEXT*`, `aggregate_id TEXT*`, `payload JSONB*`, `creado_en TIMESTAMPTZ`, `entregado_en TIMESTAMPTZ`, `intentos INT`, `idempotency_key TEXT UNIQUE` | Entrega al menos una vez con consumidores idempotentes; cola de fallos. Sin datos sensibles en payload. |
| `auditoria_eventos` | `id UUID PK` | `actor TEXT*`, `accion TEXT*`, `objeto TEXT*`, `objeto_id TEXT*`, `antes_hash/despues_hash TEXT`, `motivo TEXT`, `ocurrido_en TIMESTAMPTZ*` | Append-only; RBAC restringe lectura y escritura. |
| `consultas_auditadas` | `id UUID PK`, `release_id FK` | `intencion TEXT`, `fecha_consulta DATE`, `jurisdiccion_id FK`, `resultado_tipo TEXT`, `evidencias_usadas JSONB`, `reglas_versiones JSONB`, `latencia_ms INT` | Minimizar PII; por defecto no guardar conversación ni datos sensibles. Si hay persistencia, contrato de consentimiento/retención separado. |

## 3. Restricciones que debe implementar el DDL

1. PK/FK y unicidad de identificadores de norma; constraints de tipo del supertipo/subtipo. No FKs a entidades inexistentes ni cruce de documento/unidad/versiones.
2. `CHECK fin >= inicio`, cardinalidades y modalidades mutuamente excluyentes cuando las fechas estén determinadas. Conservar precisión e inclusividad; usar `[inicio,fin_exclusivo)` solo tras normalización trazada.
3. Valores activos aprobados sin solapamientos para `(parametro, territorio, segmento, dimensiones equivalentes)`. Versiones candidatas conflictivas se permiten; quedan fuera de la vista servible. Rangos abiertos solo cuando la fuente respalda el extremo abierto.
4. Reglas de estado: valor informado con evidencia; no aplicabilidad fundada; pendiente con motivo. No prohibir que una fuente no publique un teléfono ni obligar a inventarlo.
5. La misma versión no tiene dos artículos raíz con idéntica ruta; sí puede citar el mismo número dentro de un bloque de sustitución. Secuencia numérica no es PK.
6. Inmutabilidad de bytes, evidencias y versiones publicadas; cambios por nueva versión y evento. Borrado físico fuera del flujo normal y de permisos de API/ingesta.
7. Roles separados: migrador, ingestor, revisor, publicador, lector API, auditor. API sin acceso de escritura ni lectura directa de staging. Si hay multi-tenant, `tenant_id` en tablas privadas, FK compuestas y RLS probado; no agregar multi-tenant por suposición.
8. Índices para identificadores, emisor/jurisdicción/tipo/número/año, beneficio/línea, fecha y estado, intervalo de aplicación, caducidad de frescura, relaciones en ambas direcciones, nombre/localidad de atención y búsqueda textual en español.
9. `v_hechos_servibles(fecha,known_at,capacidad)` se implementa como función/vista parametrizada que evalúa vigencia, frescura, conflicto, autoridad y release. No depender de que un cron elimine registros a tiempo.
10. Eliminaciones en una fuente se tratan como eventos a investigar; no `DELETE` masivo de normas porque una página desapareció.

## 4. AST de reglas y lógica de evaluación

Contrato propuesto, ilustrativo y **sintético**, sin atribuirlo a ningún beneficio real:

```json
{
  "schema_version": "1.0",
  "op": "all",
  "args": [
    {"op": "compare", "field": "edad", "cmp": ">=", "value": 18, "unit": "anios_cumplidos"},
    {"op": "any", "args": [
      {"op": "compare", "field": "ingreso_hogar_mensual_bruto", "cmp": "<=", "parameter": "PARAMETRO_SINTETICO", "factor": "1.50", "unit": "ARS"},
      {"op": "is_true", "field": "excepcion_documentada"}
    ]}
  ]
}
```

Operadores cerrados y versionados: `all`, `any`, `not`, `compare`, `in`, `is_true`. No `eval`, scripts SQL ni código generado dentro de una regla. Literales y parámetros se validan contra el diccionario. Cada hoja lleva evidencia o enlaza a la regla que la contiene. Excepciones y precedencias solo se ejecutan si su alcance está respaldado.

Resultado por condición: `TRUE`, `FALSE`, `UNKNOWN`; `FALSE AND UNKNOWN=FALSE`, `TRUE AND UNKNOWN=UNKNOWN`, `TRUE OR UNKNOWN=TRUE`, `FALSE OR UNKNOWN=UNKNOWN`, `NOT UNKNOWN=UNKNOWN`. `FALSE` evalúa esa condición, no habilita un rechazo administrativo. Resultado por beneficio: `POTENCIALMENTE_APLICABLE`, `REQUIERE_DATOS`, `REQUIERE_REVISION`, `NO_CUMPLE_REGLA_EXPLICITA`. Este último exige evaluar todas las excepciones aplicables, explicitar el alcance y distinguirlo de una decisión del organismo.

## 5. Contrato mínimo de API

| Operación | Entrada | Respuesta obligatoria |
|---|---|---|
| `GET /v1/normas` | Identidad, texto, materia, jurisdicción, paginación | Ids, títulos, autoridad, estado, cobertura de campos y versión. |
| `GET /v1/normas/{id}` | `as_of`, `known_at` opcional | Versiones/citas, siete campos proyectados por beneficio, relaciones, pendientes. |
| `GET /v1/beneficios` | Población, territorio, línea | Beneficios candidatos y cobertura, sin inferir elegibilidad por pertenecer a una categoría. |
| `GET /v1/beneficios/{id}/ficha` | Fecha y jurisdicción | Poblaciones, criterios, excepciones, cuantías, plazos, revocación, trámite, evidencia y abstenciones por campo. |
| `POST /v1/evaluaciones-preliminares` | Hechos mínimos proporcionados por la persona, fecha, beneficio | Resultado preliminar, condiciones cumplidas/no cumplidas/desconocidas, salvaguardas, preguntas faltantes, reglas y citas. No persistir payload por defecto. |
| `GET /v1/valores` | Concepto, fecha, línea, segmento, territorio | Valor/fórmula, unidad, período, insumos, estado y fuente; nunca último valor por MAX(fecha) sin verificar aplicación. |
| `GET /v1/plazos` | Beneficio/trámite, ciclo, convocatoria y fecha | Ventana, tipo de plazo, estado calculado y fechas; “desconocido” cuando faltan datos. |
| `GET /v1/puntos-atencion` | Jurisdicción/localidad/tipo, geolocalización voluntaria | Datos de la misma entidad, canal, horario, frescura; no inventar cercanía si faltan coordenadas válidas. |
| `POST /v1/recuperacion` | Consulta, filtros, fecha, intención | Unidades citables del release autorizado, evidencia, fragmentos y conflictos pertinentes. |
| `GET /v1/cobertura` | Alcance autorizado | Denominadores y pendientes separados de lo validado/publicable. |
| `POST /v1/admin/revisiones/{id}/resolver` | Decisión, fundamento, actor autorizado, versión esperada | Nueva decisión auditada; 409 si cambió la versión. |
| `POST /v1/admin/releases` | Candidatos, política, actor | Release o errores de calidad, outbox atómico. |

Todas las respuestas incluyen `schema_version`, `release_id`, `as_of`, `known_at`, `data_status`, `evidence`, `missing_fields` y `warnings` pertinentes. Errores tipados: `SOURCE_UNAVAILABLE`, `STALE_DATA`, `CONFLICT`, `INSUFFICIENT_EVIDENCE`, `UNKNOWN_IDENTITY`, `UNSUPPORTED_SCOPE`; usar 4xx para solicitudes inválidas/autorización y estados de dominio explícitos para información insuficiente, sin disfrazarla como 500.

El modelo conversacional consume estas operaciones tipadas. No recibe credenciales SQL de escritura ni emite SQL arbitrario. Una afirmación del modelo solo se entrega si conserva las evidencias y estados de los datos usados.

## 6. Diccionario de salida de una ficha

```json
{
  "schema_version": "1.0",
  "norma_id": "UUID",
  "version_id": "UUID",
  "as_of": "2026-09-07",
  "beneficios": [],
  "campos": {
    "poblacion_destinataria": {"estado": "PENDIENTE", "valores": [], "evidencias": []},
    "criterios_aplicabilidad": {"estado": "PENDIENTE", "valores": [], "evidencias": []},
    "plazos": {"estado": "PENDIENTE", "valores": [], "evidencias": []},
    "criterios_revocacion": {"estado": "PENDIENTE", "valores": [], "evidencias": []},
    "interdependencias": {"estado": "PENDIENTE", "valores": [], "evidencias": []},
    "beneficio_otorgado": {"estado": "PENDIENTE", "valores": [], "evidencias": []},
    "no_descartar": {"estado": "PENDIENTE", "valores": [], "evidencias": []}
  },
  "capacidades_publicables": [],
  "missing_fields": [],
  "evidence": [],
  "release_id": null,
  "data_status": "NO_PUBLICABLE"
}
```

Ejemplo de contrato vacío intencional: estos marcadores no son datos de producción. Para normas sin beneficio directo, evaluar aplicabilidad al objeto de la norma y declarar los campos del beneficio no aplicables con fundamento, sin convertir derechos generales en prestaciones monetarias ficticias.
