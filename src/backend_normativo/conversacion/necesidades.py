"""Orientar desde la situación, no desde el nombre del programa (P-030, criterio 1).

Alguien que se quedó sin casa no sabe que lo que busca se llama «Programa de
apoyo para personas en situación de vulnerabilidad habitacional». Sabe que no
tiene dónde vivir. Este módulo va de lo segundo a lo primero.

**La necesidad la elige la persona; no se infiere.** El criterio dice que no se
infiere información sensible, y adivinar a partir de lo que alguien escribió que
tiene una discapacidad, o que está embarazada, es exactamente eso. Las
necesidades se ofrecen como opciones y la persona toca una. Lo que el sistema
deduce a partir de esa elección es una sola cosa: qué programas mirar.

**Las necesidades salen del corte publicado, no de una lista escrita a mano.**
Ofrecer «vivienda» cuando no hay ninguna norma de vivienda publicada es prometer
algo que no se tiene. Lo único escrito a mano es cómo se dice cada familia en
castellano, y una familia que no esté acá viaja con su propio texto en vez de
inventarle un nombre.

**Nada de esto es exhaustivo y se dice siempre.** Lo que devuelve es lo que hay
en el corpus, que es una parte chica de lo que existe. Presentarlo como el
catálogo completo haría que alguien deje de buscar donde sí lo hay.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Connection, text

# Cómo se dice cada familia del corpus en las palabras de quien pregunta. El
# rótulo corto es para el botón; la línea de abajo es para reconocerse en ella.
# Una familia que no esté acá no se inventa: se muestra su propio texto y hay
# una prueba que avisa cuando el corpus trae una que nadie nombró.
NECESIDADES = {
    "HABITACIONAL": (
        "Dónde vivir",
        "Me quedé sin casa, estoy en la calle o no llego a pagar dónde vivo",
    ),
    "ALIMENTARIA": (
        "Comida",
        "Comedor, vianda o refrigerio",
    ),
    "EDUCACION": (
        "Estudiar",
        "Becas y ayuda para ir a la escuela o seguir estudiando",
    ),
    "SEGURIDAD_SOCIAL": (
        "Hijos, embarazo o discapacidad",
        "Asignaciones por tener hijos a cargo, estar embarazada o una discapacidad",
    ),
    "SALUD": (
        "Salud",
        "Atención, medicamentos o tratamientos",
    ),
    "TRABAJO": (
        "Trabajo",
        "Quedarme sin trabajo, buscar uno o capacitarme",
    ),
}


def nombrar(familia: str) -> tuple[str, str]:
    """El rótulo y la línea de una familia. Sin invento para las que no están."""
    if familia in NECESIDADES:
        return NECESIDADES[familia]
    legible = familia.replace("_", " ").capitalize()
    return legible, ""


@dataclass(frozen=True)
class Necesidad:
    familia: str
    rotulo: str
    detalle: str
    cuantos: int

    def a_dict(self) -> dict:
        return {
            "familia": self.familia,
            "rotulo": self.rotulo,
            "detalle": self.detalle,
            "cuantos": self.cuantos,
        }


@dataclass(frozen=True)
class Opcion:
    """Un programa del corte, con por qué está en la lista."""

    beneficio_id: str
    codigo: str
    nombre: str
    descripcion: str | None
    jurisdiccion: str | None
    norma: str | None
    condiciones: int
    coincide_jurisdiccion: bool | None

    def a_dict(self) -> dict:
        return {
            "beneficio_id": self.beneficio_id,
            # El código viaja para poder elegir el programa; no se muestra.
            "codigo": self.codigo,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "jurisdiccion": self.jurisdiccion,
            "norma": self.norma,
            "condiciones": self.condiciones,
            "coincide_jurisdiccion": self.coincide_jurisdiccion,
        }


NECESIDADES_DEL_CORTE = """
SELECT b.familia, count(*) AS cuantos
  FROM beneficio_versiones bv
  JOIN registro_versiones rv ON rv.id = bv.registro_version_id
  JOIN release_versiones m ON m.registro_version_id = rv.id AND m.release_id = :r
  JOIN beneficios b ON b.id = bv.beneficio_id
 WHERE rv.estado_revision = 'PUBLISHED'
   AND b.familia IS NOT NULL
 GROUP BY b.familia
 ORDER BY count(*) DESC, b.familia
"""

# Cada opción con lo que la hace pertinente: de qué norma sale, para qué
# jurisdicción rige y cuántas condiciones tiene para mirar. Nada de eso es una
# afirmación sobre la persona.
OPCIONES_DE_LA_NECESIDAD = """
SELECT b.id, b.codigo, b.nombre, bv.descripcion, bv.jurisdiccion_id,
       j.nombre AS jurisdiccion,
       (SELECT count(*) FROM reglas r
         WHERE r.beneficio_version_id = bv.registro_version_id) AS condiciones,
       (SELECT n.tipo || ' ' || coalesce(n.numero, '?') || '/' || coalesce(n.anio::text, '?')
          FROM beneficio_normas bn
          JOIN norma_versiones nv ON nv.registro_version_id = bn.norma_version_id
          JOIN normas n ON n.id = nv.norma_id
         WHERE bn.beneficio_version_id = bv.registro_version_id AND bn.rol = 'CREA'
         LIMIT 1) AS norma
  FROM beneficio_versiones bv
  JOIN registro_versiones rv ON rv.id = bv.registro_version_id
  JOIN release_versiones m ON m.registro_version_id = rv.id AND m.release_id = :r
  JOIN beneficios b ON b.id = bv.beneficio_id
  LEFT JOIN jurisdicciones j ON j.id = bv.jurisdiccion_id
 WHERE rv.estado_revision = 'PUBLISHED' AND b.familia = :f
 ORDER BY b.nombre
"""


def disponibles(conexion: Connection, release_id) -> list[Necesidad]:
    """Las necesidades que el corte publicado puede atender. Puede venir vacía."""
    if release_id is None:
        return []
    salida = []
    for fila in conexion.execute(text(NECESIDADES_DEL_CORTE), {"r": release_id}).mappings():
        rotulo, detalle = nombrar(fila["familia"])
        salida.append(
            Necesidad(
                familia=fila["familia"],
                rotulo=rotulo,
                detalle=detalle,
                cuantos=fila["cuantos"],
            )
        )
    return salida


def opciones(
    conexion: Connection, release_id, *, familia: str, jurisdiccion: str | None = None
) -> list[Opcion]:
    """Los programas del corte para esa necesidad.

    La jurisdicción **no filtra**: marca. Un programa nacional le sirve a alguien
    de cualquier provincia, y esconder los de otra jurisdicción por si acaso le
    saca a la persona la chance de ver que existe algo parecido donde vive. Se
    ordena poniendo primero lo que coincide y se dice cuál coincide y cuál no.
    """
    if release_id is None:
        return []
    filas = (
        conexion.execute(text(OPCIONES_DE_LA_NECESIDAD), {"r": release_id, "f": familia})
        .mappings()
        .all()
    )
    salida = [
        Opcion(
            beneficio_id=str(fila["id"]),
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            descripcion=fila["descripcion"],
            jurisdiccion=fila["jurisdiccion"],
            norma=fila["norma"],
            condiciones=fila["condiciones"],
            coincide_jurisdiccion=(
                None if jurisdiccion is None else fila["jurisdiccion_id"] == jurisdiccion
            ),
        )
        for fila in filas
    ]
    salida.sort(key=lambda o: (o.coincide_jurisdiccion is False, o.nombre))
    return salida
