# ADR 0001 · Stack y motor de base de datos

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

El repositorio estaba vacío: no había esquema, migraciones, pruebas ni
convenciones que reutilizar. La especificación pide una base SQL con tipos
temporales, claves foráneas, restricciones, transacciones y búsqueda textual, y
propone PostgreSQL como referencia. La ingesta trabaja con HTML, JSON, CSV/ZIP y
PDF; la API expone operaciones tipadas que consume un sistema conversacional.

## Decisión

- **PostgreSQL 16.** La versión soportada más nueva de la serie. Se usan tres
  capacidades que el diseño necesita y que no todos los motores tienen:
  restricciones de exclusión con `btree_gist` (para que "dos valores aprobados
  no rigen a la vez" sea una regla del DDL y no una comprobación de
  aplicación), `daterange` con inclusividad explícita, y `UNIQUE NULLS NOT
  DISTINCT`, que hace única la evaluación de un campo cuando no hay beneficio
  asociado.
- **Python 3.11** con **SQLAlchemy 2** y **Alembic**. Los modelos son la fuente
  del esquema y `alembic check` verifica en CI que no divergieron.
- **FastAPI** para la API tipada del contrato mínimo.
- **uv** para resolver e instalar dependencias.

## Consecuencias

- Las pruebas del esquema corren contra PostgreSQL real: las reglas que
  verificamos son triggers y restricciones, y un doble en memoria no las
  ejecutaría. `make pruebas-rapidas` deja fuera lo que necesita base o red.
- Los vocabularios controlados se implementan con `CHECK` y no con `ENUM` de
  PostgreSQL: ampliar un vocabulario queda como una migración revisable.
- Cambiar de motor exigiría reimplementar la exclusión temporal y las funciones
  de servibilidad. Es un costo asumido a cambio de que las reglas vivan en la
  base y no en cada consumidor.
