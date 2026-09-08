# Estado del backlog

Historias del paquete: **123** (40 transversales + 83 por fuente).

Las transversales se verifican contra el código y las pruebas que las implementan;
las de fuente, contra las filas que dejaron en la base. `bn calidad backlog` falla
si una historia declara evidencia en una ruta que ya no existe.

| Estado | Transversales | Por fuente |
| --- | --- | --- |
| NO_INICIADA | 0 | 9 |
| BLOQUEADA | 0 | 16 |
| EN_CURSO | 5 | 53 |
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
| HU-021 | Cargar RENABAP como padrón versionado | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/importadores/renabap.py`<br>`src/backend_normativo/api/routers/operativo.py`<br>`tests/integracion/test_importador_renabap.py`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`scripts/poblar_corpus.sh`<br>`bn ingesta capturar F39`<br>`bn ingesta descubrir-renabap`<br>`bn ingesta importar-renabap` |
| HU-022 | Validar evidencia y procedencia por campo | calidad_qa | P0 | CERRADA | `src/backend_normativo/db/models/calidad.py`<br>`src/backend_normativo/curacion/campos.py`<br>`tests/integracion/test_campos_y_cobertura.py`<br>`tests/integracion/test_esquema_temporalidad.py` |
| HU-023 | Resolver vigencia y frescura por capacidad | curacion_juridica | P0 | CERRADA | `src/backend_normativo/politicas/vigencia.py`<br>`src/backend_normativo/curacion/vigencia.py`<br>`tests/integracion/test_publicacion.py`<br>`tests/integracion/test_hechos_servibles.py`<br>`bn curacion vigencia`<br>`bn revision resolver-vigencia` |
| HU-024 | Detectar y resolver conflictos de fuentes | curacion_juridica | P0 | CERRADA | `src/backend_normativo/curacion/revision.py`<br>`tests/integracion/test_publicacion.py`<br>`tests/integracion/test_hechos_servibles.py`<br>`bn revision pendientes`<br>`bn revision resolver-vigencia` |
| HU-025 | Publicar atómicamente y gestionar cuarentena | datos_sql | P0 | CERRADA | `src/backend_normativo/publicacion/release.py`<br>`src/backend_normativo/publicacion/gates.py`<br>`tests/integracion/test_publicacion.py`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`bn publicacion estado`<br>`bn publicacion publicar` |
| HU-026 | Monitorear novedades normativas | monitoreo | P0 | EN_CURSO | `src/backend_normativo/monitoreo/novedades.py`<br>`tests/integracion/test_monitoreo.py`<br>`src/backend_normativo/monitoreo/ciclo.py`<br>`tests/integracion/test_ciclo_monitoreo.py`<br>`docs/reportes/ciclo_monitoreo.md`<br>`bn monitoreo ciclo`<br>`bn monitoreo ciclo --en-seco`<br>_Falta: El ciclo está encadenado y corre entero con un comando: planifica según la frecuencia declarada de cada fuente, revalida a las vencidas, compara contra la versión anterior y propaga el impacto a la cola de eventos. Corrió sobre el corpus real y la evidencia está en docs/reportes/ciclo_monitoreo.md; los boletines M01-M04 tienen frecuencia diaria y vuelven a la cola a las veinticuatro horas, verificado en prueba. Lo único que falta es que algo lo dispare: un planificador del sistema o del orquestador llamando `bn monitoreo ciclo` cada hora. Es una decisión de despliegue, no código._ |
| HU-027 | Monitorear datos operativos y cambios semánticos | monitoreo | P0 | CERRADA | `src/backend_normativo/monitoreo/diff.py`<br>`tests/integracion/test_monitoreo.py`<br>`bn monitoreo correr` |
| HU-028 | Propagar impacto y emitir eventos de cambio | monitoreo | P0 | CERRADA | `src/backend_normativo/monitoreo/impacto.py`<br>`src/backend_normativo/monitoreo/outbox.py`<br>`tests/integracion/test_monitoreo.py`<br>`bn monitoreo entregar` |
| HU-029 | Exponer API de consulta estructurada | api_backend | P0 | CERRADA | `src/backend_normativo/api/app.py`<br>`src/backend_normativo/api/contratos.py`<br>`src/backend_normativo/api/routers`<br>`tests/integracion/test_api.py`<br>`bn api servir`<br>`bn api openapi` |
| HU-030 | Evaluar aplicabilidad de manera preliminar | api_backend | P0 | CERRADA | `src/backend_normativo/api/routers/evaluaciones.py`<br>`src/backend_normativo/reglas/beneficio.py`<br>`tests/integracion/test_api.py` |
| HU-031 | Preparar recuperación documental con citas | recuperacion_rag | P0 | CERRADA | `src/backend_normativo/publicacion/release.py`<br>`src/backend_normativo/api/routers/recuperacion.py`<br>`tests/integracion/test_api.py` |
| HU-032 | Responder ante datos faltantes y conflictos | recuperacion_rag | P0 | CERRADA | `src/backend_normativo/api/consultas.py`<br>`src/backend_normativo/api/contratos.py`<br>`tests/integracion/test_api.py`<br>`tests/integracion/test_hechos_servibles.py` |
| HU-033 | Aplicar permisos, minimización y aislamiento | seguridad_operacion | P0 | CERRADA | `src/backend_normativo/migrations/versions/0002_reglas_de_integridad.py`<br>`src/backend_normativo/api/dependencias.py`<br>`tests/integracion/test_api.py`<br>`tests/aceptacion/test_casos_aceptacion.py` |
| HU-034 | Medir calidad y alertar fallos observables | calidad_qa | P0 | CERRADA | `src/backend_normativo/calidad/cobertura.py`<br>`src/backend_normativo/publicacion/gates.py`<br>`tests/integracion/test_campos_y_cobertura.py`<br>`bn calidad cobertura` |
| HU-035 | Poblar el corpus con datos reales y conciliar | orquestacion | P0 | EN_CURSO | `scripts/poblar_corpus.sh`<br>`scripts/corrida_limpia.sh`<br>`src/backend_normativo/ingesta/importadores/infoleg.py`<br>`docs/operacion/poblacion_real.md`<br>`docs/reportes/actualizacion_controlada.md`<br>`docs/reportes/corrida_limpia.md`<br>`docs/curaduria/ley-caba-6935.json`<br>`docs/curaduria/ley-caba-2917.json`<br>`docs/curaduria/ley-nacional-24714-auh.json`<br>`docs/curaduria/ley-nacional-24714-embarazo.json`<br>`docs/curaduria/ley-nacional-24714-asignacion-por-hijo.json`<br>`docs/curaduria/decreto-caba-690-2006.json`<br>`docs/curaduria/ordenanza-caba-43478.json`<br>`src/backend_normativo/curacion/beneficios.py`<br>`bash scripts/poblar_corpus.sh`<br>`bn ingesta importar-infoleg`<br>`bn calidad ensayo-actualizacion`<br>_Falta: La población entera se corre con un comando: `scripts/poblar_corpus.sh` es la única definición del procedimiento y `scripts/corrida_limpia.sh` lo ejercita sobre una base que se crea vacía. Están el catálogo nacional entero (423.718 normas), el padrón RENABAP (6.467 barrios) y los tres directorios. Siete beneficios están curados desde el texto capturado: cuatro porteños —el apoyo habitacional de la Ley 6935, el Régimen de Becas de la Ley 2917, el subsidio para familias en situación de calle del Decreto 690/06 y la beca de comedor de la Ordenanza 43.478— y tres de la Ley nacional 24.714, curados por separado porque son prestaciones distintas con requisitos distintos sobre la misma ley: la Asignación Universal por Hijo y la Asignación por Embarazo del subsistema no contributivo, y la asignación por hijo del contributivo. Son 83 reglas vigentes, 15 poblaciones, 13 plazos y 7 cuantías —seis monetarias y una en especie—, cada pieza atada a su artículo y verificada contra el texto capturado. Falta curar el resto del corpus con texto: el trabajo es de lectura jurídica sobre cada norma, no de más ingesta._ |
| HU-036 | Verificar con corpus experto y casos adversos | calidad_qa | P0 | EN_CURSO | `docs/calidad/trazabilidad_at.json`<br>`docs/calidad/consultas_conversacionales.json`<br>`tests/aceptacion/test_casos_aceptacion.py`<br>`tests/aceptacion/test_conversacional.py`<br>`docs/calidad/trazabilidad_at.md`<br>`docs/calidad/consultas_conversacionales.md`<br>`bn calidad trazabilidad --ejecutar`<br>`bn calidad consultas`<br>_Falta: El conjunto conversacional cumple la gate DQ18 (98 consultas, 59 críticas, todas pasan) y los 80 casos AT se ejecutan y están cubiertos, sin parciales. Falta la revisión experta humana de las respuestas, que es lo que la gate llama «conjunto experto revisado» y ningún automatismo puede firmar._ |
| HU-037 | Asegurar rendimiento y recuperación | seguridad_operacion | P1 | EN_CURSO | `src/backend_normativo/operacion/respaldo.py`<br>`tests/aceptacion/test_respaldo.py`<br>`docs/reportes/restauracion.md`<br>`src/backend_normativo/calidad/rendimiento.py`<br>`tests/aceptacion/test_restauracion_completa.py`<br>`tests/integracion/test_servibles_prefiltro.py`<br>`docs/reportes/rendimiento.md`<br>`bn operacion respaldar`<br>`bn operacion restaurar`<br>`bn calidad rendimiento`<br>_Falta: El respaldo y la restauración están probados de punta a punta con pg_dump y pg_restore sobre bases propias. La latencia está medida sobre el corpus real de 423.718 normas: ninguna consulta pasa de 33 ms en el percentil 95, y la concurrencia se mide con hilos reales disputándose el pool. La medición mostró dónde está el techo: el motor sostiene 1.270 consultas por segundo con dieciséis hilos y la API se queda en 76, así que el límite es el proceso que serializa las respuestas y escalar es agregar procesos. Falta la prueba con el despliegue real —varias instancias, balanceador, red y un generador de carga externo—, que confirma si ese techo por proceso se multiplica como corresponde._ |
| HU-038 | Gestionar carga manual y fuentes bloqueadas | ingesta | P0 | CERRADA | `src/backend_normativo/ingesta/manual.py`<br>`src/backend_normativo/migrations/versions/0003_carga_manual.py`<br>`tests/integracion/test_carga_manual.py`<br>`tests/integracion/test_captura.py`<br>`bn ingesta bloqueadas`<br>`bn ingesta cargar-manual` |
| HU-039 | Entregar documentación y operación reproducible | orquestacion | P0 | EN_CURSO | `docs/operacion/runbook.md`<br>`docs/operacion/diccionario_de_datos.md`<br>`docs/adr`<br>`src/backend_normativo/calidad/backlog.py`<br>`docs/calidad/estado_backlog.json`<br>`scripts/corrida_limpia.sh`<br>`scripts/poblar_corpus.sh`<br>`docs/reportes/corrida_limpia.md`<br>`bn calidad backlog`<br>`bn calidad trazabilidad`<br>`bash scripts/corrida_limpia.sh`<br>_Falta: La documentación y los reportes están y se regeneran solos. La puesta en marcha completa se corre con un comando sobre una base que se crea vacía y se destruye al cerrar (`scripts/corrida_limpia.sh`, que llama a `scripts/poblar_corpus.sh`): migraciones desde cero, las 83 fuentes del catálogo, el recorrido por el mismo planificador que corre en producción, los importadores del catálogo nacional, el padrón y los directorios, y la curación encima de lo capturado. Tres corridas seguidas dieron lo mismo —84 fuentes, 69 capturas, 992 unidades documentales, los 5 beneficios curados y 4.610 incidencias abiertas, en 7 minutos— con el resultado fuente por fuente en `docs/reportes/corrida_limpia.md`. Reconstruir la base de desarrollo desde cero fue lo que hizo aparecer lo que no era reproducible: la planilla del padrón RENABAP y el calendario jurisdiccional de AR-C se habían creado a mano en una sesión y no los creaba ningún comando. Ahora los crea el procedimiento. Las dos fuentes que no entregan cierran con su motivo escrito en la fila de su corrida: F04 por validación TLS que no se relaja y M05 por un 403 que no se contesta rotando identidad. Lo que sigue sin poder demostrarse acá es que ese mismo recorrido dé lo mismo desde otra máquina y otra red: para eso hace falta otra máquina y otra red, y lo que queda es el procedimiento cronometrado para que la diferencia se pueda medir cuando alguien lo corra allá._ |
| HU-040 | Registrar decisiones de dominio y versionar políticas | analisis_funcional | P0 | CERRADA | `docs/adr`<br>`src/backend_normativo/politicas/vigencia.py`<br>`docs/decisiones.md`<br>`tests/integracion/test_publicacion.py` |

## Historias por fuente

Los números salen de la base, no de una declaración.

| HU | Fuente | Estado | URLs | Capturas | Versiones | Unidades | Puntos | Normas | Campos | Publicadas | Detención |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HU-F01 | F01 | EN_CURSO | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F02 | F02 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F03 | F03 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F04 | F04 | BLOQUEADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | https://ladefe.gob.ar/soy-una-nina-nino-o-adolescente/: Fallo de validación TLS: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1016). No se relaja la validación de TLS; hay que buscar una fuente oficial equivalente o hacer carga manual trazada. Responsable: ingesta. |
| HU-F05 | F05 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F06 | F06 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F07 | F07 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F08 | F08 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F09 | F09 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F10 | F10 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F11 | F11 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F12 | F12 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F13 | F13 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F14 | F14 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F15 | F15 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F16 | F16 | EN_CURSO | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F17 | F17 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F18 | F18 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F19 | F19 | EN_CURSO | 1 | 1 | 1 | 32 | 0 | 1 | 7 | 0 | — |
| HU-F20 | F20 | EN_CURSO | 1 | 1 | 1 | 0 | 21 | 0 | 0 | 0 | — |
| HU-F21 | F21 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F22 | F22 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F23 | F23 | EN_CURSO | 1 | 1 | 1 | 97 | 0 | 1 | 7 | 0 | — |
| HU-F24 | F24 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F25 | F25 | EN_CURSO | 1 | 1 | 1 | 33 | 0 | 1 | 7 | 0 | — |
| HU-F26 | F26 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F27 | F27 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F28 | F28 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F31: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F29 | F29 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F27: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F30 | F30 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F31 | F31 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F32 | F32 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F33 | F33 | EN_CURSO | 1 | 6 | 1 | 172 | 0 | 1 | 7 | 0 | — |
| HU-F34 | F34 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F35 | F35 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F36 | F36 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F37 | F37 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F38 | F38 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F39 | F39 | EN_CURSO | 2 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F40 | F40 | EN_CURSO | 1 | 1 | 1 | 132 | 0 | 0 | 0 | 0 | — |
| HU-F41 | F41 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F42 | F42 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F43 | F43 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F44 | F44 | EN_CURSO | 1 | 1 | 2 | 0 | 57 | 0 | 0 | 0 | — |
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
| HU-F56 | F56 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F57 | F57 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F58 | F58 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F59 | F59 | BLOQUEADA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin URL inequívoca conocida. Responsable: ingesta. |
| HU-F60 | F60 | EN_CURSO | 1 | 1 | 1 | 0 | 212 | 0 | 0 | 0 | — |
| HU-F61 | F61 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F62 | F62 | EN_CURSO | 1 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | — |
| HU-F63 | F63 | NO_INICIADA | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Sin capturas: la fuente está en el catálogo y todavía no se recorrió. |
| HU-F64 | F64 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F65 | F65 | ALIAS_REGISTRADO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Alias de F17: el contenido canónico vive allí y no se duplica. La identidad se conserva igual. |
| HU-F66 | F66 | EN_CURSO | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-F67 | F67 | EN_CURSO | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | — |
| HU-D01 | D01 | EN_CURSO | 3 | 16 | 3 | 213 | 0 | 1 | 14 | 0 | — |
| HU-D02 | D02 | EN_CURSO | 2 | 11 | 2 | 5 | 0 | 1 | 7 | 0 | — |
| HU-D03 | D03 | EN_CURSO | 1 | 6 | 1 | 22 | 0 | 1 | 7 | 0 | — |
| HU-D04 | D04 | EN_CURSO | 1 | 6 | 1 | 25 | 0 | 1 | 7 | 0 | — |
| HU-D05 | D05 | EN_CURSO | 1 | 6 | 1 | 29 | 0 | 1 | 7 | 0 | — |
| HU-D06 | D06 | CERRADA | 1 | 6 | 1 | 33 | 0 | 1 | 7 | 1 | — |
| HU-D07 | D07 | EN_CURSO | 1 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | — |
| HU-D08 | D08 | EN_CURSO | 1 | 1 | 1 | 77 | 0 | 0 | 0 | 0 | — |
| HU-D09 | D09 | EN_CURSO | 1 | 1 | 1 | 46 | 0 | 0 | 0 | 0 | — |
| HU-D10 | D10 | EN_CURSO | 1 | 6 | 1 | 70 | 0 | 1 | 7 | 0 | — |
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
