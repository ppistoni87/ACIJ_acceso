# Recuperación: léxica contra híbrida

- Corte evaluado: `2a5d835f-c750-4591-b929-b32286540c80`
- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Fragmentos indexados: **33**
- Preguntas respondibles: **27** de 27

## Recall@k

| k | Léxica sola | Híbrida | Diferencia |
| ---: | ---: | ---: | ---: |
| 1 | 18.5% | 37.0% | +18.5% |
| 3 | 51.9% | 66.7% | +14.8% |
| 5 | 55.6% | 74.1% | +18.5% |

El umbral del plan es Recall@5 ≥ 90% sobre preguntas respondibles. Resultado: **74.1%** — no cumple.

## Qué encontró cada una

| Caso | Consulta | Responde | Léxica | Híbrida |
| --- | --- | --- | ---: | ---: |
| RC-001 | ¿Para qué se creó este programa? | `articulo-1` | 1 | 1 |
| RC-002 | ¿Reemplaza al subsidio habitacional anterior? | `articulo-1` | 2 | 3 |
| RC-003 | ¿Quiénes pueden recibirlo? | `articulo-2` | — | — |
| RC-004 | Perdí mi casa en un incendio, ¿me alcanza? | `articulo-2` | 2 | 1 |
| RC-005 | ¿Sirve si me desalojaron? | `articulo-2` | — | — |
| RC-006 | ¿Cada cuánto me lo pagan? | `articulo-3` | 3 | 2 |
| RC-007 | ¿El monto sube con la inflación? | `articulo-3` | 1 | 1 |
| RC-008 | Somos cinco en casa, ¿cobramos más que una persona sola? | `articulo-3` | — | — |
| RC-009 | ¿En qué puedo gastar la plata? | `articulo-4` | — | — |
| RC-010 | ¿Puedo usarlo para pagar la cuota del crédito del IVC? | `articulo-4/parrafo-6` | 2 | 1 |
| RC-011 | ¿Tengo que rendir cuentas de lo que gasté? | `articulo-4/parrafo-7` | 1 | 1 |
| RC-012 | ¿Me pueden dar todo junto en vez de mes a mes? | `articulo-5` | — | — |
| RC-013 | Si agarro el pago único, ¿después puedo seguir cobrando? | `articulo-5/parrafo-9` | 3 | 3 |
| RC-014 | ¿Qué papeles necesito para pedirlo? | `articulo-6` | — | 1 |
| RC-015 | ¿Cuánto tiempo tengo que llevar viviendo en la Ciudad? | `articulo-6/inciso-a-11` | 3 | 1 |
| RC-016 | Sufrí violencia de género, ¿me piden igual la antigüedad? | `articulo-6/inciso-a-11` | 1 | 1 |
| RC-017 | ¿Hay un tope de ingresos para calificar? | `articulo-6/inciso-b-12` | 2 | 1 |
| RC-018 | Si tengo un departamento a mi nombre, ¿puedo pedirlo? | `articulo-6/inciso-c-13` | — | 4 |
| RC-019 | ¿Puedo cobrar esto y otro subsidio de vivienda a la vez? | `articulo-6/inciso-c-13` | 4 | 2 |
| RC-020 | No tengo el DNI, ¿igual puedo entrar? | `articulo-6/parrafo-15` | — | — |
| RC-021 | ¿Por cuánto tiempo me lo dan? | `articulo-7` | — | 2 |
| RC-022 | ¿Se puede renovar cuando se termina? | `articulo-7` | — | 2 |
| RC-023 | Estoy durmiendo en la calle ahora mismo, ¿hay algo urgente? | `articulo-8` | 3 | 2 |
| RC-024 | ¿Me pueden pagar la primera cuota sin tener todos los papeles? | `articulo-8` | 1 | 1 |
| RC-025 | ¿Alguien me acompaña además de darme la plata? | `articulo-9` | 2 | 3 |
| RC-026 | ¿Me ayudan a conseguir trabajo o a anotarme en la escuela? | `articulo-9` | — | 5 |
| RC-027 | Mientras no salga la reglamentación, ¿qué reglas rigen? | `transitoria-21` | — | — |

## Que no se filtre lo que el corte no publica

- «asignación universal por hijo para protección social» devolvió 5 fragmento(s) y no debía devolver ninguno: ese texto no está en el corte publicado.
- «beca de comedor escolar» devolvió 5 fragmento(s) y no debía devolver ninguno: ese texto no está en el corte publicado.
- «asignación por maternidad» devolvió 5 fragmento(s) y no debía devolver ninguno: ese texto no está en el corte publicado.
- «barrios populares del RENABAP» devolvió 5 fragmento(s) y no debía devolver ninguno: ese texto no está en el corte publicado.
