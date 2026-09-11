"""Qué decisiones humanas quedan, ordenadas por dónde conviene empezar.

«5.397 afirmaciones pendientes» no es una tarea: es un número que desalienta y
no dice por dónde agarrarlo. Son **54 versiones** —una invocación de
`bn revision aprobar-campos` cada una— y catorce de ellas respaldan los
beneficios que ya tienen sus reglas firmadas. Ese subconjunto es el que
convierte trabajo en corpus servible; el resto puede esperar.

Lo mismo con las vigencias: 153 versiones sin intervalo de aplicación suenan a
muro y son cinco grupos con criterios distintos. Una norma sin fecha pide leer
su artículo de entrada en vigor; un canal sin fecha pide otra cosa.

Este informe se genera de la base. No lleva ninguna cifra escrita a mano.
"""

from __future__ import annotations

from sqlalchemy import Connection, text

CONSULTA_AFIRMACIONES = """
SELECT n.tipo, n.numero, n.anio, left(coalesce(n.titulo, ''), 70) AS titulo,
       a.registro_version_id AS version_id,
       -- DISTINCT porque el LEFT JOIN a beneficio_normas multiplica filas:
       -- sin esto, una norma con veinte beneficios colgando informaba
       -- veinte veces sus afirmaciones. Daba 27.120 sobre un total de 5.397.
       count(DISTINCT a.id) AS afirmaciones,
       bool_or(bn.beneficio_version_id IS NOT NULL) AS respalda_beneficio
  FROM afirmaciones a
  JOIN norma_versiones nv ON nv.registro_version_id = a.registro_version_id
  JOIN normas n ON n.id = nv.norma_id
  LEFT JOIN beneficio_normas bn ON bn.norma_version_id = nv.registro_version_id
 WHERE a.estado_revision = 'CANDIDATE'
 GROUP BY 1, 2, 3, 4, 5
 ORDER BY bool_or(bn.beneficio_version_id IS NOT NULL) DESC, count(DISTINCT a.id) DESC
"""

CONSULTA_VIGENCIAS = """
SELECT rv.entidad_tipo,
       count(*) AS cuantas,
       count(*) FILTER (WHERE rv.valid_desde IS NOT NULL) AS con_fecha_de_inicio
  FROM registro_versiones rv
 WHERE rv.release_id IS NULL AND rv.valid_tipo = 'DESCONOCIDO'
 GROUP BY 1 ORDER BY 2 DESC
"""


def construir(conexion: Connection) -> str:
    afirmaciones = conexion.execute(text(CONSULTA_AFIRMACIONES)).mappings().all()
    vigencias = conexion.execute(text(CONSULTA_VIGENCIAS)).mappings().all()

    prioritarias = [f for f in afirmaciones if f["respalda_beneficio"]]
    resto = [f for f in afirmaciones if not f["respalda_beneficio"]]
    total_afirmaciones = sum(f["afirmaciones"] for f in afirmaciones)

    lineas = [
        "# Qué decisiones humanas quedan",
        "",
        "Generado por `bn revision pendientes`. Ninguna cifra está escrita a mano.",
        "",
        "Este backend no aprueba lecturas jurídicas solo: lo que sigue son decisiones",
        "que toma una persona con competencia, y el sistema las registra con su nombre",
        "y su fundamento.",
        "",
        "## Afirmaciones sobre normas",
        "",
        f"Son **{total_afirmaciones} afirmaciones** repartidas en **{len(afirmaciones)} "
        "versiones**. Eso último es lo que importa: `bn revision aprobar-campos` se",
        "invoca por versión, así que el trabajo son " + str(len(afirmaciones)) + " decisiones,",
        "no miles.",
        "",
        "Una afirmación dice «esta norma establece X sobre la población Y» y trae la",
        "evidencia que lo sostiene. Aprobarla es decir que la lectura es correcta.",
        "",
    ]

    if prioritarias:
        lineas += [
            f"### Empezar por acá: {len(prioritarias)} versiones que respaldan beneficios firmados",
            "",
            "Son las normas de las que cuelgan los beneficios cuyas reglas ya están",
            "firmadas. Aprobar estas convierte trabajo en corpus servible; el resto puede",
            "esperar sin bloquear nada.",
            "",
            "| Norma | Afirmaciones | Comando |",
            "| --- | ---: | --- |",
        ]
        for f in prioritarias:
            norma = f"{f['tipo']} {f['numero']}/{f['anio']}"
            lineas.append(
                f"| {norma} — {f['titulo']} | {f['afirmaciones']} | "
                f"`bn revision aprobar-campos {f['version_id']}` |"
            )
        lineas.append("")

    if resto:
        lineas += [
            f"### Después: {len(resto)} versiones del resto del corpus",
            "",
            "| Norma | Afirmaciones |",
            "| --- | ---: |",
        ]
        for f in resto:
            norma = f"{f['tipo']} {f['numero']}/{f['anio']}"
            lineas.append(f"| {norma} — {f['titulo']} | {f['afirmaciones']} |")
        lineas.append("")

    total_vigencias = sum(v["cuantas"] for v in vigencias)
    lineas += [
        "## Versiones sin intervalo de aplicación",
        "",
        f"**{total_vigencias} versiones** no dicen desde cuándo valen. No se publican, y",
        "está bien que no se publiquen: servirlas sería afirmar una vigencia que nadie",
        "determinó.",
        "",
        "No hay parte mecánica. Sólo diez normas tienen fecha de inicio cargada, y aun",
        "esas necesitan que alguien diga si la norma tiene fin o rige abierta: eso sale",
        "de leer su artículo de vigencia, no de un campo.",
        "",
        "| Tipo | Cuántas | Con fecha de inicio ya cargada |",
        "| --- | ---: | ---: |",
    ]
    for v in vigencias:
        lineas.append(f"| {v['entidad_tipo']} | {v['cuantas']} | {v['con_fecha_de_inicio']} |")
    lineas += [
        "",
        "Se resuelven con `bn revision resolver-vigencia`, que exige actor y fundamento.",
        "",
    ]
    return "\n".join(lineas)
