# Acta: los PDF normativos entran al grafo

Evidencia parcial de P-007, criterios 1 y 2. Registra lo verificado el 9 de
septiembre de 2026 sobre el corpus real.

## Lo que estaba pasando

El criterio 1 nombra cuatro fuentes: F33, F19, F23 y **F40**. Las tres primeras
producían relaciones —226, 16 y 1—. F40 producía **cero**, con 132 unidades
extraídas. No era un problema de F40: era de todos los PDF.

La cadena tenía tres eslabones cortados, y cada uno bastaba solo para romperla:

1. **`CapturaMaterial.config` viajaba siempre vacía.** El campo existía y el
   adaptador de PDF lo leía —`captura.config.get("tipo_documento")`—, pero la
   extracción nunca se lo pasaba. El adaptador decidía siempre a ciegas.
2. **Nadie llenaba `selector_config`.** La carga del catálogo insertaba la
   configuración de cada fuente sin ese campo. Aunque el eslabón anterior
   hubiera estado, no había qué leer.
3. **Sin declaración, el PDF caía en `OTRO`, y en silencio.** `OTRO` deja el
   documento fuera de la resolución de identidad —que filtra por
   `d.tipo = 'NORMA'`—, así que el texto se extraía entero y no llegaba a
   ninguna norma. Nada lo decía.

Y detrás había un cuarto: aunque el tipo hubiera sido `NORMA`, el adaptador
declaraba `tipo_version = NO_DETERMINADO` para todo, y la resolución no crea
versión normativa para un documento así —con razón: la ficha de una norma la
describe y no la contiene—. Un PDF con articulado sí la contiene.

**Alcance real:** cuatro fuentes de clase `PORTAL_NORMATIVO` cuyo texto nunca
llegó al grafo. D08 (77 unidades), D09 (46) y F40 (132) quedaron con documentos
`OTRO`; F67 quedó como `GUIA` por otra vía.

## Lo que se cambió

- La jurisdicción se deriva del host que publica (`boletinoficial.gba.gob.ar` →
  AR-B, `*.buenosaires.gob.ar` → AR-C, `*.gob.ar` → AR), con el sufijo más
  específico ganando. Un PDF no trae portal que lo identifique; los adaptadores
  de HTML sí saben de qué sitio leen.
- El tipo de documento se deriva de la clase declarada de la fuente. No se
  escribe fuente por fuente: una fuente normativa nueva lo recibe sola. Las
  clases que no dicen qué traen —`DOCUMENTO`, `CANAL_ATENCION`, `OTRA`— no
  declaran nada a propósito.
- La extracción le pasa esa configuración al adaptador.
- El PDF lee su identidad del encabezado, que es donde el documento la declara:
  `DECRETO Nº 690/2006`. La letra temática del Digesto porteño —`ORDENANZA F –
  N° 43.478`— se reconoce como lo que es, una clasificación del Digesto, y no
  se confunde con el número.
- Un PDF con artículos declara ser una versión del texto. Original o rearmado
  no se supone: lo dicen las notas al pie que el propio texto trae.
- Sin declaración, el PDF **avisa** en vez de elegir en silencio.
- Un documento que quedó como `OTRO` por falta de declaración se corrige al
  reextraer, y solo en ese sentido: reclasificar uno que ya tenía tipo es una
  decisión, y una decisión no se toma dentro de una reextracción.
- La resolución de identidad acepta una clave sin año **cuando la jurisdicción
  tiene una sola norma con ese tipo y número**. Con más de una no elige: abre
  incidencia con los años candidatos.

## Lo que el esquema hizo notar

Al declarar los textos del Digesto como `CONSOLIDADO`, la base los rechazó:
`ck_norma_versiones_consolidado_con_fecha` exige `fecha_consolidacion`. Tiene
razón —un consolidado sin esa fecha no dice hasta cuándo incorpora cambios— y
esos PDF no la traen. Quedan como `ACTUALIZADO`, con un aviso que dice
exactamente eso: el texto está rearmado, y hasta dónde no se sabe.

## Resultado

Las tres fuentes son ahora versiones de las normas que ya estaban en el corpus,
no normas nuevas:

| Fuente | Unidades | Norma | Versión |
| --- | ---: | --- | ---: |
| D08 | 77 | Ordenanza 43.478/1989 (AR-C) | 2 |
| D09 | 46 | Ley 2.917/2008 (AR-C) | 3 |
| F40 | 132 | Decreto 690/2006 (AR-C) | 3 |

Ninguna norma creada de más: las tres se vincularon a las existentes. D07 quedó
además corregida de `OTRO` a `PROCEDIMIENTO`.

### Un hallazgo jurídico

El artículo 2 del Decreto 690/2006 dice cosas distintas según qué
representación se lea:

- **Ficha HTML (D10)**: «Créase el programa *Atención para Familias en Situación
  de Calle*», autoridad de aplicación la Dirección General de Fortalecimiento
  Familiar y Socio-Comunitaria.
- **PDF actualizado (F40)**: «Crear el *Programa Apoyo para Personas en
  Situación de Vulnerabilidad Habitacional*», autoridad de aplicación la
  Dirección General Red de Atención, **sustituido por el Decreto 161/2025**.

El corpus venía sirviendo el texto anterior a 2025: otro nombre de programa y
otra oficina donde ir. Con F40 adentro, las dos versiones conviven y la consulta
por fecha puede elegir.

## Lo que queda en la cola, que es donde tiene que estar

F40 dejó 12 referencias pendientes, cada una con su identidad candidata, el tipo
de relación sugerido y la constancia de que no hay candidata en el corpus. Entre
ellas el **Decreto 161/2025 de CABA**, que es el que sustituye su artículo 2.

Vale la pena decir por qué no se resolvió: el corpus tiene 41 normas nacionales
numeradas «Decreto 161», una de ellas de 2025. La citada es de CABA. El
resolutor no cruzó jurisdicciones —«una ordenanza citada en una norma de CABA es
de CABA»— y la dejó pendiente. Eso es exactamente el criterio 2: se conserva
cada identidad jurisdiccional. Traer el Decreto 161/2025 porteño es trabajo de
fuente, no de curación.

## Lo que este acta no acredita

- **P-007 no está completo.** Esto cubre el criterio 1 para F40 y parte del 2.
  El criterio 3 —modificación, derogación y dos fechas de consulta— tiene el
  mecanismo (`bn_motivos_no_servible` y la bitemporalidad del registro) pero no
  el ensayo escrito sobre estas dos versiones del Decreto 690.
- **F67 sigue afuera.** Es `PORTAL_NORMATIVO` y su documento quedó como `GUIA`:
  la URL capturada es el índice HTML, no los tres reglamentos en PDF. Es trabajo
  de P-006.
- **La corrida limpia no se rehizo.** Lo verificado es sobre la base de
  desarrollo, reextrayendo fuente por fuente. Que el resultado sea el mismo
  partiendo de una base vacía lo dice la corrida limpia, que no corrió.
- **La derivación por host es una tabla, no una verdad.** Un organismo nacional
  que publique bajo un dominio provincial quedaría mal clasificado. Hoy no hay
  ninguno así en el corpus; si aparece, se ve en la conciliación del catálogo.
