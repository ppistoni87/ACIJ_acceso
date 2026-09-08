"""HU-038: carga manual trazada, para las fuentes que no se pueden recorrer.

Dieciocho fuentes del corpus están bloqueadas: unas devuelven 403, otra tiene un
certificado que no valida, la mayoría no tiene una URL inequívoca. Ninguna de
esas se resuelve rotando identidades ni desactivando TLS, así que el contenido
—cuando existe y alguien lo consigue por una vía legítima— tiene que poder
entrar de otra manera.

Esa vía es esta, y su única razón de ser es que el dato manual **no valga menos
que el automático porque nadie sepa de dónde salió**. Una carga manual entra por
la misma cadena que una captura de red: corrida, captura inmutable direccionada
por contenido, y de ahí documentos y evidencia. Lo que cambia es lo que se
declara sobre su origen, y se exige declararlo:

* **quién** la cargó, con nombre y rol;
* **de dónde** la obtuvo, en texto libre pero obligatorio;
* **cuándo** la obtuvo, que no es cuándo la cargó.

Sin eso no se carga. Un archivo sin procedencia es indistinguible de uno
inventado, y el sistema entero se apoya en poder decir de dónde salió cada cosa.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    AccessStatus,
    Adaptador,
    EstadoCorrida,
    EstadoFuente,
    RolUrl,
    TipoAcceso,
)
from backend_normativo.ingesta.almacen import AlmacenObjetos

# Un origen así de corto no dice nada: «pdf», «mail», «archivo».
MINIMO_PROCEDENCIA = 15


class ProcedenciaInsuficiente(Exception):
    """Falta declarar de dónde salió el archivo, o quién lo cargó."""


@dataclass
class ResultadoCargaManual:
    captura_id: uuid.UUID
    corrida_id: uuid.UUID
    sha256: str
    bytes: int
    ya_existia: bool
    source_id: str


class CargaManual:
    def __init__(self, conexion: Connection, almacen: AlmacenObjetos | None = None) -> None:
        self.conexion = conexion
        self.almacen = almacen or AlmacenObjetos()

    def cargar(
        self,
        source_id: str,
        archivo: pathlib.Path,
        *,
        actor: str,
        procedencia: str,
        obtenido_en: dt.date,
        mime: str | None = None,
        url_declarada: str | None = None,
    ) -> ResultadoCargaManual:
        self._exigir_procedencia(actor, procedencia)
        if not archivo.is_file():
            raise ProcedenciaInsuficiente(f"No existe el archivo {archivo}.")
        if self._fuente(source_id) is None:
            raise LookupError(f"{source_id} no está en el catálogo.")

        datos = archivo.read_bytes()
        objeto = self.almacen.guardar(datos)

        url_id = self._url(source_id, url_declarada, archivo)
        corrida_id = self._corrida(source_id, actor, procedencia, obtenido_en, archivo)
        captura_id = self.conexion.execute(
            text(
                "INSERT INTO capturas (corrida_id, source_url_id, url_final, mime, bytes, "
                " sha256_raw, objeto_uri, capturado_en, cabeceras) "
                "VALUES (:co, :u, :url, :mime, :b, :sha, :uri, :cuando, CAST(:cab AS jsonb)) "
                "RETURNING id"
            ),
            {
                "co": corrida_id,
                "u": url_id,
                # No hay `http_status`: no hubo respuesta HTTP. Poner 200 diría
                # que el servidor contestó, y no contestó nadie.
                "url": url_declarada,
                "mime": mime,
                "b": len(datos),
                "sha": objeto.sha256,
                "uri": objeto.uri,
                "cuando": dt.datetime.combine(obtenido_en, dt.time(), tzinfo=dt.UTC),
                "cab": json.dumps(
                    {
                        "carga": "MANUAL",
                        "actor": actor,
                        "procedencia": procedencia,
                        "obtenido_en": obtenido_en.isoformat(),
                        "archivo_original": archivo.name,
                    },
                    ensure_ascii=False,
                ),
            },
        ).scalar_one()

        self._marcar_fuente(source_id, actor, procedencia)
        self._auditar(captura_id, source_id, actor, procedencia, archivo)
        return ResultadoCargaManual(
            captura_id=captura_id,
            corrida_id=corrida_id,
            sha256=objeto.sha256,
            bytes=len(datos),
            ya_existia=objeto.ya_existia,
            source_id=source_id,
        )

    # --- Internos -----------------------------------------------------------

    @staticmethod
    def _exigir_procedencia(actor: str, procedencia: str) -> None:
        if not actor.strip():
            raise ProcedenciaInsuficiente(
                "Hay que decir quién carga el archivo. Una carga manual sin responsable no se "
                "puede repreguntar ni auditar."
            )
        if len(procedencia.strip()) < MINIMO_PROCEDENCIA:
            raise ProcedenciaInsuficiente(
                "Hay que declarar de dónde salió el archivo, con detalle suficiente para "
                "volver a buscarlo. Un archivo sin procedencia es indistinguible de uno "
                "inventado."
            )

    def _fuente(self, source_id: str) -> str | None:
        return self.conexion.execute(
            text("SELECT source_id FROM fuentes WHERE source_id = :s"), {"s": source_id}
        ).scalar_one_or_none()

    def _url(self, source_id: str, url_declarada: str | None, archivo: pathlib.Path) -> uuid.UUID:
        """La URL de la carga manual.

        Cuando quien carga declara la URL de origen, se usa esa. Cuando no hay
        —el caso de las fuentes sin URL inequívoca—, se registra una propia con
        esquema `manual://` en vez de inventar una http que nadie puede visitar.
        """
        url = url_declarada or f"manual://{source_id}/{archivo.name}"
        return self.conexion.execute(
            text(
                "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
                "VALUES (:s, :u, :rol, :acceso) "
                "ON CONFLICT (source_id, url) DO UPDATE SET rol = EXCLUDED.rol RETURNING id"
            ),
            {
                "s": source_id,
                "u": url,
                "rol": RolUrl.DETALLE.value,
                "acceso": TipoAcceso.CARGA_MANUAL.value,
            },
        ).scalar_one()

    def _corrida(
        self,
        source_id: str,
        actor: str,
        procedencia: str,
        obtenido_en: dt.date,
        archivo: pathlib.Path,
    ) -> uuid.UUID:
        config = self.conexion.execute(
            text(
                "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
                " ORDER BY version DESC LIMIT 1"
            ),
            {"s": source_id},
        ).scalar_one_or_none()
        if config is None:
            config = self.conexion.execute(
                text(
                    "INSERT INTO fuente_config_versiones (source_id, version, adaptador, "
                    " politica_version) VALUES (:s, 1, :a, 'acceso-fuentes-publicas@1') "
                    "RETURNING id"
                ),
                {"s": source_id, "a": Adaptador.CARGA_MANUAL.value},
            ).scalar_one()
        return self.conexion.execute(
            text(
                "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
                " extractor_version, solicitadas, descargadas, procesadas, fin, detalle_error) "
                "VALUES (:s, :c, :estado, 'carga-manual@1', 1, 1, 1, now(), :detalle) "
                "RETURNING id"
            ),
            {
                "s": source_id,
                "c": config,
                "estado": EstadoCorrida.COMPLETA.value,
                "detalle": (
                    f"Carga manual de {archivo.name} por {actor}. "
                    f"Obtenido el {obtenido_en.isoformat()}. Procedencia: {procedencia}"
                ),
            },
        ).scalar_one()

    def _marcar_fuente(self, source_id: str, actor: str, procedencia: str) -> None:
        """La fuente pasa a MANUAL y conserva por qué.

        No vuelve a ACTIVE: que alguien haya conseguido el archivo una vez no
        significa que el sistema pueda recorrerla. Decir lo contrario haría que
        el monitor la dé por cubierta y deje de avisar que sigue bloqueada.
        """
        self.conexion.execute(
            text(
                "UPDATE fuentes SET estado = :estado, motivo_estado = :motivo "
                " WHERE source_id = :s AND estado <> :activa"
            ),
            {
                "s": source_id,
                "estado": EstadoFuente.MANUAL.value,
                "activa": EstadoFuente.ACTIVE.value,
                "motivo": (
                    f"Contenido incorporado por carga manual ({actor}): {procedencia}. "
                    "La fuente sigue sin poder recorrerse automáticamente."
                ),
            },
        )

    def _auditar(
        self,
        captura_id: uuid.UUID,
        source_id: str,
        actor: str,
        procedencia: str,
        archivo: pathlib.Path,
    ) -> None:
        self.conexion.execute(
            text(
                "INSERT INTO auditoria_eventos (actor, accion, objeto, objeto_id, motivo) "
                "VALUES (:actor, 'CARGA_MANUAL', 'capturas', :id, :motivo)"
            ),
            {
                "actor": actor,
                "id": str(captura_id),
                "motivo": (
                    f"{source_id}: se incorporó {archivo.name} por carga manual. "
                    f"Procedencia declarada: {procedencia}"
                ),
            },
        )


def fuentes_bloqueadas(conexion: Connection) -> list[dict]:
    """Las que hoy necesitan esta vía, con su motivo."""
    return [
        dict(fila)
        for fila in conexion.execute(
            text(
                "SELECT source_id, nombre, estado, access_status, motivo_estado, "
                "       responsable_rol FROM fuentes "
                " WHERE access_status = ANY(:bloqueos) AND alias_of IS NULL "
                " ORDER BY source_id"
            ),
            {
                "bloqueos": [
                    AccessStatus.ACCESO_LIMITADO.value,
                    AccessStatus.BLOQUEADA.value,
                    AccessStatus.ERROR_TLS.value,
                    AccessStatus.NO_ENCONTRADA.value,
                    AccessStatus.SIN_URL_CONOCIDA.value,
                ]
            },
        ).mappings()
    ]
