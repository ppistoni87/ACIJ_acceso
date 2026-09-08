"""HU-F19 · AT-029: el procedimiento que no está en el cuerpo de la resolución.

La Resolución 1621/MEDGC/25 no dice cómo se pide una beca. Su artículo 3
«aprueba los Procedimientos para el otorgamiento, control y evaluación del
Régimen de Becas Estudiantiles de la Ley 2917, identificado como Anexo
(IF-2025-53544032-GCABA-SSGDA) el cual forma parte integrante de la presente».
Las etapas, los requisitos y los plazos están en ese anexo, que es otro archivo.

Leer sólo el cuerpo y publicar «no informa plazos» es tan falso como publicar
plazos inventados: la resolución sí los fija, en un documento que hay que ir a
buscar. Mientras el anexo no esté capturado y vinculado, los campos que dependen
de él se declaran no informados **con el motivo puesto** —remite a un anexo que
falta— y no por silencio de la norma.

El identificador del anexo es un dato: `IF-2025-53544032-GCABA-SSGDA` nombra un
documento concreto. Se guarda como referencia pendiente para que alguien lo
consiga, no se resuelve por parecido con cualquier PDF que diga «Anexo».
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoCampo,
    Severidad,
    TipoEvidencia,
    TipoIncidencia,
)

# El identificador GEDO con el que la administración porteña nombra un anexo. El
# PDF lo parte en dos renglones —«IF-2025-\n53544032-GCABA-SSGDA»— así que se
# admite el corte y después se junta.
RE_IDENTIFICADOR = re.compile(r"\b(?:IF|PLIEG|PV|DI|RESOL)-\s*\d{4}-\s*\d+-\s*[A-Z]+-\s*[A-Z]+\b")

# Las fórmulas con las que un cuerpo remite a un anexo que lo integra.
RE_REMISION = re.compile(
    r"[^.]*\b(?:anexo|anexos)\b[^.]*\b(?:forma[n]?\s+parte\s+integrante|integra[n]?\s+la\s+"
    r"presente|se\s+aprueba[n]?|apr[ou]?[eb]ar|que\s+como\s+anexo)\b[^.]*\.?",
    re.IGNORECASE,
)

# Los campos que un procedimiento aprobado por anexo sostiene. Si el anexo falta,
# ninguno de ellos se responde desde el cuerpo.
CAMPOS_DEL_PROCEDIMIENTO = ("plazos", "criterios_aplicabilidad")

RESPONSABLE = "curador jurídico"
MOTIVO_FALTA = (
    "El cuerpo remite a un anexo que aprueba el procedimiento y que todavía no está "
    "capturado y vinculado. La norma sí regula este campo: no es silencio de la fuente, "
    "es un documento que falta."
)


@dataclass
class Remision:
    texto: str
    identificador: str | None
    unidad_id: uuid.UUID
    ruta: str


@dataclass
class ResultadoAnexos:
    norma_id: uuid.UUID | None = None
    remisiones: int = 0
    identificadas: int = 0
    pendientes_abiertas: int = 0
    campos_bloqueados: int = 0
    avisos: list[str] = field(default_factory=list)


def remisiones_en(texto: str) -> list[tuple[str, str | None, int]]:
    """Las oraciones que remiten a un anexo, su identificador y dónde empiezan."""
    encontradas: list[tuple[str, str | None, int]] = []
    for m in RE_REMISION.finditer(texto):
        oracion = " ".join(m.group(0).split())
        if not oracion:
            continue
        identificador = RE_IDENTIFICADOR.search(oracion)
        encontradas.append(
            (
                oracion,
                "".join(identificador.group(0).split()) if identificador else None,
                m.start(),
            )
        )
    return encontradas


class CuradorDeAnexos:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def revisar(self, norma_id: uuid.UUID) -> ResultadoAnexos:
        """Busca remisiones a anexos y bloquea los campos que dependen de ellos."""
        resultado = ResultadoAnexos(norma_id=norma_id)
        version = (
            self.conexion.execute(
                text(
                    "SELECT nv.registro_version_id, nv.doc_version_id FROM norma_versiones nv "
                    "  JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
                    " WHERE nv.norma_id = :n AND rv.known_hasta IS NULL "
                    " ORDER BY rv.numero_version DESC LIMIT 1"
                ),
                {"n": norma_id},
            )
            .mappings()
            .first()
        )
        if version is None:
            resultado.avisos.append("La norma no tiene una versión vigente que revisar.")
            return resultado

        halladas = self._remisiones(version["doc_version_id"])
        resultado.remisiones = len(halladas)
        resultado.identificadas = sum(1 for r in halladas if r.identificador)
        if not halladas:
            return resultado

        pendientes = 0
        for remision in halladas:
            if self._ya_resuelta(norma_id, remision):
                continue
            if self._abrir_pendiente(norma_id, remision):
                resultado.pendientes_abiertas += 1
            pendientes += 1

        if pendientes:
            resultado.campos_bloqueados = self._bloquear_campos(
                version["registro_version_id"], halladas
            )
            self._incidencia(norma_id, halladas)
            resultado.avisos.append(
                f"{pendientes} remisión(es) a anexo sin resolver. Los campos "
                f"{', '.join(CAMPOS_DEL_PROCEDIMIENTO)} quedan NO_INFORMADO con el motivo "
                "puesto: la norma los regula, en un documento que falta."
            )
        else:
            resultado.avisos.append(
                "Todas las remisiones a anexo están resueltas: los campos del procedimiento "
                "se responden desde el anexo vinculado."
            )
        return resultado

    def resolver(
        self,
        referencia_id: uuid.UUID,
        *,
        doc_version_anexo: uuid.UUID,
        actor: str,
        fundamento: str,
    ) -> uuid.UUID:
        """Vincula el anexo capturado con la norma que lo aprueba.

        Es una decisión con nombre: que un PDF diga «Anexo» no prueba que sea
        el anexo que esta resolución aprobó.
        """
        if not actor.strip() or len(fundamento.strip()) < 15:
            raise ValueError(
                "Vincular un anexo exige actor y un fundamento de al menos 15 caracteres: "
                "de ese vínculo dependen los plazos que se publican."
            )
        referencia = (
            self.conexion.execute(
                text(
                    "SELECT norma_origen_id, texto_cita, estado FROM referencias_pendientes "
                    " WHERE id = :r"
                ),
                {"r": referencia_id},
            )
            .mappings()
            .first()
        )
        if referencia is None or referencia["estado"] != "PENDIENTE":
            raise ValueError(f"La referencia {referencia_id} no existe o no está pendiente.")

        norma_anexo = self.conexion.execute(
            text("SELECT nv.norma_id FROM norma_versiones nv WHERE nv.doc_version_id = :d LIMIT 1"),
            {"d": doc_version_anexo},
        ).scalar_one_or_none()
        if norma_anexo is None:
            raise ValueError(
                f"La versión documental {doc_version_anexo} no está vinculada a ninguna norma. "
                "Un anexo se vincula como norma, no como archivo suelto."
            )

        evidencia_id = self._evidencia_del_anexo(doc_version_anexo)
        relacion = self.conexion.execute(
            text(
                "INSERT INTO relaciones_normativas (norma_origen_id, norma_destino_id, "
                " evidencia_id, tipo, alcance, estado_revision) "
                "VALUES (:o, :d, :e, 'COMPLEMENTA', :a, 'APPROVED') RETURNING id"
            ),
            {
                "o": norma_anexo,
                "d": referencia["norma_origen_id"],
                "e": evidencia_id,
                "a": f"Anexo aprobado por la norma. Vinculado por {actor.strip()}: "
                f"{fundamento.strip()}",
            },
        ).scalar_one()
        self.conexion.execute(
            text(
                "UPDATE referencias_pendientes SET estado = 'RESUELTA', "
                " relacion_resultante_id = :rel, resuelta_en = now(), "
                " motivo = coalesce(motivo, '') || :nota WHERE id = :r"
            ),
            {
                "r": referencia_id,
                "rel": relacion,
                "nota": f" · Resuelta por {actor.strip()}: {fundamento.strip()}",
            },
        )
        return relacion

    # --- Internos -----------------------------------------------------------

    def _remisiones(self, doc_version_id: uuid.UUID) -> list[Remision]:
        """Busca sobre el texto completo de la versión, no unidad por unidad.

        En la Resolución 1621/25 la remisión arranca en el artículo 3 y termina
        dos párrafos después: «…identificado como Anexo (IF-…) el cual forma
        parte integrante de la presente». Mirar cada unidad por separado no
        encuentra ninguna de las dos mitades.
        """
        unidades = (
            self.conexion.execute(
                text(
                    "SELECT id, ruta, texto FROM unidades_documentales "
                    " WHERE doc_version_id = :v AND rol_contenido = 'DISPOSITIVO' ORDER BY orden"
                ),
                {"v": doc_version_id},
            )
            .mappings()
            .all()
        )
        if not unidades:
            return []

        completo = ""
        arranques: list[tuple[int, uuid.UUID, str]] = []
        for unidad in unidades:
            arranques.append((len(completo), unidad["id"], unidad["ruta"]))
            completo += unidad["texto"] + "\n"

        halladas: list[Remision] = []
        for oracion, identificador, posicion in remisiones_en(completo):
            # La remisión se atribuye a la unidad donde empieza, que es la que
            # el lector va a citar.
            unidad_id, ruta = arranques[0][1], arranques[0][2]
            for inicio, uid, r in arranques:
                if inicio > posicion:
                    break
                unidad_id, ruta = uid, r
            halladas.append(
                Remision(texto=oracion, identificador=identificador, unidad_id=unidad_id, ruta=ruta)
            )
        return halladas

    def _ya_resuelta(self, norma_id: uuid.UUID, remision: Remision) -> bool:
        return (
            self.conexion.execute(
                text(
                    "SELECT count(*) FROM referencias_pendientes "
                    " WHERE norma_origen_id = :n AND texto_cita = :t AND estado = 'RESUELTA'"
                ),
                {"n": norma_id, "t": remision.texto},
            ).scalar_one()
            > 0
        )

    def _abrir_pendiente(self, norma_id: uuid.UUID, remision: Remision) -> bool:
        ya = self.conexion.execute(
            text(
                "SELECT id FROM referencias_pendientes "
                " WHERE norma_origen_id = :n AND texto_cita = :t AND estado = 'PENDIENTE'"
            ),
            {"n": norma_id, "t": remision.texto},
        ).scalar_one_or_none()
        if ya is not None:
            return False
        evidencia_id = self._evidencia(remision)
        self.conexion.execute(
            text(
                "INSERT INTO referencias_pendientes (norma_origen_id, evidencia_id, texto_cita, "
                " identidad_candidata, motivo, estado, responsable_rol) "
                "VALUES (:n, :e, :t, :i, :m, 'PENDIENTE', :r)"
            ),
            {
                "n": norma_id,
                "e": evidencia_id,
                "t": remision.texto,
                "i": _identidad(remision),
                "m": (
                    f"El cuerpo aprueba un anexo en {remision.ruta} y el procedimiento está "
                    "ahí. Hay que capturarlo y vincularlo"
                    + (
                        f"; la norma lo identifica como {remision.identificador}."
                        if remision.identificador
                        else ", pero la norma no lo identifica: no se resuelve por parecido."
                    )
                ),
                "r": RESPONSABLE,
            },
        )
        return True

    def _bloquear_campos(self, norma_version_id: uuid.UUID, halladas: list[Remision]) -> int:
        identificadores = ", ".join(sorted({r.identificador for r in halladas if r.identificador}))
        motivo = MOTIVO_FALTA + (
            f" Identificado como {identificadores}." if identificadores else ""
        )
        bloqueados = 0
        for campo in CAMPOS_DEL_PROCEDIMIENTO:
            bloqueados += self.conexion.execute(
                text(
                    "INSERT INTO evaluaciones_completitud (norma_version_id, campo_solicitado, "
                    " estado, motivo, fuentes_revisadas) "
                    "VALUES (:v, :c, :e, :m, :f) "
                    "ON CONFLICT (norma_version_id, beneficio_version_id, campo_solicitado) "
                    "DO UPDATE SET estado = EXCLUDED.estado, motivo = EXCLUDED.motivo "
                    " WHERE evaluaciones_completitud.estado <> 'INFORMADO' RETURNING id"
                ),
                {
                    "v": norma_version_id,
                    "c": campo,
                    "e": EstadoCampo.NO_INFORMADO_EN_FUENTES_REVISADAS.value,
                    "m": motivo,
                    "f": '{"anexo": "pendiente de captura y vínculo"}',
                },
            ).rowcount
        return bloqueados

    def _incidencia(self, norma_id: uuid.UUID, halladas: list[Remision]) -> None:
        descripcion = (
            f"La norma aprueba {len(halladas)} anexo(s) que contienen el procedimiento y que "
            "no están vinculados. Publicar los plazos desde el cuerpo solo sería publicar "
            "menos de lo que la norma dice."
        )
        ya = self.conexion.execute(
            text("SELECT id FROM incidencias_revision WHERE descripcion = :d AND tipo = :t"),
            {"d": descripcion, "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value},
        ).scalar_one_or_none()
        if ya is not None:
            return
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision (tipo, severidad, estado, descripcion, "
                " responsable_rol) VALUES (:t, :s, 'ABIERTA', :d, :r)"
            ),
            {
                "t": TipoIncidencia.DATO_FALTANTE_CRITICO.value,
                "s": Severidad.HIGH.value,
                "d": descripcion,
                "r": RESPONSABLE,
            },
        )

    def _evidencia(self, remision: Remision) -> uuid.UUID:
        doc_version = self.conexion.execute(
            text("SELECT doc_version_id FROM unidades_documentales WHERE id = :u"),
            {"u": remision.unidad_id},
        ).scalar_one()
        return self._insertar_evidencia(doc_version, remision.unidad_id, remision.texto)

    def _evidencia_del_anexo(self, doc_version_anexo: uuid.UUID) -> uuid.UUID:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT id, texto FROM unidades_documentales WHERE doc_version_id = :v "
                    " ORDER BY orden LIMIT 1"
                ),
                {"v": doc_version_anexo},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise ValueError(
                f"La versión {doc_version_anexo} no tiene unidades extraídas. Un anexo sin "
                "texto no sustenta los campos que se le atribuirían."
            )
        return self._insertar_evidencia(doc_version_anexo, fila["id"], fila["texto"])

    def _insertar_evidencia(
        self, doc_version_id: uuid.UUID, unidad_id: uuid.UUID, fragmento: str
    ) -> uuid.UUID:
        selector = f"anexo:{unidad_id}"
        ya = self.conexion.execute(
            text("SELECT id FROM evidencias WHERE doc_version_id = :v AND selector = :s"),
            {"v": doc_version_id, "s": selector},
        ).scalar_one_or_none()
        if ya is not None:
            return ya
        return self.conexion.execute(
            text(
                "INSERT INTO evidencias (doc_version_id, unidad_id, fragmento, selector, tipo, "
                " hash_fragmento) VALUES (:v, :u, :f, :s, :t, :h) RETURNING id"
            ),
            {
                "v": doc_version_id,
                "u": unidad_id,
                "f": fragmento,
                "s": selector,
                "t": TipoEvidencia.FRAGMENTO_TEXTO.value,
                "h": hashlib.sha256(fragmento.encode("utf-8")).hexdigest(),
            },
        ).scalar_one()


def _identidad(remision: Remision) -> str:
    import json

    return json.dumps(
        {
            "clase": "ANEXO",
            "identificador": remision.identificador,
            "ruta_en_el_cuerpo": remision.ruta,
        },
        ensure_ascii=False,
    )
