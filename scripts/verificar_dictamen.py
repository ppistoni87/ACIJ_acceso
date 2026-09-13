#!/usr/bin/env python
"""Comprueba que un beneficio publicado llegue a los cuatro veredictos.

Corre contra el corpus real —el que tiene la base de trabajo, no el mínimo de
las pruebas— porque lo que se comprueba es que **estos datos** alcancen para
concluir. Una prueba con un corpus armado a medida diría que el motor funciona,
que ya se sabe; lo que estaba roto era el corpus.

No va como prueba de pytest por eso mismo: la suite corre sobre un corpus que no
tiene este beneficio, y una prueba salteada cuenta como éxito. Acá el resultado
es el código de salida.

    BN_DATABASE_URL=... python scripts/verificar_dictamen.py

Historia: durante toda la auditoría ninguno de los quince beneficios publicados
podía concluir. Contestando todos los campos a favor, trece daban
`REQUIERE_REVISION` y tres `REQUIERE_DATOS`. Tres arreglos lo destrabaron y
ninguno fue del motor: doce de catorce reglas de exclusión con la polaridad
invertida, diez reglas ya retiradas que se seguían evaluando, y las reglas
citando `AR.SMVM` mientras los valores vivían bajo `SMVM`.
"""

from __future__ import annotations

import datetime as dt
import sys

from sqlalchemy import text

# El corpus tiene el salario mínimo publicado desde el 1/10/2026 y no antes. Que
# falte el del mes corriente es un hueco de fuente declarado (H-08), no algo que
# este verificador deba tapar: por eso la fecha es explícita y está dicha.
FECHA = dt.date(2026, 10, 15)
CODIGO = "AR.CUIDADO-DE-SALUD-INTEGRAL"

LE_CORRESPONDE = {
    "edad_del_causante": 2,
    "causante_a_cargo_del_titular": True,
    "tuvo_derecho_a_la_auh_en_el_ano_calendario": True,
    "causante_acredita_vacunacion_y_control_sanitario": True,
    "titular_se_desempena_en_la_economia_informal": True,
    "ingreso_mensual_del_titular": 250_000,
}

SIN_LAS_VACUNAS = {
    k: v
    for k, v in LE_CORRESPONDE.items()
    if k != "causante_acredita_vacunacion_y_control_sanitario"
}

ESPERADO = [
    ("le corresponde", LE_CORRESPONDE, "POTENCIALMENTE_APLICABLE"),
    (
        "el chico ya tiene 5 años",
        {**LE_CORRESPONDE, "edad_del_causante": 5},
        "NO_CUMPLE_REGLA_EXPLICITA",
    ),
    (
        "informal por encima del salario mínimo",
        {**LE_CORRESPONDE, "ingreso_mensual_del_titular": 900_000},
        "NO_CUMPLE_REGLA_EXPLICITA",
    ),
    ("falta saber si tiene las vacunas al día", SIN_LAS_VACUNAS, "REQUIERE_DATOS"),
]


def main() -> int:
    from backend_normativo.api.routers.evaluaciones import (
        _reglas_publicadas,
        _resolver_parametro,
    )
    from backend_normativo.db.session import engine_migrador
    from backend_normativo.reglas.beneficio import evaluar_beneficio
    from backend_normativo.reglas.evaluacion import Evaluador, HechosDeclarados

    with engine_migrador().connect() as conexion:
        corte = conexion.execute(
            text(
                "SELECT id FROM releases WHERE estado = 'PUBLICADO' "
                " ORDER BY publicado_en DESC LIMIT 1"
            )
        ).scalar_one_or_none()
        if corte is None:
            print("No hay corte publicado: no hay nada servible que evaluar.", file=sys.stderr)
            return 1
        beneficio = conexion.execute(
            text("SELECT id FROM beneficios WHERE codigo = :c"), {"c": CODIGO}
        ).scalar_one_or_none()
        if beneficio is None:
            print(f"El corpus no tiene el beneficio {CODIGO}.", file=sys.stderr)
            return 1
        reglas = _reglas_publicadas(conexion, beneficio)
        evaluador = Evaluador(resolver_parametro=_resolver_parametro(conexion, corte))

        fallos = 0
        print(f"{CODIGO} · {len(reglas)} reglas publicadas · al {FECHA}")
        for nombre, hechos, esperado in ESPERADO:
            dictamen = evaluar_beneficio(
                reglas, HechosDeclarados(valores=hechos, fecha=FECHA), evaluador
            )
            obtenido = dictamen.resultado.value
            bien = obtenido == esperado
            fallos += not bien
            print(f"  {'ok ' if bien else 'MAL'} {nombre:42} {obtenido}")
            if not bien:
                print(f"      esperado {esperado}")
                if dictamen.no_ejecutables:
                    print(f"      reglas que bloquean: {len(dictamen.no_ejecutables)}")
                if dictamen.preguntas_faltantes:
                    print(f"      falta: {sorted(set(dictamen.preguntas_faltantes))}")
        if fallos:
            print(f"\n{fallos} veredicto(s) no dan lo esperado.", file=sys.stderr)
            return 1
        print("\nLos cuatro veredictos dan lo esperado sobre el corpus real.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
