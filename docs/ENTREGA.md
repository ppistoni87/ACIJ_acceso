# Evidencia final

El paquete (`docs/paquete/00_Claude_Code_Inicio.md`, «Evidencia final
obligatoria») enumera nueve puntos. Este documento dice, para cada uno, dónde
está y cómo verificarlo. Todos los números se recalculan con un comando; ninguno
está escrito a mano.

## 1. Migraciones que levantan un entorno limpio

```bash
alembic upgrade head && alembic check
```

`bn calidad ensayo-actualizacion` lo hace de punta a punta sin intervención:
crea una base descartable, la migra desde cero y opera sobre ella. Si las
migraciones no levantaran un entorno limpio, ese comando fallaría.

## 2. Catálogo SQL con los 83 identificadores

```bash
bn catalogo validar && bn catalogo cargar && bn catalogo conciliar
```

83 identificadores conservados: 52 fichas, 15 excluidas y 6 de descarte o alias.
Ninguna URL inventada; las fuentes sin URL inequívoca conservan su brecha con
una incidencia abierta y un responsable.

- Reporte: `docs/reportes/conciliacion_inventario.md`
- Pruebas: `tests/integracion/test_catalogo.py`

## 3. Filas reales

| | |
| --- | --- |
| Normas | 423.718 |
| Barrios del padrón RENABAP | 6.467 |
| Puntos de atención | 233 |
| Canales | 827 |
| Unidades documentales | 1.562 |
| Relaciones normativas candidatas | 185 |
| Evidencias | 7.274 |

El detalle de qué se cargó, con qué evidencia y qué decisión obligó a tomar cada
fuente está en `docs/operacion/poblacion_real.md`.

## 4. Reporte por fuente y por campo

```bash
bn calidad cobertura     # docs/reportes/cobertura.md
bn calidad backlog       # docs/calidad/estado_backlog.md
```

Las métricas van separadas y no promediadas: cobertura de evaluación y cobertura
sustantiva miden cosas distintas, y un promedio entre las dos suena bien y no
significa nada.

## 5. Dos corridas de ingesta que demuestren idempotencia

```bash
bn ingesta capturar F01
bn ingesta importar-infoleg <captura>   # dos veces
```

| Corrida | Filas leídas | Normas creadas | Ya presentes |
| --- | --- | --- | --- |
| 1 | 428.380 | 423.708 | 3 |
| 2 | 428.380 | 0 | 428.380 |

La segunda no creó nada y no dejó ninguna norma huérfana. Lo mismo vale para el
padrón RENABAP y para los directorios, con sus propias pruebas.

- Pruebas: `tests/integracion/test_importador_infoleg.py`,
  `test_importador_renabap.py`, `test_importador_directorios.py`

## 6. Una actualización que demuestre diff, impacto y evento

```bash
bn calidad ensayo-actualizacion --salida docs/reportes/actualizacion_controlada.md
```

Sobre el texto original y el actualizado del Decreto 1382/2001: 59 unidades
desplazadas —la misma unidad en otra ruta, que no es un cambio de la norma— y 6
cambios sustantivos. Impacto propagado, frescura vencida y un solo evento
después de propagar dos veces.

El reporte dice qué parte del ensayo es real y cuál es controlada.

## 7. Pruebas de integridad, temporalidad, evidencia, no exclusión, API, permisos y recuperación

```bash
pytest -q
```

384 pruebas sobre PostgreSQL real, porque lo que se verifica son restricciones,
disparadores y funciones de la base, y un doble no las ejecuta.

| Dimensión | Dónde |
| --- | --- |
| Integridad | `tests/integracion/test_esquema_integridad.py` |
| Temporalidad y evidencia | `tests/integracion/test_esquema_temporalidad.py` |
| Hechos y no exclusión | `tests/integracion/test_esquema_hechos.py`, `tests/unit/test_reglas.py` |
| API y abstención | `tests/integracion/test_api.py`, `test_hechos_servibles.py` |
| Permisos | `tests/aceptacion/test_casos_aceptacion.py` (rol de base, no convención) |
| Recuperación | `tests/aceptacion/test_respaldo.py`, `docs/reportes/restauracion.md` |

## 8. Los 80 casos de aceptación

```bash
bn calidad trazabilidad --ejecutar --salida docs/calidad/trazabilidad_at.md
```

66 cubiertos y 14 parciales. **Ninguno queda sin ejecutar**; los parciales dicen
qué parte del caso todavía no se ejerce. El comando verifica con pytest que cada nodeid citado
exista: un mapa que cita una prueba renombrada falla en vez de declarar
cobertura inexistente.

```bash
bn calidad consultas --salida docs/calidad/consultas_conversacionales.md
```

98 consultas del conjunto experto —las 80 del paquete más 18 ambiguas,
históricas y adversas—, todas pasan, incluidas las 59 críticas. Una abstención
esperada que se cumple es un caso que pasa: la mayoría de estas consultas
preguntan por datos que el corpus no tiene, y lo que se verifica es que el
backend lo diga en vez de devolver algo parecido.

## 9. OpenAPI, diccionario, runbook, criterios, decisiones y backlog

| Entregable | Dónde | Cómo se regenera |
| --- | --- | --- |
| OpenAPI | `docs/openapi.json` | `bn api openapi` |
| Diccionario de datos | `docs/operacion/diccionario_de_datos.md` | `bn calidad diccionario` |
| Runbook | `docs/operacion/runbook.md` | — |
| Criterios de arquitectura | `docs/adr/` (11 ADR) | — |
| Decisiones de dominio | `docs/decisiones.md` (12 decisiones) | — |
| Backlog con evidencia | `docs/calidad/estado_backlog.md` | `bn calidad backlog` |

El diccionario se genera desde los modelos: el propósito de cada tabla es el
docstring de su modelo, así que vive junto a su definición y no en un documento
aparte que nadie actualiza.

## Lo que no se construyó

El cierre completo —qué queda hecho, qué queda bloqueado, quién lo desbloquea y
con qué comando— está en **`docs/operacion/traspaso.md`**. Empieza por lo único
que bloquea al producto: las 166 reglas que esperan una firma jurídica que el
plan prohíbe expresamente que dé un agente.

El detalle por historia está en `docs/calidad/estado_backlog.md` y
`docs/calidad/trazabilidad_at.md`. En resumen:

- **Fichas de trámite fuera del portal nacional**: el adaptador cubre
  `argentina.gob.ar/servicio/`; las de CABA necesitan uno propio.
- **Directorios en HTML**: sus canales de atención sí se cargan —52 teléfonos,
  correos y formularios con su cita—, pero cada oficina como punto de atención
  con su dirección todavía no.
- **Ferias administrativas y judiciales, y feriados provinciales**: el cómputo
  de días hábiles funciona contra el calendario nacional; los otros calendarios
  que un plazo judicial o provincial necesita no están cargados.
- **Medición de rendimiento bajo carga** (HU-037): el respaldo y la restauración
  verificada están y se corrieron sobre la base real.

Ninguna de esas es una fuente inaccesible: son capacidades que este alcance no
construyó. Las fuentes que sí están bloqueadas —17— figuran con su motivo, su
responsable y su capacidad afectada, y su ingesta está pausada.
