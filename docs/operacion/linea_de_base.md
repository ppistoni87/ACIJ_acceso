# Acta de línea de base

Evidencia de P-001 del plan integral. Lo que se registra acá es lo observado en
este entorno el 9 de septiembre de 2026, no lo que el backlog anterior declara.

- **Repositorio:** `ppistoni87/ACIJ_acceso`
- **Rama:** `claude/backend-normativo-user-stories-41z94i`
- **Commit auditado:** `1c19c62`
- **Entorno:** contenedor efímero, Python 3.11.15, PostgreSQL 16 local

## Estado del repositorio

| Qué | Observado |
| --- | --- |
| Árbol de trabajo | Limpio: cero archivos sin commitear |
| Stash | Vacío |
| Ramas locales | Una: la de trabajo, alineada con su remota |
| Ramas remotas | Una, y `origin/HEAD` apunta a ella; no hay rama estable |

**El trabajo local que el plan menciona no está en este entorno.** El plan
registra «trabajo de front, endpoints de chat/revisión, RAG, seguridad,
almacenamiento y CI en una rama local, sin commit». Acá no hay nada de eso: ni
sin commitear, ni en otra rama, ni en el stash. O vivía en un contenedor que se
reinició —y entonces se perdió, porque lo no commiteado no sobrevive— o está en
otra máquina y hay que pushearlo antes de poder integrarlo.

No se puede conciliar lo que no se ve. El criterio 1 de P-001 —preservar cada
cambio o descartarlo con motivo— queda **abierto** hasta que ese trabajo
aparezca en el remoto. Lo que este acta sí cierra es que en `1c19c62` no hay
trabajo pendiente de integrar.

## Pruebas

Se corrió la suite dos veces, y la diferencia entre las dos es el hallazgo
principal de esta línea de base.

| Corrida | Recogidas | Aprobadas | Falladas | Salteadas | Código de salida |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sin PostgreSQL, antes del arreglo | 921 | 479 | 0 | **442** | **0 (verde)** |
| Sin PostgreSQL, después del arreglo | 921 | 479 | 437 errores | 5 | 1 (rojo) |
| Con PostgreSQL 16 | 921 | **921** | 0 | 0 | 0 |

Las 921 pruebas aprobadas son reales, y lo son **solo con una base disponible**.
Sin base, cuarenta y ocho por ciento de la suite se salteaba y `pytest` terminaba
en cero: un CI sin servicio de PostgreSQL habría dado verde sobre un sistema
mitad sin probar. Eso es lo que el plan llama «pruebas de base aprobadas por
omisión», y estaba.

Solo unitarias, sin base: **413 aprobadas**, que coincide con el número que el
plan registró al inspeccionar este mismo commit.

### Qué se cambió

`tests/conftest.py` ahora **falla** cuando no puede conectarse a PostgreSQL, en
lugar de saltear. Quien quiera correr solo las unitarias lo pide con
`BN_PRUEBAS_SIN_BASE=1`, y entonces el salteo es una decisión con nombre. El CI
además corre `scripts/verificar_salteos.py` sobre el reporte JUnit: cualquier
prueba salteada por un motivo que el proyecto no declaró hace fallar el trabajo,
con el inventario de cuáles son.

## Inventario conciliado

El denominador versionado que pide P-001 ya existe y se genera:
`docs/reportes/conciliacion_inventario.md`, producido por `bn catalogo conciliar`
contra la base. Distingue los denominadores que el plan exige no confundir —84
fuentes en el catálogo, 80 canónicas, 4 alias, 76 URLs, 53 documentos capturados,
423.718 normas identificadas, 16 beneficios— y lista los 67 identificadores
originales más las incorporaciones trazables a su origen.

Dos salvedades sobre ese reporte: es de este entorno, así que hay que
regenerarlo contra la base operativa cuando exista, y quedó anterior a la fuente
derivada `N01` de normas citadas, que aparecerá al regenerarlo.

## Herramientas

| Control | Resultado |
| --- | --- |
| `ruff check` | Sin hallazgos |
| `ruff format --check` | Sin diferencias |
| `alembic check` | Sin deriva entre modelos y migraciones |

## Lo que esta línea de base no acredita

- **No hay base remota.** La de este contenedor es local y efímera; se perdió en
  un reinicio durante la sesión y se volvió a levantar vacía.
- **No hay despliegue.** Ninguna URL, ninguna API corriendo fuera de acá.
- **No hay CI ejecutado.** El workflow queda escrito en este commit; su primera
  ejecución la produce el push, y esa ejecución es la evidencia, no el archivo.
- **No hay firma jurídica.** Las reglas curadas siguen en CANDIDATE.
- El corpus reproducible y los reportes de calidad son de este entorno y esta
  red. Valen como procedimiento cronometrado; no como prueba del destino
  operativo.
