"""Poner la fecha de verificación donde se puede sostener: la captura oficial.

La base exige desde la primera migración que nada llegue a `PUBLISHED` sin
`verificado_en`, y ninguna de las 14.400 versiones de dato operativo aprobadas
la tenía. Ese es el motivo real por el que la pantalla dice «no tengo cargado a
quién derivarte» teniendo 1.842 lugares de atención cargados: no es que falten,
es que la base se niega —con razón— a servir algo cuyo respaldo nadie fechó.

**Qué se decidió que significa verificar acá.** Que en una fecha concreta la
fuente oficial publicaba ese dato. Nada más. Hay una captura inmutable, con su
`sha256`, de la página del organismo, y `verificado_en` es la fecha de esa
captura. Lo que **no** significa: que la oficina esté abierta, que el teléfono
atienda, o que el organismo tuviera razón. Esa distinción no puede quedarse en
este archivo: la pantalla dice «lo tomé de la página oficial el …» y no «lo
verifiqué», porque son cosas distintas y la segunda sería mentira.

**La fecha sale de la captura y nunca de `now()`.** Sellar con la hora de la
corrida convertiría un dato de hace dos años en uno de hoy con una sola
ejecución, y sería exactamente la clase de fallo que no falla: todo verde,
todo servido, todo viejo.

**Lo que no llega a una captura no se sella.** Se cuenta y se informa. Una
versión sin cadena hasta un snapshot no tiene con qué fecharse, y ponerle una
sería inventarla.

**El horizonte de refrescado también sale de la captura.** `reverificar_antes_de`
es la captura más treinta días, no hoy más treinta: así una captura vieja nace
vencida, que es lo que es, en vez de estrenarse fresca.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

# El mismo horizonte que usa el resto de la curación para el dato operativo.
DIAS_DE_FRESCURA = 30

ACCION = "FECHAR_VERIFICACION"

# Cómo llega cada familia a la captura que la respalda. Son cuatro caminos
# distintos y ninguno se puede sustituir por otro: el punto de atención no
# tiene evidencia propia y llega por sus canales, que son los que se
# transcribieron del directorio.
#
# Para el punto se toma la captura **más vieja** de sus canales. Entre reclamar
# la más fresca y reclamar la más vieja, la segunda es la que no exagera.
CADENAS = {
    "canal": """
        SELECT ca.registro_version_id AS version_id, cap.capturado_en
          FROM canales ca
          JOIN evidencias e ON e.id = ca.evidencia_id
          JOIN documento_versiones dv ON dv.id = e.doc_version_id
          JOIN capturas cap ON cap.id = dv.captura_id
    """,
    "barrio_renabap": """
        SELECT b.registro_version_id AS version_id, cap.capturado_en
          FROM barrios_renabap b
          JOIN evidencias e ON e.id = b.evidencia_id
          JOIN documento_versiones dv ON dv.id = e.doc_version_id
          JOIN capturas cap ON cap.id = dv.captura_id
    """,
    "parametro_valor": """
        SELECT pv.registro_version_id AS version_id, cap.capturado_en
          FROM parametro_valores pv
          JOIN evidencias e ON e.id = pv.evidencia_id
          JOIN documento_versiones dv ON dv.id = e.doc_version_id
          JOIN capturas cap ON cap.id = dv.captura_id
    """,
    "punto_atencion": """
        SELECT pav.registro_version_id AS version_id, min(cap.capturado_en) AS capturado_en
          FROM punto_versiones pav
          JOIN canales ca ON ca.punto_id = pav.punto_id
          JOIN evidencias e ON e.id = ca.evidencia_id
          JOIN documento_versiones dv ON dv.id = e.doc_version_id
          JOIN capturas cap ON cap.id = dv.captura_id
         GROUP BY pav.registro_version_id
    """,
}


@dataclass
class Resultado:
    """Qué se selló, qué no, y por qué no."""

    sellados: dict[str, int] = field(default_factory=dict)
    sin_captura: dict[str, int] = field(default_factory=dict)
    simulado: bool = False

    @property
    def total(self) -> int:
        return sum(self.sellados.values())

    @property
    def total_sin_captura(self) -> int:
        return sum(self.sin_captura.values())


def _pendientes_sin_captura(conexion: Connection, tipo: str, cadena: str) -> int:
    """Versiones sin fecha que tampoco llegan a una captura. No se sellan."""
    return conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones rv "
            " WHERE rv.entidad_tipo = :t AND rv.verificado_en IS NULL "
            f"  AND NOT EXISTS (SELECT 1 FROM ({cadena}) c WHERE c.version_id = rv.id)"
        ),
        {"t": tipo},
    ).scalar_one()


def fechar_desde_la_captura(
    conexion: Connection,
    *,
    actor: str,
    tipos: list[str] | None = None,
    simular: bool = False,
) -> Resultado:
    """Sella `verificado_en` con la fecha de la captura que respalda cada dato."""
    elegidos = [t for t in CADENAS if tipos is None or t in tipos]
    resultado = Resultado(simulado=simular)

    for tipo in elegidos:
        cadena = CADENAS[tipo]
        resultado.sin_captura[tipo] = _pendientes_sin_captura(conexion, tipo, cadena)

        if simular:
            resultado.sellados[tipo] = conexion.execute(
                text(
                    f"SELECT count(*) FROM ({cadena}) c "
                    "  JOIN registro_versiones rv ON rv.id = c.version_id "
                    " WHERE rv.entidad_tipo = :t AND rv.verificado_en IS NULL"
                ),
                {"t": tipo},
            ).scalar_one()
            continue

        filas = conexion.execute(
            text(
                f"UPDATE registro_versiones rv SET verificado_en = c.capturado_en, "
                "       reverificar_antes_de = c.capturado_en + :ventana "
                f"  FROM ({cadena}) c "
                " WHERE rv.id = c.version_id AND rv.entidad_tipo = :t "
                "   AND rv.verificado_en IS NULL "
                "RETURNING rv.id"
            ),
            {"t": tipo, "ventana": dt.timedelta(days=DIAS_DE_FRESCURA)},
        ).all()
        resultado.sellados[tipo] = len(filas)

        # Rastro por versión, igual que la aprobación en bloque: lo que se sella
        # de a miles tiene que poder auditarse de a una.
        for (version_id,) in filas:
            conexion.execute(
                text(
                    "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
                    "VALUES (:a, :ac, 'registro_version', :o, :m)"
                ),
                {
                    "a": actor,
                    "ac": ACCION,
                    "o": version_id,
                    "m": (
                        "Fecha tomada de la captura oficial que respalda el dato. Significa "
                        "que en esa fecha la fuente publicaba esto; no que el lugar esté "
                        "abierto ni que el teléfono atienda."
                    ),
                },
            )

    return resultado
