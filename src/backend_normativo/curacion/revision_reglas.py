"""HU-036: el circuito de revisión de las reglas curadas.

Las reglas nacen candidatas y la evaluación no las usa hasta que alguien con
competencia jurídica las aprueba. Faltaba la otra mitad: no había forma de
aprobarlas. `bn revision aprobar-campos` mueve afirmaciones, no reglas, así que
las ciento cincuenta y cuatro reglas curadas estaban condenadas a quedarse en
CANDIDATE por ausencia de un comando, no por falta de revisión.

Acá está el circuito, y está pensado para que revisar sea posible y no
declarativo:

- `expediente` arma, regla por regla, lo que hay que decidir: el texto literal,
  qué afirma la lectura, si tiene condición ejecutable, y la pregunta concreta
  que la curaduría dejó escrita. Sin eso, «revisar 154 reglas» es una tarea sin
  forma que nadie empieza.
- `marcar_en_revision` mueve de CANDIDATE a IN_REVIEW. No aprueba nada y no
  sirve nada: dice que la regla ya fue mirada y espera decisión.
- `aprobar` y `rechazar` exigen actor y fundamento, y quedan en la bitácora. Es
  lo único que convierte una lectura curada en derecho aplicable, y por eso es
  lo único que este módulo no hace solo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import EstadoRevision


class ConflictoDeRevision(Exception):
    """La regla cambió desde que quien decide la leyó.

    Es distinto de una transición inválida: no está mal pedida, está pedida
    sobre una versión que ya no es. Quien decidió primero no puede ser
    sobrescrito por quien todavía miraba la pantalla vieja.
    """


class RevisionInvalida(Exception):
    """La transición pedida no corresponde al estado en que está la regla."""


# Las categorías que no describen a una persona sino al reparto entre personas,
# a una facultad de la autoridad o a la forma de la prestación. Aprobarlas como
# condición de acceso las convierte en un requisito que la norma no puso.
CATEGORIAS_QUE_NO_SON_CONDICION = frozenset(
    {"PRIORIDAD", "SALVAGUARDA", "SUBSANACION", "REHABILITACION"}
)


@dataclass
class ReglaEnRevision:
    id: uuid.UUID
    beneficio: str
    categoria: str
    estado: str
    texto_literal: str
    descripcion: str
    tiene_condicion: bool
    requiere_revision: bool
    motivo_revision: str
    norma: str
    ruta: str
    parametro_sin_valor: bool = False

    @property
    def clase(self) -> str:
        """En qué pila cae, según hechos observables y no según el texto del motivo.

        Clasificar por lo que se puede mirar —si tiene condición, si su umbral
        tiene valor, de qué categoría es— y no por lo que dice el motivo evita
        que la pila dependa de cómo se redactó el reparo. Y las pilas importan
        porque el riesgo de aprobar no es el mismo en todas.
        """
        if not self.tiene_condicion:
            if self.categoria in CATEGORIAS_QUE_NO_SON_CONDICION:
                return "NO_ES_CONDICION_SOBRE_LA_PERSONA"
            return "SIN_CONDICION_EJECUTABLE"
        if self.parametro_sin_valor:
            return "CONDICION_CON_UMBRAL_SIN_VALOR"
        if self.categoria in CATEGORIAS_QUE_NO_SON_CONDICION:
            return "CONDICION_EN_CATEGORIA_QUE_NO_DECIDE_ACCESO"
        return "CONDICION_EJECUTABLE"

    @property
    def que_hay_que_decidir(self) -> str:
        """La pregunta concreta, no la etiqueta.

        Una regla sin condición ejecutable y una con condición esperando
        confirmación no plantean lo mismo, y mandarlas a la misma pila hace que
        la segunda se apruebe sin mirar y la primera se apruebe sin poder.
        """
        if self.motivo_revision:
            return self.motivo_revision
        if not self.tiene_condicion:
            return (
                "No tiene condición ejecutable ni motivo declarado. Antes de aprobarla hay que "
                "decidir si la condición se puede escribir o si la regla es informativa."
            )
        return (
            "Tiene condición ejecutable y la curaduría no dejó reparos. Aprobarla la habilita "
            "para la evaluación: hay que confirmar que la condición dice lo que dice la norma."
        )


@dataclass
class ResultadoRevision:
    reglas: list[ReglaEnRevision] = field(default_factory=list)
    por_estado: dict[str, int] = field(default_factory=dict)

    @property
    def sin_condicion(self) -> int:
        return sum(1 for r in self.reglas if not r.tiene_condicion)

    @property
    def sin_ubicar(self) -> int:
        """Reglas cuya evidencia no dice a qué unidad del texto mirar."""
        return sum(1 for r in self.reglas if not r.ruta)

    @property
    def por_categoria(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for regla in self.reglas:
            cuenta[regla.categoria] = cuenta.get(regla.categoria, 0) + 1
        return dict(sorted(cuenta.items()))


CONSULTA = """
SELECT r.id, b.codigo AS beneficio, r.categoria, r.estado_revision AS estado,
       r.texto_literal, r.descripcion, (r.ast IS NOT NULL) AS tiene_condicion,
       r.requiere_revision, coalesce(r.alcance, '') AS motivo_revision,
       coalesce(n.tipo || ' ' || n.numero || '/' || n.anio::text, '—') AS norma,
       coalesce(u.ruta, e.selector, '') AS ruta,
       EXISTS (
         SELECT 1 FROM regla_parametros rp
          WHERE rp.regla_id = r.id
            AND NOT EXISTS (SELECT 1 FROM parametro_valores pv
                             WHERE pv.parametro_id = rp.parametro_id)
       ) AS parametro_sin_valor
  FROM reglas r
  JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id
  JOIN beneficios b ON b.id = bv.beneficio_id
  LEFT JOIN evidencias e ON e.id = r.evidencia_id
  -- La unidad es lo que localiza de verdad. El `selector` lo escribe quien crea
  -- la evidencia y una reusada por otro curador puede no traerlo: dos de cada
  -- tres reglas quedaban sin decir a qué artículo mirar, que es lo primero que
  -- necesita quien revisa.
  LEFT JOIN unidades_documentales u ON u.id = e.unidad_id
  LEFT JOIN documento_versiones dv ON dv.id = e.doc_version_id
  LEFT JOIN norma_versiones nv ON nv.doc_version_id = dv.id
  LEFT JOIN normas n ON n.id = nv.norma_id
 WHERE (CAST(:estado AS text) IS NULL OR r.estado_revision = :estado)
   AND (CAST(:beneficio AS text) IS NULL OR b.codigo = :beneficio)
 ORDER BY b.codigo, r.categoria, r.texto_literal
"""


@dataclass
class ExpedienteDeRegla:
    """Todo lo que hay que tener a la vista para decidir sobre una regla.

    El criterio pide seis cosas juntas: literal, interpretación, condición,
    dependencias, vigencia y controles. Juntas y no en seis pantallas: una
    condición se aprueba o no según de qué depende y sobre qué versión rige, y
    pedirle a quien revisa que las cruce a mano es pedirle que no las cruce.
    """

    regla: ReglaEnRevision
    ast: dict | None = None
    dependencias: list[dict] = field(default_factory=list)
    parametros: list[dict] = field(default_factory=list)
    vigencia: dict | None = None
    controles: list[dict] = field(default_factory=list)


def detalle(conexion: Connection, regla_id: uuid.UUID) -> ExpedienteDeRegla:
    """El expediente de una sola regla, con lo que cuelga de ella."""
    # Se reusa la consulta del expediente en vez de escribir otra: dos consultas
    # que tienen que decir lo mismo terminan diciendo cosas distintas.
    una_regla = CONSULTA.replace(
        "WHERE (CAST(:estado AS text)",
        "WHERE (r.id = :regla) AND (CAST(:estado AS text)",
    )
    fila = (
        conexion.execute(
            text(una_regla),
            {"estado": None, "beneficio": None, "regla": regla_id},
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise RevisionInvalida(f"No hay ninguna regla con id {regla_id}.")

    regla = ReglaEnRevision(
        id=fila["id"],
        beneficio=fila["beneficio"],
        categoria=fila["categoria"],
        estado=fila["estado"],
        texto_literal=fila["texto_literal"],
        descripcion=fila["descripcion"] or "",
        tiene_condicion=bool(fila["tiene_condicion"]),
        requiere_revision=bool(fila["requiere_revision"]),
        motivo_revision=fila["motivo_revision"],
        norma=fila["norma"],
        ruta=fila["ruta"],
        parametro_sin_valor=bool(fila["parametro_sin_valor"]),
    )
    expediente_ = ExpedienteDeRegla(regla=regla)

    expediente_.ast = conexion.execute(
        text("SELECT ast FROM reglas WHERE id = :id"), {"id": regla_id}
    ).scalar_one_or_none()

    expediente_.dependencias = [
        dict(f)
        for f in conexion.execute(
            text(
                "SELECT rd.tipo, rd.regla_referida_id, r2.categoria, r2.estado_revision, "
                "       r2.texto_literal "
                "  FROM regla_dependencias rd "
                "  JOIN reglas r2 ON r2.id = rd.regla_referida_id "
                " WHERE rd.regla_id = :id ORDER BY r2.categoria"
            ),
            {"id": regla_id},
        ).mappings()
    ]

    expediente_.parametros = [
        dict(f)
        for f in conexion.execute(
            text(
                "SELECT p.codigo, p.concepto, p.unidad, rp.rol, "
                "       EXISTS (SELECT 1 FROM parametro_valores pv "
                "                WHERE pv.parametro_id = p.id) AS tiene_valor "
                "  FROM regla_parametros rp JOIN parametros p ON p.id = rp.parametro_id "
                " WHERE rp.regla_id = :id ORDER BY p.codigo"
            ),
            {"id": regla_id},
        ).mappings()
    ]

    fila_vigencia = (
        conexion.execute(
            text(
                "SELECT rv.estado_revision, rv.valid_tipo, rv.valid_desde, rv.valid_hasta, "
                "       rv.known_desde, rv.known_hasta, rv.release_id IS NOT NULL AS publicada "
                "  FROM reglas r "
                "  JOIN registro_versiones rv ON rv.id = r.beneficio_version_id "
                " WHERE r.id = :id"
            ),
            {"id": regla_id},
        )
        .mappings()
        .first()
    )
    expediente_.vigencia = dict(fila_vigencia) if fila_vigencia else None

    expediente_.controles = [
        dict(f)
        for f in conexion.execute(
            text(
                "SELECT cc.control_id, cc.resultado, cc.severidad, cc.observado "
                "  FROM controles_calidad cc "
                "  JOIN reglas r ON r.beneficio_version_id = cc.registro_version_id "
                " WHERE r.id = :id ORDER BY cc.ejecutado_en DESC LIMIT 20"
            ),
            {"id": regla_id},
        ).mappings()
    ]
    return expediente_


def expediente(
    conexion: Connection,
    *,
    estado: str | None = EstadoRevision.CANDIDATE.value,
    beneficio: str | None = None,
) -> ResultadoRevision:
    """Lo que hay que decidir, regla por regla."""
    resultado = ResultadoRevision()
    for fila in conexion.execute(
        text(CONSULTA), {"estado": estado, "beneficio": beneficio}
    ).mappings():
        resultado.reglas.append(
            ReglaEnRevision(
                id=fila["id"],
                beneficio=fila["beneficio"],
                categoria=fila["categoria"],
                estado=fila["estado"],
                texto_literal=fila["texto_literal"],
                descripcion=fila["descripcion"] or "",
                tiene_condicion=bool(fila["tiene_condicion"]),
                requiere_revision=bool(fila["requiere_revision"]),
                motivo_revision=fila["motivo_revision"],
                norma=fila["norma"],
                ruta=fila["ruta"],
                parametro_sin_valor=bool(fila["parametro_sin_valor"]),
            )
        )
    for fila in conexion.execute(text("SELECT estado_revision, count(*) FROM reglas GROUP BY 1")):
        resultado.por_estado[fila[0]] = fila[1]
    return resultado


def _mover(
    conexion: Connection,
    regla_id: uuid.UUID,
    *,
    desde: tuple[str, ...],
    hasta: str,
    actor: str,
    fundamento: str,
    accion: str,
    estado_esperado: str | None = None,
) -> None:
    estado = conexion.execute(
        text("SELECT estado_revision FROM reglas WHERE id = :id"), {"id": regla_id}
    ).scalar_one_or_none()
    if estado is None:
        raise RevisionInvalida(f"No hay ninguna regla con id {regla_id}.")
    # Concurrencia optimista: quien decide declara en qué estado la leyó. Sin
    # esto, dos revisiones simultáneas se distinguen solo por cuál llegó
    # primero, y la segunda recibe un error de transición que parece un error
    # suyo cuando en realidad alguien ya decidió.
    if estado_esperado is not None and estado != estado_esperado:
        raise ConflictoDeRevision(
            f"La regla estaba en {estado_esperado} cuando se la leyó y ahora está en "
            f"{estado}: alguien decidió antes. La decisión no se aplica; hay que volver "
            "a leerla y decidir sobre lo que hay."
        )
    if estado not in desde:
        raise RevisionInvalida(
            f"La regla está en {estado} y esta transición sale de {' o '.join(desde)}. "
            "Los estados no se saltean: cada uno dice quién la miró y hasta dónde."
        )
    conexion.execute(
        text("UPDATE reglas SET estado_revision = :e WHERE id = :id"),
        {"e": hasta, "id": regla_id},
    )
    if hasta == EstadoRevision.APPROVED.value:
        _marcar_ejecutable(conexion, regla_id)
    conexion.execute(
        text(
            "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
            "VALUES (:actor, :accion, 'reglas', :id, :motivo)"
        ),
        {"actor": actor, "accion": accion, "id": str(regla_id), "motivo": fundamento},
    )


def _marcar_ejecutable(conexion: Connection, regla_id: uuid.UUID) -> bool:
    """Aprobar una regla con árbol validado es lo que la vuelve ejecutable.

    Estaban separadas y no debían estarlo. El motor decide con
    `ast is not None and not requiere_revision`, y nada bajaba esa marca: se
    podían aprobar las 166 reglas del expediente y el evaluador seguía
    contestando DESCONOCIDO en todas, con el motivo «la regla está marcada como
    pendiente de revisión». Aprobado y pendiente de revisión a la vez.

    Ninguna prueba lo veía porque cada mitad estaba bien por su cuenta: la
    transición de estados dejaba su rastro y el motor respetaba la marca. Lo que
    faltaba era que una cosa moviera la otra. El plan lo nombra en §02 como
    «hacer coherente aprobar con la marca de revisión».

    Una regla sin árbol no se toca: sin condición ejecutable no hay nada que
    ejecutar, y la restricción `ck_reglas_ejecutable_solo_tras_validacion` de la
    base dice lo mismo.
    """
    marcadas = conexion.execute(
        text(
            "UPDATE reglas SET requiere_revision = false "
            " WHERE id = :id AND ast IS NOT NULL AND requiere_revision "
            "RETURNING id"
        ),
        {"id": regla_id},
    ).scalar_one_or_none()
    return marcadas is not None


@dataclass(frozen=True)
class Habilitacion:
    """Qué quedó ejecutable y qué no, después de habilitar el expediente."""

    habilitadas: int
    sin_condicion: int
    ya_estaban: int

    def a_dict(self) -> dict:
        return {
            "habilitadas": self.habilitadas,
            "sin_condicion_ejecutable": self.sin_condicion,
            "ya_estaban_habilitadas": self.ya_estaban,
        }


def habilitar_aprobadas(
    conexion: Connection, *, actor: str, fundamento: str, beneficio: str | None = None
) -> Habilitacion:
    """Vuelve ejecutables las reglas que ya estaban aprobadas.

    Existe porque las 166 del expediente se aprobaron antes de que aprobar
    bajara la marca, y quedaron aprobadas y sin poder ejecutarse. Repetir la
    aprobación no serviría: `_mover` sale de CANDIDATE o IN_REVIEW y esas ya
    están en APPROVED.

    No es una aprobación: no cambia el estado de revisión de ninguna regla ni
    decide nada sobre su contenido. Toma lo que alguien ya aprobó y lo conecta
    al motor. Aun así exige actor y fundamento, y deja un evento por regla: lo
    que se hace de una vez tiene que poder auditarse una por una, y dentro de
    seis meses la pregunta va a ser quién decidió que estas reglas empezaran a
    contestarle a la gente.

    Las que no tienen árbol quedan afuera y se informan: son las que el plan
    manda clasificar entre formalizables, informativas y sin evidencia (P-010,
    criterio 2), y ese trabajo no lo reemplaza este comando.
    """
    if not fundamento.strip():
        raise RevisionInvalida(
            "Habilitar el expediente sin fundamento deja sin explicación el momento en que "
            "el servicio empezó a evaluar condiciones. Es la decisión que hay que poder "
            "reconstruir."
        )
    filtro = " AND b.codigo = :c" if beneficio else ""
    filas = (
        conexion.execute(
            text(
                "SELECT r.id, r.ast IS NOT NULL AS tiene_ast, r.requiere_revision "
                "  FROM reglas r "
                "  JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id "
                "  JOIN beneficios b ON b.id = bv.beneficio_id "
                f" WHERE r.estado_revision = 'APPROVED'{filtro}"
            ),
            {"c": beneficio} if beneficio else {},
        )
        .mappings()
        .all()
    )
    habilitadas = sin_condicion = ya_estaban = 0
    for fila in filas:
        if not fila["tiene_ast"]:
            sin_condicion += 1
            continue
        if not fila["requiere_revision"]:
            ya_estaban += 1
            continue
        _marcar_ejecutable(conexion, fila["id"])
        conexion.execute(
            text(
                "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
                "VALUES (:actor, 'HABILITAR_REGLA', 'reglas', :id, :motivo)"
            ),
            {"actor": actor, "id": str(fila["id"]), "motivo": fundamento},
        )
        habilitadas += 1
    return Habilitacion(habilitadas=habilitadas, sin_condicion=sin_condicion, ya_estaban=ya_estaban)


def marcar_en_revision(
    conexion: Connection,
    regla_id: uuid.UUID,
    *,
    actor: str,
    fundamento: str,
    estado_esperado: str | None = None,
) -> None:
    """Deja constancia de que la regla ya fue mirada y espera decisión.

    No aprueba ni sirve nada. Existe porque «candidata» y «analizada y a la
    espera» son cosas distintas, y meterlas en la misma pila hace que una
    revisión de ciento cincuenta reglas no tenga por dónde empezar la segunda
    vez.
    """
    _mover(
        conexion,
        regla_id,
        desde=(EstadoRevision.CANDIDATE.value,),
        hasta=EstadoRevision.IN_REVIEW.value,
        actor=actor,
        fundamento=fundamento,
        accion="REGLA_EN_REVISION",
        estado_esperado=estado_esperado,
    )


def aprobar(
    conexion: Connection,
    regla_id: uuid.UUID,
    *,
    actor: str,
    fundamento: str,
    estado_esperado: str | None = None,
) -> None:
    """Convierte una lectura curada en regla aplicable.

    Es la única transición que habilita a la evaluación a usarla, así que exige
    quién y por qué, y las dos cosas quedan en la bitácora. Que lo haya escrito
    una curaduría no lo vuelve derecho aplicable; que lo apruebe alguien con
    competencia, sí.
    """
    if not fundamento.strip():
        raise RevisionInvalida(
            "Aprobar una regla sin fundamento deja una decisión sin razón escrita. Dentro de "
            "seis meses nadie puede saber si se revisó o se aprobó de apuro."
        )
    _mover(
        conexion,
        regla_id,
        desde=(EstadoRevision.CANDIDATE.value, EstadoRevision.IN_REVIEW.value),
        hasta=EstadoRevision.APPROVED.value,
        actor=actor,
        fundamento=fundamento,
        accion="APROBAR_REGLA",
        estado_esperado=estado_esperado,
    )


def rechazar(
    conexion: Connection,
    regla_id: uuid.UUID,
    *,
    actor: str,
    fundamento: str,
    estado_esperado: str | None = None,
) -> None:
    """Descarta una regla: la lectura afirmaba algo que la norma no dice."""
    if not fundamento.strip():
        raise RevisionInvalida("Rechazar una regla sin fundamento no explica qué estaba mal.")
    _mover(
        conexion,
        regla_id,
        desde=(EstadoRevision.CANDIDATE.value, EstadoRevision.IN_REVIEW.value),
        hasta=EstadoRevision.REJECTED.value,
        actor=actor,
        fundamento=fundamento,
        accion="RECHAZAR_REGLA",
        estado_esperado=estado_esperado,
    )


def aprobar_beneficio(
    conexion: Connection, codigo: str, *, actor: str, fundamento: str
) -> list[uuid.UUID]:
    """Aprueba de una vez las reglas candidatas de un beneficio.

    Una persona revisa un beneficio entero —sus reglas se leen juntas porque se
    aplican juntas— y firma una vez. Obligarla a ciento cincuenta invocaciones
    no hace la revisión más cuidadosa: hace que no se haga, o que se haga con un
    bucle que nadie mira.

    Cada regla igual deja su propio evento en la bitácora, con el mismo actor y
    el mismo fundamento: lo que se firma una vez tiene que poder auditarse una
    por una.
    """
    if not fundamento.strip():
        raise RevisionInvalida(
            "Aprobar sin fundamento deja una decisión sin razón escrita. Dentro de seis meses "
            "nadie puede saber si se revisó o se aprobó de apuro."
        )
    reglas = (
        conexion.execute(
            text(
                "SELECT r.id FROM reglas r "
                "  JOIN beneficio_versiones bv ON bv.registro_version_id = r.beneficio_version_id "
                "  JOIN beneficios b ON b.id = bv.beneficio_id "
                " WHERE b.codigo = :c AND r.estado_revision IN ('CANDIDATE', 'IN_REVIEW')"
            ),
            {"c": codigo},
        )
        .scalars()
        .all()
    )
    if not reglas:
        raise RevisionInvalida(
            f"El beneficio {codigo!r} no tiene reglas candidatas ni en revisión. O el código "
            "está mal escrito, o ya se aprobaron: `bn revision reglas --estado todos` lo dice."
        )
    for regla_id in reglas:
        aprobar(conexion, regla_id, actor=actor, fundamento=fundamento)
    return list(reglas)


# La propuesta de cada pila. No es la firma: es el trabajo previo a la firma,
# hecho para que revisar ciento cincuenta y cuatro reglas sea decidir ocho cosas
# y repartir, en vez de empezar de cero ciento cincuenta y cuatro veces.
PROPUESTAS: dict[str, tuple[str, str]] = {
    "CONDICION_EJECUTABLE": (
        "Aprobar tras confirmar la condición contra el texto",
        "Tienen su condición escrita y validada, y su umbral tiene valor. Lo que queda es lo "
        "único que una máquina no puede hacer: leer el artículo citado y confirmar que la "
        "condición dice lo mismo. Es la pila donde aprobar habilita respuestas afirmativas, "
        "así que es la que hay que leer con más cuidado y la que más devuelve.",
    ),
    "CONDICION_CON_UMBRAL_SIN_VALOR": (
        "Aprobar: mientras el parámetro no tenga valor, la regla contesta «no se sabe»",
        "La condición está escrita y compara contra un parámetro que todavía no tiene valor "
        "aprobado —el salario mínimo del convenio de comercio, el sueldo mínimo municipal—. "
        "Aprobarlas es de bajo riesgo justamente por eso: sin valor, la evaluación devuelve "
        "desconocido, que es la respuesta correcta, y no «no calificás». Dejarlas candidatas "
        "no protege de nada y esconde condiciones que sí están bien leídas. Lo que hay que "
        "decidir aparte, y con evidencia, es el valor del parámetro.",
    ),
    "SIN_CONDICION_EJECUTABLE": (
        "No aprobar todavía: primero decidir si la condición se puede escribir",
        "No tienen condición ejecutable porque la norma remite a una reglamentación que no "
        "está en el corpus, porque el dato que harían falta no existe en el modelo, o porque "
        "lo que dicen no se puede reducir a verdadero o falso. Aprobarlas no habilita nada "
        "—no hay qué evaluar— y sí las presenta como revisadas. Cada una necesita una de tres "
        "decisiones: se puede escribir la condición, hay que traer la norma que falta, o la "
        "regla es informativa y se conserva sin condición.",
    ),
    "NO_ES_CONDICION_SOBRE_LA_PERSONA": (
        "No aprobar como condición de acceso: describen otra cosa",
        "Prioridades, salvaguardas, subsanaciones y rehabilitaciones no dicen si alguien "
        "accede: dicen cómo se reparte un cupo, qué pasa cuando nadie pidió el beneficio, o "
        "cómo se recupera. Aprobarlas como condición de aplicabilidad las convertiría en un "
        "requisito que la norma no puso, y son justamente las que evitan que la falta de "
        "solicitud se lea como falta de derecho. Hay que decidir cómo las representa el "
        "modelo, y esa es una decisión de diseño antes que jurídica.",
    ),
    "CONDICION_EN_CATEGORIA_QUE_NO_DECIDE_ACCESO": (
        "Revisar la categoría antes que la condición",
        "Tienen condición escrita pero están en una categoría que no decide acceso. O la "
        "categoría está mal puesta y la condición sirve, o la categoría está bien y la "
        "condición no debería evaluarse como aplicabilidad. Es un caso por caso corto.",
    ),
}


def formatear(resultado: ResultadoRevision) -> str:
    """El expediente, para que revisar tenga forma de tarea y no de intención."""
    lineas = [
        "# Expediente de revisión de reglas",
        "",
        "Las reglas curadas nacen candidatas y la evaluación no las usa hasta que alguien",
        "con competencia jurídica las aprueba. Este documento es lo que esa persona",
        "necesita para poder hacerlo: cada regla con su texto literal, qué afirma la",
        "lectura y la pregunta concreta que hay que contestar.",
        "",
        "Se genera con `bn revision reglas`. No aprueba nada: aprobar es",
        "`bn revision aprobar-regla`, que exige actor y fundamento y los deja en la",
        "bitácora.",
        "",
        "## Estado",
        "",
        "| Estado | Reglas |",
        "| --- | ---: |",
    ]
    for estado, cuantas in sorted(resultado.por_estado.items()):
        lineas.append(f"| {estado} | {cuantas} |")
    lineas += [
        "",
        f"En este expediente: **{len(resultado.reglas)}** regla(s), de las cuales "
        f"**{resultado.sin_condicion}** no tienen condición ejecutable. Esas dos pilas no se "
        "revisan igual: una condición escrita se confirma contra el texto, y una regla sin "
        "condición hay que decidir si se puede escribir o si es informativa.",
        "",
        "| Categoría | Reglas |",
        "| --- | ---: |",
    ]
    for categoria, cuantas in resultado.por_categoria.items():
        lineas.append(f"| {categoria} | {cuantas} |")
    if resultado.sin_ubicar:
        lineas += [
            "",
            f"**{resultado.sin_ubicar}** regla(s) no dicen a qué unidad del texto mirar: su "
            "evidencia no localiza una unidad. Revisarlas exige buscar el artículo a mano, así "
            "que conviene resolverlo antes de empezar.",
        ]
    lineas.append("")

    por_clase: dict[str, list[ReglaEnRevision]] = {}
    for regla in resultado.reglas:
        por_clase.setdefault(regla.clase, []).append(regla)
    if por_clase:
        lineas += [
            "",
            "## Propuesta de disposición, por pila",
            "",
            "Las ciento cincuenta y cuatro reglas no plantean ciento cincuenta y cuatro",
            "preguntas distintas: plantean unas pocas, repetidas. Agruparlas por lo que hay",
            "que decidir convierte la revisión en decidir esas pocas y repartir, que es como",
            "se trabaja de verdad.",
            "",
            "Esto es una **propuesta**, no una aprobación. Aprobar es afirmar que lo que el",
            "backend contesta es lo que dice el derecho, y eso lo firma una persona con",
            "competencia jurídica, con su nombre y su fundamento en la bitácora.",
            "",
        ]
        for clase, reglas in sorted(por_clase.items(), key=lambda x: -len(x[1])):
            titulo, razon = PROPUESTAS.get(clase, (clase, ""))
            lineas += [
                f"### {clase} · {len(reglas)} regla(s)",
                "",
                f"**Propuesta: {titulo}.** {razon}",
                "",
                "Beneficios alcanzados: " + ", ".join(sorted({r.beneficio for r in reglas})) + ".",
                "",
            ]

    beneficio = None
    for regla in resultado.reglas:
        if regla.beneficio != beneficio:
            beneficio = regla.beneficio
            lineas += ["", f"## {beneficio}", ""]
        lineas += [
            f"### `{regla.id}` · {regla.categoria}",
            "",
            f"**Norma:** {regla.norma} · **Unidad:** `{regla.ruta or '—'}` · "
            f"**Estado:** {regla.estado} · "
            f"**Condición ejecutable:** {'sí' if regla.tiene_condicion else 'no'}",
            "",
            f"> {regla.texto_literal}",
            "",
            f"**La lectura afirma:** {regla.descripcion}",
            "",
            f"**Qué hay que decidir:** {regla.que_hay_que_decidir}",
            "",
        ]
    return "\n".join(lineas) + "\n"
