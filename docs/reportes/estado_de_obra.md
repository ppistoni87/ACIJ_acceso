# Estado de obra: las 24 historias del plan integral

El backend está construido y el corpus está cargado. Lo que todavía no existe es
una sola regla jurídica firmada, y de ahí cuelga casi todo lo que falta: el
sistema hoy sabe abstenerse mejor de lo que sabe responder.

Estado al 11.09.2026, rama `claude/backend-normativo-user-stories-41z94i`,
sobre `024bee1` más los cambios del frente ciudadano. Ninguna cifra de las
tablas de este informe es una estimación: todas salen de una consulta a la base
o de un reporte generado.

- **5** historias cerradas contra su criterio de aceptación
- **16** parciales, con el resto identificado
- **2** sin empezar, las dos de cierre (P-023 y P-024)
- **1** no hecha a propósito: P-010, la firma jurídica
- **1.240** pruebas verdes, **108** decisiones registradas

El recuento sale de la tabla de abajo, columna por columna. Decía «11 cerradas,
8 parciales, 5 sin empezar»: quedó de una versión anterior y ya no coincidía con
su propia tabla. Un número escrito a mano arriba de una tabla que sí se
actualiza es la forma más barata de mentir sin querer.

## Los seis tramos

| Gate | Trabajo | Estado |
| --- | --- | --- |
| G0 | Línea de base, inventario, decisiones, CI iniciada | Cumplido |
| G1 | Neon, migraciones, roles, originales, bootstrap | Cumplido |
| G2 | Fuentes pendientes, relaciones, siete dimensiones, revisión | Parcial |
| G3 | Publicación por corte, recuperación híbrida, generación, front | Parcial |
| G4 | Backoffice, cierre jurídico, scheduler, alertas, restauración | Abierto |
| G5 | Evaluación independiente, piloto, traspaso | Abierto |

## Las cinco causas

Los pendientes no son un problema distinto cada uno. Hoy **ninguna de las cinco
causas se resuelve escribiendo código**: la que lo era se agotó.

**A · Falta una firma jurídica.** El criterio 2 de P-010 lo prohíbe
explícitamente: las reglas «no se aprueban en lote por un agente». Aprobarlas
desde acá pondría en la bitácora un actor que no revisó nada y haría que la API
empiece a contestar «te corresponde» sobre esa base. Afecta a P-008, P-010,
P-014 y P-023.

**B · Falta una cuenta de nube.** Bucket privado, Cloud Run, Cloud Scheduler,
canal de alertas y el plan contratado de Neon con su retención. Nada de eso se
provisiona desde el repositorio. Afecta a P-004, P-019, P-020, P-021 y P-022.

**C · Falta construirlo. Agotada.** Era desarrollo no empezado y no bloqueado
por nada externo: P-013, P-015 y P-016. Los tres están construidos y probados.
Lo que les queda no es código —una clave de proveedor de modelo, una URL de
staging y una revisión de accesibilidad con personas— y cae bajo las causas B
y A.

**D · Límite del contenedor.** Sin egreso TCP al puerto 5432, el esquema se
aplicó a Neon por su endpoint HTTPS oficial —TLS validado, sin túneles—, pero la
carga del corpus y la medición de conexiones contra la base remota no se
pudieron ejercitar acá. Afecta a P-002 y P-005.

**E · Falta decidir qué cuenta como verificar un directorio.** La base exige
desde la primera migración que nada llegue a `PUBLISHED` sin fecha de
verificación, y ninguna de las 14.390 versiones operativas aprobadas la tiene:
1.842 puntos de atención, 6.134 canales, 6.467 barrios y 9 valores. Nada en la
curación se la pone —sólo la ponen `Revisor.resolver` y `ResolutorVigencia`, que
trabajan sobre normas—. Es la razón por la que el frente dice «no tengo cargado
a quién derivarte» teniendo 1.842 lugares cargados. Si alcanza la fecha de la
captura oficial, que es cuándo se vio lo que la fuente publicaba, o hace falta
confirmarlos uno por uno, lo decide ACIJ: es lo que define si esos lugares
llegan a la pantalla de alguien que esta noche no tiene dónde dormir. Afecta a
todo el corpus operativo y, por dependencia, a P-023 y P-024. Hasta la
publicación de este informe la causa estaba oculta: `bn publicacion estado`
contaba los 14.390 como publicables y con los ocho gates en verde (D-128).

## Historia por historia

| # | Historia | Estado | Qué falta y por qué |
| --- | --- | --- | --- |
| P-001 | Consolidar una línea de base reproducible | Hecha | Nada del criterio. |
| P-002 | Provisionar PostgreSQL persistente en Neon | Parcial | Criterio 3: medir el presupuesto de conexiones con carga (causa D). La región se heredó del proyecto y no se eligió con criterios medibles. |
| P-003 | Migrar el esquema y aislar permisos | Parcial | Ninguna prueba corrió todavía contra PostgreSQL 18: el CI usa 16 y Neon sirve 18.6. El esquema remoto está al día en `0011`, verificado contra la base con `scripts/estado_neon.py`. |
| P-004 | Conservar originales fuera del contenedor | Parcial | El bucket privado y su política de retención (causa B). La verificación de integridad está implementada y bloquea la publicación. |
| P-005 | Cargar el corpus de forma reanudable | Parcial | Los tres criterios se cumplen, pero nunca corrió contra Neon (causa D). |
| P-006 | Completar adaptadores y fuentes operativas | Parcial | **44 de 85 sirven** (eran 31). Las «capturadas y sin destino» bajaron de 17 a 7 y las «nunca extraídas» de 5 a 2. Cuatro arreglos: la extracción de páginas institucionales daba cero unidades; los índices no se seguían; el adaptador aceptaba por dominio y no por lo que el catálogo declara; y una página sin encabezados quedaba sin nada que citar. Sobre las que se pueden ingestar hoy —descontadas las bloqueadas, las de carga manual y las que el catálogo declara que no se ingestan— **sirven 44 de 55**. Quedan 7 sin destino, 2 boletines sin adaptador, 4 esperando carga manual y 17 bloqueadas por política de acceso. Ninguna fuente activa quedó sin capturar. |
| P-007 | Resolver citas, vigencia y relaciones | Hecha | Las 215 referencias sin resolver son la cola auditable que el criterio 2 pide. |
| P-008 | Completar las siete dimensiones | Parcial | 135 campos en PENDIENTE y sólo 4 INFORMADO (1,06 %). Causa A. |
| P-009 | Operar el circuito de revisión humana | Hecha | Nada del criterio. Falta que alguien lo use, y eso es P-010. |
| P-010 | Resolver el expediente jurídico del alcance | **No hecha, a propósito** | La firma. 166 candidatas listas —109 con condición ejecutable, 57 sin ella—. Causa A. |
| P-011 | Publicar cortes completos y reversibles | Hecha | Nada del criterio. |
| P-012 | Implementar recuperación híbrida trazable | Parcial | Construida y medida: Recall@5 híbrido **74,1 %**, sin llegar al umbral de 90 %. La mitad léxica daba **0,0 % en los tres k**: `plainto_tsquery` exige todas las palabras y ninguna pregunta entera las tiene. Con la ampliación por sonda pasó a 18,5 / 51,9 / 55,6 %, y la híbrida subió de 33,3 a 37,0 en @1 y de 51,9 a 66,7 en @3. El techo de @5 es otro: el corte publicado se armó con la extracción vieja, y volver a medir sobre un corte limpio exige re-curar las citas (trabajo jurídico). |
| P-013 | Generar respuestas con citas y abstención | Parcial | Construido: tres modos declarados —generada, extracto, abstención—, cuatro validadores de cita y un proveedor HTTP configurable por entorno, probado entero con `httpx.MockTransport`. Sin `BN_MODELO_CLAVE` contesta en modo extracto, que no puede alucinar. Falta la evidencia del criterio 1, «proveedor real probado en staging»: necesita una clave del proyecto (causa B). |
| P-014 | Evaluar condiciones con lógica tipada | Parcial | El criterio 1 dice «reglas publicadas» y no hay ninguna. Causa A. |
| P-015 | Completar el front conversacional | Parcial | Construido y probado: una pantalla en `/consulta`, servida por la misma imagen que la API, con jurisdicción y fecha elegibles dentro del diálogo, cancelar, reintentar, empezar de nuevo y salir borrando. La respuesta muestra explicación, fuentes abribles, fecha, estado de la información, advertencias y canal oficial; errores y abstenciones tienen mensajes en castellano llano. 36 casos de extremo a extremo en Chromium, nueve de ellos de accesibilidad, sobre un corte que ahora incluye un lugar de atención publicado. Es un **chat**: un hilo de mensajes donde la persona escribe con sus palabras y sigue preguntando. Las aclaraciones —jurisdicción, fecha— pasan dentro del diálogo y lo que el sistema termina teniendo en cuenta queda a la vista y se puede quitar. El ciclo cierra: al pie de cada respuesta hay tres botones —«Sí», «No», «Quiero hablar con una persona»— y **ninguna caja de texto**, la señal se cruza con la traza por `request_id` y se lee con `bn operacion devoluciones`. Pedir una persona no abre un canal de vuelta y la pantalla lo dice: como no se piden datos, no hay a dónde escribirle a quien lo pidió. Falta todavía el escenario «¿cumplo?» con datos faltantes, que exige que el sistema repregunte y depende de las reglas firmadas (causa A). Faltan además las dos evidencias que no dependen de código: **URL de staging integrada** (causa B) y **revisión manual de accesibilidad** con personas usando lector de pantalla, declarada abierta en `docs/reportes/accesibilidad_frente_ciudadano.md`. |
| P-016 | Completar el backoffice de datos y revisión | Hecha | Consola de revisión de reglas con cola clasificada y firma con fundamento obligatorio; búsqueda de normas por número y por título; comparación de dos versiones cualesquiera; tablero de calidad con siete indicadores que abren el registro que cuentan. |
| P-017 | Identidad, privacidad y protección | Parcial | **Criterios 1 y 2 cerrados, 3 casi.** El actor sale de una credencial firmada por persona, con roles, vencimiento y revocación. La consulta ciudadana no pide DNI, domicilio ni datos de contacto —no existe el campo—, la traza guarda la forma de la consulta y nunca su texto, y caduca a los 90 días con `bn operacion purgar-consultas`. Hay límites en servidor: dos baldes por origen, 429 tipado con `Retry-After`, y el 429 queda medido. Todo en `docs/operacion/politica_de_datos.md`. Falta un proveedor de identidad (OIDC) y el modelo de amenazas escrito como tal. |
| P-018 | Hacer obligatoria la integración continua | Parcial | Criterio 3: la protección de rama necesita permisos de administración del repositorio. |
| P-019 | Desplegar revisión y producción | Parcial | Las sondas están: `/salud` no toca la base a propósito —si dependiera de ella, una base momentáneamente inalcanzable reiniciaría procesos sanos— y `/listo` verifica conexión, migración aplicada y, en producción, corte publicado, devolviendo 503 con el motivo. Falta el despliegue en sí (causa B). |
| P-020 | Programar monitoreo y entrega de eventos | Parcial | Sólo el disparador horario (causa B). El criterio 2 quedó cerrado: dos disparos simultáneos ya no procesan lo mismo dos veces. |
| P-021 | Medir salud, calidad, costos y nivel de servicio | Parcial | Cada consulta de lectura deja rastro correlacionable —`X-Request-Id`, ruta, resultado, latencia, corte y motivo de abstención— sin guardar nada de quien pregunta, y el tablero de calidad sirve siete indicadores por API y por CLI. Faltan alertas y panel de gasto (causa B). |
| P-022 | Respaldar y restaurar base más documentos | Parcial | La retención de Neon no está decidida y RPO/RTO no están medidos contra el plan contratado. Causa B. |
| P-023 | Validar el recorrido completo | Sin empezar | Depende de nueve historias. Faltan 52 consultas para llegar a las 150 anotadas. |
| P-024 | Piloto, traspaso y cierre | Sin empezar | Depende de P-023. Su criterio 2 ordena este informe: «no se denomina completo a un corpus parcialmente habilitado». |

## Qué desbloquea qué

1. **Firmar el expediente de las 166 reglas.** Destraba P-008, P-014, dos
   capacidades que hoy sirven cero, HU-036 y, por dependencia, P-023 y P-024.
   Sólo puede hacerlo curación jurídica.
2. **Definir titularidad de la cuenta de nube y el pagador.** Una decisión
   destraba cinco historias, y además permite correr la carga contra Neon.
3. **Correr la suite contra PostgreSQL 18.** El CI usa 16 y Neon sirve 18.6. El
   esquema coincide, pero ninguna prueba corrió contra el motor que va a
   producción.
4. **Volver a medir la recuperación sobre un corte limpio.** La extracción
   corregida existe; falta re-curar las citas de la Ley 6935 para que el corte
   deje de servir los once fragmentos que no son la norma.
5. **La protección de rama** que hace obligatorios los checks de CI (P-018,
   criterio 3). Necesita permisos de administración del repositorio.

## Pendiente de seguridad

La cadena de conexión del rol `neondb_owner` circuló por el chat de la sesión.
No está en el repositorio ni en ninguna imagen, pero es el rol que aplica DDL y
conviene tratarla como comprometida: rotarla desde la consola de Neon y
actualizar `.env.local`. `bn_api` y `bn_ingesta` no se vieron afectadas. Además,
hoy cualquiera con la cadena entra: no hay lista de direcciones permitidas ni
límite de conexiones por rol.
