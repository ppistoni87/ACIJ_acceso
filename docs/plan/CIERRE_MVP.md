# Plan de cierre del MVP — ACIJ Acceso a Derechos

Derivado de las brechas verificadas en `docs/auditoria/ESTADO_Y_HALLAZGOS.md` y
`docs/auditoria/MATRIZ_PLAN_VS_REALIDAD.md` (13/09/2026, `e1aa8c9`).
**No reemplaza `docs/plan/Plan_Integral_ACIJ.md`.** Conserva los IDs originales y
los relaciona con IDs nuevos `T-xx`.

---

## 1. Alcance de cierre — qué podrá hacer una persona, y qué no

Esto se define **antes** de estimar, porque el esfuerzo depende de dónde se pone
la línea.

### Lo que el MVP permitirá hacer

Una persona entra al front web desde el teléfono o la computadora, escribe en
lenguaje natural qué le pasa —o elige su situación de una lista—, y el sistema:

1. le pregunta **de a un dato por vez**, con las palabras de la norma, cuando ese
   dato cambia la orientación;
2. le dice **qué condiciones cumple, cuáles no y cuáles no se pueden determinar**
   con lo que contó, para **al menos un programa** del corpus;
3. le muestra **las vías de subsanación** que la norma prevé para lo que no cumple;
4. le da **próximos pasos concretos** y **dónde ir o llamar**, con la fecha en que
   ese dato se sacó de la página oficial;
5. le muestra **la fuente oficial abrible** de cada afirmación relevante;
6. **le dice que no sabe** cuando no sabe, y le ofrece atención humana;
7. le deja **corregir** cualquier dato y ver que la orientación cambió;
8. borra todo al salir, y le dice qué guardó y por cuánto.

En ningún momento afirma que el beneficio le corresponde, que se lo van a
otorgar, denegar o revocar: la decisión es del organismo, y la pantalla lo dice.

### Fuentes y casos efectivamente cubiertos en el cierre

* **Nacional (ANSES / Ley 24.714 y su reglamentación):** AUH, asignación por hijo,
  hijo con discapacidad, embarazo, prenatal, maternidad, nacimiento, adopción,
  matrimonio, cónyuge SIJP, ayuda escolar anual, cuidado de salud integral.
* **CABA:** apoyo a la vulnerabilidad habitacional (Ley 6935/2025), subsidio de
  situación de calle (Decreto 690/06), becas estudiantiles (Ley 2917), beca de
  comedor escolar (Ordenanza 43.478).
* **Datos operativos:** 290 puntos de atención con 6.134 canales y 6.467 barrios
  RENABAP, cada uno con la fecha de su captura.

### Limitaciones que se comunicarán en la pantalla

* «Esto no es una decisión del organismo.»
* Que la lista de programas **no es completa** y que el corpus cubre 44 de 85
  fuentes catalogadas.
* Que un dato de contacto fue publicado por el organismo en una fecha dada y
  **no** que alguien lo haya confirmado por teléfono.
* Qué condiciones **no** se pudieron formalizar y por eso quedan «no determinables».

### Fuera del cierre (segunda etapa ya acordada)

Audio y lectura de respuestas (P-033), explicación de PDF/imágenes (P-034),
novedades opcionales (P-035), su evaluación (P-036) y su despliegue (P-038).
**WhatsApp, SMS, correo y push quedan fuera por instrucción expresa.**

### Reducciones de alcance propuestas — decisiones, no recortes silenciosos

| Propuesta | Consecuencia si se acepta | Consecuencia si se rechaza |
| --- | --- | --- |
| **D-P1 — ACEPTADA el 13/09/2026 (D-148).** Curar a fondo **4 beneficios** (AUH, asignación por hijo, Ley 6935, becas estudiantiles) en vez de los 16 | El MVP concluye de verdad en los cuatro caminos más consultados; los otros 12 siguen ofreciéndose con evidencia y sin dictamen, dicho en pantalla | Curar 176 reglas antes de cerrar: es el camino crítico entero y no hay capacidad declarada para sostenerlo |
| **D-P2.** Piloto **interno** antes que público | Se valida con personas de ACIJ, sin exponer orientación a quien depende de ella | Salir a público con la gate DQ18 sin cumplir |
| **D-P3.** Cubrir los **montos del período corriente** solamente (no la serie histórica) | Se puede contestar «cuánto cobro»; la serie queda para después | Hoy no hay ningún monto vigente (H-08) |

Ninguna de las tres elimina requisitos, fuentes ni historias del compromiso: las
difiere y lo deja escrito. **La decisión es de producto, no de esta auditoría.**

### Qué se preserva

Todo el código actual. No hay ningún refactor propuesto por gusto: los dos únicos
cambios estructurales del plan (`T-01`, `T-02`) están justificados por defectos
P0 comprobados. **No se propone migrar de stack, reescribir ni cambiar de
plataforma.**

---

## 2. Hitos, camino crítico y demostración observable

| Hito | Entrada | Salida (demostración observable) |
| --- | --- | --- |
| **M0 · El tablero dice la verdad** | rama actual | Una corrida de CI **en verde** que ejecuta migraciones, `alembic check`, 1.504 pruebas, verificador de salteos y `docker build` |
| **M1 · El chatbot concluye y se calla cuando no sabe** | M0 | En vivo: un programa da dictamen con condiciones cumplidas/no cumplidas/desconocidas, y «¿cuánto sale un pasaje a Madrid?» devuelve abstención con derivación |
| **M2 · La conversación progresa** | M1 | En vivo: tres turnos donde el sistema pregunta de a uno, la persona corrige, y el dictamen cambia |
| **M3 · El corpus sostiene la respuesta** | M1 | Montos vigentes, vigencia en la cita, referencias navegables, cero etiquetas HTML, invariante publicado≡servido |
| **M4 · Está en un lugar al que se entra** | M0, y **espera externa** | Front y API por HTTPS sobre base persistente, scheduler corriendo, restauración ensayada |
| **M5 · Alguien lo usó** | M1–M4 | Gate DQ18 cumplida y piloto interno con recorridos aprobados |

**Camino crítico:** `T-04 → T-01 → T-01b → T-12 → T-13`.
El cuello de botella real no es de ingeniería sino de **curaduría jurídica**:
`T-01` es la tarea más larga y **todo M1, M2 y M5 dependen de ella**.

**Puede avanzar en paralelo, sin bloquear a nadie:** `T-02`, `T-03`, `T-06`,
`T-07`, `T-09`, `T-10`, `T-14`, `T-15`.
**Bloqueado por decisión externa:** `T-11` (infraestructura) y `T-05` (proveedor
de modelo), que arrastran a `T-02b` sólo en su parte de destino.

---

## 3. Backlog ejecutable

Formato por tarea: **ID / IDs originales · objetivo de usuario · alcance ·
componentes · pasos técnicos · dependencias · responsable por rol · esfuerzo y
supuestos · criterios de aceptación · prueba o comando · evidencia de cierre.**

Los esfuerzos son **rangos en jornadas de una persona dedicada al rol indicado**.
**No hay fechas firmes ni capacidad de equipo declarada**: no se conoce quién ni
cuántas personas hay. Se separa el esfuerzo técnico de las esperas externas.

---

### PRIMER BLOQUE DE TRABAJO — detallado

#### T-04 · Dejar el CI en verde de punta a punta
* **IDs originales:** P-018 · resuelve **H-03, H-04, H-05**, habilita comprobar **H-14**
* **Objetivo de usuario:** ninguno directo. Es la condición para que todo lo demás
  se pueda afirmar: hoy los mensajes de commit dicen «1.504 pruebas en verde» y en
  CI no corrió ninguna.
* **Alcance:** los tres pasos que fallan, y sólo esos. No se toca el workflow salvo
  para no romperlo.
* **Componentes:** `src/backend_normativo/api/routers/recuperacion.py:502`,
  `src/backend_normativo/db/models/publicacion.py:205`,
  `src/backend_normativo/db/models/` (seis tablas y dos columnas),
  `tests/conftest.py` (fixture `corpus`), `.github/workflows/ci.yml`.
* **Pasos técnicos:**
  1. `ruff format .` y confirmar `ruff format --check .` en verde.
  2. Declarar en los modelos ORM: `sesiones_conversacion`, `release_versiones`,
     `fragmento_vectores`, `indices_semanticos`, `credenciales_revocadas`,
     `arrendamientos`; las columnas `auditoria_eventos.identidad` y
     `chunks.url_fuente`; los índices `ix_chunks_tsv`,
     `ix_fragmento_vectores_hnsw`, `ix_release_versiones_version`,
     `ix_sesiones_actividad`, `ix_sesiones_creada`; y **borrar** las columnas
     fantasma `chunks.modelo_embedding` y `chunks.embedding_ref`. Alinear los tres
     comentarios divergentes.
  3. Ampliar el corpus de prueba con una versión candidata, un documento con dos
     versiones documentales y una regla candidata, para que dejen de saltearse las
     6 pruebas de `test_aprobacion_operativa`, `test_backoffice_normas`,
     `test_tablero_de_calidad` y `test_transcripcion_decisiones`.
  4. Empujar y mirar la corrida completa, incluido `docker build`.
  5. Pedir protección de rama (**espera externa**: permisos de administración).
* **Dependencias:** ninguna. **Es la primera tarea.**
* **Responsable por rol:** backend + QA.
* **Esfuerzo:** **1–2 jornadas**. Supuestos: la deriva ORM es sólo declarativa
  (verificado: la base ya tiene el esquema correcto) y no aparece una falla nueva
  en los pasos 8–11, que **nunca corrieron en CI** y podrían traer sorpresas —de
  ahí el rango.
* **Criterios de aceptación:** (a) `ruff check` y `ruff format --check` en verde;
  (b) `alembic check` sin operaciones detectadas; (c) 1.504+ pruebas ejecutadas
  con 0 salteos no declarados; (d) `docker build` exitoso; (e) **una corrida de CI
  con `conclusion: success`**.
* **Prueba / comando:** `ruff check . && ruff format --check . && alembic upgrade head && alembic check && pytest -q -rs --junitxml=resultados/pruebas.xml && python scripts/verificar_salteos.py resultados/pruebas.xml && docker build -t acij-acceso:local .`
* **Evidencia de cierre:** URL de la corrida de CI en verde.

#### T-01 · Que al menos un beneficio pueda concluir
* **IDs originales:** P-014, P-010, P-008 · resuelve **H-01 (P0)**
* **Objetivo de usuario:** «Contesté todo lo que me preguntaron y ahora sé qué
  condiciones cumplo y cuáles no.»
* **Alcance:** curar hasta dejar **el 100 % de las reglas de acceso ejecutables**
  (categorías `APLICABILIDAD` y `EXCLUSION`, más sus `EXCEPCION`) de los
  beneficios que la decisión D-P1 fije. Se empieza por **uno**.
* **Componentes:** `reglas/` (AST), `curacion/`, `bn revision`, y las filas de
  `reglas` (176) en la base. No se cambia el motor: **el motor funciona**
  (`test_todo_cumplido_da_un_resultado_preliminar_positivo`).
* **Pasos técnicos:**
  1. Elegir el beneficio semilla por volumen: `AR.ASIGNACION-POR-CONYUGE-SIJP`
     (4 reglas, 1 no ejecutable) o `AR.ASIGNACION-POR-ADOPCION` (5, 1).
  2. Para cada regla sin AST: escribir la condición tipada desde el texto literal,
     con su evidencia, o clasificarla como informativa —y entonces **no** debe
     contar como bloqueante.
  3. Para cada regla con `requiere_revision`: revisarla y decidir, dejando el
     evento con actor.
  4. Verificar la hipótesis **I-03**: cruzar las `condiciones_desconocidas` que
     quedan contra `conversacion/preguntas._preguntables()`, para saber cuántas
     son las reglas multicampo de D-136 y necesitan un rótulo por hoja.
  5. Publicar un corte y volver a correr la evaluación.
  6. Repetir para AUH, asignación por hijo, Ley 6935 y becas estudiantiles.
* **Dependencias:** T-04 (para que la prueba nueva cuente).
* **Responsable por rol:** curaduría jurídica (principal) + backend (rótulos por hoja).
* **Esfuerzo:** **1–2 jornadas el beneficio semilla**; **8–15 jornadas los cuatro
  del alcance D-P1**; **30–50 jornadas los 16**. Supuestos: 176 reglas, 67 sin AST
  y 77 por revisar; ritmo estimado de 8–15 reglas por jornada según complejidad
  del texto. **Este rango es el mayor riesgo de estimación de todo el plan** y hay
  que recalibrarlo con el beneficio semilla antes de comprometer nada.
* **Criterios de aceptación:** con hechos favorables el beneficio devuelve
  `POTENCIALMENTE_APLICABLE`; con un hecho bloqueante devuelve
  `NO_CUMPLE_REGLA_EXPLICITA` **acompañado de sus vías de subsanación**; con un
  dato ausente devuelve `REQUIERE_DATOS` y la pregunta que falta. Ninguna
  respuesta afirma otorgamiento ni denegatoria.
* **Prueba / comando:** una prueba de aceptación nueva que recorra los tres casos
  vía `POST /v1/evaluaciones-preliminares`, más
  `bn calidad consultas` para no regresionar.
* **Evidencia de cierre:** la prueba en verde en CI y el corte publicado que la
  sostiene.

#### T-02 · Abstenerse cuando no hay evidencia que respalde
* **IDs originales:** P-013, P-023 · resuelve **H-02 (P0)**
* **Objetivo de usuario:** «Me dijo que eso no lo sabe, en vez de darme una ley
  que no tiene nada que ver.»
* **Alcance:** umbral de puntaje en la recuperación y una salida tipada de
  abstención que el front sepa mostrar. **No** incluye el reranker (eso es T-03).
* **Componentes:** `recuperacion/`, `api/routers/recuperacion.py`,
  `api/contratos.py` (código de abstención), `consulta.html`.
* **Pasos técnicos:**
  1. Instrumentar la puntuación de los resultados y volcarla para las 150 consultas.
  2. Barrer el umbral sobre el conjunto congelado midiendo **las dos direcciones**:
     cuántos de los 54 casos pasan a abstenerse y cuántos de los 78 que hoy pasan
     se pierden (hipótesis **I-01**).
  3. Fijar el umbral con la medición a la vista y dejarlo configurable por entorno.
  4. Emitir `SIN_EVIDENCIA_SUFICIENTE` con motivo, y que el front lo convierta en
     abstención + oferta de atención humana.
* **Dependencias:** ninguna técnica; se valida con T-12.
* **Responsable por rol:** datos/RAG + backend + front.
* **Esfuerzo:** **3–5 jornadas.** Supuesto: el conjunto congelado de 150 consultas
  alcanza para calibrar; si el barrido muestra que no hay umbral que mejore las dos
  direcciones, la tarea escala a T-03 y el rango sube.
* **Criterios de aceptación:** los 54 casos `SE_ABSTIENE → RESPONDE_CON_EVIDENCIA`
  pasan a abstenerse; **ninguno** de los 78 que hoy pasan se rompe; una consulta
  fuera de alcance devuelve abstención con derivación y sin fragmentos.
* **Prueba / comando:** `bn calidad consultas` y un caso E2E con «¿cuánto sale un
  pasaje de avión a Madrid?».
* **Evidencia de cierre:** el informe de la gate antes y después.

#### T-01b · Que la conversación elija el programa y pregunte de a una
* **IDs originales:** P-025 (criterio 2), P-026, P-030 · resuelve **H-06, H-07**
* **Objetivo de usuario:** «Me preguntó cuál de estos programas, se lo dije, y a
  partir de ahí me fue preguntando de a una cosa.»
* **Alcance:** cerrar la bifurcación del grafo que hoy no se toma. La elección la
  hace **la persona**, nunca el sistema por parecido.
* **Componentes:** `conversacion/grafo.py` (`_nodo_identificar`,
  `_hay_que_aclarar`), `conversacion/sesion.py`, `api/routers/recuperacion.py`,
  `consulta.html`.
* **Pasos técnicos:**
  1. Cuando hay varios candidatos, emitir **una pregunta de elección** en vez de
     `motivo_sin_evaluar="varios_beneficios"` sin salida.
  2. Guardar la elección como contexto de sesión y **usarla para acotar** los
     candidatos de los turnos siguientes (hoy se recalculan desde la última frase).
  3. Acumular intención y hechos en el estado y filtrar la identificación con ellos.
  4. Una prueba de aceptación **sin dobles** que recorra API→pregunta→respuesta→dictamen.
* **Dependencias:** **T-01** (sin un beneficio que concluya, la conversación
  progresa hacia nada).
* **Responsable por rol:** backend conversacional + front.
* **Esfuerzo:** **3–5 jornadas.**
* **Criterios de aceptación:** en tres turnos el conjunto de candidatos **no
  crece**; el beneficio nombrado explícitamente aparece entre los candidatos; una
  pregunta contestada cambia el dictamen; nunca se hacen dos preguntas en el mismo
  turno; lo que no se puede preguntar se cuenta y se declara.
* **Prueba / comando:** prueba de aceptación nueva + los 59 E2E de Chromium.
* **Evidencia de cierre:** la traza de la conversación de tres turnos.

---

### BLOQUES SIGUIENTES — definidos para ejecutar y refinar

| ID | IDs orig. | Objetivo de usuario | Alcance y pasos | Dependencias | Rol | Esfuerzo | Aceptación / prueba |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **T-14** | P-011 · H-09 | Que nada publicado deje de servirse en silencio | Invariante `PUBLISHED ≡ miembro del corte vigente`; consulta en la publicación que lo reporte; reparar la membresía de la Ley 6935; prueba que falle si vuelve a pasar | T-04 | backend | **1–2 j** | La diferencia entre 14.476 y las membresías del corte es 0, o está reportada. `bn publicacion publicar --simular` lo declara |
| **T-15** | P-007 · H-08, H-10, H-11, H-13 | Que la respuesta traiga montos vigentes, el estado de vigencia y las normas que cita | (a) cargar y aprobar los valores del período corriente; (b) normalizar el texto en curación y rechazar marcado en la publicación; (c) proyectar `valid_tipo`/intervalo en cada cita; (d) resolver referencias cruzadas del corte como enlaces | T-04 | curaduría + backend | **4–7 j** | `GET /v1/valores` devuelve SMVM y AUH con período que contiene hoy; 0 fragmentos con etiquetas; una consulta sobre norma con derogación parcial lo declara; una cita a otra norma del corte es navegable |
| **T-03** | P-012, P-026 · R-04 | Que lo que se recupera sea lo pertinente | Reranker acotado sobre el conjunto congelado; se aprueba **sólo con mejora demostrada** | T-02 | datos/RAG | **5–8 j** | Recall@5 ≥ 90 % sin perder precisión; medición antes/después |
| **T-02b** | P-031 | Que quien no encuentre respuesta llegue a una persona | Cola de derivación con acuse y contexto; directorio con fecha de verificación. **Nunca se inventa un teléfono**: sólo se ofrece lo capturado, con su fecha | T-02; destino → T-11 | producto + backend + front | **4–6 j** técnicas + **espera** de la decisión de ACIJ sobre quién atiende | Una derivación deja registro con contexto y acuse; la pantalla dice qué pasa después |
| **T-07** | P-028 | Que cada afirmación tenga su fuente, no la respuesta entera | `evidence_ids` por afirmación, criticidad, verificación de respaldo semántico, retención de la afirmación afectada y no de la respuesta | T-05 para el modo generado | backend | **5–8 j** | Una afirmación sin respaldo se retiene sola; el resto de la respuesta se sirve |
| **T-06** | P-032, P-015 | Que las fuentes se puedan abrir y cerrar, y que los errores se vean | «Ver fuentes» plegable por respuesta; estados de carga, error y vacío; recuperación ante fallo; navegación por teclado | — | front | **3–5 j** | Los 59 E2E más casos nuevos de error/vacío/teclado |
| **T-08** | P-030 (crit. 3), P-009, P-016 | Que los próximos pasos incluyan lo que pide el organismo | Curar los 6 trámites hoy en CANDIDATE y asociarlos a su beneficio; publicarlos; ejercer el circuito de revisión con datos reales | T-01, T-04 | curaduría + backoffice | **4–7 j** | Un beneficio muestra los pasos y documentos del organismo, con su fuente |
| **T-09** | P-029, P-015 | Que el sistema hable siempre igual y se entienda | Catálogo versionado de textos (ID, situación, texto anterior, corregido, variables, responsable, fecha); revisión de accesibilidad **con personas** | — | producto + front | **3–5 j** + **espera** de las sesiones con personas | Cada texto de pantalla sale del catálogo; informe de accesibilidad con hallazgos |
| **T-10** | P-017, P-037 | Que la persona decida qué se guarda | Consentimientos independientes; recuperación entre sesiones; modelo de amenazas escrito; proveedor de identidad para el backoffice | — | seguridad + backend | **5–8 j** + **espera** de la elección de proveedor de identidad | Consentimientos verificables; modelo de amenazas revisado |
| **T-05** | P-027, P-013, P-021 · R-01 | Que la respuesta se explique en castellano, no se copie | Configurar un proveedor real; registrar modelo, versión, región, límites y **costo medido**; salida validada por Pydantic; ensayo de reversión a `EXTRACTO`; **ejercitar la inyección de prompt desde una fuente recuperada contra el modelo real** | **espera externa**: clave y presupuesto | backend + seguridad | **4–6 j** una vez desbloqueado | Modo `GENERADA` con validadores en verde; una fuente con instrucciones maliciosas no cambia el comportamiento; caída del proveedor degrada a `EXTRACTO` sin error |
| **T-11** | P-002, P-004, P-005, P-019, P-020, P-022 | Que exista un lugar al que entrar | Base persistente, bucket, HTTPS, scheduler, monitoreo, respaldo y **restauración ensayada contra el destino**; medir RPO/RTO. **Rotar antes la credencial de R-03** | **espera externa**: cuenta de nube y presupuesto | infraestructura | **6–10 j** una vez desbloqueado | Front y API por HTTPS; una restauración ejecutada y verificada sobre el destino |
| **T-12** | P-023 | Que la calidad se mida y no se opine | Completar el conjunto a 150 con la credencial del arnés resuelta (H-15); correr la gate como criterio de salida; **evaluación de las respuestas por alguien distinto de quien las genera** | T-01, T-01b, T-02, T-15 | QA | **4–6 j** | Gate DQ18 cumplida; 0 casos `SIN_CLASIFICAR`; revisión independiente de una muestra |
| **T-13** | P-024 | Que alguien de ACIJ lo use antes que el público | Piloto interno con recorridos guionados y registro de hallazgos | T-11, T-12 | producto | **5–8 j** + **espera** de la disponibilidad de las personas | Recorridos críticos aprobados por quien participó |

---

## 4. Primeras diez acciones, en orden

1. `ruff format .` y confirmar que `ruff format --check .` pasa. *(T-04)*
2. Declarar las 6 tablas y 2 columnas en los modelos ORM y borrar las 2 fantasma;
   `alembic check` en verde. *(T-04)*
3. Ampliar el corpus de prueba para que las 6 pruebas salteadas corran. *(T-04)*
4. Empujar y **verificar una corrida de CI en verde**, incluido `docker build`. *(T-04)*
5. Curar el beneficio semilla hasta 0 reglas no ejecutables y **recalibrar con eso
   la estimación de T-01**. *(T-01)*
6. Publicar el corte y probar los tres resultados del dictamen con una prueba de
   aceptación. *(T-01)*
7. Instrumentar el puntaje de recuperación y barrer el umbral sobre las 150
   consultas, midiendo las dos direcciones. *(T-02)*
8. Emitir `SIN_EVIDENCIA_SUFICIENTE` y mostrarlo como abstención con derivación. *(T-02)*
9. Reemplazar `motivo_sin_evaluar="varios_beneficios"` por una pregunta de elección
   y usar la elección para acotar los turnos siguientes. *(T-01b)*
10. Cargar y aprobar los valores de parámetro del período corriente. *(T-15)*

En paralelo y sin bloquear a nadie: **rotar la credencial de `neondb_owner`**
(R-03) y **pedir la decisión de infraestructura** que desbloquea T-11 y T-05.

---

## 5. La primera historia lista para implementar

> **T-04 · Dejar el CI en verde de punta a punta.**
> Está completamente especificada en §3: archivos y líneas exactas, los seis
> nombres de tabla, las dos columnas a agregar y las dos a borrar, las cuatro
> pruebas cuyo corpus hay que ampliar, el comando de validación y la evidencia de
> cierre. No depende de ninguna decisión pendiente ni de ningún acceso externo, y
> **hasta que no esté hecha ninguna otra afirmación de este repositorio sobre su
> propia salud es comprobable**.

---

## 6. Decisiones realmente pendientes

| # | Decisión | Quién debería resolverla | Qué se necesita | Qué sigue disponible mientras tanto | Cómo se verifica el desbloqueo |
| --- | --- | --- | --- | --- | --- |
| ~~1~~ | ~~**D-P1**: ¿4 beneficios o los 16?~~ | — | — | — | **Resuelta el 13/09/2026: cuatro (D-148).** |
| 2 | **Infraestructura**: cuenta de nube, base persistente, bucket, HTTPS, scheduler | Responsable del proyecto | Presupuesto y titularidad de la cuenta | Todo el trabajo local | Existe un destino y `bn operacion` restaura contra él |
| 3 | **Proveedor de modelo**: cuál, con qué límites y qué costo por consulta se acepta | Responsable del proyecto | Clave y presupuesto | Modo `EXTRACTO`, que ya funciona | `GENERADA` con costo medido y ensayo de reversión |
| 4 | **Quién atiende las derivaciones** | ACIJ | Persona o equipo, horario y canal | La señal ya se cuenta | Una derivación con acuse y respuesta |
| 5 | **Revisión jurídica externa**: D-130 decidió proceder sin firma jurídica. ¿Se sostiene para un piloto con público? | ACIJ | Criterio institucional | Todo, con la salvedad escrita en pantalla | Decisión documentada |
| 6 | **Protección de la rama y estrategia de ramas** (hoy hay una sola, sin proteger, y es la rama por defecto) | Responsable del repositorio | Permisos de administración | Todo | `main` protegida y CI obligatoria para integrar |
| 7 | **Revisión de este código por alguien que no lo escribió** | ACIJ | Una persona con criterio técnico ajena a la sesión | Todo | Informe de revisión independiente |

---

## 7. Qué NO se propone hacer

* No se propone reescribir nada, ni cambiar de stack, ni introducir plataformas
  nuevas. Los dos cambios estructurales (T-01, T-02) responden a defectos P0
  comprobados y son locales.
* No se propone tocar el motor de reglas: **funciona**; lo que falta son datos.
* No se propone quitar del compromiso ninguna fuente, historia ni criterio. Las
  reducciones de §1 son propuestas explícitas con sus consecuencias.
