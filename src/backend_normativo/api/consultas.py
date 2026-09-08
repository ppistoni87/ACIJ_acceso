"""Consultas SQL de la API.

Están acá y no en las rutas por una razón del contrato: el modelo conversacional
consume operaciones tipadas y no emite SQL. Cada consulta es determinista y se
resuelve contra un release, para que dos respuestas a la misma pregunta con el
mismo `known_at` sean idénticas.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Connection, text

from backend_normativo.api.contratos import (
    CoberturaDeCampos,
    Evidencia,
    NormaResumen,
    RelacionResumen,
    VersionNorma,
)
from backend_normativo.db.vocabularios import CAMPOS_SOLICITADOS


def _identificadores(conexion: Connection, norma_id: uuid.UUID) -> dict[str, str]:
    return {
        fila[0]: fila[1]
        for fila in conexion.execute(
            text("SELECT namespace, valor FROM norma_identificadores WHERE norma_id = :n"),
            {"n": norma_id},
        )
    }


def _cobertura(conexion: Connection, norma_id: uuid.UUID) -> CoberturaDeCampos:
    """Estado de los siete campos, tomando el mejor estado por campo.

    "Mejor" significa el más informativo: si alguna versión de la norma tiene el
    campo informado, la cobertura lo refleja. La ficha por versión conserva el
    detalle.
    """
    orden = {
        "INFORMADO": 4,
        "NO_APLICA_JUSTIFICADO": 3,
        "EN_CONFLICTO": 2,
        "NO_INFORMADO_EN_FUENTES_REVISADAS": 1,
        "PENDIENTE": 0,
    }
    estados: dict[str, str] = dict.fromkeys(CAMPOS_SOLICITADOS, "PENDIENTE")
    filas = conexion.execute(
        text(
            "SELECT e.campo_solicitado, e.estado FROM evaluaciones_completitud e "
            "  JOIN norma_versiones nv ON nv.registro_version_id = e.norma_version_id "
            " WHERE nv.norma_id = :n"
        ),
        {"n": norma_id},
    )
    for campo, estado in filas:
        if orden.get(estado, 0) > orden.get(estados.get(campo, "PENDIENTE"), 0):
            estados[campo] = estado
    return CoberturaDeCampos(**estados)


def buscar_normas(
    conexion: Connection,
    *,
    texto_libre: str | None,
    jurisdiccion: str | None,
    tipo: str | None,
    numero: str | None,
    anio: int | None,
    materia: str | None,
    limite: int,
    desplazamiento: int,
) -> tuple[list[NormaResumen], int]:
    condiciones = ["1 = 1"]
    parametros: dict[str, object] = {}
    if jurisdiccion:
        condiciones.append("n.jurisdiccion_id = :jurisdiccion")
        parametros["jurisdiccion"] = jurisdiccion
    if tipo:
        condiciones.append("n.tipo = :tipo")
        parametros["tipo"] = tipo
    if numero:
        condiciones.append("n.numero = :numero")
        parametros["numero"] = numero
    if anio:
        condiciones.append("n.anio = :anio")
        parametros["anio"] = anio
    if materia:
        condiciones.append(":materia = ANY(n.materias)")
        parametros["materia"] = materia
    if texto_libre:
        # Búsqueda textual en español sobre el título; el texto completo se
        # consulta por `POST /v1/recuperacion`, que devuelve citas.
        condiciones.append("to_tsvector('spanish', n.titulo) @@ plainto_tsquery('spanish', :texto)")
        parametros["texto"] = texto_libre

    donde = " AND ".join(condiciones)
    total = conexion.execute(
        text(f"SELECT count(*) FROM normas n WHERE {donde}"), parametros
    ).scalar_one()

    filas = conexion.execute(
        text(
            "SELECT n.id, n.jurisdiccion_id, n.tipo, n.numero, n.anio, n.titulo, "
            "       o.nombre AS emisor, n.identidad_incierta, "
            "       (SELECT count(*) FROM norma_versiones nv "
            "          JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
            "         WHERE nv.norma_id = n.id AND rv.estado_revision = 'PUBLISHED') AS pub "
            f"  FROM normas n LEFT JOIN organismos o ON o.id = n.emisor_id WHERE {donde} "
            " ORDER BY n.anio DESC NULLS LAST, n.numero LIMIT :limite OFFSET :desp"
        ),
        {**parametros, "limite": limite, "desp": desplazamiento},
    ).mappings()

    return (
        [
            NormaResumen(
                norma_id=fila["id"],
                jurisdiccion=fila["jurisdiccion_id"],
                tipo=fila["tipo"],
                numero=fila["numero"],
                anio=fila["anio"],
                titulo=fila["titulo"],
                emisor=fila["emisor"],
                identificadores=_identificadores(conexion, fila["id"]),
                identidad_incierta=fila["identidad_incierta"],
                versiones_publicadas=fila["pub"],
                cobertura_de_campos=_cobertura(conexion, fila["id"]),
            )
            for fila in filas
        ],
        total,
    )


def obtener_norma(conexion: Connection, norma_id: uuid.UUID) -> NormaResumen | None:
    fila = (
        conexion.execute(
            text(
                "SELECT n.id, n.jurisdiccion_id, n.tipo, n.numero, n.anio, n.titulo, "
                "       o.nombre AS emisor, n.identidad_incierta, "
                "       (SELECT count(*) FROM norma_versiones nv "
                "          JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
                "         WHERE nv.norma_id = n.id AND rv.estado_revision = 'PUBLISHED') AS pub "
                "  FROM normas n LEFT JOIN organismos o ON o.id = n.emisor_id WHERE n.id = :id"
            ),
            {"id": norma_id},
        )
        .mappings()
        .first()
    )
    if fila is None:
        return None
    return NormaResumen(
        norma_id=fila["id"],
        jurisdiccion=fila["jurisdiccion_id"],
        tipo=fila["tipo"],
        numero=fila["numero"],
        anio=fila["anio"],
        titulo=fila["titulo"],
        emisor=fila["emisor"],
        identificadores=_identificadores(conexion, fila["id"]),
        identidad_incierta=fila["identidad_incierta"],
        versiones_publicadas=fila["pub"],
        cobertura_de_campos=_cobertura(conexion, fila["id"]),
    )


def versiones_de(
    conexion: Connection,
    norma_id: uuid.UUID,
    *,
    fecha: dt.date,
    momento: dt.datetime,
    capacidad: str,
) -> list[VersionNorma]:
    """Versiones de la norma, cada una con si puede servirse y por qué no."""
    filas = (
        conexion.execute(
            text(
                "SELECT nv.registro_version_id, nv.tipo_version, nv.estado_legal_declarado, "
                "       nv.estado_legal_validado, rv.valid_tipo, rv.valid_desde, rv.valid_hasta, "
                "       rv.verificado_en, rv.reverificar_antes_de "
                "  FROM norma_versiones nv "
                "  JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
                " WHERE nv.norma_id = :n ORDER BY rv.numero_version"
            ),
            {"n": norma_id},
        )
        .mappings()
        .all()
    )

    versiones: list[VersionNorma] = []
    for fila in filas:
        motivos = list(
            conexion.execute(
                text("SELECT bn_motivos_no_servible(:v, :f, :k, :c)"),
                {"v": fila["registro_version_id"], "f": fecha, "k": momento, "c": capacidad},
            ).scalars()
        )
        versiones.append(
            VersionNorma(
                version_id=fila["registro_version_id"],
                tipo_version=fila["tipo_version"],
                estado_legal_declarado=fila["estado_legal_declarado"],
                estado_legal_validado=fila["estado_legal_validado"],
                valid_tipo=fila["valid_tipo"],
                valid_desde=fila["valid_desde"],
                valid_hasta=fila["valid_hasta"],
                verificado_en=fila["verificado_en"],
                reverificar_antes_de=fila["reverificar_antes_de"],
                servible=not motivos,
                motivos_no_servible=motivos,
            )
        )
    return versiones


def relaciones_de(conexion: Connection, norma_id: uuid.UUID) -> list[RelacionResumen]:
    filas = conexion.execute(
        text(
            "SELECT r.tipo, 'SALIENTE' AS direccion, r.alcance, r.estado_revision, "
            "       d.tipo || ' ' || coalesce(d.numero, '?') || '/' || "
            "       coalesce(d.anio::text, '?') AS norma "
            "  FROM relaciones_normativas r JOIN normas d ON d.id = r.norma_destino_id "
            " WHERE r.norma_origen_id = :n "
            " UNION ALL "
            "SELECT r.tipo, 'ENTRANTE', r.alcance, r.estado_revision, "
            "       o.tipo || ' ' || coalesce(o.numero, '?') || '/' || "
            "       coalesce(o.anio::text, '?') "
            "  FROM relaciones_normativas r JOIN normas o ON o.id = r.norma_origen_id "
            " WHERE r.norma_destino_id = :n "
            " ORDER BY 2, 1"
        ),
        {"n": norma_id},
    ).mappings()
    return [
        RelacionResumen(
            tipo=fila["tipo"],
            direccion=fila["direccion"],
            norma=fila["norma"],
            alcance=fila["alcance"],
            estado_revision=fila["estado_revision"],
        )
        for fila in filas
    ]


def campos_de(conexion: Connection, norma_id: uuid.UUID) -> tuple[dict[str, dict], list[str]]:
    """Los siete campos proyectados, con sus valores publicados y su estado.

    Solo se proyectan afirmaciones publicadas. Un candidato en revisión aparece
    contado, no como valor: es lo que distingue "lo estamos mirando" de "esto
    dice la norma".
    """
    campos: dict[str, dict] = {}
    faltantes: list[str] = []

    for campo in CAMPOS_SOLICITADOS:
        estado = (
            conexion.execute(
                text(
                    "SELECT e.estado, e.motivo FROM evaluaciones_completitud e "
                    "  JOIN norma_versiones nv ON nv.registro_version_id = e.norma_version_id "
                    " WHERE nv.norma_id = :n AND e.campo_solicitado = :c "
                    " ORDER BY CASE e.estado WHEN 'INFORMADO' THEN 0 ELSE 1 END LIMIT 1"
                ),
                {"n": norma_id, "c": campo},
            )
            .mappings()
            .first()
        )

        valores = (
            conexion.execute(
                text(
                    "SELECT a.valor, a.motivo FROM afirmaciones a "
                    "  JOIN norma_versiones nv ON nv.registro_version_id = a.registro_version_id "
                    " WHERE nv.norma_id = :n AND a.campo_path = :c "
                    "   AND a.estado_revision = 'PUBLISHED'"
                ),
                {"n": norma_id, "c": campo},
            )
            .mappings()
            .all()
        )

        en_revision = conexion.execute(
            text(
                "SELECT count(*) FROM afirmaciones a "
                "  JOIN norma_versiones nv ON nv.registro_version_id = a.registro_version_id "
                " WHERE nv.norma_id = :n AND a.campo_path = :c "
                "   AND a.estado_revision = 'CANDIDATE'"
            ),
            {"n": norma_id, "c": campo},
        ).scalar_one()

        campos[campo] = {
            "estado": estado["estado"] if estado else "PENDIENTE",
            "motivo": estado["motivo"] if estado else "El campo todavía no fue evaluado.",
            "valores": [v["valor"] for v in valores],
            "candidatos_en_revision": en_revision,
        }
        if not valores:
            faltantes.append(campo)

    return campos, faltantes


def evidencias_de(
    conexion: Connection, norma_id: uuid.UUID, *, limite: int = 20
) -> list[Evidencia]:
    filas = conexion.execute(
        text(
            "SELECT DISTINCT ON (e.id) e.id, e.fragmento, u.ruta, f.url, d.source_id, "
            "       cap.capturado_en, "
            "       n.tipo || ' ' || coalesce(n.numero, '?') AS norma "
            "  FROM afirmaciones a "
            "  JOIN evidencias e ON e.id = a.evidencia_id "
            "  JOIN norma_versiones nv ON nv.registro_version_id = a.registro_version_id "
            "  JOIN normas n ON n.id = nv.norma_id "
            "  JOIN documento_versiones dvers ON dvers.id = e.doc_version_id "
            "  JOIN documentos d ON d.id = dvers.documento_id "
            "  JOIN capturas cap ON cap.id = dvers.captura_id "
            "  JOIN fuente_urls f ON f.id = cap.source_url_id "
            "  LEFT JOIN unidades_documentales u ON u.id = e.unidad_id "
            " WHERE nv.norma_id = :n AND a.estado_revision = 'PUBLISHED' "
            " LIMIT :limite"
        ),
        {"n": norma_id, "limite": limite},
    ).mappings()
    return [
        Evidencia(
            evidencia_id=fila["id"],
            fragmento=fila["fragmento"],
            norma=fila["norma"],
            unidad=fila["ruta"],
            url_fuente=fila["url"],
            source_id=fila["source_id"],
            capturado_en=fila["capturado_en"],
        )
        for fila in filas
    ]


def referencias_pendientes_de(conexion: Connection, norma_id: uuid.UUID) -> list[dict]:
    filas = conexion.execute(
        text(
            "SELECT texto_cita, identidad_candidata, motivo FROM referencias_pendientes "
            " WHERE norma_origen_id = :n AND estado = 'PENDIENTE' LIMIT 50"
        ),
        {"n": norma_id},
    ).mappings()
    return [
        {
            "texto_cita": fila["texto_cita"],
            "identidad_candidata": fila["identidad_candidata"],
            "motivo": fila["motivo"],
        }
        for fila in filas
    ]
