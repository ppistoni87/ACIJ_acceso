# Paquete funcional: backend normativo de acceso a derechos

Versión 1.0 · 8 de septiembre de 2026.

**Entregable:** especificación completa para que Claude Code implemente y pueble un backend SQL con evidencia, calidad y monitoreo. No contiene una base ya desplegada ni declara datos de producción cargados.

## Cómo usarlo

Descomprimir el ZIP en el repositorio de trabajo y pedir a Claude Code: **"Leé `00_Claude_Code_Inicio.md` y ejecutá el paquete usando mis agentes disponibles."** El prompt contiene orden de lectura, asignación por capacidades, hitos y evidencia de cierre.

## Contenido

| Archivo | Uso |
|---|---|
| `00_Claude_Code_Inicio.md` | Prompt maestro listo para el orquestador. |
| `01_Especificacion_Backend_Normativo.md` | Alcance, siete campos, calidad, políticas y 40 historias transversales. |
| `02_Historias_por_Fuente.md` | 83 historias individuales, URLs, destinos SQL y pruebas específicas. |
| `03_Modelo_SQL_y_Contratos.md` | Diccionario relacional, restricciones, lógica de reglas y contrato mínimo de API. Diseño a implementar por migraciones. |
| `04_Calidad_y_Pruebas.json` | 80 casos de aceptación con entradas/contexto y resultados esperados; incluye preguntas para evaluación conversacional. |
| `05_Manifiesto_Fuentes.json` | Catálogo procesable, estados iniciales, URLs y referencias de selectores/campos del manual. |
| `06_Backlog.json` | 123 historias procesables por los agentes con dependencias y criterios. |
| `07_Revision_del_Paquete.md` | Verificación de cobertura y consistencia documental de esta entrega. |
| `referencias/Manual_de_ingesta_de_fuentes.pdf` | Manual aportado por el usuario, como referencia histórica. |

## Cobertura y límites explícitos

- **67 IDs originales** preservados: 52 fichas (46 de contenido y seis de descarte/alias), más 15 excluidas en anexo.
- **16 incorporaciones:** D01–D10 para seis normas relacionadas y cuatro documentos/representaciones, y M01–M06 para novedades y contraste oficial.
- **83 fuentes/recursos no son 83 leyes.** Algunas fuentes producen muchas normas, otras son directorios, anexos, alias o canales.
- **15 IDs sin URL concreta en el anexo:** F08, F13, F14, F15, F21, F22, F26, F30, F34, F35, F37, F42, F57, F58, F59. Tienen historias de recuperación/importación/referencia y no se ocultan ni se rellenan con URLs inventadas.
- El manual contiene hallazgos del 31/08/2026. Sus valores, selectores y estados requieren verificación al implementar. No es un certificado de vigencia actual.
- Las siete dimensiones pedidas están modeladas: población, aplicabilidad, plazos, revocación, interdependencias, beneficio y qué no descartar. La última distingue salvaguardas de evaluación y preservación documental.
- Las pruebas del paquete son especificaciones de aceptación, **no resultados de un backend implementado**. La revisión documental valida estructura/cobertura del paquete, no los datos del sistema futuro.

## Población completa: qué significa

Completar la base exige cargar fuentes reales, revisar los siete campos, resolver dependencias, pasar gates y publicar solo capacidades sustentadas. Un campo puede carecer legítimamente de información: se registra el estado y la búsqueda realizada. Eso no cuenta como valor sustantivo completo, y no habilita a inventar requisitos ni excluir personas.

El equipo puede empezar sin otra reunión de arquitectura. Las ambigüedades jurídicas se presentan como registros concretos para revisión, mientras avanza el resto de la implementación.
