# Trazabilidad de los casos de aceptación

- Casos del paquete: **80**
- Cubiertos por pruebas que corren: **45**
- Cubiertos parcialmente: **11**
- No ejecutados: **24**
- Pruebas citadas: **98** (ejecutadas)

Cada caso remite a los nodeids que lo ejercen. `bn calidad trazabilidad` verifica
que existan antes de contarlos; con `--ejecutar` además los corre.

| Caso | Título | HU | Estado | Resultado | Pruebas / motivo |
| --- | --- | --- | --- | --- | --- |
| AT-001 | Identidad sin colisión | HU-002 | CUBIERTO | PASSED | `test_dos_leyes_mismo_numero_distinta_jurisdiccion_no_colisionan`<br>`test_dos_normas_con_igual_numero_y_distinta_jurisdiccion_no_se_fusionan` |
| AT-002 | Idempotencia de norma | HU-002 | CUBIERTO | PASSED | `test_dos_corridas_son_idempotentes`<br>`test_ninguna_norma_queda_sin_identificador`<br>`test_norma_conjunta_es_una_norma_con_incidencia`<br>`test_misma_jurisdiccion_y_numero_no_se_duplica` |
| AT-003 | FK a versión ajena | HU-002 | CUBIERTO | PASSED | `test_evidencia_no_puede_citar_una_unidad_de_otra_version` |
| AT-004 | Fuente sin URL | HU-001 | CUBIERTO | PASSED | `test_las_fuentes_sin_url_conservan_su_brecha`<br>`test_cada_brecha_tiene_incidencia_abierta_con_responsable`<br>`test_una_fuente_sin_url_no_se_automatiza` |
| AT-005 | Alias F65 | HU-F65 | CUBIERTO | PASSED | `test_los_alias_apuntan_a_una_sola_fuente_canonica`<br>`test_un_alias_no_esta_necesariamente_caido` |
| AT-006 | Alias con fragmento | HU-F28 | CUBIERTO_PARCIAL | PASSED | `test_los_alias_apuntan_a_una_sola_fuente_canonica`<br>_Falta: El ancla rota (#44 inexistente en F31) no se reporta todavía: el catálogo conserva el alias pero nadie verifica que el fragmento exista en el documento destino._ |
| AT-007 | 404 con HTML | HU-004 | CUBIERTO_PARCIAL | PASSED | `test_una_corrida_con_rechazos_no_figura_completa`<br>`test_un_403_pausa_la_fuente_y_no_la_deja_como_sin_datos`<br>_Falta: El caso concreto de un 404 con cuerpo HTML extenso no tiene fixture propia; se ejerce la regla general de que un rechazo no es una corrida completa._ |
| AT-008 | Login con 200 | HU-004 | CUBIERTO_PARCIAL | PASSED | `test_no_se_guardan_cookies_ni_credenciales`<br>_Falta: Clasificar un 200 con formulario de login como canal/estado de acceso exige el adaptador de trámites, que no está construido._ |
| AT-009 | 304 y frescura | HU-023 | CUBIERTO | PASSED | `test_un_304_exige_captura_previa`<br>`test_la_revalidacion_reutiliza_el_objeto_previo`<br>`test_vencer_la_frescura_no_deroga_pero_sí_impide_servir` |
| AT-010 | ETag cambia sin semántica | HU-027 | CUBIERTO | PASSED | `test_una_nota_editorial_no_cuenta_como_cambio_de_la_norma`<br>`test_la_revalidacion_reutiliza_el_objeto_previo` |
| AT-011 | CSV de muestra | HU-F01 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-012 | CSV sin texto | HU-005 | CUBIERTO | PASSED | `test_metadata_only_se_conserva` |
| AT-013 | Contadores no son aristas | HU-F01 | CUBIERTO | PASSED | `test_los_contadores_no_se_convierten_en_relaciones` |
| AT-014 | Cambio de esquema dataset | HU-005 | CUBIERTO | PASSED | `test_forma_inesperada_detiene_la_importacion` |
| AT-015 | ZIP malicioso o sobredimensionado | HU-005 | CUBIERTO | PASSED | `test_zip_con_ruta_fuera_del_arbol_se_rechaza`<br>`test_expansion_por_encima_del_presupuesto_se_rechaza` |
| AT-016 | Contenedor vacío | HU-F52 | NO_EJECUTADO | — | _F52 (cronograma con contenedores field-item) no está capturada: su adaptador HTML específico no se construyó en este alcance._ |
| AT-017 | Bloque escolar oculto | HU-F27 | NO_EJECUTADO | — | _F27 (inscripción escolar con bloques d-none) no está capturada; la regla de visibilidad CSS no está implementada en el adaptador HTML._ |
| AT-018 | PDF sin magic | HU-F40 | NO_EJECUTADO | — | _El adaptador PDF no está construido: sin él no hay validación de magic bytes que probar._ |
| AT-019 | Prefijo PDF conocido | HU-F40 | NO_EJECUTADO | — | _El adaptador PDF no está construido: la reparación trazada de un prefijo de warning no tiene implementación que ejercer._ |
| AT-020 | PDF página gráfica | HU-007 | NO_EJECUTADO | — | _El adaptador PDF no está construido: no hay medición de cobertura por página ni decisión de OCR._ |
| AT-021 | Tabla PDF y caption posterior | HU-F62 | NO_EJECUTADO | — | _El adaptador PDF no está construido: no hay extracción de tablas ni asociación con su caption._ |
| AT-022 | Orden de pasos Canva | HU-F54 | NO_EJECUTADO | — | _F54 (instructivo con rótulos Paso 1/Paso 2 fuera del orden de lectura) no está capturada._ |
| AT-023 | Artículo con sufijo | HU-008 | CUBIERTO | PASSED | `test_conserva_el_sufijo_como_parte_de_la_identidad`<br>`test_el_sufijo_del_articulo_sobrevive_a_la_extraccion` |
| AT-024 | Artículo citado dentro de sustitución | HU-008 | CUBIERTO | PASSED | `test_un_articulo_sustituido_no_es_una_raiz`<br>`test_normativaba_no_toma_el_articulo_sustituido_como_propio`<br>`test_articulo_citado_no_colisiona_con_el_articulo_raiz` |
| AT-025 | Encabezado no soportado | HU-008 | CUBIERTO | PASSED | `test_el_texto_no_clasificado_queda_visible`<br>`test_un_numero_que_retrocede_sin_verbo_queda_marcado_como_ambiguo` |
| AT-026 | Preámbulo preservado | HU-F23 | CUBIERTO | PASSED | `test_visto_considerando_y_transitorias_se_conservan` |
| AT-027 | Anexo después de antecedentes | HU-008 | CUBIERTO | PASSED | `test_un_anexo_reinicia_la_numeracion_sin_marcar_ambiguedad`<br>`test_el_texto_no_clasificado_queda_visible` |
| AT-028 | Identidad resolución 1621 | HU-D04 | CUBIERTO | PASSED | `test_normativaba_detecta_una_transposicion_de_digitos_en_la_sintesis`<br>`test_una_cita_normal_a_otra_norma_no_se_reporta_como_discrepancia` |
| AT-029 | Anexo separado de resolución | HU-F19 | CUBIERTO_PARCIAL | PASSED | `test_una_version_publicada_se_sirve_solo_en_las_capacidades_que_sustenta`<br>`test_la_ficha_se_abstiene_en_las_capacidades_que_no_sustenta`<br>_Falta: La captura y vinculación del anexo de F19 no está hecha: se prueba que sin el anexo la capacidad PLAZO se abstiene, no que con él se complete._ |
| AT-030 | Abrogación y restablecimiento | HU-F33 | CUBIERTO | PASSED | `test_la_nota_produce_la_abrogacion_y_la_restitucion`<br>`test_la_nota_conserva_la_abrogacion_y_la_restitucion`<br>`test_abrogada_y_restablecida_no_tiene_lectura_automatica` |
| AT-031 | Monto histórico en ley | HU-F33 | CUBIERTO | PASSED | `test_un_valor_de_vigencia_desconocida_no_se_publica`<br>`test_un_valor_de_otro_periodo_no_se_devuelve`<br>`test_cuantia_no_informada_no_necesita_inventar_un_monto` |
| AT-032 | Renumeración 10 a 9 | HU-F23 | CUBIERTO_PARCIAL | PASSED | `test_original_y_actualizado_son_versiones_distintas`<br>`test_la_ficha_no_es_una_version_del_texto`<br>_Falta: La correspondencia comprobada 10→9 entre versiones (tabla equivalencias_unidades) no está poblada ni ejercida._ |
| AT-033 | Modificatoria no vigente | HU-D05 | CUBIERTO | PASSED | `test_una_etiqueta_no_vigente_no_alcanza_para_cerrar_la_vigencia`<br>`test_normativaba_separa_el_estado_declarado_de_la_conclusion` |
| AT-034 | Condición transitoria pendiente | HU-D06 | CUBIERTO | PASSED | `test_condicionado_exige_declarar_la_condicion`<br>`test_sin_estado_declarado_la_vigencia_va_a_revision` |
| AT-035 | Novedad candidata de reglamentación | HU-M02 | CUBIERTO | PASSED | `test_el_impacto_alcanza_a_las_normas_que_la_citan`<br>`test_toda_relacion_nace_candidata_y_con_evidencia` |
| AT-036 | Ciclo legítimo de citas | HU-010 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-037 | Frontera de dependencias | HU-010 | CUBIERTO | PASSED | `test_una_norma_no_registrada_queda_como_referencia_pendiente` |
| AT-038 | No aplicabilidad fundada | HU-012 | CUBIERTO | PASSED | `test_un_campo_sin_senales_dice_donde_se_busco`<br>`test_no_informado_exige_decir_que_fuentes_se_revisaron` |
| AT-039 | No informado no es no existe | HU-017 | CUBIERTO | PASSED | `test_no_informado_exige_decir_que_fuentes_se_revisaron`<br>`test_una_causal_de_revocacion_no_decide_el_acceso` |
| AT-040 | Completitud aparente | HU-012 | CUBIERTO | PASSED | `test_evaluacion_completa_no_es_base_completa`<br>`test_cobertura_separa_evaluado_de_sustantivo` |
| AT-041 | Roles de población | HU-013 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-042 | AND con desconocido | HU-014 | CUBIERTO | PASSED | `test_la_tabla_de_verdad_es_la_de_la_especificacion`<br>`test_un_dato_que_falta_no_es_un_incumplimiento`<br>`test_falta_un_dato_y_el_resultado_pide_datos_en_vez_de_negar` |
| AT-043 | OR con alternativa válida | HU-014 | CUBIERTO | PASSED | `test_la_tabla_de_verdad_es_la_de_la_especificacion`<br>`test_una_condicion_falsa_no_arrastra_a_las_desconocidas`<br>`test_una_condicion_cumplida_no_tapa_lo_que_falta` |
| AT-044 | Negación de desconocido | HU-014 | CUBIERTO | PASSED | `test_la_tabla_de_verdad_es_la_de_la_especificacion`<br>`test_un_dato_declarado_como_nulo_tampoco_lo_es` |
| AT-045 | Límite inclusivo | HU-014 | CUBIERTO | PASSED | `test_menor_que_no_es_menor_o_igual`<br>`test_los_importes_se_comparan_como_decimales` |
| AT-046 | Excepción de no exclusión | HU-015 | CUBIERTO | PASSED | `test_con_la_excepcion_cumplida_el_bloqueo_no_aplica`<br>`test_no_se_niega_sin_haber_evaluado_las_excepciones`<br>`test_con_todas_las_excepciones_descartadas_si_hay_negativa_explicable` |
| AT-047 | Falta documentación subsanable | HU-015 | CUBIERTO | PASSED | `test_una_salvaguarda_nunca_excluye_y_siempre_se_informa`<br>`test_falta_un_dato_y_el_resultado_pide_datos_en_vez_de_negar` |
| AT-048 | Edad oficial en conflicto | HU-F66 | CUBIERTO | PASSED | `test_candidatos_en_conflicto_pueden_coexistir`<br>`test_un_conflicto_abierto_bloquea_la_publicacion_de_ese_hecho` |
| AT-049 | Suspensión no es revocación | HU-017 | CUBIERTO_PARCIAL | PASSED | `test_una_causal_de_revocacion_no_decide_el_acceso`<br>_Falta: Distinguir suspensión de revocación y detallar el remedio exige el campo criterios_revocacion poblado con texto real: hoy ninguna versión del corpus lo tiene sustantivo._ |
| AT-050 | Cierre conocido sin cambio web | HU-016 | CUBIERTO | PASSED | `test_una_fecha_fuera_del_periodo_no_se_sirve_como_actual`<br>`test_una_fecha_anterior_a_la_vigencia_no_se_sirve_como_actual` |
| AT-051 | Días hábiles con feriado | HU-016 | NO_EJECUTADO | — | _El cómputo de días hábiles con calendario poblado no está implementado: el esquema exige el calendario y la migración lo modela, pero no hay calculadora ni calendario jurisdiccional cargado._ |
| AT-052 | Calendario sin cobertura | HU-016 | CUBIERTO | PASSED | `test_dias_habiles_sin_calendario_no_producen_una_fecha` |
| AT-053 | Rango sin año | HU-016 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-054 | Último tramo salarial | HU-F12 | CUBIERTO | PASSED | `test_un_valor_de_vigencia_desconocida_no_se_publica`<br>`test_abierto_fin_no_admite_fecha_de_cierre` |
| AT-055 | SMVM versus comercio | HU-018 | CUBIERTO | PASSED | `test_sin_valor_vigente_del_parametro_la_condicion_es_desconocida`<br>`test_el_parametro_se_resuelve_a_la_fecha_consultada` |
| AT-056 | Períodos mixtos en PDF | HU-F62 | NO_EJECUTADO | — | _El adaptador PDF no está construido: sin extracción de tablas no hay período por tabla que normalizar._ |
| AT-057 | Monto versus tope | HU-018 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-058 | Cambio de parámetro | HU-028 | CUBIERTO | PASSED | `test_dos_valores_aprobados_no_pueden_regir_a_la_vez`<br>`test_aprobar_una_version_reevalua_el_solapamiento`<br>`test_propagar_dos_veces_no_duplica_el_evento` |
| AT-059 | No informado operativo | HU-F60 | NO_EJECUTADO | — | _Los canales de atención (HU-019) no están poblados: no hay importador de directorios que pueda encontrarse un literal N/A._ |
| AT-060 | Conflicto de piso | HU-F20 | CUBIERTO_PARCIAL | PASSED | `test_candidatos_en_conflicto_pueden_coexistir`<br>_Falta: Los puntos de atención (HU-020) no están poblados: el conflicto de piso entre CSV y ficha no tiene datos reales donde darse._ |
| AT-061 | Horarios por canal | HU-F03 | NO_EJECUTADO | — | _Los canales por tipo con horarios propios (HU-019) no están poblados._ |
| AT-062 | Atribución de directorio | HU-F44 | NO_EJECUTADO | — | _El directorio de la DPN (F44) no está capturado: la atribución de un operador municipal no tiene datos donde ejercerse._ |
| AT-063 | Coordenadas locales | HU-020 | NO_EJECUTADO | — | _El dataset de sedes con coordenadas (HU-020) no está cargado: no hay geometría cuyo CRS discutir._ |
| AT-064 | RENABAP no encontrado | HU-021 | NO_EJECUTADO | — | _El padrón RENABAP (HU-021) no está importado: la tabla existe pero no tiene snapshot donde buscar un barrio._ |
| AT-065 | Tabla estacional vacía | HU-F64 | NO_EJECUTADO | — | _F64 (sedes estacionales) no está capturada._ |
| AT-066 | Fuente secundaria y cita | HU-022 | CUBIERTO_PARCIAL | PASSED | `test_la_recuperacion_devuelve_citas_localizables`<br>_Falta: No hay fuente secundaria de ONG en el corpus poblado: la atribución secundaria se sostiene por el modelo de evidencia, no por un caso real._ |
| AT-067 | Contenido con instrucciones maliciosas | HU-033 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-068 | Ingestor intenta publicar | HU-033 | CUBIERTO | PASSED | `test_sin_credencial_configurada_la_administracion_esta_cerrada`<br>`test_una_credencial_invalida_no_autoriza` |
| AT-069 | Release parcial fallido | HU-025 | NO_EJECUTADO | — | _Sin motivo declarado._ |
| AT-070 | Índice retrasado | HU-031 | CUBIERTO | PASSED | `test_sin_release_la_recuperacion_no_toca_staging`<br>`test_solo_se_indexa_texto_dispositivo`<br>`test_sin_release_publicado_la_respuesta_lo_dice` |
| AT-071 | Jobs caídos y TTL | HU-034 | CUBIERTO | PASSED | `test_vencer_la_frescura_no_deroga_pero_sí_impide_servir`<br>`test_sin_release_publicado_ninguna_capacidad_sirve_datos` |
| AT-072 | Evento repetido | HU-028 | CUBIERTO | PASSED | `test_una_entrega_exitosa_lleva_la_clave_de_idempotencia`<br>`test_propagar_dos_veces_no_duplica_el_evento`<br>`test_una_entrega_fallida_no_marca_el_evento_como_entregado` |
| AT-073 | No proveedor Web Push | HU-028 | CUBIERTO | PASSED | `test_sin_consumidor_configurado_no_se_declara_ninguna_entrega`<br>`test_un_evento_que_agoto_los_intentos_pasa_a_la_cola_de_fallos` |
| AT-074 | Restauración | HU-037 | NO_EJECUTADO | — | _La prueba de restauración (HU-037) exige un procedimiento de backup y un entorno aislado que este alcance no construyó._ |
| AT-075 | Fecha de carpeta PDF | HU-F67 | CUBIERTO_PARCIAL | PASSED | `test_la_ruta_de_infoleg_distingue_original_de_actualizado`<br>_Falta: El caso de F67 es un PDF alojado en una carpeta de año viejo: sin adaptador PDF, solo se prueba que la ruta no dicta la identidad de la versión._ |
| AT-076 | Costo ausente | HU-F45 | CUBIERTO_PARCIAL | PASSED | `test_cuantia_no_informada_no_necesita_inventar_un_monto`<br>_Falta: Los trámites (HU-019) no están poblados: la ficha sin costo ni duración no tiene datos reales donde darse._ |
| AT-077 | Formulario público sin envío | HU-F04 | CUBIERTO | PASSED | `test_no_se_guardan_cookies_ni_credenciales`<br>`test_el_planificador_ignora_lo_que_no_se_puede_pedir` |
| AT-078 | Sustituto de otra granularidad | HU-F09 | CUBIERTO_PARCIAL | PASSED | `test_una_fuente_retirada_explica_por_que`<br>`test_el_reporte_no_confunde_fuentes_con_leyes`<br>_Falta: El caso concreto de F09 (directorio municipal caído con lista provincial disponible) no tiene fixture: se prueba la regla de que una fuente retirada explica su motivo, no la sustitución por otra granularidad._ |
| AT-079 | Evaluación no administrativa | HU-030 | CUBIERTO | PASSED | `test_la_evaluacion_aclara_que_no_es_una_decision`<br>`test_el_cuerpo_de_una_evaluacion_no_se_persiste`<br>`test_todo_cumplido_da_un_resultado_preliminar_positivo` |
| AT-080 | Historial bitemporal | HU-009 | NO_EJECUTADO | — | _Sin motivo declarado._ |

## Cómo leer los no ejecutados

Un caso no ejecutado no es un caso que falle: es una capacidad que este alcance
no construyó y que por eso no tiene nada que probar. El motivo dice cuál, para
que la siguiente iteración sepa qué habilita cada caso.
