"""HU-009: resolver la identidad de una norma y crear su versión.

La identidad jurídica es jurisdicción + emisor + tipo + número + año, con los
identificadores oficiales alternativos conservados. Dos cosas que este módulo no
hace nunca:

* **Fusionar por parecido.** Si la identidad no está completa, la norma queda en
  staging marcada como incierta y con una incidencia abierta. Dos normas con el
  mismo número y año pero distinta jurisdicción son normas distintas.
* **Deducir vigencia.** La versión nace con `valid_tipo = DESCONOCIDO` aunque se
  conozca la fecha de publicación. Que una norma se haya publicado no dice hasta
  cuándo rige, y un límite temporal desconocido no puede volverse infinito
  aplicable por defecto. Resolver la vigencia es otro paso, con su evidencia.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import (
    EstadoRevision,
    Severidad,
    TipoIncidencia,
    TipoNorma,
    TipoOrganismo,
    ValidTipo,
)

# Espacios de nombres de identificadores oficiales. El id de InfoLEG no se
# mezcla con el de NormativaBA aunque coincida el número.
NAMESPACE_POR_CLAVE = {
    "infoleg_id": "infoleg",
    "normativaba_id": "normativaba",
}


@dataclass
class ResultadoIdentidad:
    normas_creadas: int = 0
    normas_vinculadas: int = 0
    identificadores_creados: int = 0
    versiones_creadas: int = 0
    versiones_existentes: int = 0
    inciertas: int = 0
    incidencias_creadas: int = 0
    avisos: list[str] = field(default_factory=list)


class ResolutorIdentidad:
    def __init__(self, conexion: Connection) -> None:
        self.conexion = conexion

    def resolver_pendientes(self, source_id: str | None = None) -> ResultadoIdentidad:
        """Versiones documentales de tipo norma que todavía no tienen versión
        normativa asociada."""
        filas = (
            self.conexion.execute(
                text(
                    "SELECT dv.id, dv.identidad_candidata, dv.tipo_version, d.source_id, "
                    "       d.external_id "
                    "  FROM documento_versiones dv "
                    "  JOIN documentos d ON d.id = dv.documento_id "
                    " WHERE d.tipo = 'NORMA' "
                    "   AND (CAST(:sid AS text) IS NULL OR d.source_id = :sid) "
                    "   AND NOT EXISTS (SELECT 1 FROM norma_versiones nv "
                    "                   WHERE nv.doc_version_id = dv.id) "
                    " ORDER BY dv.creado_en"
                ),
                {"sid": source_id},
            )
            .mappings()
            .all()
        )

        resultado = ResultadoIdentidad()
        for fila in filas:
            self._resolver_version(dict(fila), resultado)
        return resultado

    # --- Una versión --------------------------------------------------------

    def _resolver_version(self, fila: dict, resultado: ResultadoIdentidad) -> None:
        candidata = fila["identidad_candidata"] or {}
        identificadores = self._identificadores(candidata)

        norma_id = self._por_identificador(identificadores)
        if norma_id is None:
            norma_id = self._por_clave_canonica(candidata) or self._por_numero_sin_anio(
                candidata, fila, resultado
            )
            if norma_id is not None:
                resultado.normas_vinculadas += 1
        else:
            resultado.normas_vinculadas += 1

        if norma_id is None:
            norma_id = self._crear_norma(candidata, fila, resultado)
        else:
            self._completar_identidad(norma_id, candidata, fila, resultado)
        if norma_id is None:
            return

        resultado.identificadores_creados += self._registrar_identificadores(
            norma_id, identificadores
        )
        self._crear_version(norma_id, fila, candidata, resultado)

    def _identificadores(self, candidata: dict) -> list[tuple[str, str]]:
        return [
            (namespace, str(candidata[clave]))
            for clave, namespace in NAMESPACE_POR_CLAVE.items()
            if candidata.get(clave)
        ]

    def _por_identificador(self, identificadores: list[tuple[str, str]]) -> uuid.UUID | None:
        for namespace, valor in identificadores:
            encontrada = self.conexion.execute(
                text(
                    "SELECT norma_id FROM norma_identificadores "
                    "WHERE namespace = :ns AND valor = :v"
                ),
                {"ns": namespace, "v": valor},
            ).scalar_one_or_none()
            if encontrada is not None:
                return encontrada
        return None

    def _por_clave_canonica(self, candidata: dict) -> uuid.UUID | None:
        """Solo busca cuando la clave está completa.

        Con la clave incompleta no se busca ni se aproxima: fusionar por parecido
        es exactamente lo que produce dos normas distintas colapsadas en una.
        """
        jurisdiccion = candidata.get("jurisdiccion")
        tipo = candidata.get("tipo")
        numero = candidata.get("numero")
        anio = candidata.get("anio")
        if not (jurisdiccion and tipo and numero and anio):
            return None
        return self.conexion.execute(
            text(
                "SELECT id FROM normas WHERE jurisdiccion_id = :j AND tipo = :t "
                "  AND numero = :n AND anio = :a AND identidad_incierta = false"
            ),
            {"j": jurisdiccion, "t": tipo, "n": str(numero), "a": int(anio)},
        ).scalar_one_or_none()

    def _por_numero_sin_anio(
        self, candidata: dict, fila: dict, resultado: ResultadoIdentidad
    ) -> uuid.UUID | None:
        """Sin año, solo si la jurisdicción tiene una sola norma con ese número.

        Un texto consolidado del Digesto porteño se presenta como «ORDENANZA F –
        N° 43.478», sin fecha: no la lleva porque el consolidado no es el acto
        original. Descartarlo por eso dejaría afuera justamente la versión más
        actual de la norma.

        Con más de una candidata no se elige: dos normas del mismo tipo y número
        en una jurisdicción son años distintos, y quedarse con una sería inventar
        cuál. Eso va a la cola de revisión.
        """
        jurisdiccion = candidata.get("jurisdiccion")
        tipo = candidata.get("tipo")
        numero = candidata.get("numero")
        if not (jurisdiccion and tipo and numero) or candidata.get("anio"):
            return None
        filas = self.conexion.execute(
            text(
                "SELECT id, anio FROM normas "
                " WHERE jurisdiccion_id = :j AND tipo = :t AND numero = :n "
                "   AND identidad_incierta = false "
                " ORDER BY anio"
            ),
            {"j": jurisdiccion, "t": tipo, "n": str(numero)},
        ).all()
        if len(filas) == 1:
            return filas[0].id
        if len(filas) > 1:
            anios = ", ".join(str(f.anio) for f in filas)
            self._abrir_incidencia(
                fila["source_id"],
                TipoIncidencia.IDENTIDAD_AMBIGUA,
                Severidad.MEDIUM,
                f"El documento se presenta como {tipo} N° {numero} de {jurisdiccion} sin "
                f"año, y en el corpus hay {len(filas)} normas con ese número ({anios}). "
                "No se elige ninguna.",
                resultado,
            )
        return None

    def _crear_norma(
        self, candidata: dict, fila: dict, resultado: ResultadoIdentidad
    ) -> uuid.UUID | None:
        jurisdiccion = candidata.get("jurisdiccion")
        if not jurisdiccion:
            # Sin jurisdicción no hay identidad posible: dos leyes con el mismo
            # número y año pertenecen a jurisdicciones distintas.
            self._abrir_incidencia(
                fila["source_id"],
                TipoIncidencia.IDENTIDAD_AMBIGUA,
                Severidad.HIGH,
                f"La versión documental {fila['id']} no declara jurisdicción. "
                "No se crea la norma: sin jurisdicción la identidad no existe.",
                resultado,
            )
            resultado.avisos.append(f"{fila['external_id']}: sin jurisdicción")
            return None

        completa = bool(candidata.get("tipo") and candidata.get("numero") and candidata.get("anio"))
        emisor_id = self._organismo(jurisdiccion, candidata.get("emisor_declarado"))

        norma_id = self.conexion.execute(
            text(
                "INSERT INTO normas "
                "(jurisdiccion_id, emisor_id, tipo, numero, anio, titulo, identidad_incierta) "
                "VALUES (:j, :e, :t, :n, :a, :titulo, :incierta) RETURNING id"
            ),
            {
                "j": jurisdiccion,
                "e": emisor_id,
                "t": candidata.get("tipo") or TipoNorma.OTRO.value,
                "n": str(candidata["numero"]) if candidata.get("numero") else None,
                "a": int(candidata["anio"]) if candidata.get("anio") else None,
                "titulo": candidata.get("titulo")
                or candidata.get("encabezado")
                or f"Norma sin título identificado ({fila['external_id']})",
                "incierta": not completa,
            },
        ).scalar_one()
        resultado.normas_creadas += 1

        if not completa:
            resultado.inciertas += 1
            faltantes = [c for c in ("tipo", "numero", "anio") if not candidata.get(c)]
            self._abrir_incidencia(
                fila["source_id"],
                TipoIncidencia.IDENTIDAD_AMBIGUA,
                Severidad.HIGH,
                f"La norma {norma_id} quedó en identidad incierta: falta "
                f"{', '.join(faltantes)}. No se fusiona con ninguna otra hasta resolverlo.",
                resultado,
            )
        return norma_id

    def _completar_identidad(
        self,
        norma_id: uuid.UUID,
        candidata: dict,
        fila: dict,
        resultado: ResultadoIdentidad,
    ) -> None:
        """Completa una identidad incierta con lo que aporta otra vista.

        Una vista de texto no trae tipo, número ni año: eso está en la ficha. Si
        la norma se creó desde el texto y después llega la ficha con la
        identidad completa, se completa la que ya existe. Corregir un título o
        una URL no crea otra norma.

        Nunca se pisa una identidad ya completa: si la nueva vista dice algo
        distinto, es un conflicto para revisión, no una corrección automática.
        """
        actual = (
            self.conexion.execute(
                text(
                    "SELECT tipo, numero, anio, titulo, emisor_id, identidad_incierta, "
                    "       jurisdiccion_id FROM normas WHERE id = :id"
                ),
                {"id": norma_id},
            )
            .mappings()
            .one()
        )

        completa_nueva = bool(
            candidata.get("tipo") and candidata.get("numero") and candidata.get("anio")
        )
        if not completa_nueva:
            return

        if not actual["identidad_incierta"]:
            difiere = (
                actual["tipo"] != candidata.get("tipo")
                or actual["numero"] != str(candidata.get("numero"))
                or actual["anio"] != int(candidata["anio"])
            )
            if difiere:
                self._abrir_incidencia(
                    fila["source_id"],
                    TipoIncidencia.IDENTIDAD_AMBIGUA,
                    Severidad.HIGH,
                    f"La norma {norma_id} ya está identificada como "
                    f"{actual['tipo']} {actual['numero']}/{actual['anio']} y otra vista "
                    f"declara {candidata.get('tipo')} {candidata.get('numero')}/"
                    f"{candidata.get('anio')}. No se sobrescribe: hay que resolver cuál "
                    "corresponde.",
                    resultado,
                    candidatos={
                        "registrada": {
                            "tipo": actual["tipo"],
                            "numero": actual["numero"],
                            "anio": actual["anio"],
                        },
                        "nueva": {
                            "tipo": candidata.get("tipo"),
                            "numero": candidata.get("numero"),
                            "anio": candidata.get("anio"),
                        },
                        "origen": fila["external_id"],
                    },
                )
            return

        self.conexion.execute(
            text(
                "UPDATE normas SET tipo = :t, numero = :n, anio = :a, titulo = :titulo, "
                "  emisor_id = coalesce(:e, emisor_id), identidad_incierta = false "
                "WHERE id = :id"
            ),
            {
                "t": candidata["tipo"],
                "n": str(candidata["numero"]),
                "a": int(candidata["anio"]),
                "titulo": candidata.get("titulo")
                or candidata.get("encabezado")
                or actual["titulo"],
                "e": self._organismo(actual["jurisdiccion_id"], candidata.get("emisor_declarado")),
                "id": norma_id,
            },
        )
        resultado.inciertas = max(0, resultado.inciertas - 1)
        # La incidencia que abrió la identidad incierta ya no aplica.
        self.conexion.execute(
            text(
                "UPDATE incidencias_revision "
                "   SET estado = 'RESUELTA', decision = :decision, decidido_por = :actor, "
                "       resuelta_en = now() "
                " WHERE tipo = 'IDENTIDAD_AMBIGUA' AND estado = 'ABIERTA' "
                "   AND descripcion LIKE :patron"
            ),
            {
                "decision": (
                    f"La ficha de la fuente {fila['source_id']} aportó tipo, número y año: "
                    f"{candidata['tipo']} {candidata['numero']}/{candidata['anio']}."
                ),
                "actor": "curacion:identidad-automatica",
                "patron": f"%{norma_id}%",
            },
        )

    def _organismo(self, jurisdiccion: str, nombre: str | None) -> uuid.UUID | None:
        """Organismo emisor tal como lo declara la fuente.

        El nombre declarado se conserva sin normalizar contra un catálogo: dos
        redacciones distintas pueden ser el mismo organismo, y unificarlas es una
        decisión de revisión, no una inferencia de la ingesta.
        """
        if not nombre:
            return None
        existente = self.conexion.execute(
            text(
                "SELECT id FROM organismos WHERE jurisdiccion_id = :j AND nombre = :n "
                "  AND tipo = :t"
            ),
            {"j": jurisdiccion, "n": nombre, "t": TipoOrganismo.EMISOR.value},
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        return self.conexion.execute(
            text(
                "INSERT INTO organismos (jurisdiccion_id, nombre, tipo) "
                "VALUES (:j, :n, :t) RETURNING id"
            ),
            {"j": jurisdiccion, "n": nombre, "t": TipoOrganismo.EMISOR.value},
        ).scalar_one()

    def _registrar_identificadores(
        self, norma_id: uuid.UUID, identificadores: list[tuple[str, str]]
    ) -> int:
        creados = 0
        for namespace, valor in identificadores:
            nuevo = self.conexion.execute(
                text(
                    "INSERT INTO norma_identificadores (norma_id, namespace, valor) "
                    "VALUES (:n, :ns, :v) ON CONFLICT (namespace, valor) DO NOTHING "
                    "RETURNING id"
                ),
                {"n": norma_id, "ns": namespace, "v": valor},
            ).scalar_one_or_none()
            creados += int(nuevo is not None)
        return creados

    def _crear_version(
        self,
        norma_id: uuid.UUID,
        fila: dict,
        candidata: dict,
        resultado: ResultadoIdentidad,
    ) -> None:
        """Crea la versión normativa para esta versión documental.

        La ficha de una norma no es una versión de su texto: describe la norma
        pero no la contiene. Solo se versionan los documentos que traen el
        articulado.
        """
        if fila["tipo_version"] == "NO_DETERMINADO":
            return

        ya_existe = self.conexion.execute(
            text(
                "SELECT nv.registro_version_id FROM norma_versiones nv "
                "WHERE nv.norma_id = :n AND nv.doc_version_id = :dv"
            ),
            {"n": norma_id, "dv": fila["id"]},
        ).scalar_one_or_none()
        if ya_existe is not None:
            resultado.versiones_existentes += 1
            return

        numero_version = self.conexion.execute(
            text(
                "SELECT coalesce(max(numero_version), 0) + 1 FROM registro_versiones "
                "WHERE entidad_tipo = 'norma' AND entidad_id = :n"
            ),
            {"n": norma_id},
        ).scalar_one()

        fechas = candidata.get("fechas") or {}
        publicacion = fechas.get("PUBLICACION") or fechas.get("SANCION")

        registro_id = self.conexion.execute(
            text(
                "INSERT INTO registro_versiones "
                "(entidad_tipo, entidad_id, numero_version, estado_revision, valid_tipo, "
                " valid_desde) "
                "VALUES ('norma', :n, :nv, :estado, :vt, :desde) RETURNING id"
            ),
            {
                "n": norma_id,
                "nv": numero_version,
                "estado": EstadoRevision.CANDIDATE.value,
                # Conocer la publicación no dice hasta cuándo rige: el intervalo
                # queda sin resolver hasta que alguien lo fundamente.
                "vt": ValidTipo.DESCONOCIDO.value,
                "desde": publicacion,
            },
        ).scalar_one()

        self.conexion.execute(
            text(
                "INSERT INTO norma_versiones "
                "(registro_version_id, norma_id, doc_version_id, tipo_version, "
                " estado_legal_declarado) "
                "VALUES (:rv, :n, :dv, :tv, :declarado)"
            ),
            {
                "rv": registro_id,
                "n": norma_id,
                "dv": fila["id"],
                "tv": fila["tipo_version"],
                # Lo que dice la fuente. `estado_legal_validado` sigue en
                # NO_DETERMINADA hasta que haya fundamento.
                "declarado": candidata.get("estado_legal_declarado"),
            },
        )
        resultado.versiones_creadas += 1

    def _abrir_incidencia(
        self,
        source_id: str,
        tipo: TipoIncidencia,
        severidad: Severidad,
        descripcion: str,
        resultado: ResultadoIdentidad,
        candidatos: object | None = None,
    ) -> None:
        self.conexion.execute(
            text(
                "INSERT INTO incidencias_revision "
                "(source_id, tipo, severidad, estado, descripcion, responsable_rol, candidatos) "
                "VALUES (:s, :t, :sev, 'ABIERTA', :d, 'curacion_juridica', :c)"
            ),
            {
                "s": source_id,
                "t": tipo.value,
                "sev": severidad.value,
                "d": descripcion,
                "c": json.dumps(candidatos, ensure_ascii=False) if candidatos else None,
            },
        )
        resultado.incidencias_creadas += 1
