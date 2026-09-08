"""HU-011, HU-013 y HU-017: cargar un beneficio desde una lectura curada.

La lectura vive en `docs/curaduria/*.json` y no en este módulo a propósito. Lo
que dice una ley sobre quién accede y con qué condiciones es una interpretación
jurídica, y una interpretación tiene que poder discutirse contra el texto sin
leer Python. Acá está el mecanismo; allá, la lectura.

Tres cosas que el cargador impone y que son la razón de que exista:

* **Cada afirmación apunta a su artículo.** Toda regla, población y cuantía
  nace atada a la unidad documental que la sostiene. Una condición de acceso
  sin evidencia es una condición que el sistema inventó.
* **Nada entra aprobado.** Todo queda CANDIDATE. La evaluación de un beneficio
  decide si alguien puede pedir algo; que la haya escrito una curaduría no la
  vuelve derecho aplicable.
* **Lo que la ley remite a la reglamentación no se completa.** Cuando el texto
  dice «según lo establezca la reglamentación», la regla se carga con su texto
  literal, sin AST, y marcada para revisión. Formalizar lo que la norma no
  dijo es la manera más rápida de que el sistema afirme algo que ninguna
  autoridad dispuso.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EntidadVersionada,
    EstadoRevision,
    Severidad,
    TipoEvidencia,
    TipoIncidencia,
    ValidTipo,
)
from backend_normativo.plazos.calendarios import derivar_jurisdiccional
from backend_normativo.reglas.ast import ErrorDeContrato, validar_ast

RUTA_CURADURIA = pathlib.Path("docs/curaduria")


class LecturaInvalida(Exception):
    """La lectura curada no se puede cargar tal como está."""


@dataclass
class ResultadoCuracion:
    beneficio_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    poblaciones: int = 0
    reglas: int = 0
    reglas_sin_formalizar: int = 0
    cuantias: int = 0
    plazos: int = 0
    campos_no_informados: int = 0
    dependencias: int = 0
    avisos: list[str] = field(default_factory=list)


class CuradorDeBeneficios:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def cargar(self, ruta: pathlib.Path) -> ResultadoCuracion:
        lectura = json.loads(ruta.read_text(encoding="utf-8"))
        resultado = ResultadoCuracion()

        doc_version_id, norma_version_id = self._version_de_la_norma(lectura["norma"])
        unidades = self._unidades(doc_version_id)

        beneficio_id = self._beneficio(lectura["beneficio"])
        version_id = self._version_de_beneficio(beneficio_id, lectura["beneficio"])
        resultado.beneficio_id = beneficio_id
        resultado.version_id = version_id

        self._atar_a_la_norma(
            version_id,
            norma_version_id,
            lectura["norma"],
            self._evidencia(doc_version_id, unidades, lectura["beneficio"]["ruta_evidencia"]),
        )

        for poblacion in lectura.get("poblaciones", ()):
            self._poblacion(version_id, poblacion, doc_version_id, unidades)
            resultado.poblaciones += 1

        claves: dict[str, uuid.UUID] = {}
        for regla in lectura.get("reglas", ()):
            regla_id, sin_formalizar = self._regla(version_id, regla, doc_version_id, unidades)
            claves[regla["clave"]] = regla_id
            resultado.reglas += 1
            resultado.reglas_sin_formalizar += int(sin_formalizar)
        self._dependencias_entre_reglas(lectura.get("reglas", ()), claves)
        self._retirar_reglas_que_la_lectura_ya_no_tiene(
            version_id, lectura.get("reglas", ()), resultado
        )

        if lectura.get("cuantia"):
            self._cuantia(version_id, lectura["cuantia"], doc_version_id, unidades)
            resultado.cuantias += 1

        for plazo in lectura.get("plazos", ()):
            self._plazo(version_id, norma_version_id, plazo, doc_version_id, unidades)
            resultado.plazos += 1

        for campo in lectura.get("campos_no_informados", ()):
            self._campo_no_informado(norma_version_id, campo)
            resultado.campos_no_informados += 1

        for dependencia in lectura.get("dependencias", ()):
            self._dependencia(lectura["norma"]["referencia"], dependencia)
            resultado.dependencias += 1

        self._avisos(lectura, resultado)
        return resultado

    # --- Anclaje en la norma -------------------------------------------------

    def _version_de_la_norma(self, norma: dict) -> tuple[uuid.UUID, uuid.UUID]:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT dv.id AS doc_version_id, nv.registro_version_id "
                    "  FROM documento_versiones dv "
                    "  JOIN documentos d ON d.id = dv.documento_id "
                    "  JOIN norma_versiones nv ON nv.doc_version_id = dv.id "
                    " WHERE d.external_id = :e ORDER BY dv.version DESC LIMIT 1"
                ),
                {"e": norma["external_id"]},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise LecturaInvalida(
                f"No hay una versión normativa para {norma['external_id']}. La lectura curada "
                "se apoya en el texto capturado: sin ese texto no hay nada que citar."
            )
        return fila["doc_version_id"], fila["registro_version_id"]

    def _unidades(self, doc_version_id: uuid.UUID) -> dict[str, dict]:
        return {
            fila["ruta"]: dict(fila)
            for fila in self.conexion.execute(
                text(
                    "SELECT id, ruta, texto FROM unidades_documentales  WHERE doc_version_id = :d"
                ),
                {"d": doc_version_id},
            ).mappings()
        }

    @staticmethod
    def _verificar_cita(unidades: dict[str, dict], ruta: str, literal: str, quien: str) -> None:
        """La cita tiene que estar en la unidad que dice citar.

        Una afirmación cuya evidencia apunta a un texto que no la dice es peor
        que una afirmación sin evidencia: parece verificada. Esto no revisa que
        la lectura jurídica sea correcta —eso lo hace una persona—, revisa lo
        único que una máquina puede revisar sola, que es que el texto citado
        exista donde se dice que existe.

        Se comparan los espacios normalizados: el boletín corta las líneas donde
        le queda y eso no cambia lo que dice. Cualquier otra diferencia sí: si la
        cita resume, elide con puntos suspensivos o corrige una errata de la
        fuente, deja de ser una cita del texto capturado y falla acá.
        """
        unidad = unidades.get(ruta)
        if unidad is None:
            return  # `_evidencia` da un error mejor para una ruta que no existe.
        buscado = " ".join(literal.split())
        if buscado in " ".join(unidad["texto"].split()):
            return
        # Decir dónde sí está ahorra la búsqueda a mano y, sobre todo, distingue
        # los dos casos: la cita se movió de unidad porque cambió la
        # segmentación, o la cita no está en ninguna parte del texto.
        donde = sorted(r for r, u in unidades.items() if buscado in " ".join(u["texto"].split()))
        pista = (
            f" El texto sí está en {donde[0]!r}."
            if donde
            else " El texto no está en ninguna unidad."
        )
        raise LecturaInvalida(
            f"{quien}: el texto citado no está en la unidad {ruta!r}.{pista} La evidencia apunta "
            "a un fragmento que no dice lo que se afirma. Si la cita resume o elide, hay que "
            "citar el fragmento continuo que sí está; si la fuente publica una errata, se cita "
            "con la errata: lo capturado es lo único contra lo que se puede verificar."
        )

    def _evidencia(
        self, doc_version_id: uuid.UUID, unidades: dict[str, dict], ruta: str
    ) -> uuid.UUID:
        unidad = unidades.get(ruta)
        if unidad is None:
            raise LecturaInvalida(
                f"La lectura cita la unidad {ruta!r} y esa ruta no existe en el texto "
                f"capturado. Rutas disponibles de primer nivel: "
                f"{sorted(r for r in unidades if '/' not in r)[:12]}"
            )
        # Una unidad puede tener más de una evidencia: la curación de
        # equivalencias y la de anexos también citan unidades, con su propio
        # selector. Se toma la más antigua para que la elección no dependa del
        # orden en que se hayan cargado.
        ya = self.conexion.execute(
            text(
                "SELECT id FROM evidencias WHERE doc_version_id = :d AND unidad_id = :u "
                " ORDER BY creado_en, id LIMIT 1"
            ),
            {"d": doc_version_id, "u": unidad["id"]},
        ).scalar_one_or_none()
        if ya is not None:
            # Se reusa: una unidad tiene una evidencia, no una por cada quien la
            # cite. Si viene de una pasada anterior y no trae `selector`, se deja
            # como está. La evidencia es inmutable por diseño y el intento de
            # completarle el localizador terminó en el error que corresponde: lo
            # que localiza es `unidad_id`, que es más preciso que un texto.
            return ya
        fragmento = unidad["texto"]
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, selector, tipo, "
                " hash_fragmento) VALUES (:d, :u, :f, :s, :t, :h) RETURNING id"
            ),
            {
                "d": doc_version_id,
                "u": unidad["id"],
                "f": fragmento,
                "s": ruta,
                "t": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
            },
        ).scalar_one()

    # --- Beneficio -----------------------------------------------------------

    def _beneficio(self, datos: dict) -> uuid.UUID:
        return self.conexion.execute(
            text(
                "INSERT INTO beneficios (codigo, nombre, linea, familia) "
                "VALUES (:c, :n, :l, :f) "
                "ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre RETURNING id"
            ),
            {
                "c": datos["codigo"],
                "n": datos["nombre"],
                "l": datos.get("linea"),
                "f": datos.get("familia"),
            },
        ).scalar_one()

    def _version_de_beneficio(self, beneficio_id: uuid.UUID, datos: dict) -> uuid.UUID:
        ya = self.conexion.execute(
            text(
                "SELECT bv.registro_version_id FROM beneficio_versiones bv "
                "  JOIN registro_versiones rv ON rv.id = bv.registro_version_id "
                " WHERE bv.beneficio_id = :b AND rv.known_hasta IS NULL"
            ),
            {"b": beneficio_id},
        ).scalar_one_or_none()
        if ya is not None:
            return ya

        siguiente = self.conexion.execute(
            text(
                "SELECT coalesce(max(numero_version), 0) + 1 FROM registro_versiones "
                " WHERE entidad_tipo = :t AND entidad_id = :e"
            ),
            {"t": EntidadVersionada.BENEFICIO.value, "e": beneficio_id},
        ).scalar_one()
        registro = self.conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo) VALUES (:t, :e, :nv, :estado, :vt) RETURNING id"
            ),
            {
                "t": EntidadVersionada.BENEFICIO.value,
                "e": beneficio_id,
                "nv": siguiente,
                # Candidato: la vigencia del beneficio la decide la revisión, no
                # la curaduría.
                "estado": EstadoRevision.CANDIDATE.value,
                "vt": ValidTipo.DESCONOCIDO.value,
            },
        ).scalar_one()
        self.conexion.execute(
            text(
                "INSERT INTO beneficio_versiones (registro_version_id, beneficio_id, "
                " jurisdiccion_id, naturaleza, descripcion, unidad_beneficiaria, modalidad, "
                " frecuencia, requiere_solicitud) "
                "VALUES (:rv, :b, :j, :nat, :desc, :ub, :mod, :fre, :req)"
            ),
            {
                "rv": registro,
                "b": beneficio_id,
                "j": datos["jurisdiccion"],
                "nat": datos["naturaleza"],
                "desc": datos["descripcion"],
                "ub": datos.get("unidad_beneficiaria"),
                "mod": datos.get("modalidad"),
                "fre": datos.get("frecuencia"),
                "req": datos.get("requiere_solicitud"),
            },
        )
        return registro

    def _atar_a_la_norma(
        self,
        version_id: uuid.UUID,
        norma_version_id: uuid.UUID,
        norma: dict,
        evidencia_id: uuid.UUID,
    ) -> None:
        self.conexion.execute(
            text(
                "INSERT INTO beneficio_normas (beneficio_version_id, norma_version_id, "
                " evidencia_id, rol, alcance) VALUES (:bv, :nv, :e, :rol, :alcance) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "bv": version_id,
                "nv": norma_version_id,
                "e": evidencia_id,
                "rol": norma.get("rol", "CREA"),
                "alcance": norma.get("referencia"),
            },
        )

    # --- Piezas --------------------------------------------------------------

    def _poblacion(
        self,
        version_id: uuid.UUID,
        datos: dict,
        doc_version_id: uuid.UUID,
        unidades: dict[str, dict],
    ) -> None:
        poblacion_id = self.conexion.execute(
            text(
                "INSERT INTO poblaciones (codigo, nombre, definicion) VALUES (:c, :n, :d) "
                "ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre RETURNING id"
            ),
            {"c": datos["codigo"], "n": datos["nombre"], "d": datos.get("definicion")},
        ).scalar_one()
        self.conexion.execute(
            text(
                "INSERT INTO beneficio_poblaciones (beneficio_version_id, poblacion_id, "
                " evidencia_id, rol_persona, alcance) VALUES (:bv, :p, :e, :rol, :alcance) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "bv": version_id,
                "p": poblacion_id,
                "e": self._evidencia(doc_version_id, unidades, datos["ruta_evidencia"]),
                # El rol importa: la ley mide el ingreso del hogar y la
                # residencia del titular. Mezclarlos excluye a quien califica.
                "rol": datos["rol_persona"],
                "alcance": datos.get("alcance"),
            },
        )

    def _regla(
        self,
        version_id: uuid.UUID,
        datos: dict,
        doc_version_id: uuid.UUID,
        unidades: dict[str, dict],
    ) -> tuple[uuid.UUID, bool]:
        arbol = datos.get("ast")
        sin_formalizar = bool(datos.get("requiere_revision")) or arbol is None
        if arbol is not None:
            try:
                validar_ast(arbol)
            except ErrorDeContrato as exc:
                raise LecturaInvalida(
                    f"El AST de la regla {datos['clave']!r} no cumple el contrato: {exc}"
                ) from exc

        ya = self.conexion.execute(
            text("SELECT id FROM reglas WHERE beneficio_version_id = :bv AND texto_literal = :t"),
            {"bv": version_id, "t": datos["texto_literal"]},
        ).scalar_one_or_none()
        if ya is not None:
            return ya, sin_formalizar

        self._verificar_cita(
            unidades, datos["ruta_evidencia"], datos["texto_literal"], f"regla {datos['clave']!r}"
        )
        evidencia_id = self._evidencia(doc_version_id, unidades, datos["ruta_evidencia"])
        regla_id = self.conexion.execute(
            text(
                "INSERT INTO reglas (beneficio_version_id, evidencia_id, categoria, "
                " texto_literal, descripcion, ast, ast_schema_version, requiere_revision, "
                " alcance, estado_revision) "
                "VALUES (:bv, :e, :cat, :texto, :desc, CAST(:ast AS jsonb), :ver, :rev, "
                "        :alcance, :estado) RETURNING id"
            ),
            {
                "bv": version_id,
                "e": evidencia_id,
                "cat": datos["categoria"],
                "texto": datos["texto_literal"],
                "desc": datos.get("descripcion"),
                "ast": json.dumps(arbol, ensure_ascii=False) if arbol else None,
                "ver": arbol.get("schema_version") if arbol else None,
                # Siempre true, y el esquema lo exige: una regla con AST solo
                # puede quedar sin revisión si ya está aprobada. Es la misma
                # promesa que el módulo declara —nada entra aprobado desde la
                # curaduría—, escrita donde no se puede evitar.
                "rev": True,
                "alcance": datos.get("motivo_revision"),
                # Nunca APPROVED desde la curaduría: una regla ejecutable sin
                # revisión decide accesos con la lectura de una sola persona.
                "estado": EstadoRevision.CANDIDATE.value,
            },
        ).scalar_one()

        for parametro in datos.get("parametros", ()):
            self.conexion.execute(
                text(
                    "INSERT INTO regla_parametros (regla_id, parametro_id, rol) "
                    "VALUES (:r, :p, :rol) ON CONFLICT DO NOTHING"
                ),
                {
                    "r": regla_id,
                    "p": self._parametro(parametro["codigo"]),
                    "rol": parametro.get("rol", "UMBRAL"),
                },
            )
        return regla_id, sin_formalizar

    def _retirar_reglas_que_la_lectura_ya_no_tiene(
        self, version_id: uuid.UUID, reglas, resultado: ResultadoCuracion
    ) -> None:
        """Una cita corregida no deja atrás la versión vieja de la regla.

        Las reglas se reconocen por su texto literal, así que corregir una cita
        —recortarla donde termina la causal, sacarle unos puntos suspensivos—
        crea una regla nueva y deja la anterior en la base. Nadie la vuelve a
        escribir en la lectura y nadie la borra: queda una regla candidata que
        ningún archivo curado reclama, citable como cualquier otra.

        No se borra: se marca SUPERSEDED, que es lo que el vocabulario tiene
        para esto. Lo que ya pasó por revisión no se toca por editar un archivo
        —retirar una regla aprobada es una decisión de revisión, no una
        consecuencia de guardar un JSON— y se avisa para que alguien lo mire.
        """
        vigentes = [" ".join(r["texto_literal"].split()) for r in reglas]
        sobrantes = (
            self.conexion.execute(
                text(
                    "SELECT id, estado_revision, texto_literal FROM reglas "
                    " WHERE beneficio_version_id = :bv "
                    "   AND regexp_replace(btrim(texto_literal), '\\s+', ' ', 'g') "
                    "       <> ALL(:vigentes)"
                ),
                {"bv": version_id, "vigentes": vigentes or [""]},
            )
            .mappings()
            .all()
        )
        retiradas = 0
        for sobrante in sobrantes:
            if sobrante["estado_revision"] == EstadoRevision.SUPERSEDED.value:
                # Ya se retiró en una corrida anterior. Volver a avisarlo cada vez
                # convierte el aviso en ruido, y el aviso que importa —una regla
                # aprobada que la lectura dejó de tener— se pierde entre ellos.
                continue
            if sobrante["estado_revision"] != EstadoRevision.CANDIDATE.value:
                resultado.avisos.append(
                    f"La regla «{sobrante['texto_literal'][:60]}…» ya no está en la lectura y "
                    f"está en {sobrante['estado_revision']}: no se retira sola. Retirar una "
                    "regla que pasó por revisión es una decisión de revisión."
                )
                continue
            self.conexion.execute(
                text(
                    "UPDATE reglas SET estado_revision = :estado, alcance = :motivo  WHERE id = :id"
                ),
                {
                    "estado": EstadoRevision.SUPERSEDED.value,
                    "motivo": (
                        "La lectura curada ya no contiene esta regla: su cita se corrigió o se "
                        "quitó. Se conserva el texto para poder explicar qué se afirmaba antes."
                    ),
                    "id": sobrante["id"],
                },
            )
            retiradas += 1
        if retiradas:
            resultado.avisos.append(
                f"{retiradas} regla(s) quedaron fuera de la lectura y pasaron a SUPERSEDED. "
                "No se borran: siguen explicando qué se afirmaba antes de corregir la cita."
            )

    def _dependencias_entre_reglas(self, reglas, claves: dict[str, uuid.UUID]) -> None:
        """Una excepción sabe de qué regla es excepción.

        Sin esa arista, el evaluador no puede cumplir la promesa de no negar sin
        haber mirado las excepciones: no sabría cuáles mirar.
        """
        for regla in reglas:
            referida = regla.get("excepcion_de")
            if referida is None:
                continue
            if referida not in claves:
                raise LecturaInvalida(
                    f"La regla {regla['clave']!r} dice ser excepción de {referida!r}, que no "
                    "está en la lectura."
                )
            self.conexion.execute(
                text(
                    "INSERT INTO regla_dependencias (regla_id, regla_referida_id, tipo) "
                    "VALUES (:r, :ref, 'EXCEPCION_DE') ON CONFLICT DO NOTHING"
                ),
                {"r": claves[regla["clave"]], "ref": claves[referida]},
            )

    def _parametro(self, codigo: str) -> uuid.UUID:
        return self.conexion.execute(
            text(
                "INSERT INTO parametros (codigo, concepto, unidad, moneda) "
                "VALUES (:c, :con, 'MONEDA', 'ARS') "
                "ON CONFLICT (codigo) DO UPDATE SET concepto = EXCLUDED.concepto RETURNING id"
            ),
            {"c": codigo, "con": codigo.replace(".", " ").replace("-", " ")},
        ).scalar_one()

    def _cuantia(
        self,
        version_id: uuid.UUID,
        datos: dict,
        doc_version_id: uuid.UUID,
        unidades: dict[str, dict],
    ) -> None:
        ya = self.conexion.execute(
            text("SELECT id FROM beneficio_cuantias WHERE beneficio_version_id = :bv"),
            {"bv": version_id},
        ).scalar_one_or_none()
        if ya is not None:
            return
        # La ley describe la escala en palabras y remite el detalle a la
        # Autoridad de Aplicación. La fórmula queda declarada con su versión y
        # sin valor: servir el piso como «el monto» diría que todos cobran igual.
        #
        # Los parámetros entran con el rol que la lectura les da, no solo los de
        # piso. Una asignación cuyo importe es «la mayor suma del inciso a) o b)»
        # no tiene piso: tiene una referencia a otra norma que se actualiza sola,
        # y perder ese rol al guardarla la dejaría indistinguible de un monto que
        # nadie actualiza.
        tipo = datos["tipo"]
        if tipo not in ("FORMULA", "ESPECIE", "NO_INFORMADO"):
            raise LecturaInvalida(
                f"La cuantía declara tipo {tipo!r} y el cargador sabe guardar FORMULA, ESPECIE "
                "y NO_INFORMADO. Un tipo FIJO exige un valor y una moneda que ninguna lectura "
                "curada trajo todavía: escribirlo sin un caso real sería adivinar cómo se "
                "guarda un monto que después se sirve como «lo que vas a cobrar»."
            )

        parametros = datos.get("parametros", ())
        # Por cuántos se cobra no es un detalle de presentación: una asignación
        # que se paga por cada hijo y una que se paga por hogar dan importes
        # distintos con los mismos datos.
        campos = {
            "bv": version_id,
            "e": self._evidencia(doc_version_id, unidades, datos["ruta_evidencia"]),
            "t": tipo,
            "ub": datos.get("unidad_beneficiaria", "HOGAR"),
            "f": None,
            "fv": None,
            "esp": None,
        }
        if tipo == "FORMULA":
            # La ley describe la escala en palabras y remite el detalle a la
            # Autoridad de Aplicación. La fórmula queda declarada con su versión
            # y sin valor: servir el piso como «el monto» diría que todos cobran
            # igual.
            #
            # Los parámetros entran con el rol que la lectura les da, no solo los
            # de piso. Una asignación cuyo importe es «la mayor suma del inciso
            # a) o b)» no tiene piso: tiene una referencia a otra norma que se
            # actualiza sola, y perder ese rol al guardarla la dejaría
            # indistinguible de un monto que nadie actualiza.
            por_rol: dict[str, list[str]] = {}
            for parametro in parametros:
                por_rol.setdefault(parametro.get("rol", "PISO"), []).append(parametro["codigo"])
            campos["f"] = json.dumps(
                {
                    "schema_version": "1.0",
                    "descripcion": datos["descripcion"],
                    "piso": [p["codigo"] for p in parametros if p.get("rol", "PISO") == "PISO"],
                    "parametros": por_rol,
                },
                ensure_ascii=False,
            )
            campos["fv"] = datos["formula_version"]
        elif tipo == "ESPECIE":
            # Lo que recibe la persona es una cosa, no un importe: un almuerzo,
            # un pasaje, un remedio. Guardarlo como fórmula obligaría a inventar
            # un número, y el número es justamente lo que la norma no da.
            campos["esp"] = datos["descripcion"]

        cuantia_id = self.conexion.execute(
            text(
                "INSERT INTO beneficio_cuantias (beneficio_version_id, evidencia_id, tipo, "
                " formula_ast, formula_version, descripcion_especie, unidad_beneficiaria) "
                "VALUES (:bv, :e, :t, CAST(:f AS jsonb), :fv, :esp, :ub) RETURNING id"
            ),
            campos,
        ).scalar_one()
        for parametro in datos.get("parametros", ()):
            self.conexion.execute(
                text(
                    "INSERT INTO cuantia_parametros (cuantia_id, parametro_id, rol) "
                    "VALUES (:c, :p, :rol) ON CONFLICT DO NOTHING"
                ),
                {
                    "c": cuantia_id,
                    "p": self._parametro(parametro["codigo"]),
                    "rol": parametro.get("rol", "PISO"),
                },
            )

    def _plazo(
        self,
        version_id: uuid.UUID,
        norma_version_id: uuid.UUID,
        datos: dict,
        doc_version_id: uuid.UUID,
        unidades: dict[str, dict],
    ) -> None:
        ya = self.conexion.execute(
            text(
                "SELECT p.plazo_id FROM plazos p WHERE p.beneficio_version_id = :bv "
                "  AND p.evento_inicio = :ev"
            ),
            {"bv": version_id, "ev": datos["evento_inicio"]},
        ).scalar_one_or_none()
        if ya is not None:
            return

        self._verificar_cita(
            unidades, datos["ruta_evidencia"], datos["texto_literal"], f"plazo {datos['clave']!r}"
        )
        plazo_id = uuid.uuid4()
        siguiente = self.conexion.execute(
            text(
                "SELECT coalesce(max(numero_version), 0) + 1 FROM registro_versiones "
                " WHERE entidad_tipo = :t AND entidad_id = :e"
            ),
            {"t": EntidadVersionada.PLAZO.value, "e": plazo_id},
        ).scalar_one()
        registro = self.conexion.execute(
            text(
                "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
                " estado_revision, valid_tipo) VALUES (:t, :e, :nv, :estado, :vt) RETURNING id"
            ),
            {
                "t": EntidadVersionada.PLAZO.value,
                "e": plazo_id,
                "nv": siguiente,
                "estado": EstadoRevision.CANDIDATE.value,
                "vt": ValidTipo.DESCONOCIDO.value,
            },
        ).scalar_one()
        self.conexion.execute(
            text(
                "INSERT INTO plazos (registro_version_id, plazo_id, beneficio_version_id, "
                " evidencia_id, tipo, cantidad, unidad, tipo_dia, evento_inicio, "
                " calendario_id, zona_horaria) "
                "VALUES (:rv, :p, :bv, :e, :tipo, :cant, :uni, :td, :ev, :cal, "
                " 'America/Argentina/Buenos_Aires')"
            ),
            {
                "rv": registro,
                "p": plazo_id,
                "bv": version_id,
                "e": self._evidencia(doc_version_id, unidades, datos["ruta_evidencia"]),
                "tipo": datos["tipo"],
                "cant": datos["cantidad"],
                "uni": datos["unidad"],
                # La ley no dice si corre en corridos o hábiles; NO_INFORMADO es
                # la respuesta, no un defecto que haya que rellenar.
                "td": datos["tipo_dia"],
                "ev": datos["evento_inicio"],
                "cal": self._calendario(datos),
            },
        )
        del norma_version_id

    def _calendario(self, datos: dict) -> uuid.UUID | None:
        """El calendario con el que se computa un plazo hábil.

        El esquema lo exige para los plazos en días hábiles, y con razón: saltear
        sólo sábados y domingos cuenta mal cualquier mes con feriado. La lectura
        curada declara de qué jurisdicción tiene que ser; si no hay uno cargado
        para ella, el plazo no se carga a medias con el de otra jurisdicción.
        """
        if datos["tipo_dia"] not in ("HABIL_ADMINISTRATIVO", "HABIL_JUDICIAL"):
            return None
        jurisdiccion = datos.get("calendario_jurisdiccion")
        if not jurisdiccion:
            raise LecturaInvalida(
                f"El plazo {datos.get('clave')!r} corre en días {datos['tipo_dia']} y la "
                "lectura no declara de qué jurisdicción tiene que ser el calendario. Un "
                "plazo hábil sin calendario no se puede computar y con el calendario "
                "equivocado se computa mal."
            )
        calendario = self.conexion.execute(
            text(
                "SELECT id FROM calendarios WHERE jurisdiccion_id = :j "
                " ORDER BY fecha_desde DESC LIMIT 1"
            ),
            {"j": jurisdiccion},
        ).scalar_one_or_none()
        if calendario is None:
            # Se deriva de los feriados nacionales, que rigen en todo el país: el
            # calendario resultante es cierto en lo que dice y le faltan las
            # ferias administrativas locales, que alargan el plazo. Por eso el
            # nombre declara la limitación —viaja en el fundamento de cada
            # cómputo— y la derivación abre una incidencia con responsable.
            #
            # Antes esto no se derivaba solo y había que crearlo a mano, con lo
            # que una base recién poblada no podía cargar ninguna lectura con un
            # plazo hábil local. Vincularlo al calendario nacional sigue estando
            # prohibido: contaría los feriados de otra jurisdicción.
            calendario = derivar_jurisdiccional(
                self.conexion, jurisdiccion=jurisdiccion, anio=dt.date.today().year
            )
        if calendario is None:
            raise LecturaInvalida(
                f"El plazo {datos.get('clave')!r} necesita un calendario de {jurisdiccion} y no "
                "hay ninguno cargado, ni uno nacional del que derivarlo. Vincularlo al "
                "calendario nacional de otro año contaría feriados que no son los de ese "
                "período, que es el error que hace perder un plazo. Hay que correr "
                "`bn plazos calendario <año>` antes de cargar las lecturas curadas."
            )
        return calendario

    def _campo_no_informado(self, norma_version_id: uuid.UUID, campo: dict) -> None:
        """Un campo que la ley remite a la reglamentación queda dicho como tal.

        No informado no es inexistente: que la norma no lo declare no significa
        que no haya causales, y responder «no te lo pueden quitar» sería la
        lectura opuesta a la correcta.
        """
        self.conexion.execute(
            text(
                "UPDATE evaluaciones_completitud SET estado = :estado, motivo = :motivo, "
                "  evaluado_en = now() "
                " WHERE norma_version_id = :nv AND campo_solicitado = :campo"
            ),
            {
                "nv": norma_version_id,
                "campo": campo["campo"],
                "estado": "NO_INFORMADO_EN_FUENTES_REVISADAS",
                "motivo": campo["motivo"],
            },
        )

    def _dependencia(self, referencia_origen: str, dependencia: dict) -> None:
        descripcion = (
            f"{referencia_origen} depende de {dependencia['referencia']}: {dependencia['motivo']}"
        )
        ya = self.conexion.execute(
            text("SELECT 1 FROM incidencias_revision WHERE descripcion = :d"),
            {"d": descripcion},
        ).first()
        if ya is not None:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, descripcion, "
                " responsable_rol) VALUES (:t, :s, 'ABIERTA', :d, 'curacion juridica')"
            ),
            {
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "s": Severidad.HIGH.value,
                "d": descripcion,
            },
        )

    def _avisos(self, lectura: dict, resultado: ResultadoCuracion) -> None:
        resultado.avisos.append(
            f"El beneficio y sus {resultado.reglas} regla(s) quedan como candidatos. La "
            "evaluación no los usa hasta que una persona con competencia jurídica los apruebe: "
            "que lo haya escrito una curaduría no lo vuelve derecho aplicable."
        )
        if resultado.reglas_sin_formalizar:
            # Son dos situaciones distintas y el aviso las mezclaba: una regla
            # con AST y `requiere_revision` conserva su condición escrita y
            # espera aprobación; una sin AST no tiene condición que ejecutar.
            # Decir de las dos «se conserva su texto literal y nada más» era
            # falso para la primera y hacía parecer perdido un trabajo hecho.
            sin_condicion = [r["clave"] for r in lectura.get("reglas", ()) if r.get("ast") is None]
            con_condicion_a_revisar = [
                r["clave"]
                for r in lectura.get("reglas", ())
                if r.get("ast") is not None and r.get("requiere_revision")
            ]
            if sin_condicion:
                resultado.avisos.append(
                    f"{len(sin_condicion)} regla(s) sin condición ejecutable "
                    f"({', '.join(sin_condicion)}): la ley las remite a la reglamentación o no "
                    "alcanza para escribir su condición. Se conserva su texto literal y nada "
                    "más."
                )
            if con_condicion_a_revisar:
                resultado.avisos.append(
                    f"{len(con_condicion_a_revisar)} regla(s) tienen su condición escrita y "
                    f"esperan revisión ({', '.join(con_condicion_a_revisar)}): el árbol está "
                    "guardado y validado, y no se ejecuta hasta que alguien con competencia "
                    "jurídica lo apruebe. Cada una dice en su motivo qué hay que decidir."
                )
        if resultado.dependencias:
            resultado.avisos.append(
                f"{resultado.dependencias} norma(s) de las que este beneficio depende no están "
                "en el corpus. Mientras falten, las condiciones que definen quedan declaradas "
                "y no evaluables."
            )


def cargar_todas(conexion: Connection, raiz: pathlib.Path | None = None) -> list[ResultadoCuracion]:
    """Carga cada lectura curada del repositorio, y sigue si una no se puede.

    Que a una lectura le falte la norma que cita no es razón para no cargar las
    demás: el bloqueo se reporta con su motivo y el resto entra. Abortar el lote
    entero dejaría el corpus sin los beneficios que sí estaban listos, y sin
    decir por qué.
    """
    base = (raiz or pathlib.Path.cwd()) / RUTA_CURADURIA
    if not base.is_dir():
        return []
    curador = CuradorDeBeneficios(conexion)
    resultados: list[ResultadoCuracion] = []
    for ruta in sorted(base.glob("*.json")):
        try:
            resultados.append(curador.cargar(ruta))
        except LecturaInvalida as error:
            resultados.append(
                ResultadoCuracion(
                    avisos=[f"{ruta.name} no se cargó: {error}"],
                )
            )
    return resultados
