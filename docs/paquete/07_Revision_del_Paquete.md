# Revisión del paquete funcional

Revisión documental del 8 de septiembre de 2026 · Especificación v1.0.

**Resultado:** paquete consistente para iniciar implementación. La revisión verificó los archivos, las referencias internas y la cobertura del inventario. No equivale a haber construido, poblado ni probado el backend futuro.

## Controles ejecutados sobre esta entrega

| Control | Resultado observado |
|---|---|
| JSON de manifiesto, backlog y pruebas | Los tres archivos se analizaron correctamente. |
| Catálogo de fuentes | 83 IDs únicos: F01–F67, D01–D10 y M01–M06. |
| Conciliación con el manual | 52 fichas conservadas, incluidas las seis de descarte/alias; 15 IDs adicionales del anexo preservados. |
| URL de entrada | 70 entradas HTTP(S) con formato válido; 15 fuentes sin URL inequívoca mantienen la brecha. El formato válido no demuestra disponibilidad actual. |
| Historias | 123 IDs únicos: 40 transversales y 83 por fuente/recurso. |
| Criterios de aceptación | 670 criterios; cada historia tiene al menos tres, entregables y evidencia de cierre. |
| Asignación por fuente | Cada ID tiene exactamente una historia y sus tablas destino. |
| Dependencias de tareas | Todas apuntan a historias existentes; no se encontraron ciclos. Los ciclos jurídicos se permiten y tienen tratamiento propio. |
| Referencias y alias | Todos los IDs relacionados y destinos de alias existen en el manifiesto. |
| Diccionario relacional | 53 tablas propuestas; todos los destinos de las fuentes figuran en el modelo. Incluye puentes con FK para evidencia, reglas y derivaciones. |
| Casos de aceptación | 80 IDs únicos con historia referenciada, contexto, acción y resultado esperado. |
| Estado de ejecución | Ningún caso se presenta como ejecutado; ninguna fuente se presenta como cargada por este paquete. |
| Formato de documentos | Tablas Markdown continuas y referencias internas coherentes. |
| Selectores históricos | Sin claves de terceros en las referencias procesables del manifiesto. Validar cada selector al implementarlo. |
| Manual adjunto | La copia dentro del paquete coincide byte por byte con el original aportado. |

## Trazabilidad de los siete campos

| Campo pedido | Historias centrales | Estructura prevista |
|---|---|---|
| Población destinataria | HU-012, HU-013 | Poblaciones, vínculo con beneficio, rol de persona y evidencia. |
| Criterios de aplicabilidad | HU-014, HU-015 | Reglas, AST, parámetros fechados, excepciones y evaluación con desconocidos. |
| Plazo | HU-016, HU-023 | Plazos tipados, eventos, calendarios, zona horaria y períodos aplicables. |
| Criterios de revocación | HU-017 | Reglas diferenciadas de revocación, suspensión, cese, subsanación y rehabilitación. |
| Interdependencias | HU-009, HU-010, HU-026 | Identidad, versiones, relaciones con alcance, referencias pendientes y monitoreo. |
| Beneficio que otorga | HU-011, HU-018 | Beneficios, vínculo normativo, cuantías, modalidades y fórmulas con insumos. |
| Qué no hay que descartar | HU-008, HU-010, HU-015 | Salvaguardas respaldadas, anexos, transitorias, antecedentes, excepciones y versiones. |

HU-012 y HU-022 hacen transversal la evaluación de completitud y el respaldo por campo. Los campos pedidos se proyectan por norma y, cuando corresponde, por cada beneficio/versión: una relación muchos-a-muchos no se reduce a un texto único que mezcle regímenes.

## Brechas que deben resolverse al implementar

- Recuperar identidad/URL de F08, F13, F14, F15, F21, F22, F26, F30, F34, F35, F37, F42, F57, F58, F59. Las historias indican descubrimiento, carga manual o referencia según el caso.
- Ejecutar acceso real y revalidación de cada fuente. Los estados iniciales son planificación; los selectores y observaciones del manual son históricos.
- Verificar el significado jurídico y la temporalidad de las reglas contra capturas fechadas, incluidos F19, F23, F33 y F40. No deducir vigencia por antigüedad o por una sola etiqueta.
- Implementar las migraciones SQL: el diccionario entregado es el diseño de destino, no una base ejecutada.
- Crear fixtures y ejecutar los 80 casos; preparar además el conjunto mínimo de 60 consultas revisadas por dominio. Una pregunta técnica dentro de un caso no sustituye una consulta ciudadana representativa.
- Medir cobertura sustantiva, frescura y capacidades publicables sobre los datos realmente cargados. Un campo revisado sin información no se cuenta como valor sustantivo completo.

Huella SHA-256 del manual de referencia: `4bc0abc69133ef993485587b33602be7e0c488ab7c78848f62b6eeda27942358`.
