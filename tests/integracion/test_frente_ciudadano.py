"""P-015: lo que el frente ciudadano necesita de la API para ser honesto.

El recorrido completo en un navegador está en `tests/aceptacion`. Acá se prueba
el contrato del que ese recorrido depende: que una cita se pueda abrir, que la
respuesta diga para cuándo vale y con qué estado, que los selectores tengan de
dónde salir, y que la consulta —la única ruta que una persona usa de verdad—
deje rastro medible.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

pytestmark = pytest.mark.integracion


def test_la_pantalla_se_sirve_desde_la_misma_imagen(cliente_api) -> None:
    """Un frente que viaja aparte puede quedar pidiendo campos que ya no existen."""
    respuesta = cliente_api.get("/consulta")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    cuerpo = respuesta.text
    assert '<html lang="es">' in cuerpo
    # Consume estas dos rutas y ninguna de administración.
    assert "/v1/respuestas" in cuerpo
    assert "/v1/vocabularios" in cuerpo
    assert "/v1/admin/" not in cuerpo


def test_los_selectores_salen_de_la_base_y_no_del_html(cliente_api, corpus) -> None:
    """Una jurisdicción que se agrega al corpus no puede quedar invisible."""
    cuerpo = cliente_api.get("/v1/vocabularios").json()
    jurisdicciones = cuerpo["data"]["jurisdicciones"]
    assert jurisdicciones, "el catálogo cargado tiene jurisdicciones"
    assert {"id", "nombre", "nivel"} <= set(jurisdicciones[0])
    # Y no están escritas en el HTML: el único <option> que trae es el neutro.
    html = cliente_api.get("/consulta").text
    for j in jurisdicciones:
        assert f'value="{j["id"]}"' not in html


def test_la_respuesta_dice_para_cuando_vale_y_con_que_estado(cliente_api, corpus_publicado) -> None:
    cuerpo = cliente_api.post("/v1/respuestas", json={"consulta": "apoyo"}).json()
    assert cuerpo["as_of"]
    assert cuerpo["known_at"]
    assert cuerpo["data_status"] in {"PUBLICADO", "SIN_RESULTADOS", "NO_PUBLICABLE"}
    assert cuerpo["modo"] in {"GENERADA", "EXTRACTO", "ABSTENCION"}
    # `fuentes` siempre viaja, aunque esté vacía: el frente no tiene que
    # adivinar si la clave falta porque no hay o porque la ruta no la manda.
    assert isinstance(cuerpo["fuentes"], list)


def test_la_cita_se_puede_abrir(cliente_api, corpus_publicado) -> None:
    """Un uuid no lo verifica nadie: la cita viaja con norma y con URL."""
    cuerpo = cliente_api.post("/v1/respuestas", json={"consulta": "beneficiarios"}).json()
    if cuerpo["modo"] == "ABSTENCION":
        pytest.skip("sin fragmentos recuperados no hay cita que abrir")
    assert cuerpo["fuentes"], "una respuesta no abstenida trae sus fuentes"
    fuente = cuerpo["fuentes"][0]
    assert {"chunk_id", "norma", "unidad", "url_fuente", "jurisdiccion"} <= set(fuente)
    assert fuente["norma"]
    # Y cada cita del texto tiene su fuente en la lista: una nota al pie que no
    # lleva a ningún lado es peor que no ponerla.
    citados = {str(f["chunk_id"]) for f in cuerpo["fuentes"]}
    for cita in cuerpo["citas"]:
        assert str(cita) in citados


def test_sin_evidencia_se_abstiene_con_motivo_y_alternativa(cliente_api, corpus_publicado) -> None:
    """Una abstención tiene que poder distinguirse de un «no te corresponde».

    Con corte publicado: sin él la respuesta sería NO_PUBLICABLE, que es otra
    cosa —no es que no haya evidencia, es que no hay corpus servible— y no
    probaría lo que este caso quiere probar.
    """
    cuerpo = cliente_api.post(
        "/v1/respuestas", json={"consulta": "zzzz qwrtpxk nada de esto existe"}
    ).json()
    assert cuerpo["modo"] == "ABSTENCION"
    assert cuerpo["motivo"] == "SIN_EVIDENCIA"
    assert cuerpo["alternativa"], "una abstención sin alternativa deja a la persona sin salida"
    assert cuerpo["data_status"] == "SIN_RESULTADOS"


def test_sin_corte_publicado_no_se_confunde_con_una_abstencion(cliente_api, corpus) -> None:
    """«No tengo con qué» y «no hay nada publicado todavía» no son lo mismo."""
    cuerpo = cliente_api.post("/v1/respuestas", json={"consulta": "apoyo"}).json()
    assert cuerpo["data_status"] == "NO_PUBLICABLE"
    assert cuerpo["release_id"] is None


def test_la_consulta_del_frente_deja_rastro(conexion: Connection, engine_pruebas) -> None:
    """Sin esto la ruta más usada del sistema quedaba como SIN_CLASIFICAR.

    No pasa por la envoltura `Respuesta`, que es la que anota sola; se probó
    contra la anotación directa, que es lo que la ruta hace.
    """
    from backend_normativo.api.contratos import abrir_anotacion, anotar, ultima_respuesta

    hueco = abrir_anotacion()
    anotar(data_status="PUBLICADO", release_id=None, motivo=None, evidencias=3)
    assert ultima_respuesta() is hueco
    assert hueco["data_status"] == "PUBLICADO"
    assert hueco["evidencias"] == 3
    assert hueco["motivo"] is None


def test_el_frente_no_pide_datos_de_identidad(cliente_api) -> None:
    """Lo que no se pide no se puede filtrar."""
    html = cliente_api.get("/consulta").text
    for prohibido in ('type="email"', 'type="tel"', 'name="dni"', 'name="cuil"'):
        assert prohibido not in html


def test_la_jurisdiccion_del_selector_filtra_de_verdad(cliente_api, corpus_publicado) -> None:
    """Un filtro que se ofrece y no se aplica es peor que no ofrecerlo."""
    propia = cliente_api.post(
        "/v1/respuestas", json={"consulta": "beneficiarios", "jurisdiccion": "AR-C"}
    ).json()
    for fuente in propia["fuentes"]:
        assert fuente["jurisdiccion"] == "AR-C"

    # Y pedir otra jurisdicción no devuelve la de al lado como equivalente.
    ajena = cliente_api.post(
        "/v1/respuestas", json={"consulta": "beneficiarios", "jurisdiccion": "AR-B"}
    ).json()
    assert ajena["fuentes"] == []
    assert ajena["modo"] == "ABSTENCION"


def test_vocabularios_no_lee_staging(conexion: Connection) -> None:
    """El lector conversacional accede solo a proyecciones servibles."""
    conexion.execute(text("SET ROLE bn_lector_api"))
    try:
        conexion.execute(text("EXPLAIN SELECT id, nombre, nivel FROM jurisdicciones"))
        conexion.execute(
            text("EXPLAIN SELECT DISTINCT linea FROM beneficios WHERE linea IS NOT NULL")
        )
    finally:
        conexion.execute(text("RESET ROLE"))


def test_la_senal_de_solo_parecido_siempre_viaja(cliente_api, corpus_publicado) -> None:
    """El frente decide con esto si presenta los textos como la respuesta.

    Acá se verifica que el contrato la lleve siempre y que sea booleana; que se
    encienda cuando corresponde se prueba en `test_recuperacion.py`, que es
    donde hay índice semántico construido. Este corpus de API no lo tiene, y una
    prueba que se saltea se cuenta como éxito.
    """
    cuerpo = cliente_api.post(
        "/v1/respuestas", json={"consulta": "asignación universal por hijo"}
    ).json()
    assert isinstance(cuerpo["solo_parecidos"], bool)
    if cuerpo["solo_parecidos"]:
        assert any("usa las palabras que escribiste" in aviso for aviso in cuerpo["avisos"])


def test_la_respuesta_dice_que_hay_publicado(cliente_api, corpus_publicado) -> None:
    """Si alguien pregunta por algo que el corte no cubre, decirle qué cubre.

    Es más útil que devolverle los párrafos más parecidos y callarse. El dato
    ya estaba en la base; lo que faltaba era decirlo.
    """
    cuerpo = cliente_api.post("/v1/respuestas", json={"consulta": "cualquier cosa"}).json()
    assert cuerpo["cobertura"], "un corte publicado siempre cubre alguna norma"
    assert {"norma", "jurisdiccion", "titulo"} <= set(cuerpo["cobertura"][0])


def test_sin_corte_la_cobertura_viaja_vacia_y_no_falta(cliente_api, corpus) -> None:
    """El frente no tiene que adivinar si la clave falta o está vacía."""
    cuerpo = cliente_api.post("/v1/respuestas", json={"consulta": "algo"}).json()
    assert cuerpo["cobertura"] == []
    assert cuerpo["solo_parecidos"] is False


def test_lo_que_es_de_la_cocina_no_llega_a_la_pantalla(cliente_api, corpus_publicado) -> None:
    """El plan lo prohíbe con todas las letras: «sin nombres de tablas o
    detalles del modelo dentro del recorrido ciudadano».

    Antes de esto, alguien que preguntaba si lo podían desalojar podía leer
    «se construye con `bn recuperacion indexar`». Quien opera el servicio
    necesita eso; quien pregunta por sus derechos, no.
    """
    import re

    cuerpo = cliente_api.post("/v1/respuestas", json={"consulta": "prestación"}).json()
    # Las marcas `[[chunk:<id>]]` no se cuentan: son el formato de cita que el
    # contrato exige, y el frente las convierte en «fuente 1». Nadie las ve.
    texto = re.sub(r"\[\[chunk:[^\]]+\]\]", "", cuerpo.get("texto") or "")
    de_la_persona = " ".join([texto, cuerpo.get("alternativa") or "", *cuerpo["avisos"]])
    for jerga in (
        "bn recuperacion",
        "embeddings",
        "índice semántico",
        "proveedor de modelo",
        "semántic",
        "léxic",
        "corpus",
        "Error",
        "None",
    ):
        assert jerga not in de_la_persona, f"«{jerga}» llegó a la pantalla de la persona"
    # Y no se pierde: lo que no va a la persona viaja por su propio canal.
    assert isinstance(cuerpo["notas_operativas"], list)


def test_la_urgencia_viaja_con_la_respuesta(cliente_api, corpus_publicado) -> None:
    """Hay una clase de mensaje donde el canal va primero y la norma después."""
    urgente = cliente_api.post(
        "/v1/respuestas", json={"consulta": "estoy durmiendo en la calle con mi bebé"}
    ).json()
    assert urgente["urgencia"] == {"clase": "NINEZ"}

    normal = cliente_api.post(
        "/v1/respuestas", json={"consulta": "quién puede pedir el subsidio habitacional"}
    ).json()
    assert normal["urgencia"] is None


def test_lo_que_la_persona_conto_no_vuelve_en_la_respuesta(cliente_api, corpus_publicado) -> None:
    """La expresión que disparó la urgencia es un pedazo de su vida.

    Se usa para clasificar y no sale del servidor: la respuesta lleva la clase,
    que es lo que el frente necesita para elegir qué decir.
    """
    cuerpo = cliente_api.post(
        "/v1/respuestas", json={"consulta": "mi pareja me pega y no sé qué hacer"}
    ).json()
    assert cuerpo["urgencia"] == {"clase": "VIOLENCIA"}
    assert "me pega" not in json_str(cuerpo)


def json_str(d) -> str:
    import json

    return json.dumps(d, ensure_ascii=False)


def test_sin_corte_publicado_la_urgencia_igual_se_reconoce(cliente_api, corpus) -> None:
    """Saberlo no puede depender de que la búsqueda encuentre algo.

    Quien escribe «estoy en la calle» necesita lo mismo tanto si el corpus tiene
    una ley de vivienda como si está vacío.
    """
    cuerpo = cliente_api.post(
        "/v1/respuestas", json={"consulta": "estoy durmiendo en la calle"}
    ).json()
    assert cuerpo["data_status"] == "NO_PUBLICABLE"
    assert cuerpo["urgencia"] == {"clase": "CALLE"}


def test_la_pantalla_tiene_un_solo_lugar_para_escribir(cliente_api) -> None:
    """El cuadro de la consulta, y ninguno más.

    La devolución son tres botones, no una caja de comentarios. Una caja de
    texto debajo de una respuesta sobre desalojos o pensiones es exactamente
    donde alguien escribe su caso completo, y eso sí se guardaría. Si algún día
    aparece un segundo campo de escritura en esta pantalla, esta prueba lo tiene
    que ver antes que una persona.
    """
    html = cliente_api.get("/consulta").text
    assert html.count("<textarea") == 1
    assert 'id="pregunta"' in html
    # Ni un campo de texto suelto: el único `input` que hay es el de fecha, que
    # se crea desde el guion cuando alguien pide ver qué decía la norma antes.
    assert '<input type="text"' not in html


def test_la_pantalla_tiene_texto_para_todo_lo_que_el_motor_puede_contestar(cliente_api) -> None:
    """Un resultado sin frase se dibuja como un párrafo vacío.

    Y un párrafo vacío arriba de una lista de condiciones se lee como si el
    sistema no tuviera nada que decir sobre el caso, cuando en realidad lo que
    pasó es que nadie escribió la frase. Pasó con `REQUIERE_DATOS`, que es
    justamente el resultado más frecuente. Esto lo agarra antes.
    """
    from backend_normativo.reglas.evaluacion import ResultadoBeneficio

    pantalla = cliente_api.get("/consulta").text
    bloque = pantalla.split("const RESULTADOS = {", 1)[1].split("};", 1)[0]
    faltan = [r.value for r in ResultadoBeneficio if r.value + ":" not in bloque]
    assert not faltan, f"la pantalla no sabe cómo decir estos resultados: {faltan}"


def test_la_pantalla_no_muestra_el_nombre_interno_de_ningun_campo(cliente_api) -> None:
    """La clave con la que se guarda un hecho no es una pregunta.

    `edad_del_causante` es el modelo de datos. Lo que se muestra es el texto de
    la norma; la clave viaja para poder guardar la respuesta y nunca se pinta.
    """
    pantalla = cliente_api.get("/consulta").text
    # Las dos formas en que se escaparía: pintarla en el repaso o en la pregunta.
    assert "pregunta.campo" in pantalla, "la clave se usa para guardar, eso sí"
    for escape in ("textContent = pregunta.campo", "esc(pregunta.campo)", "esc(clave)"):
        assert escape not in pantalla, f"«{escape}» pondría el modelo de datos en pantalla"


def test_la_pantalla_dice_que_guarda_lo_que_la_persona_confirma(cliente_api) -> None:
    """La promesa vieja dejó de ser cierta y la pantalla tuvo que cambiarla.

    Decía «nada de lo que escribas se guarda». Desde que la conversación
    recuerda los datos confirmados, eso sería mentira, y una promesa de
    privacidad incumplida es peor que no haberla hecho.
    """
    pantalla = cliente_api.get("/consulta").text
    assert "Nada de lo que escribas se guarda" not in pantalla
    assert "Tus mensajes no se guardan" in pantalla
    # Y dice las tres cosas que hacen que la promesa se pueda verificar: qué se
    # guarda, por cuánto y cómo se borra.
    assert "confirmes" in pantalla
    assert "media hora" in pantalla and "dos horas" in pantalla
    assert "Borrar estos datos" in pantalla
