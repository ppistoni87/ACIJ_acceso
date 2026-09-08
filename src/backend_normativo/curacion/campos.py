"""HU-012: evaluar los siete campos pedidos, por norma y por beneficio.

Dos cosas distintas que la especificación separa y este módulo también:

* **Evaluar** un campo es haberlo buscado y registrar con qué resultado. DQ03
  pide el 100% de los campos evaluados.
* **Tener valor sustantivo** es otra cosa. DQ04 la mide aparte, y un campo en
  `NO_INFORMADO_EN_FUENTES_REVISADAS` no cuenta como completo. Cien por ciento
  de filas en ese estado da cobertura de evaluación, nunca "base completa".

La detección de candidatos propone, no concluye. Cada candidato apunta al
fragmento exacto que lo sugiere y nace en estado `CANDIDATE`: que un artículo
contenga la palabra "caducará" sugiere una causal de cese, no la establece.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    CAMPOS_SOLICITADOS,
    EstadoCampo,
    EstadoRevision,
    TipoEvidencia,
)


@dataclass(frozen=True)
class PatronDeCampo:
    """Señales textuales que sugieren que una unidad habla de un campo."""

    campo: str
    patron: re.Pattern[str]
    descripcion: str


def _p(campo: str, expresion: str, descripcion: str) -> PatronDeCampo:
    return PatronDeCampo(campo, re.compile(expresion, re.IGNORECASE), descripcion)


# Los patrones son deliberadamente amplios: es preferible proponer de más y que
# la revisión descarte, a perder una disposición que nadie va a volver a buscar.
PATRONES: tuple[PatronDeCampo, ...] = (
    _p(
        "poblacion_destinataria",
        r"\b(?:destinad[oa]s?\s+a|dirigid[oa]s?\s+a|beneficiari[oa]s?|"
        r"titulares?\s+de|alcanza\s+a|comprende\s+a|ser[áa]n?\s+beneficiari)",
        "menciona a quién alcanza la disposición",
    ),
    _p(
        "criterios_aplicabilidad",
        r"\b(?:requisitos?|deber[áa]n?\s+acreditar|siempre\s+que|"
        r"a\s+condici[óo]n\s+de|que\s+acrediten|no\s+super(?:e|en)|"
        r"menores?\s+de\s+\d+\s+años|mayores?\s+de\s+\d+\s+años)",
        "menciona condiciones de acceso",
    ),
    _p(
        "plazos",
        r"\b(?:plazo\s+de\s+\w+|dentro\s+de\s+(?:los\s+)?\w+\s+d[íi]as|"
        r"hasta\s+el\s+\d{1,2}\s*/\s*\d{1,2}|vigencia|entrar[áa]\s+en\s+vigor|"
        r"a\s+partir\s+de(?:l)?\s+\d|caduca(?:r[áa])?\s+el)",
        "menciona un plazo o una vigencia",
    ),
    _p(
        "criterios_revocacion",
        r"\b(?:revoca(?:ci[óo]n|r[áa]n?|se)|caduc(?:idad|ar[áa]n?)|"
        r"se\s+suspender[áa]|suspensi[óo]n\s+del\s+beneficio|"
        r"p[ée]rdida\s+del\s+(?:beneficio|derecho)|cese\s+de\s+la\s+prestaci[óo]n|"
        r"dar[áa]\s+de\s+baja)",
        "menciona revocación, suspensión, caducidad o cese",
    ),
    _p(
        "beneficio_otorgado",
        r"\b(?:consistir[áa]\s+en|se\s+abonar[áa]|prestaci[óo]n\s+(?:consistente|mensual)|"
        r"suma\s+de\s+dinero|asignaci[óo]n\s+de|otorga(?:r[áa]|se)|"
        r"tendr[áa]n?\s+derecho\s+a\s+percibir|exenci[óo]n\s+de)",
        "menciona qué se otorga",
    ),
    _p(
        "no_descartar",
        r"\b(?:excepto|salvo|no\s+obstante|sin\s+perjuicio\s+de|"
        r"podr[áa]n?\s+subsanar|en\s+caso\s+de\s+imposibilidad|"
        r"documentaci[óo]n\s+alternativa|situaciones?\s+especiales?)",
        "menciona una excepción, salvaguarda o alternativa documental",
    ),
)


def _resumen_de_relacion(fila: dict) -> dict[str, str]:
    norma = f"{fila['destino_tipo']} {fila['destino_numero']}/{fila['destino_anio']}"
    return {"tipo": fila["tipo"], "norma": norma}


@dataclass
class ResultadoCampos:
    versiones_evaluadas: int = 0
    evaluaciones_creadas: int = 0
    afirmaciones_creadas: int = 0
    por_estado: dict[str, int] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)


class EvaluadorDeCampos:
    """Detecta candidatos y deja una fila de evaluación por campo y por ficha."""

    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def evaluar(self, source_id: str | None = None) -> ResultadoCampos:
        resultado = ResultadoCampos()
        versiones = (
            self.conexion.execute(
                text(
                    "SELECT nv.registro_version_id, nv.norma_id, nv.doc_version_id, d.source_id "
                    "  FROM norma_versiones nv "
                    "  JOIN documento_versiones dv ON dv.id = nv.doc_version_id "
                    "  JOIN documentos d ON d.id = dv.documento_id "
                    " WHERE (CAST(:sid AS text) IS NULL OR d.source_id = :sid)"
                ),
                {"sid": source_id},
            )
            .mappings()
            .all()
        )

        for version in versiones:
            self._evaluar_version(dict(version), resultado)
            resultado.versiones_evaluadas += 1
        return resultado

    def _evaluar_version(self, version: dict, resultado: ResultadoCampos) -> None:
        candidatos = self._detectar(version, resultado)
        fuentes_revisadas = [version["source_id"]]

        for campo in CAMPOS_SOLICITADOS:
            afirmaciones = candidatos.get(campo, [])
            estado, motivo = self._estado_del_campo(
                version["registro_version_id"], campo, afirmaciones
            )
            evaluacion_id = self._registrar_evaluacion(
                version["registro_version_id"], campo, estado, motivo, fuentes_revisadas
            )
            if evaluacion_id is None:
                continue
            resultado.evaluaciones_creadas += 1
            resultado.por_estado[estado.value] = resultado.por_estado.get(estado.value, 0) + 1
            for afirmacion_id in afirmaciones:
                self.conexion.execute(
                    text(
                        "INSERT INTO completitud_afirmaciones (evaluacion_id, afirmacion_id, rol) "
                        "VALUES (:e, :a, 'CANDIDATO') ON CONFLICT DO NOTHING"
                    ),
                    {"e": evaluacion_id, "a": afirmacion_id},
                )

    # --- Detección ----------------------------------------------------------

    def _detectar(self, version: dict, resultado: ResultadoCampos) -> dict[str, list[uuid.UUID]]:
        """Propone afirmaciones candidatas con su fragmento localizable."""
        unidades = (
            self.conexion.execute(
                text(
                    "SELECT id, texto, tipo, numero, rol_contenido FROM unidades_documentales "
                    " WHERE doc_version_id = :dv AND rol_contenido = 'DISPOSITIVO' "
                    " ORDER BY orden"
                ),
                {"dv": version["doc_version_id"]},
            )
            .mappings()
            .all()
        )

        por_campo: dict[str, list[uuid.UUID]] = {}
        for unidad in unidades:
            for patron in PATRONES:
                coincidencia = patron.patron.search(unidad["texto"])
                if coincidencia is None:
                    continue
                afirmacion_id = self._afirmacion_candidata(
                    version, dict(unidad), patron, coincidencia
                )
                if afirmacion_id is not None:
                    por_campo.setdefault(patron.campo, []).append(afirmacion_id)
                    resultado.afirmaciones_creadas += 1

        # Las interdependencias no se detectan por texto: ya están construidas
        # como relaciones con evidencia. Reutilizarlas evita proponer dos veces
        # lo mismo con menos respaldo.
        relaciones = self._afirmacion_de_interdependencias(version)
        if relaciones is not None:
            por_campo.setdefault("interdependencias", []).append(relaciones)
            resultado.afirmaciones_creadas += 1

        return por_campo

    def _afirmacion_candidata(
        self,
        version: dict,
        unidad: dict,
        patron: PatronDeCampo,
        coincidencia: re.Match[str],
    ) -> uuid.UUID | None:
        evidencia_id = self._evidencia(version["doc_version_id"], unidad, coincidencia)
        valor = {
            "unidad": unidad["tipo"],
            "numero": unidad["numero"],
            "senal": coincidencia.group(0),
            "texto": unidad["texto"][:2000],
        }
        return self.conexion.execute(
            text(
                "INSERT INTO afirmaciones "
                "(registro_version_id, evidencia_id, campo_path, valor, estado_campo, "
                " motivo, source_id, estado_revision) "
                "VALUES (:rv, :e, :campo, :valor, :estado, :motivo, :s, :revision) "
                "ON CONFLICT DO NOTHING RETURNING id"
            ),
            {
                "rv": version["registro_version_id"],
                "e": evidencia_id,
                "campo": patron.campo,
                "valor": json.dumps(valor, ensure_ascii=False),
                "estado": EstadoCampo.INFORMADO.value,
                "motivo": (
                    f"Candidato propuesto por extracción: la unidad {patron.descripcion}. "
                    "Requiere revisión de dominio antes de publicarse."
                ),
                "s": version["source_id"],
                # Propone, no concluye.
                "revision": EstadoRevision.CANDIDATE.value,
            },
        ).scalar_one_or_none()

    def _afirmacion_de_interdependencias(self, version: dict) -> uuid.UUID | None:
        relaciones = (
            self.conexion.execute(
                text(
                    "SELECT r.tipo, r.evidencia_id, "
                    "       d.tipo AS destino_tipo, d.numero AS destino_numero, "
                    "       d.anio AS destino_anio "
                    "  FROM relaciones_normativas r "
                    "  JOIN normas d ON d.id = r.norma_destino_id "
                    " WHERE r.norma_origen_id = :n "
                    " UNION ALL "
                    "SELECT r.tipo, r.evidencia_id, o.tipo, o.numero, o.anio "
                    "  FROM relaciones_normativas r "
                    "  JOIN normas o ON o.id = r.norma_origen_id "
                    " WHERE r.norma_destino_id = :n"
                ),
                {"n": version["norma_id"]},
            )
            .mappings()
            .all()
        )
        if not relaciones:
            return None

        return self.conexion.execute(
            text(
                "INSERT INTO afirmaciones "
                "(registro_version_id, evidencia_id, campo_path, valor, estado_campo, motivo, "
                " source_id, estado_revision) "
                "VALUES (:rv, :e, 'interdependencias', :valor, :estado, :motivo, :s, :revision) "
                "ON CONFLICT DO NOTHING RETURNING id"
            ),
            {
                "rv": version["registro_version_id"],
                "e": relaciones[0]["evidencia_id"],
                "valor": json.dumps(
                    [_resumen_de_relacion(r) for r in relaciones], ensure_ascii=False
                ),
                "estado": EstadoCampo.INFORMADO.value,
                "motivo": (
                    f"{len(relaciones)} relación(es) normativas construidas con evidencia. "
                    "Cada una conserva su propia cita."
                ),
                "s": version["source_id"],
                "revision": EstadoRevision.CANDIDATE.value,
            },
        ).scalar_one_or_none()

    def _evidencia(
        self, doc_version_id: uuid.UUID, unidad: dict, coincidencia: re.Match[str]
    ) -> uuid.UUID:
        inicio = max(0, coincidencia.start() - 60)
        fragmento = unidad["texto"][inicio : coincidencia.end() + 200].strip()
        hash_fragmento = hashlib.sha256(fragmento.encode("utf-8")).hexdigest()
        # Puede haber más de una fila con el mismo hash para la misma unidad: la
        # curaduría de beneficios también crea evidencia sobre las unidades que
        # cita, y cuando el fragmento coincide con el texto entero de la unidad
        # el hash es el mismo. Son la misma evidencia —mismo documento, misma
        # unidad, mismo texto—, así que se reusa la más antigua y la elección no
        # depende del orden en que se hayan corrido los comandos.
        existente = self.conexion.execute(
            text(
                "SELECT id FROM evidencias WHERE doc_version_id = :dv AND unidad_id = :u "
                "  AND hash_fragmento = :h ORDER BY creado_en, id LIMIT 1"
            ),
            {"dv": doc_version_id, "u": unidad["id"], "h": hash_fragmento},
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias "
                "(doc_version_id, unidad_id, fragmento, hash_fragmento, tipo, offset_inicio, "
                " offset_fin) VALUES (:dv, :u, :f, :h, :tipo, :ini, :fin) RETURNING id"
            ),
            {
                "dv": doc_version_id,
                "u": unidad["id"],
                "f": fragmento,
                "h": hash_fragmento,
                "tipo": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "ini": inicio,
                "fin": coincidencia.end() + 200,
            },
        ).scalar_one()

    # --- Evaluación ---------------------------------------------------------

    def _estado_del_campo(
        self, registro_version_id: uuid.UUID, campo: str, candidatos: list[uuid.UUID]
    ) -> tuple[EstadoCampo, str]:
        aprobadas = self.conexion.execute(
            text(
                "SELECT count(*) FROM afirmaciones "
                " WHERE registro_version_id = :rv AND campo_path = :c "
                "   AND estado_revision IN ('APPROVED', 'PUBLISHED') "
                "   AND estado_campo = 'INFORMADO'"
            ),
            {"rv": registro_version_id, "c": campo},
        ).scalar_one()
        if aprobadas:
            return (
                EstadoCampo.INFORMADO,
                f"{aprobadas} afirmación(es) aprobadas con evidencia.",
            )

        en_revision = self.conexion.execute(
            text(
                "SELECT count(*) FROM afirmaciones "
                " WHERE registro_version_id = :rv AND campo_path = :c "
                "   AND estado_revision = 'CANDIDATE'"
            ),
            {"rv": registro_version_id, "c": campo},
        ).scalar_one()
        if en_revision:
            return (
                EstadoCampo.PENDIENTE,
                f"{en_revision} candidato(s) con evidencia esperando revisión de dominio. "
                "El campo está evaluado, pero todavía no tiene valor sustantivo.",
            )

        return (
            EstadoCampo.NO_INFORMADO_EN_FUENTES_REVISADAS,
            "Se revisó el texto de esta versión y no se encontraron disposiciones sobre "
            "el campo. No significa que no existan en otra fuente.",
        )

    def _registrar_evaluacion(
        self,
        registro_version_id: uuid.UUID,
        campo: str,
        estado: EstadoCampo,
        motivo: str,
        fuentes_revisadas: list[str],
    ) -> uuid.UUID | None:
        return self.conexion.execute(
            text(
                "INSERT INTO evaluaciones_completitud "
                "(norma_version_id, campo_solicitado, estado, fuentes_revisadas, motivo, "
                " revisor_id) "
                "VALUES (:rv, :c, :e, :f, :m, :revisor) "
                "ON CONFLICT (norma_version_id, beneficio_version_id, campo_solicitado) "
                "DO UPDATE SET estado = EXCLUDED.estado, motivo = EXCLUDED.motivo, "
                "  fuentes_revisadas = EXCLUDED.fuentes_revisadas, evaluado_en = now() "
                "RETURNING id"
            ),
            {
                "rv": registro_version_id,
                "c": campo,
                "e": estado.value,
                "f": json.dumps(fuentes_revisadas),
                "m": motivo,
                "revisor": "curacion:deteccion-automatica",
            },
        ).scalar_one_or_none()
