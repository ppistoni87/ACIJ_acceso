"""Extracción: de bytes capturados a documentos, versiones y unidades.

Trabaja sobre capturas ya guardadas, nunca sobre la red. Eso es lo que hace la
extracción repetible: con la misma captura y la misma versión de extractor, el
resultado es el mismo.

Reingerir un contenido idéntico no duplica la versión documental ni sus
unidades. Sí deja la captura nueva, porque haber verificado que el texto no
cambió es información: no es lo mismo "no lo miramos desde marzo" que "lo
miramos ayer y sigue igual".
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoFuenteCandidata,
    Severidad,
    TipoDocumento,
    TipoIncidencia,
)
from backend_normativo.ingesta.adaptadores.base import (
    Adaptador,
    CapturaMaterial,
    DocumentoExtraido,
    ResultadoExtraccion,
)
from backend_normativo.ingesta.adaptadores.infoleg_legacy import AdaptadorInfolegLegacy
from backend_normativo.ingesta.adaptadores.normativa_ba import AdaptadorNormativaBA
from backend_normativo.ingesta.adaptadores.normativa_nacional import AdaptadorNormativaNacional
from backend_normativo.ingesta.adaptadores.pagina_institucional import (
    AdaptadorPaginaInstitucional,
)
from backend_normativo.ingesta.adaptadores.pdf import AdaptadorPdf
from backend_normativo.ingesta.adaptadores.tramite_argentina import (
    AdaptadorTramiteArgentina,
)
from backend_normativo.ingesta.almacen import AlmacenObjetos

# @6: la configuración versionada de la fuente ahora llega al adaptador. Antes
# `CapturaMaterial.config` viajaba siempre vacía, así que el adaptador de PDF
# leía `tipo_documento` de un diccionario que nadie llenaba y caía en OTRO
# —dejando cada PDF normativo fuera de la resolución de identidad—. Cambió lo
# que la extracción produce con las mismas capturas, y por eso cambia el número.
VERSION_EXTRACTOR = "extraccion@15"

# Cobertura mínima para no marcar la extracción como sospechosa. Es una señal
# técnica: por debajo de esto hay texto que no quedó en ninguna unidad, y
# publicar sobre esa versión sería publicar sobre un texto incompleto.
COBERTURA_MINIMA = 0.60


# --- Marcado que viaja dentro del texto -------------------------------------
#
# Una fuente publica su HTML **escapado dentro de la propia página**: la captura
# de D10 tiene catorce `&lt;p&gt;` contra diez `<p>` reales. El extractor hace lo
# correcto —decodifica la entidad, porque eso es texto visible— y el resultado
# es que el marcado queda como contenido y termina en la pantalla de alguien que
# pregunta si lo pueden desalojar:
#
#     <p>CLÁUSULA TRANSITORIA de la Ley 6935: establece que…</p>
#
# No es que el extractor no limpie: limpia la capa que le toca. Faltaba mirar la
# segunda. Se hace acá, en la extracción, y no en cada adaptador: aparecieron
# diez fuentes distintas afectadas, así que el problema no es de un adaptador.
#
# El reconocimiento exige un **nombre de etiqueta conocido**, no cualquier cosa
# entre signos. Una norma puede decir «el monto debe ser < 3 salarios», y
# pasarle un parser de HTML a todo el texto legal rompería justo lo que hay que
# cuidar.
ETIQUETAS_CONOCIDAS = (
    "p|br|div|span|style|script|details|summary|ul|ol|li|table|tr|td|th|"
    "b|i|em|strong|a|h1|h2|h3|h4|h5|h6|blockquote|pre|hr|img"
)
RE_MARCADO = re.compile(rf"</?(?:{ETIQUETAS_CONOCIDAS})(?:\s[^<>]*)?/?>", re.IGNORECASE)
RE_ESPACIOS = re.compile(r"\s+")
# Lo que va entre estas etiquetas no es texto de la norma: es hoja de estilo o
# código. Se saca con su contenido, no sólo la etiqueta.
RE_CON_CONTENIDO = re.compile(
    r"<(style|script)(?:\s[^<>]*)?>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)


def hay_marcado(texto: str) -> bool:
    """Si el texto trae etiquetas HTML como contenido. No modifica nada."""
    return bool(texto) and bool(RE_MARCADO.search(texto))


def limpiar_marcado(texto: str) -> tuple[str, bool]:
    """Saca el marcado incrustado. Devuelve el texto y si hubo que tocarlo.

    Se informa si tocó, para que la corrida lo pueda declarar: una limpieza
    silenciosa esconde que la fuente publica así, y eso es justamente lo que hay
    que poder ver en el informe.
    """
    if not hay_marcado(texto):
        return texto, False
    sin_bloques = RE_CON_CONTENIDO.sub(" ", texto)
    limpio = RE_MARCADO.sub(" ", sin_bloques)
    limpio = RE_ESPACIOS.sub(" ", limpio).strip()
    return limpio, True


@dataclass
class ResultadoPersistencia:
    documentos_creados: int = 0
    versiones_creadas: int = 0
    versiones_repetidas: int = 0
    unidades_creadas: int = 0
    candidatas_creadas: int = 0
    incidencias_creadas: int = 0
    avisos: list[str] = field(default_factory=list)
    version_ids: list[uuid.UUID] = field(default_factory=list)


def adaptadores_por_defecto() -> list[Adaptador]:
    return [
        AdaptadorNormativaNacional(),
        AdaptadorInfolegLegacy(),
        AdaptadorNormativaBA(),
        AdaptadorTramiteArgentina(),
        # Último: los anteriores reconocen su portal por la URL, y el de PDF
        # acepta por contenido. Si fuera primero, se quedaría con cualquier
        # captura que traiga un PDF incrustado en una página.
        AdaptadorPdf(),
        # Último de todos: acepta cualquier página de los portales del corpus,
        # así que puesto antes se quedaría con las que otro sabe leer mejor.
        AdaptadorPaginaInstitucional(),
    ]


class Extractor:
    def __init__(
        self,
        conexion: Connection,
        adaptadores: list[Adaptador] | None = None,
        almacen: AlmacenObjetos | None = None,
        version_extractor: str = VERSION_EXTRACTOR,
    ) -> None:
        self.conexion = conexion
        self.adaptadores = adaptadores or adaptadores_por_defecto()
        self.almacen = almacen or AlmacenObjetos()
        self.version_extractor = version_extractor

    # --- API ---------------------------------------------------------------

    def extraer_captura(self, captura_id: uuid.UUID) -> ResultadoPersistencia:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT c.id, c.sha256_raw, c.mime, c.url_final, u.source_id, "
                    "       cfg.selector_config, f.clase "
                    "FROM capturas c "
                    "JOIN fuente_urls u ON u.id = c.source_url_id "
                    "JOIN fuentes f ON f.source_id = u.source_id "
                    "LEFT JOIN corridas_ingesta ci ON ci.id = c.corrida_id "
                    "LEFT JOIN fuente_config_versiones cfg ON cfg.id = ci.config_version_id "
                    "WHERE c.id = :id"
                ),
                {"id": captura_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise LookupError(f"No existe la captura {captura_id}")

        resultado = ResultadoPersistencia()
        material = CapturaMaterial(
            source_id=fila["source_id"],
            url_final=fila["url_final"] or "",
            contenido=self.almacen.leer(fila["sha256_raw"]),
            mime=fila["mime"],
            sha256=fila["sha256_raw"],
            # La configuración versionada de la fuente, la misma con la que se
            # capturó. `CapturaMaterial` la aceptaba desde el principio y nadie
            # se la pasaba, así que el adaptador de PDF decidía siempre a
            # ciegas: la leía vacía y caía en OTRO.
            config=dict(fila["selector_config"] or {}),
            clase=fila["clase"],
        )

        adaptador = next((a for a in self.adaptadores if a.acepta(material)), None)
        if adaptador is None:
            # El aviso solo vive mientras alguien mira la terminal, y la fuente
            # queda ACTIVE y ACCESIBLE como si hubiera funcionado. Se abre
            # incidencia para que la capacidad quede pendiente hasta que haya un
            # adaptador que lea esto: los bytes están, lo que falta es leerlos.
            texto_aviso = (
                f"Ninguna familia de extracción acepta {material.url_final!r} "
                f"(mime {material.mime!r}). La captura queda guardada sin extraer."
            )
            resultado.avisos.append(texto_aviso)
            self._abrir_incidencia(
                fila["source_id"],
                TipoIncidencia.COBERTURA_EXTRACCION,
                Severidad.HIGH,
                texto_aviso,
                resultado,
            )
            return resultado

        extraccion = adaptador.extraer(material)
        for documento in extraccion.documentos:
            self._persistir_documento(fila, documento, resultado)
        self._persistir_candidatas(fila["source_id"], extraccion, resultado)
        resultado.avisos.extend(a.texto for a in extraccion.avisos)

        if not extraccion.documentos:
            # Un adaptador la aceptó y no salió ningún documento. Los avisos del
            # adaptador explican por qué, pero viven en la salida de la corrida:
            # sin incidencia, la fuente queda ACTIVE y ACCESIBLE como si hubiera
            # traído algo. Se abre una sola, con el motivo que el adaptador dio.
            motivo = " | ".join(a.texto for a in extraccion.avisos) or "sin motivo declarado"
            self._abrir_incidencia(
                fila["source_id"],
                TipoIncidencia.COBERTURA_EXTRACCION,
                Severidad.HIGH,
                f"La captura de {material.url_final!r} no produjo ningún documento: {motivo}",
                resultado,
            )
        return resultado

    def extraer_pendientes(self, source_id: str | None = None) -> ResultadoPersistencia:
        """Capturas sin versión, y las que la tienen de un extractor viejo.

        Lo segundo es lo que le da sentido a numerar el extractor. Antes solo
        entraban las capturas sin versión, así que mejorar la segmentación no
        alcanzaba a nada de lo ya extraído: había que volver a capturar para que
        el reproceso se disparara de rebote. Una fuente que ya no responde
        quedaba con la segmentación vieja para siempre, sin que nada lo dijera.
        """
        filas = (
            self.conexion.execute(
                text(
                    "SELECT c.id FROM capturas c "
                    "JOIN fuente_urls u ON u.id = c.source_url_id "
                    # Un 404 con una página de error extensa se lee como
                    # cualquier HTML y produciría un documento con el texto de
                    # «no encontrado». La captura se conserva —es la prueba de
                    # lo que devolvió esa URL— y no se extrae.
                    "WHERE coalesce(c.http_status, 200) BETWEEN 200 AND 299 "
                    "  AND (CAST(:sid AS text) IS NULL OR u.source_id = :sid) "
                    "  AND (NOT EXISTS (SELECT 1 FROM documento_versiones dv "
                    "                    WHERE dv.captura_id = c.id) "
                    "       OR EXISTS (SELECT 1 FROM documento_versiones dv "
                    "                  WHERE dv.captura_id = c.id "
                    "                    AND dv.extractor_version <> :extractor)) "
                    "ORDER BY c.capturado_en"
                ),
                {"sid": source_id, "extractor": self.version_extractor},
            )
            .scalars()
            .all()
        )

        total = ResultadoPersistencia()
        for captura_id in filas:
            parcial = self.extraer_captura(captura_id)
            total.documentos_creados += parcial.documentos_creados
            total.versiones_creadas += parcial.versiones_creadas
            total.versiones_repetidas += parcial.versiones_repetidas
            total.unidades_creadas += parcial.unidades_creadas
            total.candidatas_creadas += parcial.candidatas_creadas
            total.incidencias_creadas += parcial.incidencias_creadas
            total.avisos.extend(parcial.avisos)
            total.version_ids.extend(parcial.version_ids)
        return total

    # --- Persistencia -------------------------------------------------------

    def _persistir_documento(
        self, captura: dict, documento: DocumentoExtraido, resultado: ResultadoPersistencia
    ) -> None:
        documento_id, creado = self._documento_id(captura["source_id"], documento, resultado)
        resultado.documentos_creados += int(creado)

        hash_texto = hashlib.sha256(documento.texto.encode("utf-8")).hexdigest()
        existente = (
            self.conexion.execute(
                text(
                    "SELECT id, extractor_version FROM documento_versiones "
                    "WHERE documento_id = :d AND hash_texto = :h AND tipo_version = :t"
                ),
                {"d": documento_id, "h": hash_texto, "t": documento.tipo_version.value},
            )
            .mappings()
            .first()
        )
        if existente is not None:
            resultado.version_ids.append(existente["id"])
            if existente["extractor_version"] == self.version_extractor:
                # El texto no cambió y el extractor es el mismo: la captura
                # queda como constancia de que se verificó, sin duplicar nada.
                resultado.versiones_repetidas += 1
                return
            # Mismo texto, extractor distinto: la segmentación pudo mejorar, así
            # que se rehace sobre la misma versión en vez de dejarla vieja.
            self._reprocesar_version(existente["id"], documento, resultado)
            return

        proxima = self.conexion.execute(
            text(
                "SELECT coalesce(max(version), 0) + 1 FROM documento_versiones "
                "WHERE documento_id = :d"
            ),
            {"d": documento_id},
        ).scalar_one()

        version_id = self.conexion.execute(
            text(
                "INSERT INTO documento_versiones ("
                "  documento_id, captura_id, version, tipo_version, fecha_documento, "
                "  tipo_fecha, texto_extraido, hash_texto, modo_extraccion, paginas, "
                "  chars_por_pagina, extraccion_score, identidad_candidata, extractor_version"
                ") VALUES (:d, :c, :v, :tv, :fecha, :tf, :texto, :hash, :modo, :pag, "
                "          :chars, :score, :identidad, :extractor) RETURNING id"
            ),
            {
                "d": documento_id,
                "c": captura["id"],
                "v": proxima,
                "tv": documento.tipo_version.value,
                "fecha": documento.fecha_documento,
                "tf": documento.tipo_fecha.value,
                "texto": documento.texto,
                "hash": hash_texto,
                "modo": documento.modo_extraccion.value,
                "pag": documento.paginas,
                "chars": json.dumps(documento.chars_por_pagina)
                if documento.chars_por_pagina
                else None,
                "score": documento.extraccion_score,
                "identidad": json.dumps(documento.identidad, ensure_ascii=False)
                if documento.identidad
                else None,
                "extractor": self.version_extractor,
            },
        ).scalar_one()
        resultado.versiones_creadas += 1
        resultado.version_ids.append(version_id)

        resultado.unidades_creadas += self._persistir_unidades(version_id, documento, resultado)
        self._controlar_cobertura(captura, documento, version_id, resultado)

    def _reprocesar_version(
        self, version_id: uuid.UUID, documento: DocumentoExtraido, resultado: ResultadoPersistencia
    ) -> None:
        """Rehace las unidades de una versión ya publicada por otro extractor.

        Solo se permite mientras la versión no está aprobada —una versión
        publicada se corrige creando otra, no editando la que ya se sirvió— y
        mientras nadie haya citado sus unidades. Lo segundo es más fuerte que lo
        primero y no depende de la revisión: una evidencia localiza una unidad,
        y rehacer la segmentación la borra. La cita quedaría apuntando a algo
        que ya no existe, que es exactamente lo que una evidencia está para
        impedir.

        Cuando eso pasa, mejorar la segmentación de esa versión deja de ser un
        reproceso y pasa a ser una decisión: hay que volver a curar lo que la
        citaba. Se avisa con el número de citas para que se vea el tamaño de esa
        decisión, y no se toca nada.
        """
        citas = self.conexion.execute(
            text(
                "SELECT count(*) FROM evidencias e "
                "  JOIN unidades_documentales u ON u.id = e.unidad_id "
                " WHERE u.doc_version_id = :dv"
            ),
            {"dv": version_id},
        ).scalar_one()
        if citas:
            resultado.avisos.append(
                f"La versión {version_id} tiene {citas} evidencia(s) sobre sus unidades: no se "
                "reprocesa. Rehacer la segmentación borraría las unidades que esas citas "
                "localizan, y una cita que apunta a una unidad que ya no existe no se puede "
                "verificar. Para aplicarle el extractor nuevo hay que volver a curar lo que la "
                "cita."
            )
            resultado.versiones_repetidas += 1
            return

        aprobada = self.conexion.execute(
            text(
                "SELECT count(*) FROM norma_versiones nv "
                "JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
                "WHERE nv.doc_version_id = :dv "
                "  AND rv.estado_revision IN ('APPROVED', 'PUBLISHED')"
            ),
            {"dv": version_id},
        ).scalar_one()
        if aprobada:
            resultado.avisos.append(
                f"La versión {version_id} ya fue aprobada con otro extractor: no se "
                "reprocesa. Corregirla exige una versión nueva."
            )
            resultado.versiones_repetidas += 1
            return

        self.conexion.execute(
            text("DELETE FROM unidades_documentales WHERE doc_version_id = :dv"),
            {"dv": version_id},
        )
        self.conexion.execute(
            text(
                "UPDATE documento_versiones SET extractor_version = :v, "
                "  extraccion_score = :s, identidad_candidata = :i WHERE id = :dv"
            ),
            {
                "v": self.version_extractor,
                "s": documento.extraccion_score,
                "i": json.dumps(documento.identidad, ensure_ascii=False)
                if documento.identidad
                else None,
                "dv": version_id,
            },
        )
        resultado.unidades_creadas += self._persistir_unidades(version_id, documento, resultado)
        resultado.versiones_creadas += 1

    def _documento_id(
        self,
        source_id: str,
        documento: DocumentoExtraido,
        resultado: ResultadoPersistencia | None = None,
    ) -> tuple[uuid.UUID, bool]:
        if documento.external_id:
            fila = (
                self.conexion.execute(
                    text(
                        "SELECT id, tipo FROM documentos  WHERE source_id = :s AND external_id = :e"
                    ),
                    {"s": source_id, "e": documento.external_id},
                )
                .mappings()
                .first()
            )
            if fila is not None:
                self._corregir_tipo(fila, documento, source_id, resultado)
                return fila["id"], False
        nuevo = self.conexion.execute(
            text(
                "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
                "VALUES (:s, :t, :titulo, :e) RETURNING id"
            ),
            {
                "s": source_id,
                "t": documento.tipo.value,
                "titulo": documento.titulo,
                "e": documento.external_id,
            },
        ).scalar_one()
        return nuevo, True

    def _corregir_tipo(
        self,
        fila: dict,
        documento: DocumentoExtraido,
        source_id: str,
        resultado: ResultadoPersistencia | None,
    ) -> None:
        """Un documento que quedó como OTRO por falta de declaración se corrige.

        Solo en ese sentido. Pasar de OTRO a algo concreto es reparar una
        clasificación que nunca se hizo; reclasificar un documento que ya tenía
        tipo es una decisión, y una decisión no se toma en silencio dentro de
        una reextracción.
        """
        if fila["tipo"] != TipoDocumento.OTRO.value:
            return
        if documento.tipo is TipoDocumento.OTRO:
            return
        self.conexion.execute(
            text("UPDATE documentos SET tipo = :t WHERE id = :id"),
            {"t": documento.tipo.value, "id": fila["id"]},
        )
        if resultado is not None:
            resultado.avisos.append(
                f"{source_id}: el documento estaba como OTRO y la fuente ahora declara "
                f"{documento.tipo.value}. Con OTRO quedaba fuera de la resolución de "
                "identidad; se corrige."
            )

    def _persistir_unidades(
        self,
        version_id: uuid.UUID,
        documento: DocumentoExtraido,
        resultado: ResultadoPersistencia | None = None,
    ) -> int:
        ids: dict[int, uuid.UUID] = {}
        limpiadas = 0
        for indice, unidad in enumerate(documento.unidades):
            padre = ids.get(unidad.padre_indice) if unidad.padre_indice is not None else None
            # Segunda capa de marcado: hay fuentes que publican su HTML escapado
            # dentro de la página, así que el texto visible —el que el extractor
            # toma, bien— trae etiquetas como contenido. Se limpia acá, que es
            # por donde pasan todos los adaptadores.
            texto_unidad, se_limpio = limpiar_marcado(unidad.texto)
            limpiadas += int(se_limpio)
            nuevo = self.conexion.execute(
                text(
                    "INSERT INTO unidades_documentales ("
                    "  doc_version_id, parent_id, tipo, numero, sufijo, rotulo, ruta, orden, "
                    "  texto, inicio, fin, pagina_desde, pagina_hasta, rol_contenido"
                    ") VALUES (:dv, :padre, :tipo, :numero, :sufijo, :rotulo, :ruta, :orden, "
                    "          :texto, :inicio, :fin, :pd, :ph, :rol) RETURNING id"
                ),
                {
                    "dv": version_id,
                    "padre": padre,
                    "tipo": unidad.tipo.value,
                    "numero": unidad.numero,
                    "sufijo": unidad.sufijo,
                    "rotulo": unidad.rotulo,
                    "ruta": unidad.ruta,
                    "orden": unidad.orden,
                    "texto": texto_unidad,
                    "inicio": unidad.inicio,
                    "fin": unidad.fin,
                    "pd": unidad.pagina_desde,
                    "ph": unidad.pagina_hasta,
                    "rol": unidad.rol_contenido.value,
                },
            ).scalar_one()
            ids[indice] = nuevo
        # Se declara. Una limpieza silenciosa esconde que la fuente publica así,
        # y eso es justamente lo que hay que ver en el informe de la corrida.
        if limpiadas and resultado is not None:
            resultado.avisos.append(
                f"La versión {version_id} traía marcado HTML dentro del texto en {limpiadas} "
                "unidad(es): la fuente publica su HTML escapado dentro de la propia página. Se "
                "sacó al guardar. Si el número crece, cambió la maquetación del origen."
            )
        return len(ids)

    def _controlar_cobertura(
        self,
        captura: dict,
        documento: DocumentoExtraido,
        version_id: uuid.UUID,
        resultado: ResultadoPersistencia,
    ) -> None:
        """Registra el control DQ06 y abre incidencia si quedó texto afuera."""
        clasificados = sum(len(u.texto) for u in documento.unidades)
        total = len(documento.texto)
        cobertura = clasificados / total if total else 0.0
        pasa = cobertura >= COBERTURA_MINIMA or not documento.unidades

        self.conexion.execute(
            text(
                "INSERT INTO controles_calidad "
                "(corrida_id, control_id, version, resultado, severidad, observado, esperado) "
                "SELECT c.corrida_id, 'DQ06', :ver, :res, :sev, :obs, :esp "
                "FROM capturas c WHERE c.id = :cap"
            ),
            {
                "ver": VERSION_EXTRACTOR,
                "res": "PASA" if pasa else "FALLA",
                "sev": Severidad.MEDIUM.value if pasa else Severidad.HIGH.value,
                "obs": json.dumps(
                    {
                        "doc_version_id": str(version_id),
                        "cobertura": round(cobertura, 4),
                        "unidades": len(documento.unidades),
                        "caracteres_totales": total,
                    }
                ),
                "esp": json.dumps({"cobertura_minima": COBERTURA_MINIMA}),
                "cap": captura["id"],
            },
        )
        if not pasa:
            self._abrir_incidencia(
                captura["source_id"],
                TipoIncidencia.COBERTURA_EXTRACCION,
                Severidad.HIGH,
                f"La versión {version_id} clasificó el {cobertura:.0%} del texto. "
                "Queda texto sin unidad asignada: publicar sobre esta versión sería "
                "publicar sobre un texto incompleto.",
                resultado,
            )
        for aviso in documento.avisos:
            self._abrir_incidencia(
                captura["source_id"], aviso.tipo, aviso.severidad, aviso.texto, resultado
            )

    def _persistir_candidatas(
        self, source_id: str, extraccion: ResultadoExtraccion, resultado: ResultadoPersistencia
    ) -> None:
        """Las URLs descubiertas entran como candidatas, no como fuentes.

        Promoverlas es una decisión de revisión: un enlace en un texto no prueba
        que sea una fuente del alcance.
        """
        for descubierta in extraccion.urls_descubiertas:
            creada = self.conexion.execute(
                text(
                    "INSERT INTO fuentes_candidatas "
                    "(source_id_origen, url, relacion, tipo_esperado, estado) "
                    "VALUES (:s, :u, :rel, :tipo, :estado) "
                    "ON CONFLICT (source_id_origen, url) DO NOTHING RETURNING id"
                ),
                {
                    "s": source_id,
                    "u": descubierta.url,
                    "rel": descubierta.relacion,
                    "tipo": descubierta.tipo_esperado,
                    "estado": EstadoFuenteCandidata.NUEVA.value,
                },
            ).scalar_one_or_none()
            resultado.candidatas_creadas += int(creada is not None)

    def _abrir_incidencia(
        self,
        source_id: str,
        tipo: TipoIncidencia,
        severidad: Severidad,
        descripcion: str,
        resultado: ResultadoPersistencia,
    ) -> None:
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(source_id, tipo, severidad, estado, descripcion, responsable_rol) "
                "VALUES (:s, :t, :sev, 'ABIERTA', :d, 'curacion_juridica')"
            ),
            {"s": source_id, "t": tipo.value, "sev": severidad.value, "d": descripcion},
        )
        resultado.incidencias_creadas += 1
