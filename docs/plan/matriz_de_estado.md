# Matriz de estado de las 38 historias

Plan integral v1.1 (12/09/2026) · reconciliada el 12/09/2026 contra el código de
la rama `claude/backend-normativo-user-stories-41z94i`.

El punto 5 de la instrucción de ejecución fija el vocabulario y la regla:
**NO_INICIADA, EN_CURSO, BLOQUEADA, LISTA_PARA_ACEPTACION, ACEPTADA**, y «una
historia sólo queda ACEPTADA cuando se cumplen todos sus criterios en el entorno
requerido». Nada está desplegado en un destino remoto, así que **ninguna historia
figura ACEPTADA**: lo más avanzado que hay es LISTA_PARA_ACEPTACION, que acá
significa que los criterios se cumplen con evidencia reproducible en este
entorno y falta la aceptación formal de quien corresponda.

La línea de base del plan es `1c19c62`. La rama tiene **140 commits** y ese
commit quedó atrás: la reconciliación de abajo se hace contra el código actual,
no contra el que el plan inspeccionó. La suite completa está en **1.370 pruebas
aprobadas y 6 salteadas** sobre PostgreSQL 16 local.

## Cómo leer «EN_CURSO» y «BLOQUEADA»

* **EN_CURSO**: hay código integrado y probado que cubre parte de los criterios,
  y lo que falta se puede escribir.
* **BLOQUEADA**: lo que falta **no se resuelve escribiendo código**. Las causas
  están en `docs/reportes/estado_de_obra.md`: A firma jurídica, B cuenta de
  nube, D límite del contenedor, E qué cuenta como verificar un directorio.

**La causa A se cerró el 12/09 por decisión de producto** (D-130): no va a haber
firma jurídica y se procede sin ella. Lo que quedaba detrás de esa causa no
desapareció, cambió de naturaleza: ahora es trabajo de curación —determinar
vigencias y aprobar afirmaciones— y no la espera de una persona con competencia
jurídica.

## Entrega E1 · P-001 a P-024

| # | Historia | Estado | Qué falta, concretamente |
| --- | --- | --- | --- |
| P-001 | Línea de base reproducible | EN_CURSO | Este documento es parte del criterio. Falta recalibrar esfuerzos y calendario con las 38 historias y fijar el SHA de referencia nuevo. |
| P-002 | PostgreSQL persistente en Neon | BLOQUEADA (B, D) | Proyecto Neon del servicio y medición del presupuesto de conexiones con carga real. |
| P-003 | Esquema y permisos aislados | EN_CURSO | Ninguna prueba corrió contra PostgreSQL 18: el CI usa 16 y Neon sirve 18.6. |
| P-004 | Originales fuera del contenedor | BLOQUEADA (B) | Bucket privado y su política de retención. |
| P-005 | Carga reanudable del corpus | BLOQUEADA (D) | Los tres criterios se cumplen local; nunca corrió contra Neon. |
| P-006 | Adaptadores y fuentes operativas | EN_CURSO | 44 de 85 fuentes sirven. El corpus servible pasó de 1 norma a 7. |
| P-007 | Citas, vigencia y relaciones | LISTA_PARA_ACEPTACION | Las 215 referencias sin resolver son la cola auditable que el criterio pide. |
| P-008 | Siete dimensiones por norma y beneficio | EN_CURSO | Con D-130 deja de esperar una firma. Son 5.397 afirmaciones en 54 versiones, y `bn revision aprobar-campos` se invoca por versión: 54 decisiones, 14 de ellas sobre las normas que sostienen los beneficios. |
| P-009 | Circuito de revisión humana | LISTA_PARA_ACEPTACION | Que alguien lo use, y eso es P-010. |
| P-010 | Expediente jurídico del alcance | EN_CURSO | **Cambió el 12/09: no va a haber firma jurídica y se procede sin ella** (D-130). Las 99 reglas con condición ejecutable quedaron habilitadas con Pedro Pistoni como responsable registrado, un evento por regla. Quedan las 67 sin condición, que el criterio 2 manda clasificar entre formalizables, informativas y sin evidencia. |
| P-011 | Cortes completos y reversibles | LISTA_PARA_ACEPTACION | Ejercitado sobre datos reales, y el ejercicio encontró que la herencia sólo alcanzaba a los fragmentos: publicar el dato operativo dejó de servir los 15 beneficios con el informe en verde. Se revirtió, se arregló con una tabla de membresía y se republicó (`0fd34d45`). La publicación ahora avisa qué deja de servir (D-127, D-142). Reversible probado: revertir un corte no apaga lo que heredó del anterior. |
| P-012 | Recuperación híbrida trazable | EN_CURSO | Recall@5 híbrido 74,1 % contra un umbral de 90 %. |
| P-013 | Respuestas con citas y abstención | EN_CURSO | Tres modos, cuatro validadores y abstención tipada; sin proveedor de modelo configurado sólo se sirve extracto (causa B). |
| P-014 | Condiciones y datos con lógica tipada | EN_CURSO | **Contesta.** Con el corte `180ae01f` hay 15 beneficios publicados y 93 reglas ejecutables sirviendo. La evaluación devuelve cumple / no cumple / desconocido con el texto literal y la pregunta que falta. Los nueve valores de parámetro ya se sirven con fecha de verificación tomada de su captura (D-141). |
| P-015 | Front conversacional | EN_CURSO | Construido y probado con 59 casos E2E en Chromium. Los 1.842 lugares de atención ya llegan a la pantalla, con la fecha de su captura y el aviso de confirmar antes de ir (D-141). Faltan URL de staging (B) y revisión manual de accesibilidad con personas. |
| P-016 | Backoffice de datos y revisión | LISTA_PARA_ACEPTACION | Nada del criterio. |
| P-017 | Identidad, privacidad y protección | EN_CURSO | Criterios 1 y 2 cerrados. Falta proveedor de identidad y el modelo de amenazas escrito. |
| P-018 | Integración continua obligatoria | EN_CURSO | Protección de rama: necesita permisos de administración del repositorio. |
| P-019 | Desplegar revisión y producción | BLOQUEADA (B) | Sondas listas; no hay destino. |
| P-020 | Monitoreo y entrega de eventos programados | BLOQUEADA (B) | Scheduler en la nube. |
| P-021 | Salud, calidad, costos y nivel de servicio | EN_CURSO | Traza por consulta, tablero y límites medidos. Tokens y costo no se registran porque no hay proveedor. |
| P-022 | Respaldo y restauración | EN_CURSO | Retención de Neon sin decidir; RPO/RTO no medidos contra el plan contratado. |
| P-023 | Recorrido completo con pruebas independientes | NO_INICIADA | Depende de nueve historias. Faltan 52 consultas para llegar a las 150. |
| P-024 | Piloto, traspaso y cierre de E1 | NO_INICIADA | Depende de P-023. |

## Entrega E1 · ampliación P-025 a P-032, P-037

| # | Historia | Estado | Qué hay y qué falta |
| --- | --- | --- | --- |
| P-025 | Conversación y memoria mínima | LISTA_PARA_ACEPTACION | Estado mínimo con hechos, procedencia y `rehusado`, corrección que sube versión, TTL de 30 min / 2 h, rutas y purga (D-134). El turno como grafo de LangGraph, que puede parar a preguntar (D-135). Y el frente lo usa: pregunta con las palabras de la norma, guarda lo confirmado y lo deja corregir (D-136, D-137). Lo que no se puede preguntar se declara, no se calla. |
| P-026 | Desambiguar beneficios y reordenar evidencia | EN_CURSO | La búsqueda híbrida existe y está medida, con conjunto congelado. Faltan las fichas comparativas por beneficio y el reranker acotado, que sólo se aprueban con mejora demostrada. |
| P-027 | Adaptador de modelos actualizado | EN_CURSO | Hay adaptador por variables de entorno (`BN_MODELO_*`) con `httpx`, sin SDK. Faltan registro de modelo/versión/región/límites/costo medido, salida validada por Pydantic y ensayo de reversión. |
| P-028 | Verificar cada respuesta antes de mostrarla | EN_CURSO | Los validadores comprueban que cada cita exista y pertenezca al corte, y el modo se declara. Falta lo caro: `evidence_ids` por afirmación, criticidad, verificación de respaldo semántico y retención de la afirmación afectada en vez de la respuesta entera. |
| P-029 | Limpiar y versionar el lenguaje conversacional | EN_CURSO | La humanización está hecha y documentada en las decisiones. Falta el catálogo versionado: ID, situación de uso, texto anterior, texto corregido, variables, responsable y fecha. |
| P-030 | Orientar desde situaciones y armar próximos pasos | EN_CURSO | Criterios 1 y 2 cerrados: las situaciones salen del corte y las elige la persona —no se infieren— con jurisdicción, norma de origen y el aviso de que la lista no es completa (D-138); y cada bloqueo viaja con la excepción que la norma prevé para levantarlo, distinguiendo «no tengo cargada ninguna» de «la ley no prevé ninguna» (D-139). Criterio 3 a medias: los pasos que dependen de la conversación y de la norma ya salen, el canal dice cuándo se verificó y el resumen descargable se arma en el navegador (D-140); faltan los pasos que pide el organismo, que son datos —los seis trámites siguen en CANDIDATE y sin beneficio asociado—. |
| P-031 | Derivar con contexto a atención humana | EN_CURSO | Desde el 12/09 la persona puede pedir hablar con alguien y queda contado (D-125). No hay cola, ni acuse, ni directorio con fecha de verificación: hoy la pantalla dice con todas las letras que no puede comunicar a nadie. |
| P-032 | Front web conversacional de ACIJ | EN_CURSO | «Revisar lo que me contaste» con corrección de hechos, estado de vencimiento de sesión y elección de programa (D-137); orientación por situación, vías de subsanación, próximos pasos y resumen descargable (D-138 a D-140). Falta: control «Ver fuentes» plegable por respuesta y el flujo HTTP/SSE con eventos tipados. |
| P-037 | Memoria, datos y consentimientos | EN_CURSO | Criterio 1 cerrado de las dos puntas: la sesión expira a los 30 minutos de inactividad y vive dos horas como máximo, con purga propia (D-134), y la pantalla lo dice —qué guarda, por cuánto y cómo se borra— con una prueba que falla si vuelve la promesa vieja (D-137). Faltan la recuperación entre sesiones y los consentimientos independientes. |

## Entrega E2 · P-033 a P-036, P-038

| # | Historia | Estado | Nota |
| --- | --- | --- | --- |
| P-033 | Audios y lectura en voz | NO_INICIADA | Depende de P-032 y P-037. |
| P-034 | Leer documentos sin crear expediente | NO_INICIADA | Depende de P-004 (bloqueada), P-032 y P-037. |
| P-035 | Novedades voluntarias en el front | NO_INICIADA | Depende de P-020 (bloqueada), P-032 y P-037. |
| P-036 | Evaluar front, diálogo, voz y adjuntos | NO_INICIADA | 270 casos mínimos y piloto con 12 participantes. |
| P-038 | Cierre del despliegue de la ampliación | NO_INICIADA | Depende de P-024 y P-036. |

## Recuento

| Estado | E1 base | Ampliación E1 | E2 | Total |
| --- | --- | --- | --- | --- |
| LISTA_PARA_ACEPTACION | 4 | 0 | 0 | 4 |
| EN_CURSO | 13 | 7 | 0 | 20 |
| BLOQUEADA | 5 | 0 | 0 | 5 |
| NO_INICIADA | 2 | 2 | 5 | 9 |
| ACEPTADA | 0 | 0 | 0 | 0 |

## Brechas de §02 del plan, contra el código de hoy

El plan v1.1 nombra seis brechas que «ya deben formar parte de la
implementación». Estado real:

| Brecha del plan | Estado |
| --- | --- |
| Eliminar supuestos de localhost del bootstrap | Pendiente. |
| Impedir que las pruebas de base se aprueben por omisión | Hecho: sin PostgreSQL la suite falla, y saltearlas exige `BN_PRUEBAS_SIN_BASE=1`, que deja el salteo dicho. |
| Completar el tratamiento de reglas sin condición | Pendiente, causa A. |
| Hacer coherente aprobar con la marca de revisión | Hecho en parte: la publicación exige `verificado_en` y la cuarentena lo dice (D-128). Queda que la curación de directorios la escriba, que es la decisión E. |
| Verificar permisos reales de las funciones de consulta | Hecho: `tests/integracion/test_permisos_de_la_api.py` corre cada ruta pública con `SET ROLE bn_lector_api`. |
| Probar que un nuevo release conserve las versiones publicadas | Hecho: D-127 y `tests/integracion/test_corte_completo.py`. Era también un riesgo declarado en §12. |
