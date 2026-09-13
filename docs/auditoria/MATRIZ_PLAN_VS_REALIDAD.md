# Matriz plan vs. realidad

Contraste de los IDs originales del plan contra la evidencia recogida el
**13/09/2026** sobre `claude/backend-normativo-user-stories-41z94i` @ `e1aa8c9`.
Complementa —no reemplaza— `docs/plan/matriz_de_estado.md`, que es el documento
del equipo; donde las dos difieren, esta matriz dice por qué y con qué evidencia.

## Versión del plan aplicable y conflictos documentales

* **Aplicable:** `docs/plan/Plan_Integral_ACIJ.md`, **Plan integral v1.1 del
  12/09/2026**, 1.061 líneas, con la ampliación conversacional a **38 historias**
  (`P-001`…`P-038`).
* **Conjunto anterior, vigente y distinto:** el paquete normativo de **123
  historias** (40 transversales `HU-0xx` + 83 por fuente `HU-Fxx`), **670
  criterios** y **80 casos de aceptación** `AT-001`…`AT-080`, con estado propio
  en `bn calidad backlog` y `bn calidad trazabilidad`.
* **Conflicto a declarar:** los dos conjuntos **se solapan y no deben sumarse**.
  Las 38 historias `P-xxx` son el plan de producto conversacional; las 123
  `HU-xxx` son las historias de construcción del corpus normativo que aquéllas
  consumen. Ejemplo: `P-014` (condiciones con lógica tipada) descansa sobre
  `HU-014`, `HU-015` y `HU-018`, que figuran CERRADAS — y aun así `P-014` no
  cumple, porque lo que falta es curaduría de datos, no código.
* **Segundo conflicto:** la línea histórica del 09/09 (`1c19c62`, 53 tablas,
  413 tests) quedó atrás; hoy son 61 tablas y 1.504 pruebas. El plan no fue
  reescrito con esos números.
* **No se reconstruyó ningún plan a partir del código:** la documentación existe
  y se usó tal cual.

## Vocabulario de estado

`pendiente` · `parcial` · `implementado sin verificar` · `verificado` ·
`bloqueado` · `no verificable`.
**Ninguna historia figura `verificado`**: el estado exige comprobar cada criterio
en el entorno que ese criterio pide, y **no existe entorno objetivo** (sin base
persistente provisionada, sin URL pública, sin scheduler). Que el código esté
probado y que la historia esté aceptada son dos cosas distintas, y esta matriz
las mantiene separadas en dos columnas.

---

## A. Plan conversacional — 38 historias (IDs originales `P-xxx`)

| ID | Requisito / criterio | Entrega prevista | Implementación encontrada | Evidencia de integración | Prueba y resultado | Despliegue / aceptación | Estado | Brecha | Acción propuesta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P-001 | Línea de base reproducible | Corrida limpia y matriz de estado | `scripts/corrida_limpia.sh`, `docs/plan/matriz_de_estado.md` | en rama | V-5 suite en verde | sin aceptación | **parcial** | El SHA de referencia sigue siendo `1c19c62`; el recuento de la matriz no cuadra (H-16) | Refijar la línea base en `e1aa8c9` y corregir el recuento |
| P-002 | PostgreSQL persistente | Base gestionada, presupuesto de conexiones medido | — | — | — | — | **bloqueado** | Sin cuenta de nube (causa B) | Provisionar; rotar antes la credencial de R-03 |
| P-003 | Esquema y permisos aislados | Roles y grants por función | `migrations/`, `tests/integracion/test_permisos_de_la_api.py` | en rama | Pruebas de permisos en verde sobre PG16 | nunca contra PG18 | **parcial** | Sin PG18 ni destino | Correr la suite contra la versión del destino |
| P-004 | Originales fuera del contenedor | Bucket privado con retención | `ingesta/almacen.py` (local) | en rama | pruebas locales | — | **bloqueado** | Sin bucket (causa B) | Provisionar y migrar el almacén |
| P-005 | Carga reanudable del corpus | Carga contra base persistente | `bn ingesta …` reanudable | en rama | local, sí | nunca contra destino | **bloqueado** | Depende de P-002 | — |
| P-006 | Adaptadores y fuentes operativas | Fuentes sirviendo | 85 fuentes, 55 accesibles, 313 capturas | en rama y en base | V-9 (AT de ingesta) | — | **parcial** | 41 de 85 fuentes no sirven; CABA rechazada por egreso del entorno | Priorizar fuentes por beneficio del alcance de cierre |
| P-007 | Citas, vigencia y relaciones | Vigencia determinada y citas resueltas | `curacion/`, `docs/revision/dictamen_vigencia.md` | en rama y en base | Ley 24.714 fundada con el texto | — | **parcial** | **H-11** la vigencia no llega a la respuesta; **H-13** referencias sin resolver; 215 referencias en cola | Proyectar vigencia en la cita; resolver referencias del corte |
| P-008 | Siete dimensiones por norma y beneficio | 5.397 afirmaciones aprobadas | `curacion/campos.py` | en rama | — | — | **parcial** | 54 decisiones de aprobación por versión pendientes | Aprobar las 14 que sostienen los beneficios del cierre |
| P-009 | Circuito de revisión humana | Revisar, aprobar, rechazar con registro | `api/routers/admin*`, CLI `bn revision` | en rama | **H-05: 6 pruebas del backoffice se saltean** | nadie lo usó | **implementado sin verificar** | Nadie ejerció el circuito con datos reales | Corpus de prueba con candidatos + una sesión real de revisión |
| P-010 | Expediente jurídico del alcance | Reglas habilitadas con responsable | 99 reglas habilitadas, evento por regla (D-130) | en base | — | — | **parcial** | 67 reglas sin condición sin clasificar; **H-01** depende de esto | Clasificar y formalizar; ver T-01 del plan de cierre |
| P-011 | Cortes completos y reversibles | Publicar y revertir sin perder servicio | `publicacion/release.py`, `release_versiones` (0021) | en base, 6 cortes | Prueba de árbol que prohíbe filtrar por `rv.release_id` | — | **parcial** | **H-09**: una versión PUBLISHED fuera del corte y sin detección | Invariante publicado ≡ servido, con prueba |
| P-012 | Recuperación híbrida trazable | Recall@5 ≥ 90 % | pgvector HNSW + tsvector, conjunto congelado | en rama | **Recall@5 74,1 %** (medición del proyecto) | — | **parcial** | 16 puntos por debajo del umbral propio | Ver T-03 |
| P-013 | Respuestas con citas y abstención | Tres modos, validadores, abstención tipada | `generacion/`, `api/routers/recuperacion.py` | en rama | **H-02**: 54 casos responden donde deben abstenerse | sin proveedor | **parcial** | La abstención existe como tipo y no se dispara | **T-02** (P0) |
| P-014 | Condiciones y datos con lógica tipada | Cumple / no cumple / desconocido | `reglas/evaluacion.py`, `reglas/beneficio.py` | en base, 16 beneficios | **H-01: 0 de 16 alcanzan resultado positivo** | — | **parcial** | La matriz del equipo dice «Contesta»; **la evidencia lo desmiente** | **T-01** (P0) |
| P-015 | Front conversacional | Pantalla usable en móvil y escritorio | `consulta.html` 1.897 líneas | en rama | 59 E2E en Chromium en verde | sin URL | **parcial** | **H-10** etiquetas literales; sin accesibilidad revisada con personas | T-06 y T-09 |
| P-016 | Backoffice de datos y revisión | Revisión y publicación con permisos | rutas `/v1/admin/*` | en rama | **401 en todas sin credencial (correcto)**; H-05 | nadie lo usó | **implementado sin verificar** | Igual que P-009 | T-08 |
| P-017 | Identidad, privacidad y protección | Sesiones aisladas, sin datos personales de más | `conversacion/sesion.py`, CHECK de claves | en base | **C-10 aislamiento comprobado**; V-14 sin secretos | — | **parcial** | Sin proveedor de identidad; modelo de amenazas no escrito | T-10 |
| P-018 | Integración continua obligatoria | CI que impide el verde falso | `.github/workflows/ci.yml` | en rama | **H-03: 8 corridas seguidas en `failure`; pasos 8-11 `skipped`** | — | **parcial** | El CI existe y **está en rojo**: no impide nada hoy | **T-04** (P1), y proteger la rama |
| P-019 | Desplegar revisión y producción | Front y API por HTTPS | sondas listas | en rama | — | — | **bloqueado** | Sin destino (causa B) | Decisión de infraestructura |
| P-020 | Monitoreo y eventos programados | Scheduler y entrega | `monitoreo/`, outbox | en rama | pruebas locales | — | **bloqueado** | Sin scheduler en la nube | — |
| P-021 | Salud, calidad, costos y nivel de servicio | Traza, tablero, límites | `api/observabilidad.py`, `api/limites.py` | en rama | — | — | **parcial** | Tokens y costo sin registrar: no hay proveedor | Depende de T-05 |
| P-022 | Respaldo y restauración | Restauración ensayada | `bn operacion`, AT-074 | en rama | AT-074 cubierto y en verde **en local** | no ensayado contra destino | **parcial** | RPO/RTO no medidos | T-11 |
| P-023 | Recorrido completo con pruebas independientes | 150 consultas y gate | conjunto de 150 ya existe | en rama | **Gate DQ18: 78/150, NO CUMPLE** | — | **pendiente** | Depende de 9 historias | T-12 |
| P-024 | Piloto, traspaso y cierre de E1 | Piloto con personas | — | — | — | — | **pendiente** | Depende de P-023 | T-13 |
| P-025 | Conversación y memoria mínima | Recuerda, corrige, pregunta de a una | `conversacion/sesion.py`, `grafo.py`, `preguntas.py` | en rama y en base | Estado, TTL, corrección y rehúse **comprobados**; **H-06: la pregunta nunca se dispara de punta a punta** | — | **parcial** | La matriz del equipo la da LISTA_PARA_ACEPTACION; el criterio 2 no se cumple en el recorrido real | **T-01b** |
| P-026 | Desambiguar beneficios y reordenar evidencia | Fichas comparativas y reranker | búsqueda híbrida | en rama | **H-07: los candidatos se recalculan por consulta** | — | **parcial** | La conversación no acota la identificación | **T-01b** |
| P-027 | Adaptador de modelos actualizado | Registro de modelo, límites y costo | `generacion/proveedores.py` | en rama | sólo con `ServidorDeMentira` | — | **parcial** (criterios de costo y reversión: **no verificable**) | **R-01** | T-05 |
| P-028 | Verificar cada respuesta antes de mostrarla | `evidence_ids` por afirmación | `generacion/validadores.py` (cita existe y pertenece al corte) | en rama | pruebas unitarias en verde | — | **parcial** | Falta cita por afirmación y respaldo semántico | T-07 |
| P-029 | Lenguaje conversacional versionado | Catálogo con ID, versión y responsable | textos humanizados en el front | en rama | pruebas que fijan frases | — | **parcial** | No hay catálogo versionado | T-09 |
| P-030 | Orientar desde situaciones y próximos pasos | Situaciones del corte, subsanaciones, pasos | `necesidades.py`, `pasos.py`, `Subsanacion` | en rama y en base | criterios 1 y 2 comprobados | — | **parcial** | Criterio 3 a medias: 6 trámites en CANDIDATE sin beneficio | T-08 |
| P-031 | Derivar con contexto a atención humana | Cola, acuse, directorio verificado | sólo la señal «quiere persona» (D-125) | en rama | contada, sin destino | — | **pendiente** | No hay derivación real; hoy la pantalla lo dice con todas las letras | **T-02b** — y agravado por H-02: sin abstención no hay cuándo derivar |
| P-032 | Front web conversacional de ACIJ | Fuentes plegables, SSE tipado | `consulta.html` | en rama | 59 E2E | — | **parcial** | Falta «Ver fuentes» plegable por respuesta y el flujo SSE | T-06 |
| P-033 | Audios y lectura en voz | — | — | — | — | — | **pendiente** | Segunda etapa acordada | fuera del cierre |
| P-034 | Leer documentos sin crear expediente | — | — | — | — | — | **pendiente** | Segunda etapa; depende de P-004 | fuera del cierre |
| P-035 | Novedades voluntarias | — | — | — | — | — | **pendiente** | Segunda etapa; depende de P-020 | fuera del cierre |
| P-036 | Evaluar front, diálogo, voz y adjuntos | 270 casos y piloto de 12 personas | — | — | — | — | **pendiente** | Segunda etapa | fuera del cierre |
| P-037 | Memoria, datos y consentimientos | TTL, purga, consentimientos | TTL 30′/2 h, purga, la pantalla lo dice | en rama y en base | prueba que falla si vuelve la promesa vieja | — | **parcial** | Faltan recuperación entre sesiones y consentimientos independientes | T-10 |
| P-038 | Cierre del despliegue de la ampliación | — | — | — | — | — | **pendiente** | Depende de P-024 y P-036 | fuera del cierre |

### Recuento (38 historias)

| Estado | Cantidad | IDs |
| --- | --- | --- |
| verificado | 0 | — |
| parcial | 23 | P-001, P-003, P-006, P-007, P-008, P-010, P-011, P-012, P-013, P-014, P-015, P-017, P-018, P-021, P-022, P-025, P-026, P-027, P-028, P-029, P-030, P-032, P-037 |
| implementado sin verificar | 2 | P-009, P-016 |
| pendiente | 8 | P-023, P-024, P-031, P-033, P-034, P-035, P-036, P-038 |
| bloqueado | 5 | P-002, P-004, P-005, P-019, P-020 |
| no verificable | 0 | (criterios sueltos de P-027 sí lo son) |

**Diferencias con `docs/plan/matriz_de_estado.md`, y por qué:**

| ID | Estado del equipo | Estado de esta auditoría | Evidencia que lo mueve |
| --- | --- | --- | --- |
| P-014 | EN_CURSO, «**Contesta**. La evaluación devuelve cumple / no cumple / desconocido» | **parcial**, con el defecto P0 | Los 16 beneficios evaluados con todos los campos a favor: **0 positivos** (H-01) |
| P-025 | LISTA_PARA_ACEPTACION | **parcial** | El criterio 2 —preguntar de a una— no ocurre en el recorrido real (H-06) |
| P-011 | LISTA_PARA_ACEPTACION | **parcial** | Una versión PUBLISHED fuera del corte vigente (H-09) |
| P-007 | LISTA_PARA_ACEPTACION | **parcial** | La vigencia determinada no llega a la respuesta (H-11) |
| P-009, P-016 | LISTA_PARA_ACEPTACION | **implementado sin verificar** | 6 pruebas del backoffice se saltean por falta de corpus (H-05) y nadie usó el circuito |
| P-018 | EN_CURSO, «falta protección de rama» | **parcial**, con defecto P1 | El CI lleva 8 corridas en rojo y no ejecuta pruebas (H-03) |

---

## B. Paquete normativo — 123 historias (IDs originales `HU-xxx`)

Estado del propio proyecto (`bn calidad backlog`, ejecutado en esta auditoría):

| Estado | Transversales (40) | Por fuente (83) | Total |
| --- | --- | --- | --- |
| CERRADA | 35 | 7 | **42** |
| EN_CURSO | 3 | 47 | **50** |
| BLOQUEADA | 2 | 16 | **18** |
| ESPERA_CARGA_MANUAL | 0 | 4 | 4 |
| NO_SE_INGESTA | 0 | 5 | 5 |
| ALIAS_REGISTRADO | 0 | 4 | 4 |
| NO_INICIADA | 0 | 0 | **0** |

El comando falla si una historia declara evidencia en una ruta que ya no existe,
así que las rutas citadas existen. **Lo que ese comando no comprueba es que la
capacidad funcione para una persona**: `HU-014`, `HU-015` y `HU-018` figuran
CERRADAS y sostienen a `P-014`, que no cumple. Una historia de construcción
cerrada no implica una historia de producto cumplida.

## C. Casos de aceptación — 80 (IDs originales `AT-xxx`)

`bn calidad trazabilidad`: **80 de 80 CUBIERTOS**, 245 pruebas citadas,
0 parciales, 0 no ejecutados. Las pruebas citadas existen (verificado por
colección) y la suite completa pasa (V-5). **Ninguno está aceptado en el entorno
objetivo**, porque no hay entorno objetivo: la columna de despliegue está vacía
para los 80.

Tres casos merecen una nota, porque su cobertura por prueba convive con un
defecto del sistema real:

| AT | Título | Cubierto por | Realidad medida |
| --- | --- | --- | --- |
| AT-067 | Contenido con instrucciones maliciosas | `test_at067_las_instrucciones_dentro_de_un_documento_se_guardan_como_texto` | Correcto en ingesta. **Sin proveedor de modelo, la parte de generación no se ejerció** (R-01) |
| AT-070 | Índice retrasado | 3 pruebas | Correcto. No cubre H-09 (versión publicada fuera del corte) |
| AT-079 | Evaluación no administrativa | `test_todo_cumplido_da_un_resultado_preliminar_positivo` | **La prueba obtiene un positivo con datos sintéticos; ningún beneficio real puede obtenerlo** (H-01) |

## D. Implementado y **no** previsto en el plan

Trabajo integrado que no responde a ningún ID original y que conviene registrar
para no perderlo ni contarlo dos veces:

| Qué | Dónde | Por qué apareció |
| --- | --- | --- |
| Tabla de membresía de cortes `release_versiones` | `migrations/0021`, `publicacion/release.py` | D-142: publicar un corte dejó de servir 15 beneficios sin un solo error |
| Herencia de versiones entre cortes y reporte «dejó de servir» | `publicacion/release.py` | idem |
| Fechado de publicación desde el portal de normativa nacional | `ingesta/fecha_de_publicacion.py` | D-143: InfoLeg responde 403; 46 normas sin fecha |
| Sellado de `verificado_en` desde la captura, nunca desde `now()` | `curacion/verificacion.py` | D-141 |
| Vías de subsanación en el dictamen (`Subsanacion`) | `reglas/beneficio.py` | D-139: la excepción prevista es muchas veces la vía que queda |
| Necesidades y próximos pasos derivados del corte | `conversacion/necesidades.py`, `pasos.py` | D-138, D-140 |
| Resumen descargable armado en el navegador | `consulta.html` | D-140: no sale de la máquina |
| Dictamen fundado de vigencia de la Ley 24.714 | `docs/revision/dictamen_vigencia.md` | D-145 |
| Prueba de árbol que prohíbe filtrar versiones por `rv.release_id` | `tests/` | D-142 |
