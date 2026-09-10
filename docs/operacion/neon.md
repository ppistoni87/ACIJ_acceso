# Acta de la base gestionada (Neon)

Evidencia de P-002 y P-003 del plan integral. Registra lo verificado el 9 de
septiembre de 2026 contra la base real, no lo que la configuración declara.

- **Proveedor:** Neon (PostgreSQL gestionado)
- **Proyecto/endpoint:** el registrado en `.env.local`, región `us-east-2` (AWS).
  El identificador del endpoint no se versiona: este repositorio es público y
  publicarlo sería regalar la mitad de la credencial.
- **Base:** `neondb`
- **Motor:** PostgreSQL **18.6**
- **Cabeza de migraciones aplicada:** este acta ya no la declara. Se pregunta:

  ```
  NEON_DSN=... python scripts/estado_neon.py
  ```

  Este acta declaraba `0008_el_ingestor_no_resuelve` escrito a mano. Después se
  aplicaron tres migraciones más y el número quedó viejo sin que nada avisara,
  hasta que un informe de estado lo leyó y dio por pendiente un trabajo que ya
  estaba hecho. `scripts/estado_neon.py` compara la cabeza de la base contra la
  que el código espera y comprueba, migración por migración, que su efecto esté
  en el esquema y no solo su fila en `alembic_version` —una migración aplicada
  por HTTP en lotes es exactamente donde una cosa puede pasar sin la otra—. Sale
  distinto de cero si no coinciden.

La cuenta y el proyecto los creó la persona que opera; el agente recibió la
cadena de conexión ya provista. Ninguna credencial vive en el repositorio.

## Cómo se aplicó el esquema

Este contenedor no tiene egreso TCP al puerto 5432: los tres registros A del
endpoint responden con timeout y la política del proxy declara las bases por
TCP crudo como no soportadas. No se rodeó esa política. Neon publica además un
endpoint HTTP oficial sobre el mismo motor —`https://<endpoint>/sql`, puerto
443, TLS validado de punta a punta—, y por ahí viajaron las sentencias.

El esquema se generó con el modo sin conexión de Alembic (`alembic upgrade head
--sql`), que produce exactamente el mismo SQL que aplicaría una corrida normal,
y se aplicó con `scripts/sql_neon.py --transaccion`: las 246 sentencias en una
sola transacción, todas o ninguna. Un esquema a medio aplicar no sirve.

Donde haya conexión TCP —Cloud Run, una laptop, el runner de CI— se usa
`alembic upgrade head`. Este camino no lo reemplaza; lo suple donde no hay
puerto.

## Que el esquema sea el mismo, comprobado

Comparación objeto por objeto entre el PostgreSQL 16.13 local, donde corren las
pruebas, y el 18.6 de Neon:

| Objeto | Local (16.13) | Neon (18.6) |
| --- | --- | --- |
| Tablas | 54 | 54 |
| Vistas | 0 | 0 |
| Índices | 207 | 207 |
| Disparadores propios | 19 | 19 |
| Funciones propias (sin extensión) | 14 | 14 |
| Restricciones `CHECK` | 152 | 152 |
| Claves foráneas | 117 | 117 |
| Claves primarias | 54 | 54 |
| Restricciones de disparador | 14 | 14 |
| Restricciones `UNIQUE` | 24 | 24 |
| Restricciones de exclusión | 1 | 1 |
| Restricciones `NOT NULL` catalogadas | 0 | 292 |

El total crudo de `pg_constraint` da 362 contra 654, y esa diferencia no es una
diferencia de esquema: desde PostgreSQL 17 las restricciones `NOT NULL` se
catalogan como filas propias (`contype = 'n'`). Descontadas esas 292, cada tipo
coincide exactamente. Las 25 funciones de más en Neon son de `pgcrypto` y
`btree_gist` en versión más nueva; las propias son las mismas 14.

Las extensiones que el esquema necesita están disponibles: `pgcrypto`,
`btree_gist`, y también `vector`, `pg_trgm` y `unaccent`, que hacen falta para
el RAG híbrido más adelante.

## Aislamiento de permisos

La migración 0002 crea seis roles de grupo sin login —`bn_migrador`,
`bn_ingestor`, `bn_revisor`, `bn_publicador`, `bn_lector_api`, `bn_auditor`— y
les otorga permisos. Sobre eso se crearon dos identidades con contraseña:

| Identidad | Grupo | Para qué |
| --- | --- | --- |
| `neondb_owner` | propietario | Aplica DDL. Es la única que Alembic usa. |
| `bn_api` | `bn_lector_api` | La API: solo lectura, y sin staging. |
| `bn_ingesta` | `bn_ingestor` | La ingesta: escribe descubrimiento, no publica. |

Las contraseñas se generaron con `secrets.token_urlsafe` y viven en `.env.local`,
que git ignora y que el contexto de la imagen excluye. En la nube van al gestor
de secretos.

`scripts/verificar_permisos.py` prueba contra la base que cada rol pueda lo que
debe y nada más. Las sondas llevan `WHERE false`: PostgreSQL verifica el permiso
igual y no se cambia ni una fila, así que la verificación es inocua incluso
contra producción. Resultado sobre Neon: **22 sondas, 0 discrepancias**.

```
BN_DATABASE_URL_API        leer normas/reglas/parámetros: permitido
                           auditar su consulta: permitido
                           leer capturas, afirmaciones, incidencias, corridas: denegado
                           escribir normas, reglas, releases: denegado
BN_DATABASE_URL_INGESTA    leer y escribir capturas, candidatas, auditoría: permitido
                           publicar un release, aprobar una regla, resolver una incidencia: denegado
```

### Lo que la verificación encontró

La primera corrida dio 17 de 18. El ingestor podía marcar una incidencia como
RESUELTA. El comentario que encabeza los permisos de la 0002 dice «el ingestor
escribe descubrimiento y candidatos; no publica ni resuelve», pero el GRANT
otorgaba `INSERT, UPDATE` sobre `incidencias_revision`, y con el UPDATE cerrarla
era posible. La diferencia no se veía leyendo el SQL —la tabla está en una lista
de doce— y apareció al probar contra la base.

Las dos únicas sentencias que resuelven una incidencia viven en `curacion/`, que
es trabajo de revisor; ninguna ruta de ingesta actualiza la tabla, solo inserta.
La migración `0008_el_ingestor_no_resuelve` revoca ese UPDATE y deja el INSERT.
El invariante quedó como prueba de aceptación contra la base
(`test_el_rol_ingestor_no_puede_resolver_una_incidencia`), no solo como sonda.

## Lo que este acta no acredita

- **No hay datos.** El esquema está aplicado y vacío: cero normas, cero
  capturas. La carga del corpus es P-005 y todavía no corrió.
- **No hay nada desplegado.** Ninguna aplicación apunta todavía a esta base.
- **La región no se eligió con criterios medibles.** `us-east-2` es la que traía
  el proyecto. El plan pide que la región se cierre en G0 con criterios
  medibles; eso sigue abierto, y mover una base con datos cuesta más que
  moverla vacía.
- **Retención, respaldos y punto de recuperación no están decididos.** Neon trae
  un historial por defecto; nadie lo revisó contra un objetivo.
- **No hay lista de direcciones permitidas ni límite de conexiones por rol.**
  Cualquiera con la cadena de conexión entra.
- **El agrupador (`-pooler`) no se midió.** Se eligió para procesos de vida
  corta por criterio, no por medición; `pool_size` sigue en el valor que se
  midió contra el PostgreSQL local.
- **El motor no es el que prueban las pruebas.** El CI corre contra PostgreSQL
  16 y Neon sirve 18.6. El esquema coincide, pero ninguna prueba corrió todavía
  contra 18.
