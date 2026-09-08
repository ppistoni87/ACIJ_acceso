# Historias de usuario por fuente

83 historias: 67 IDs preservados y 16 incorporaciones (10 dependencias/representaciones y seis fuentes de monitoreo o contraste). Cada historia indica acceso, destino y criterios específicos. Los estados iniciales son decisiones de planificación basadas en evidencia disponible, no resultados de una corrida de producción.

## Inventario de ejecución

| ID | Fuente | Prioridad | Estado inicial | TTL manual (días) | Destino |
|---|---|---|---|---|---|
| F01 | InfoLEG (normativa nacional) - dataset abierto | P0 | DISCOVERY | 30 | normas / norma_identificadores / relaciones_normativas |
| F02 | Becas Progresar - inscripción nivel obligatorio (ficha + URL de inscripción por línea) | P2 | REFERENCE_ONLY | 30 | tramites / canales / fuentes_candidatas |
| F03 | Defensoría del Pueblo CABA - Sede Central y canales de atención | P1 | DISCOVERY | 7 | puntos_atencion / canales |
| F04 | La Defe - formulario NNyA (migrado a ladefe.gob.ar) | P1 | DISCOVERY | 30 | tramites / canales / fuentes_candidatas |
| F05 | Asesoría General Tutelar (MPT) - oficinas de atención | P1 | DISCOVERY | 7 | puntos_atencion / canales |
| F06 | CDNNyA - Subsedes (URL muerta) + monitor y domicilio institucional | P1 | RETIRED | 1 | fuentes / fuentes_candidatas |
| F07 | CDNNyA - Defensorías Zonales | P1 | DISCOVERY | 7 | puntos_atencion / canales |
| F08 | Fuente excluida por antibot/robots; identidad por recuperar | P1 | DISCOVERY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F09 | Servicios locales de Proteccion PBA (fuente muerta + sustituto provincial) | P1 | RETIRED | 7 | fuentes / fuentes_candidatas |
| F10 | Centros de Acceso a la Justicia (CAJ) | P1 | MANUAL | 7 | puntos_atencion / canales |
| F11 | Programa Acceder - MPD (sede + centros barriales) | P1 | DISCOVERY | 30 | puntos_atencion / canales |
| F12 | Salario Vital y Movil (Consejo del Salario) | P0 | DISCOVERY | 7 | parametros / parametro_valores / relaciones_normativas |
| F13 | Documento del equipo en Drive/Docs; identidad por recuperar | P1 | MANUAL | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F14 | Listado de oficinas ANSES | P1 | DISCOVERY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F15 | Login o turnero ANSES del catálogo; URL por recuperar | P1 | REFERENCE_ONLY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F16 | FAQ Progresar por línea (obligatoria + superior) - receta única parametrizada | P1 | DISCOVERY | 60 | documentos / unidades_documentales / reglas |
| F17 | FAQ general Progresar (la que enlaza la home) - ID reasignado | P0 | DISCOVERY | 60 | documentos / reglas / tramites |
| F18 | Portal Becas Progresar - mapa de entradas de inscripción | P0 | DISCOVERY | 7 | canales / fuentes_candidatas |
| F19 | Becas Media - Regulacion (Ley 2917, Boletin Oficial CABA) | P0 | DISCOVERY | 90 | normas / norma_versiones / reglas / beneficios |
| F20 | Comunas CABA - sedes, subsedes y Unidad de Atención Ciudadana | P1 | DISCOVERY | 30 | puntos_atencion / canales |
| F21 | Fuente excluida por antibot/robots; identidad por recuperar | P1 | DISCOVERY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F22 | Fuente excluida por antibot/robots; identidad por recuperar | P1 | DISCOVERY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F23 | Beca Alimentaria - Ordenanza 43.478/89 (Comedores Escolares, CABA) | P0 | DISCOVERY | 90 | normas / norma_versiones / equivalencias_unidades / reglas |
| F24 | Beca Alimentaria - iniciar trámite (landing del sistema en línea) | P1 | MANUAL | 14 | tramites / canales |
| F25 | Ley de Educacion Nacional 26.206 (texto actualizado InfoLEG) | P0 | DISCOVERY | 90 | normas / norma_versiones / unidades_documentales |
| F26 | Constitución de CABA; copia del equipo | P1 | MANUAL | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F27 | Inscripción escolar CABA (página de trámite) | P0 | DISCOVERY | 7 | tramites / plazos / canales |
| F28 | Preinscripcion escolar FAQ (ancla #44) - alias de F31 con ancla rota | P2 | REFERENCE_ONLY | 15 | fuentes / fuente_urls |
| F29 | Sistema de inscripción escolar en línea (alias de F27) | P2 | REFERENCE_ONLY | 7 | fuentes / fuente_urls |
| F30 | Documento del equipo en Drive/Docs; identidad por recuperar | P1 | MANUAL | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F31 | Preguntas frecuentes inscripción escolar | P1 | DISCOVERY | 15 | documentos / unidades_documentales / plazos |
| F32 | Turnero de Inscripción en Línea (turnos presenciales) | P1 | DISCOVERY | 7 | fuentes / canales |
| F33 | Ley de Asignaciones Familiares 24.714 / AUH (texto actualizado InfoLEG) | P0 | DISCOVERY | 90 | normas / norma_versiones / relaciones_normativas / reglas |
| F34 | Login o turnero ANSES del catálogo; URL por recuperar | P1 | REFERENCE_ONLY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F35 | Video de apoyo del catálogo; URL por recuperar | P1 | REFERENCE_ONLY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F36 | Tramitar DNI | P0 | DISCOVERY | 7 | tramites / tramite_pasos / parametro_valores / fuentes_candidatas |
| F37 | Login o turnero ANSES del catálogo; URL por recuperar | P1 | REFERENCE_ONLY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F38 | Guia de prevencion de desalojos (PDF) | P2 | REFERENCE_ONLY | 180 | documentos / unidades_documentales |
| F39 | Listado RENABAP (padron de barrios populares) | P1 | DISCOVERY | 30 | barrios_renabap / documento_versiones |
| F40 | Decreto 690/2006 situación de calle (PDF texto actualizado, Boletin Oficial CABA) | P0 | DISCOVERY | 30 | normas / norma_versiones / unidades_documentales / plazos |
| F41 | CUD - Certificado Único de Discapacidad (ACIJ, fuente NO oficial) | P2 | REFERENCE_ONLY | 90 | documentos / unidades_documentales / fuentes_candidatas |
| F42 | AySA; fuente con restricción de acceso | P1 | DISCOVERY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F43 | Reclamos a ERAS (Ente Regulador de Agua y Saneamiento) | P1 | DISCOVERY | 30 | tramites / canales / fuentes_candidatas |
| F44 | Listado defensorias del pueblo (param idS) | P1 | DISCOVERY | 30 | puntos_atencion / canales |
| F45 | Reclamo ante Defensa del Consumidor | P1 | DISCOVERY | 30 | tramites / tramite_pasos / canales |
| F46 | EDENOR - Servicio técnico | P1 | DISCOVERY | 30 | canales / documentos / unidades_documentales |
| F47 | EDENOR - Danos en equipamiento electrico | P1 | DISCOVERY | 30 | tramites / tramite_pasos / documentos / plazos |
| F48 | EDESUR - Como hacer un reclamo en Edesur | P1 | DISCOVERY | 30 | canales / documentos |
| F49 | ENRE - Formularios en línea (gestión de reclamos) | P1 | DISCOVERY | 30 | tramites / canales / fuentes_candidatas |
| F50 | ENRE - Saca turno por Internet (turno previo) | P1 | DISCOVERY | 14 | tramites / canales |
| F51 | ENRE - portada del organismo / sección 'Mas información' | P1 | DISCOVERY | 30 | organismos / puntos_atencion / canales / fuentes_candidatas |
| F52 | Progresar - Monto de la beca y cronograma de pagos | P0 | DISCOVERY | 3 | parametro_valores / plazos |
| F53 | Progresar - Iniciar trámite, plazos de convocatoria y mapa de subpaginas | P0 | DISCOVERY | 1 | tramites / plazos / fuentes_candidatas |
| F54 | Instructivo beca - como revisar una solicitud (PDF) | P1 | DISCOVERY | 180 | documentos / unidades_documentales / fuentes_candidatas |
| F55 | Beca Alimentaria - alias sin barra final de F24 (la ficha lo llama 'formulario' y no lo es) | P2 | REFERENCE_ONLY | 14 | fuentes / fuente_urls |
| F56 | Beca Alimentaria - requisitos y condiciones (texto de la declaracion jurada) | P0 | MANUAL | 90 | documentos / reglas / tramites |
| F57 | Login o turnero ANSES del catálogo; URL por recuperar | P1 | REFERENCE_ONLY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F58 | Login o turnero ANSES del catálogo; URL por recuperar | P1 | REFERENCE_ONLY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F59 | AySA; fuente con restricción de acceso | P1 | DISCOVERY | por definir | fuentes / fuente_urls / fuentes_candidatas |
| F60 | Sedes de Atención Social (SAS) - CABA | P1 | DISCOVERY | 7 | puntos_atencion / canales |
| F61 | RENABAP - canales de asesoramiento desalojos | P1 | DISCOVERY | 30 | canales / fuentes_candidatas |
| F62 | Marco legal, procesos y MONTOS de becas alimentarias y servicios (PDF, ciclo lectivo 2026) | P0 | DISCOVERY | 7 | parametro_valores / documentos / reglas |
| F63 | Preguntas frecuentes de Becas Alimentarias (PDF en sistemas1, host con certificado que no lo cubre) | P1 | MANUAL | 60 | documentos / unidades_documentales |
| F64 | Sedes y puntos presenciales de inscripción escolar | P1 | DISCOVERY | 30 | puntos_atencion / fuentes |
| F65 | Progresar - FAQ general (la que enlaza la home) - DUPLICADO EXACTO de F17, no es una tercera FAQ | P2 | REFERENCE_ONLY | 60 | fuentes / fuente_urls |
| F66 | Progresar - Requisitos por línea (hub /requisitos + 3 hojas: obligatorio, superior, formacion profesional) | P0 | DISCOVERY | 30 | reglas / beneficio_versiones / fuentes_candidatas |
| F67 | Progresar - 'Informes' (301 -> /reglamentos): los 3 reglamentos generales en PDF (ANEXO I, II y III) | P0 | DISCOVERY | 90 | documentos / norma_versiones / reglas / referencias_pendientes |
| D01 | Decreto DNU 1382/2001 | P0 | DISCOVERY | por definir | normas / relaciones_normativas |
| D02 | Decreto DNU 1604/2001 | P0 | DISCOVERY | por definir | normas / relaciones_normativas |
| D03 | Decreto CABA 75/2015 | P0 | DISCOVERY | por definir | normas / reglas |
| D04 | Resolución 1621/MEDGC/2025 | P0 | DISCOVERY | por definir | normas / relaciones_normativas / tramites |
| D05 | Ley CABA 547/2001 | P0 | DISCOVERY | por definir | normas / relaciones_normativas / equivalencias_unidades |
| D06 | Ley CABA 6935/2025 | P0 | DISCOVERY | por definir | normas / beneficios / plazos / relaciones_normativas |
| D07 | Anexo de Resolución 1621/MEDGC/2025 | P0 | DISCOVERY | por definir | documentos / reglas / tramite_pasos / plazos |
| D08 | PDF actualizado de Ordenanza 43.478 | P0 | DISCOVERY | por definir | documento_versiones / norma_versiones / equivalencias_unidades |
| D09 | PDF actualizado de Ley 2917 | P0 | DISCOVERY | por definir | documento_versiones / norma_versiones |
| D10 | Ficha HTML de Decreto CABA 690/2006 | P0 | DISCOVERY | por definir | fuentes_candidatas / relaciones_normativas / norma_versiones |
| M01 | Monitor Boletín Oficial nacional | P0 | DISCOVERY | por definir | fuentes_candidatas / documentos / relaciones_normativas |
| M02 | Monitor Boletín Oficial CABA | P0 | DISCOVERY | por definir | fuentes_candidatas / documentos / relaciones_normativas |
| M03 | Monitor normativa PBA | P0 | DISCOVERY | por definir | fuentes_candidatas / normas |
| M04 | Monitor Boletín Oficial PBA | P0 | DISCOVERY | por definir | fuentes_candidatas / documentos |
| M05 | ANSES: descubrimiento de AUH, montos y calendario público | P0 | DISCOVERY | por definir | fuentes_candidatas / parametro_valores / plazos / tramites |
| M06 | Ficha oficial para obtener CUD | P0 | DISCOVERY | por definir | tramites / reglas / plazos / fuentes_candidatas |



## Contrato común de una fuente

Cada fuente debe entregar identidad, modo de acceso, evidencias, mapeo SQL, estados temporales por hecho, control de calidad, idempotencia, métricas y test de regresión. La receta del manual es una referencia histórica; las decisiones de esta especificación y la evidencia actual prevalecen. No copiar credenciales ni relajaciones TLS de ejemplos. Para fuentes con varias hojas/PDF, registrar recursos hijos y conciliarlos; no declarar completa una fuente porque respondió el hub.



### HU-F01 · InfoLEG (normativa nacional) - dataset abierto

**Prioridad:** P0 · **Capacidad responsable:** `datos_sql`

**Historia:** Como curador de datos del sistema conversacional, quiero importar catálogo nacional y relaciones; priorizar textos del alcance. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-005.

**Criterios de aceptación:**

1. Dada F01, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Seleccionar recurso de producción por metadatos/sufijo verificado; no usar CSV de muestra como corpus completo.

3. Conservar las filas sin texto como metadata-only, validar las 17 columnas de la fixture y alertar cambios de esquema.

4. No resolver todos los textos nacionales de forma indiscriminada ni interpretar contadores como aristas.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://datos.jus.gob.ar/dataset/d9a963ea-8b1d-4ca3-9dd9-07a4773e8c23/resource/bf0ec116-ad4e-4572-a476-e57167a84403/download/base-infoleg-normativa-nacional.zip](https://datos.jus.gob.ar/dataset/d9a963ea-8b1d-4ca3-9dd9-07a4773e8c23/resource/bf0ec116-ad4e-4572-a476-e57167a84403/download/base-infoleg-normativa-nacional.zip)

**Destino SQL:** `normas`, `norma_identificadores`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DATASET ABIERTO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 6; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** No hay bloque de campos separado: aplicar modelo normativo y contrato de fuente.



### HU-F02 · Becas Progresar - inscripción nivel obligatorio (ficha + URL de inscripción por línea)

**Prioridad:** P2 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar el canal legado y contrastar destino con F18/F53. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F02, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El PDF comentado de 2020 no se publica como FAQ ni plazo actual; si se conserva, es histórico.

3. No inferir línea desde hidden_tipo_nivel inconsistente y no enviar login/registro.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://becasprogresar.educacion.gob.ar/inicio_nivel_obligatorio.php](https://becasprogresar.educacion.gob.ar/inicio_nivel_obligatorio.php)

**Destino SQL:** `tramites`, `canales`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 9; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** linea_beca · detalle_linea · url_inscripcion (miargentina.php?t=OBLIGATORIO) · url_formulario_registro · url_formulario_ingreso · url_formulario_miargentina · hidden_tipo_nivel (control de calidad) · url_pdf_no_publicado · texto_pdf_historico (condicionado)



### HU-F03 · Defensoría del Pueblo CABA - Sede Central y canales de atención

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer ficha y canales de atención vecinal. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F03, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Separar horarios de atención presencial, teléfono y WhatsApp; no copiar el mismo horario a todos.

3. Correo desde texto validado si href está mal; la cuenta de redes sociales no es email.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://defensoria.org.ar/atencion-vecinal/](https://defensoria.org.ar/atencion-vecinal/)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 12; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre · organismo · direccion · horario · telefono · whatsapp · email · horario_telefono · horario_whatsapp · url_fuente · fecha_actualizacion



### HU-F04 · La Defe - formulario NNyA (migrado a ladefe.gob.ar)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero verificar identidad del organismo y capturar información pública del formulario NNyA. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F04, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Verificar vínculo oficial del dominio y TLS antes de activar; no saltar captcha ni enviar formularios.

3. No convertir campos HTML obligatorios en requisitos legales; deduplicar opciones por nombre sin usar el select como padrón de provincias.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://ladefe.gob.ar/soy-una-nina-nino-o-adolescente/](https://ladefe.gob.ar/soy-una-nina-nino-o-adolescente/)

**Destino SQL:** `tramites`, `canales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 14; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_tramite · url_canonica · fecha_modificacion (wp modified) · organismo · descripcion/instrucciones (breve) · cf7_form_id · campos_del_formulario (name, tipo, requerido, opciones) · provincias ofrecidas en el select · vias de comunicacion ofrecidas (telefono, email, whatsapp, videollamada)



### HU-F05 · Asesoría General Tutelar (MPT) - oficinas de atención

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer oficinas MPT por bloque y puntos de cada oficina. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F05, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Incluir bloque CENTRO aunque no tenga clase ofc; encabezados de barrios no son puntos.

3. Horario comentado queda no informado; no heredar dirección o barrio al siguiente bloque.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://mptutelar.gob.ar/oficinas-de-atencion](https://mptutelar.gob.ar/oficinas-de-atencion)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 17; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** oad · nombre · direccion · horario · telefono · email · barrio · es_nuevo



### HU-F06 · CDNNyA - Subsedes (URL muerta) + monitor y domicilio institucional

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero registrar fuente retirada y brecha de cobertura de subsedes. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F06, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No insertar una página 404 ni una mesa de entradas como subsede de atención general.

3. F07 puede cubrir otra necesidad territorial pero la equivalencia funcional debe quedar documentada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://buenosaires.gob.ar/gcaba_historico/node/86736](https://buenosaires.gob.ar/gcaba_historico/node/86736)

**Destino SQL:** `fuentes`, `fuentes_candidatas`.

**Estado inicial:** RETIRED · **Técnica de referencia:** DESCARTAR · **TTL del manual:** 1 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 19; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre · organismo · direccion · horario · telefono · email · lat · lng · url_fuente



### HU-F07 · CDNNyA - Defensorías Zonales

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer Defensorías Zonales y sus canales. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F07, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Distinguir lat/lng WGS84 de coordenadas locales con lon; no reproyectar sin CRS.

3. Usar correo institucional visible cuando href nominal difiere; horario común solo se aplica al conjunto al que el texto refiere.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://buenosaires.gob.ar/gcaba_historico/defensorias-zonales](https://buenosaires.gob.ar/gcaba_historico/defensorias-zonales)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 21; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre · organismo · comuna · direccion · telefono · email · horario · lat · lng · x_caba · y_caba · url_fuente



### HU-F08 · Fuente excluida por antibot/robots; identidad por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero no hay URL identificable en el anexo del manual. Recuperar registro original y documentar acceso permitido; no evadir controles. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F08, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVERY_REQUIRED · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F09 · Servicios locales de Proteccion PBA (fuente muerta + sustituto provincial)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar el alcance municipal pendiente mediante fuente legítima. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F09, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Redirección a portada no equivale a listado recuperado.

3. Un directorio provincial sustituto tiene otra identidad; snapshot 2023 no se publica como municipal vigente.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [http://www.snya.gba.gob.ar/index.php/recursos/servicios-locales](http://www.snya.gba.gob.ar/index.php/recursos/servicios-locales)

**Destino SQL:** `fuentes`, `fuentes_candidatas`.

**Estado inicial:** RETIRED · **Técnica de referencia:** DESCARTAR · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 24; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** (fuente original) ninguno - descartada · (sustituto /areas-de-ninez-provinciales) jurisdiccion · organismo · direccion · telefonos (de a[href^=tel:]) · emails (de a[href^=mailto:], en claro)



### HU-F10 · Centros de Acceso a la Justicia (CAJ)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero obtener listado CAJ por un recurso público autorizado o carga controlada. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F10, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No usar clave de Google ajena publicada por el frontend para un job recurrente; registrar vía de acceso requerida.

3. Fecha del listado y cobertura provincial quedan explícitas; no afirmar inexistencia de centros por falta de fila.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/justicia/afianzar/caj/listado](https://www.argentina.gob.ar/justicia/afianzar/caj/listado)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** MANUAL · **Técnica de referencia:** ENDPOINT JSON · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 26; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** provincia · nombre · direccion · telefonos (lista: fijo y whatsapp) · horario · correo · url_mapa · turno_online (hoy vacio en las 31)



### HU-F11 · Programa Acceder - MPD (sede + centros barriales)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar sede Acceder y su hoja de abordaje territorial. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F11, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Recorrer tabla de centros además de ficha de sede; preservar días, frecuencias y excepciones por centro.

3. Guardar cargo responsable cuando sea suficiente; no trasladar nombres personales a respuestas por defecto.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.mpd.gov.ar/index.php/acceder](https://www.mpd.gov.ar/index.php/acceder)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 28; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** sede: responsable, direccion, horario, telefono · centros: zona, dia de atencion, nombre del centro, direccion, frecuencia (cada 15 dias), horario override



### HU-F12 · Salario Vital y Movil (Consejo del Salario)

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar serie salarial con norma y períodos aplicables. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-005.

**Criterios de aceptación:**

1. Dada F12, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Separar SMVM mensual/diario/hora y verificar norma del tramo para la fecha requerida.

3. Último mes disponible no crea un vencimiento jurídico; abrir revisión si falta período y mantener aplicación solo con fundamento.

4. Página de otro mes no se trata como conflicto para la misma fecha.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/trabajo/consejodelsalario](https://www.argentina.gob.ar/trabajo/consejodelsalario)

**Destino SQL:** `parametros`, `parametro_valores`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DATASET ABIERTO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 31; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** concepto · periodo_vigencia · monto_mensual · monto_diario · monto_hora · norma_respaldo_titulo · norma_respaldo_url · tramo_vigente_segun_norma · fuente_url · fecha_captura · alertas



### HU-F13 · Documento del equipo en Drive/Docs; identidad por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero obtener archivo del equipo y procedencia; carga manual con controles, sin scrapear una sesión de Drive. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F13, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** MANUAL · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F14 · Listado de oficinas ANSES

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero buscar recurso público de UDAI/oficinas o vía institucional; no tratar la brecha como resuelta con la home. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F14, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVERY_REQUIRED · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F15 · Login o turnero ANSES del catálogo; URL por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero guardar enlace como canal del trámite; no autenticar, consultar cuentas ni extraer datos individuales. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F15, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F16 · FAQ Progresar por línea (obligatoria + superior) - receta única parametrizada

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar las dos FAQ por línea Progresar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F16, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Expandir dos URLs concretas y aceptar headings h2–h6 con respuestas multibloque.

3. Mantener identidad por línea; no combinar edades o requisitos entre superior y obligatorio.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar/educacion-obligatoria-faq](https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar/educacion-obligatoria-faq); [https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar/educacion-superior-faq](https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar/educacion-superior-faq)

**Destino SQL:** `documentos`, `unidades_documentales`, `reglas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 60 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 34; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** linea (obligatoria|superior) · titulo_seccion · pregunta · respuesta · node_id (188916 / 188912) · url_canonica



### HU-F17 · FAQ general Progresar (la que enlaza la home) - ID reasignado

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar FAQ general e introducción antifraude. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F17, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Conservar contenido previo al primer heading y preguntas de suspensión/cese.

3. Revisar edición y circuito de inscripción según observación posterior F65; F65 no genera chunks propios.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar-faq](https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar-faq)

**Destino SQL:** `documentos`, `reglas`, `tramites`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 60 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 36; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** linea (general) · titulo_seccion · intro_antifraude · pregunta · respuesta · node_id (461614) · url_canonica



### HU-F18 · Portal Becas Progresar - mapa de entradas de inscripción

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero descubrir destinos de inscripción por campaña. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada F18, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Host con año se lee desde página; no hardcodear 26 en el scraper.

3. Separar accesos ciudadanos e institucionales; guardar enlaces a login sin recorrer sesión.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://becasprogresar.educacion.gob.ar/](https://becasprogresar.educacion.gob.ar/)

**Destino SQL:** `canales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 38; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** linea_beca · detalle_linea · url_destino_inscripcion · publico (ciudadano|institucional) · urls_lenguas_originarias (6)



### HU-F19 · Becas Media - Regulacion (Ley 2917, Boletin Oficial CABA)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar Ley 2917 por versión y cerrar dependencias. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F19, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Paneles se localizan por rótulo; Texto actualizado es vínculo a PDF, no articulado HTML.

3. Procesar Decreto 75/2015 y Resolución 1621/MEDGC/2025 con anexo; conservar discrepancia 1261/1621 como incidencia.

4. Texto original de 2008 queda diferenciado del aplicable; comparar consolidación y reformas posteriores.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/125647](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/125647)

**Destino SQL:** `normas`, `norma_versiones`, `reglas`, `beneficios`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 40; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** No hay bloque de campos separado: aplicar modelo normativo y contrato de fuente.



### HU-F20 · Comunas CABA - sedes, subsedes y Unidad de Atención Ciudadana

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero importar sedes comunales y enriquecer por sede/subsede. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-005.

**Criterios de aceptación:**

1. Dada F20, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Conservar dirección catastral y legible, sin asignar teléfono general como propio de sede.

3. Conflicto de piso de Subsede 2 se retiene; CRS desconocido y horarios ausentes quedan explícitos.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/sedes-comunales/sedes_comunales.csv](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/sedes-comunales/sedes_comunales.csv)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DATASET ABIERTO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 43; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre · organismo · tipo · direccion · direccion_legible · barrio · comuna · telefono · horario · url_ficha · x_local · y_local · lat · lng



### HU-F21 · Fuente excluida por antibot/robots; identidad por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar URL del relevamiento y evaluar alternativa pública autorizada; acceso bloqueado permanece explícito. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F21, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVERY_REQUIRED · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F22 · Fuente excluida por antibot/robots; identidad por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar URL del relevamiento; no recrear un scraper sin identificar fuente y alcance. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F22, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVERY_REQUIRED · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F23 · Beca Alimentaria - Ordenanza 43.478/89 (Comedores Escolares, CABA)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar ordenanza y relacionar modificaciones/renumeración. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F23, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Preservar preámbulo y artículo 23 bis del original; no omitir texto previo al artículo 1.

3. Verificar equivalencias 10→9 y 16→15 con versiones identificadas; no reemplazar el artículo equivocado.

4. Estado No vigente de Ley 547 no borra automáticamente contenido incorporado a la ordenanza.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/38345](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/38345)

**Destino SQL:** `normas`, `norma_versiones`, `equivalencias_unidades`, `reglas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 46; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** No hay bloque de campos separado: aplicar modelo normativo y contrato de fuente.



### HU-F24 · Beca Alimentaria - iniciar trámite (landing del sistema en línea)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar landing pública mediante vía segura o importación controlada. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F24, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No relajar hostname/TLS para resolverla; registrar disponibilidad de fuente equivalente.

3. Deduplicar botones responsive y separar aviso operativo del trámite; no inferir campaña de un texto que mezcla años.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [http://sistemas1.buenosaires.edu.ar/wsad/becas_web.php/](http://sistemas1.buenosaires.edu.ar/wsad/becas_web.php/)

**Destino SQL:** `tramites`, `canales`.

**Estado inicial:** MANUAL · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 14 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 49; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_tramite · canales_de_inicio (accion + url) · url_consulta_estado · telefono_contacto (lista) · email_contacto (lista) · aviso_modal_turnos · md5_cuerpo · anomalias



### HU-F25 · Ley de Educacion Nacional 26.206 (texto actualizado InfoLEG)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar Ley de Educación 26.206 y vínculos pertinentes. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F25, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Detectar/registrar encoding y procesar variantes de marcadores con parser común.

3. Separar notas de sustitución como evidencia de versiones; no incluirlas como una nueva condición de acceso.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://servicios.infoleg.gob.ar/infolegInternet/anexos/120000-124999/123542/texact.htm](https://servicios.infoleg.gob.ar/infolegInternet/anexos/120000-124999/123542/texact.htm)

**Destino SQL:** `normas`, `norma_versiones`, `unidades_documentales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 52; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** No hay bloque de campos separado: aplicar modelo normativo y contrato de fuente.



### HU-F26 · Constitución de CABA; copia del equipo

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero localizar versión oficial y relacionar copia manual sin atribuirle vigencia por fecha de descarga. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F26, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** MANUAL · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F27 · Inscripción escolar CABA (página de trámite)

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar inscripción escolar visible para el ciclo correcto. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F27, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Excluir bloques d-none de la respuesta actual y conservarlos como antecedente si es necesario.

3. Acotar teléfonos al contenido del trámite; no capturar emergencias del pie como contacto escolar.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [http://www.buenosaires.gob.ar/inscripcionescolar](http://www.buenosaires.gob.ar/inscripcionescolar)

**Destino SQL:** `tramites`, `plazos`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 55; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** url_canonica · titulo · ciclo_lectivo · cuerpo_visible · cuerpo_oculto_ciclo_anterior · cta_inicio_tramite · telefonos_ayuda · fingerprint · anomalias



### HU-F28 · Preinscripcion escolar FAQ (ancla #44) - alias de F31 con ancla rota

**Prioridad:** P2 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero registrar alias de FAQ y ancla rota. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dado el alias F28, se verifica su relación con F31 y se registra sin crear contenido semántico duplicado.

2. Alias de F31 sin duplicar capturas/chunks semánticos.

3. No identificar #44 con otra ancla por coincidencia numérica; reconstruir enlace solo con evidencia de pregunta.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.buenosaires.gob.ar/educacion/estudiantes/inscripcionescolar/preguntas-frecuentes#44](https://www.buenosaires.gob.ar/educacion/estudiantes/inscripcionescolar/preguntas-frecuentes#44)

**Destino SQL:** `fuentes`, `fuente_urls`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** DESCARTAR · **TTL del manual:** 15 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 57; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** url_alias · url_canonica · ancla_original_rota · es_alias_de_F31 · mapa_pregunta_a_ancla_real · anomalias



### HU-F29 · Sistema de inscripción escolar en línea (alias de F27)

**Prioridad:** P2 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero registrar alias de inscripción escolar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dado el alias F29, se verifica su relación con F27 y se registra sin crear contenido semántico duplicado.

2. Un solo trámite canónico con F27; conservar redirecciones.

3. Tokens de formularios no constituyen cambio sustantivo; aplicación con login queda como canal.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.buenosaires.gob.ar/educacion/estudiantes/inscripcionescolar](https://www.buenosaires.gob.ar/educacion/estudiantes/inscripcionescolar)

**Destino SQL:** `fuentes`, `fuente_urls`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** DESCARTAR · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 59; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** url_alias · url_canonica · hash_cuerpo · es_alias · estado_sistema_iel · anomalias



### HU-F30 · Documento del equipo en Drive/Docs; identidad por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero obtener título, archivo y origen del inventario original; aplicar el contrato de ingesta manual. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F30, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** MANUAL · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F31 · Preguntas frecuentes inscripción escolar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer FAQ escolar por sección y pregunta. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F31, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Preguntas de calendario se asocian a ciclo/fecha, no al año de captura.

3. Preservar respuesta completa y ancla; material 2025 no se presenta como calendario vigente sin revalidar.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.buenosaires.gob.ar/educacion/estudiantes/inscripcionescolar/preguntas-frecuentes](https://www.buenosaires.gob.ar/educacion/estudiantes/inscripcionescolar/preguntas-frecuentes)

**Destino SQL:** `documentos`, `unidades_documentales`, `plazos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 15 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 61; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** seccion · orden_seccion · pregunta · respuesta · ancla · url_deep_link · fingerprint · anomalias



### HU-F32 · Turnero de Inscripción en Línea (turnos presenciales)

**Prioridad:** P1 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero observar estado público de turnos sin reservar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada F32, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No convertir mensajes sin cupo ni shortcuts en oficinas o trámites nuevos.

3. No abrir sesión ni reservar; cierre estacional se registra con fecha y ámbito.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://turnoseducacion.buenosaires.gob.ar/inscripcionEnLinea](https://turnoseducacion.buenosaires.gob.ar/inscripcionEnLinea)

**Destino SQL:** `fuentes`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 63; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** estado_turnos · mensaje_del_sistema · accesos_disponibles · urls_de_acciones · tramites_ofrecidos · version_app · observado_en · anomalias



### HU-F33 · Ley de Asignaciones Familiares 24.714 / AUH (texto actualizado InfoLEG)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar Ley 24.714 y contexto de AUH. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F33, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Preservar artículo/sufijo, nota de abrogación-restablecimiento y excepciones.

3. Separar antecedentes sin perder anexos; montos históricos nunca alimentan valor actual por extracción de símbolos $.

4. Cerrar D01/D02 y descubrir normas de AUH y de importes necesarias para el caso de uso.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://servicios.infoleg.gob.ar/infolegInternet/anexos/35000-39999/39880/texact.htm](https://servicios.infoleg.gob.ar/infolegInternet/anexos/35000-39999/39880/texact.htm)

**Destino SQL:** `normas`, `norma_versiones`, `relaciones_normativas`, `reglas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 65; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** No hay bloque de campos separado: aplicar modelo normativo y contrato de fuente.



### HU-F34 · Login o turnero ANSES del catálogo; URL por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar vínculo de canal; no operar sesión ni completar formularios. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F34, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F35 · Video de apoyo del catálogo; URL por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar título y enlace como apoyo; no afirmar que existe transcripción normativa ingesta. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F35, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F36 · Tramitar DNI

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recorrer hub DNI con frontera persistente y hojas públicas. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F36, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Un hub no es un trámite completo; se rastrean hojas con presupuesto y cola pendiente visible.

3. No duplicar li/p anidados; aranceles se separan con TTL propio y fecha de aplicación.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/interior/dni](https://www.argentina.gob.ar/interior/dni)

**Destino SQL:** `tramites`, `tramite_pasos`, `parametro_valores`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 68; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo · url · es_hub · dirigido_a · requisitos · como_hago · duracion · costo · vigencia · pasos_ord · cta_url · etiquetas



### HU-F37 · Login o turnero ANSES del catálogo; URL por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero registrar vínculo verificado como canal; no leer cuenta de una persona. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F37, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F38 · Guia de prevencion de desalojos (PDF)

**Prioridad:** P2 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar guía de desalojos como referencia fechada. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-007.

**Criterios de aceptación:**

1. Dada F38, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No derivar organigrama ni contactos actuales del folleto 2021.

3. Marco normativo se contrasta con normas y contactos con F61; solo se cita lo que efectivamente respalda el documento.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/sites/default/files/2021/08/guia_prevencion_desalojos.pdf](https://www.argentina.gob.ar/sites/default/files/2021/08/guia_prevencion_desalojos.pdf)

**Destino SQL:** `documentos`, `unidades_documentales`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** PDF CON TEXTO · **TTL del manual:** 180 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 71; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** texto_por_pagina · numero_pagina · titulo_pdf (/Title de metadata) · fecha_documento (last-modified: 2021-09-02) · etag · sha256_del_archivo · organismos_mencionados (Ministerio Publico Fiscal, Ministerio Publico de la Defensa, Defensoria del Pueblo de la Nacion) · telefono '0800 222 3245' · url_renabap_mapa · referencia normativa (ley 27.453, Certificado de Vivienda Familiar)



### HU-F39 · Listado RENABAP (padron de barrios populares)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero importar padrón RENABAP desde recurso público permitido. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-005.

**Criterios de aceptación:**

1. Dada F39, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Tabla propia con fecha de corte, identificación oficial y conciliación.

3. No usar API key de tercero como fallback; ausencia de coincidencia no niega protección jurídica.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/obras-publicas/sisu/renabap/listado-renabap](https://www.argentina.gob.ar/obras-publicas/sisu/renabap/listado-renabap)

**Destino SQL:** `barrios_renabap`, `documento_versiones`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DATASET ABIERTO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 73; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** id_renabap · nombre_barrio · provincia · departamento · localidad · cantidad_viviendas_aproximadas · cantidad_familias_aproximada · decada_de_creacion · anio_de_creacion · energia_electrica · efluentes_cloacales · agua_corriente · cocina · calefaccion · titulo_propiedad · clasificacion_barrio · superficie_m2 · url_mapa (derivada: .../renabap/mapa#<id_renabap>)



### HU-F40 · Decreto 690/2006 situación de calle (PDF texto actualizado, Boletin Oficial CABA)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer decreto PDF y evaluar condición transitoria. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F40, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Detectar warning antes de %PDF y EOF irregular; conservar raw y diagnóstico de derivación.

3. No usar idf=1 como fallback sin comprobar PDF real; no aplicar limpieza de espacios que una palabras.

4. Vincular Ley 6935 y el monitor de reglamentación; no marcar condición resuelta sin evidencia.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=86704&idf=2](https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=86704&idf=2)

**Destino SQL:** `normas`, `norma_versiones`, `unidades_documentales`, `plazos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF CON TEXTO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 76; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** No hay bloque de campos separado: aplicar modelo normativo y contrato de fuente.



### HU-F41 · CUD - Certificado Único de Discapacidad (ACIJ, fuente NO oficial)

**Prioridad:** P2 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar material secundario CUD con atribución y enlazar fuente oficial. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F41, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Fecha editorial 2021 se conserva; no etiquetar ONG como organismo oficial.

3. No sustituir cita de ACIJ por una oficial si esta no respalda la afirmación; usar fuente oficial M06 para requisitos actuales.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://discapacidadyderechos.org.ar/prestaciones/certificado-unico-discapacidad/](https://discapacidadyderechos.org.ar/prestaciones/certificado-unico-discapacidad/)

**Destino SQL:** `documentos`, `unidades_documentales`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 79; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo · url · bloques_texto · enlaces_salientes · audio_url · paginas_hijas · modified_gmt · fuente_no_oficial · organizacion



### HU-F42 · AySA; fuente con restricción de acceso

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar URL y gestionar alternativa pública o documento institucional; no evadir antibot ni abrir puertos. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F42, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVERY_REQUIRED · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F43 · Reclamos a ERAS (Ente Regulador de Agua y Saneamiento)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar vías públicas de reclamo ERAS y hojas asociadas. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F43, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Distinguir hub y trámite; conservar requisito de reclamo previo cuando esté respaldado.

3. No guardar email protected ni desofuscar protección de correo; usar canal institucional publicado por vía permitida.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/eras](https://www.argentina.gob.ar/eras)

**Destino SQL:** `tramites`, `canales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 82; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_organismo · direccion · codigo_postal · telefono · email (decodificado de data-cfemail) · whatsapp · tarjetas_atajos (titulo + url) · url_tramite_reclamos · titulo_tramite · alerta_previa_AySA · cuerpo_tramite



### HU-F44 · Listado defensorias del pueblo (param idS)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero cargar las tres secciones publicadas del directorio de defensorías. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F44, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Descubrir y validar idS 2100/2200/2300 desde navegación, sin barrer parámetros arbitrarios.

3. Atribuir cada oficina al operador real; no tratar otros defensores como sedes DPN.

4. No desofuscar correos; duplicados requieren conciliación de entidad, no descarte por nombre solo.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.dpn.gob.ar/oficinas.php?idS=2300](https://www.dpn.gob.ar/oficinas.php?idS=2300)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 84; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** seccion (regional / receptoria / otro defensor) · provincia · nombre de la oficina · direccion (calle y numero) · localidad · codigo_postal · telefonos (lista) · emails (lista, decodificados de Cloudflare) · sitio web



### HU-F45 · Reclamo ante Defensa del Consumidor

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar ficha vigente de Defensa del Consumidor. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F45, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. URL histórica 404 se conserva como alias fallido, no se parsea página de error.

3. Extraer li de primer nivel y pasos completos; duracion vacía no significa duración cero.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/servicio/iniciar-un-reclamo-ante-defensa-del-consumidor](https://www.argentina.gob.ar/servicio/iniciar-un-reclamo-ante-defensa-del-consumidor)

**Destino SQL:** `tramites`, `tramite_pasos`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 87; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo · url_canonica · node_id · dirigido_a · requisitos · como_hago · duracion · costo · es_gratuito · pasos · cta_url · etiquetas



### HU-F46 · EDENOR - Servicio técnico

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar canales y contenido técnico EDENOR. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F46, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Validar contrato del endpoint público tRPC observado; contentSlug como lista.

3. DOM de navegación no equivale a artículo; no evaluar JavaScript remoto para extraer contenido.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.edenor.com/hogares-y-comercios/servicio-tecnico](https://www.edenor.com/hogares-y-comercios/servicio-tecnico)

**Destino SQL:** `canales`, `documentos`, `unidades_documentales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** ENDPOINT JSON · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 90; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo · seo_description · hero_title · hero_description · tabs[].title · sections[].title · blocks[].__component · texto_por_bloque · canales (telefono, WhatsApp, SMS, oficina online)



### HU-F47 · EDENOR - Danos en equipamiento electrico

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar reclamo por daños EDENOR y formularios públicos. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F47, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Diferenciar endpoint de cuerpo de endpoint de layout; seguir PDF enlazados como recursos públicos.

3. Preservar plazo de respuesta y tipo de días; no enviar formularios ni construir una reclamación real.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.edenor.com/hogares-y-comercios/tramites/danos-en-equipamiento-electrico](https://www.edenor.com/hogares-y-comercios/tramites/danos-en-equipamiento-electrico)

**Destino SQL:** `tramites`, `tramite_pasos`, `documentos`, `plazos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** ENDPOINT JSON · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 93; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo · tabs (etapas del tramite) · secciones · bloques (__component + titulo + texto) · requisitos · plazo_respuesta · formularios_pdf · links_internos · telefono_contacto



### HU-F48 · EDESUR - Como hacer un reclamo en Edesur

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer post EDESUR y contrastar canales actuales. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F48, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Eliminar CSS embebido del contenido; conservar date y modified del post.

3. Canales antiguos quedan pendientes hasta contraste oficial específico; no explorar puertos no publicados ni eludir WAF.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.edesur.com.ar/novedades/como-hacer-un-reclamo-en-edesur/](https://www.edesur.com.ar/novedades/como-hacer-un-reclamo-en-edesur/)

**Destino SQL:** `canales`, `documentos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** ENDPOINT JSON · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 95; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** post_id · date · modified · titulo · texto_completo · canales (seccion, detalle, telefonos, whatsapp, emails, horario) · enlaces_normalizados · enlaces_rotos_en_origen



### HU-F49 · ENRE - Formularios en línea (gestión de reclamos)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar hub ENRE y fichas públicas de reclamo. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F49, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Guardar URL del iframe como canal; no relajar suites TLS ni enviar formulario Lotus Domino.

3. Separar vías web y TAD; no duplicar trámites al encontrarlos en navegación y cuerpo.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/enre/gestion-de-reclamos/formularios-online](https://www.argentina.gob.ar/enre/gestion-de-reclamos/formularios-online)

**Destino SQL:** `tramites`, `canales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 98; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_hub · lista_tramites_web (texto + url) · lista_tramites_tad · arbol_seccion (book-nav) · url_formulario_externo (iframe enre.gov.ar) · por ficha /servicio/: titulo, resumen, etiquetas, a_quien, que_necesito, como_hago, costo, pasos, cta



### HU-F50 · ENRE - Saca turno por Internet (turno previo)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar formas públicas de obtener turno ENRE. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F50, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Seleccionar contenedor pertinente con texto, no el primero vacío.

3. No inventar dirección/horario; tomarla de otra fuente solo con evidencia y vínculo a la misma sede.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/enre/saca-turno-online](https://www.argentina.gob.ar/enre/saca-turno-online)

**Destino SQL:** `tramites`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 14 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 101; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo · cuerpo (3 vias para sacar turno) · url_verificacion_turno · url_mapa_sede · telefonos_0800 · urls_relacionadas · resumen_markdown (meta description) · hash_control



### HU-F51 · ENRE - portada del organismo / sección 'Mas información'

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar estructura pública ENRE y descubrir novedades relevantes. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F51, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Recorrer panes hermanos asociándolos a sección correcta; no cortar en el primer bloque vacío.

3. Verificar cambios de organismo competente y guardar relaciones de sucesión respaldadas, sin inferirlas del slug.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/enre](https://www.argentina.gob.ar/enre)

**Destino SQL:** `organismos`, `puntos_atencion`, `canales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 103; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_organismo · bajada (Decreto 452/2025, Ley 24.065) · secciones -> tarjetas (titulo + url + bajada) · barra_superior (6 accesos rapidos) · sedes (nombre + direccion + CP + localidad) · latitud · longitud · noticias_recientes



### HU-F52 · Progresar - Monto de la beca y cronograma de pagos

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar montos y cronogramas por período Progresar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada F52, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Usar contenedor con contenido y validar período por texto/acto; Last-Modified reciente no vuelve actual un cronograma viejo.

3. Modelar terminación de documento, línea, fecha de pago y monto como dimensiones distintas, sin datos de personas reales.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar/cronograma](https://www.argentina.gob.ar/educacion/progresar/cronograma)

**Destino SQL:** `parametro_valores`, `plazos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 3 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 106; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** monto_beca · moneda · texto_crudo_monto · texto_crudo_bloque · fecha_inicio_cronograma · cabeceras_tabla · tabla_dni_terminado_en -> inicio_de_cobro · fecha_captura · vigencia (coherente_con_mes_actual | posiblemente_desactualizado)



### HU-F53 · Progresar - Iniciar trámite, plazos de convocatoria y mapa de subpaginas

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar convocatorias y descubrimiento de hojas Progresar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada F53, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Extraer año del contexto de convocatoria y fechas por línea; resolver ambigüedades antes de calcular.

3. Estado abierto/cerrado se calcula por reloj, aunque el aviso no cambie; cola de enlaces queda deduplicada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar](https://www.argentina.gob.ar/educacion/progresar)

**Destino SQL:** `tramites`, `plazos`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 1 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 109; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_tramite · bajada · aviso_convocatoria_vigente · anio_convocatoria · convocatorias por linea (linea, desde, hasta, estado) · url_inscripcion · enlaces_subpaginas (11) · node_id (55180)



### HU-F54 · Instructivo beca - como revisar una solicitud (PDF)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar instructivo para escuelas y catálogo de PDF relacionados. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-007.

**Criterios de aceptación:**

1. Dada F54, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Etiquetar público institucional, no instrucciones de solicitante.

3. Validar orden Paso N y capturas de pantalla; página gráfica no se interpreta como texto ausente de todo el documento.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://static.buenosaires.gob.ar/sites/default/files/2025-11/21_instructivo%20como%20revisar%20una%20solicitud%20de%20beca.pdf](https://static.buenosaires.gob.ar/sites/default/files/2025-11/21_instructivo%20como%20revisar%20una%20solicitud%20de%20beca.pdf)

**Destino SQL:** `documentos`, `unidades_documentales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF CON TEXTO · **TTL del manual:** 180 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 112; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** texto_por_pagina · titulo (metadata /Title) · autor y fecha de creacion (metadata) · etag y last_modified (para revalidacion condicional) · catalogo_del_indice (los 3 PDFs hermanos) · anomalias



### HU-F55 · Beca Alimentaria - alias sin barra final de F24 (la ficha lo llama 'formulario' y no lo es)

**Prioridad:** P2 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar variante sin barra como alias de F24. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dado el alias F55, se verifica su relación con F24 y se registra sin crear contenido semántico duplicado.

2. No generar trámites/chunks propios; mantener historial de redirección.

3. Hereda problema de acceso de F24, sin excepción de transporte añadida.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [http://sistemas1.buenosaires.edu.ar/wsad/becas_web.php](http://sistemas1.buenosaires.edu.ar/wsad/becas_web.php)

**Destino SQL:** `fuentes`, `fuente_urls`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** DESCARTAR · **TTL del manual:** 14 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 115; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** url_alias · url_canonica · hash_cuerpo · es_alias · n_form · anomalias



### HU-F56 · Beca Alimentaria - requisitos y condiciones (texto de la declaracion jurada)

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar texto público de requisitos por vía segura. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F56, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No atravesar enlace Acepta términos/bienvenida ni enviar declaración jurada.

3. Extraer requisitos visibles preservando base de salario de comercio y excepciones; revalidar contra ordenanza y reformas.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [http://sistemas1.buenosaires.edu.ar/wsad/becas_web.php/terminosycondiciones](http://sistemas1.buenosaires.edu.ar/wsad/becas_web.php/terminosycondiciones)

**Destino SQL:** `documentos`, `reglas`, `tramites`.

**Estado inicial:** MANUAL · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 117; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** titulo_panel · requisitos_y_condiciones (3.057 chars) · norma_citada · topes_en_sueldos_minimos_comercio · incremento_por_hijo_pct · caracter_declaracion_jurada · puerta_de_aceptacion (mapeada, no atravesada) · fingerprint · anomalias



### HU-F57 · Login o turnero ANSES del catálogo; URL por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero mapear al trámite correspondiente cuando se identifique; no generar contenido desde un login. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F57, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F58 · Login o turnero ANSES del catálogo; URL por recuperar

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero mantener referencia del canal y limitación, sin sesiones automatizadas. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F58, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** MANUAL_OR_LINK_ONLY · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F59 · AySA; fuente con restricción de acceso

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero identificar recurso original; exigir evidencia de vía permitida antes de automatizar y registrar alcance pendiente. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-006.

**Criterios de aceptación:**

1. Dada F59, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. El ID permanece en catálogo con causa y responsable; no inventar URL ni contenido.

3. La historia se cierra con vínculo/carga verificados o como bloqueo documentado, manteniendo distinguida la cobertura no poblada.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** Pendiente de recuperar del inventario original. No se proporcionó URL inequívoca en el anexo.

**Destino SQL:** `fuentes`, `fuente_urls`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVERY_REQUIRED · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Campos de referencia de la fuente:** Identidad, acceso, motivo, alcance y procedencia; payload pendiente según documento.



### HU-F60 · Sedes de Atención Social (SAS) - CABA

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero importar SAS y contrastar página de sedes. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-005.

**Criterios de aceptación:**

1. Dada F60, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. N/A se registra como no informado; no como teléfono literal.

3. Conservar dos horarios en conflicto y ausencia de sede en la web sin borrado automático; no afirmar vigencia solo por estar en CSV.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-desarrollo-humano-y-habitat/subsecretaria-familia-y-comunidad/efectores.csv](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-desarrollo-humano-y-habitat/subsecretaria-familia-y-comunidad/efectores.csv)

**Destino SQL:** `puntos_atencion`, `canales`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DATASET ABIERTO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 120; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre · organismo · direccion · barrio · comuna · dias · horario_dataset · horario_web · telefono · email · web · lat · lng



### HU-F61 · RENABAP - canales de asesoramiento desalojos

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar canales de asesoramiento de desalojos. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada F61, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Acotar WhatsApp al cuerpo para excluir botón Compartir.

3. Dirección ausente es válida para canal remoto; no completar con domicilio de otra oficina.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/obras-publicas/sisu/renabap/suspension-de-desalojos-de-barrios-populares/canales-de-asesoramiento-y](https://www.argentina.gob.ar/obras-publicas/sisu/renabap/suspension-de-desalojos-de-barrios-populares/canales-de-asesoramiento-y)

**Destino SQL:** `canales`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 124; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre (texto del h4) · telefono (digitos de tel: o del parametro phone= de api.whatsapp.com) · canal_tipo (telefono / whatsapp / formulario web) · horario (regex sobre el <p>: '9:00 a 17:00') · url (href absoluto del formulario) · detalle (texto completo del <p>) · organismo (SISU / RENABAP) · direccion = NULL (la pagina no publica domicilio)



### HU-F62 · Marco legal, procesos y MONTOS de becas alimentarias y servicios (PDF, ciclo lectivo 2026)

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar umbrales de becas alimentarias por período y composición familiar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-007.

**Criterios de aceptación:**

1. Dada F62, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Distinguir umbral de ingresos, porcentaje de beca y número de hermanos; conservar tabla de origen.

3. Validar cada tabla y período; monotributo histórico no adquiere vigencia por fecha del PDF.

4. Descubrir nueva versión desde índice oficial o registrar falta de hub; no modificar año/mes de URL para adivinar archivos.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://static.buenosaires.gob.ar/sites/default/files/2026-08/Marco_legal_procesos_y_montos_de_analisis_y_otorgamiento_becas_y_servicios.pdf](https://static.buenosaires.gob.ar/sites/default/files/2026-08/Marco_legal_procesos_y_montos_de_analisis_y_otorgamiento_becas_y_servicios.pdf)

**Destino SQL:** `parametro_valores`, `documentos`, `reglas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF CON TEXTO · **TTL del manual:** 7 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 127; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** periodo_texto · anio · meses · es_rango · beca_pct · topes_por_hermanos (0..4) · categoria_monotributo · ingreso_bruto_mensual · monotributo_vigencia · last_modified · etag



### HU-F63 · Preguntas frecuentes de Becas Alimentarias (PDF en sistemas1, host con certificado que no lo cubre)

**Prioridad:** P1 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero recuperar FAQ de becas alimentarias por vía segura. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-038, HU-007.

**Criterios de aceptación:**

1. Dada F63, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. No desactivar verificación de hostname/TLS; usar copia manual trazable o equivalente oficial.

3. Clave de pregunta compuesta por sección y número; revisar pantallas antiguas antes de dar instrucciones actuales.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [http://sistemas1.buenosaires.edu.ar/wsad/becas/Preguntas-Frecuentes-Becas.pdf](http://sistemas1.buenosaires.edu.ar/wsad/becas/Preguntas-Frecuentes-Becas.pdf)

**Destino SQL:** `documentos`, `unidades_documentales`.

**Estado inicial:** MANUAL · **Técnica de referencia:** PDF CON TEXTO · **TTL del manual:** 60 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 131; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** seccion · nro · clave · pregunta · respuesta · last_modified · telefono_boti



### HU-F64 · Sedes y puntos presenciales de inscripción escolar

**Prioridad:** P1 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero monitorear sedes estacionales de inscripción escolar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada F64, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Página que informa cierre y no trae tabla genera estado estacional sin oficinas nuevas.

3. No cargar sedes de Wayback como actuales; cuando reaparece tabla validar encabezados td y ciclo.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://buenosaires.gob.ar/educacion/escuelas/sedes-puntos-presenciales](https://buenosaires.gob.ar/educacion/escuelas/sedes-puntos-presenciales)

**Destino SQL:** `puntos_atencion`, `fuentes`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 134; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** nombre · direccion · distrito_escolar · dias · horarios · aviso · ventana_inscripcion · hay_datos



### HU-F65 · Progresar - FAQ general (la que enlaza la home) - DUPLICADO EXACTO de F17, no es una tercera FAQ

**Prioridad:** P2 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero cerrar lead duplicado y trasladar evidencia de actualización a F17. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dado el alias F65, se verifica su relación con F17 y se registra sin crear contenido semántico duplicado.

2. Alias de F17 por URL/node; cero chunks nuevos.

3. Conservar fecha editorial y diferencias observadas por auditoría; no perder hallazgos útiles al cerrar el duplicado.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar-faq](https://www.argentina.gob.ar/educacion/progresar/preguntas-frecuentes-progresar-faq)

**Destino SQL:** `fuentes`, `fuente_urls`.

**Estado inicial:** REFERENCE_ONLY · **Técnica de referencia:** DESCARTAR · **TTL del manual:** 60 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 137; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** es_duplicado_de (F17) · node_id (461614) · titulo_seccion · modificado (article:modified_time) · intro_antifraude · pregunta · respuesta · pares_no_cubiertos_por_linea (12 de 12) · mejor_jaccard (0.57) · anomalias



### HU-F66 · Progresar - Requisitos por línea (hub /requisitos + 3 hojas: obligatorio, superior, formacion profesional)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar requisitos de las tres líneas Progresar. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F66, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Descubrir hojas desde navegación lateral; el hub no contiene los requisitos.

3. Conflicto de edad con F67 queda a nivel regla; no excluir a una persona escogiendo automáticamente el valor menor.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar/requisitos](https://www.argentina.gob.ar/educacion/progresar/requisitos)

**Destino SQL:** `reglas`, `beneficio_versiones`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** HTML ESTATICO · **TTL del manual:** 30 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 140; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** linea · url_hoja · node_id (246941 / 246943 / 246947) · modificado (article:modified_time) · bloque (h6 'Requisitos') · requisito (un chunk por li, 22 en total) · n_requisitos_por_linea · url_hub y node_hub (246939) · anomalias



### HU-F67 · Progresar - 'Informes' (301 -> /reglamentos): los 3 reglamentos generales en PDF (ANEXO I, II y III)

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero capturar tres reglamentos PDF y resolver acto aprobatorio. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada F67, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Guardar alias /informes y canónica /reglamentos; año de carpeta no es año normativo.

3. Identificador GEDO y fecha de firma no reemplazan identidad/fecha de publicación del acto madre.

4. Procesar capítulos y artículos y vincular anexo a resolución comprobada; pendientes de autoridad bloquean reglas afectadas.

5. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

6. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

7. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/educacion/progresar/reglamentos](https://www.argentina.gob.ar/educacion/progresar/reglamentos); [https://www.argentina.gob.ar/educacion/progresar/informes](https://www.argentina.gob.ar/educacion/progresar/informes)

**Destino SQL:** `documentos`, `norma_versiones`, `reglas`, `referencias_pendientes`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF CON TEXTO · **TTL del manual:** 90 días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Referencia:** Manual de ingesta de fuentes, página 143; observación histórica, no ejecución de este paquete.

**Campos de referencia de la fuente:** linea · titulo_documento · anexo (I | II | III) · gedo (numero_documento, IF-2026-...-APN-SSPIE#MCH) · fecha_firma (/M de la firma digital) · anio_norma · url_pdf · url_alias (/informes) y url_canonica (/reglamentos) · sha256 · bytes · paginas · chars · chars_por_pagina · modo (pdf_directo | pdf_ocr) · capitulo · articulo_nro · articulo_texto · anomalias



### HU-D01 · Decreto DNU 1382/2001

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero conservar efecto de abrogación y alcance con contexto histórico; no concluir vigencia de Ley 24.714 por lectura aislada. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D01, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Conservar efecto de abrogación y alcance con contexto histórico; no concluir vigencia de Ley 24.714 por lectura aislada.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/normativa/nacional/norma-69649](https://www.argentina.gob.ar/normativa/nacional/norma-69649)

**Destino SQL:** `normas`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F33.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D02 · Decreto DNU 1604/2001

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero modelar restablecimiento y excepciones en dirección y fechas correctas; no borrar evento previo. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D02, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Modelar restablecimiento y excepciones en dirección y fechas correctas; no borrar evento previo.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/normativa/nacional/norma-70499/texto](https://www.argentina.gob.ar/normativa/nacional/norma-70499/texto)

**Destino SQL:** `normas`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F33.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D03 · Decreto CABA 75/2015

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero extraer destinatarios, excepciones y competencia para normas operativas, con evidencia por regla. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D03, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Extraer destinatarios, excepciones y competencia para normas operativas, con evidencia por regla.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/273414](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/273414)

**Destino SQL:** `normas`, `reglas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F19.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D04 · Resolución 1621/MEDGC/2025

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero contrastar identidad 1621 frente a síntesis 1261; procesar disposiciones que dejan sin efecto normas previas y vincular D07. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D04, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Contrastar identidad 1621 frente a síntesis 1261; procesar disposiciones que dejan sin efecto normas previas y vincular D07.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/829906](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/829906)

**Destino SQL:** `normas`, `relaciones_normativas`, `tramites`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F19.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D05 · Ley CABA 547/2001

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero preservar cambios de artículos y unidad anidada del texto sustituto; No vigente de la ficha no borra efectos incorporados. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D05, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Preservar cambios de artículos y unidad anidada del texto sustituto; No vigente de la ficha no borra efectos incorporados.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/11223](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/11223)

**Destino SQL:** `normas`, `relaciones_normativas`, `equivalencias_unidades`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F23.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D06 · Ley CABA 6935/2025

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero registrar condición hasta publicación de reglamentación y sus dependencias; monitor M02, sin declarar condición cumplida por defecto. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D06, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Registrar condición hasta publicación de reglamentación y sus dependencias; monitor M02, sin declarar condición cumplida por defecto.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/830431](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/830431)

**Destino SQL:** `normas`, `beneficios`, `plazos`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F40.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D07 · Anexo de Resolución 1621/MEDGC/2025

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero guardar como anexo, no resolución autónoma; preservar procedimientos, subsanación y reconsideración de la versión capturada. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-007.

**Criterios de aceptación:**

1. Dada D07, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Guardar como anexo, no resolución autónoma; preservar procedimientos, subsanación y reconsideración de la versión capturada.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MEDGC-MEDGC-1621-25-ANX.pdf](https://documentosboletinoficial.buenosaires.gob.ar/publico/PE-RES-MEDGC-MEDGC-1621-25-ANX.pdf)

**Destino SQL:** `documentos`, `reglas`, `tramite_pasos`, `plazos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** D04.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D08 · PDF actualizado de Ordenanza 43.478

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero vincular como versión de la misma norma y comprobar renumeración, sin aplicar dos veces Ley 547. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D08, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Vincular como versión de la misma norma y comprobar renumeración, sin aplicar dos veces Ley 547.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idf=1&idn=38345](https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idf=1&idn=38345)

**Destino SQL:** `documento_versiones`, `norma_versiones`, `equivalencias_unidades`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F23.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D09 · PDF actualizado de Ley 2917

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero revalidar PDF desde panel Texto actualizado y reformas posteriores; la etiqueta actualizado no asegura cobertura hasta hoy. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D09, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Revalidar PDF desde panel Texto actualizado y reformas posteriores; la etiqueta actualizado no asegura cobertura hasta hoy.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=125647&idf=1](https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=125647&idf=1)

**Destino SQL:** `documento_versiones`, `norma_versiones`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** PDF · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F19.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-D10 · Ficha HTML de Decreto CABA 690/2006

**Prioridad:** P0 · **Capacidad responsable:** `curacion_juridica`

**Historia:** Como curador de datos del sistema conversacional, quiero leer relaciones y representaciones del decreto; original HTML y PDF de F40 no son necesariamente la misma versión. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-008, HU-009, HU-010, HU-012.

**Criterios de aceptación:**

1. Dada D10, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Leer relaciones y representaciones del decreto; original HTML y PDF de F40 no son necesariamente la misma versión.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/normativaba/norma/86704](https://boletinoficial.buenosaires.gob.ar/normativaba/norma/86704)

**Destino SQL:** `fuentes_candidatas`, `relaciones_normativas`, `norma_versiones`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** NORMATIVE_HTML · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F40.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-M01 · Monitor Boletín Oficial nacional

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero descubrir publicación/buscador públicos y registrar ventana, cursor, paginación y evidencia. Filtrar actos relevantes por identidad y programa, sin adivinar endpoints. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada M01, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Descubrir publicación/buscador públicos y registrar ventana, cursor, paginación y evidencia. Filtrar actos relevantes por identidad y programa, sin adivinar endpoints.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.boletinoficial.gob.ar/](https://www.boletinoficial.gob.ar/)

**Destino SQL:** `fuentes_candidatas`, `documentos`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVER_PUBLIC_INDEX · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F01.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-M02 · Monitor Boletín Oficial CABA

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero monitorear actos y anexos de educación/vivienda y condición Ley 6935. Publicación candidata abre revisión de alcance, no sustitución automática. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada M02, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Monitorear actos y anexos de educación/vivienda y condición Ley 6935. Publicación candidata abre revisión de alcance, no sustitución automática.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.buenosaires.gob.ar/](https://boletinoficial.buenosaires.gob.ar/)

**Destino SQL:** `fuentes_candidatas`, `documentos`, `relaciones_normativas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVER_PUBLIC_INDEX · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F19, F23, F40, D06.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-M03 · Monitor normativa PBA

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero descubrir búsqueda/actualizaciones públicas y sus capacidades; mantener separado el alcance provincial del municipal. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada M03, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Descubrir búsqueda/actualizaciones públicas y sus capacidades; mantener separado el alcance provincial del municipal.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://normas.gba.gob.ar/](https://normas.gba.gob.ar/)

**Destino SQL:** `fuentes_candidatas`, `normas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVER_PUBLIC_INDEX · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F09.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-M04 · Monitor Boletín Oficial PBA

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero verificar acceso y mecanismo público de novedades; la consulta de este paquete fue no concluyente, no se presume endpoint operativo. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada M04, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Verificar acceso y mecanismo público de novedades; la consulta de este paquete fue no concluyente, no se presume endpoint operativo.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://boletinoficial.gba.gob.ar/](https://boletinoficial.gba.gob.ar/)

**Destino SQL:** `fuentes_candidatas`, `documentos`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVER_PUBLIC_INDEX · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** M03.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-M05 · ANSES: descubrimiento de AUH, montos y calendario público

**Prioridad:** P0 · **Capacidad responsable:** `monitoreo`

**Historia:** Como curador de datos del sistema conversacional, quiero descubrir páginas oficiales AUH y calendarios desde navegación pública; no consultar cobros personalizados ni logins. Distinguir resoluciones de monto y calendario público. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-026, HU-027.

**Criterios de aceptación:**

1. Dada M05, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Descubrir páginas oficiales AUH y calendarios desde navegación pública; no consultar cobros personalizados ni logins. Distinguir resoluciones de monto y calendario público.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.anses.gob.ar/](https://www.anses.gob.ar/)

**Destino SQL:** `fuentes_candidatas`, `parametro_valores`, `plazos`, `tramites`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVER_PUBLIC_INDEX · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F33.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.



### HU-M06 · Ficha oficial para obtener CUD

**Prioridad:** P0 · **Capacidad responsable:** `ingesta`

**Historia:** Como curador de datos del sistema conversacional, quiero contrastar requisitos y procedimientos con fuente oficial y normas enlazadas; conservar atribución de material secundario F41 sin convertirlo en norma. para incorporar la fuente con cobertura y evidencia acordes a su alcance.

**Dependencias:** HU-001, HU-003, HU-004, HU-022, HU-006.

**Criterios de aceptación:**

1. Dada M06, al ejecutar su contrato se registra URL final, acceso, contenido recibido y resultado; una falla no se presenta como carga exitosa.

2. Contrastar requisitos y procedimientos con fuente oficial y normas enlazadas; conservar atribución de material secundario F41 sin convertirlo en norma.

3. Capturar evidencia y distinguir documento, norma, anexo y versión; no afirmar vigencia solo por disponibilidad.

4. Los datos extraídos se mapean a las tablas destino con evidencia y estado por campo; los hechos históricos del manual se revalidan antes de tratarlos como actuales.

5. La reingesta idéntica no duplica entidades ni versiones de contenido; se conserva la nueva observación.

6. El cierre entrega muestra real de filas y controles, o bloqueo verificable con responsable y capacidad afectada; no se contabiliza bloqueo como contenido poblado.

**Entregables:** Contrato de fuente versionado; Corrida/diagnóstico verificable; Datos SQL con evidencia o estado de bloqueo; Pruebas de regresión específicas.

**Evidencia de cierre:** resultado de acceso real; reconciliación de filas/unidades; muestra de datos/citas; controles de calidad ejecutados.



**URL(s) identificada(s):** [https://www.argentina.gob.ar/servicio/como-obtener-el-certificado-unico-de-discapacidad-cud](https://www.argentina.gob.ar/servicio/como-obtener-el-certificado-unico-de-discapacidad-cud)

**Destino SQL:** `tramites`, `reglas`, `plazos`, `fuentes_candidatas`.

**Estado inicial:** DISCOVERY · **Técnica de referencia:** DISCOVER_PUBLIC_INDEX · **TTL del manual:** no especificado días. Ajustar frescura por tipo de dato; no confundir TTL con vigencia legal.

**Fuentes vinculadas:** F41.

**Campos de referencia de la fuente:** Identidad, texto/relaciones o novedades, fechas, alcance, evidencia y siete campos cuando corresponda.

