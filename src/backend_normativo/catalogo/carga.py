"""Carga idempotente del catálogo de fuentes.

Reejecutar la carga sobre la misma base no duplica filas ni pierde el estado
que la operación haya avanzado: actualiza la procedencia documental y agrega las
URLs nuevas, y deja intactos los campos que la ingesta administra
(`estado`, `access_status`), porque el manifiesto describe el punto de partida y
no el presente.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.catalogo import derivacion as der
from backend_normativo.catalogo.jurisdicciones import SEMILLA
from backend_normativo.catalogo.manifiesto import Manifiesto, cargar_manifiesto
from backend_normativo.db import vocabularios as voc


@dataclass
class ResultadoCarga:
    jurisdicciones_creadas: int = 0
    fuentes_creadas: int = 0
    fuentes_actualizadas: int = 0
    urls_creadas: int = 0
    configuraciones_creadas: int = 0
    incidencias_creadas: int = 0
    advertencias: list[str] = field(default_factory=list)

    @property
    def fuentes_totales(self) -> int:
        return self.fuentes_creadas + self.fuentes_actualizadas


def cargar_jurisdicciones(conexion: Connection) -> int:
    creadas = 0
    for j in SEMILLA:
        resultado = conexion.execute(
            text(
                "INSERT INTO jurisdicciones (id, parent_id, nombre, nivel, codigo_oficial) "
                "VALUES (:id, :parent, :nombre, :nivel, :codigo) "
                "ON CONFLICT (id) DO UPDATE SET nombre = EXCLUDED.nombre "
                "RETURNING (xmax = 0) AS insertada"
            ),
            {
                "id": j.id,
                "parent": j.parent_id,
                "nombre": j.nombre,
                "nivel": j.nivel.value,
                "codigo": j.codigo_oficial,
            },
        ).scalar_one()
        creadas += int(bool(resultado))
    return creadas


def cargar_catalogo(conexion: Connection, manifiesto: Manifiesto | None = None) -> ResultadoCarga:
    manifiesto = manifiesto or cargar_manifiesto()
    resultado = ResultadoCarga()
    resultado.advertencias.extend(manifiesto.validar_coherencia())

    resultado.jurisdicciones_creadas = cargar_jurisdicciones(conexion)

    # Primera pasada sin alias: la clave foránea de alias exige que la fuente
    # canónica ya exista, y el manifiesto no garantiza un orden topológico.
    for fuente in manifiesto.sources:
        insertada = conexion.execute(
            text(
                "INSERT INTO fuentes ("
                "  source_id, nombre, clase, estado, access_status, prioridad, "
                "  politica_acceso, motivo_estado, responsable_rol, alcance, relacionadas, "
                "  origen, manual_pagina, origen_url_status, tarea, aceptacion_especifica, "
                "  tablas_destino, referencia_selectores, referencia_campos"
                ") VALUES ("
                "  :source_id, :nombre, :clase, :estado, :access_status, :prioridad, "
                "  :politica, :motivo, :responsable, :alcance, :relacionadas, "
                "  :origen, :pagina, :url_status, :tarea, :aceptacion, "
                "  :destino, :selectores, :campos"
                ") ON CONFLICT (source_id) DO UPDATE SET "
                # La procedencia documental y las notas del manual se refrescan;
                # el estado operativo no, porque lo administra la ingesta.
                "  nombre = EXCLUDED.nombre, "
                "  clase = EXCLUDED.clase, "
                "  prioridad = EXCLUDED.prioridad, "
                "  politica_acceso = EXCLUDED.politica_acceso, "
                "  responsable_rol = EXCLUDED.responsable_rol, "
                "  relacionadas = EXCLUDED.relacionadas, "
                "  origen = EXCLUDED.origen, "
                "  manual_pagina = EXCLUDED.manual_pagina, "
                "  origen_url_status = EXCLUDED.origen_url_status, "
                "  tarea = EXCLUDED.tarea, "
                "  aceptacion_especifica = EXCLUDED.aceptacion_especifica, "
                "  tablas_destino = EXCLUDED.tablas_destino, "
                "  referencia_selectores = EXCLUDED.referencia_selectores, "
                "  referencia_campos = EXCLUDED.referencia_campos "
                "RETURNING (xmax = 0) AS insertada"
            ),
            {
                "source_id": fuente.source_id,
                "nombre": fuente.title,
                "clase": der.clase_de(fuente).value,
                "estado": der.estado_de(fuente).value,
                "access_status": der.access_status_de(fuente).value,
                "prioridad": fuente.priority,
                "politica": der.politica_acceso_de(fuente).value,
                "motivo": der.motivo_estado_de(fuente),
                "responsable": fuente.owner_capability,
                "alcance": fuente.task,
                "relacionadas": _json(fuente.related_source_ids),
                "origen": fuente.origin,
                "pagina": fuente.manual_page,
                "url_status": fuente.url_status,
                "tarea": fuente.task,
                "aceptacion": _json(fuente.specific_acceptance),
                "destino": _json(fuente.target_tables),
                "selectores": fuente.manual_selector_reference,
                "campos": fuente.manual_fields_reference,
            },
        ).scalar_one()
        if insertada:
            resultado.fuentes_creadas += 1
        else:
            resultado.fuentes_actualizadas += 1

    # Segunda pasada: alias, ya con todas las fuentes presentes.
    for fuente in manifiesto.sources:
        if fuente.alias_of:
            conexion.execute(
                text("UPDATE fuentes SET alias_of = :canonica WHERE source_id = :sid"),
                {"canonica": fuente.alias_of, "sid": fuente.source_id},
            )

    for fuente in manifiesto.sources:
        for indice, url in enumerate(fuente.urls):
            insertada = conexion.execute(
                text(
                    "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso, es_canonica) "
                    "VALUES (:sid, :url, :rol, :acceso, :canonica) "
                    "ON CONFLICT (source_id, url) DO UPDATE SET rol = EXCLUDED.rol "
                    "RETURNING (xmax = 0) AS insertada"
                ),
                {
                    "sid": fuente.source_id,
                    "url": url,
                    "rol": der.rol_url(indice, fuente).value,
                    "acceso": der.tipo_acceso_de(fuente, url).value,
                    "canonica": indice == 0,
                },
            ).scalar_one()
            resultado.urls_creadas += int(bool(insertada))

        insertada = conexion.execute(
            text(
                "INSERT INTO fuente_config_versiones ("
                "  source_id, version, adaptador, frecuencia, ttl_defecto, presupuesto, "
                "  politica_version, selector_config"
                ") VALUES (:sid, 1, :adaptador, :frecuencia, :ttl, :presupuesto, :politica, "
                "          :selector) "
                # La configuración se refresca: si la derivación mejora, las
                # fuentes ya cargadas tienen que recibirla sin borrar la base.
                "ON CONFLICT (source_id, version) DO UPDATE SET "
                "  selector_config = EXCLUDED.selector_config "
                # `xmax = 0` distingue la fila recién insertada de la
                # actualizada: sin eso, refrescar la configuración de una fuente
                # ya cargada se contaría como una configuración nueva.
                "RETURNING (xmax = 0) AS creada"
            ),
            {
                "sid": fuente.source_id,
                "adaptador": der.adaptador_de(fuente).value,
                "frecuencia": der.frecuencia_de(fuente),
                "ttl": der.ttl_de(fuente),
                "presupuesto": _json(der.presupuesto_de(fuente)),
                "politica": "acceso-fuentes-publicas@1",
                "selector": _json(der.selector_config_de(fuente)),
            },
        ).scalar_one_or_none()
        resultado.configuraciones_creadas += int(bool(insertada))

    resultado.incidencias_creadas = _registrar_brechas(conexion, manifiesto)
    return resultado


def _registrar_brechas(conexion: Connection, manifiesto: Manifiesto) -> int:
    """Las fuentes sin URL conocida quedan como incidencia abierta.

    Es la única forma honesta de tratarlas: no se inventa una dirección, no se
    las descarta y no desaparecen del denominador de cobertura. Cada una tiene
    responsable y motivo, y sigue contando como fuente pendiente.
    """
    creadas = 0
    for fuente in manifiesto.sources:
        if not fuente.sin_url_conocida:
            continue
        ya_existe = conexion.execute(
            text(
                "SELECT 1 FROM incidencias_revision "
                "WHERE source_id = :sid AND tipo = 'ACCESO_BLOQUEADO' AND estado <> 'RESUELTA'"
            ),
            {"sid": fuente.source_id},
        ).first()
        if ya_existe:
            continue
        conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(source_id, tipo, severidad, estado, descripcion, responsable_rol, candidatos) "
                "VALUES (:sid, 'ACCESO_BLOQUEADO', :sev, 'ABIERTA', :desc, :rol, :cand)"
            ),
            {
                "sid": fuente.source_id,
                "sev": voc.Severidad.HIGH.value
                if fuente.priority in ("P0", "P1")
                else voc.Severidad.MEDIUM.value,
                "desc": (
                    f"{fuente.source_id} no tiene URL inequívoca en el manual "
                    f"({fuente.origin}). Hay que recuperar la identidad desde el relevamiento "
                    "original o resolverla por carga manual trazada. No se fabrica una "
                    f"dirección. Tarea declarada: {fuente.task or 'sin tarea declarada'}"
                ),
                "rol": fuente.owner_capability,
                "cand": _json(fuente.related_source_ids),
            },
        )
        creadas += 1
    return creadas


def _json(valor: object) -> str | None:
    import json

    if valor is None:
        return None
    return json.dumps(valor, ensure_ascii=False)
