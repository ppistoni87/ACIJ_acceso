"""El estado mínimo de una conversación: qué recuerda, qué no, y hasta cuándo.

P-025 pide que la persona pueda corregir lo dicho sin repetir todo, y que una
corrección invalide lo que dependía del dato viejo. P-037 pone los plazos: 30
minutos de inactividad, dos horas de vida. Y el proyecto entero pone el límite
que atraviesa las dos: acá no se guarda ningún mensaje.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import Connection, text

from backend_normativo.conversacion import sesion as ses

pytestmark = pytest.mark.integracion


def test_una_sesion_nace_vacia_y_con_vencimiento(conexion: Connection) -> None:
    s = ses.abrir(conexion)
    assert s.hechos == {}
    assert s.version == 0
    assert s.vence_en() <= s.creada_en + ses.VIDA_MAXIMA


def test_confirmar_un_hecho_guarda_su_procedencia(conexion: Connection) -> None:
    """Lo que la persona dijo y lo que el sistema dedujo no se mezclan."""
    s = ses.abrir(conexion)
    s = ses.confirmar(conexion, s.id, clave="ingreso_mensual_del_hogar", valor=100000)
    hecho = s.hechos["ingreso_mensual_del_hogar"]
    assert hecho["valor"] == 100000
    assert hecho["origen"] == "declarado"
    assert hecho["en"]


def test_la_correccion_reemplaza_y_sube_la_version(conexion: Connection) -> None:
    """Es lo que permite marcar como reemplazada la respuesta anterior."""
    s = ses.abrir(conexion)
    s = ses.confirmar(conexion, s.id, clave="jurisdiccion_declarada", valor="AR-B")
    primera = s.version
    s = ses.confirmar(conexion, s.id, clave="jurisdiccion_declarada", valor="AR-C")
    assert s.hechos["jurisdiccion_declarada"]["valor"] == "AR-C"
    assert s.version > primera, "sin versión nueva nadie sabe qué respuestas quedaron viejas"


def test_no_responder_no_es_responder_que_no(conexion: Connection) -> None:
    """Un dato desconocido nunca se transforma en falso (P-025, criterio 2)."""
    s = ses.abrir(conexion)
    s = ses.confirmar(conexion, s.id, clave="tiene_hijos", rehusado=True)
    hecho = s.hechos["tiene_hijos"]
    assert hecho["rehusado"] is True
    assert "valor" not in hecho

    with pytest.raises(ses.SesionInvalida):
        ses.confirmar(conexion, s.id, clave="tiene_hijos", valor=False, rehusado=True)


def test_olvidar_un_hecho_lo_devuelve_a_desconocido(conexion: Connection) -> None:
    s = ses.abrir(conexion)
    s = ses.confirmar(conexion, s.id, clave="edad", valor=40)
    s = ses.olvidar(conexion, s.id, clave="edad")
    assert "edad" not in s.hechos, "quitar un hecho tiene que dejarlo desconocido, no en falso"


def test_el_estado_no_puede_guardar_la_conversacion(conexion: Connection) -> None:
    """El límite que atraviesa todo: acá no entra el texto de nadie."""
    s = ses.abrir(conexion)
    with pytest.raises(ses.SesionInvalida, match="historial"):
        ses._guardar(
            conexion,
            s.id,
            {"version": 1, "mensajes": ["me quieren echar de mi casa"]},
            dt.datetime.now(dt.UTC),
        )


def test_la_base_tambien_lo_rechaza(conexion: Connection) -> None:
    """Y no sólo el módulo: si alguien escribe por SQL, la restricción lo frena."""
    s = ses.abrir(conexion)
    with pytest.raises(Exception, match=r"(?i)ck_sesiones_solo_estado_estructurado|check"):
        conexion.execute(
            text(
                "UPDATE sesiones_conversacion "
                '   SET estado = \'{"historial": ["lo que escribió"]}\'::jsonb '
                " WHERE id = :id"
            ),
            {"id": s.id},
        )
    conexion.execute(text("ROLLBACK"))


def test_vence_por_inactividad(conexion: Connection) -> None:
    s = ses.abrir(conexion)
    despues = s.ultima_actividad_en + ses.INACTIVIDAD + dt.timedelta(seconds=1)
    assert ses.leer(conexion, s.id, ahora=despues) is None


def test_vence_por_las_dos_horas_aunque_se_la_use(conexion: Connection) -> None:
    """El techo no se corre tocándola: es el máximo de vida, no de inactividad."""
    s = ses.abrir(conexion)
    # Se la usa cada 20 minutos, siempre dentro de la ventana de inactividad,
    # así que por ese lado nunca vencería. El techo igual la corta.
    momento = s.creada_en
    viva_hasta = None
    for _ in range(8):
        momento += dt.timedelta(minutes=20)
        if ses.tocar(conexion, s.id, ahora=momento) is None:
            break
        viva_hasta = momento
    assert viva_hasta is not None
    assert viva_hasta < s.creada_en + ses.VIDA_MAXIMA, "siguió viva más allá del techo de dos horas"
    assert momento >= s.creada_en + ses.VIDA_MAXIMA


def test_leer_una_vencida_la_borra(conexion: Connection) -> None:
    """No se resucita ni se deja «un ratito más»: un plazo no es una sugerencia."""
    s = ses.abrir(conexion)
    despues = s.creada_en + ses.VIDA_MAXIMA + dt.timedelta(seconds=1)
    ses.leer(conexion, s.id, ahora=despues)
    quedan = conexion.execute(
        text("SELECT count(*) FROM sesiones_conversacion WHERE id = :id"), {"id": s.id}
    ).scalar_one()
    assert quedan == 0


def test_purgar_borra_las_que_nadie_vuelve_a_mirar(conexion: Connection) -> None:
    """Que `leer` borre no alcanza: una sesión abandonada no se lee nunca más."""
    s = ses.abrir(conexion)
    ses.confirmar(conexion, s.id, clave="ingreso_mensual_del_hogar", valor=1)
    conexion.execute(
        text(
            "UPDATE sesiones_conversacion "
            "   SET creada_en = now() - interval '3 hours', "
            "       ultima_actividad_en = now() - interval '3 hours' WHERE id = :id"
        ),
        {"id": s.id},
    )
    assert ses.purgar(conexion) >= 1
    assert conexion.execute(text("SELECT count(*) FROM sesiones_conversacion")).scalar_one() == 0


def test_dos_sesiones_no_se_mezclan(conexion: Connection) -> None:
    """P-025, criterio 3: dos conversaciones simultáneas no comparten hechos."""
    una = ses.abrir(conexion)
    otra = ses.abrir(conexion)
    ses.confirmar(conexion, una.id, clave="ingreso_mensual_del_hogar", valor=100000)
    ses.confirmar(conexion, otra.id, clave="ingreso_mensual_del_hogar", valor=999)
    assert ses.leer(conexion, una.id).hechos["ingreso_mensual_del_hogar"]["valor"] == 100000
    assert ses.leer(conexion, otra.id).hechos["ingreso_mensual_del_hogar"]["valor"] == 999


def test_borrar_es_borrar(conexion: Connection) -> None:
    s = ses.abrir(conexion)
    ses.confirmar(conexion, s.id, clave="edad", valor=40)
    assert ses.borrar(conexion, s.id) is True
    assert ses.leer(conexion, s.id) is None


def test_una_sesion_que_no_existe_no_rompe_nada(conexion: Connection) -> None:
    inventada = uuid.uuid4()
    assert ses.leer(conexion, inventada) is None
    assert ses.tocar(conexion, inventada) is None
    assert ses.confirmar(conexion, inventada, clave="edad", valor=1) is None
    assert ses.borrar(conexion, inventada) is False


def test_un_origen_inventado_no_se_acepta(conexion: Connection) -> None:
    """Lo inferido no se puede mostrar como dicho por la persona."""
    s = ses.abrir(conexion)
    with pytest.raises(ses.SesionInvalida, match="origen"):
        ses.confirmar(conexion, s.id, clave="edad", valor=40, origen="adivinado")


# --- Las rutas ----------------------------------------------------------------


def test_el_recorrido_completo_por_la_api(cliente_api) -> None:
    """Abrir, contar algo, corregirlo y borrar todo, sin identificarse."""
    abierta = cliente_api.post("/v1/sesiones")
    assert abierta.status_code == 201, abierta.text
    sesion_id = abierta.json()["sesion_id"]
    assert abierta.json()["hechos"] == {}
    assert abierta.json()["vence_en"]

    contexto = cliente_api.patch(
        f"/v1/sesiones/{sesion_id}/contexto", json={"jurisdiccion": "AR-C"}
    )
    assert contexto.json()["jurisdiccion"] == "AR-C"

    primero = cliente_api.put(
        f"/v1/sesiones/{sesion_id}/hechos",
        json={"clave": "ingreso_mensual_del_hogar", "valor": 100000},
    ).json()
    corregido = cliente_api.put(
        f"/v1/sesiones/{sesion_id}/hechos",
        json={"clave": "ingreso_mensual_del_hogar", "valor": 250000},
    ).json()
    assert corregido["hechos"]["ingreso_mensual_del_hogar"]["valor"] == 250000
    assert corregido["version"] > primero["version"]

    olvidado = cliente_api.delete(
        f"/v1/sesiones/{sesion_id}/hechos/ingreso_mensual_del_hogar"
    ).json()
    assert "ingreso_mensual_del_hogar" not in olvidado["hechos"]

    assert cliente_api.delete(f"/v1/sesiones/{sesion_id}").status_code == 204
    assert cliente_api.get(f"/v1/sesiones/{sesion_id}").status_code == 404


def test_la_ruta_no_acepta_el_texto_de_la_conversacion(cliente_api) -> None:
    """Es la prueba de la decisión: acá no entra lo que la persona escribió."""
    sesion_id = cliente_api.post("/v1/sesiones").json()["sesion_id"]
    respuesta = cliente_api.patch(
        f"/v1/sesiones/{sesion_id}/contexto",
        json={"jurisdiccion": "AR-C", "mensaje": "me quieren echar de mi casa"},
    )
    assert respuesta.status_code == 422


def test_una_sesion_que_no_existe_contesta_404_y_no_500(cliente_api) -> None:
    import uuid as _uuid

    assert cliente_api.get(f"/v1/sesiones/{_uuid.uuid4()}").status_code == 404


def test_no_hay_forma_de_listar_las_sesiones_de_otros(cliente_api) -> None:
    """El identificador es lo único que da acceso, y no hay índice que recorrer."""
    from backend_normativo.api.app import crear_app

    caminos = crear_app().openapi()["paths"]
    assert "get" not in caminos["/v1/sesiones"], (
        "un listado de sesiones deja recorrer las conversaciones de cualquiera"
    )
