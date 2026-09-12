# ACIJ Acceso

# Plan integral del proyecto

Versión 1.1 · 12 de septiembre de 2026

Plan de implementación y aceptación. Actualización: incorporación del chatbot ampliado a partir del análisis de Boti. Estado de esta entrega: documentación y backlog actualizados; capacidades pendientes de implementación, integración y aceptación.

**Cambio incorporado:** front web conversacional propio de ACIJ, conversación con contexto, desambiguación de beneficios, modelos intercambiables actuales, verificación de respuestas y limpieza de lenguaje. Se incorporan atención humana y extensiones opcionales de audio, lectura de documentos y novedades dentro de la web, con dos entregas verificables. El plan pasa de 24 a 38 historias de producto, conservando el backlog de fuentes. Por indicación expresa de Pedro, WhatsApp queda fuera del alcance.

**Cómo leer esta versión:** E1 entrega el front web conversacional completo; E2 añade modalidades opcionales dentro de ese mismo front. Las secciones 08 y 09 contienen el diseño funcional y conversacional, incluida la especificación de interfaz en 08.7; el Anexo B incorpora P-025 a P-038. El presupuesto y calendario anteriores se conservan como referencia y se actualizan en las secciones 11 y 12.

## 01. Resultado contratado y definición de terminado

Construir y poner en operación **ACIJ Acceso**: un sistema conversacional de acceso a derechos que consulte un corpus normativo persistente, explique con citas verificables y permita a especialistas controlar qué información se publica. El producto comprende la cadena completa desde la fuente hasta la respuesta y su mantenimiento.

Este documento cierra la planificación. **No certifica una base provisionada, un despliegue activo ni la aprobación jurídica de las reglas.** Los estados observados se detallan a continuación. Las métricas y plazos de este plan son objetivos propuestos, sujetos a las pruebas indicadas.

La entrega se considera terminada cuando concurren siete resultados:

- Base PostgreSQL administrada, poblada con datos reales, roles separados y persistencia demostrada después de reemplazar la aplicación.
- Inventario conciliado, siete dimensiones por norma/beneficio y originales recuperables; las brechas del alcance quedan resueltas o motivan una modificación formal del alcance.
- Chat web integrado al backend, con generación real, recuperación, citas, aclaraciones y evaluación determinista de condiciones cuando corresponde.
- Backoffice para revisar datos, resolver dependencias, aprobar reglas y publicar cortes consistentes con auditoría.
- URLs HTTPS de revisión y producción; CI/CD, planificador y monitoreo instalados y probados.
- Validación jurídica y pruebas de calidad, seguridad, carga, accesibilidad y utilidad sobre el recorrido completo.
- Recuperación de base y documentos ensayada; cuentas institucionales, responsables de operación y traspaso documentado.

**Qué significa 100%:** cobertura de los componentes y del inventario acordado en G0. No significa recopilar automáticamente toda la legislación argentina, garantizar cero errores futuros ni completar hechos que una fuente no publica. Cada nueva dependencia relevante amplía el inventario mediante control de cambios. Una fuente bloqueada sigue en el denominador de adquisición; no desaparece para mejorar la métrica.

**Alcance funcional inicial:** información normativa y operativa de los beneficios del corpus, incluyendo las cadenas señaladas para F33, F19, F23 y F40. Consulta ciudadana y de personas acompañantes; operación por curadores, revisores y publicadores. La evaluación orienta de manera preliminar: no sustituye la decisión de la autoridad competente.

**Alcance ampliado v1.1:** E1 comprende el front web conversacional propio, adaptable a computadora y celular, con contexto, orientación preliminar, lenguaje claro, fuentes y derivación. E2 incorpora entrada de audio y lectura de respuestas, explicación de PDF/imágenes y novedades voluntarias, todo dentro del mismo front. WhatsApp está excluido por decisión del usuario, al igual que SMS, mensajes por correo y notificaciones push. El proyecto no depende de una cuenta, número telefónico ni proveedor de mensajería para la consulta ciudadana.

**Límites que se mantienen:** el sistema no presenta trámites ni recursos, no acepta declaraciones juradas, no otorga ni deniega prestaciones y no crea un expediente personal. No exige identificación de menores. El acceso a sistemas transaccionales de organismos requeriría un alcance y convenio específico. Leer un documento voluntariamente aportado no lo incorpora al corpus ni habilita un expediente.

## 02. Punto de partida verificado

Fecha de corte: **9 de septiembre de 2026**. Referencia de código: repositorio `ppistoni87/ACIJ_acceso`, rama `claude/backend-normativo-user-stories-41z94i`, commit `1c19c62`. El plan preserva la inversión en Python, FastAPI, SQLAlchemy y Alembic.

| Elemento | Evidencia y estado al cerrar el plan |
| --- | --- |
| Código base | Commit inspeccionado y disponible en GitHub. Existe código de ingesta, curación, reglas, calidad, publicación, API y monitoreo. |
| Modelo SQL | El diccionario versionado declara 53 tablas y 513 columnas. Es una definición de esquema; no demuestra que una base remota esté poblada. |
| Corpus reproducible | El reporte de corrida limpia del 09/09 registra unos 11 minutos. Es evidencia histórica de ese entorno y esa red; debe repetirse sobre el destino operativo. |
| Inventario y backlog | El paquete original contiene 83 recursos y 123 historias: 40 transversales y 83 por fuente. Recursos, normas, artículos y beneficios son denominadores distintos. |
| Revisión jurídica | El expediente versionado registra 166 reglas CANDIDATE; 67 sin condición ejecutable. Debe reconciliarse al cargar la base y resolverse en P-010. |
| Pruebas | La sesión registró 413 pruebas unitarias aprobadas en la línea de base. Las 921 pruebas informadas por el usuario no constituyen una ejecución integral vigente sobre Neon. |
| Neon | Conexión confirmada. La consulta de proyectos de la organización accesible devolvió una lista vacía. Aún no hay un proyecto de este servicio provisionado. |
| Nuevos cambios locales | Hay trabajo de front, endpoints de chat/revisión, RAG, seguridad, almacenamiento y CI en una rama local. Está sin commit y sin validación integral; requiere revisión e integración. |
| Operación | No se ha acreditado URL pública, API desplegada, CI ejecutándose, scheduler instalado o restauración del destino operativo. |

No se transfiere automáticamente el estado «CERRADA» del backlog anterior al producto desplegado. P-001 reconciliará cada historia con su evidencia técnica y operativa actual.

**Brechas que ya deben formar parte de la implementación:** eliminar supuestos de localhost del bootstrap; impedir que las pruebas de base se aprueben por omisión; completar el tratamiento de reglas sin condición; hacer coherente aprobar con la marca de revisión; verificar permisos reales de las funciones de consulta; y probar que un nuevo release conserve las versiones publicadas que siguen siendo pertinentes.

Las historias **P-001 a P-038** amplían e integran el backlog existente; no reemplazan las 83 historias de fuente ni renumeran HU-001 a HU-040. Las referencias históricas son puntos de partida, no certificaciones de vigencia jurídica actual.

**Revisión documental al 12/09/2026:** se volvieron a consultar el README y pyproject.toml de la rama del repositorio. La configuración publicada conserva Python >=3.11, FastAPI, Pydantic 2, SQLAlchemy, Alembic y fastembed opcional. La lectura detecta evolución posterior de archivos, pero no constituye ejecución de pruebas ni verificación de una infraestructura activa. Se mantiene 1c19c62 como referencia histórica; P-001 debe fijar el SHA real y reconciliar todos los estados antes de implementar.

## 03. Arquitectura objetivo y decisiones técnicas

**Base propuesta:** conservar FastAPI/SQLAlchemy/Alembic, usar PostgreSQL administrado en Neon y desplegar el contenedor de aplicación en Cloud Run. La ampliación añade LangGraph para el estado conversacional y adaptadores de modelos dentro de la arquitectura Python existente. El front se sirve inicialmente junto a la API bajo un mismo origen. Esta arquitectura es una propuesta de ejecución; Cloud Run y su cuenta de facturación siguen por configurar.

| Capa | Solución y responsabilidad |
| --- | --- |
| Interfaz ciudadana | Front web conversacional propio: escritura libre, fuentes desplegables, hechos corregibles y próximos pasos. Adaptable a móvil y computadora; sin cuenta ni teléfono obligatorios. Reutilizar el front iniciado y completar P-015/P-032. |
| Interfaz de equipo | Revisión jurídica, siete dimensiones y tablero en rutas administrativas separadas, con roles y autenticación. |
| API | FastAPI, contratos tipados, autenticación administrativa, orquestación de consulta y motor determinista. El cliente no recibe credenciales de base o del modelo. |
| Datos | Lakebase Postgres mediante Neon: tablas del dominio, auditoría, versiones, eventos, FTS en español y pgvector. Alembic como única autoridad de migraciones. |
| Documentos | Bucket persistente privado en Cloud Storage, con hashes y referencias desde SQL; respaldos separados. El disco del contenedor sólo sirve para temporales. |
| RAG | Recuperación híbrida textual y vectorial, filtros jurídicos y de permisos, contexto trazable, generación mediante proveedor configurado y validación de citas. |
| Conversación v1.1 | LangGraph con pasos tipados, memoria mínima con vencimiento, selección de herramientas permitidas y validación antes de emitir. Un workflow acotado; no se requiere una infraestructura multiagente. |
| Modalidades del front | Texto como acceso principal; voz y OCR opcionales producen entradas normalizadas dentro de la web, sin duplicar la lógica jurídica. Novedades consultables en la propia interfaz. |
| Procesamiento | Cloud Run Jobs para ingesta, indexación y mantenimiento; Cloud Scheduler dispara el ciclo horario. La API no ejecuta scraping largo dentro de una consulta. |
| Identidad | Proveedor OIDC para equipo, sesiones seguras y roles de aplicación; MFA para administradores. Visitante anónimo por defecto, sin expediente personal. |
| Operación | GitHub Actions, imágenes por digest, secretos administrados, logs estructurados, métricas, alertas, respaldo y restauración. |

**Flujo de datos:** la ingesta conserva originales y extrae versiones; calidad y revisión autorizan hechos; un publicador produce el corte; los índices recuperan únicamente contenido habilitado. La API elige entre cálculo tipado y explicación RAG. Cada respuesta conserva el corte y las evidencias que utilizó.

**Conexiones:** tráfico de aplicación por endpoint agrupado; migraciones, dumps y operaciones que requieren estado de sesión por endpoint directo. Neon utiliza PgBouncer en modo transacción: los límites de clientes no equivalen a capacidad ilimitada de transacciones. [S1]

Presupuesto conservador inicial: **instancias máximas × procesos por instancia × suma de (pool_size + max_overflow) de cada engine + conexiones directas de jobs + reserva**. Ejemplo de dimensionamiento, no medición del proveedor: 2 × 1 × (5 + 5 + 5) + 10 + 20 = 60. Debe contrastarse con límites reales y carga; incluye todos los roles, evita transacciones largas y no supone que max_connections sea 100.

Las ramas de Neon permiten probar cambios de esquema con aislamiento; la ventana de recuperación depende de su configuración y plan. La búsqueda vectorial se afina comparando latencia y recuperación, sin asumir que un índice aproximado siempre mejora ambos. [S2, S3]

**Decisión de continuidad:** no introducir una segunda API en otro lenguaje para acomodar el hosting. Un cambio de plataforma requiere demostrar soporte del contenedor, jobs, secretos, conectividad y recuperación. Región, cuenta cloud, proveedor/modelo y retención se cierran en G0 con criterios medibles; Neon conectado resuelve el acceso al proveedor de base, no esas decisiones restantes.

## 04. Modelo SQL y contrato de información

Se evoluciona el esquema existente mediante migraciones. Cada registro debe distinguir la identidad estable de la norma, la versión de su texto, la versión de la interpretación y el corte que la publica. Una norma puede regular varios beneficios y un beneficio depender de varias normas.

| Grupo | Entidades y reglas de diseño |
| --- | --- |
| Fuentes y originales | fuentes, fuente_urls, fuente_config_versiones, corridas_ingesta, capturas, documentos y documento_versiones. Trazan origen, configuración, captura y bytes. |
| Identidad jurídica | jurisdicciones, organismos, normas, norma_identificadores, norma_versiones y unidades_documentales. Clave canónica compuesta por jurisdicción, emisor, tipo, número y año cuando corresponda. |
| Hechos y beneficios | beneficios, beneficio_versiones, beneficio_normas, poblaciones, reglas, plazos, cuantías, parámetros, trámites y canales. Columnas y tipos explícitos; no una celda de texto que sustituya la lógica. |
| Evidencia y calidad | afirmaciones, evidencias, evaluaciones de completitud, controles e incidencias. Todo hecho publicado apunta a una evidencia recuperable. |
| Relaciones | relaciones_normativas y referencias_pendientes. Dirección, tipo, alcance al artículo, período y fundamento; citar no implica modificar o derogar. |
| Publicación y consulta | registro_versiones, releases, chunks y pertenencia release-versiones a incorporar o ajustar. Auditoría y outbox mantienen decisiones y cambios. |
| Extensiones RAG | Vectores por chunk, modelo, dimensión y hash; ejecución de recuperación por request_id, corte y fuentes. Reutilizar consultas_auditadas para trazas mínimas; evitar tablas duplicadas. |

**Metadatos mínimos de toda afirmación:** identificador; norma y versión; beneficio cuando corresponda; dimensión; valor tipado y unidad; estado del dato; estado de revisión; evidencia y fragmento; captura; vigencia desde/hasta; fecha de conocimiento; fecha de verificación; responsable y fundamento; corte de publicación. Fechas jurídicas y de observación deben mantenerse separadas.

**Integridad:** claves foráneas sin huérfanos; unicidad canónica y de contenido; intervalos coherentes; moneda e importes con DECIMAL; unidades y enumeraciones controladas; timestamps con zona; borrado restringido de evidencia publicada. JSONB sólo para estructuras cuya variación esté justificada, por ejemplo el árbol de una condición, con esquema y versión.

**Proyecciones:** documentos y hechos son la evidencia del dominio; chunks y embeddings son índices reconstruibles. Actualizar un índice no altera el original ni aprueba una regla. Conservar el corte utilizado permite reproducir una consulta histórica; no se mezclan cortes o versiones incompatibles.

**Consulta tipada propuesta:** mensaje, historial acotado, jurisdicción, fecha consultada, beneficio y hechos mínimos. Respuesta: explicación, modo, estado de orientación, aclaraciones, datos estructurados, fuentes con artículo y URL, faltantes, advertencias, release_id, known_at y request_id. Los nombres finales se alinean al OpenAPI existente en P-014.

## 05. Las siete dimensiones que debe completar el corpus

La unidad de completitud es **versión de norma × beneficio o ámbito regulado × dimensión**. Debe existir un registro explícito aun cuando no haya un beneficio autónomo. «No aplica» sólo se admite con fundamento; no se fuerza una norma modificatoria a inventar un beneficio propio.

| Dimensión | Contenido obligatorio cuando corresponda |
| --- | --- |
| Población destinataria | Niños, niñas, adolescentes, personas en situación de vulnerabilidad y demás grupos definidos por la norma; rol de titular, destinatario o representante; edades, residencia, ámbito y condiciones expresamente previstas. No inferir pertenencia a un grupo por una etiqueta. |
| Criterios de aplicabilidad | Requisitos, inclusiones, incompatibilidades, exclusiones y excepciones; operadores AND/OR, umbrales y parámetros; hechos a preguntar y documentación exigida. Separar requisito sustantivo de evidencia para acreditarlo. |
| Plazos | Solicitud, inscripción, duración del beneficio, renovación, pago, reclamo y recurso; hecho que inicia el cómputo; días hábiles o corridos; calendario y jurisdicción; prórroga, suspensión y efectos del vencimiento. |
| Revocación y cese | Causales diferenciadas de suspensión, revocación, cese o caducidad; autoridad, procedimiento, notificación, posibilidad de subsanar, defensa y recurso cuando estén previstos. |
| Interdependencias | Norma base, reglamentación, modificación, derogación, remisión y parámetros externos; dirección y artículo afectado; versión temporal; estado de resolución de cada dependencia. |
| Beneficio otorgado | Prestación dineraria, servicio, subsidio o derecho; cuantía fija o fórmula, moneda, periodicidad y topes; organismo, trámite, requisitos documentales y canales verificados. |
| Qué no descartar | A: salvaguardas, excepciones y vías alternativas que evitan excluir por error, especialmente ante información faltante. B: preservación de anexos, versiones anteriores, normas citadas y transitorias, rechazos y bloqueos. Mantener A y B diferenciados. |

**Estados del dato:** PRESENTE, AUSENTE_EN_FUENTE, NO_APLICA_JUSTIFICADO, PENDIENTE_EXTRACCION, PENDIENTE_REVISION, CONFLICTO y DESACTUALIZADO. Son conceptos funcionales; P-003/P-008 los mapearán a los vocabularios existentes mediante una migración si hiciera falta. No se implementa una enumeración paralela sin conciliación.

**Estado jurídico y editorial:** vigencia del hecho, frescura de verificación y aprobación son ejes independientes. PRESENTE no equivale a verdadero ni a publicable; una firma tampoco vuelve actual un parámetro vencido. Una ausencia documentada mejora la trazabilidad, pero no aumenta la disponibilidad de información positiva.

**Ejemplo de conducta, sin afirmar una regla vigente:** si falta un dato de residencia, el sistema solicita la aclaración necesaria; no concluye que la persona carece del derecho. Si una norma modificatoria sólo cambia una condición, la ficha vincula el beneficio de la norma base y cita ese alcance específico.

## 06. Adquisición, citas cruzadas y actualización

El catálogo versionado en el repositorio es la fuente del inventario de trabajo. Cada recurso conserva su historia individual con URL, tipo, adaptador, frecuencia, campos destino, cobertura esperada y prueba. Se prioriza dataset oficial cuando satisface el caso; HTML, PDF y OCR son rutas de extracción con controles específicos.

| Caso inicial | Fuente principal y dependencias que deben resolverse |
| --- | --- |
| F33 | Ley 24.714 / AUH: D01 Decreto 1382/2001 y D02 Decreto 1604/2001. Separar identidad principal de referencias y reconstruir sus períodos y relaciones. |
| F19 | Ley 2917, Becas Media: D03 Decreto 75/2015 y D04 Resolución 1621/MEDGC/2025. Vincular reglamentación y documentación operativa con evidencia. |
| F23 | Ordenanza 43.478: D05 Ley 547/2001. Resolver identidad, artículo y alcance del vínculo sin fusionar las dos normas. |
| F40 | Decreto 690/2006: D06 Ley 6935/2025. Diferenciar texto original y consolidado y verificar en qué versión aparece la referencia. |

Estos vínculos provienen del relevamiento aportado y del manifiesto. **El plan exige verificarlos; no afirma por sí mismo su vigencia o efecto jurídico.** Una norma citada adicional puede ser un hallazgo correcto del scraper: el fallo consiste en confundirla con la norma principal, perder el vínculo o atribuirle efectos sin evidencia.

**Fuentes de novedades ya previstas:** boletines nacional, CABA y PBA; portal normativo PBA; ANSES para montos y calendarios; ficha oficial de CUD cuando corresponda al corpus. Las URLs del manifiesto son puntos de partida históricos y deben revalidarse al ejecutar. No se usa una página institucional genérica como prueba de un importe o fecha concreta.

**Ciclo operativo:** descubrir -> capturar -> validar respuesta y contenido -> extraer -> identificar -> resolver relaciones -> evaluar campos y reglas -> revisar -> publicar -> reindexar -> notificar al consumidor. Ingesta por lotes, checkpoints, reintentos con espera incremental y límites por dominio. TLS se valida; bloqueos no se eluden.

**Frecuencia propuesta:** disparo del planificador cada hora; boletines y fuentes de montos/calendarios al menos diariamente o con la frecuencia que requiera su criticidad; fuentes estables según su configuración. Descargar y detectar cambios no equivale a aprobarlos. La publicación de una regla modificada exige revisión y pruebas.

**Cobertura exigida:** textos completos del ámbito necesario, anexos pertinentes, paginación y remisiones críticas. Fuentes sólo de metadatos pueden cerrar su importación de catálogo, pero no la lectura jurídica ni la capacidad conversacional. Una dependencia referida fuera del alcance inicial se clasifica y se incorpora si determina una respuesta.

**Política de fallos:** los registros incompletos permanecen en cuarentena, con causa, evidencia, responsable y próximo intento. Si la fuente crítica continúa inaccesible, se busca una copia oficial autorizada o se declara la capacidad pendiente. El cierre completo requiere resolver la brecha; un piloto acotado exige señalar expresamente su alcance menor.

## 07. Criterios de calidad y medición

Los siguientes umbrales son **criterios de aceptación propuestos**, no resultados obtenidos. Se calculan con denominador y fecha explícitos; el tablero debe permitir abrir las filas que componen cada indicador.

| Indicador | Cálculo y umbral de salida |
| --- | --- |
| Inventario trazado | Recursos con identidad, estado, responsable y prueba / recursos del manifiesto aprobado = 100%. No mide contenido adquirido. |
| Adquisición efectiva | Recursos exigibles con contenido validado / recursos exigibles. Objetivo 100% del alcance final; alias y descartes justificados se concilian aparte. |
| Completitud de ficha | Dimensiones con registro y estado explícitos / siete dimensiones exigibles = 100%. Se informa por separado la proporción PRESENTE y publicable. |
| Evidencia | Afirmaciones publicadas con cita recuperable y versión / afirmaciones publicadas = 100%; enlaces o hashes rotos = 0 en el corte. |
| Integridad | Duplicados canónicos, huérfanos y solapamientos temporales inválidos = 0. Un mismo texto en dos portales no aumenta su autoridad. |
| Dependencias | Dependencias críticas resueltas / dependencias críticas de las capacidades publicadas = 100%. Pendientes no críticas permanecen visibles. |
| Aprobación | Reglas usadas en evaluación con firma humana, casos y versión / reglas usadas = 100%. CANDIDATE o IN_REVIEW servidas como definitivas = 0. |
| Frescura | Afirmaciones operativas servidas dentro del TTL de su capacidad = 100%. Fecha de verificación y fecha jurídica se muestran separadas. |
| Recuperación | Recall@5 >= 90% en preguntas respondibles del conjunto congelado; reportar por beneficio, lenguaje, fecha e intención. |
| Fidelidad | >= 98% de afirmaciones sustantivas respaldadas según revisión experta; 100% de afirmaciones críticas sobre derecho, importe, requisito o plazo con soporte correcto. |
| No exclusión errónea | 0 denegaciones causadas por un dato desconocido, un conflicto sin resolver o una excepción omitida en los casos críticos. |
| Utilidad | >= 85% de consultas respondibles resueltas correctamente; >= 90% de abstenciones esperadas correctas; tasa de abstención innecesaria informada. |

**Muestra de evaluación:** al menos 150 consultas anotadas: 60 respondibles, 30 con datos faltantes o ambiguos, 25 históricas o con cambios normativos, 20 fuera de alcance/conflicto y 15 adversarias. Particionar ajuste y evaluación final antes de desarrollar; añadir casos sin reescribir el esperado para que coincida con el modelo. La revisión jurídica determina las respuestas de referencia.

**Calidad del OCR:** validar por muestreo estratificado y comparación con páginas originales; revisión completa de números, negaciones y artículos que sostienen decisiones. Una confianza OCR alta no sustituye verificar la cláusula crítica. Detectar texto vacío, páginas faltantes, tablas desestructuradas y anexos omitidos.

**Contrato de habilitación:** cada capacidad de un beneficio tiene requisitos propios. Explicar historia normativa puede habilitarse aunque no exista un importe actual verificado; calcular ese importe debe bloquearse. Los conflictos se acotan a lo afectado y nunca se silencian. El sistema siempre distingue «no tengo evidencia suficiente» de «no tenés derecho».

## 08. Chatbot ampliado: arquitectura, modelos y respuesta verificable

### 08.1. Adaptación del caso Boti a ACIJ

El análisis de Boti aporta patrones de conversación, recuperación y derivación. El piloto técnico publicado por AWS describe resúmenes comparativos y desambiguación de trámites, junto con prompts adaptados al contexto [S7]. En ACIJ esos patrones se aplican a derechos y beneficios del corpus. Los resultados experimentales de Boti no se utilizan como métricas de ACIJ.

La persona puede explicar una necesidad sin conocer el nombre del beneficio. El servicio identifica alternativas, pregunta lo mínimo, consulta reglas y fuentes, y devuelve próximos pasos. El corpus inicial conserva normativa nacional, CABA y las fuentes de PBA efectivamente incluidas; un directorio de alcance nacional no amplía por sí solo la cobertura jurídica.

| Capacidad | Comportamiento exigido | Entrega / historias |
| --- | --- | --- |
| Conversación libre | Comprender intención, errores de escritura, reformulaciones y referencias al mensaje anterior. | E1 / P-025, P-029 |
| Contexto | Recordar hechos mínimos durante la sesión y permitir corregirlos; distinguir hechos de la persona y evidencia normativa. | E1 / P-025, P-037 |
| Orientación por situación | Relacionar una necesidad con alternativas verificadas del corpus, explicando cobertura y límites. | E1 / P-026, P-030 |
| Requisitos y cálculos | Evaluación ternaria, excepciones, importes y plazos mediante funciones tipadas ya previstas. | E1 / P-014, P-030 |
| Citas y vigencia | Sustentar cada afirmación relevante con artículo/fragmento, fuente y fecha; mostrar qué no se pudo confirmar. | E1 / P-028 |
| Acompañamiento | Directorio verificado y cola humana configurada; resumen confirmado por la persona y estado real. | E1 / P-031 |
| Front conversacional propio | Escritura libre, preguntas contextuales, fuentes desplegables, hechos corregibles y acciones claras en computadora y celular. | E1 / P-015, P-032 |
| Audio | Transcripción corregible y lectura de la respuesta previamente verificada, con texto disponible. | E2 / P-033 |
| Documentos | Explicar un PDF o una foto con localizadores; no autenticar ni transformar el documento en norma oficial. | E2 / P-034 |
| Novedades web | Temas elegidos voluntariamente y cambios publicados visibles al abrir la web; preferencias con vencimiento y borrado. | E2 / P-035 |

### 08.2. Flujo conversacional y herramientas

El workflow comprende recepción y normalización, identificación de intención, aclaración cuando sea necesaria, consulta de funciones y evidencias, armado de respuesta, verificación y emisión. Una corrección vuelve a evaluar sólo los resultados que dependen del hecho cambiado. Los temas sin evidencia suficiente conservan una salida útil de aclaración o derivación.

LangGraph permite combinar pasos deterministas y llamadas LLM, preservar estado y habilitar intervención humana [S8]. Se integra como módulo dentro del backend existente; la versión y las dependencias se fijan en un archivo de bloqueo tras pruebas de compatibilidad. No se migra el sistema completo a Bedrock, Botmaker o una segunda base para reproducir una arquitectura histórica.

| Función propuesta | Datos que puede usar | Límite de autoridad |
| --- | --- | --- |
| buscar_opciones | Necesidad, territorio y fecha; fichas publicadas. | Devuelve candidatos; no decide elegibilidad. |
| recuperar_evidencia | Intención, beneficio, filtros, corte y localizadores. | Sólo contenido permitido, vigente para la consulta y suficientemente fresco. |
| evaluar_condiciones | Hechos confirmados, reglas y excepciones aprobadas. | Devuelve cumple / no cumple / desconocido por condición, con explicación preliminar. |
| consultar_monto_y_plazo | Parámetros tipados, evento inicial y calendario aplicable. | Nunca calcula desde el recuerdo del LLM ni equipara fecha del documento a notificación. |
| buscar_atencion | Tema, localidad y directorio con fecha de verificación. | No inventa disponibilidad ni asegura representación jurídica. |
| preparar_resumen | Hechos mínimos y respuesta ya verificada. | Muestra una vista previa; no envía ni crea caso por sí sola. |
| solicitar_derivacion | Conector configurado y consentimiento específico confirmado. | Acción operativa con idempotencia; no altera el corpus ni sistemas estatales. |
| consultar_novedades | Temas y territorio elegidos, eventos de publicación aprobados. | Consulta de sólo lectura; guardar preferencias es una acción explícita de la interfaz. |

El modelo propone llamadas con argumentos tipados; el servidor aplica permisos, límites y estados. No hay SQL libre, navegación autónoma por sitios ni scraping dentro del turno. Las búsquedas ciudadanas usan el corpus publicado; el descubrimiento de fuentes sigue el proceso de ingesta y curación.

### 08.3. Recuperación actualizada y control temporal

Se conserva el RAG híbrido previsto en P-012: FTS en español más pgvector. La documentación de pgvector contempla combinación con búsqueda textual y reordenamiento de resultados [S9]. La ampliación agrega fichas comparativas por beneficio/trámite y un reranker acotado para casos ambiguos. Su activación depende de una mejora comprobada frente al recuperador base.

Las fichas reúnen población, territorio, requisitos diferenciales, compatibilidades, trámite, fecha y excepciones, con respaldo para cada dato. Se segmenta por estructura normativa y se recuperan las excepciones junto con las condiciones a las que pertenecen. Los resúmenes ayudan a elegir documentos; las afirmaciones finales se apoyan en texto o hechos aprobados.

Se filtran permisos, publicación, jurisdicción, vigencia y frescura antes de entregar contexto. No se mezclan cortes incompatibles. Cada turno verifica que su corte siga habilitado: si cambió un dato pertinente, se recalcula y se explica el cambio; si no puede resolverse, se bloquea esa capacidad. Un resultado anterior no se reutiliza como actual sólo porque esté en la memoria del chat.

La expansión por relaciones se limita a las necesarias para responder; se usa el modelo relacional existente. No se requiere un grafo adicional ni descargar todo el derecho argentino. Los montos, fechas, teléfonos y reglas continúan resolviéndose por consultas tipadas.

### 08.4. Modelos y componentes vigentes

| Pieza | Decisión para el proyecto | Verificación necesaria |
| --- | --- | --- |
| Generación | Adaptador de proveedor; candidato de referencia actual: GPT-6 Astra, documentado en el catálogo de OpenAI [S10]. Usar Responses API con salida estructurada cuando corresponda. | Acceso efectivo, versión, evaluación en español y dominio, retención, latencia y costo. No se promete disponibilidad en la cuenta. |
| Selección de modelo | Comparar el candidato con una alternativa de menor costo habilitada. Resolver consultas simples mediante funciones o plantillas cuando alcancen. | Elegir por calidad crítica y costo por orientación resuelta; guardar decisión y versión exacta. |
| Embeddings | Preservar el adaptador fastembed del proyecto. Comparar su modelo configurado con text-embedding-3-small como candidato documentado [S11]. | Calidad sobre español cotidiano, negaciones y términos jurídicos; dimensión e índice compatibles. Cambiar de modelo implica reindexar. |
| Salida tipada | Pydantic y JSON Schema; Structured Outputs ayuda a obtener la estructura requerida [S12]. | Manejar rechazos y truncamiento. JSON válido no acredita verdad ni respaldo legal. |
| Voz / documentos | Adaptadores independientes STT, TTS y OCR; conservar respuesta textual y original temporal cuando sea necesario. | Confirmación de datos críticos, política de datos y pruebas por modalidad antes de habilitar. |

La configuración tiene proveedor, modelo y versión, versión del prompt, parámetros admitidos, timeout, presupuesto y capacidades. No se fijan los modelos de las publicaciones históricas de Boti como estándar actual. La selección productiva se cierra con la cuenta y las pruebas de G0/G3; esta versión incorpora la arquitectura y candidatos actuales, no contrata ni activa esos servicios.

### 08.5. Contrato de respuesta y verificación

Extender el OpenAPI existente de forma compatible; los nombres finales se concilian en P-014/P-028. Se necesitan respuesta visible, modo, intención, jurisdicción, fecha consultada, hechos pendientes, próximos pasos, estado de orientación, fuentes y localizadores, release_id y request_id. Internamente, cada afirmación sustantiva incorpora sus evidence_ids, criticidad y estado de verificación. Modelo y prompt quedan en la traza técnica, no en el mensaje ciudadano.

| Resultado funcional | Expresión ciudadana orientativa |
| --- | --- |
| Orientación respaldada | Se explica lo que puede afirmarse con sus condiciones y próximos pasos. |
| Falta un hecho | Se pregunta el dato concreto que cambia la orientación. |
| Falta evidencia o hay conflicto | Se indica qué punto no se pudo confirmar y una vía verificable para continuarlo. |
| Fuera de cobertura | Se explica el alcance disponible y se ofrece un canal pertinente si existe en el directorio. |
| Requiere acompañamiento | Se ofrece una derivación real, con su estado y consentimiento. |

No se traduce desconocido como no elegible. El LLM no otorga ni deniega un derecho: comunica el resultado del motor y sus condiciones. Se verifica que cada cita exista, pertenezca al corte y respalde la afirmación; se comprueban negaciones, sujeto, alcance temporal, números y excepciones. La revisión experta evalúa el respaldo semántico que los validadores automáticos no garantizan.

El streaming puede mostrar progreso, pero el contenido sustantivo se entrega después de validarlo. La síntesis de voz lee únicamente esa respuesta. Ante una falla del generador se puede mostrar una respuesta estructurada o un extracto pertinente; ante evidencia insuficiente se aclara o deriva. No se crea una respuesta plausible para evitar una abstención.

### 08.6. Memoria y retención

El estado mantiene ocho turnos recientes como límite de contexto inicial y hechos mínimos estructurados con procedencia; los límites se configuran y se ensayan. No debe olvidarse una excepción o una negación al resumir. Si un hecho deja de estar disponible se vuelve a preguntar antes de usarlo.

| Datos | Política inicial propuesta | Prueba exigida |
| --- | --- | --- |
| Sesión web y checkpoints | Estado mínimo: 30 minutos de inactividad, máximo dos horas; sin historial permanente por defecto. | Expiración efectiva, eliminación y ausencia en logs. |
| Recuperación entre sesiones | Opción expresa y revocable; máximo inicial de siete días, con aviso de vencimiento. | Acceso del titular y borrado de copias operativas. |
| Audios y documentos | Original temporal hasta completar el procesamiento y como máximo 24 horas. | Borrado programado, acceso acotado y exclusión del corpus público. |
| Derivación | Sólo datos necesarios y destino elegido; plazos del servicio documentados antes de activar. | Consentimiento, acceso y retención del conector comprobados. |
| Preferencias de novedades | Temas y territorio opcionales, en este navegador, durante un máximo inicial de siete días; sin historial ni identificadores personales. | Opt-in explícito, vencimiento, borrado y aviso para dispositivos compartidos. |
| Trazas técnicas | Metadatos mínimos de respuesta, modelo, corte y errores; sin contenido identificable innecesario. Plazo acordado en G0. | Auditoría posible sin reconstruir una historia personal innecesaria. |

Para OpenAI, configurar store=false cuando aplique y verificar los controles contratados. La documentación distingue retención de estado y registros de abuso: no usar datos para entrenamiento por defecto no equivale a retención cero [S13]. Cada proveedor de modelo, voz, OCR o alojamiento debe tener finalidad, destinatario, región y retención documentadas. No se promete eliminación de copias externas fuera del control de ACIJ.

Guardar preferencias, recuperar una conversación, derivar y cargar documentos requieren decisiones separadas de la persona. Se minimizan diagnósticos, DNI, direcciones precisas y datos identificables de menores. El front no solicita teléfono para consultar; no cruza sesiones ni crea un perfil persistente de forma implícita.

### 08.7. Front web conversacional propio de ACIJ

El acceso principal es una pantalla de conversación dentro de la web de ACIJ. La persona puede contar su situación con sus palabras, ampliar o corregir lo dicho y abrir las fuentes sin perder el hilo. Se reutiliza la implementación frontend existente tras P-001; la actualización no impone migrar a otro framework. El backoffice tiene rutas y permisos separados.

| Componente | Comportamiento de la interfaz |
| --- | --- |
| Inicio | Identidad ACIJ, explicación breve del alcance, campo «Contanos qué necesitás» y ejemplos opcionales por necesidad. Se permite empezar sin registro. |
| Conversación | Mensajes de persona y asistente diferenciados, una pregunta necesaria por turno, escritura libre siempre disponible y opciones sugeridas sólo cuando ayudan. |
| Entrada | Campo multilínea con etiqueta visible, botón Enviar y validación comprensible. Enter envía y Shift+Enter agrega una línea; el envío respeta la composición de texto del dispositivo. El borrador se conserva en memoria, sin guardado persistente automático. |
| Respuesta | Explicación breve primero; condiciones pendientes y próximos pasos a continuación. Los detalles se amplían a pedido. Se indica cuándo falta un dato o no pudo verificarse una afirmación. |
| Fuentes | Control «Ver fuentes» por respuesta; abre norma, fragmento, enlace oficial y fecha pertinente. En móvil el detalle se expande en el mismo recorrido; en escritorio puede abrir un panel lateral. |
| Contexto corregible | Control «Revisar lo que me contaste» con los hechos mínimos confirmados y acción Corregir. Las inferencias no se muestran como hechos. El servidor recalcula los resultados afectados y el front identifica los anteriores como reemplazados. |
| Próximos pasos | Acciones concretas como ver requisitos, abrir un canal oficial, preparar un resumen o pedir acompañamiento. Sólo aparecen si hay evidencia o capacidad habilitada; no se simula un trámite presentado. |
| Control de sesión | «Nueva consulta» y «Borrar conversación» accesibles, con confirmación si hay datos que perder; explica vencimiento y alcance real de la eliminación. Recuperación entre sesiones sólo por opción expresa. |
| Modalidades opcionales E2 | Micrófono, lectura en voz, adjuntar documento y novedades dentro de la web. No aparecen como acciones operativas hasta que su capacidad esté habilitada y aceptada. |

**Jerarquía y presentación:** la conversación ocupa el área principal. Las fuentes y el contexto son detalles desplegables, sin obligar a recorrer las siete dimensiones del modelo de datos. En móvil se usa una columna, con entrada accesible al aparecer el teclado; en escritorio la lectura mantiene un ancho cómodo. Se ofrece volver al último mensaje cuando la persona esté leyendo respuestas anteriores, sin desplazarla automáticamente. El color acompaña rótulos claros y no decide por sí solo si una condición está satisfecha.

**Integración:** el navegador se comunica con la API existente bajo el mismo origen; el servidor mantiene permisos, estado jurídico y secretos. Reconciliar las rutas OpenAPI reales antes de implementar. Como extensión, usar un flujo HTTP/SSE con eventos tipados de progreso, respuesta verificada, aclaración, fallo y finalización; JSON convencional es la alternativa si el entorno no admite streaming. Un ID por solicitud vincula reintentos, cancelación y respuesta, y evita duplicados. Cancelar detiene la visualización y el trabajo cancelable; no acredita anular una acción externa ya confirmada.

| Estado del front | Mensaje o comportamiento esperado |
| --- | --- |
| Listo | Entrada activa, sugerencias opcionales y datos de la sesión accesibles. |
| Procesando | «Estoy revisando la información disponible». Se permite cancelar; no se muestran conclusiones pendientes de verificar. |
| Falta un dato | Pregunta concreta, opciones pertinentes y posibilidad de escribir o no responder. |
| Respuesta lista | Contenido verificado, fuentes y próximos pasos; enlace a aclarar o corregir. |
| Error recuperable | Explicación simple, reintento seguro y borrador conservado mientras la página sigue abierta. |
| Sesión vencida | Explicación del vencimiento y acción para empezar; no se reutilizan hechos borrados. |
| Acompañamiento | Resumen revisable y, tras la acción voluntaria, estado real de recepción o alternativa disponible. |

**Aceptación E1 del front:** P-015 cubre integración y visualización base; P-032 agrega la experiencia de contexto, detalles y estados. Validar recorridos desde 320 px, zoom al 200%, navegación por teclado y lector de pantalla, foco visible, anuncios breves de resultados, errores asociados al campo y ausencia de movimiento forzado. Ensayar red lenta, respuesta fuera de orden, doble envío, cancelación, vencimiento y corrección de un dato. Los casos críticos de este front forman parte de P-023/P-024 antes de E2.

## 09. Experiencia de usuario y revisión jurídica

| Recorrido | Entrega verificable |
| --- | --- |
| Inicio | Propósito claro, lenguaje cotidiano, preguntas sugeridas y explicación breve de qué datos conviene evitar. Consulta anónima sin formulario de identidad. |
| Conversación | Mensajes, carga, cancelación, reintento y nueva conversación. Aclaraciones de jurisdicción, fecha, beneficio y hechos mínimos con controles adecuados a su tipo. |
| Respuesta | Explicación legible, resultado preliminar cuando corresponda, requisitos pendientes, próximos pasos, citas y fecha de la información. Sin nombres de tablas o detalles del modelo dentro del recorrido ciudadano. |
| Evidencia | Norma, versión, artículo, fragmento, fuente y fechas; abrir documento oficial y regresar al mismo punto del chat. Diferenciar texto histórico de dato operativo actual. |
| Ficha normativa | Siete dimensiones, beneficios vinculados, relaciones, estados y evidencia. La vista pública muestra lo publicado; revisión ve pendientes con sus permisos. |
| Revisión | Cola priorizada, filtros, comparación original/interpretación, condición y excepciones; decisión fundada, actor real y control de concurrencia. |
| Publicación | Resumen del corte, cambios, controles y capacidades afectadas; confirmación del rol publicador; historial y mecanismo de reversión. |
| Calidad | Inventario, bloqueos, faltantes, dependencia crítica, frescura, decisiones y resultados de corridas con acceso al registro afectado. |

**Accesibilidad:** objetivo WCAG 2.2 AA para el alcance web, con revisión automática y manual; teclado, foco visible, etiquetas, errores comprensibles, contraste, ampliación y lector de pantalla. Ensayar móviles desde 360 px y conexiones lentas. No depender sólo del color para comunicar aprobación, conflicto o estado de carga. [S6]

**Revisión de reglas:** CANDIDATE -> IN_REVIEW -> APPROVED o REJECTED, con correcciones que originan nueva versión cuando alteran el contenido. PUBLISHED depende de un release válido. Los estados finales se alinean al vocabulario real; no se altera una evidencia ya firmada sin dejar trazabilidad.

**Trabajo jurídico pendiente:** reconciliar las 166 candidatas; distinguir las 67 sin condición ejecutable entre reglas formalizables, disposiciones informativas y vacíos de evidencia; probar umbrales, negaciones, incompatibilidades, prórrogas y excepciones. Una regla rechazada no desaparece del expediente. Si deja incompleto un requisito crítico, el beneficio no se habilita hasta resolverlo.

**Firma de HU-036:** el responsable jurídico firma por beneficio y capacidad, con fecha, versiones, conjunto de pruebas y dependencias. Curadores y agentes pueden preparar la evidencia y proponer condiciones; no reemplazan esa firma. Producto valida utilidad y operación valida disponibilidad: son decisiones distintas y las tres tienen evidencia de cierre.

### 09.1. Limpieza del corpus conversacional

Inventariar mensajes, plantillas, preguntas, errores y salidas generadas por intención. Cada registro debe conservar ID, situación de uso, original, versión corregida, variables, fuente cuando corresponda, responsable y fecha. Clasificar problemas de claridad, repetición, ambigüedad, exactitud, tono y accesibilidad. El contenido jurídico permanece versionado; limpiar la redacción no elimina excepciones ni antecedentes.

La capa de búsqueda normaliza espacios, caracteres y variantes para encontrar información, conservando el texto original. No elimina negaciones ni convierte desconocido en falso. Diccionarios de lenguaje cotidiano vinculan expresiones con intenciones, sin asumir que una frase ambigua identifica un único programa. Los nombres de normas, importes, fechas y domicilios no se corrigen automáticamente sin confirmación.

### 09.2. Reglas editoriales y patrones aplicados

1. Identidad clara: asistente de orientación de ACIJ. Voseo consistente, español sencillo y tratamiento respetuoso.
2. Responder primero lo preguntado. Usar mensajes breves y ofrecer detalle adicional sin ocultar condiciones.
3. Pedir una aclaración necesaria por turno; aprovechar datos confirmados y permitir no responder.
4. Describir pasos con verbos concretos. Conservar negaciones, sujeto, plazos, unidades y excepciones.
5. Diferenciar orientación, cálculo, texto de un documento y estado de una acción. No prometer que una gestión fue presentada o un derecho concedido.
6. Tono sobrio ante dificultades. Evitar entusiasmo automático, culpa, tecnicismos y exceso de emojis. No rechazar por enojo una consulta legítima.
7. Mostrar fuentes con norma, fragmento y fecha. Dar instrucciones de trámite sólo si están respaldadas y habilitadas.
8. No cerrar cada turno con una pregunta genérica. Cuando la necesidad esté resuelta, permitir terminar.
9. Si hay un error, explicar qué no pudo hacerse y una alternativa real. No afirmar pérdida de datos o envío exitoso sin evidencia.
10. Usar la misma semántica en todas las modalidades del front. El texto, audio y resumen deben comunicar las mismas condiciones.

| Problema / frase ilustrativa | Redacción propuesta | Condición de uso |
| --- | --- | --- |
| Burocracia: A los efectos de analizar la procedencia... | Para orientarte, necesito saber en qué localidad vivís. | La jurisdicción cambia la respuesta. |
| Dato faltante convertido en rechazo: No cumplís los requisitos. | Todavía falta confirmar [condición]. ¿[pregunta concreta]? | Falta información; no es una condición incumplida. |
| Menú sin contexto: Seleccioná una categoría. | ¿Querés saber cómo pedir la ayuda o qué hacer si te la rechazaron? | Esas son las dos interpretaciones pertinentes. |
| Conflicto oculto: El monto es [valor]. | No pude confirmar el monto que corresponde a esa fecha. Podés verificarlo en [canal]. | Importe no habilitado y canal verificado. |
| Error genérico: Intentá más tarde. | No pude consultar esa información. Podés volver a intentar o revisar [fuente]. | Fallo real y alternativa disponible. |
| Acción exagerada: Ya te derivé. | El equipo recibió tu consulta. El número es [ID]. | Sólo después del acuse real. Antes: mostrar resumen y pedir confirmación. |
| Plazo incierto: Tenés diez días para reclamar. | Para revisar el plazo, necesito saber cuándo recibiste la notificación. | Esa fecha es relevante según la fuente; no se conoce todavía. |
| Entusiasmo inadecuado: ¡Genial, vamos con tu problema! | Vamos paso a paso. Puedo ayudarte a revisar [necesidad]. | Situación sensible; capacidad efectivamente disponible. |

Son ejemplos de diseño, no transcripciones ni afirmaciones de derecho vigente. Ninguna variable entre corchetes debe llegar sin completar al usuario. La plantilla se habilita sólo si sus condiciones y datos están validados.

### 09.3. Ejemplo de experiencia

Ejemplo ficticio para probar el flujo, sin afirmar requisitos de un programa real:

- Persona: No me alcanza para el alquiler y no sé qué ayuda puedo pedir.
- Asistente: Puedo ayudarte a revisar las opciones del lugar donde vivís. ¿En qué localidad estás?
- Persona: En CABA.
- Asistente: ¿Buscás información para pedir una ayuda o ya tenés una solicitud en trámite?
- Persona: La pedí y me la rechazaron.
- Asistente: Vamos a revisar qué podés hacer. ¿Te dieron el motivo del rechazo por escrito?
- Persona: Sí, pero no lo entiendo.
- Asistente, con E2 habilitada: Podés copiar la parte que no entendés o compartir una imagen sin nombres, DNI ni domicilio. Voy a explicarte qué dice y qué datos faltan para revisar los próximos pasos.

El siguiente turno debe distinguir el texto aportado de una regla aplicable, consultar evidencia vigente y ofrecer un canal si hace falta acompañamiento. Si un adjunto no está habilitado, no se ofrece cargarlo.

### 09.4. Atención humana, documentos y novedades en la web

La derivación se ofrece cuando la persona la pide, la evidencia no resuelve la situación o se requiere acompañamiento. No se asume que ACIJ tenga una guardia o asesoramiento individual para todos los temas. El directorio y la cola deben contar con responsable, horarios y alcance reales; si sólo hay un canal externo se entrega ese contacto con su fecha de verificación.

Los documentos privados se procesan de forma temporal, con consentimiento y minimización. Su contenido no se vuelve evidencia normativa ni prueba de identidad. Los datos críticos detectados por OCR o audio se confirman antes de usarlos; las fechas relativas se interpretan con zona horaria y contexto, y se piden aclaraciones cuando cambian el resultado.

Las novedades voluntarias se basan en cambios aprobados del corpus, no en inferencias sobre elegibilidad personal. La persona elige temas y territorio, y puede borrar esas preferencias. Las novedades aparecen cuando abre la web, con fuente y fecha; no se envían mensajes fuera de ella ni se presupone que la persona las leyó. Guardar preferencias en el navegador requiere consentimiento y vencimiento; en un dispositivo compartido se permite consultar sin guardarlas.

## 10. Operación, entrega y objetivos de servicio

**Entornos:** desarrollo aislado, staging de revisión y producción. Base y credenciales separadas; ramas de prueba con vencimiento y datos anonimizados si llegaran a existir datos personales. Código y esquema siguen ramas coordinadas, pero una rama de base no equivale a una fusión de código ni a un respaldo independiente.

**CI/CD:** ejecutar checks en push y PR, usar PostgreSQL real en integración, conservar resultados por SHA y exigirlos para integrar. Probar migración vacía y actualización desde el estado anterior; construir una sola imagen y promover ese digest. Definir rama estable y protección mediante un PR de integración. Nunca forzar una migración incompatible sólo para obtener un despliegue verde. [S5]

**Monitoreo horario:** Cloud Scheduler invoca un Cloud Run Job; el ciclo aplica las frecuencias por fuente. Autenticar la invocación, limitar duración y reintentos, impedir solapamientos y alertar atraso. Si se usa bloqueo de sesión PostgreSQL, emplear conexión directa; con pool transaccional usar un lease diseñado para ello. [S1, S4]

| Objetivo inicial | Cómo demostrarlo |
| --- | --- |
| Persistencia | Reemplazar la instancia de aplicación y consultar los mismos registros y originales desde una nueva. |
| Disponibilidad | Objetivo 99,5% mensual del servicio público. En piloto se presenta la observación real; una prueba breve no demuestra un mes de disponibilidad. |
| Latencia | Con 20 conversaciones concurrentes durante 30 minutos: p95 \<= 2 s para respuestas estructuradas; p95 \<= 15 s para respuestas generadas completas. Medir arranques en frío aparte. |
| Estabilidad | Errores inesperados \< 1% bajo esa carga, sin agotar conexiones ni superar los límites configurados de cómputo y tokens. |
| Frescura | Fuentes críticas operativas dentro de 24 h de verificación propuesta, salvo un TTL específico más exigente; expiración bloquea la capacidad afectada. |
| Alertas | Aviso probado ante dos ciclos fallidos, atraso de un ciclo crítico, evidencia corrupta, error sostenido o límite de gasto. Receptor operativo configurado en el despliegue. |
| Recuperación | RPO \<= 24 h y RTO \<= 4 h iniciales, demostrados restaurando base y originales en destino aislado. Revisar objetivos según volumen y criticidad. |
| Reversión | Volver a imagen y release anterior compatible, preservando auditoría y contenido; ensayo durante staging. |

**Respaldo:** configurar la ventana de recuperación de Neon según el objetivo, respaldar fuera de la aplicación y probar una copia recuperable independiente conforme al riesgo. Un pg_dump sin objetos documentales no reconstruye la evidencia; se requiere manifiesto consistente de ambos. Las referencias de versiones publicadas no se eliminan por una política genérica de limpieza. [S2]

**Privacidad y costos:** no registrar conversaciones completas en logs; presupuesto por entorno, límite por consulta y alertas de consumo. Sumar base, cómputo web/jobs, objetos, transferencia, registros, embeddings y generación. El plan gratuito de una cuenta no constituye garantía de cumplir retención, capacidad o nivel de servicio.

## 11. Secuencia de ejecución y gates

La versión 1.0 estimaba **12 a 20 semanas** y una ruta crítica de 50-82 días laborables para sus 24 historias. El nuevo escenario orientativo es **16 a 28 semanas para E1 + E2**, antes de confirmar cuentas y acuerdos de atención; no se conserva la ruta crítica anterior como cálculo de la ampliación. La tabla siguiente mantiene la secuencia base G0-G5 y añade G6-G7. P-001 recalcula el calendario con las 38 historias y sus capacidades asignadas. Supone acceso a cuentas en la primera semana, tres perfiles técnicos equivalentes a tiempo completo, QA y revisión jurídica disponibles en paralelo y reutilización efectiva del código existente. Se recalibra después de P-001; no es un compromiso de fecha ni una estimación de tiempo de generación de código por agentes.

| Tramo | Trabajo principal | Evidencia para avanzar |
| --- | --- | --- |
| Semana 1 / G0 | Línea de base, inventario, alcance de capacidades, cuenta/región, responsable jurídico, presupuesto y estrategia de integración. Iniciar CI. | Denominador y decisiones documentados; backlog asignable, baseline y criterios de aceptación. |
| Semanas 1-4 / G1 | Base Neon, migraciones, roles, originales persistentes, bootstrap y staging técnico. | Carga real conservada tras reemplazo de aplicación; idempotencia; CI ejecutado sobre PostgreSQL. |
| Semanas 4-8 / G2 | Fuentes pendientes, relaciones, siete dimensiones y workflow de revisión. Curación comienza por las cuatro cadenas prioritarias. | Cobertura y dependencias conciliadas; fichas y evidencias; pendientes críticos visibles y asignados. |
| Semanas 8-14 / G3 | Publicación por corte, recuperación híbrida, generación, motor operativo y front integrado. | Recorrido fuente -> cita en staging; primeras capacidades aprobadas útiles; evaluación RAG y diálogo. |
| Semanas 5-15 / G4 | Backoffice, cierre jurídico del alcance, scheduler, alertas, backups y restauración, seguridad y carga. | Acta HU-036, dos ciclos automáticos, restauración y rollback; objetivos técnicos verificados. |
| Semanas 15-20 orientativas / G5 | Aceptación E1: incluir P-025 a P-032 y P-037 en el recorrido web; piloto y traspaso de E1. | Front conversacional propio, evidencia, contexto, lenguaje y derivación aceptados. E2 sigue abierta. |
| Semanas 18-25 orientativas / G6 | Integración y ensayo de audio, documentos y novedades dentro del front. Preparación técnica puede adelantarse con contratos estables. | P-033 a P-035 en staging; permisos de navegador, consentimientos, borrado y visualización probados. |
| Semanas 24-28 orientativas / G7 | Evaluación P-036, correcciones y cierre P-038. | Aceptación integral de E2, métricas por modalidad y operación transferida. |

**Ruta crítica:** alcance -> persistencia y carga -> resolución de dependencias y lectura jurídica -> publicación consistente -> evaluación útil del chat -> piloto y aceptación. La revisión jurídica empieza con los primeros lotes, no al final del desarrollo. Fuentes externas bloqueadas o falta de firma pueden mover la fecha aunque el código esté terminado.

**Trabajo en paralelo permitido:** frontend contra contratos acordados; QA prepara casos antes del RAG; plataforma habilita CI y staging mientras ingesta completa fuentes. Un integrador administra el orden de migraciones, contratos API y promoción. Cada agente trabaja en archivos o ramas definidos para reducir conflictos.

**Demostraciones intermedias:** G1 acredita persistencia; G3 muestra un servicio de revisión utilizable con capacidades explícitas. Si G2 o G4 mantienen dependencias críticas, se puede realizar un piloto acotado etiquetado como tal, pero no cerrar el proyecto integral ni declarar el corpus 100% completo.

**Regla de terminación de una historia:** código integrado, prueba relevante aprobada, migración y contrato consistentes, evidencia enlazada, documentación operativa y demostración en el entorno que corresponda. «Funciona en el contenedor» no cierra una historia que exige un servicio remoto o una corrida programada.

## 12. Equipo, esfuerzo y riesgos

| Responsabilidad | Asignación propuesta |
| --- | --- |
| Producto y alcance | Pedro o delegado formal: prioridades, aceptación funcional y control de cambios. |
| Integración técnica | Un responsable humano apoyado por el agente integrador: arquitectura, migraciones, contratos, PR y gates. |
| Datos e ingesta | Un perfil equivalente a tiempo completo: SQL, fuentes, carga, trazabilidad y dependencias; colaboración de curación. |
| Backend y RAG | Un perfil equivalente a tiempo completo: API, reglas, recuperación, generación y evaluación técnica. |
| Frontend y plataforma | Un perfil equivalente a tiempo completo, con apoyo especializado puntual: UX, backoffice, despliegue y operación. |
| QA | Dedicación aproximada de medio tiempo, reforzada en aceptación; pruebas independientes y evidencias. |
| Jurídico / curación | Responsable designado, aproximadamente medio tiempo durante la curación, con disponibilidad de firma. La carga depende de complejidad y fuentes faltantes. |

Los nombres de agentes instalados no se presuponen: Claude Code debe descubrirlos y mapear estas capacidades. Los agentes preparan cambios, pruebas y expedientes; la responsabilidad institucional, aceptación y criterio jurídico permanecen en personas designadas.

**Esfuerzo total orientativo actualizado: 131-219 días-persona**, antes de la reserva. Conserva 85-143 días-persona de la versión 1.0 y agrega 46-76 para P-025 a P-038. El incremento cubre diferencias de alcance, sin volver a presupuestar la recuperación básica, el motor ni el front previstos. Con reserva del 20%: 157,2-262,8 días-persona. El backlog adjunto tiene rangos en días-persona de ocho horas por historia. Representa trabajo de implementación, integración, revisión y pruebas del tramo restante, con incertidumbre inicial. No se suman esos días como duración calendario: hay paralelismo y capacidades distintas. Reservar un 20% adicional para incertidumbre de fuentes y retrabajo; P-001 recalibra los rangos frente a la línea de base.

**Asignaciones adicionales:** diseño del front y del lenguaje, validación de comprensión; responsable de la cola de atención; revisión de privacidad para voz/documentos; QA de interacción y modalidades. Estos esfuerzos están contemplados en los rangos de las historias nuevas, y se deben asignar antes de prometer fecha. P-032 estima la ampliación de experiencia sobre P-015, sin incluir conectores de mensajería.

**Presupuesto en G0:** trabajo = días por perfil × tarifa acordada; operación = base + aplicación/jobs + objetos/copias + transferencia + logs + embeddings + tokens + minutos de audio + OCR. No se presupuestan servicios de mensajería. No se asignan tarifas no verificadas; cotizar por escenario de uso y por cuenta real. El primer sprint entrega cotización, escenarios de consultas/día, límites de gasto y responsable pagador. Este plan no contrata recursos pagos.

| Riesgo concreto | Tratamiento y dueño |
| --- | --- |
| Fuente bloqueada o incompleta | Fuente oficial alternativa, captura permitida o gestión con titular; mantener brecha visible. Ingesta y producto. |
| Reglas candidatas sin firma | Lotes priorizados, expediente con literal y pruebas; calendarizar revisión desde semana 2. Responsable jurídico. |
| Corte nuevo pierde versiones anteriores | Pertenencia explícita y prueba A + B entre releases. Integración / datos. |
| Saturación de conexiones | Presupuesto por todos los engines/roles, transacciones cortas y carga sobre Neon. Plataforma / DBA. |
| Respuesta convincente sin respaldo | Recuperación filtrada, verificación de citas y revisión experta; bloqueo de afirmaciones críticas. RAG / QA. |
| Pérdida de base u originales | Persistencia externa, manifiesto consistente y restauración cronometrada. Operación. |
| Alcance que crece sin control | Denominador versionado y análisis de impacto por nueva dependencia; no declarar «todo» sin definir universo. Producto. |
| Dependencia de cuentas/modelo | Resolver acceso, región, cuotas, retención y responsable pagador en G0; no confundir artefactos listos con infraestructura activa. Plataforma. |

## Anexo A. Historias de ejecución del producto

Las 24 historias originales conservan su identidad; P-015 concreta el front propio y P-023/P-024 incorporan la aceptación de E1. Las 14 historias del Anexo B agregan el alcance v1.1. Sus estados siguen PLANIFICADA hasta reconciliar evidencia en P-001.

### P-001 · Consolidar una línea de base reproducible

**Capacidad:** Integración. **Prioridad:** P0. **Esfuerzo:** 2-3 días-persona. **Dependencias:** Ninguna. **Trazabilidad previa:** HU-001, HU-035, HU-040.

Como responsable del producto quiero un inventario conciliado y una rama de integración para saber qué existe y qué falta.

1. Dado el commit 1c19c62 y los cambios locales, al auditar el repositorio se preserva el trabajo y cada cambio queda incluido o descartado con motivo en un PR; no se sobrescribe la rama original.
2. Dado el manifiesto de 83 recursos y las incorporaciones posteriores, al conciliar se obtiene un denominador versionado con cada ID, URL, tipo, beneficio, responsable, estado y criterio de cierre.
3. Dadas las pruebas existentes, al ejecutar la línea de base se registran commit, entorno, total recogido, aprobadas, fallidas y omitidas; una omisión de integración no se cuenta como aprobación.

**Evidencia de aceptación:** Acta de línea de base; Inventario versionado; PR y reporte de pruebas.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-002 · Provisionar PostgreSQL persistente en Neon

**Capacidad:** Plataforma / DBA. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-001. **Trazabilidad previa:** HU-002, HU-037.

Como operador quiero una base administrada que conserve el corpus cuando reinicie o reemplace la aplicación.

1. Dada la cuenta Neon conectada, al provisionar se documentan proyecto, región, versión PostgreSQL, ramas de revisión y producción, límites y propietario; las credenciales se guardan fuera de Git.
2. Dada una carga controlada, al terminar el proceso y desplegar una instancia nueva se conservan filas, versiones y referencias a originales; la prueba usa la base remota.
3. Dadas las conexiones por instancia, al medir con carga se respeta el presupuesto conjunto de pools, jobs y reserva; migraciones y operaciones de sesión usan conexión directa.

**Evidencia de aceptación:** Identificador del proyecto y ramas; Prueba de persistencia; Medición de conexiones con límites reales.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-003 · Migrar el esquema y aislar permisos

**Capacidad:** Datos SQL. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-002. **Trazabilidad previa:** HU-002, HU-022, HU-033.

Como mantenedor quiero migraciones versionadas y permisos mínimos para evolucionar el esquema sin exponer datos de revisión.

1. Dada una rama Neon vacía y otra con la versión anterior, al ejecutar Alembic ambas llegan al mismo esquema y alembic check no detecta deriva.
2. Dado el rol lector, al intentar modificar tablas o leer cuarentena se recibe denegación; revisor, publicador, ingesta y migrador tienen únicamente los permisos documentados.
3. Dadas claves, intervalos temporales y evidencias, al insertar huérfanos, intervalos imposibles o identidades duplicadas se rechazan por restricciones y pruebas sobre PostgreSQL real.

**Evidencia de aceptación:** Migraciones ascendentes y estrategia de reversión; Diccionario regenerado; Matriz y pruebas SQL de permisos.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-004 · Conservar originales fuera del contenedor

**Capacidad:** Ingesta / Plataforma. **Prioridad:** P0. **Esfuerzo:** 2-4 días-persona. **Dependencias:** P-002. **Trazabilidad previa:** HU-004, HU-007, HU-037.

Como curador quiero recuperar el original exacto de cada afirmación aunque cambie la página o se borre el contenedor.

1. Dado un HTML, PDF o anexo, al capturarlo se guardan bytes, SHA-256, tipo, tamaño, fecha, URL solicitada y final, resultado HTTP y versión del adaptador en almacenamiento persistente.
2. Dadas dos capturas iguales y una distinta, al reingestar se deduplican los bytes iguales y se conserva la nueva versión sin sobrescribir la evidencia anterior.
3. Dada una referencia a un objeto, al recuperarlo desde otra instancia el hash coincide; si falta o difiere, se abre incidencia y se bloquea su publicación.

**Evidencia de aceptación:** Bucket privado y política de retención; Manifiesto de hashes; Prueba de lectura desde una instancia nueva.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-005 · Cargar el corpus de forma reanudable

**Capacidad:** Ingesta. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-003, P-004. **Trazabilidad previa:** HU-005, HU-021, HU-035.

Como operador quiero reconstruir y actualizar el corpus sin eliminar información ya aprobada.

1. Dada una base remota vacía, al ejecutar el bootstrap operativo se aplican migraciones, catálogo, importaciones y curación; el comando no contiene DROP DATABASE ni credenciales locales fijas.
2. Dada una interrupción entre lotes, al reanudar se conserva el checkpoint y no se duplican normas, evidencias, reglas o eventos.
3. Dadas las filas esperadas por cada importador, al cerrar la corrida se concilian leídas, nuevas, actualizadas, repetidas y rechazadas; cada error tiene causa y evidencia.

**Evidencia de aceptación:** Comando de bootstrap no destructivo; Reporte por fuente; Ensayo de interrupción y reanudación.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-006 · Completar adaptadores y fuentes operativas

**Capacidad:** Scraping / Datos. **Prioridad:** P0. **Esfuerzo:** 5-8 días-persona. **Dependencias:** P-005. **Trazabilidad previa:** HU-006, HU-007, HU-019, HU-020, HU-026, HU-027.

Como persona que consulta quiero textos, requisitos, montos, plazos y canales provenientes de fuentes oficiales actualizadas.

1. Dada cada fuente del manifiesto, al ejecutarla se cumple su historia individual y se verifica paginación, cobertura de artículos y anexos, contenido esperado y destino SQL; un HTTP 200 no basta.
2. Dado un bloqueo, CAPTCHA, URL caída o documento ilegible, se conserva el fallo, se busca una representación oficial permitida y se mantiene la capacidad afectada como pendiente hasta resolverla.
3. Dadas las fuentes de montos y calendarios, al cargar se registra período, fecha de verificación y beneficio; un importe histórico nunca reemplaza el actual por ser el último descargado.

**Evidencia de aceptación:** Evidencia de las historias por fuente; Fixtures de regresión por familia; Conciliación y registro de bloqueos.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-007 · Resolver citas, vigencia y relaciones

**Capacidad:** Curación / Datos SQL. **Prioridad:** P0. **Esfuerzo:** 4-7 días-persona. **Dependencias:** P-005. **Trazabilidad previa:** HU-009, HU-010, HU-023, HU-024.

Como analista jurídico quiero distinguir la norma consultada, sus versiones y las normas que cita para reconstruir su efecto en una fecha.

1. Dadas F33, F19, F23 y F40, al extraer se preserva la identidad de la norma principal y se crean referencias independientes a D01-D06 con artículo, dirección, evidencia y tipo pendiente de confirmar.
2. Dadas referencias ambiguas o ciclos, al resolver se conserva cada identidad jurisdiccional, se evita recursión infinita y se mantiene una cola auditable de dependencias sin texto.
3. Dadas una modificación, una derogación y dos fechas de consulta, al consultar se devuelve la versión aplicable al período y conocida en ese momento; la fecha de descarga no decide vigencia.

**Evidencia de aceptación:** Seis relaciones iniciales verificadas; Pruebas históricas y de identidad; Grafo y pendientes conciliados.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-008 · Completar las siete dimensiones por norma y beneficio

**Capacidad:** Análisis funcional / Curación. **Prioridad:** P0. **Esfuerzo:** 6-10 días-persona. **Dependencias:** P-006, P-007. **Trazabilidad previa:** HU-011, HU-012, HU-013, HU-015, HU-017, HU-018.

Como especialista quiero una ficha completa y trazable para explicar a quién alcanza una norma y qué derechos o condiciones establece.

1. Dada una versión y cada beneficio que regula, al cerrar su ficha existen siete dimensiones con valores tipados o estados explícitos; ningún vacío se interpreta como respuesta negativa.
2. Dado un valor afirmado, al abrir su evidencia se accede a norma, versión, artículo y fragmento exacto; las salvaguardas de no exclusión se distinguen de la preservación documental.
3. Dadas condiciones insuficientes o contradictorias, se registra el límite y se bloquea únicamente la capacidad dependiente; no se fabrican valores para lograr completitud.

**Evidencia de aceptación:** Fichas pobladas; Matriz dimensión-beneficio-evidencia; Informe de completitud semántica.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-009 · Operar el circuito de revisión humana

**Capacidad:** Backend / Curación. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-003, P-008. **Trazabilidad previa:** HU-024, HU-036.

Como revisor quiero comparar cada interpretación con el original y dejar una decisión identificada y fundamentada.

1. Dada una regla candidata, al revisarla se muestran literal, interpretación, condición, dependencias, vigencia y controles; aprobar, rechazar o pedir cambios exige actor autenticado y fundamento.
2. Dadas dos revisiones simultáneas, la segunda decisión sobre una versión desactualizada recibe conflicto y no sobrescribe la primera.
3. Dada una aprobación, se actualizan coherentemente estado y marca de revisión, se preserva auditoría y la regla todavía no aparece como publicada hasta pasar el corte de publicación.

**Evidencia de aceptación:** API de decisiones; Auditoría con actor real; Pruebas de concurrencia y transición.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-010 · Resolver el expediente jurídico del alcance

**Capacidad:** Responsable jurídico. **Prioridad:** P0. **Esfuerzo:** 6-10 días-persona. **Dependencias:** P-009. **Trazabilidad previa:** HU-036.

Como responsable jurídico quiero decidir todas las reglas que sostienen el servicio para autorizar su uso con un alcance definido.

1. Dado el expediente inicial de 166 candidatas, al conciliar se confirma el total actual y cada regla queda aprobada, rechazada con reemplazo cuando corresponda, informativa o devuelta a corrección.
2. Dadas las 67 reglas inicialmente sin condición ejecutable, se decide cuáles requieren formalización y pruebas, cuáles sólo explican y cuáles no tienen evidencia suficiente; no se aprueban en lote por un agente.
3. Dado cada beneficio del alcance público, se firma una matriz de capacidades habilitadas con evidencias y excepciones; una dependencia crítica pendiente impide declarar completa esa capacidad.

**Evidencia de aceptación:** Expediente decidido; Casos jurídicos positivos y negativos; Acta HU-036 por beneficio y capacidad.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-011 · Publicar cortes completos y reversibles

**Capacidad:** Datos SQL / Backend. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-007, P-009. **Trazabilidad previa:** HU-025, HU-031.

Como publicador quiero un corte consistente para que las consultas no mezclen versiones ni pierdan normas sin cambios.

1. Dado un primer corte con A y un segundo que incorpora B, ambos A y B son recuperables en el segundo; el primero conserva su contenido histórico.
2. Dada una dependencia no aprobada, obsoleta o en conflicto crítico, al publicar se rechaza la capacidad afectada y no queda un corte parcialmente visible.
3. Dado un corte válido, al publicar o volver al anterior cambian de forma atómica el manifiesto, la pertenencia de versiones y los índices de consulta; los originales no se borran.

**Evidencia de aceptación:** Migración de pertenencia release-versiones si corresponde; Prueba de dos cortes y rollback; Manifiesto con hash y firma.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-012 · Implementar recuperación híbrida trazable

**Capacidad:** RAG / Datos SQL. **Prioridad:** P0. **Esfuerzo:** 5-8 días-persona. **Dependencias:** P-011. **Trazabilidad previa:** HU-031, HU-032.

Como persona que consulta quiero encontrar la evidencia pertinente aunque use palabras distintas de las del texto legal.

1. Dado un corte publicado, se indexan fragmentos por artículo o unidad con versión, jurisdicción, beneficio y vigencia; el embedding conserva modelo, dimensión y hash del texto.
2. Dada una consulta, se combinan búsqueda textual y vectorial, se fusionan duplicados y se filtran permisos y temporalidad antes de entregar contexto al modelo.
3. Dado el conjunto de evaluación congelado, la recuperación alcanza Recall@5 >= 90% en preguntas respondibles y no recupera como servible contenido candidato o fuera del corte.

**Evidencia de aceptación:** Índices PostgreSQL y pgvector; Comparación lexical frente a híbrido; Reporte de Recall@5 segmentado.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-013 · Generar respuestas con citas y abstención

**Capacidad:** RAG / Backend. **Prioridad:** P0. **Esfuerzo:** 4-7 días-persona. **Dependencias:** P-012. **Trazabilidad previa:** HU-032.

Como persona que consulta quiero una explicación comprensible respaldada por evidencia y una respuesta honesta cuando esa evidencia falta.

1. Dado contexto suficiente, el modelo configurado genera una respuesta estructurada con citas a fragmentos recuperados; se rechazan citas inventadas, enlaces ajenos al contexto y números sin soporte.
2. Dadas instrucciones maliciosas en una fuente o en el chat, el modelo no cambia permisos, no ejecuta SQL libre y no trata documentos como instrucciones del sistema.
3. Dadas falta de evidencia, caída del proveedor o contexto insuficiente, el chat explica el límite, ofrece una alternativa útil y registra el modo de respuesta; un extracto de respaldo no se presenta como generación activa.

**Evidencia de aceptación:** Proveedor real probado en staging; Validadores y evaluación de fidelidad; Pruebas de fallo y prompt injection.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-014 · Evaluar condiciones y datos operativos con lógica tipada

**Capacidad:** Backend / Dominio. **Prioridad:** P0. **Esfuerzo:** 4-7 días-persona. **Dependencias:** P-008, P-011. **Trazabilidad previa:** HU-014, HU-016, HU-018, HU-029, HU-030.

Como persona que consulta quiero orientación preliminar sobre condiciones, importes y plazos sin que el modelo los improvise.

1. Dadas reglas publicadas y hechos suficientes, el motor obtiene un resultado reproducible con reglas y parámetros usados; el modelo sólo explica el resultado.
2. Dado un dato faltante, se pregunta el mínimo necesario y se conserva DESCONOCIDO; no se transforma falta de información en inelegibilidad.
3. Dado un monto por fórmula o un plazo hábil, se usa parámetro y calendario vigentes y versionados; si faltan, se abstiene del cálculo y no reutiliza un valor anterior.

**Evidencia de aceptación:** Contratos OpenAPI; Pruebas de límites, fórmulas y calendarios; Trazas con reglas y parámetros.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-015 · Completar el front conversacional

**Capacidad:** Frontend / UX. **Prioridad:** P0. **Esfuerzo:** 5-8 días-persona. **Dependencias:** P-013, P-014, P-017. **Trazabilidad previa:** HU-029, HU-030, HU-032.

Como persona que busca un derecho quiero conversar desde el celular, entender la respuesta y acceder a sus fuentes y próximos pasos.

1. Dada una consulta, se puede seleccionar o aclarar jurisdicción, fecha y beneficio, aportar hechos mínimos, cancelar, reintentar y comenzar de nuevo sin perder el control de la conversación.
2. Dada una respuesta, se muestran explicación, fuentes abribles, fecha y estado de información, advertencias pertinentes y canal oficial; errores y abstenciones tienen mensajes comprensibles.
3. Dado teclado, lector de pantalla y un ancho de 360 px, el flujo principal mantiene foco, etiquetas, contraste y mensajes accesibles; cerrar sesión borra credenciales y contenido privado visible.
4. El acceso ciudadano es el front web conversacional propio de ACIJ; P-032 amplía sus componentes de contexto, fuentes y acciones. El backoffice de revisión tiene un acceso separado.

**Evidencia de aceptación:** URL de staging integrada; E2E del recorrido ciudadano; Revisión manual de accesibilidad.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-016 · Completar el backoffice de datos y revisión

**Capacidad:** Frontend / Curación. **Prioridad:** P0. **Esfuerzo:** 4-6 días-persona. **Dependencias:** P-009, P-011, P-017. **Trazabilidad previa:** HU-012, HU-024, HU-034, HU-036.

Como curador quiero resolver pendientes y publicar desde una interfaz conectada al mismo corpus que consulta el chat.

1. Dado un rol autorizado, se puede buscar normas, abrir las siete dimensiones, comparar versiones, revisar reglas y dependencias, filtrar pendientes y registrar decisiones con evidencia.
2. Dado un publicador, ve el resumen del corte, sus controles y capacidades afectadas antes de confirmar; un revisor sin ese rol no puede publicarlo.
3. Dado el tablero de calidad, cada indicador permite abrir los registros que lo componen; los conteos se consultan en la base y no provienen de constantes de demostración.

**Evidencia de aceptación:** URL de backoffice con roles; E2E revisión-publicación; Tablero conciliado con SQL.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-017 · Aplicar identidad, privacidad y protección del servicio

**Capacidad:** Seguridad / Backend. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-003. **Trazabilidad previa:** HU-033.

Como responsable del servicio quiero acceso administrativo individual y consultas ciudadanas que recolecten sólo lo necesario.

1. Dado un usuario administrativo, la identidad validada determina los roles y actor auditado; no se acepta un X-Actor libre como identidad de producción y se prueba revocación de sesión.
2. Dada una consulta ciudadana, no se exigen DNI, domicilio preciso ni datos de menores identificables; los hechos mínimos y la conversación tienen una política explícita de retención.
3. Dado abuso o una sesión no autorizada, se aplican límites y permisos en servidor, secretos fuera del front, protección XSS/CSRF según el mecanismo de sesión y logs sin texto sensible.

**Evidencia de aceptación:** Modelo de amenazas acotado; Pruebas de autorización y revocación; Política de datos y retención.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-018 · Hacer obligatoria la integración continua

**Capacidad:** QA / Plataforma. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-001. **Trazabilidad previa:** HU-002, HU-037, HU-040.

Como integrador quiero pruebas automáticas por cambio para impedir que un repositorio aparente estar sano por controles ejecutados a mano.

1. Dado un push o PR, CI ejecuta Ruff, pruebas unitarias, integración en PostgreSQL, migraciones desde cero, alembic check y construcción del contenedor.
2. Dada una base inaccesible, una prueba crítica omitida o un fallo de contrato, el trabajo falla; toda exclusión tiene inventario, motivo y decisión explícita.
3. Dado un PR aprobado, los resultados quedan vinculados al SHA y se exigen para integrar en la rama estable; se incorporan E2E y evaluaciones de RAG al existir esos componentes.

**Evidencia de aceptación:** Workflow ejecutado en GitHub; Checks obligatorios; Artefactos de resultados por commit.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-019 · Desplegar revisión y producción

**Capacidad:** Plataforma. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-002, P-004, P-017, P-018. **Trazabilidad previa:** HU-037.

Como usuario y operador quiero URLs estables con la aplicación y la API funcionando fuera del entorno de desarrollo.

1. Dada una imagen inmutable validada, el pipeline despliega front y API en Cloud Run con secretos por entorno, identidad de servicio y conexión a Neon; la imagen no contiene credenciales.
2. Dada una instancia nueva, readiness verifica esquema compatible y conexiones; producción además exige el corte habilitado y las capacidades declaradas; liveness se mantiene separado.
3. Dada una versión fallida, se revierte la imagen sin borrar la base y se demuestra compatibilidad de migraciones; la URL HTTPS funciona desde una red externa.

**Evidencia de aceptación:** URLs y revisión desplegada; Configuración operativa versionada; Prueba externa y rollback.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-020 · Programar monitoreo y entrega de eventos

**Capacidad:** Monitoreo / Plataforma. **Prioridad:** P0. **Esfuerzo:** 2-4 días-persona. **Dependencias:** P-006, P-019. **Trazabilidad previa:** HU-026, HU-027, HU-028.

Como operador quiero que las fuentes se revaliden automáticamente y que los cambios lleguen a la cola de revisión.

1. Dado Cloud Scheduler, se dispara cada hora un job que ejecuta bn monitoreo ciclo y respeta la frecuencia individual de cada fuente; invocación y ejecución quedan identificadas.
2. Dados dos disparos simultáneos, un bloqueo o lease con vencimiento impide procesamiento duplicado; se prueban tiempo máximo, reintentos acotados y recuperación tras caída.
3. Dado un cambio relevante, se propaga impacto a beneficios, reglas e índices, se marca la frescura y se entrega un evento idempotente al consumidor configurado; un evento pendiente no se registra como entregado.

**Evidencia de aceptación:** Scheduler instalado; Dos ciclos automáticos consecutivos; Ensayo de solapamiento y entrega de evento.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-021 · Medir salud, calidad, costos y nivel de servicio

**Capacidad:** Observabilidad / QA. **Prioridad:** P0. **Esfuerzo:** 2-4 días-persona. **Dependencias:** P-019, P-020. **Trazabilidad previa:** HU-034, HU-037.

Como responsable operativo quiero detectar fallos y degradaciones antes de que afecten sostenidamente a las consultas.

1. Dado tráfico real o de ensayo, se registran latencia, errores, abstenciones por causa, tokens, costo, recuperación, frescura y conexiones, con request_id y sin conversación sensible en logs.
2. Dado un job atrasado, fallo repetido, corte inválido o presupuesto agotado, se genera una alerta hacia el canal operativo previamente configurado y se demuestra su recepción.
3. Dado el tablero, se distingue una abstención correcta de una respuesta resuelta; los objetivos técnicos se presentan como mediciones con período, denominador y carga.

**Evidencia de aceptación:** Tablero y alertas probadas; Panel de gasto y límites; Runbook de incidentes.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-022 · Respaldar y restaurar base más documentos

**Capacidad:** DBA / Plataforma. **Prioridad:** P0. **Esfuerzo:** 2-4 días-persona. **Dependencias:** P-005, P-019. **Trazabilidad previa:** HU-037.

Como responsable del corpus quiero recuperar una versión consistente ante pérdida o corrupción de datos y archivos.

1. Dada la retención configurada y documentada en Neon, se generan respaldos recuperables de base y originales con manifiesto consistente; una rama de desarrollo no se considera copia independiente.
2. Dado un ensayo aislado, se restaura a una base nueva y se recuperan los objetos referenciados; coinciden conteos, hashes, permisos, releases y respuestas de control.
3. Dados los objetivos iniciales RPO \<= 24 h y RTO \<= 4 h, se mide el cumplimiento y se registra cada limitación del plan contratado; si no cumple, no pasa el gate operativo.

**Evidencia de aceptación:** Política de respaldo y retención; Informe de restauración cronometrada; Hashes y consultas de control.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-023 · Validar el recorrido completo con pruebas independientes

**Capacidad:** QA / Jurídico. **Prioridad:** P0. **Esfuerzo:** 5-8 días-persona. **Dependencias:** P-010, P-012, P-013, P-014, P-015, P-016, P-020, P-021, P-022, P-025, P-028, P-029, P-030, P-031, P-032, P-037. **Trazabilidad previa:** HU-036, HU-037, HU-038, HU-039, HU-040.

Como responsable de calidad quiero demostrar que el servicio funciona con datos reales y resiste errores relevantes.

1. Dado staging, se prueba fuente -> captura -> SQL -> revisión -> publicación -> recuperación -> chat -> cita, y una actualización que invalida o reemplaza la respuesta anterior.
2. Dado un conjunto congelado de al menos 150 consultas anotadas, se alcanzan los umbrales de recuperación, fidelidad, no exclusión y utilidad de este plan; los casos no se ajustan para acomodar la salida.
3. Dadas 20 conversaciones concurrentes durante 30 minutos y fallos inducidos de proveedor, base y fuente, se verifican latencia, límites, recuperación y ausencia de exposición de datos pendientes.
4. La aceptación E1 incluye el front propio P-032, correcciones de hechos, continuidad, lenguaje claro, verificación antes de emitir y derivación con estado real; las capacidades E2 se aceptan en P-036/P-038.

**Evidencia de aceptación:** Reporte de aceptación reproducible; E2E y evaluación RAG; Carga y fallos con evidencias.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-024 · Realizar piloto, traspaso y cierre de E1

**Capacidad:** Producto / Operación. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-023. **Trazabilidad previa:** HU-036, HU-040.

Como responsable del proyecto quiero recibir un servicio operable y un alcance explícitamente aceptado, con responsables y evidencia.

1. Dado un piloto con al menos ocho participantes que representen consulta, acompañamiento y revisión, al ejecutar tareas acordadas se documenta comprensión, utilidad, errores y correcciones.
2. Dadas las evidencias G0-G5 y los criterios E1 ampliados, producto, jurídico y operación aceptan E1; E2 conserva su backlog y no se declara cerrada hasta P-038/G7.
3. Dado el traspaso, otra persona opera una ingesta, revisa una regla, publica un corte, recibe una alerta y restaura usando la documentación; quedan accesos institucionales y responsables de soporte.

**Evidencia de aceptación:** Acta de aceptación; URL pública o acceso institucional acordado; Runbook, capacitación y propiedad de cuentas.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

## Anexo B. Nuevas historias del chatbot ampliado

P-025 a P-038 agregan 46-76 días-persona orientativos. E1 se valida en P-023/P-024; E2 se cierra en P-036/P-038. Cada historia indica qué capacidad base amplía para evitar duplicación.

### P-025 · Orquestar conversación y memoria mínima

**Capacidad:** Backend / Diseño conversacional. **Prioridad:** P0. **Esfuerzo:** 4-6 días-persona. **Dependencias:** P-013, P-014, P-027, P-037. **Entrega:** E1. **Amplía:** P-013, P-014, P-015.

Como persona que consulta quiero explicar mi situación, corregir datos y retomar el tema sin repetir lo que ya dije.

1. Dado un diálogo con cambios de tema y correcciones, el estado conserva intención, jurisdicción, fecha y hechos mínimos con origen y confirmación; el último dato confirmado reemplaza al anterior e invalida resultados dependientes.
2. Dada una conversación incompleta, LangGraph solicita sólo el dato que cambia la orientación y permite no responder, corregir o empezar de nuevo; un dato desconocido nunca se transforma en falso.
3. Dadas dos sesiones simultáneas, reintentos, expiración o cancelación, no se mezclan hechos ni se duplica una acción; los checkpoints respetan TTL y permisos, sin historial permanente por defecto.

**Evidencia de aceptación:** Pruebas de diálogo de varios turnos; Esquema de estado y diagrama ejecutable; Ensayo de aislamiento y expiración.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-026 · Desambiguar beneficios y reordenar evidencia

**Capacidad:** RAG / Datos. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-012. **Entrega:** E1. **Amplía:** P-012.

Como persona que desconoce el nombre del programa quiero encontrar información pertinente a mi necesidad.

1. Dadas expresiones cotidianas, faltas de ortografía y programas similares, la búsqueda híbrida consulta sólo el corte habilitado y emplea fichas comparativas para diferenciar población, territorio, trámite y período.
2. Dada ambigüedad entre candidatos, un reranker o paso LLM acotado mejora el orden o solicita aclaración; nunca selecciona por similitud una jurisdicción, cohorte o versión inaplicable.
3. Dado el conjunto congelado, se compara recuperación base y ampliada por dominio, negación, fecha y excepción; se publica calidad, latencia y costo. La aprobación requiere ausencia de regresión crítica y mejora demostrada o simplificación justificada.

**Evidencia de aceptación:** Benchmark comparativo y configuración versionada; Trazas con candidatos y evidencia; Pruebas de filtros anteriores y posteriores al ranking.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-027 · Incorporar un adaptador de modelos actualizado

**Capacidad:** Backend / RAG. **Prioridad:** P0. **Esfuerzo:** 2-4 días-persona. **Dependencias:** P-001, P-017. **Entrega:** E1. **Amplía:** P-013.

Como responsable técnico quiero cambiar el modelo sin alterar reglas, contratos ni datos del proyecto.

1. Dado un proveedor habilitado, la configuración registra modelo y versión exacta, capacidades, región, endpoint, límites, política de datos y costo medido; se compara el candidato vigente con una alternativa de menor costo sobre el mismo conjunto.
2. Dada una llamada, Responses API o un adaptador equivalente devuelve JSON validado por Pydantic; rechazo del proveedor, timeout o salida truncada se manejan explícitamente y no se muestran como respuesta jurídica.
3. Dado un cambio de proveedor/modelo/prompt, las pruebas preceden la promoción; una falla revierte a la versión aprobada o a respuesta estructurada sin generador, sin enviar datos automáticamente a otro proveedor.

**Evidencia de aceptación:** Registro de modelos y decisión de selección; Pruebas contractuales del adaptador; Medición de costo y ensayo de reversión.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-028 · Verificar cada respuesta antes de mostrarla

**Capacidad:** Backend / Jurídico / QA. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-013, P-014, P-026, P-027. **Entrega:** E1. **Amplía:** P-013, P-014.

Como persona que consulta quiero una respuesta clara cuyas afirmaciones estén respaldadas.

1. Dadas afirmaciones sobre requisitos, plazos, importes o derechos, cada una apunta a evidencia del corte y a su localizador; fechas y cálculos provienen de funciones tipadas. Se verifica respaldo semántico además de existencia del enlace.
2. Dadas contradicciones, falta de evidencia o citas ajenas al contexto, se retiene la afirmación afectada y se ofrece una aclaración o derivación útil; los datos independientes que sí están habilitados pueden responderse.
3. Dado streaming o síntesis de voz, ningún texto sustantivo se emite antes de verificarlo; se pueden emitir estados de progreso sin contenido jurídico. Las instrucciones en documentos, OCR o resultados de herramientas no amplían permisos.

**Evidencia de aceptación:** Contrato de afirmaciones y evidencias; Casos de cita real pero conclusión incorrecta; Prueba de bloqueo antes de emisión.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-029 · Limpiar y versionar el lenguaje conversacional

**Capacidad:** Diseño conversacional / Jurídico. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-015, P-028. **Entrega:** E1. **Amplía:** P-015.

Como persona con distinta experiencia digital quiero entender qué puedo hacer y cuál es el próximo paso.

1. Dado el inventario de mensajes, cada pieza tiene intención, condición de uso, texto anterior, texto corregido, variables, fuente cuando corresponda, responsable y versión; se eliminan duplicados editoriales sin borrar versiones jurídicas.
2. Dado un caso cotidiano, la respuesta utiliza voseo consistente, explicación breve, una pregunta necesaria por turno y ampliación opcional; preserva negaciones, excepciones, cuantías y plazos, sin prometer resultados no acreditados.
3. Dada una queja, una situación sensible o baja alfabetización, se adapta el tono y se ensaya comprensión con personas usuarias; nunca se bloquea una consulta legítima sólo por enojo, errores de escritura o vocabulario informal.

**Evidencia de aceptación:** Catálogo antes/después y guía de estilo; Rúbrica de comprensión y no exclusión; Pruebas de variables, términos y tono.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-030 · Orientar desde situaciones y armar próximos pasos

**Capacidad:** Producto / Backend / Jurídico. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-014, P-025, P-028. **Entrega:** E1. **Amplía:** P-014, P-015.

Como persona que busca ayuda quiero conocer alternativas del corpus y los pasos para avanzar.

1. Dada una necesidad como vivienda, escolaridad o discapacidad, se muestran opciones del alcance con jurisdicción, condiciones y razones de pertinencia; no se presenta el catálogo como exhaustivo ni se infiere información sensible.
2. Dada una evaluación, se diferencian condiciones satisfechas, no satisfechas y desconocidas; se revisan excepciones aplicables y vías de subsanación con respaldo antes de comunicar un resultado preliminar desfavorable.
3. Dado el resultado, se ofrece una lista de próximos pasos y canales verificados con fecha; un resumen descargable es voluntario, no crea expediente ni equivale a presentar un trámite o garantizar una prestación.

**Evidencia de aceptación:** Casos de orientación por necesidad; Pruebas ternarias y de alternativas; Demostración de resumen y canales.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-031 · Derivar con contexto a atención humana

**Capacidad:** Backend / Operación. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-015, P-017, P-025. **Entrega:** E1. **Amplía:** P-015, P-016.

Como persona que necesita acompañamiento quiero pasar a un equipo disponible sin explicar todo de nuevo.

1. Dada una solicitud de atención, se consulta un directorio con organización, temas, territorio, horarios y fecha de verificación; el chat distingue un canal externo de una cola operativa de ACIJ.
2. Dada una cola configurada y la conformidad de la persona, se muestra y confirma el resumen mínimo antes de enviarlo; sólo un acuse real permite decir que la solicitud quedó registrada.
3. Dada atención fuera de horario, rechazo o caída del conector, se informa el estado real y una alternativa verificada; no se inventan turnos, SLA ni números de caso. El bot pausa cuando toma la conversación un operador.

**Evidencia de aceptación:** Directorio y acuerdo de operación; Prueba de acuse, pausa y reanudación; Pruebas de autorización y fallos.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-032 · Diseñar e integrar el front web conversacional de ACIJ

**Capacidad:** Frontend / Diseño UX. **Prioridad:** P0. **Esfuerzo:** 4-7 días-persona. **Dependencias:** P-015, P-025, P-028, P-029. **Entrega:** E1. **Amplía:** P-015.

Como persona que busca orientación quiero conversar desde una interfaz web propia de ACIJ, ver las fuentes y corregir mi situación sin salir de la consulta.

1. Dada la entrada desde computadora o celular, la pantalla principal ofrece escritura libre y ejemplos opcionales, sin exigir cuenta ni teléfono. El recorrido funciona a 320 px, con zoom al 200%, teclado y lector de pantalla; los detalles jurídicos y el backoffice no compiten con la conversación.
2. Dada una respuesta verificada, el front presenta explicación breve, fuentes abribles con fragmento y fecha, próximos pasos y hechos confirmados que la persona puede corregir. Las opciones sugeridas no impiden escribir libremente; una corrección invalida las conclusiones dependientes y solicita reevaluación al servidor.
3. Dados envío, espera, cancelación, reintento, fallo o vencimiento, el front muestra el estado real, conserva el borrador sólo en memoria mientras la página está abierta y evita mensajes duplicados. Una respuesta de una solicitud cancelada no se añade al diálogo; sólo los eventos verificados muestran contenido sustantivo. Nueva consulta borra el estado activo y explica el alcance del borrado.

**Evidencia de aceptación:** Prototipo navegable y contrato de componentes/estados; Recorrido E2E desde entrada libre hasta fuente y próximos pasos; Pruebas de móvil, teclado, red lenta, cancelación y corrección.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-033 · Comprender audios y ofrecer lectura en voz en la web

**Capacidad:** Backend / UX. **Prioridad:** P1. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-025, P-028, P-029, P-032, P-037. **Entrega:** E2. **Amplía:** capacidad nueva.

Como persona a quien le cuesta escribir o leer quiero consultar por audio y escuchar una respuesta.

1. Dado un audio permitido, se transcribe mediante un adaptador de voz y se permite confirmar o corregir datos críticos; ruido, acentos, negaciones e importes dudosos no generan una conclusión automática.
2. Dada una respuesta ya verificada, la síntesis lee ese mismo contenido y conserva una versión textual con enlaces accesibles; no agrega instrucciones o conclusiones durante la lectura.
3. Dadas fallas o archivos excesivos, se ofrece texto y se aplican límites configurables de duración, tamaño y costo. El audio original se elimina según la política del adjunto y nunca se exige biometría de voz.

**Evidencia de aceptación:** Pruebas con ruido y distintas voces; Comparación texto/voz; Pruebas de límites y borrado.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-034 · Leer documentos aportados desde el front sin crear expediente

**Capacidad:** Backend / Datos / Privacidad. **Prioridad:** P1. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-004, P-025, P-028, P-032, P-037. **Entrega:** E2. **Amplía:** capacidad nueva.

Como persona que recibió una comunicación quiero entender su contenido y saber qué información necesito verificar.

1. Dado un PDF o imagen permitido, se valida MIME real, tamaño, páginas y contenido activo, se extrae texto/OCR en un entorno acotado y se indica página y fragmento; la lectura del archivo no prueba autenticidad ni vigencia jurídica.
2. Dado un documento con nombres, DNI, domicilio o datos de menores, se minimizan o tachan identificadores antes del envío externo; si no puede hacerse con fiabilidad se pide una versión sin esos datos. El archivo no se incorpora al corpus normativo ni a entrenamiento.
3. Dada una fecha de resolución o notificación, se distingue texto detectado de hecho confirmado y se solicita el dato que inicia el plazo; sólo el motor tipado, calendario y fuente aprobada permiten calcularlo. No se redacta ni presenta automáticamente un recurso.

**Evidencia de aceptación:** Casos de PDF, foto y OCR dudoso; Pruebas de separación de corpus y documentos privados; Ensayo de eliminación y fechas ambiguas.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-035 · Mostrar novedades voluntarias dentro del front

**Capacidad:** Backend / Frontend. **Prioridad:** P1. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-020, P-032, P-037. **Entrega:** E2. **Amplía:** capacidad nueva.

Como persona interesada en un tema quiero ver sus novedades aprobadas cuando consulte la web y poder dejar de seguirlo.

1. Dada una selección de temas, el front muestra novedades aprobadas del corpus sin exigir teléfono o correo. Guardar preferencias en este navegador requiere una opción expresa, plazo visible y borrado accesible; consultar un beneficio no activa seguimiento.
2. Dado un evento de cambio, sólo una publicación aprobada y pertinente al tema y territorio aparece en la sección Novedades del front, con fuente y fecha. No se infiere que cambió la elegibilidad individual ni se guarda el contenido de la conversación como preferencia.
3. Dados actualizaciones, recargas o baja, un identificador estable evita entradas duplicadas y se distinguen disponible, mostrada y abierta sin afirmar lectura efectiva. Las novedades se consultan al abrir la web; esta historia no incluye mensajes externos, correo ni notificaciones push.

**Evidencia de aceptación:** Pruebas de selección, consentimiento y borrado de preferencias; Evento publicado visible con fuente y fecha; Ensayo de recarga, duplicados y expiración.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-036 · Evaluar el front, el diálogo, la voz y los adjuntos

**Capacidad:** QA / Jurídico / UX. **Prioridad:** P1. **Esfuerzo:** 6-9 días-persona. **Dependencias:** P-031, P-032, P-033, P-034, P-035, P-021. **Entrega:** E2. **Amplía:** P-023.

Como responsable de calidad quiero comprobar las nuevas capacidades con casos independientes y personas usuarias.

1. Dado el conjunto base de 150 consultas, se agregan al menos 120 escenarios: 60 de varios turnos, 20 de interfaz/derivación/novedades, 20 de audio y 20 de documentos. Ajuste y evaluación final permanecen separados y los esperados son revisados por dominio.
2. Dada cada modalidad del front, pasan todos los casos críticos de negaciones, no exclusión, jurisdicción, fecha, cita, permiso, consentimiento e identidad; se informa calidad por estrato, latencia p95 y costo por orientación resuelta sin extrapolar resultados del piloto de Boti.
3. Dado un piloto de al menos 12 participantes adultos representativos, incluidos acompañantes y distintas habilidades digitales, se observa comprensión y finalización de tareas; se ensayan teclado/lector de pantalla, red lenta y fallas, con todos los defectos críticos corregidos.

**Evidencia de aceptación:** Conjunto mínimo de 270 casos y reporte reproducible; Pruebas del front por modalidad; Informe de comprensión con hallazgos.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-037 · Controlar memoria, datos y consentimientos

**Capacidad:** Seguridad / Backend. **Prioridad:** P0. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-017. **Entrega:** E1. **Amplía:** P-017.

Como persona que consulta quiero controlar mis datos y saber cuándo se guardan o se comparten.

1. Dada una consulta web, no se exige identidad y el estado mínimo expira tras 30 minutos de inactividad, con máximo de dos horas; cualquier recuperación entre sesiones requiere opción expresa y plazo separado, propuesto inicialmente en siete días.
2. Dados checkpoints, adjuntos y proveedores, se prueba eliminación, aislamiento, redacción y política de retención por sistema; los adjuntos originales tienen máximo inicial de 24 horas y no se copian a trazas. La retención contractual del proveedor se explica sin prometer borrado absoluto.
3. Dadas acciones de derivar, guardar una conversación, seguir temas o cargar documentos, cada permiso es independiente y revocable; documentos y hechos personales no se usan para aprendizaje ni publicación automática. Las preferencias locales de temas tienen un máximo inicial de siete días y no incluyen el historial ni identificadores personales. La trazabilidad técnica evita contenido identificable innecesario.

**Evidencia de aceptación:** Mapa de datos y tabla de retención; Pruebas de borrado y acceso cruzado; Registro de decisiones y consentimientos.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

### P-038 · Cerrar el despliegue de la ampliación

**Capacidad:** Producto / Operación. **Prioridad:** P1. **Esfuerzo:** 3-5 días-persona. **Dependencias:** P-024, P-036. **Entrega:** E2. **Amplía:** capacidad nueva.

Como responsable del proyecto quiero recibir la ampliación funcionando, con responsables, mediciones y una reversión probada.

1. Dadas E1 y E2, se habilitan capacidades del front mediante configuración después de sus pruebas y acuerdos de operación; la disponibilidad de la conversación por texto no acredita voz, documentos, novedades o atención humana.
2. Dado un cambio de modelo, prompt, índice o proveedor, se ejecuta evaluación antes de promoción, despliegue gradual y reversión; incidentes preservan evidencia mínima y detienen la capacidad afectada.
3. Dado el cierre G7, producto, jurídico y operación aceptan por capacidad las pruebas, costos y datos tratados; se entregan cuentas institucionales y runbook. Una dependencia externa abierta queda visible y no se marca ACEPTADA.

**Evidencia de aceptación:** Acta de aceptación de E2; Matriz de capacidades y responsables; Ensayo de reversión y traspaso.

**Estado:** PLANIFICADA. No aceptada por esta actualización documental.

## 13. Evidencias de aceptación y traspaso

El cierre no depende de una declaración del agente. Debe entregarse un expediente de aceptación con enlaces y resultados reproducibles.

| Entrega | Evidencia mínima |
| --- | --- |
| Código y versión | Commit integrado, PR, rama estable, imagen por digest y CI del mismo SHA. |
| Base | Proyecto y ramas Neon, esquema y migración, conteos por entidad, roles y prueba de persistencia. Sin credenciales en el informe. |
| Corpus | Manifiesto conciliado, carga por fuente, siete dimensiones, dependencias, originales y hashes; brechas resueltas o cambio de alcance explícito. |
| Jurídico | Acta HU-036 con beneficio, capacidad, reglas, versiones, vigencia, pruebas y responsable de aprobación. |
| Front y RAG | URLs, recorridos ciudadanos y de revisión, ejemplos con citas, evaluación congelada, utilidad y abstenciones por causa. |
| Operación | Scheduler instalado, ciclos y alertas recibidas, presupuesto de conexiones, métricas de carga y límites de gasto. |
| Recuperación | Base restaurada y objetos conciliados, RPO/RTO medidos y prueba de reversión de imagen y corte. |
| Transferencia | OpenAPI y diccionario actualizados, runbook, matriz de accesos, capacitación y responsables de soporte y renovación de cuentas. |

**Aceptación adicional v1.1:** mantener las 150 consultas base y agregar al menos 120 escenarios para P-036: 60 de varios turnos, 20 de interfaz/atención/novedades, 20 de audio y 20 de documentos. El conjunto final mínimo de 270 casos se divide entre ajuste y evaluación, con referencia experta. Medir por dominio y modalidad; cero fallos críticos en el conjunto es una condición de salida, no garantía de riesgo cero futuro. Los casos críticos del front por texto se ejecutan en E1; P-036 agrega las modalidades E2 y verifica ausencia de regresión.

**Evidencias E2:** permisos de micrófono y entrada alternativa por texto, transcripciones corregibles, equivalencia de voz y texto, documentos abiertos dentro del front, borrado de adjuntos/checkpoints, selección y eliminación de temas de novedades y costos por modalidad. P-036 incorpora un piloto con al menos 12 personas adultas; P-038 exige responsables operativos y aceptación por capacidad. Las metas de latencia de la sección 10 se mantienen para texto; audio y documentos se miden por duración/tamaño y se fijan objetivos propios antes de G6.

**Lista de verificación final:** ningún fallo crítico de integridad, identidad, vigencia, acceso, evidencia o no exclusión; ningún criterio omitido contabilizado como aprobado; ningún dato ficticio presentado como corpus real; ninguna aprobación jurídica automática; ningún servicio local presentado como despliegue. Debe existir al menos una consulta útil aprobada por cada capacidad declarada y la cobertura del alcance final debe estar conciliada.

**Uso del paquete:** leer este plan, importar las 38 historias del JSON y ejecutar la instrucción de inicio incluida. El JSON describe el trabajo pendiente; no crea incidencias en GitHub ni asigna personas por sí mismo. El tablero de ejecución debe vincular cada criterio a una prueba, archivo, corrida o acta.

**Control de cambios:** toda variación del universo, capacidad o criterio crítico registra motivo, impacto en esfuerzo y fechas y aprobación de producto y, si corresponde, de jurídico. Reducir el alcance permite una entrega menor explícita; no convierte retrospectivamente un bloqueo en un resultado completo.

## 14. Referencias y trazabilidad del plan

Las referencias S1-S6 corresponden a la versión 1.0, consultadas el 09/09/2026; S7-S13 se verificaron documentalmente el 12/09/2026. Sirven para justificar decisiones de arquitectura; los umbrales, equipo y estimaciones son propuestas de este plan. Las fuentes jurídicas deben verificarse durante la curación, no se certifica su vigencia aquí.

- **S1. Neon, Connection pooling.** Pool transaccional, conexiones directas y límites. https://neon.com/docs/connect/connection-pooling
- **S2. Neon, Branching.** Aislamiento de ramas e historial de recuperación según configuración. https://neon.com/docs/introduction/branching
- **S3. Neon, Optimize pgvector search.** Selección de índices, rendimiento y recuperación. https://neon.com/docs/ai/ai-vector-search-optimization
- **S4. Google Cloud, Execute jobs on a schedule.** Cloud Scheduler, Cloud Run Jobs e identidad de invocación. https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule
- **S5. GitHub, PostgreSQL service containers.** Base real para pruebas de integración en Actions. https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers
- **S6. W3C, Web Content Accessibility Guidelines 2.2.** Referencia del objetivo de accesibilidad, a verificar durante implementación. https://www.w3.org/TR/WCAG22/


- **S7. AWS, caso Boti (28/08/2025).** Patrón de desambiguación y generación contextual; piloto, no configuración vigente completa. [Leer caso](https://aws.amazon.com/blogs/machine-learning/meet-boti-the-ai-assistant-transforming-how-the-citizens-of-buenos-aires-access-government-information-with-amazon-bedrock/).
- **S8. LangGraph, Overview.** Estado, persistencia, pasos deterministas e intervención humana. [Documentación](https://docs.langchain.com/oss/python/langgraph/overview).
- **S9. pgvector, documentación del proyecto.** Búsqueda vectorial, filtros y combinación con búsqueda textual. [Repositorio oficial](https://github.com/pgvector/pgvector).
- **S10. OpenAI, GPT-6 Astra.** Candidato documentado para evaluación; confirmar acceso y configuración de cuenta. [Ficha del modelo](https://developers.openai.com/api/docs/models/gpt-6-astra).
- **S11. OpenAI, text-embedding-3-small.** Candidato de embeddings a comparar con el adaptador local. [Ficha del modelo](https://developers.openai.com/api/docs/models/text-embedding-3-small).
- **S12. OpenAI, Structured Outputs.** Contrato JSON y manejo de excepciones; no valida verdad jurídica. [Guía](https://developers.openai.com/api/docs/guides/structured-outputs).
- **S13. OpenAI, Data controls.** Diferencias entre entrenamiento, registros de abuso y estado de aplicación. [Controles de datos](https://developers.openai.com/api/docs/guides/your-data).


**Repositorio inspeccionado en la línea de base v1.0:** https://github.com/ppistoni87/ACIJ_acceso/tree/1c19c6281d1094cae7fd8189c0b05435e4c6ea11

**Documentos de línea de base en ese commit:**

- `docs/paquete/05_Manifiesto_Fuentes.json`: catálogo inicial de 83 recursos.
- `docs/paquete/02_Historias_por_Fuente.md` y `06_Backlog.json`: historias previas y aceptación por fuente.
- `docs/operacion/diccionario_de_datos.md`: esquema de 53 tablas declarado por los modelos.
- `docs/calidad/estado_backlog.md`: estados históricos y trazabilidad del trabajo anterior.
- `docs/calidad/revision_de_reglas.md`: expediente de 166 candidatas y 67 sin condición ejecutable.
- `docs/reportes/corrida_limpia.md`: ejecución histórica de reconstrucción del corpus.
- `docs/operacion/normas_citadas.md`: distinción entre textos adquiridos y lectura curada.
- `scripts/corrida_limpia.sh` y `scripts/poblar_corpus.sh`: procedimientos existentes, a adaptar al destino persistente.

**Cambio solicitado por Pedro:** incorporar al proyecto ACIJ Acceso la funcionalidad del chatbot tomando como referencia el análisis de Boti, con tecnología actualizada y un front conversacional propio. Su corrección explícita excluye WhatsApp. Esta actualización incorpora especificación y backlog; no altera código, despliega servicios, da de alta cuentas ni acredita nuevas pruebas operativas.

**Inventario de este paquete:** `Plan_Integral_ACIJ.pdf` para lectura; `Plan_Integral_ACIJ.md` como especificación editable; `Backlog_Producto_ACIJ.json` con 38 historias, dependencias, entregas, estimaciones y aceptación; `Inicio_Claude_Code.md` con orden de ejecución. El ZIP reúne las tres piezas editables.