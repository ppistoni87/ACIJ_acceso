# Instrucción de ejecución para Claude Code

Versión 1.1 · 12 de septiembre de 2026 · 38 historias de producto; entregas E1 y E2.

Implementá y llevá a operación el alcance de `Plan_Integral_ACIJ.md`, usando `Backlog_Producto_ACIJ.json` y preservando el backlog de fuentes que ya existe en el repositorio. El proyecto es `https://github.com/ppistoni87/ACIJ_acceso`; línea de base inspeccionada: `1c19c62`, rama `claude/backend-normativo-user-stories-41z94i`.

1. Leé instrucciones del repositorio, estado de Git, esquema, pruebas y catálogo real. Verificá si están disponibles los cambios iniciados en `codex/producto-conversacional-persistente`: al cerrar este plan estaban locales, sin commit ni validación integral; no supongas que existen en GitHub ni los des por aprobados.
2. Descubrí los agentes ya instalados y asigná por capacidades: integración, datos SQL, ingesta, curación, backend, RAG, frontend, plataforma y QA. No inventes nombres. Usá paralelismo para trabajo independiente, con propiedad de archivos y un único integrador para migraciones y contratos.
3. Empezá por P-001, P-018 y los artefactos de P-002. Reutilizá FastAPI, SQLAlchemy y Alembic. No construyas otro backend sin justificar la migración. Preservá las 83 historias individuales de fuentes y conciliá cualquier ampliación.
4. Prepará cambios de base en una rama aislada de Neon. Usá conexión directa para migraciones y operaciones de sesión, y pool para tráfico de aplicación. Guardá secretos en el gestor del entorno, no en Git, el front, logs o el informe. No uses `corrida_limpia.sh` sobre una base compartida o productiva: el bootstrap operativo debe ser no destructivo.
5. Avanzá por G0-G7 y actualizá una matriz de estado con evidencia: NO_INICIADA, EN_CURSO, BLOQUEADA, LISTA_PARA_ACEPTACION y ACEPTADA. Una historia sólo queda ACEPTADA cuando se cumplen todos sus criterios en el entorno requerido. No cierres por cantidad de archivos o pruebas unitarias.
6. Para cada fuente ejecutá adquisición, validación, curación y conciliación. No inventes URLs, montos, fechas, criterios o relaciones. No eludas bloqueos. Preservá versiones, anexos y dependencias; separá referencia, modificación y vigencia.
7. El chat debe usar recuperación y generación reales, y cálculo tipado para condiciones, importes y plazos. Mostrá citas verificables y abstención útil. No apruebes automáticamente reglas CANDIDATE ni sustituyas la firma jurídica de HU-036.
8. Ejecutá CI sobre PostgreSQL real, pruebas de contratos y permisos, evaluación RAG, E2E, carga, persistencia, monitoreo programado, rollback y restauración de base más objetos. Reportá pruebas omitidas como omitidas y proveedores no configurados como pendientes.
9. Publicá el servicio en el destino autorizado con URLs estables y evidencia de cada gate. Prepará todo lo reversible y revisable antes de pedir una decisión o autorización adicional que sea realmente necesaria. Los recursos pagos, región y responsables deben respetar las decisiones vigentes; no los inventes.
10. Entregá commit y PR integrados, URLs, proyecto/ramas de base sin credenciales, versión de esquema, conteos reales, capacidades habilitadas, acta jurídica, resultados de calidad y RAG, pruebas operativas y runbook. Si persiste un bloqueo, indicá acción exacta, evidencia, responsable, impacto y próximo paso; continuá con lo que pueda completarse.

El objetivo es un servicio completo y operable dentro del alcance acordado. El presente documento es un plan, no una afirmación de que esos resultados ya existen.

## Ampliación del chatbot v1.1

Leé las secciones 08 y 09 y el Anexo B del plan. P-025 a P-038 son diferencias de alcance: no reconstruyas la búsqueda, el motor ni el front que ya existen. Reconciliá el estado real antes de aceptar historias. P-023/P-024 cierran E1; P-036/P-038 cierran E2.

- Conservá FastAPI, SQLAlchemy, Alembic, Neon/PostgreSQL, pgvector y el hosting previsto. Añadí LangGraph como módulo de estado y un adaptador de modelos con salidas Pydantic. No migres a la infraestructura de Boti por imitación.
- Evaluá los candidatos actuales indicados en el plan y fijá versiones, límites y política de datos; nunca uses el nombre de un modelo como prueba de calidad o disponibilidad. Rechazos, truncamientos y fallas requieren salida controlada.
- La generación explica las reglas publicadas; los importes, plazos y condiciones se resuelven con herramientas tipadas. No habilites SQL libre ni acciones sobre organismos estatales. Verificá afirmaciones antes de enviarlas o leerlas en voz.
- Priorizá el front web conversacional propio en E1: P-015/P-032 y sección 08.7. Implementá entrada libre, fuentes desplegables, hechos corregibles, próximos pasos y estados de espera, fallo y vencimiento. Reutilizá el front iniciado y separá el acceso administrativo. WhatsApp está excluido por instrucción expresa de Pedro; no crees un conector ni requieras teléfono para consultar.
- Implementá estado mínimo y corregible, borrado por TTL y consentimientos separados. Documentos y audios no habilitan expedientes ni identificación de menores. No persistas el historial por defecto.
- Implementá voz, lectura de documentos y novedades como capacidades E2 dentro del mismo front. Las novedades aparecen al abrir la web; no incluyen SMS, correo ni push. La atención humana debe probar estados y acuses reales; no inventes una guardia, un ticket o una entrega.
- Actualizá la guía de mensajes, los casos de varios turnos, el conjunto multimodal y la matriz de evidencia. Conservá la firma jurídica y el conjunto base; no modifiques esperados para hacer pasar el modelo.
- Guardá en el repositorio el plan, backlog y esta instrucción en una ruta documental acordada. No declares implementada una historia por recibir este paquete; adjuntá PR, pruebas, despliegue y aceptación de la capacidad correspondiente.
