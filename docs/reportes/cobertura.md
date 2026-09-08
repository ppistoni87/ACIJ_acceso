# Cobertura y calidad del corpus

Las métricas se informan por separado porque miden cosas distintas.
Promediarlas produce un número que suena bien y no significa nada.

## (a) Cobertura de fuentes

| Concepto | Cantidad |
|---|---:|
| Fuentes en el catálogo | 84 |
| Con al menos una captura | 63 |
| Con documentos extraídos | 55 |
| Sin URL conocida | 15 |
| Con acceso bloqueado o limitado | 2 |
| Pendientes de capturar | 21 |

Una fuente bloqueada no cuenta como poblada.

## (b) y (c) Campos evaluados frente a campos con valor

| Concepto | Valor |
|---|---:|
| Versiones normativas | 12 |
| Evaluaciones esperadas (siete campos por versión) | 84 |
| Evaluaciones registradas | 84 (100.0%) |
| Campos con valor sustantivo validado | 4 (4.76%) |

| Estado del campo | Cantidad |
|---|---:|
| INFORMADO | 4 |
| NO_INFORMADO_EN_FUENTES_REVISADAS | 36 |
| PENDIENTE | 44 |

Un campo evaluado sin información no cuenta como valor sustantivo. Cien por
ciento de evaluación con cero valor sustantivo es un resultado posible y
honesto: significa que se buscó en todas las fichas y todavía no hay nada
aprobado para publicar.

## (e) Conflictos abiertos por severidad

| Severidad | Abiertos |
|---|---:|
| HIGH | 34 |
| INFO | 4489 |
| LOW | 19 |
| MEDIUM | 48 |

## (f) Dependencias pendientes

167 referencias normativas citadas que todavía no se resolvieron contra el corpus.

## (g) Fidelidad de extracción

Señal técnica observable, separada del juicio sobre el contenido.

| Métrica | Valor |
|---|---:|
| score promedio | 0.2909 |
| score minimo | 0.0 |
| versiones bajo umbral | 38 |

## (h) Capacidades publicables

Versiones que hoy pueden servirse por capacidad. Una norma con monto
desconocido puede sustentar una explicación general y aun así abstenerse
de responder cuánto se cobra.

| Capacidad | Versiones servibles |
|---|---:|
| IDENTIFICACION | 1 |
| DESCRIPCION_GENERAL | 1 |
| REQUISITOS | 1 |
| EVALUACION_PRELIMINAR | 0 |
| MONTO | 1 |
| PLAZO | 0 |
| CANAL | 1 |
| EXPLICACION_HISTORICA | 1 |

## Corpus cargado

| Tabla | Filas |
|---|---:|
| capturas | 84 |
| documentos | 62 |
| documento_versiones | 63 |
| unidades_documentales | 1562 |
| evidencias | 7433 |
| normas | 423718 |
| norma_versiones | 12 |
| relaciones_normativas | 185 |
| beneficios | 1 |
| afirmaciones | 944 |
| releases | 1 |

