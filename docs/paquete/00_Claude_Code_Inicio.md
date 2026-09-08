# Prompt de inicio para Claude Code

## Instrucción para ejecutar

Actuá como responsable de implementación de un backend normativo para un sistema conversacional de acceso a derechos. Leé este paquete y el repositorio real. Usá los agentes que ya estén disponibles en mi configuración, asignándolos por las capacidades indicadas abajo. No inventes nombres de agentes instalados. Si una capacidad no tiene agente especializado, asumila con el agente general disponible. Respetá las instrucciones aplicables del repositorio y resolvé tareas independientes en paralelo cuando sea posible.

Tu objetivo es construir y **poblar con datos reales** la base SQL, los procesos de ingesta/monitoreo, los controles de calidad y la API definidos. Persistí hasta terminar el alcance ejecutable. No termines después de crear tablas, seeds de ejemplo o un plan. Si una fuente externa impide avanzar, continuá con las demás y documentá el bloqueo exacto, su evidencia, responsable y capacidad afectada. No pidas validaciones genéricas al usuario cuando puedas preparar un resultado concreto para revisión.

## Orden de lectura

1. `README.md`: alcance, conteos y límites del paquete.
2. `01_Especificacion_Backend_Normativo.md`: campos, políticas, historias transversales y gates.
3. `03_Modelo_SQL_y_Contratos.md`: entidades, restricciones, lógica y API.
4. `05_Manifiesto_Fuentes.json`: catálogo de 83 fuentes/recursos con los 67 IDs originales preservados.
5. `02_Historias_por_Fuente.md` y `06_Backlog.json`: tareas y dependencias.
6. `04_Calidad_y_Pruebas.json`: casos de aceptación, expected assertions y preguntas de evaluación.
7. `referencias/Manual_de_ingesta_de_fuentes.pdf`: evidencia técnica histórica y detalles de las fichas. Sus ejemplos no son contratos de producción ni deben copiarse sin validar. Si contradicen esta especificación, registrar la diferencia y usar los controles aquí definidos; no reinterpretar políticas de acceso ni relajar TLS.

## Primeras acciones

- Inspeccioná stack, esquema, migraciones, pruebas, instrucciones y agentes existentes. Reutilizá lo que sirva; no sobrescribas trabajo ajeno ni crees un backend paralelo innecesario.
- Creá una matriz que asigne cada historia a un agente/capacidad, dependencias, archivos que puede editar, estado y evidencia requerida. Un solo integrador administra migraciones y contratos compartidos.
- Ejecutá conciliación del inventario. Quince IDs del anexo no tienen URL concreta en el manual: buscala en el relevamiento original del repo/archivos suministrados, sin inventarla. Si no existe, registrá la carencia. Los seis descartes de las 52 fichas no son seis fuentes activas.
- Implementá migraciones y contratos comunes antes de abrir trabajo por fuente. Usá SQL como verdad de identidad, vigencia, reglas y datos operativos; el índice de recuperación es reconstruible.
- Elegí entorno y versión SQL compatibles con el repo; PostgreSQL es la referencia. Dejá un ADR corto de decisiones rutinarias, sin frenar por preferencias de nombres o librerías.

## Distribución sugerida por capacidades

| Capacidad | Trabajo | Límite de edición |
|---|---|---|
| `orquestacion` | DAG, hitos, integración, cobertura y entrega | Manifiesto de ejecución y coordinación; asigna ownership. |
| `analisis_funcional` | Campos, reglas, población, salvaguardas y decisiones | Contratos funcionales y fixtures revisables; no aprobar semántica sin evidencia. |
| `datos_sql` | Migraciones, constraints, versiones, proyecciones y cálculos | Esquema con integrador único; interfaces acordadas antes de trabajo paralelo. |
| `ingesta` | Adaptadores, capturas, documentos y cargas | Módulos de adaptador y contratos por fuente, sin publicar por cuenta propia. |
| `curacion_juridica` | Identidad, versiones, relaciones y conflictos | Candidatos con fundamento; asuntos ambiguos quedan para revisor de dominio. |
| `monitoreo` | Scheduler, novedades, diff, impacto y outbox | Jobs/eventos; no operar portales transaccionales. |
| `api_backend` | Endpoints y evaluación determinista | API tipada y permisos de lectura, sin SQL arbitrario del modelo. |
| `recuperacion_rag` | Segmentación, índice, filtros y citas | Proyecciones del corpus publicado. |
| `calidad_qa` | Gates, casos, corpus experto y reportes | Fixtures y tests independientes del resultado que se pretende validar. |
| `seguridad_operacion` | RBAC, logs, respaldo y rendimiento | Configuración operativa sin secretos en código. |

Estos son roles funcionales, no nombres de agentes que se presupongan instalados. Un agente puede cubrir varias capacidades. Las tareas que cambian contratos compartidos se secuencian; los adaptadores independientes pueden avanzar en paralelo después de fijar interfaces.

## Reglas de ejecución

1. No hardcodear beneficios, edades, montos, plazos, excepciones ni jerarquías jurídicas dentro del scraper. Capturarlos como datos con fuente, versión y revisión. Los fixtures sí pueden fijar valores esperados de una captura histórica o sintética.
2. Cada campo pedido debe evaluarse. Lo desconocido se marca como tal; no rellenar para llegar al 100%. Una norma sin beneficio directo no se transforma en un programa ficticio.
3. No hacer afirmaciones actuales con montos históricos ni plazos de campañas anteriores. Ausencia de un nuevo tramo no equivale a vencimiento legal. Resolver fecha y fundamento.
4. Separar original/actualizado/consolidado; no aplicar una reforma dos veces. No confundir artículo citado/anidado con artículo raíz. Registrar correspondencias de renumeración.
5. Capturar bytes, URL y fecha antes de extraer. Evidencia a nivel de campo y reglas. Mantener consulta histórica y temporalidad de conocimiento.
6. No enviar formularios, iniciar sesión, aceptar declaraciones juradas, usar claves ajenas, evadir antibot/robots ni desactivar validación TLS. Fuentes bloqueadas mantienen su brecha y pueden resolverse por equivalente público o carga manual trazada.
7. IA puede proponer extracción, nunca inventar dato ni resolver automáticamente un conflicto jurídico. Reglas operativas explícitas solo se autopublican si hay política y gates que lo permitan.
8. No afirmar elegibilidad definitiva, otorgamiento, denegatoria o revocación. El backend hace evaluación preliminar y explica condiciones/excepciones con datos mínimos.
9. El lector conversacional accede únicamente a proyecciones servibles; no staging. Montos, contactos y fechas salen de consultas deterministas, no de mezclar chunks.
10. Web Push no está supuesto. Implementar outbox/eventos y consumidor configurable; no afirmar mensajes enviados si no existe entrega comprobada.

## Hitos de implementación

H1 inventario + SQL + capturas/configuración. H2 normas críticas y dependencias. H3 beneficios, parámetros, montos y plazos. H4 directorios, procedimientos y fuentes restantes. H5 API + conversación + monitores + QA + operación.

En cada hito entregá: cambios realizados, pruebas ejecutadas, datos efectivamente cargados, métricas de cobertura/calidad y pendientes. No ejecutes un rastreo nacional indiscriminado; importá metadatos globales cuando el dataset público lo permita y resolvé texto completo del alcance y dependencias.

## Evidencia final obligatoria

- Migraciones y comandos de instalación/carga que corran en un entorno limpio compatible.
- Catálogo SQL con los 83 IDs del paquete y todas las URLs hijas descubiertas; duplicados/alias conciliados.
- Filas reales de normas/versiones/artículos, siete campos por ficha, beneficios/reglas, plazos, valores, procedimientos y atención donde la fuente lo permita.
- Reporte por fuente y campo: metadata-only, descargado, extraído, validado, publicado, pendiente o bloqueado. No contar fuentes bloqueadas como pobladas.
- Dos corridas de ingesta que demuestren idempotencia y una actualización real/controlada que demuestre diff, impacto y evento.
- Pruebas de integridad, temporalidad, evidencia, no exclusión, API, permisos, recuperación y restauración. Casos críticos sin fallos; mínimo 60 consultas con expected revisado.
- OpenAPI, diccionario, runbook, criterios de datos, decisiones y backlog con estado y evidencia de cierre.

No declares el backend completo si faltan datos críticos. Si existe un bloqueo externo irresoluble, entregá todo lo demás y una lista precisa de lo que hace falta para completar esa capacidad. No vuelvas a pedirme una aprobación general del diseño: presentá el resultado concreto y solo las decisiones de dominio que no puedan resolverse con evidencia.
