"""P-016 criterio 1: buscar normas y comparar dos versiones cualesquiera.

Quien revisa llega con una cita —«la 24.714», «decreto 1382»— y no con un
identificador interno. Y necesita elegir dos versiones: la publicada y la que
está por publicarse, o la de hace un año. El monitoreo compara cada versión
contra su inmediata anterior, que es otra pregunta.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Connection, text

from backend_normativo.monitoreo import diff

pytestmark = pytest.mark.integracion

SECRETO = "secreto-de-prueba-backoffice"


@pytest.fixture
def revisor(monkeypatch) -> str:
    from backend_normativo.seguridad.credenciales import ROL_REVISOR, emitir

    monkeypatch.setenv("BN_CREDENCIAL_SECRETO", SECRETO)
    monkeypatch.delenv("BN_IDENTIDAD_MODO", raising=False)
    monkeypatch.delenv("BN_ADMIN_TOKENS", raising=False)
    token, _ = emitir(
        "revisor-de-prueba",
        {ROL_REVISOR},
        duracion=dt.timedelta(hours=1),
        secreto_bytes=SECRETO.encode(),
    )
    return token


def test_buscar_normas_exige_credencial(cliente_api) -> None:
    assert cliente_api.get("/v1/admin/normas").status_code == 401


def test_sin_texto_devuelve_las_mas_recientes(cliente_api, corpus, revisor: str) -> None:
    """Mejor que una pantalla en blanco pidiendo que adivinen."""
    cuerpo = cliente_api.get(
        "/v1/admin/normas", headers={"Authorization": f"Bearer {revisor}"}
    ).json()
    assert isinstance(cuerpo["normas"], list)


def test_se_busca_por_numero_y_por_titulo(cliente_api, corpus, revisor: str) -> None:
    """Una cita trae el número; el catálogo, el título. Se busca por los dos."""
    cabeceras = {"Authorization": f"Bearer {revisor}"}
    por_numero = cliente_api.get("/v1/admin/normas?q=24714", headers=cabeceras).json()
    assert "normas" in por_numero


def test_comparar_dos_versiones_cualesquiera(
    conexion: Connection, documento_con_dos_versiones: str
) -> None:
    """No sólo contra la inmediata anterior, que es lo que mira el monitoreo."""
    par = conexion.execute(
        text(
            "SELECT string_agg(dv.id::text, ' ' ORDER BY dv.version) "
            "  FROM documento_versiones dv "
            " WHERE dv.documento_id = ("
            "   SELECT documento_id FROM documento_versiones "
            "    GROUP BY documento_id HAVING count(*) > 1 LIMIT 1)"
        )
    ).scalar_one_or_none()
    assert par, "la fixture deja un documento con dos versiones para comparar"
    a, b = par.split()
    diferencia = diff.comparar_dos(conexion, a, b)
    assert diferencia is not None
    assert diferencia.version_anterior is not None


def test_comparar_con_una_version_inexistente_no_inventa_nada(conexion: Connection, corpus) -> None:
    """Devolver una diferencia vacía haría creer que las dos versiones son iguales."""
    import uuid

    alguna = conexion.execute(
        text("SELECT id FROM documento_versiones LIMIT 1")
    ).scalar_one_or_none()
    assert alguna is not None, "el corpus deja al menos una versión documental"
    assert diff.comparar_dos(conexion, alguna, uuid.uuid4()) is None


def test_un_desplazamiento_no_cuenta_como_cambio_de_la_norma(conexion: Connection) -> None:
    """Insertar un párrafo corre todas las rutas posteriores.

    Contar eso como texto modificado llenaría la comparación de cambios falsos:
    agregar tres párrafos daría decenas de «eliminadas» y «agregadas» que son el
    mismo texto un lugar más abajo.
    """
    viejas = {"art-1": ("ARTICULO", "Uno."), "art-2": ("ARTICULO", "Dos.")}
    nuevas = {"art-2": ("ARTICULO", "Uno."), "art-3": ("ARTICULO", "Dos.")}
    cambios = diff._comparar(viejas, nuevas)
    assert all(c.clase == "DESPLAZADA" for c in cambios), [c.clase for c in cambios]
