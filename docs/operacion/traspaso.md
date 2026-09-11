# Traspaso: qué queda hecho, qué queda bloqueado y quién lo desbloquea

Este documento cierra el trabajo que se pudo hacer sin dos cosas que no se
pueden fabricar desde acá: **una firma jurídica** y **una cuenta de nube**.
Todo lo demás está construido, probado y en la rama.

## Lo primero, porque es lo único que bloquea el producto

**166 reglas esperan que una persona con competencia jurídica las firme.**

No están sin firmar por falta de herramienta. El expediente está armado regla
por regla, la consola existe, los comandos exigen actor y fundamento, y la
credencial ata cada firma a una persona verificable. Están sin firmar porque el
plan lo dice con todas las letras en el criterio 2 de P-010: **«no se aprueban
en lote por un agente»**. Aprobarlas desde acá pondría en la bitácora un actor
que no revisó nada y haría que la API empiece a contestar «te corresponde» sobre
esa base.

De esa firma cuelgan: los 135 campos en `PENDIENTE` de las siete dimensiones, las
dos capacidades que hoy sirven cero —evaluación preliminar y plazo—, el acta
HU-036, y por dependencia P-023 y P-024.

### Cómo se hace

```bash
bn operacion emitir-credencial --actor "curacion_juridica:nombre" --rol revisor --dias 30
bn api servir
# después, en el navegador: http://…/backoffice/reglas
```

La cola llega clasificada en cinco pilas que no se revisan igual:

| Pila | Cuántas | Qué hay que decidir |
| --- | ---: | --- |
| `CONDICION_EJECUTABLE` | 72 | Confirmar que la condición dice lo que dice la norma |
| `SIN_CONDICION_EJECUTABLE` | 42 | Si la condición se puede escribir o la regla es informativa |
| `NO_ES_CONDICION_SOBRE_LA_PERSONA` | 25 | No decide acceso: revisar como informativa |
| `CONDICION_CON_UMBRAL_SIN_VALOR` | 20 | La condición existe, su umbral no tiene valor |
| `CONDICION_EN_CATEGORIA_QUE_NO_DECIDE_ACCESO` | 7 | Tiene condición donde no resuelve elegibilidad |

Las 166 están ubicadas en su artículo: ninguna queda sin ubicar en el texto.
Aprobar **no** publica: eso es un corte, y lo firma otra persona con otro rol.

## Lo segundo: una cuenta de nube con titular y pagador

Una sola decisión destraba cinco historias del plan.

| Historia | Qué falta | Sin eso |
| --- | --- | --- |
| P-004 | Bucket privado y política de retención | Los originales viven en el volumen del contenedor |
| P-019 | Cloud Run, secretos, identidad de servicio | Nada desplegado, ninguna URL |
| P-020 | Cloud Scheduler cada hora | El ciclo corre cuando alguien lo llama |
| P-021 | Tablero, alertas, panel de gasto | Sin tráfico que instrumentar |
| P-022 | Retención de Neon, RPO ≤ 24 h y RTO ≤ 4 h medidos | El plan dice que sin esto no pasa el gate |

Con esa cuenta corre además lo que le falta a P-005: la carga del corpus contra
Neon. Hoy el esquema está aplicado allá y vacío, porque este contenedor no tiene
egreso TCP al 5432.

**Decisión que conviene tomar antes de provisionar:** la región. El acta de Neon
dejó anotado que `us-east-2` se heredó del proyecto y no se eligió, y que mover
una base vacía cuesta menos que mover una con datos. Sigue vacía. La
recomendación medida está en el informe de estado: todo junto en `us-east4`,
pegado a Neon, porque cada consulta a la base cuesta ~2 ms en vez de ~110 ms y
las usuarias pagan la latencia una vez por mensaje, no una por consulta.

## Lo tercero: dos cosas chicas que necesitan permisos que el agente no tiene

- **Protección de rama** (P-018, criterio 3): hacer obligatorios los checks de CI
  para integrar. Es una casilla en la configuración de GitHub.
- **Rotar la contraseña de `neondb_owner`**: circuló por el chat de la sesión. No
  está en el repositorio ni en ninguna imagen, pero es el rol que aplica DDL.

## Qué queda construido

Las cifras de esta tabla son una foto al 10.09.2026. Este proyecto ya se
tropezó una vez con un número escrito a mano que envejeció en silencio —el acta
de Neon declaraba una cabeza de migraciones vieja y este mismo informe dio por
pendiente un trabajo ya hecho—, así que abajo está el comando que regenera cada
una. Si no coinciden, mandan los comandos.

| | | Se regenera con |
| --- | ---: | --- |
| Pruebas | 1.124, sin salteos sin declarar | `pytest -q -rs` |
| Migraciones | 15, aplicadas también en Neon | `scripts/estado_neon.py` |
| Sondas de permisos | 23, sin discrepancia | `scripts/verificar_permisos.py` |
| Decisiones de dominio registradas | 85 | `docs/decisiones.md` |
| Normas en el catálogo nacional | 423.718 | `bn calidad cobertura` |
| Beneficios curados desde el texto | 16 | `bn curacion beneficios` |
| Reglas extraídas con su artículo | 176 | `bn revision reglas` |
| Fuentes que sirven | 44 de 55 ingestables | `bn calidad fuentes` |

Y lo que el sistema **se niega** a hacer, que es la parte que más costó:

- No aprueba reglas en lote.
- No publica como texto de la ley lo que un organismo publica sobre un derecho.
- No carga un teléfono bajo un organismo que no se declaró.
- No completa una característica telefónica que falta.
- No convierte un 403 en «sin datos» ni rota identidades para evadirlo.
- No da por vigente un importe porque sea el último que descargó.
- No cita un número que su propia cita no contiene.

## Cómo verificar todo esto sin creerme

```bash
bash scripts/corrida_limpia.sh      # base vacía -> corpus, con reporte
pytest -q -rs                        # 1.124 pruebas, los salteos con motivo
bn calidad fuentes                   # cada fuente contra la historia que declara
bn calidad backlog                   # cada historia contra su evidencia en el repo
NEON_DSN=... python scripts/estado_neon.py       # la base gestionada contra el código
NEON_DSN=... python scripts/verificar_permisos.py  # 23 sondas de permisos
```

Los informes generados (`docs/reportes/`) no tienen cifras escritas a mano:
salen de esos comandos, y regenerarlos sin cambios da el mismo texto. La tabla
de arriba sí es una transcripción —por eso lleva al lado el comando que la
desmiente.

## Lo que no se construyó, y por qué

- **P-013, generación de respuestas con citas**: no hay proveedor de modelo
  configurado. La política de abstención sí está: `bn_motivos_no_servible()`
  devuelve el motivo tipado por el que algo no se puede servir.
- **P-015, front ciudadano**: depende de P-013. No existe.
- **P-012 al 90 %**: la recuperación híbrida está construida y medida —Recall@5
  74,1 % contra 0 % de la léxica sola— y no llega al umbral. La causa está
  medida y corregida en el origen, pero el corte publicado se armó con la
  extracción vieja; volver a medir sobre un corte limpio exige re-curar las citas,
  que es trabajo jurídico.
- **Un adaptador de boletines**: M01 y M03 declaran `normas` y
  `relaciones_normativas`, que no salen de partir una página en secciones. Son
  las dos únicas fuentes capturadas que ningún adaptador procesó, y el informe
  las separa de las que sí se extrajeron pero no dejaron filas.

## Una cosa que el informe marca y no es un error de programa

`bn calidad fuentes` lista seis fuentes «capturadas, extraídas y sin destino»:
respondieron 200, se extrajeron y no dejaron una fila donde su historia dice que
deberían. En dos de ellas —F18 y F32— miré la página: F32 es el widget de turnos
(cuatro botones: reservar, modificar, cancelar, comprobante) y F18 es un párrafo
que describe Progresar. Ninguna de las dos tiene un teléfono, una dirección ni un
horario, así que el catálogo les declara `canales` y la página no los contiene.

No las reclasifiqué. La diferencia entre «el extractor no lo vio» y «la página no
lo tiene» decide si esto es trabajo de ingesta o una corrección del catálogo, y
esa es una revisión de las seis, una por una, con la página al lado. Dejarlas
visibles y mal atribuidas cuesta una revisión; esconderlas detrás de un estado
nuevo que yo inventara cuesta no volver a mirarlas.
