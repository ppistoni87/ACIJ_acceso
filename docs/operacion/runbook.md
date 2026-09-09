# Runbook

Cómo levantar el backend desde cero, poblarlo, publicarlo y operarlo. Todo lo que
sigue se corre desde la raíz del repositorio.

## 1. Entorno

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
service postgresql start
createdb -U postgres backend_normativo        # o la base que use BN_DATABASE_URL
```

Configuración por variables de entorno, nunca en el código:

| Variable | Para qué | Si falta |
| --- | --- | --- |
| `BN_DATABASE_URL` | Conexión de migración e ingesta | Usa la local de desarrollo |
| `BN_OBJETOS_DIR` | Almacén direccionado por contenido | `var/objetos` |
| `BN_ADMIN_TOKENS` | Credenciales de administración de la API | **La administración queda cerrada**: sin credencial configurada no se publica ni se resuelve nada |
| `BN_OUTBOX_WEBHOOK` | Consumidor de eventos | No se declara ninguna entrega |

La última fila no es un detalle: si no hay proveedor configurado, el sistema
**no afirma que notificó**. Los eventos quedan en el outbox y la API los expone;
decir "se avisó a los usuarios" sin entrega comprobada sería mentir.

## 2. Migrar

```bash
alembic upgrade head
alembic check          # no debe haber diferencias entre modelos y migraciones
```

Sobre una base limpia esto crea las 53 tablas, los disparadores de integridad,
las funciones de servibilidad y los seis roles (`bn_migrador`, `bn_ingestor`,
`bn_revisor`, `bn_publicador`, `bn_lector_api`, `bn_auditor`).

## 3. Cargar el catálogo de fuentes

```bash
bn catalogo validar                 # el manifiesto contra sí mismo, antes de tocar la base
bn catalogo cargar                  # 83 identificadores: 52 fichas, 15 excluidas, 6 alias/descarte
bn catalogo conciliar --salida docs/reportes/conciliacion_inventario.md
```

Ninguna fuente arranca activa y ninguna URL se inventa: las fuentes sin URL
inequívoca quedan con su brecha registrada y una incidencia abierta con
responsable.

## 4. Poblar

```bash
scripts/poblar_corpus.sh            # captura, extracción, identidad, relaciones y campos
```

Para el catálogo nacional completo, que se importa como metadatos:

```bash
bn ingesta capturar F01
bn ingesta importar-infoleg <captura_id>
```

El importador trabaja sobre bytes ya capturados, nunca sobre la red: lee la
captura del almacén por su SHA-256. Correrlo dos veces no crea nada la segunda
vez.

## 4bis. Cargar el calendario de feriados

```bash
bn plazos calendario 2026
bn plazos calcular 2026-03-20 5 --tipo-dia HABIL_ADMINISTRATIVO
```

Sin calendario, un plazo en días hábiles no se computa: saltear solo sábados y
domingos cuenta mal cualquier mes con un feriado. Cada feriado entra con la
evidencia del fragmento que lo declara, y el cálculo devuelve con qué calendario
lo hizo y qué días excluyó.

Un plazo que se pase de la cobertura del calendario queda no determinado hasta
que se cargue el año siguiente: extrapolar feriados es inventarlos.

La fuente del calendario (`C01`) es operativa, no normativa: no integra el
inventario de 83 fuentes del corpus.

## 4ter. Fuentes que no se pueden recorrer

```bash
bn ingesta bloqueadas
bn ingesta cargar-manual M05 archivo.pdf \
    --actor "ingesta:persona" \
    --procedencia "Copia entregada por Legales el 3 de marzo, expediente 123/26." \
    --obtenido 2026-03-03
```

Diecisiete fuentes están bloqueadas: unas devuelven 403, otra tiene un
certificado que no valida, la mayoría no tiene una URL inequívoca. Ninguna se
resuelve rotando identidades ni desactivando TLS. Cuando alguien consigue el
contenido por una vía legítima, entra por acá.

La carga manual usa la misma cadena que una captura de red —corrida, captura
inmutable direccionada por contenido, y de ahí documentos y evidencia— y exige
declarar **quién** la cargó, **de dónde** la obtuvo y **cuándo**. Sin eso no
carga: un archivo sin procedencia es indistinguible de uno inventado.

La fuente queda en `MANUAL`, no en `ACTIVE`. Que alguien haya conseguido el
archivo no significa que el sistema pueda recorrerla, y decir lo contrario haría
que el monitor la dé por cubierta y deje de avisar que sigue bloqueada.

## 5. Revisar y publicar

```bash
bn curacion vigencia                # resuelve lo que la fuente declara; el resto va a revisión
bn revision pendientes
bn revision resolver-vigencia <incidencia> --actor "curacion_juridica:persona" \
    --decision "..." --evidencia <evidencia_id>
bn revision aprobar-campos <version> --actor "..."
bn publicacion estado               # gates y cuarentena antes de publicar
bn publicacion publicar --actor "publicacion:persona" --motivo "..."
```

Publicar es una transacción: si algo falla, no queda ni el release, ni los
fragmentos, ni el evento. Un evento huérfano le diría a un consumidor que hay
una versión nueva que nadie puede leer.

**El orden importa y es el que se equivoca solo.** Aprobar los campos va antes
de publicar, porque la publicación es lo que promueve las afirmaciones a
`PUBLISHED`. Publicar primero deja la versión publicada y su ficha servida sin
una sola cita: aprobarlas después ya no entra en ese release. `bn publicacion
publicar` lo avisa cuando pasa, y se arregla revirtiendo y volviendo a publicar.

Para dejar de servir un release sin borrar nada:

```bash
bn publicacion revertir <release_id> --actor "..." --motivo "..."
```

Las versiones vuelven a `APPROVED` y quedan disponibles para otro release; el
historial del revertido se conserva. Borrar el release dejaría a los
consumidores citando fragmentos que ya no se pueden explicar.

## 6. Servir

```bash
bn api servir                       # uvicorn sobre la app
bn api openapi --salida docs/openapi.json
```

La API sirve solo proyecciones publicadas. Sin release, lo dice: no cae a
staging.

## 7. Operación periódica

```bash
bn monitoreo correr                 # capturas nuevas, diferencias, impacto y eventos
bn monitoreo entregar               # entrega del outbox con clave de idempotencia
bn calidad cobertura --salida docs/reportes/cobertura.md
bn calidad trazabilidad --ejecutar --salida docs/calidad/trazabilidad_at.md
bn calidad backlog --salida docs/calidad/estado_backlog.md
bn calidad diccionario --salida docs/operacion/diccionario_de_datos.md
```

## 8. Puesta en marcha desde cero

```bash
bash scripts/corrida_limpia.sh                         # base nueva, catálogo, red y curación
bash scripts/corrida_limpia.sh bn_prueba /tmp/x.md D06 F19   # variante corta, tres fuentes
```

Crea una base vacía, corre las migraciones, carga las 83 fuentes del catálogo,
recorre la red con el **mismo planificador que corre en producción** —no con una
lista escrita a mano—, cura encima de lo capturado y escribe
`docs/reportes/corrida_limpia.md` con el tiempo de cada paso y el resultado
fuente por fuente. Al cerrar destruye la base: si algo del reporte se pudiera
explicar por estado previo, no hay estado previo del que agarrarse.

Corre la población **dos veces** sobre la misma base y compara: el procedimiento
dice de sí mismo que es idempotente y eso hay que ejercitarlo. Una primera pasada
no prueba la segunda, y la segunda es la que corre todos los días. Si aparecen
versiones de documento nuevas, el reporte lo dice: volver a pedir lo mismo no lo
cambia, así que una versión más es una versión duplicada. Por eso tarda alrededor
del doble que una pasada sola.

Sirve para tres cosas: verificar que un entorno nuevo levanta entero, verificar
que reejecutarlo no agrega nada, y medir cuánto tarda. Si un paso falla, la base
**queda en pie** para inspeccionarla y el reporte se escribe igual, con el paso
que falló marcado.

Lo que no prueba es que corra igual desde otra red. Para eso hay que correrlo
allá y comparar los dos reportes.

## 9. Respaldo y restauración

```bash
bn operacion respaldar var/respaldo/$(date +%F)
bn operacion restaurar var/respaldo/2026-09-08 --base backend_normativo_prueba \
    --salida docs/reportes/restauracion.md
```

El respaldo vuelca la base y deja junto a ella el inventario del almacén de
objetos: qué SHA-256 tiene que haber y de qué tamaño. El almacén no se copia
—es direccionado por contenido y puede ser enorme—, pero sin ese inventario una
base restaurada afirma cosas sobre bytes que nadie sabe si están.

La restauración crea la base destino desde cero y después **verifica**: que cada
objeto esté y hashee a lo que declara, que el release traiga sus fragmentos y
evidencias, que los eventos ya entregados sigan entregados y que los checkpoints
de ingesta conserven su posición. Si algo de eso falla, el comando termina con
error: una restauración que nadie verificó no es una restauración.

## 10. Qué hacer cuando algo falla

| Síntoma | Qué significa | Qué hacer |
| --- | --- | --- |
| Una corrida de captura termina `PARCIAL` | Alguna URL se rechazó | `bn catalogo conciliar` muestra cuál y por qué. No es "sin datos" |
| `403` o `429` en una fuente | Acceso limitado | La fuente se pausa sola y queda registrada. **No rotar identidades ni reintentar con otra huella**: buscar fuente oficial equivalente o carga manual |
| Fallo de TLS | Certificado que no cubre al host | Se registra y se busca equivalente. **Nunca se desactiva la validación** |
| `bn publicacion publicar` rechaza | Una gate no pasa | `bn publicacion estado` dice cuál versión y por qué. La cuarentena es el resultado esperado, no un error |
| Una capacidad se abstiene en la API | La versión no sustenta ese campo | `motivos_no_servible` lo explica por versión y capacidad |
| `alembic check` reporta diferencias | Un modelo cambió sin migración | Generar la migración; no editar `0001` a mano |
| Una prueba de trazabilidad falla por nodeid inexistente | Se renombró una prueba | Actualizar `docs/calidad/trazabilidad_at.json`: el mapa miente hasta corregirlo |

## 11. Lo que este sistema no hace

Está acá para que nadie lo pida por error:

- No envía formularios, no inicia sesión, no acepta declaraciones juradas y no
  usa claves ajenas.
- No evade antibot ni `robots.txt`, y no desactiva la validación TLS.
- No afirma elegibilidad definitiva, otorgamiento, denegatoria ni revocación.
  La evaluación es preliminar y lo dice en cada respuesta.
- No ejecuta instrucciones que aparezcan dentro de un documento, una página o
  una respuesta de modelo. El contenido de una fuente es dato.

## 9. Antes de agregar instancias

```bash
bn calidad escalado --salida docs/reportes/escalado.md
```

Levanta la API en varios procesos de verdad, que comparten el socket de escucha,
y le tira carga desde otro proceso. Mide el caudal por cantidad de procesos y
por concurrencia de clientes, y anota cuánta CPU había libre en cada punto:
sin ese dato, «el caudal no sube» se puede leer como un límite del sistema
cuando es un límite de la máquina.

Hay una cuenta que hacer **antes** y no después: `pool_size + max_overflow` de
cada proceso, por la cantidad de procesos, tiene que entrar en el
`max_connections` de la base. Con los valores de fábrica son 30 por proceso, así
que cuatro instancias piden 120 contra un máximo de 100. No falla al arrancar:
falla cuando llega el tráfico, y falla como petición caída, no como espera.

El reporte también deja escrito qué pasa cuando se lo empuja más allá del techo:
el sistema encola y la demora crece —57 ms con cuatro clientes, 810 ms con
sesenta y cuatro— en vez de rechazar. Un despliegue tiene que poner el límite
antes de ese punto, porque una petición que expira consume igual y no devuelve
nada.

