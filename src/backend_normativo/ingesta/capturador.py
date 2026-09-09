"""Corridas de captura: del catálogo a bytes inmutables en la base.

Una corrida toma las URLs de una fuente, las pide con la política vigente y deja
una fila de `capturas` por cada resultado. No extrae nada: la extracción es el
paso siguiente y trabaja sobre estos bytes, no sobre la red.

Lo que esta capa garantiza:

* los contadores de la corrida reconcilian, y una corrida incompleta no queda
  marcada como completa;
* un `304 Not Modified` reutiliza el objeto y el hash de la captura previa en
  lugar de inventar un cuerpo descargado;
* un acceso limitado o un fallo de TLS degradan la fuente y abren una
  incidencia, en vez de convertirse en "no hay datos".
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import Connection, text

from backend_normativo.db import vocabularios as voc
from backend_normativo.ingesta.almacen import AlmacenObjetos
from backend_normativo.ingesta.cliente import ClienteCaptura, Descarga
from backend_normativo.ingesta.politica import Presupuesto

VERSION_EXTRACTOR = "capturador@1"


@dataclass
class ResultadoCaptura:
    corrida_id: uuid.UUID
    source_id: str
    solicitadas: int = 0
    descargadas: int = 0
    procesadas: int = 0
    rechazadas: int = 0
    no_modificadas: int = 0
    # URLs que esta corrida no volvió a pedir porque una corrida anterior ya
    # las había hecho y dejó constancia en el checkpoint.
    reanudadas: int = 0
    reanudada: bool = False
    capturas: list[uuid.UUID] = field(default_factory=list)
    incidencias: list[str] = field(default_factory=list)
    estado: voc.EstadoCorrida = voc.EstadoCorrida.EN_CURSO


class Capturador:
    def __init__(
        self,
        conexion: Connection,
        cliente: ClienteCaptura | None = None,
        almacen: AlmacenObjetos | None = None,
        confirmar: Callable[[], None] | None = None,
    ) -> None:
        self.conexion = conexion
        self.cliente = cliente or ClienteCaptura()
        self.almacen = almacen or AlmacenObjetos()
        # Un checkpoint que nadie confirma no sobrevive a la interrupción que
        # tiene que sobrevivir: si toda la corrida va en una transacción, el
        # corte la revierte entera y el checkpoint se va con ella. Quien
        # orquesta decide cuándo confirmar; las pruebas no confirman nunca,
        # porque su aislamiento depende de revertir al final.
        self.confirmar = confirmar

    # --- API principal ----------------------------------------------------

    def capturar_fuente(self, source_id: str) -> ResultadoCaptura:
        fuente = self._fuente(source_id)
        if fuente is None:
            raise LookupError(f"La fuente {source_id} no está en el catálogo")

        if fuente["politica_acceso"] != (
            voc.PoliticaAcceso.PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS.value
        ):
            # No es un fallo: es la política declarada para esa fuente.
            raise PermisoDePoliticaDenegado(
                f"{source_id} tiene política {fuente['politica_acceso']}: "
                "no se automatiza hasta identificarla como pública."
            )

        config = self._config_vigente(source_id)
        presupuesto = Presupuesto.desde_config(config["presupuesto"])
        urls = self._urls(source_id)

        corrida_id, hechas = self._corrida_reanudable(source_id, config["id"])
        resultado = ResultadoCaptura(
            corrida_id=corrida_id,
            source_id=source_id,
            solicitadas=len(urls),
            reanudada=bool(hechas),
        )

        if hechas:
            # Los contadores de lo hecho antes del corte no se pueden inventar:
            # se recuentan de las capturas que la corrida ya tiene. Lo que quedó
            # anotado como hecho y no dejó captura fue un rechazo, y así
            # reconcilia: reanudadas = descargadas previas + rechazadas previas.
            self._recontar_lo_ya_hecho(resultado, hechas)

        for url in urls:
            if str(url["id"]) in hechas:
                # Ya se pidió y se guardó en una corrida que se cortó. Volver a
                # pedirla no agregaría nada y le costaría una solicitud más a la
                # fuente, que es justo lo que el presupuesto trata de cuidar.
                continue
            previa = self._captura_previa(url["id"])
            descarga = self.cliente.descargar(
                url["url"],
                etag=previa["etag"] if previa else None,
                last_modified=previa["last_modified"] if previa else None,
                presupuesto=presupuesto,
            )
            self._procesar(resultado, url, descarga, previa)
            hechas.add(str(url["id"]))
            self._guardar_checkpoint(corrida_id, hechas)
            if self.confirmar is not None:
                self.confirmar()

        self._cerrar_corrida(resultado)
        if self.confirmar is not None:
            self.confirmar()
        return resultado

    # --- Procesamiento de una descarga ------------------------------------

    def _procesar(
        self,
        resultado: ResultadoCaptura,
        url: dict,
        descarga: Descarga,
        previa: dict | None,
    ) -> None:
        if descarga.error_tls:
            resultado.rechazadas += 1
            self._degradar_fuente(
                resultado,
                voc.AccessStatus.ERROR_TLS,
                voc.TipoIncidencia.ACCESO_BLOQUEADO,
                f"{url['url']}: {descarga.error}. No se relaja la validación de TLS; "
                "hay que buscar una fuente oficial equivalente o hacer carga manual trazada.",
                severidad=voc.Severidad.HIGH,
            )
            return

        if descarga.acceso_limitado:
            resultado.rechazadas += 1
            self._degradar_fuente(
                resultado,
                voc.AccessStatus.ACCESO_LIMITADO,
                voc.TipoIncidencia.ACCESO_BLOQUEADO,
                f"{url['url']}: {descarga.error}. La fuente queda pausada; "
                "no se rotan identidades ni se evaden controles de acceso.",
                severidad=voc.Severidad.HIGH,
            )
            return

        if descarga.no_modificado:
            if previa is None:
                # Un 304 sin captura previa no acredita nada: no hay cuerpo que
                # reutilizar y el esquema lo rechazaría.
                resultado.rechazadas += 1
                self._abrir_incidencia(
                    resultado,
                    voc.TipoIncidencia.CAMBIO_DE_ESQUEMA,
                    f"{url['url']} respondió 304 sin captura previa válida.",
                    severidad=voc.Severidad.MEDIUM,
                )
                return
            captura_id = self._insertar_captura(
                resultado.corrida_id,
                url["id"],
                descarga,
                sha256=previa["sha256_raw"],
                objeto_uri=previa["objeto_uri"],
                bytes_=previa["bytes"],
                # Un 304 no trae `Content-Type` porque no trae cuerpo. El tipo
                # se hereda de la captura cuyos bytes se reutilizan: si no, una
                # revalidación borraría el tipo que la primera captura sí supo.
                mime=previa["mime"],
                captura_previa_id=previa["id"],
            )
            resultado.descargadas += 1
            resultado.procesadas += 1
            resultado.no_modificadas += 1
            resultado.capturas.append(captura_id)
            return

        if not descarga.exitosa:
            resultado.rechazadas += 1
            # Un 404 suele traer una página entera. Se guarda como lo que es
            # —la respuesta que dio esa URL, con su status— para poder mostrar
            # qué contestó y notar cuándo deja de contestar eso. No se extrae:
            # la consulta de extracción sólo toma capturas 2xx.
            if descarga.contenido:
                objeto = self.almacen.guardar(descarga.contenido)
                resultado.capturas.append(
                    self._insertar_captura(
                        resultado.corrida_id,
                        url["id"],
                        descarga,
                        sha256=objeto.sha256,
                        objeto_uri=objeto.uri,
                        bytes_=objeto.bytes,
                        captura_previa_id=None,
                    )
                )
            # Un recurso que no está y uno que nadie miró no son lo mismo. Sin
            # degradar la fuente, el reporte de cobertura diría que está sin
            # empezar, que es exactamente convertir un error en «sin datos».
            self._degradar_fuente(
                resultado,
                voc.AccessStatus.NO_ENCONTRADA
                if descarga.http_status in (404, 410)
                else voc.AccessStatus.NO_VERIFICADO,
                voc.TipoIncidencia.ACCESO_BLOQUEADO,
                f"{url['url']}: {descarga.error}. "
                + (
                    "El recurso ya no está en esa dirección; hay que recuperar la identidad "
                    "de la fuente o registrarla como retirada."
                    if descarga.http_status in (404, 410)
                    else "La fuente queda pausada hasta entender el fallo."
                ),
                severidad=voc.Severidad.MEDIUM,
            )
            return

        objeto = self.almacen.guardar(descarga.contenido)
        captura_id = self._insertar_captura(
            resultado.corrida_id,
            url["id"],
            descarga,
            sha256=objeto.sha256,
            objeto_uri=objeto.uri,
            bytes_=objeto.bytes,
            captura_previa_id=previa["id"] if previa else None,
        )
        resultado.descargadas += 1
        resultado.procesadas += 1
        resultado.capturas.append(captura_id)

    # --- Acceso a la base --------------------------------------------------

    def _fuente(self, source_id: str) -> dict | None:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT source_id, estado, access_status, politica_acceso "
                    "FROM fuentes WHERE source_id = :sid"
                ),
                {"sid": source_id},
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    def _config_vigente(self, source_id: str) -> dict:
        fila = (
            self.conexion.execute(
                text(
                    "SELECT id, adaptador, presupuesto, ttl_defecto, frecuencia "
                    "FROM fuente_config_versiones WHERE source_id = :sid "
                    "ORDER BY version DESC LIMIT 1"
                ),
                {"sid": source_id},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise LookupError(f"{source_id} no tiene configuración de extracción")
        return dict(fila)

    def _urls(self, source_id: str) -> list[dict]:
        return [
            dict(fila)
            for fila in self.conexion.execute(
                text(
                    "SELECT id, url, rol FROM fuente_urls WHERE source_id = :sid "
                    "ORDER BY es_canonica DESC, descubierta_en"
                ),
                {"sid": source_id},
            ).mappings()
        ]

    def _captura_previa(self, source_url_id: uuid.UUID) -> dict | None:
        """Última captura con cuerpo propio de esa URL.

        Una revalidación (304) no tiene cuerpo: si se tomara como previa, la
        cadena de reutilización perdería el objeto original.
        """
        fila = (
            self.conexion.execute(
                text(
                    "SELECT id, sha256_raw, objeto_uri, bytes, mime, etag, last_modified "
                    "FROM capturas "
                    "WHERE source_url_id = :u AND coalesce(http_status, 0) <> 304 "
                    "ORDER BY capturado_en DESC LIMIT 1"
                ),
                {"u": source_url_id},
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    def _corrida_reanudable(
        self, source_id: str, config_id: uuid.UUID
    ) -> tuple[uuid.UUID, set[str]]:
        """La corrida que quedó abierta con checkpoint, o una nueva.

        Una corrida EN_CURSO con checkpoint es una que se cortó: nadie la
        cerró. Continuarla en vez de abrir otra es lo que hace que reanudar no
        vuelva a pedir lo que ya se pidió, y que la reconciliación de la fuente
        siga siendo una sola fila y no dos mitades.
        """
        fila = (
            self.conexion.execute(
                text(
                    "SELECT id, checkpoint FROM corridas_ingesta "
                    " WHERE source_id = :sid AND estado = 'EN_CURSO' "
                    "   AND checkpoint IS NOT NULL "
                    " ORDER BY inicio DESC LIMIT 1"
                ),
                {"sid": source_id},
            )
            .mappings()
            .first()
        )
        if fila is not None:
            hechas = set((fila["checkpoint"] or {}).get("urls_hechas", []))
            return fila["id"], hechas

        corrida_id = self.conexion.execute(
            text(
                "INSERT INTO corridas_ingesta "
                "(source_id, config_version_id, estado, extractor_version) "
                "VALUES (:sid, :cfg, 'EN_CURSO', :ver) RETURNING id"
            ),
            {"sid": source_id, "cfg": config_id, "ver": VERSION_EXTRACTOR},
        ).scalar_one()
        return corrida_id, set()

    def _recontar_lo_ya_hecho(self, resultado: ResultadoCaptura, hechas: set[str]) -> None:
        fila = self.conexion.execute(
            text(
                "SELECT count(*) AS capturas, "
                "       count(*) FILTER (WHERE http_status = 304) AS no_modificadas "
                "  FROM capturas WHERE corrida_id = :id"
            ),
            {"id": resultado.corrida_id},
        ).one()
        resultado.reanudadas = len(hechas)
        resultado.descargadas = fila.capturas
        resultado.procesadas = fila.capturas
        resultado.no_modificadas = fila.no_modificadas
        resultado.rechazadas = max(0, len(hechas) - fila.capturas)

    def _guardar_checkpoint(self, corrida_id: uuid.UUID, hechas: set[str]) -> None:
        import json

        self.conexion.execute(
            text("UPDATE corridas_ingesta SET checkpoint = CAST(:c AS jsonb) WHERE id = :id"),
            {
                "c": json.dumps(
                    {
                        "urls_hechas": sorted(hechas),
                        "actualizado_en": datetime.now(UTC).isoformat(),
                    }
                ),
                "id": corrida_id,
            },
        )

    def _insertar_captura(
        self,
        corrida_id: uuid.UUID,
        source_url_id: uuid.UUID,
        descarga: Descarga,
        *,
        sha256: str,
        objeto_uri: str,
        bytes_: int | None,
        captura_previa_id: uuid.UUID | None,
        mime: str | None = None,
    ) -> uuid.UUID:
        import json

        return self.conexion.execute(
            text(
                "INSERT INTO capturas ("
                "  corrida_id, source_url_id, captura_previa_id, url_final, http_status, "
                "  capturado_en, mime, bytes, sha256_raw, objeto_uri, etag, last_modified, "
                "  cabeceras, redirecciones"
                ") VALUES ("
                "  :corrida, :url, :previa, :url_final, :status, :capturado, :mime, :bytes, "
                "  :sha, :objeto, :etag, :last_modified, :cabeceras, :redirecciones"
                ") RETURNING id"
            ),
            {
                "corrida": corrida_id,
                "url": source_url_id,
                "previa": captura_previa_id,
                "url_final": descarga.url_final,
                "status": descarga.http_status,
                "capturado": descarga.capturado_en,
                "mime": mime or descarga.mime,
                "bytes": bytes_,
                "sha": sha256,
                "objeto": objeto_uri,
                "etag": descarga.etag,
                "last_modified": descarga.last_modified,
                "cabeceras": json.dumps(descarga.cabeceras, ensure_ascii=False),
                "redirecciones": json.dumps(descarga.redirecciones, ensure_ascii=False),
            },
        ).scalar_one()

    def _cerrar_corrida(self, resultado: ResultadoCaptura) -> None:
        if resultado.rechazadas == 0 and resultado.solicitadas > 0:
            estado = voc.EstadoCorrida.COMPLETA
        elif resultado.procesadas > 0:
            estado = voc.EstadoCorrida.PARCIAL
        elif resultado.solicitadas == 0:
            # Una fuente sin URL conocida no falló: no había nada que pedir.
            estado = voc.EstadoCorrida.COMPLETA
        else:
            estado = voc.EstadoCorrida.FALLIDA
        resultado.estado = estado

        # Una corrida que cierra en FALLIDA o PARCIAL sin decir por qué obliga a
        # buscar el motivo en otra tabla. El motivo ya está: son las incidencias
        # que la corrida abrió. Copiarlas acá es lo que hace que la fila de la
        # corrida se explique sola cuando alguien la mire dentro de seis meses.
        detalle = None
        if estado is not voc.EstadoCorrida.COMPLETA and resultado.incidencias:
            detalle = " | ".join(resultado.incidencias)

        self.conexion.execute(
            text(
                "UPDATE corridas_ingesta SET estado = :estado, fin = :fin, "
                "  solicitadas = :sol, descargadas = :desc, procesadas = :proc, "
                "  rechazadas = :rech, detalle_error = :detalle, checkpoint = NULL "
                "WHERE id = :id"
            ),
            {
                "estado": estado.value,
                "fin": datetime.now(UTC),
                "sol": resultado.solicitadas,
                "desc": resultado.descargadas,
                "proc": resultado.procesadas,
                "rech": resultado.rechazadas,
                "detalle": detalle,
                "id": resultado.corrida_id,
            },
        )
        if estado is voc.EstadoCorrida.COMPLETA and resultado.descargadas:
            self.conexion.execute(
                text(
                    "UPDATE fuentes SET estado = 'ACTIVE', access_status = 'ACCESIBLE' "
                    "WHERE source_id = :sid AND estado IN ('DISCOVERY', 'ACTIVE', 'DEGRADED')"
                ),
                {"sid": resultado.source_id},
            )

    def _degradar_fuente(
        self,
        resultado: ResultadoCaptura,
        access_status: voc.AccessStatus,
        tipo: voc.TipoIncidencia,
        descripcion: str,
        *,
        severidad: voc.Severidad,
    ) -> None:
        self.conexion.execute(
            text(
                "UPDATE fuentes SET estado = 'DEGRADED', access_status = :acceso, "
                "  motivo_estado = :motivo WHERE source_id = :sid"
            ),
            {
                "acceso": access_status.value,
                "motivo": descripcion,
                "sid": resultado.source_id,
            },
        )
        self._abrir_incidencia(resultado, tipo, descripcion, severidad=severidad)

    def _abrir_incidencia(
        self,
        resultado: ResultadoCaptura,
        tipo: voc.TipoIncidencia,
        descripcion: str,
        *,
        severidad: voc.Severidad,
    ) -> None:
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(source_id, tipo, severidad, estado, descripcion, responsable_rol) "
                "VALUES (:sid, :tipo, :sev, 'ABIERTA', :desc, 'ingesta')"
            ),
            {
                "sid": resultado.source_id,
                "tipo": tipo.value,
                "sev": severidad.value,
                "desc": descripcion,
            },
        )
        resultado.incidencias.append(descripcion)


class PermisoDePoliticaDenegado(Exception):
    """La política de la fuente no habilita automatizar su captura."""
