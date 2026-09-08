# Estado del backlog

Historias del paquete: **123** (40 transversales + 83 por fuente).

Las transversales se verifican contra el código y las pruebas que las implementan;
las de fuente, contra las filas que dejaron en la base. `bn calidad backlog` falla
si una historia declara evidencia en una ruta que ya no existe.

| Estado | Transversales | Por fuente |
| --- | --- | --- |
| NO_INICIADA | 0 | 0 |
| BLOQUEADA | 0 | 17 |
| EN_CURSO | 5 | 61 |
| ALIAS_REGISTRADO | 0 | 4 |
| CERRADA | 35 | 1 |

## Historias transversales

| HU | Título | Capacidad | Prioridad | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- |
| HU-001 | Conciliar el alcance y conservar cada fuente | analisis_funcional | P0 | CERRADA | `src/backend_normativo/catalogo/carga.py`<br>`src/backend_normativo/catalogo/reconciliacion.py`<br>`tests/integracion/test_catalogo.py`<br>`src/backend_normativo/catalogo/anclas.py`<br>`tests/integracion/test_anclas.py`<br>`bn catalogo validar`<br>`bn catalogo cargar`<br>`bn catalogo conciliar`<br>`bn catalogo anclas` |
| HU-002 | Construir migraciones y restricciones SQL | datos_sql | P0 | CERRADA | `src/backend_normativo/db/models`<br>`src/backend_normativo/migrations/versions/0001_esquema_inicial.py`<br>`src/backend_normativo/migrations/versions/0002_reglas_de_integridad.py`<br>`tests/integracion/test_esquema_integridad.py`<br>`tests/integracion/test_esquema_temporalidad.py`<br>`tests/integracion/test_esquema_hechos.py`<br>`alembic upgrade head`<br>`alembic check` |
| HU-003 | Versionar configuración y programar fuentes | ingesta | P0 | CERRADA | `src/backend_normativo/catalogo/carga.py`<br>`src/backend_normativo/ingesta/planificador.py`<br>`tests/integracion/test_captura.py`<br>`bn catalogo cargar` |
| HU-004 | Capturar originales inmutables | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/capturador.py`<br>`src/backend_normativo/ingesta/almacen.py`<br>`src/backend_normativo/ingesta/cliente.py`<br>`tests/integracion/test_captura.py`<br>`bn ingesta capturar` |
| HU-005 | Importar datasets públicos con conciliación | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/importadores/infoleg.py`<br>`tests/integracion/test_importador_infoleg.py`<br>`bn ingesta importar-infoleg` |
| HU-006 | Extraer páginas HTML y endpoints públicos | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/adaptadores/html.py`<br>`src/backend_normativo/ingesta/adaptadores/normativa_nacional.py`<br>`src/backend_normativo/ingesta/adaptadores/normativa_ba.py`<br>`src/backend_normativo/ingesta/adaptadores/infoleg_legacy.py`<br>`tests/unit/test_adaptadores.py`<br>`src/backend_normativo/ingesta/adaptadores/pagina_institucional.py`<br>`tests/unit/test_adaptador_pagina.py`<br>`bn ingesta extraer`<br>`bn ingesta descubrir` |
| HU-007 | Extraer PDF y anexos con control de cobertura | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/adaptadores/pdf.py`<br>`tests/unit/test_adaptador_pdf.py`<br>`tests/fixtures/prefijo_boletin_caba.json`<br>`src/backend_normativo/ingesta/adaptadores/fecha_documento.py`<br>`tests/unit/test_fecha_documento.py`<br>`bn ingesta capturar D07 D08 D09 F38 F40 F54 F62 F63`<br>`bn ingesta extraer` |
| HU-008 | Segmentar normativa sin perder jerarquía | curacion_juridica | P0 | CERRADA | `src/backend_normativo/curacion/segmentacion.py`<br>`tests/unit/test_segmentacion.py`<br>`bn ingesta extraer` |
| HU-009 | Resolver identidad y versiones de normas | curacion_juridica | P0 | CERRADA | `src/backend_normativo/curacion/identidad.py`<br>`tests/integracion/test_curacion.py`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`src/backend_normativo/curacion/equivalencias.py`<br>`tests/integracion/test_equivalencias.py`<br>`bn curacion identidad`<br>`bn curacion equivalencias`<br>`bn revision aprobar-equivalencia` |
| HU-010 | Construir relaciones normativas y resolver dependencias | curacion_juridica | P0 | CERRADA | `src/backend_normativo/curacion/citas.py`<br>`src/backend_normativo/curacion/relaciones.py`<br>`tests/unit/test_citas.py`<br>`tests/integracion/test_curacion.py`<br>`src/backend_normativo/curacion/anexos.py`<br>`tests/integracion/test_anexos.py`<br>`bn curacion relaciones`<br>`bn curacion anexos`<br>`bn curacion vincular-anexo` |
| HU-011 | Registrar todos los beneficios y sus bases | analisis_funcional | P0 | CERRADA | `src/backend_normativo/curacion/beneficios.py`<br>`docs/curaduria/ley-caba-6935.json`<br>`tests/integracion/test_curacion_beneficios.py`<br>`src/backend_normativo/db/models/beneficios.py`<br>`bn curacion beneficios` |
| HU-012 | Completar los siete campos con estados explícitos | analisis_funcional | P0 | CERRADA | `src/backend_normativo/curacion/campos.py`<br>`src/backend_normativo/db/vocabularios.py`<br>`tests/integracion/test_campos_y_cobertura.py`<br>`bn curacion campos`<br>`bn revision aprobar-campos` |
| HU-013 | Modelar población y roles del beneficio | analisis_funcional | P0 | CERRADA | `src/backend_normativo/curacion/beneficios.py`<br>`docs/curaduria/ley-caba-6935.json`<br>`tests/integracion/test_curacion_beneficios.py`<br>`src/backend_normativo/reglas/ast.py`<br>`tests/aceptacion/test_casos_reglas.py`<br>`bn curacion beneficios` |
| HU-014 | Representar criterios lógicos y parámetros | datos_sql | P0 | CERRADA | `src/backend_normativo/reglas/ast.py`<br>`src/backend_normativo/reglas/evaluacion.py`<br>`src/backend_normativo/reglas/beneficio.py`<br>`tests/unit/test_reglas.py` |
| HU-015 | Preservar excepciones y salvaguardas de no exclusión | analisis_funcional | P0 | CERRADA | `src/backend_normativo/reglas/beneficio.py`<br>`tests/unit/test_reglas.py` |
| HU-016 | Representar y calcular plazos distintos | datos_sql | P0 | CERRADA | `src/backend_normativo/plazos/computo.py`<br>`src/backend_normativo/plazos/calendarios.py`<br>`tests/unit/test_computo_plazos.py`<br>`tests/integracion/test_calendarios.py`<br>`tests/integracion/test_esquema_hechos.py`<br>`bn plazos calendario 2026`<br>`bn plazos calcular` |
| HU-017 | Separar suspensión, cese y revocación | analisis_funcional | P0 | CERRADA | `src/backend_normativo/curacion/beneficios.py`<br>`docs/curaduria/ley-caba-6935.json`<br>`tests/integracion/test_curacion_beneficios.py`<br>`src/backend_normativo/reglas/beneficio.py`<br>`bn curacion beneficios` |
| HU-018 | Modelar cuantías y fórmulas reproducibles | datos_sql | P0 | CERRADA | `src/backend_normativo/db/models/hechos.py`<br>`src/backend_normativo/reglas/evaluacion.py`<br>`tests/integracion/test_esquema_hechos.py`<br>`tests/unit/test_reglas.py` |
| HU-019 | Cargar trámites y documentos exigidos | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/adaptadores/tramite_argentina.py`<br>`src/backend_normativo/curacion/tramites.py`<br>`tests/unit/test_adaptador_tramite.py`<br>`tests/integracion/test_tramites.py`<br>`src/backend_normativo/ingesta/adaptadores/pasos_pdf.py`<br>`tests/unit/test_pasos_pdf.py`<br>`bn ingesta extraer`<br>`bn curacion tramites` |
| HU-020 | Cargar directorios sin mezclar entidades | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/importadores/directorios.py`<br>`tests/integracion/test_importador_directorios.py`<br>`src/backend_normativo/ingesta/importadores/dpn.py`<br>`tests/integracion/test_importador_dpn.py`<br>`bn ingesta capturar F20 F60 F44`<br>`bn ingesta importar-directorio`<br>`bn ingesta importar-dpn` |
| HU-021 | Cargar RENABAP como padrón versionado | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/importadores/renabap.py`<br>`src/backend_normativo/api/routers/operativo.py`<br>`tests/integracion/test_importador_renabap.py`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`bn ingesta capturar F39`<br>`bn ingesta importar-renabap` |
| HU-022 | Validar evidencia y procedencia por campo | calidad_qa | P0 | CERRADA | `src/backend_normativo/db/models/calidad.py`<br>`src/backend_normativo/curacion/campos.py`<br>`tests/integracion/test_campos_y_cobertura.py`<br>`tests/integracion/test_esquema_temporalidad.py` |
| HU-023 | Resolver vigencia y frescura por capacidad | curacion_juridica | P0 | CERRADA | `src/backend_normativo/politicas/vigencia.py`<br>`src/backend_normativo/curacion/vigencia.py`<br>`tests/integracion/test_publicacion.py`<br>`tests/integracion/test_hechos_servibles.py`<br>`bn curacion vigencia`<br>`bn revision resolver-vigencia` |
| HU-024 | Detectar y resolver conflictos de fuentes | curacion_juridica | P0 | CERRADA | `src/backend_normativo/curacion/revision.py`<br>`tests/integracion/test_publicacion.py`<br>`tests/integracion/test_hechos_servibles.py`<br>`bn revision pendientes`<br>`bn revision resolver-vigencia` |
| HU-025 | Publicar atómicamente y gestionar cuarentena | datos_sql | P0 | CERRADA | `src/backend_normativo/publicacion/release.py`<br>`src/backend_normativo/publicacion/gates.py`<br>`tests/integracion/test_publicacion.py`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`bn publicacion estado`<br>`bn publicacion publicar` |
| HU-026 | Monitorear novedades normativas | monitoreo | P0 | EN_CURSO | `src/backend_normativo/monitoreo/novedades.py`<br>`tests/integracion/test_monitoreo.py`<br>_Falta: El monitor corre sobre las fuentes capturadas y el ensayo de actualización ejercita diff, impacto y evento de punta a punta. Los boletines oficiales (M01-M04) están capturados pero todavía no en un ciclo periódico: eso necesita un planificador corriendo, no más código._ |
| HU-027 | Monitorear datos operativos y cambios semánticos | monitoreo | P0 | CERRADA | `src/backend_normativo/monitoreo/diff.py`<br>`tests/integracion/test_monitoreo.py`<br>`bn monitoreo correr` |
| HU-028 | Propagar impacto y emitir eventos de cambio | monitoreo | P0 | CERRADA | `src/backend_normativo/monitoreo/impacto.py`<br>`src/backend_normativo/monitoreo/outbox.py`<br>`tests/integracion/test_monitoreo.py`<br>`bn monitoreo entregar` |
| HU-029 | Exponer API de consulta estructurada | api_backend | P0 | CERRADA | `src/backend_normativo/api/app.py`<br>`src/backend_normativo/api/contratos.py`<br>`src/backend_normativo/api/routers`<br>`tests/integracion/test_api.py`<br>`bn api servir`<br>`bn api openapi` |
| HU-030 | Evaluar aplicabilidad de manera preliminar | api_backend | P0 | CERRADA | `src/backend_normativo/api/routers/evaluaciones.py`<br>`src/backend_normativo/reglas/beneficio.py`<br>`tests/integracion/test_api.py` |
| HU-031 | Preparar recuperación documental con citas | recuperacion_rag | P0 | CERRADA | `src/backend_normativo/publicacion/release.py`<br>`src/backend_normativo/api/routers/recuperacion.py`<br>`tests/integracion/test_api.py` |
| HU-032 | Responder ante datos faltantes y conflictos | recuperacion_rag | P0 | CERRADA | `src/backend_normativo/api/consultas.py`<br>`src/backend_normativo/api/contratos.py`<br>`tests/integracion/test_api.py`<br>`tests/integracion/test_hechos_servibles.py` |
| HU-033 | Aplicar permisos, minimización y aislamiento | seguridad_operacion | P0 | CERRADA | `src/backend_normativo/migrations/versions/0002_reglas_de_integridad.py`<br>`src/backend_normativo/api/dependencias.py`<br>`tests/integracion/test_api.py`<br>`tests/aceptacion/test_casos_aceptacion.py` |
| HU-034 | Medir calidad y alertar fallos observables | calidad_qa | P0 | CERRADA | `src/backend_normativo/calidad/cobertura.py`<br>`src/backend_normativo/publicacion/gates.py`<br>`tests/integracion/test_campos_y_cobertura.py`<br>`bn calidad cobertura` |
| HU-035 | Poblar el corpus con datos reales y conciliar | orquestacion | P0 | EN_CURSO | `scripts/poblar_corpus.sh`<br>`src/backend_normativo/ingesta/importadores/infoleg.py`<br>`docs/operacion/poblacion_real.md`<br>`docs/reportes/actualizacion_controlada.md`<br>`bn ingesta importar-infoleg`<br>`bn calidad ensayo-actualizacion`<br>_Falta: El catálogo nacional está importado entero (423.718 normas), el padrón RENABAP y dos directorios abiertos están cargados, las 83 fuentes fueron recorridas y 31 páginas institucionales, 8 PDF y 2 fichas de trámite están extraídos. Falta que las fuentes capturadas y extraídas se conviertan en beneficios con reglas: eso depende de curación jurídica, no de más ingesta._ |
| HU-036 | Verificar con corpus experto y casos adversos | calidad_qa | P0 | EN_CURSO | `docs/calidad/trazabilidad_at.json`<br>`docs/calidad/consultas_conversacionales.json`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`tests/aceptacion/test_conversacional.py`<br>`docs/calidad/trazabilidad_at.md`<br>`docs/calidad/consultas_conversacionales.md`<br>`bn calidad trazabilidad --ejecutar`<br>`bn calidad consultas`<br>_Falta: El conjunto conversacional cumple la gate DQ18 (98 consultas, 59 críticas, todas pasan) y los 80 casos AT se ejecutan y están cubiertos, sin parciales. Falta la revisión experta humana de las respuestas, que es lo que la gate llama «conjunto experto revisado» y ningún automatismo puede firmar._ |
| HU-037 | Asegurar rendimiento y recuperación | seguridad_operacion | P1 | EN_CURSO | `src/backend_normativo/operacion/respaldo.py`<br>`tests/aceptacion/test_respaldo.py`<br>`docs/reportes/restauracion.md`<br>`src/backend_normativo/calidad/rendimiento.py`<br>`tests/aceptacion/test_restauracion_completa.py`<br>`tests/integracion/test_servibles_prefiltro.py`<br>`docs/reportes/rendimiento.md`<br>`bn operacion respaldar`<br>`bn operacion restaurar`<br>`bn calidad rendimiento`<br>_Falta: El respaldo y la restauración están probados de punta a punta: pg_dump de una base con datos confirmados y pg_restore en otra que empieza vacía, verificando sobre la restaurada las 83 fuentes, el hash de la captura, la integridad y que los triggers de inmutabilidad sigan ahí. La latencia está medida sobre el corpus real de 423.718 normas y ninguna consulta pasa de 30 ms en el percentil 95. Falta la prueba de concurrencia: cuántas consultas por segundo resiste el despliegue real, que necesita el entorno de producción y generadores de carga, no la máquina de desarrollo._ |
| HU-038 | Gestionar carga manual y fuentes bloqueadas | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/manual.py`<br>`src/backend_normativo/migrations/versions/0003_carga_manual.py`<br>`tests/integracion/test_carga_manual.py`<br>`tests/integracion/test_captura.py`<br>`bn ingesta bloqueadas`<br>`bn ingesta cargar-manual` |
| HU-039 | Entregar documentación y operación reproducible | orquestacion | P0 | EN_CURSO | `docs/operacion/runbook.md`<br>`docs/operacion/diccionario_de_datos.md`<br>`docs/adr`<br>`src/backend_normativo/calidad/backlog.py`<br>`docs/calidad/estado_backlog.json`<br>`bn calidad backlog`<br>`bn calidad trazabilidad`<br>_Falta: La documentación y los reportes están y se regeneran solos; `bn calidad ensayo-actualizacion`, `bn operacion restaurar` y las pruebas de restauración levantan bases desde cero en cada corrida, con lo que la reproducibilidad de las migraciones queda probada. Falta el ciclo completo de población en una máquina distinta de la de desarrollo: lo que no se puede demostrar acá es que las 83 fuentes se recorran igual desde otra red._ |
| HU-040 | Registrar decisiones de dominio y versionar políticas | analisis_funcional | P0 | CERRADA | `docs/adr`<br>`src/backend_normativo/politicas/vigencia.py`<br>`docs/decisiones.md`<br>`tests/integracion/test_publicacion.py` |

## Historias por fuente

Los números salen de la base, no de una declaración.

| HU | Fuente | Estado | URLs | Capturas | Versiones | Unidades | Puntos | Normas | Campos | Publicadas | Detención |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HU-F01 | F01 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F02 | F02 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F03 | F03 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F04 | F04 | BLOQUEADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | https://ladefe.gob.ar/soy-una-nina-nino-o-adolescente/: Fallo de validación TLS: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016). No se relaja la validación de TLS; hay que buscar una fuente oficial equivalente o hacer carga manual trazada. Responsable: ingesta. |
| HU-F05 | F05 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F06 | F06 | BLOQUEADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | https://buenosaires.gob.ar/gcaba_historico/node/86736: HTTP 404. El recurso ya no está en esa dirección; hay que recuperar la identidad de la fuente o registrarla como retirada. Responsable: ingesta. |
| HU-F07 | F07 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F08 | F08 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F09 | F09 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F10 | F10 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F11 | F11 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F12 | F12 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F13 | F13 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F14 | F14 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F15 | F15 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F16 | F16 | EN_CURSO | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F17 | F17 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F18 | F18 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F19 | F19 | EN_CURSO | 1 | 1 | 1 | 34 | 0 | 1 | 7 | 0 | — |
| HU-F20 | F20 | EN_CURSO | 2 | 3 | 1 | 0 | 21 | 0 | 0 | 0 | — |
| HU-F21 | F21 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F22 | F22 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F23 | F23 | EN_CURSO | 1 | 1 | 1 | 104 | 0 | 1 | 7 | 0 | — |
| HU-F24 | F24 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F25 | F25 | EN_CURSO | 1 | 1 | 1 | 33 | 0 | 1 | 7 | 0 | — |
| HU-F26 | F26 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F27 | F27 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F28 | F28 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F31: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F29 | F29 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F27: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F30 | F30 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F31 | F31 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F32 | F32 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F33 | F33 | EN_CURSO | 1 | 2 | 1 | 172 | 0 | 1 | 7 | 0 | — |
| HU-F34 | F34 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F35 | F35 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F36 | F36 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F37 | F37 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F38 | F38 | EN_CURSO | 1 | 1 | 1 | 180 | 0 | 0 | 0 | 0 | — |
| HU-F39 | F39 | EN_CURSO | 2 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F40 | F40 | EN_CURSO | 1 | 1 | 1 | 228 | 0 | 0 | 0 | 0 | — |
| HU-F41 | F41 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F42 | F42 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F43 | F43 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F44 | F44 | EN_CURSO | 3 | 4 | 4 | 0 | 78 | 0 | 0 | 0 | — |
| HU-F45 | F45 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F46 | F46 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F47 | F47 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F48 | F48 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F49 | F49 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F50 | F50 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F51 | F51 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F52 | F52 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F53 | F53 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F54 | F54 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F55 | F55 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F24: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F56 | F56 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F57 | F57 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F58 | F58 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F59 | F59 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F60 | F60 | EN_CURSO | 1 | 1 | 1 | 0 | 212 | 0 | 0 | 0 | — |
| HU-F61 | F61 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F62 | F62 | EN_CURSO | 1 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | — |
| HU-F63 | F63 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F64 | F64 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F65 | F65 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F17: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F66 | F66 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F67 | F67 | EN_CURSO | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-D01 | D01 | EN_CURSO | 3 | 4 | 3 | 213 | 0 | 1 | 14 | 0 | — |
| HU-D02 | D02 | EN_CURSO | 2 | 3 | 2 | 5 | 0 | 1 | 7 | 0 | — |
| HU-D03 | D03 | EN_CURSO | 1 | 2 | 1 | 38 | 0 | 1 | 7 | 0 | — |
| HU-D04 | D04 | EN_CURSO | 1 | 2 | 1 | 34 | 0 | 1 | 7 | 0 | — |
| HU-D05 | D05 | EN_CURSO | 1 | 2 | 1 | 30 | 0 | 1 | 7 | 0 | — |
| HU-D06 | D06 | CERRADA | 1 | 2 | 1 | 98 | 0 | 1 | 7 | 1 | — |
| HU-D07 | D07 | EN_CURSO | 1 | 2 | 1 | 3 | 0 | 0 | 0 | 0 | — |
| HU-D08 | D08 | EN_CURSO | 1 | 2 | 1 | 187 | 0 | 0 | 0 | 0 | — |
| HU-D09 | D09 | EN_CURSO | 1 | 2 | 1 | 111 | 0 | 0 | 0 | 0 | — |
| HU-D10 | D10 | EN_CURSO | 1 | 2 | 1 | 89 | 0 | 1 | 7 | 0 | — |
| HU-M01 | M01 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-M02 | M02 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-M03 | M03 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-M04 | M04 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-M05 | M05 | EN_CURSO | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-M06 | M06 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |

## Cómo leer los estados

- **CERRADA**: la fuente tiene al menos una versión en un release publicado.
- **EN_CURSO**: hay capturas y contenido extraído, pero nada llegó a publicarse.
- **ALIAS_REGISTRADO**: la fuente es un alias; su contenido canónico vive en otra y
  duplicarlo sería contar dos veces la misma norma.
- **BLOQUEADA**: hay un impedimento concreto —acceso restringido o URL inequívoca
  desconocida— con su motivo y su responsable. No es un pendiente de programación.
- **NO_INICIADA**: la fuente está en el catálogo y todavía no se recorrió.

Una fuente importada como metadatos —F01, el catálogo nacional— figura con sus
capturas y sin versiones de documento: no tiene textos segmentados porque no se
descargaron sus 428.380 textos. Sus números están en
`docs/operacion/poblacion_real.md`.
