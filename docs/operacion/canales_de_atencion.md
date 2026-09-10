# Acta de los canales de atención

Evidencia de P-006. Doce de las diecisiete fuentes «capturadas, extraídas y sin
destino» declaraban `canales` en su historia: teléfonos, correos, WhatsApp y
formularios por donde se accede a un derecho. Es también una de las siete
dimensiones y una de las ocho capacidades, y es lo primero que necesita quien
consulta: dónde ir.

## Qué se cargó

52 canales sobre el corpus real, en siete fuentes:

| Fuente | Organismo | Canales |
| --- | --- | ---: |
| F03 | Defensoría del Pueblo (CABA) | 3 |
| F05 | Asesoría General Tutelar (CABA) | 15 |
| F07 | Consejo de Derechos de NNyA (CABA) | 28 |
| F27 | Ministerio de Educación (CABA) | 2 |
| F43 | Ente Regulador de Agua y Saneamiento | 1 |
| F51 | Ente Nacional Regulador de la Electricidad | 2 |
| F61 | Secretaría de Integración Socio Urbana | 1 |

El recuento de fuentes pasó de **31 a 38 sirviendo**, y las «sin destino» de 17 a
10.

## Tres reglas, y las tres son sobre lo que no se hace

**El organismo se declara, no se adivina.** `canales.organismo_id` no admite
nulo y ninguna fuente del catálogo trae organismo. Emparejar el nombre de una
fuente contra la tabla de organismos por parecido pondría el teléfono de un
organismo bajo el nombre de otro, y **quien llame va a marcar ese número**. La
correspondencia vive en `ORGANISMOS_POR_FUENTE`, escrita a mano y revisable en un
diff: cada línea se verificó abriendo la página y leyendo de quién es. No se
infiere de la URL —`argentina.gob.ar` aloja decenas de organismos distintos—.

Dos fuentes quedaron sin cargar por esto mismo: **F44** con 31 canales y **M02**
con 10. Cada una dejó una incidencia que dice cuántos encontró y dónde se
declara el organismo que falta.

**Un valor que no normaliza no es un canal.** «1999 1998 1997» tiene la forma de
un teléfono para una expresión regular y es una lista de años. La defensa está en
dos capas: el patrón encuentra candidatos y la normalización decide, así que un
patrón que se ensancha no arrastra basura a la base. Tampoco se completa una
característica que falta: un número de ocho dígitos sin característica es uno al
que no se puede llamar desde afuera de esa ciudad, y ponerle la de Buenos Aires
sería fabricar el dato.

**El tipo lo dice la página, no el número.** Un mismo número puede ser teléfono o
WhatsApp, y eso lo declara el rótulo de la sección. Lo mismo con un enlace: es
formulario si la sección dice que lo es.

## Cada canal cita de dónde salió

La evidencia apunta a la unidad informativa y guarda **la sección entera**, no
solo el número: un teléfono suelto no dice para qué es. Así, el canal
`1165366767` se lee junto a «Oficinas NUEVA BALVANERA - SAN CRISTÓBAL (11)
6536-6767 oad-balvanera-sancristobal@mptutelar.gob.ar», que es lo que la página
publicó.

## Lo que este acta no acredita

- **Que los canales sigan vigentes.** Se cargan como versiones `CANDIDATE` con
  `valid_tipo = 'DESCONOCIDO'`: la página los publicaba el día de la captura y
  eso es todo lo que se puede afirmar. Un teléfono que dejó de atender se ve
  igual que uno que atiende.
- **Que estén completos.** Se cargó lo que las secciones publican en texto. Un
  canal que la página muestra en una imagen, en un mapa o detrás de un
  desplegable que no se abre sin JavaScript no está.
- **Que el canal corresponda al beneficio que quien consulta pregunta.** El canal
  cuelga del organismo, no del beneficio: decir que este teléfono es «el de la
  beca» exige una lectura que no se hizo.
- **Las diez fuentes que siguen sin destino.** Declaran `tramites`,
  `tramite_pasos`, `puntos_atencion` y `parametro_valores`, que necesitan sus
  propios curadores. Las secciones informativas ya están: lo que falta es
  leerlas.
