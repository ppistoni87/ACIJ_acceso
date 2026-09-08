# ADR 0002 · Supertipo de versiones y bitemporalidad

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

Las afirmaciones, los controles de calidad y las incidencias apuntan a "una
versión de algo": puede ser una norma, un beneficio, un valor de parámetro, un
plazo, un trámite, un punto de atención, un canal o un barrio del padrón. El
diccionario advierte contra las claves foráneas polimórficas sin control.

Además, la especificación separa dos ejes que suelen confundirse: el período en
que un hecho **se aplica** y el período en que el sistema **lo conoció**.

## Decisión

`registro_versiones` es un supertipo con `entidad_tipo` y `entidad_id`. Cada
subtipo tiene el `registro_version_id` como clave primaria y un trigger de
restricción verifica que el tipo y la entidad coincidan con lo que declara el
supertipo.

Para que `entidad_id` apunte a algo estable, los subtipos que no tenían una
entidad lógica propia la ganan: `parametro_valores.hecho_id`,
`plazos.plazo_id`, `canales.canal_id` y `barrios_renabap.barrio_id`. Corregir un
valor publicado crea una versión nueva del mismo hecho, no un hecho distinto.

La bitemporalidad se guarda en el supertipo: `valid_desde`/`valid_hasta` con
`valid_tipo`, y `known_desde`/`known_hasta`. `valid_tipo = DESCONOCIDO` no
produce rango: un límite temporal que no conocemos no se vuelve infinito
aplicable por defecto.

## Consecuencias

- Una afirmación puede referirse a cualquier versión con una única clave foránea
  real, y el trigger impide que un subtipo se apropie de la versión de otro.
- `parametro_valores` mantiene un espejo del rango y del estado
  (`rango_aplicacion`, `publicable`), sincronizado por trigger en las dos
  direcciones. Existe porque una restricción de exclusión no puede abarcar dos
  tablas: sin ese espejo, la regla quedaría fuera del DDL.
- Los triggers de restricción son `DEFERRABLE INITIALLY DEFERRED`, porque la
  carga real inserta grafos completos y necesita cerrarlos antes de validarlos.
