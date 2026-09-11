"""P-019 criterio 2: readiness y liveness, separadas y con motivo.

Lo que estas pruebas cuidan es la separación. Si readiness y liveness fueran la
misma sonda, una base momentáneamente inalcanzable reiniciaría procesos sanos y
convertiría una caída parcial en una total. Y si readiness dijera sólo «no»,
habría que entrar al contenedor para saber por qué.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from backend_normativo.api import sondas

pytestmark = pytest.mark.integracion


def test_liveness_no_toca_la_base(cliente_api) -> None:
    """Esa es toda su gracia: contesta aunque la base no esté."""
    respuesta = cliente_api.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_readiness_pasa_con_la_base_al_dia(conexion: Connection) -> None:
    estado = sondas.verificar(conexion, entorno="local")
    assert estado.listo, estado.a_dict()
    assert {v.nombre for v in estado.verificaciones} == {"conexion", "esquema"}


def test_produccion_exige_un_corte_publicado(conexion: Connection) -> None:
    """Sin release, la API contesta abstenciones correctas y vacías.

    Eso está bien en desarrollo y no está bien en una instancia recibiendo gente
    que pregunta por sus derechos, así que en producción no se declara lista.
    """
    conexion.execute(text("UPDATE releases SET estado = 'BORRADOR'"))
    estado = sondas.verificar(conexion, entorno=sondas.ENTORNO_PRODUCCION)
    corte = next(v for v in estado.verificaciones if v.nombre == "corte")
    assert not corte.pasa
    assert not estado.listo


def test_en_local_no_se_exige_corte(conexion: Connection) -> None:
    """La misma base sin corte sí sirve para desarrollar."""
    conexion.execute(text("UPDATE releases SET estado = 'BORRADOR'"))
    estado = sondas.verificar(conexion, entorno="local")
    assert {v.nombre for v in estado.verificaciones} == {"conexion", "esquema"}


def test_una_base_inalcanzable_no_es_un_500(conexion: Connection) -> None:
    """Readiness tiene que decir 503 y por qué, no romperse.

    Cuando la conexión se abría como dependencia del framework, una base caída
    hacía fallar la dependencia antes de la sonda: el servicio devolvía 500 y no
    alcanzaba a decir nada. Un orquestador lee 503 como «no le mandes tráfico».
    """

    def no_abre():
        raise OSError("la base no está")

    estado = sondas.verificar_abriendo(no_abre, entorno="local")
    assert not estado.listo
    conexion_fallida = next(v for v in estado.verificaciones if v.nombre == "conexion")
    assert not conexion_fallida.pasa
    assert "no se pudo abrir" in conexion_fallida.detalle.lower()


def test_no_poder_leer_la_migracion_no_es_no_tener_migracion(conexion: Connection) -> None:
    """Dos diagnósticos opuestos con el mismo síntoma.

    La primera versión atrapaba cualquier error y reportaba «la base está en
    ninguna migración» cuando lo que pasaba era que el rol de lectura no alcanza
    `alembic_version`: mandaba a revisar la base cuando era un permiso.
    """

    class ConexionSinPermiso:
        def execute(self, clausula, *args, **kwargs):
            texto = str(clausula)
            if "alembic_version" in texto:
                raise PermissionError("permission denied for table alembic_version")
            return conexion.execute(clausula, *args, **kwargs)

    estado = sondas.verificar(ConexionSinPermiso(), entorno="local")
    esquema = next(v for v in estado.verificaciones if v.nombre == "esquema")
    assert not esquema.pasa
    assert "permiso" in esquema.detalle.lower()
    assert "ninguna migración" not in esquema.detalle


def test_la_cabeza_esperada_sale_de_las_migraciones_y_no_de_una_constante() -> None:
    """Una constante escrita a mano envejece en silencio; ya pasó en este proyecto."""
    cabeza = sondas.cabeza_esperada()
    assert cabeza and cabeza.startswith("00")
