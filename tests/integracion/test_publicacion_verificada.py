"""Nada se sirve sin fecha de verificación, y el estado tiene que decirlo.

La base lo exige desde la primera migración: `estado_revision <> 'PUBLISHED' OR
(release_id IS NOT NULL AND verificado_en IS NOT NULL)`. Es una invariante
buena —una dirección o un teléfono que nadie confirmó contra la fuente no
debería llegar a la pantalla de alguien que los va a usar— y el publicador no
la conocía.

El resultado era el peor de los dos mundos. `bn publicacion estado` contaba
14.390 candidatos con los ocho gates en verde, y publicar reventaba con una
violación de CHECK a mitad de la transacción. Nadie podía saber, leyendo el
estado, que el corpus entero estaba a un paso de no poder publicarse: el
informe decía que sí y la base decía que no.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from tests.conftest import construir_corpus, publicar_corpus

pytestmark = pytest.mark.integracion

MOTIVO = "sin fecha de verificación"


def _punto_aprobado(conexion: Connection, *, verificado: bool) -> str:
    from backend_normativo.catalogo.carga import cargar_catalogo

    if not conexion.execute(text("SELECT count(*) FROM jurisdicciones")).scalar_one():
        cargar_catalogo(conexion)
    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', :n, 'PRESTADOR') RETURNING id"
        ),
        {"n": f"Organismo {'verificado' if verificado else 'sin verificar'}"},
    ).scalar_one()
    punto = conexion.execute(
        text(
            "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, alcance) "
            "VALUES (:o, 'AR-C', :n, 'SEDE', 'PROVINCIAL') RETURNING id"
        ),
        {"o": organismo, "n": f"Sede {'verificada' if verificado else 'sin verificar'}"},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            "  estado_revision, valid_tipo, valid_desde, verificado_en) "
            "VALUES ('punto_atencion', :p, 1, 'APPROVED', 'ABIERTO_FIN', DATE '2025-01-01', "
            "        CASE WHEN :v THEN now() ELSE NULL END) RETURNING id"
        ),
        {"p": punto, "v": verificado},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_legible) "
            "VALUES (:v, :p, 'Av. Siempreviva 742')"
        ),
        {"v": version, "p": punto},
    )
    return str(version)


def test_una_version_sin_verificar_no_es_candidata(conexion: Connection) -> None:
    from backend_normativo.publicacion.release import Publicador

    sin_verificar = _punto_aprobado(conexion, verificado=False)
    con_verificacion = _punto_aprobado(conexion, verificado=True)

    publicador = Publicador(conexion)
    candidatos = {str(c) for c in publicador.candidatos()}
    assert con_verificacion in candidatos
    assert sin_verificar not in candidatos, (
        "una versión que la base va a rechazar no puede figurar como publicable"
    )


def test_el_estado_dice_por_que_no_se_puede_publicar(conexion: Connection) -> None:
    """«No aparece» y «no existe» tienen que poder distinguirse."""
    from backend_normativo.publicacion.release import Publicador

    sin_verificar = _punto_aprobado(conexion, verificado=False)
    cuarentena = {c["registro_version_id"]: c for c in Publicador(conexion).cuarentena()}
    assert sin_verificar in cuarentena, "lo que no se puede publicar tiene que estar en la lista"
    assert any(MOTIVO in m for m in cuarentena[sin_verificar]["motivos"])


def test_publicar_no_intenta_lo_que_la_base_va_a_rechazar(conexion: Connection) -> None:
    """Antes esto terminaba en una violación de CHECK a mitad de transacción."""
    from backend_normativo.publicacion.release import NadaQuePublicar, Publicador

    publicar_corpus(conexion, construir_corpus(conexion))
    _punto_aprobado(conexion, verificado=False)

    with pytest.raises(NadaQuePublicar):
        Publicador(conexion).publicar(actor="publicador:equipo", motivo="Puntos de atención.")


def test_lo_verificado_sigue_publicandose(conexion: Connection) -> None:
    """El arreglo no puede dejar de publicar lo que sí está en condiciones."""
    from backend_normativo.publicacion.release import Publicador

    publicar_corpus(conexion, construir_corpus(conexion))
    version = _punto_aprobado(conexion, verificado=True)
    resultado = Publicador(conexion).publicar(actor="publicador:equipo", motivo="Punto verificado.")
    assert resultado.versiones_publicadas == 1
    estado = conexion.execute(
        text("SELECT estado_revision FROM registro_versiones WHERE id = :v"), {"v": version}
    ).scalar_one()
    assert estado == "PUBLISHED"
