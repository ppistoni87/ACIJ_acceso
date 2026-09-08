"""HU-035: ensayo de actualización, sobre texto normativo real.

El paquete pide dos corridas de ingesta que demuestren idempotencia y una
actualización real o controlada que demuestre diff, impacto y evento. Las dos
corridas están en la importación del catálogo nacional; esto es la
actualización.

Qué tiene de real y qué de controlado, para que nadie lo lea de más:

* **Real es el texto.** Las dos versiones son el texto original y el texto
  actualizado del Decreto 1382/2001 tal como los publica InfoLEG, extraídos de
  capturas fechadas de D01. Los artículos que cambian entre una y otra son los
  que cambiaron de verdad.
* **Controlado es el momento.** Presentar esas dos versiones como dos capturas
  sucesivas de una misma URL es un montaje: nadie va a esperar a que InfoLEG
  publique una modificación para probar que el monitor funciona. Lo que se
  ejercita —comparar, propagar, emitir— es el mismo código que corre en
  producción.

Corre sobre una base descartable, nunca sobre la de producción: los datos del
ensayo no se mezclan con el corpus.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.curacion.identidad import ResolutorIdentidad
from backend_normativo.monitoreo.diff import Diferencia, comparar_versiones
from backend_normativo.monitoreo.impacto import Impacto, propagar

RUTA_FIXTURE = pathlib.Path("tests/fixtures/decreto_1382_2001_versiones.json")
SOURCE_ID = "D01"
EXTERNAL_ID = "ensayo:infoleg:69649"
POLITICA = "PUBLIC_READ_ONLY_WITH_VALID_TLS_NO_THIRD_PARTY_KEYS"


@dataclass
class ResultadoEnsayo:
    procedencia: dict = field(default_factory=dict)
    unidades_antes: int = 0
    unidades_despues: int = 0
    diferencia: Diferencia | None = None
    impacto: Impacto | None = None
    evento_id: uuid.UUID | None = None
    idempotency_key: str = ""
    eventos_tras_repetir: int = 0
    versiones_con_frescura_vencida: int = 0

    @property
    def resumen(self) -> dict[str, int]:
        return self.diferencia.resumen if self.diferencia else {}


def correr(conexion: Connection, *, raiz: pathlib.Path | None = None) -> ResultadoEnsayo:
    base = raiz or pathlib.Path.cwd()
    fixture = json.loads((base / RUTA_FIXTURE).read_text())
    resultado = ResultadoEnsayo(procedencia=fixture["procedencia"])

    cargar_catalogo(conexion)
    documento_id, primera = _primera_version(conexion, fixture["original"])
    ResolutorIdentidad(conexion).resolver_pendientes()
    segunda = _segunda_version(conexion, documento_id, fixture["actualizado"])

    resultado.unidades_antes = len(fixture["original"])
    resultado.unidades_despues = len(fixture["actualizado"])
    resultado.diferencia = comparar_versiones(conexion, segunda)
    assert primera is not None

    norma_id = conexion.execute(
        text("SELECT nv.norma_id FROM norma_versiones nv WHERE nv.doc_version_id = :v"),
        {"v": primera},
    ).scalar_one()

    clave = f"ensayo-actualizacion:{segunda}"
    resultado.idempotency_key = clave
    resultado.impacto = propagar(
        conexion,
        norma_id,
        motivo="Ensayo de actualización: texto actualizado del Decreto 1382/2001.",
        idempotency_key=clave,
    )
    resultado.evento_id = conexion.execute(
        text("SELECT id FROM eventos_outbox WHERE idempotency_key = :k"), {"k": clave}
    ).scalar_one()

    # La misma propagación otra vez: un consumidor no debe recibir dos avisos
    # del mismo cambio.
    propagar(conexion, norma_id, motivo="Repetición del mismo cambio.", idempotency_key=clave)
    resultado.eventos_tras_repetir = conexion.execute(
        text("SELECT count(*) FROM eventos_outbox WHERE idempotency_key = :k"), {"k": clave}
    ).scalar_one()

    resultado.versiones_con_frescura_vencida = conexion.execute(
        text(
            "SELECT count(*) FROM registro_versiones rv "
            "  JOIN norma_versiones nv ON nv.registro_version_id = rv.id "
            " WHERE nv.norma_id = :n AND rv.reverificar_antes_de <= now()"
        ),
        {"n": norma_id},
    ).scalar_one()
    return resultado


def _primera_version(conexion: Connection, unidades: list[list]) -> tuple[uuid.UUID, uuid.UUID]:
    url_id = conexion.execute(
        text(
            "INSERT INTO fuente_urls (source_id, url, rol, tipo_acceso) "
            "VALUES (:s, :u, 'DETALLE', 'HTTP_GET_PUBLICO') "
            "ON CONFLICT (source_id, url) DO UPDATE SET rol = 'DETALLE' RETURNING id"
        ),
        {"s": SOURCE_ID, "u": "https://ensayo.local/infoleg/69649"},
    ).scalar_one()
    config = conexion.execute(
        text(
            "SELECT id FROM fuente_config_versiones WHERE source_id = :s "
            " ORDER BY version DESC LIMIT 1"
        ),
        {"s": SOURCE_ID},
    ).scalar_one()
    corrida = conexion.execute(
        text(
            "INSERT INTO corridas_ingesta (source_id, config_version_id, estado, "
            " extractor_version, solicitadas, descargadas, procesadas, fin) "
            "VALUES (:s, :c, 'COMPLETA', 'ensayo', 1, 1, 1, now()) RETURNING id"
        ),
        {"s": SOURCE_ID, "c": config},
    ).scalar_one()
    documento_id = conexion.execute(
        text(
            "INSERT INTO documentos (source_id, tipo, titulo, external_id) "
            "VALUES (:s, 'NORMA', 'Decreto 1382/2001', :e) RETURNING id"
        ),
        {"s": SOURCE_ID, "e": EXTERNAL_ID},
    ).scalar_one()
    version = _agregar_version(
        conexion, documento_id, url_id, corrida, numero=1, tipo="ORIGINAL", unidades=unidades
    )
    norma_id = conexion.execute(
        text(
            "INSERT INTO normas (jurisdiccion_id, tipo, numero, anio, titulo) "
            "VALUES ('AR', 'DECRETO', '1382', 2001, 'Decreto 1382/2001') RETURNING id"
        )
    ).scalar_one()
    registro = conexion.execute(
        text(
            "INSERT INTO registro_versiones (entidad_tipo, entidad_id, numero_version, "
            " estado_revision, valid_tipo, valid_desde, reverificar_antes_de) "
            "VALUES ('norma', :n, 1, 'CANDIDATE', 'ABIERTO_FIN', '2001-11-01', "
            "        now() + interval '30 days') RETURNING id"
        ),
        {"n": norma_id},
    ).scalar_one()
    conexion.execute(
        text(
            "INSERT INTO norma_versiones (registro_version_id, norma_id, doc_version_id, "
            " tipo_version) VALUES (:rv, :n, :dv, 'ORIGINAL')"
        ),
        {"rv": registro, "n": norma_id, "dv": version},
    )
    return documento_id, version


def _segunda_version(
    conexion: Connection, documento_id: uuid.UUID, unidades: list[list]
) -> uuid.UUID:
    fila = (
        conexion.execute(
            text(
                "SELECT dv.captura_id, c.source_url_id, c.corrida_id FROM documento_versiones dv "
                "  JOIN capturas c ON c.id = dv.captura_id WHERE dv.documento_id = :d LIMIT 1"
            ),
            {"d": documento_id},
        )
        .mappings()
        .one()
    )
    return _agregar_version(
        conexion,
        documento_id,
        fila["source_url_id"],
        fila["corrida_id"],
        numero=2,
        tipo="ACTUALIZADO",
        unidades=unidades,
    )


def _agregar_version(
    conexion: Connection,
    documento_id: uuid.UUID,
    url_id: uuid.UUID,
    corrida_id: uuid.UUID,
    *,
    numero: int,
    tipo: str,
    unidades: list[list],
) -> uuid.UUID:
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    captura = conexion.execute(
        text(
            "INSERT INTO capturas (corrida_id, source_url_id, url_final, http_status, mime, "
            " bytes, sha256_raw, objeto_uri) "
            "VALUES (:co, :u, :url, 200, 'text/html', :b, :sha, :uri) RETURNING id"
        ),
        {
            "co": corrida_id,
            "u": url_id,
            "url": "https://ensayo.local/infoleg/69649",
            "b": sum(len(u[3]) for u in unidades),
            "sha": sha,
            "uri": f"objeto://sha256/{sha}",
        },
    ).scalar_one()
    version = conexion.execute(
        text(
            "INSERT INTO documento_versiones (documento_id, captura_id, version, tipo_version, "
            " tipo_fecha, hash_texto, modo_extraccion, extractor_version) "
            "VALUES (:d, :c, :v, :t, 'PUBLICACION', :h, 'HTML', 'ensayo') RETURNING id"
        ),
        {"d": documento_id, "c": captura, "v": numero, "t": tipo, "h": sha},
    ).scalar_one()
    for orden, (tipo_unidad, numero_unidad, ruta, texto_unidad, rol) in enumerate(
        unidades, start=1
    ):
        conexion.execute(
            text(
                "INSERT INTO unidades_documentales "
                "(doc_version_id, tipo, numero, ruta, orden, texto, rol_contenido) "
                "VALUES (:dv, :t, :n, :ruta, :o, :texto, :rol)"
            ),
            {
                "dv": version,
                "t": tipo_unidad,
                "n": numero_unidad,
                "ruta": ruta,
                "o": orden,
                "texto": texto_unidad,
                "rol": rol,
            },
        )
    return version


def formatear(resultado: ResultadoEnsayo) -> str:
    diferencia = resultado.diferencia
    impacto = resultado.impacto
    lineas = [
        "# Ensayo de actualización: diff, impacto y evento",
        "",
        "Generado con `bn calidad ensayo-actualizacion`, sobre una base descartable.",
        "",
        "## Qué es real y qué es controlado",
        "",
        resultado.procedencia.get("nota", ""),
        "",
        f"- Norma: **{resultado.procedencia.get('norma')}**",
        f"- Fuente: {resultado.procedencia.get('fuente')}",
        f"- URL del texto actualizado: `{resultado.procedencia.get('url_actualizado')}`",
        f"- SHA-256 de la captura: `{resultado.procedencia.get('sha256_captura_actualizado')}`",
        "",
        "## 1. Diferencia por unidad",
        "",
        f"El texto original tiene **{resultado.unidades_antes}** unidades y el actualizado "
        f"**{resultado.unidades_despues}**.",
        "",
    ]
    if not diferencia or not diferencia.hay_cambios:
        lineas.append("_No se detectaron cambios._")
    else:
        lineas += [
            "| Clase | Unidades |",
            "| --- | --- |",
        ]
        for clase, cuantas in sorted(resultado.resumen.items()):
            lineas.append(f"| {clase} | {cuantas} |")
        desplazadas = resultado.resumen.get("DESPLAZADA", 0)
        lineas += [
            "",
            f"De esas, **{desplazadas}** son la misma unidad en otra ruta: al insertarse "
            "párrafos, el ordinal de las unidades sin número corre y todas las posteriores "
            "cambian de ruta sin que cambie una palabra. No cuentan como cambio de la norma.",
            "",
            f"Cambios sustantivos: **{len(diferencia.sustantivos)}**.",
            "",
            "| Unidad | Clase | Similitud |",
            "| --- | --- | --- |",
        ]
        ordenados = sorted(diferencia.sustantivos, key=lambda c: c.similitud)
        for cambio in ordenados[:10]:
            lineas.append(f"| `{cambio.ruta}` | {cambio.clase} | {cambio.similitud} |")
        lineas += [
            "",
            "La comparación es por unidad y solo sobre texto dispositivo: una nota editorial",
            "o un token de formulario que cambie no produce un cambio de la norma.",
        ]

    lineas += ["", "## 2. Impacto", ""]
    if impacto:
        lineas += [
            f"- Normas dependientes alcanzadas: **{len(impacto.normas_dependientes)}**"
            + (
                f" ({', '.join(impacto.normas_dependientes)})"
                if impacto.normas_dependientes
                else ""
            ),
            f"- Beneficios afectados: **{len(impacto.beneficios_afectados)}**",
            f"- Reglas afectadas: **{impacto.reglas_afectadas}**",
            f"- Versiones cuya frescura venció por el cambio: "
            f"**{resultado.versiones_con_frescura_vencida}**",
            "",
            "Vencer la frescura no deroga nada: impide seguir sirviendo un dato como actual",
            "hasta que alguien lo verifique.",
        ]

    lineas += [
        "",
        "## 3. Evento",
        "",
        f"- Evento en el outbox: `{resultado.evento_id}`",
        f"- Clave de idempotencia: `{resultado.idempotency_key}`",
        f"- Eventos tras repetir la misma propagación: **{resultado.eventos_tras_repetir}**",
        "",
        "Propagar el mismo cambio dos veces deja un solo evento. El evento queda en el",
        "outbox y la API lo expone; sin proveedor de entrega configurado no se afirma que",
        "se haya notificado a nadie.",
    ]
    return "\n".join(lineas)
