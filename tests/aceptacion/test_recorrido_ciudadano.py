"""P-015: el recorrido de una persona, en un navegador de verdad.

Esto no prueba la API: eso ya está probado. Prueba lo que una persona hace —
escribir, elegir, mandar, cancelar, volver a empezar, salir— contra un servidor
real en otro proceso, con Chromium.

Corre aparte porque levanta una base y un servidor: `-m "aceptacion and lento"`.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text

pytestmark = [pytest.mark.aceptacion, pytest.mark.lento]

BASE_E2E = os.environ.get("BN_TEST_DB_E2E", "backend_normativo_e2e")
URL_ADMIN = os.environ.get(
    "BN_TEST_ADMIN_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres"
)
ANCHO_MINIMO = 360  # el criterio 3 lo pide con ese número


def _url_e2e() -> str:
    return URL_ADMIN.rsplit("/", 1)[0] + "/" + BASE_E2E


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_e2e() -> str:
    """Base propia, migrada y con un corte publicado, confirmado.

    Confirmado y no en una transacción que se revierte: el servidor corre en
    otro proceso y no vería nada de lo que esta prueba dejara sin confirmar.
    """
    from tests.conftest import construir_corpus, publicar_corpus

    admin = create_engine(URL_ADMIN, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{BASE_E2E}" WITH (FORCE)'))
            c.execute(text(f'CREATE DATABASE "{BASE_E2E}"'))
    except Exception as exc:  # pragma: no cover - entorno sin PostgreSQL
        pytest.fail(f"PostgreSQL no disponible para el recorrido ciudadano: {exc}", pytrace=False)
    finally:
        admin.dispose()

    anterior = os.environ.get("BN_DATABASE_URL")
    os.environ["BN_DATABASE_URL"] = _url_e2e()
    from alembic import command
    from alembic.config import Config

    from backend_normativo.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")

    motor = create_engine(_url_e2e(), future=True)
    with motor.begin() as conexion:
        conexion.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        corpus = publicar_corpus(conexion, construir_corpus(conexion))
        _punto_de_atencion_publicado(conexion)
        _beneficio_con_reglas_publicado(conexion, corpus)
    motor.dispose()

    yield _url_e2e()

    if anterior is None:
        os.environ.pop("BN_DATABASE_URL", None)
    else:
        os.environ["BN_DATABASE_URL"] = anterior
    get_settings.cache_clear()


def _punto_de_atencion_publicado(conexion) -> None:
    """Un lugar de atención de verdad en el corte del recorrido.

    Sin esto, «A dónde ir» sólo se probaba vacío: los treinta y pico de casos
    corrían contra un corpus sin un solo punto publicado, que es justo la mitad
    que el frente muestra mal si se descuida. Va con fecha de verificación
    porque la base no publica nada sin ella.
    """
    from backend_normativo.publicacion.release import Publicador

    organismo = conexion.execute(
        text(
            "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
            "VALUES ('AR-C', 'Comuna de prueba', 'PRESTADOR') RETURNING id"
        )
    ).scalar_one()
    punto = conexion.execute(
        text(
            "INSERT INTO puntos_atencion (organismo_id, jurisdiccion_id, nombre, tipo, alcance) "
            "VALUES (:o, 'AR-C', 'Sede Comunal de prueba', 'SEDE', 'PROVINCIAL') RETURNING id"
        ),
        {"o": organismo},
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            "  estado_revision, valid_tipo, valid_desde, verificado_en) "
            "VALUES ('punto_atencion', :p, 1, 'APPROVED', 'ABIERTO_FIN', DATE '2025-01-01', "
            "        now()) RETURNING id"
        ),
        {"p": punto},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO punto_versiones (registro_version_id, punto_id, direccion_legible, "
            "  localidad, es_presencial) "
            "VALUES (:v, :p, 'Humberto 1° 250', 'San Telmo', true)"
        ),
        {"v": version, "p": punto},
    )
    Publicador(conexion).publicar(
        actor="publicador:recorrido", motivo="Un lugar de atención en el corte."
    )


# El texto que la persona va a ver como pregunta. Es el de la norma, palabra por
# palabra: la pantalla no lo reescribe.
CONDICION_PREGUNTABLE = (
    "Son beneficiarios las personas en situación de vulnerabilidad habitacional."
)
CONDICION_DE_DOS_COSAS = (
    "Acreditar la identidad de la persona titular y la del grupo conviviente."
)


def _beneficio_con_reglas_publicado(conexion, corpus) -> None:
    """Un beneficio publicado con condiciones evaluables, para el recorrido.

    Sin esto el recorrido nunca llega a la parte que orienta: la consulta
    contesta con evidencia y ahí se termina. Van dos reglas a propósito, una que
    se puede preguntar —nombra un solo dato— y otra que no, porque pide dos
    cosas en la misma oración; la segunda es la que prueba que la pantalla
    prefiere declarar que no puede preguntar antes que preguntar mal.
    """
    import json

    beneficio = conexion.execute(
        text(
            "INSERT INTO beneficios (codigo, nombre, linea, familia) "
            "VALUES ('AR.RECORRIDO', 'Apoyo habitacional', 'SUBSIDIO', 'HABITACIONAL') "
            "RETURNING id"
        )
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde, release_id, verificado_en) "
            "SELECT 'beneficio', :b, 1, 'PUBLISHED', 'ABIERTO_FIN', DATE '2025-12-23', "
            "       rv.release_id, now() "
            "  FROM registro_versiones rv WHERE rv.id = :rv RETURNING id"
        ),
        {"b": beneficio, "rv": corpus.registro_version_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
            " jurisdiccion_id, naturaleza, descripcion) "
            "VALUES (:rv, :b, 'AR-C', 'PRESTACION_MONETARIA', "
            " 'Prestación económica mensual para el recorrido.')"
        ),
        {"rv": version, "b": beneficio},
    )
    evidencia = conexion.execute(text("SELECT id FROM evidencias LIMIT 1")).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO beneficio_normas (beneficio_version_id, norma_version_id, rol, "
            " evidencia_id) VALUES (:bv, :nv, 'CREA', :e)"
        ),
        {"bv": version, "nv": corpus.registro_version_id, "e": evidencia},
    )
    for literal, ast in (
        (
            CONDICION_PREGUNTABLE,
            {"op": "is_true", "field": "vulnerabilidad_habitacional", "schema_version": "1.0"},
        ),
        (
            CONDICION_DE_DOS_COSAS,
            {
                "op": "all",
                "schema_version": "1.0",
                "args": [
                    {"op": "is_true", "field": "identidad_titular", "schema_version": "1.0"},
                    {"op": "is_true", "field": "identidad_grupo", "schema_version": "1.0"},
                ],
            },
        ),
    ):
        conexion.execute(
            text(
                "INSERT INTO reglas (beneficio_version_id, evidencia_id, categoria, "
                " texto_literal, descripcion, ast, ast_schema_version, requiere_revision, "
                " estado_revision) "
                "VALUES (:bv, :e, 'APLICABILIDAD', :l, 'Condición del recorrido.', "
                " CAST(:a AS jsonb), '1.0', false, 'APPROVED')"
            ),
            {"bv": version, "e": evidencia, "l": literal, "a": json.dumps(ast)},
        )


@pytest.fixture(scope="module")
def servidor(base_e2e: str) -> Iterator[str]:
    """Uvicorn de verdad, en su propio proceso."""
    import httpx

    puerto = _puerto_libre()
    entorno = dict(os.environ)
    entorno["BN_DATABASE_URL"] = base_e2e
    entorno.pop("BN_DATABASE_URL_API", None)
    entorno["BN_ENTORNO"] = "local"
    # Sin límite de consultas: los veintiún casos llegan desde el mismo origen
    # y en menos de un minuto, así que compartirían un balde y el recorrido
    # empezaría a fallar por el cupo que gastaron los casos anteriores. Eso
    # sería un fallo que no dice nada de la pantalla. El límite se prueba en
    # `tests/integracion/test_limites_de_uso.py` y bajo carga real en
    # `bn calidad carga`.
    entorno["BN_LIMITE_CONSULTAS_POR_MINUTO"] = "0"
    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend_normativo.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(puerto),
            "--log-level",
            "warning",
        ],
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{puerto}"
    limite = time.monotonic() + 60
    try:
        while time.monotonic() < limite:
            if proceso.poll() is not None:
                salida = (proceso.stdout.read() or b"").decode("utf-8", "replace")
                pytest.fail(f"el servidor murió al arrancar:\n{salida}", pytrace=False)
            try:
                if httpx.get(f"{base}/salud", timeout=2).status_code == 200:
                    break
            except Exception:
                time.sleep(0.4)
        else:
            pytest.fail("el servidor no llegó a contestar /salud en 60 s", pytrace=False)
        yield base
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proceso.kill()


def _chromium_del_entorno() -> str | None:
    """El navegador que haya, sin bajarse uno.

    La versión de Playwright instalada y la del navegador provisto por el
    entorno no tienen por qué coincidir, y bajar un navegador desde una prueba
    no es algo que una prueba deba hacer. Si hay uno declarado, se usa ése.
    """
    import os
    import pathlib as _pathlib

    declarado = os.environ.get("BN_PRUEBAS_CHROMIUM")
    candidatos = [declarado] if declarado else []
    candidatos.append("/opt/pw-browsers/chromium")
    for candidato in candidatos:
        if candidato and _pathlib.Path(candidato).exists():
            return candidato
    return None


@pytest.fixture(scope="module")
def navegador():
    try:
        from playwright import sync_api as playwright
    except ImportError:  # pragma: no cover - entorno sin Playwright
        pytest.fail(
            "Playwright no está instalado y el recorrido ciudadano no puede correr. "
            "Va en el extra `dev`: pip install -e '.[dev]'",
            pytrace=False,
        )
    ejecutable = _chromium_del_entorno()
    with playwright.sync_playwright() as pw:
        opciones = {"args": ["--no-sandbox"]}
        if ejecutable:
            opciones["executable_path"] = ejecutable
        try:
            browser = pw.chromium.launch(**opciones)
        except Exception as error:  # pragma: no cover - entorno sin navegador
            pytest.fail(
                "No hay Chromium para correr el recorrido ciudadano. No se saltea: un "
                "salteo se cuenta como éxito y este es el único caso que prueba la "
                "pantalla que usa una persona.\n"
                "  Para correrlo:  playwright install chromium\n"
                "  O declarar uno: BN_PRUEBAS_CHROMIUM=/ruta/al/chrome\n"
                f"  El error fue:   {error}",
                pytrace=False,
            )
        yield browser
        browser.close()


@pytest.fixture
def pagina(navegador, servidor: str):
    """Una pestaña a 360 px: el ancho que el criterio 3 nombra."""
    contexto = navegador.new_context(viewport={"width": ANCHO_MINIMO, "height": 780})
    hoja = contexto.new_page()
    hoja.goto(f"{servidor}/consulta", wait_until="domcontentloaded")
    # El saludo aparece cuando el hilo ya cargó lo que hay publicado. No se
    # espera «networkidle»: el navegador hace pedidos de fondo propios que a
    # través del proxy quedan colgados y esa espera nunca termina.
    hoja.wait_for_selector(".msj.suyo", timeout=25_000)
    yield hoja
    contexto.close()


def _preguntar(pagina, texto: str) -> None:
    """Escribir y mandar, como se manda un mensaje: con Enter."""
    pagina.fill("#pregunta", texto)
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector("#titulo-respuesta", timeout=20_000)


# --- criterio 1: quien pregunta no pierde el control -------------------------


def test_se_puede_preguntar_y_se_contesta(pagina) -> None:
    _preguntar(pagina, "beneficiarios del programa de apoyo")
    assert pagina.inner_text("#titulo-respuesta").strip()
    # Queda un hilo: lo que escribió la persona y lo que contestó el sistema.
    assert pagina.locator(".msj.mia").count() == 1


def test_se_puede_aclarar_la_jurisdiccion_dentro_de_la_conversacion(pagina) -> None:
    """Las aclaraciones son parte del diálogo, no un formulario arriba.

    Y lo que el sistema termina teniendo en cuenta queda a la vista y se puede
    quitar: un chat que arrastra supuestos sin mostrarlos es donde estos
    sistemas empiezan a mentir.
    """
    _preguntar(pagina, "prestación económica")
    pagina.get_by_role("button", name="Buscar sólo donde vivo").click()
    pagina.get_by_role("button", name="Ciudad Autónoma de Buenos Aires").first.click()
    pagina.wait_for_selector("#contexto:not([hidden])", timeout=20_000)
    assert "Jurisdicción" in pagina.inner_text("#contexto")

    # Y se puede sacar: el supuesto no queda pegado a la conversación.
    pagina.locator("#contexto-fichas button").first.click()
    assert pagina.locator("#contexto").is_hidden()


def test_lo_que_la_persona_cuenta_no_se_guarda(pagina) -> None:
    """Un chat hace que la gente cuente más que un formulario. No se guarda nada."""
    pagina.fill("#pregunta", "me quedé sin casa después de un incendio")
    with pagina.expect_request("**/v1/respuestas**") as esperado:
        pagina.keyboard.press("Enter")
    enviado = esperado.value.post_data_json
    assert "me quedé sin casa" in enviado["consulta"]
    pagina.wait_for_selector("#titulo-respuesta", timeout=20_000)
    assert pagina.evaluate("() => Object.keys(localStorage).length") == 0
    assert pagina.evaluate("() => Object.keys(sessionStorage).length") == 0


def test_la_pantalla_abre_invitando_a_escribir(pagina) -> None:
    """Un chat que arranca con un mensaje del sistema ya parece usado.

    Mientras no hay conversación la portada está sobre la página y el cuadro de
    escritura va al centro; en cuanto se manda algo, la portada se va y el
    cuadro baja.
    """
    assert pagina.locator(".bienvenida").count() == 1
    assert "sin-conversacion" in (pagina.get_attribute("body", "class") or "")

    _preguntar(pagina, "estoy durmiendo en la calle")
    assert pagina.locator(".bienvenida").count() == 0
    assert "sin-conversacion" not in (pagina.get_attribute("body", "class") or "")


def test_mientras_busca_se_ve_que_esta_buscando(pagina) -> None:
    """Y se puede parar: un control apagado mientras el sistema piensa deja a
    quien escribió sin ninguna salida."""
    assert pagina.locator("#cancelar").is_hidden()
    pagina.fill("#pregunta", "prestación económica")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector(".pensando", timeout=5_000)
    assert pagina.locator("#cancelar").is_visible()

    pagina.wait_for_selector("#titulo-respuesta", timeout=20_000)
    # El indicador no queda colgado después de contestar.
    assert pagina.locator(".pensando").count() == 0
    assert pagina.locator("#cancelar").is_hidden()


def test_el_indicador_no_queda_colgado_si_falla(pagina) -> None:
    pagina.route("**/v1/respuestas**", lambda ruta: ruta.fulfill(status=503, body="{}"))
    _preguntar(pagina, "prestación")
    assert pagina.locator(".pensando").count() == 0


def test_la_apertura_avisa_que_no_hacen_falta_datos_personales(pagina) -> None:
    """Lo que no se pide no se puede filtrar, y en un chat hay que decirlo."""
    apertura = pagina.inner_text(".msj.suyo")
    assert "no hace falta" in apertura.lower()
    assert "documento" in apertura.lower()


def test_se_puede_empezar_una_conversacion_nueva(pagina) -> None:
    _preguntar(pagina, "una situación privada que conté")
    pagina.click("#limpiar")
    pagina.wait_for_selector(".msj.suyo", timeout=10_000)
    assert pagina.input_value("#pregunta") == ""
    # El hilo anterior no está: queda sólo el saludo de la conversación nueva.
    assert pagina.locator(".msj.mia").count() == 0
    assert "una situación privada" not in pagina.inner_text("#resultado")
    assert pagina.evaluate("() => document.activeElement.id") == "pregunta"


def test_una_consulta_sin_texto_no_se_manda_y_lo_dice(pagina) -> None:
    pagina.click("#enviar")
    assert pagina.is_visible("#estado")
    assert "querés saber" in pagina.inner_text("#estado")


def test_se_puede_reintentar_cuando_el_servicio_falla(pagina) -> None:
    """El error tiene que ser comprensible y no dejar a la persona sin salida."""
    pagina.route("**/v1/respuestas**", lambda ruta: ruta.fulfill(status=503, body="{}"))
    pagina.fill("#pregunta", "prestación")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector("#titulo-respuesta", timeout=20_000)
    texto = pagina.inner_text("#resultado")
    assert "no pude" in texto.lower()
    assert "503" not in pagina.inner_text("#titulo-respuesta")
    assert pagina.is_visible("#reintentar")
    # La pregunta quedó en el hilo: reintentar no obliga a volver a escribirla.
    assert "prestación" in pagina.inner_text(".msj.mia")

    pagina.unroute("**/v1/respuestas**")
    pagina.click("#reintentar")
    pagina.wait_for_selector(".s-EXTRACTO, .s-GENERADA, .s-ABSTENCION", timeout=20_000)


def test_se_puede_cancelar_una_consulta_en_curso(pagina) -> None:
    pagina.route("**/v1/respuestas**", lambda ruta: None)  # se cuelga a propósito
    pagina.fill("#pregunta", "prestación")
    pagina.click("#enviar")
    pagina.wait_for_selector("#cancelar:not([disabled])", timeout=5_000)
    pagina.click("#cancelar")
    pagina.wait_for_function(
        "() => document.getElementById('estado').textContent.includes('cancel')",
        timeout=10_000,
    )
    assert not pagina.is_disabled("#enviar")


# --- criterio 2: la respuesta se puede verificar -----------------------------


def test_la_respuesta_muestra_fuentes_abribles(pagina) -> None:
    _preguntar(pagina, "beneficiarios vulnerabilidad habitacional")
    if pagina.is_visible(".s-ABSTENCION"):
        pytest.fail("el corpus publicado tiene el texto: esto debería encontrarlo")
    assert pagina.locator("ol.fuentes li").count() >= 1
    # Cada nota al pie del texto lleva a una fuente que existe en la lista.
    for destino in pagina.eval_on_selector_all(
        "a.nota", "nodos => nodos.map(n => n.getAttribute('href'))"
    ):
        assert pagina.locator(destino).count() == 1, f"la nota {destino} no lleva a ningún lado"


def test_la_respuesta_declara_fecha_estado_y_modo(pagina) -> None:
    _preguntar(pagina, "prestación económica")
    ficha = pagina.inner_text(".ficha").casefold()
    assert "vale para el" in ficha
    # La fecha es lo único de esto que le sirve a una persona. El identificador
    # del corte no se muestra —es un uuid— pero queda para quien dé soporte.
    assert pagina.get_attribute(".ficha", "data-corte")
    # Un extracto no se presenta como generación activa.
    assert pagina.locator(".sello").count() == 1


def test_una_abstencion_se_explica_y_ofrece_una_salida(pagina) -> None:
    _preguntar(pagina, "zzzz qwrtpxk esto no existe en ninguna norma")
    # `inner_text` devuelve el texto **renderizado**, y los encabezados de
    # sección van en versalitas por CSS: se compara sin distinguir mayúsculas.
    texto = pagina.inner_text("#resultado").casefold()
    assert "no lo sé" in pagina.inner_text("#titulo-respuesta").casefold()
    assert "no te estoy diciendo que no te corresponda" in texto
    # Y le dice qué hay publicado, en vez de dejarla sin salida.
    assert "lo que tengo publicado" in texto


def test_siempre_hay_canal_oficial_o_se_dice_que_no_lo_hay(pagina) -> None:
    """Nunca una respuesta que termina sin decir a dónde ir."""
    _preguntar(pagina, "prestación")
    texto = pagina.inner_text("#resultado").casefold()
    assert "a dónde ir" in texto
    assert ("lugar de atención" in texto) or pagina.locator(".canal").count() >= 1


# Palabras nuestras, no de quien pregunta si lo pueden desalojar. El plan lo
# pide con esas letras: «sin nombres de tablas o detalles del modelo dentro del
# recorrido ciudadano». Hubo un momento en que la pantalla mostraba, textual,
# «se construye con `bn recuperacion indexar`».
JERGA_PROHIBIDA = (
    "corte publicado",
    "release",
    "chunk",
    "embedding",
    "semántic",
    "léxic",
    "corpus",
    "fragmento",
    "índice",
    "proveedor de modelo",
    "extracto",
    "abstención",
    "schema",
    "data_status",
    "bn recuperacion",
    "traceback",
    "http 5",
)


def test_la_pantalla_no_habla_en_jerga(pagina) -> None:
    """Cuatro recorridos distintos, y en ninguno aparece una palabra de la cocina."""
    visto = [pagina.inner_text("body")]
    for consulta in (
        "me quedé sin casa después de un incendio",
        "¿cuánto cobra la asignación universal por hijo?",
        "zzzz qwrtpxk esto no existe",
    ):
        _preguntar(pagina, consulta)
        visto.append(pagina.inner_text("body"))
    entero = " ".join(visto).casefold()
    colados = [jerga for jerga in JERGA_PROHIBIDA if jerga in entero]
    assert colados == [], f"la pantalla habló en jerga: {colados}"


def test_lo_urgente_va_arriba_de_la_norma(pagina) -> None:
    """Alguien en la calle recibía el artículo 10 de una ley. Ahora no.

    Y el aviso no diagnostica —«si necesitás un lugar esta noche», no «estás en
    una emergencia»— ni inventa un teléfono: cuando no hay canal cargado lo
    dice, porque improvisar un número que esté mal hace daño inmediato.
    """
    _preguntar(pagina, "estoy durmiendo en la calle con mi bebé")
    assert pagina.locator(".urgente").count() == 1

    # Arriba del título de la respuesta, no debajo.
    orden = pagina.evaluate(
        """() => {
            const u = document.querySelector('.urgente');
            const t = document.querySelector('#titulo-respuesta');
            return u.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING ? 1 : 0;
        }"""
    )
    assert orden == 1, "la urgencia tiene que leerse antes que la norma"

    texto = pagina.inner_text(".urgente").casefold()
    assert "no reemplaza pedir ayuda" in texto
    assert "no tengo cargado a quién llamar para una emergencia" in texto
    for inventado in ("911", "147", "144", "llamá al"):
        assert inventado not in texto, f"apareció un canal que nadie curó: {inventado}"


def test_una_consulta_informativa_no_dispara_la_alarma(pagina) -> None:
    """Un aviso de emergencia que aparece siempre deja de leerse."""
    _preguntar(pagina, "quién puede pedir el subsidio habitacional")
    assert pagina.locator(".urgente").count() == 0


def test_la_pantalla_no_afirma_elegibilidad(pagina) -> None:
    """Prohibido por la especificación, y es lo primero que se lee."""
    encabezado = pagina.inner_text("main")
    assert "no decide si te corresponde" in encabezado
    for prohibido in ("te corresponde el beneficio", "tenés derecho a", "fuiste aprobad"):
        assert prohibido not in encabezado.lower()


# --- criterio 3: teclado, lector de pantalla, 360 px -------------------------


def test_cada_control_tiene_etiqueta(pagina) -> None:
    """Un campo sin etiqueta es un campo que un lector de pantalla no nombra."""
    sin_nombre = pagina.evaluate(
        """() => {
            const malos = [];
            document.querySelectorAll('input, select, textarea').forEach(c => {
                const etiqueta = c.labels && c.labels.length
                    ? c.labels[0].textContent.trim()
                    : (c.getAttribute('aria-label') || '').trim();
                if(!etiqueta) malos.push(c.id || c.name || c.outerHTML.slice(0, 60));
            });
            return malos;
        }"""
    )
    assert sin_nombre == []


def test_a_360_px_no_hay_desborde_horizontal(pagina) -> None:
    _preguntar(pagina, "beneficiarios vulnerabilidad habitacional")
    desborde = pagina.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert desborde <= 1, f"la página se sale {desborde} px del ancho de 360"


def test_el_foco_se_mueve_a_la_respuesta(pagina) -> None:
    """Con lector de pantalla, una respuesta que aparece fuera del foco no se anuncia."""
    _preguntar(pagina, "prestación")
    assert pagina.evaluate("() => document.activeElement.id") == "titulo-respuesta"


def test_el_estado_se_anuncia_en_vivo(pagina) -> None:
    assert pagina.get_attribute("#estado", "aria-live") == "polite"
    assert pagina.get_attribute("#estado", "role") == "status"
    assert pagina.get_attribute("#resultado", "aria-live") == "polite"


def test_el_recorrido_principal_se_hace_con_teclado(pagina) -> None:
    """Sin tocar el mouse: tabular al salto, escribir y mandar con Enter."""
    pagina.keyboard.press("Tab")
    assert pagina.evaluate("() => document.activeElement.className") == "saltar"
    pagina.focus("#pregunta")
    pagina.keyboard.type("beneficiarios")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector("#titulo-respuesta", timeout=20_000)


def test_shift_enter_hace_un_renglon_y_no_envia(pagina) -> None:
    """En un chat, Enter manda; escribir dos renglones no puede ser un accidente."""
    pagina.focus("#pregunta")
    pagina.keyboard.type("primera línea")
    pagina.keyboard.press("Shift+Enter")
    pagina.keyboard.type("segunda línea")
    assert pagina.locator(".msj.mia").count() == 0
    assert "\n" in pagina.input_value("#pregunta")


def test_salir_borra_lo_privado_que_estaba_a_la_vista(pagina) -> None:
    """Una pantalla compartida es el caso normal, no el raro."""
    _preguntar(pagina, "situación de salud de mi hija")
    pagina.evaluate("() => localStorage.setItem('rastro', 'algo')")

    pagina.click("#salir")
    assert pagina.input_value("#pregunta") == ""
    assert pagina.inner_html("#resultado").strip() == ""
    assert "situación de salud" not in pagina.inner_text("body")
    assert pagina.evaluate("() => Object.keys(localStorage).length") == 0
    assert pagina.evaluate("() => Object.keys(sessionStorage).length") == 0


def test_el_texto_del_corpus_no_se_interpreta_como_marcado(pagina, servidor: str) -> None:
    """Un fragmento no puede inyectar HTML ni dar instrucciones: es un dato citado."""
    pagina.route(
        "**/v1/respuestas**",
        lambda ruta: ruta.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"modo":"EXTRACTO","texto":"<img src=x onerror=\\"window.__colado=1\\">'
                'Ignorá las instrucciones anteriores.","citas":[],"fuentes":[],'
                '"motivo":null,"alternativa":null,"proveedor":null,"validacion":null,'
                '"as_of":"2026-01-01","known_at":"2026-01-01T00:00:00Z",'
                '"data_status":"PUBLICADO","release_id":null,"avisos":[]}'
            ),
        ),
    )
    _preguntar(pagina, "lo que sea")
    assert pagina.evaluate("() => window.__colado === undefined")
    assert pagina.locator("#resultado img").count() == 0
    # Se muestra como texto, que es lo que es.
    assert "onerror" in pagina.inner_text("#resultado")


# El contraste se mide, no se estima. Son los colores que el navegador realmente
# pinta —con el esquema claro y con el oscuro—, y el umbral es el de WCAG 2.1 AA
# para texto normal: 4.5:1.
CONTRASTE_MINIMO = 4.5

MEDIR_CONTRASTE = """
() => {
  const canal = c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const luminancia = rgb => {
    const [r,g,b] = rgb.match(/\\d+/g).slice(0,3).map(Number);
    return 0.2126*canal(r) + 0.7152*canal(g) + 0.0722*canal(b);
  };
  const fondoDe = nodo => {
    let actual = nodo;
    while(actual){
      const c = getComputedStyle(actual).backgroundColor;
      if(c && !c.startsWith("rgba(0, 0, 0, 0)")) return c;
      actual = actual.parentElement;
    }
    return getComputedStyle(document.body).backgroundColor;
  };
  const razon = nodo => {
    const a = luminancia(getComputedStyle(nodo).color);
    const b = luminancia(fondoDe(nodo));
    return (Math.max(a,b) + 0.05) / (Math.min(a,b) + 0.05);
  };
  const UMBRAL = 4.5;
  const flojos = [];
  document.querySelectorAll(
    "p, li, label, legend, h1, h2, h3, a, button, dt, dd, span"
  ).forEach(nodo => {
    if(!nodo.offsetParent && nodo.tagName !== "BODY") return;   // no visible
    if(!(nodo.textContent || "").trim()) return;
    const r = razon(nodo);
    if(r < UMBRAL) flojos.push(
      nodo.tagName + "." + (nodo.className || "-") + " → " + r.toFixed(2) + ":1"
    );
  });
  return flojos;
}
"""


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_el_contraste_alcanza_el_umbral_en_los_dos_esquemas(
    navegador, servidor: str, esquema: str
) -> None:
    contexto = navegador.new_context(
        viewport={"width": ANCHO_MINIMO, "height": 780}, color_scheme=esquema
    )
    hoja = contexto.new_page()
    try:
        hoja.goto(f"{servidor}/consulta", wait_until="domcontentloaded")
        hoja.wait_for_selector(".msj.suyo", timeout=25_000)
        hoja.fill("#pregunta", "beneficiarios vulnerabilidad habitacional")
        hoja.keyboard.press("Enter")
        hoja.wait_for_selector("#titulo-respuesta", timeout=20_000)
        flojos = hoja.evaluate(MEDIR_CONTRASTE)
        assert flojos == [], f"con esquema {esquema} no llegan a {CONTRASTE_MINIMO}:1 → {flojos}"
    finally:
        contexto.close()


# --- cerrar el ciclo: qué puede contestar la persona -------------------------


def test_antes_de_contestar_no_hay_nada_que_devolver(pagina) -> None:
    """La portada no pregunta «¿te sirvió?»: todavía no sirvió de nada."""
    assert pagina.locator(".cierre").count() == 0


def test_se_puede_decir_que_no_sirvio_y_no_viaja_lo_que_escribio(pagina) -> None:
    """La señal viaja sola: el identificador de la respuesta y nada más.

    Es la prueba de la decisión de privacidad, no del botón. Si algún día el
    cuerpo lleva un comentario, este caso lo tiene que ver.
    """
    _preguntar(pagina, "me quieren echar de la pieza donde vivo con mis hijos")
    pagina.wait_for_selector(".cierre", timeout=20_000)
    with pagina.expect_request("**/v1/devoluciones") as esperado:
        pagina.locator('.cierre button[data-senal="NO_SIRVIO"]').click()
    enviado = esperado.value.post_data_json
    assert set(enviado) == {"request_id", "senal"}
    assert enviado["senal"] == "NO_SIRVIO"
    assert enviado["request_id"]
    assert "pieza" not in str(enviado)

    pagina.wait_for_selector(".cierre-gracias", timeout=10_000)
    gracias = pagina.inner_text(".cierre-gracias")
    assert "Gracias" in gracias
    # Y la salida a una persona sigue estando: es donde más hace falta.
    assert pagina.get_by_role("button", name="Quiero hablar con una persona").count() >= 1


def test_la_devolucion_se_ata_a_la_respuesta_que_se_leyo(pagina) -> None:
    """El `request_id` que se manda es el que trajo esa respuesta."""
    pagina.fill("#pregunta", "prestación económica")
    with pagina.expect_response("**/v1/respuestas**") as respuesta:
        pagina.keyboard.press("Enter")
    de_la_respuesta = respuesta.value.header_value("x-request-id")
    pagina.wait_for_selector(".cierre", timeout=20_000)
    with pagina.expect_request("**/v1/devoluciones") as esperado:
        pagina.locator('.cierre button[data-senal="SIRVIO"]').click()
    assert esperado.value.post_data_json["request_id"] == de_la_respuesta


def test_pedir_una_persona_no_promete_lo_que_no_puede(pagina) -> None:
    """No hay a dónde escribirle a nadie, y se dice.

    La pantalla no pide datos —esa es la decisión de la que cuelga todo lo
    demás—, así que no puede prometer que alguien va a llamar. Y no inventa un
    teléfono: ese número, si está mal, hace daño el mismo día.
    """
    _preguntar(pagina, "no tengo dónde dormir esta noche")
    pagina.wait_for_selector(".cierre", timeout=20_000)
    pagina.locator('.cierre button[data-senal="QUIERE_PERSONA"]').click()
    pagina.wait_for_selector(".cierre-gracias", timeout=10_000)
    texto = pagina.inner_text(".cierre-gracias")
    assert "no tengo a dónde escribirte" in texto
    for inventado in ("911", "147", "144", "llamá al", "te vamos a llamar", "te contactamos"):
        assert inventado not in texto, f"apareció una promesa que nadie puede cumplir: {inventado}"


def test_apretar_dos_veces_no_cuenta_dos_veces(pagina) -> None:
    """Los botones se van al primer clic: la tasa no se infla desde la pantalla."""
    _preguntar(pagina, "prestación económica")
    pagina.wait_for_selector(".cierre", timeout=20_000)
    pagina.locator('.cierre button[data-senal="SIRVIO"]').click()
    pagina.wait_for_selector(".cierre-gracias", timeout=10_000)
    assert pagina.locator('.cierre button[data-senal="SIRVIO"]').count() == 0


# --- lo urgente y lo que hay: no son lo mismo --------------------------------


def test_a_donde_ir_muestra_el_lugar_publicado(pagina) -> None:
    """La otra mitad del frente, que hasta ahora sólo se probaba vacía."""
    _preguntar(pagina, "prestación económica")
    assert pagina.locator(".canal").count() >= 1
    texto = pagina.inner_text(".canal")
    assert "Sede Comunal de prueba" in texto
    assert "Humberto 1° 250" in texto


def test_una_oficina_con_horario_no_se_ofrece_como_canal_de_emergencia(pagina) -> None:
    """Lo que hay cargado son sedes con horario, no guardias.

    Mandar a alguien cuyo hijo está en riesgo esta noche a una comuna que abre a
    las nueve es peor que decirle que no tengo: parece una respuesta y no lo es.
    El corpus todavía no distingue un canal de emergencia de una mesa de
    entradas —no hay campo que lo diga—, así que el bloque de urgencia no ofrece
    ninguno.
    """
    _preguntar(pagina, "estoy durmiendo en la calle con mi bebé")
    urgente = pagina.locator(".urgente")
    assert urgente.count() == 1
    texto = urgente.inner_text()
    assert "No tengo cargado a quién llamar para una emergencia" in texto
    assert "Sede Comunal de prueba" not in texto, (
        "el bloque de urgencia está ofreciendo una oficina con horario como si fuera "
        "un canal para esta noche"
    )
    for inventado in ("911", "147", "144", "llamá al"):
        assert inventado not in texto
    # Y el lugar sigue estando donde corresponde: más abajo, como lo que es.
    assert "Sede Comunal de prueba" in pagina.inner_text(".canal")


# --- P-025 / P-032 / P-037: la conversación recuerda, y se puede corregir -----
#
# Esta parte del recorrido es la que puede hacer daño de verdad. No porque se
# rompa, sino porque puede quedarse con datos que la persona no sabe que dio,
# mostrarle una conclusión calculada con un dato que ya corrigió, o preguntarle
# el nombre de un campo de una tabla. Los casos de acá miran eso.


def _orientar(pagina) -> None:
    """Llegar hasta donde la pantalla mira las condiciones del programa."""
    _preguntar(pagina, "vulnerabilidad habitacional")
    pagina.wait_for_selector(".pregunta", timeout=20_000)


def _contestar(pagina, boton: str) -> str:
    """Contestar la pregunta y devolver la orientación **nueva**, en minúsculas.

    Contestar dispara otra consulta, así que hay que esperar a que llegue: leer
    el último mensaje enseguida devuelve el «buscando en las normas».
    """
    cuantas = pagina.locator(".msj.suyo.con-orientacion").count()
    pagina.locator(".pregunta").last.get_by_text(boton, exact=True).click()
    pagina.wait_for_function(
        "n => document.querySelectorAll('.msj.suyo.con-orientacion').length > n",
        arg=cuantas,
        timeout=20_000,
    )
    # En minúsculas: los rótulos de los grupos se pintan en mayúsculas por CSS y
    # `inner_text` devuelve lo que se ve, no lo que dice el HTML. Esa diferencia
    # es de estilo, no de contenido, y una prueba no debería atarse a ella.
    return pagina.locator(".msj.suyo.con-orientacion").last.inner_text().lower()


def test_la_portada_dice_que_se_guarda_lo_que_se_confirma(pagina) -> None:
    """Antes prometía que no se guardaba nada. Dejó de ser cierto.

    Una promesa de privacidad incumplida es peor que no haberla hecho, así que
    la portada dice las tres cosas que la hacen verificable: qué se guarda, por
    cuánto tiempo y cómo se borra.
    """
    apertura = pagina.inner_text(".bienvenida")
    assert "Nada de lo que escribas se guarda" not in apertura
    assert "mensajes no se guardan" in apertura.lower()
    assert "confirmes" in apertura.lower()
    assert "media hora" in apertura and "dos horas" in apertura


def test_antes_de_confirmar_nada_no_hay_nada_que_revisar(pagina) -> None:
    """El repaso no está vacío en pantalla: no está."""
    assert pagina.locator("#repaso").is_hidden()
    _preguntar(pagina, "una consulta cualquiera")
    assert pagina.locator("#repaso").is_hidden()


def test_la_pregunta_usa_las_palabras_de_la_norma_y_no_el_nombre_del_campo(pagina) -> None:
    _orientar(pagina)
    caja = pagina.inner_text(".pregunta")

    assert CONDICION_PREGUNTABLE in caja
    # El nombre interno del dato no aparece en ningún lado de la pantalla.
    assert "vulnerabilidad_habitacional" not in pagina.inner_text("body")
    # Y siempre está la salida de no contestar: no contestar es una respuesta.
    assert "Prefiero no contestar" in caja


def test_lo_que_se_confirma_queda_a_la_vista_y_dice_quien_lo_dijo(pagina) -> None:
    _orientar(pagina)
    _contestar(pagina, "Sí")

    repaso = pagina.inner_text("#repaso")
    assert "Sí" in repaso
    assert CONDICION_PREGUNTABLE in repaso
    assert "me lo dijiste vos" in repaso
    assert "vulnerabilidad_habitacional" not in repaso


def test_la_condicion_confirmada_pasa_a_cumplida_y_no_se_vuelve_a_preguntar(pagina) -> None:
    _orientar(pagina)
    orientacion = _contestar(pagina, "Sí")

    assert "se cumple con lo que me contaste" in orientacion
    assert CONDICION_PREGUNTABLE.lower() in orientacion


def test_cambiar_un_dato_marca_como_reemplazado_lo_que_se_calculo_con_el_viejo(pagina) -> None:
    """Dos conclusiones distintas conviviendo en la misma pantalla es lo peor
    que puede pasar acá: la persona se lleva la que le convenga o la que vio
    primero, y ninguna de las dos tiene por qué ser la que vale."""
    _orientar(pagina)
    _contestar(pagina, "Sí")

    pagina.locator("#repaso").get_by_text("Cambiar", exact=True).click()
    pagina.wait_for_selector(".msj.reemplazada", timeout=20_000)

    assert "ya no vale" in pagina.inner_text(".reemplazo")
    # Y el dato volvió a preguntarse, con la misma forma de antes.
    pagina.wait_for_selector(".pregunta", timeout=20_000)
    assert CONDICION_PREGUNTABLE in pagina.locator(".pregunta").last.inner_text()


def test_rehusar_no_se_lee_como_una_negativa_y_no_se_insiste(pagina) -> None:
    """No contestar no es contestar que no, y la diferencia decide un derecho."""
    _orientar(pagina)
    ultima = _contestar(pagina, "Prefiero no contestar")

    assert "Preferiste no contestar" in pagina.inner_text("#repaso")
    assert "no se cumple con lo que me contaste" not in ultima
    assert "todavía no lo sé" in ultima


def test_se_declara_lo_que_no_se_puede_preguntar_en_vez_de_callarlo(pagina) -> None:
    """Callarlo dejaría a la persona creyendo que contestó todo lo que había."""
    _orientar(pagina)
    texto = pagina.locator(".msj.suyo").last.inner_text()
    assert "no te puedo preguntar todavía" in texto
    # Y no se le muestra dos veces la misma oración esperando que adivine cuál
    # de las dos cosas que pide le están preguntando.
    assert CONDICION_DE_DOS_COSAS not in pagina.locator(".pregunta").inner_text()


def test_borrar_los_datos_los_saca_y_deja_leer_lo_que_ya_contesto(pagina) -> None:
    """Alguien puede querer sacar sus datos y seguir leyendo lo que le
    contestaron. Lo que no puede pasar es que la conclusión calculada con esos
    datos quede en pantalla como si todavía valiera."""
    _orientar(pagina)
    _contestar(pagina, "Sí")

    pagina.click("#borrar-conversacion")
    pagina.wait_for_selector("#repaso", state="hidden", timeout=20_000)
    pagina.wait_for_selector(".msj.reemplazada", timeout=20_000)
    assert "ya no vale" in pagina.inner_text(".reemplazo")
    # El hilo sigue ahí para leerlo.
    assert CONDICION_PREGUNTABLE in pagina.inner_text("#resultado")


def test_salir_y_borrar_saca_tambien_lo_que_estaba_en_pantalla(pagina) -> None:
    """El otro botón sí limpia todo: es el de la pantalla compartida."""
    _orientar(pagina)
    _contestar(pagina, "Sí")

    pagina.click("#salir")
    pagina.wait_for_selector("#repaso", state="hidden", timeout=20_000)
    assert CONDICION_PREGUNTABLE not in pagina.inner_text("body")


def test_una_conversacion_vencida_se_dice_y_no_se_resucita(pagina) -> None:
    """El plazo es una promesa de la pantalla, no un detalle del servidor."""
    pagina.route(
        "**/v1/respuestas**",
        lambda ruta: ruta.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"modo":"EXTRACTO","texto":"algo","citas":[],"fuentes":[],"motivo":null,'
                '"alternativa":null,"proveedor":null,"validacion":null,'
                '"as_of":"2026-01-01","known_at":"2026-01-01T00:00:00Z",'
                '"release_id":null,"data_status":"PUBLICADO","cobertura":[],'
                '"notas_operativas":[],"avisos":[],"solo_parecidos":false,'
                '"urgencia":{"clase":null,"detectada":false},'
                '"sesion_vencida":true,"orientacion":null}'
            ),
        ),
    )
    pagina.fill("#pregunta", "algo")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector("text=Se cerró la conversación", timeout=20_000)

    texto = pagina.inner_text(".msj.suyo >> nth=-1")
    assert "media hora" in texto
    assert pagina.locator("#repaso").is_hidden()


def test_la_eleccion_de_programa_se_ve_y_se_puede_deshacer(pagina, servidor: str) -> None:
    """Un supuesto que el sistema arrastra sin mostrarlo es donde estos
    sistemas empiezan a mentir, y sacarlo de la vista sin sacarlo de la
    conversación es peor: sigue acotando cada consulta por atrás."""
    pagina.route(
        "**/v1/respuestas**",
        lambda ruta: ruta.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"modo":"EXTRACTO","texto":"algo","citas":[],"fuentes":[],"motivo":null,'
                '"alternativa":null,"proveedor":null,"validacion":null,'
                '"as_of":"2026-01-01","known_at":"2026-01-01T00:00:00Z",'
                '"release_id":null,"data_status":"PUBLICADO","cobertura":[],'
                '"notas_operativas":[],"avisos":[],"solo_parecidos":false,'
                '"urgencia":{"clase":null,"detectada":false},"sesion_vencida":false,'
                '"orientacion":{"beneficio":null,"resultado":null,"version_estado":0,'
                '"condiciones_cumplidas":[],"condiciones_no_cumplidas":[],'
                '"condiciones_desconocidas":[],"salvaguardas":[],"pregunta":null,'
                '"sin_preguntar":0,"motivo_sin_evaluar":"varios_beneficios",'
                '"candidatos":[{"codigo":"AR.UNO","nombre":"Programa uno"},'
                '{"codigo":"AR.DOS","nombre":"Programa dos"}],"aclaracion":"No decide."}}'
            ),
        ),
    )
    _preguntar(pagina, "algo que toca dos programas")
    pagina.wait_for_selector(".pregunta", timeout=20_000)
    assert "No elijo yo cuál es el tuyo" in pagina.inner_text(".pregunta")
    # Se ofrecen los nombres, nunca los códigos: «AR.UNO» es cómo lo llamamos
    # nosotros, no cómo lo conoce quien pregunta.
    assert "AR.UNO" not in pagina.inner_text("body")

    pagina.locator(".pregunta").get_by_text("Programa uno", exact=True).click()
    pagina.wait_for_selector("#contexto:not([hidden])", timeout=20_000)
    assert "Programa: Programa uno" in pagina.inner_text("#contexto")

    pagina.locator("#contexto").get_by_role("button").first.click()
    pagina.wait_for_selector("#contexto", state="hidden", timeout=20_000)
    assert "Programa uno" not in pagina.inner_text("#contexto")


def test_los_controles_de_una_respuesta_reemplazada_dejan_de_andar(pagina) -> None:
    """Un botón que sigue contestando adentro de un bloque marcado como «esto ya
    no vale» vuelve a escribir el dato viejo."""
    _orientar(pagina)
    _contestar(pagina, "Sí")
    pagina.locator("#repaso").get_by_text("Cambiar", exact=True).click()
    pagina.wait_for_selector(".msj.reemplazada", timeout=20_000)

    controles = pagina.locator(".msj.reemplazada .pregunta button")
    assert controles.count() > 0
    for i in range(controles.count()):
        assert controles.nth(i).is_disabled()
