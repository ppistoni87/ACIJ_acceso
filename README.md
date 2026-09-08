# Backend normativo para un sistema conversacional de acceso a derechos

Base SQL, ingesta, curación jurídica, publicación y API para responder consultas
sobre derechos sociales con evidencia localizable — y para **abstenerse cuando
corresponde**, que es la mitad del trabajo.

El paquete funcional que originó este repositorio está en `docs/paquete/` tal
como se recibió. Lo que sigue es lo que se construyó a partir de él.

## Lo primero que conviene saber

Este backend no afirma elegibilidad definitiva, otorgamiento, denegatoria ni
revocación. Devuelve lo que las fuentes dicen, con la cita que lo respalda, y
dice explícitamente qué no sabe. Un campo sin dato no se completa con un cero, un
tope de ingresos no se sirve como el monto que alguien va a cobrar, y no figurar
en un padrón no es una conclusión sobre derechos.

Las razones de cada una de esas decisiones están en `docs/decisiones.md`.

## Empezar

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
service postgresql start
alembic upgrade head
bn catalogo cargar
scripts/poblar_corpus.sh
bn api servir
```

El ciclo completo, con qué hacer cuando algo falla, está en
`docs/operacion/runbook.md`.

## Estado

| | |
| --- | --- |
| Historias del paquete | 123: **31 transversales cerradas**, 9 en curso, 60 fuentes en curso, 18 bloqueadas con motivo, 4 alias, 1 cerrada |
| Casos de aceptación | 80: **61 cubiertos**, 14 parciales, 5 no ejecutados con su motivo |
| Evaluación conversacional | **98 consultas, 98 pasan**; las 59 críticas pasan todas |
| Pruebas | 327, sobre PostgreSQL real |
| Corpus | 423.718 normas · 6.467 barrios · 233 puntos de atención · 827 canales · 7.274 evidencias |

Ninguno de esos números se declara a mano: `bn calidad backlog`,
`bn calidad trazabilidad --ejecutar` y `bn calidad consultas` los recalculan y
fallan si el mapa cita una prueba que ya no existe o una evidencia en una ruta
que se movió.

## Dónde está cada cosa

| Ruta | Qué hay |
| --- | --- |
| `src/backend_normativo/db/` | 53 tablas, vocabularios y la migración de reglas de integridad |
| `src/backend_normativo/ingesta/` | Captura inmutable, adaptadores (HTML, PDF, datasets) e importadores |
| `src/backend_normativo/curacion/` | Segmentación, identidad, relaciones, siete campos y vigencia |
| `src/backend_normativo/reglas/` | AST cerrado y evaluación ternaria |
| `src/backend_normativo/plazos/` | Calendarios jurisdiccionales y cómputo de días hábiles |
| `src/backend_normativo/publicacion/` | Gates, release atómico y cuarentena |
| `src/backend_normativo/api/` | Contrato v1 con abstención explicada |
| `src/backend_normativo/monitoreo/` | Diferencias por unidad, impacto y outbox |
| `src/backend_normativo/operacion/` | Respaldo y restauración verificada |
| `docs/adr/` | Once decisiones de arquitectura con su contexto |
| `docs/decisiones.md` | Doce decisiones de dominio: qué se puede afirmar y con qué respaldo |
| `docs/operacion/` | Runbook, diccionario de datos generado y población real |
| `docs/calidad/` | Trazabilidad de los 80 casos, estado del backlog y conjunto conversacional |
| `docs/reportes/` | Cobertura, conciliación del inventario, ensayo de actualización y restauración |
| `docs/ENTREGA.md` | La evidencia final que pide el paquete, con dónde verificar cada punto |

## Lo que este sistema no hace

- No envía formularios, no inicia sesión, no acepta declaraciones juradas y no
  usa claves ajenas.
- No evade antibot ni `robots.txt`, y no desactiva la validación TLS. Un 403 o un
  certificado que no valida pausan la fuente y quedan registrados.
- No ejecuta instrucciones que aparezcan dentro de un documento, una página o una
  respuesta de modelo: el contenido de una fuente es dato.
- No afirma que notificó a nadie si no hay entrega comprobada.
