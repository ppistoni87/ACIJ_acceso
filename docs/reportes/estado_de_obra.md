# Estado de obra: las 24 historias del plan integral

El backend está construido y el corpus está cargado. Lo que todavía no existe es
una sola regla jurídica firmada, y de ahí cuelga casi todo lo que falta: el
sistema hoy sabe abstenerse mejor de lo que sabe responder.

Estado al 10.09.2026, commit `eef0fdb`, rama
`claude/backend-normativo-user-stories-41z94i`. Ninguna cifra de este informe es
una estimación: todas salen de una consulta a la base o de un reporte generado.

- **11** historias cerradas contra su criterio de aceptación
- **8** parciales, con el resto identificado
- **5** sin empezar

## Los seis tramos

| Gate | Trabajo | Estado |
| --- | --- | --- |
| G0 | Línea de base, inventario, decisiones, CI iniciada | Cumplido |
| G1 | Neon, migraciones, roles, originales, bootstrap | Cumplido |
| G2 | Fuentes pendientes, relaciones, siete dimensiones, revisión | Parcial |
| G3 | Publicación por corte, recuperación híbrida, generación, front | Parcial |
| G4 | Backoffice, cierre jurídico, scheduler, alertas, restauración | Abierto |
| G5 | Evaluación independiente, piloto, traspaso | Abierto |

## Las cuatro causas

Los trece pendientes no son trece problemas distintos. Tres de las cuatro causas
no se resuelven escribiendo código.

**A · Falta una firma jurídica.** El criterio 2 de P-010 lo prohíbe
explícitamente: las reglas «no se aprueban en lote por un agente». Aprobarlas
desde acá pondría en la bitácora un actor que no revisó nada y haría que la API
empiece a contestar «te corresponde» sobre esa base. Afecta a P-008, P-010,
P-014 y P-023.

**B · Falta una cuenta de nube.** Bucket privado, Cloud Run, Cloud Scheduler,
canal de alertas y el plan contratado de Neon con su retención. Nada de eso se
provisiona desde el repositorio. Afecta a P-004, P-019, P-020, P-021 y P-022.

**C · Falta construirlo.** Desarrollo no empezado y no bloqueado por nada
externo. Afecta a P-013 y P-015; de P-016 falta la parte que no es revisión de
reglas.

**D · Límite del contenedor.** Sin egreso TCP al puerto 5432, el esquema se
aplicó a Neon por su endpoint HTTPS oficial —TLS validado, sin túneles—, pero la
carga del corpus y la medición de conexiones contra la base remota no se
pudieron ejercitar acá. Afecta a P-002 y P-005.

## Historia por historia

| # | Historia | Estado | Qué falta y por qué |
| --- | --- | --- | --- |
| P-001 | Consolidar una línea de base reproducible | Hecha | Nada del criterio. |
| P-002 | Provisionar PostgreSQL persistente en Neon | Parcial | Criterio 3: medir el presupuesto de conexiones con carga (causa D). La región se heredó del proyecto y no se eligió con criterios medibles. |
| P-003 | Migrar el esquema y aislar permisos | Parcial | Ninguna prueba corrió todavía contra PostgreSQL 18: el CI usa 16 y Neon sirve 18.6. El esquema remoto está al día en `0011`, verificado contra la base con `scripts/estado_neon.py`. |
| P-004 | Conservar originales fuera del contenedor | Parcial | El bucket privado y su política de retención (causa B). La verificación de integridad está implementada y bloquea la publicación. |
| P-005 | Cargar el corpus de forma reanudable | Parcial | Los tres criterios se cumplen, pero nunca corrió contra Neon (causa D). |
| P-006 | Completar adaptadores y fuentes operativas | Parcial | **38 de 85 sirven** (eran 31). Las «capturadas y sin destino» bajaron de 17 a 10 al arreglar la extracción de páginas institucionales y curar 52 canales de atención. Quedan 29 sin capturar, 15 sin URL conocida, 5 capturadas sin extraer, y 10 que necesitan curadores de trámites, pasos y puntos de atención. |
| P-007 | Resolver citas, vigencia y relaciones | Hecha | Las 215 referencias sin resolver son la cola auditable que el criterio 2 pide. |
| P-008 | Completar las siete dimensiones | Parcial | 135 campos en PENDIENTE y sólo 4 INFORMADO (1,06 %). Causa A. |
| P-009 | Operar el circuito de revisión humana | Hecha | Nada del criterio. Falta que alguien lo use, y eso es P-010. |
| P-010 | Resolver el expediente jurídico del alcance | **No hecha, a propósito** | La firma. 166 candidatas listas —109 con condición ejecutable, 57 sin ella—. Causa A. |
| P-011 | Publicar cortes completos y reversibles | Hecha | Nada del criterio. |
| P-012 | Implementar recuperación híbrida trazable | Parcial | Construida y medida: Recall@5 híbrido **74,1 %** contra 0 % de la léxica sola, sin llegar al umbral de 90 %. La causa está identificada y corregida en el origen, pero el corte publicado se armó con la extracción vieja; volver a medir sobre un corte limpio exige re-curar las citas (trabajo jurídico). |
| P-013 | Generar respuestas con citas y abstención | Sin empezar | No hay proveedor de modelo ni validadores de cita. Causa C, depende de P-012. |
| P-014 | Evaluar condiciones con lógica tipada | Parcial | El criterio 1 dice «reglas publicadas» y no hay ninguna. Causa A. |
| P-015 | Completar el front conversacional | Sin empezar | El proyecto de front no existe: no hay ningún `package.json`. Causa C. |
| P-016 | Completar el backoffice de datos y revisión | Parcial | La consola de revisión de reglas está construida y probada con navegador real: cola de 166 clasificada en cinco pilas, expediente en una pantalla y firma con fundamento obligatorio. Faltan buscar normas y comparar versiones, el resumen del corte antes de publicar y el tablero de calidad con apertura de registros. |
| P-017 | Identidad, privacidad y protección | Parcial | **Criterio 1 cerrado**: el actor sale de una credencial firmada por persona, con roles y vencimiento, revocable, y la bitácora registra cómo se estableció. Falta un proveedor de identidad (OIDC), la política de retención de conversación y los límites de abuso, que dependen del front. |
| P-018 | Hacer obligatoria la integración continua | Parcial | Criterio 3: la protección de rama necesita permisos de administración del repositorio. |
| P-019 | Desplegar revisión y producción | Sin empezar | Todo el despliegue y los probes de readiness/liveness. Causa B. |
| P-020 | Programar monitoreo y entrega de eventos | Parcial | Sólo el disparador horario (causa B). El criterio 2 quedó cerrado: dos disparos simultáneos ya no procesan lo mismo dos veces. |
| P-021 | Medir salud, calidad, costos y nivel de servicio | Sin empezar | No hay tablero, alertas ni panel de gasto. Causa B. |
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
