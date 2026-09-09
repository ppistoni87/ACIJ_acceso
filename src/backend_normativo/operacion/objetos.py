"""P-004: comprobar que el original detrás de cada afirmación siga estando.

El almacén guarda los bytes por su hash y la base guarda ese hash. Mientras las
dos mitades coincidan, cualquiera puede volver al documento exacto que sostiene
una regla. Cuando dejan de coincidir —el objeto no está, o está y hashea a otra
cosa— lo que se pierde no es un archivo: es la posibilidad de comprobar lo que
el sistema afirma.

Eso no puede quedar en un renglón de un reporte. Un objeto ausente es
indistinguible de uno correcto hasta que alguien lo lee, y para entonces la
regla ya se sirvió. Por eso la verificación abre una incidencia CRITICAL sobre
cada versión que dependa del objeto roto, y esa incidencia bloquea la
publicación por el camino que ya existe: `bn_motivos_no_servible` devuelve
CONFLICT ante una incidencia abierta de severidad alta.

La diferencia con `respaldo.verificar` es de punto de partida. Aquella compara
lo restaurado contra el manifiesto de un respaldo: sirve para saber si la
restauración salió bien. Esta parte de las capturas que la base tiene hoy, sin
manifiesto de por medio, y sirve para saber si el almacén sigue respaldando lo
que se está sirviendo. Con `--desde` se apunta a otro almacén, que es como se
ensaya el criterio de recuperar el original desde otra instancia.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from backend_normativo.db.vocabularios import Severidad, TipoIncidencia
from backend_normativo.ingesta.almacen import AlmacenObjetos, sha256_de

FALTA = "falta"
DIFIERE = "difiere"

# Las versiones que quedan sin original se bloquean, no se marcan. CRITICAL es
# el umbral que `bn_motivos_no_servible` mira.
SEVERIDAD = Severidad.CRITICAL
TIPO = TipoIncidencia.EVIDENCIA_NO_RECUPERABLE
ROL = "operacion"

# Una captura puede sostener una norma o un trámite; ambas cuelgan de la misma
# versión de documento.
SQL_VERSIONES_AFECTADAS = """
SELECT DISTINCT nv.registro_version_id AS id
  FROM capturas c
  JOIN documento_versiones dv ON dv.captura_id = c.id
  JOIN norma_versiones nv ON nv.doc_version_id = dv.id
 WHERE c.sha256_raw = :sha
UNION
SELECT DISTINCT tv.registro_version_id AS id
  FROM capturas c
  JOIN documento_versiones dv ON dv.captura_id = c.id
  JOIN tramite_versiones tv ON tv.doc_version_id = dv.id
 WHERE c.sha256_raw = :sha
"""


@dataclass
class Hallazgo:
    sha256: str
    objeto_uri: str
    motivo: str
    capturas: int = 0
    versiones: list[str] = field(default_factory=list)
    incidencias_abiertas: int = 0
    incidencias_ya_abiertas: int = 0

    @property
    def explicacion(self) -> str:
        if self.motivo == FALTA:
            return "no está en el almacén: la captura quedó sin bytes detrás"
        return "sus bytes no hashean a lo que la captura declara: el objeto cambió"


@dataclass
class ReporteSincronizacion:
    origen: str = ""
    destino: str = ""
    referenciados: int = 0
    ya_estaban: int = 0
    copiados: int = 0
    bytes_copiados: int = 0
    sin_origen: list[str] = field(default_factory=list)
    no_verificados: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return not self.sin_origen and not self.no_verificados


@dataclass
class ReporteObjetos:
    almacen: str = ""
    referencias: int = 0
    intactos: int = 0
    hallazgos: list[Hallazgo] = field(default_factory=list)
    incidencias_abiertas: int = 0
    versiones_bloqueadas: int = 0
    versiones_sin_dependientes: int = 0

    @property
    def hay_problemas(self) -> bool:
        return bool(self.hallazgos)


def _versiones_afectadas(conexion: Connection, sha: str) -> list[str]:
    filas = conexion.execute(text(SQL_VERSIONES_AFECTADAS), {"sha": sha}).fetchall()
    return [str(fila.id) for fila in filas]


def _ya_hay_incidencia(conexion: Connection, version_id: str | None, sha: str) -> bool:
    """Verificar dos veces no abre dos incidencias por el mismo objeto."""
    if version_id is None:
        consulta = (
            "SELECT 1 FROM incidencias_revision "
            " WHERE tipo = :tipo AND estado IN ('ABIERTA', 'EN_REVISION') "
            "   AND registro_version_id IS NULL AND descripcion LIKE :patron LIMIT 1"
        )
        parametros: dict[str, object] = {"tipo": TIPO.value, "patron": f"%{sha}%"}
    else:
        consulta = (
            "SELECT 1 FROM incidencias_revision "
            " WHERE tipo = :tipo AND estado IN ('ABIERTA', 'EN_REVISION') "
            "   AND registro_version_id = :version AND descripcion LIKE :patron LIMIT 1"
        )
        parametros = {"tipo": TIPO.value, "version": version_id, "patron": f"%{sha}%"}
    return conexion.execute(text(consulta), parametros).first() is not None


def _abrir(conexion: Connection, version_id: str | None, hallazgo: Hallazgo) -> bool:
    if _ya_hay_incidencia(conexion, version_id, hallazgo.sha256):
        return False
    descripcion = (
        f"El objeto {hallazgo.sha256} ({hallazgo.objeto_uri}) {hallazgo.explicacion}. "
        f"Sostiene {hallazgo.capturas} captura(s). Hasta recuperarlo de un respaldo o "
        "recapturar la fuente, lo que dependa de él no puede servirse: no hay con qué "
        "comprobar lo que afirma."
    )
    conexion.execute(
        text(
            "INSERT INTO incidencias_revision "
            "(registro_version_id, tipo, severidad, estado, descripcion, responsable_rol) "
            "VALUES (:version, :tipo, :severidad, 'ABIERTA', :descripcion, :rol)"
        ),
        {
            "version": version_id,
            "tipo": TIPO.value,
            "severidad": SEVERIDAD.value,
            "descripcion": descripcion,
            "rol": ROL,
        },
    )
    return True


def verificar_almacen(
    conexion: Connection,
    almacen: AlmacenObjetos | None = None,
    *,
    abrir_incidencias: bool = True,
) -> ReporteObjetos:
    """Lee del almacén cada objeto que la base referencia y compara el hash."""
    almacen = almacen or AlmacenObjetos()
    reporte = ReporteObjetos(almacen=almacen.base_uri)

    referencias = conexion.execute(
        text(
            "SELECT sha256_raw, min(objeto_uri) AS objeto_uri, count(*) AS capturas "
            "  FROM capturas "
            " WHERE sha256_raw IS NOT NULL "
            " GROUP BY sha256_raw "
            " ORDER BY sha256_raw"
        )
    ).fetchall()
    reporte.referencias = len(referencias)

    for fila in referencias:
        sha = fila.sha256_raw
        try:
            datos = almacen.leer(sha)
        except FileNotFoundError:
            motivo = FALTA
        else:
            if sha256_de(datos) == sha:
                reporte.intactos += 1
                continue
            motivo = DIFIERE

        hallazgo = Hallazgo(
            sha256=sha,
            objeto_uri=fila.objeto_uri or almacen.uri_de(sha),
            motivo=motivo,
            capturas=fila.capturas,
        )
        hallazgo.versiones = _versiones_afectadas(conexion, sha)
        reporte.hallazgos.append(hallazgo)

        if not abrir_incidencias:
            continue
        # Un objeto roto del que todavía no cuelga ninguna versión también deja
        # constancia: si se pierde ahora, se pierde igual cuando se cure.
        objetivos: list[str | None] = list(hallazgo.versiones) or [None]
        if not hallazgo.versiones:
            reporte.versiones_sin_dependientes += 1
        for objetivo in objetivos:
            if _abrir(conexion, objetivo, hallazgo):
                hallazgo.incidencias_abiertas += 1
                reporte.incidencias_abiertas += 1
                if objetivo is not None:
                    reporte.versiones_bloqueadas += 1
            else:
                hallazgo.incidencias_ya_abiertas += 1

    return reporte


def formatear(reporte: ReporteObjetos) -> str:
    lineas = [
        "# Verificación del almacén de objetos",
        "",
        f"Almacén: `{reporte.almacen}`",
        "",
        f"- Objetos referenciados por capturas: {reporte.referencias}",
        f"- Recuperados y con hash coincidente: {reporte.intactos}",
        f"- Con problema: {len(reporte.hallazgos)}",
    ]
    if not reporte.hallazgos:
        lineas += [
            "",
            "Cada captura de la base tiene sus bytes detrás y esos bytes hashean a lo "
            "que la fila declara. Se puede volver al original de cualquier afirmación.",
        ]
        return "\n".join(lineas) + "\n"

    lineas += [
        f"- Incidencias abiertas en esta corrida: {reporte.incidencias_abiertas}",
        f"- Versiones que quedan bloqueadas: {reporte.versiones_bloqueadas}",
        "",
        "## Qué falta",
        "",
    ]
    for hallazgo in reporte.hallazgos:
        lineas.append(f"### `{hallazgo.sha256[:16]}…` — {hallazgo.explicacion}")
        lineas.append("")
        lineas.append(f"- URI: `{hallazgo.objeto_uri}`")
        lineas.append(f"- Capturas que lo referencian: {hallazgo.capturas}")
        if hallazgo.versiones:
            lineas.append(f"- Versiones que dependen de él: {len(hallazgo.versiones)}")
        else:
            lineas.append(
                "- Ninguna versión depende todavía de él: la incidencia queda sin "
                "versión asociada para que no se pierda el hallazgo."
            )
        if hallazgo.incidencias_ya_abiertas:
            lineas.append(
                f"- Ya había {hallazgo.incidencias_ya_abiertas} incidencia(s) abierta(s) "
                "por este objeto: no se duplicaron."
            )
        lineas.append("")

    lineas += [
        "## Qué no dice",
        "",
        "Que un objeto esté y hashee bien no dice que su contenido sea correcto: dice "
        "que es el mismo que se capturó. Si la fuente publicó algo equivocado, esto lo "
        "confirma equivocado e intacto.",
        "",
        "Tampoco reemplaza el respaldo. Recuperar un objeto perdido exige tenerlo en "
        "otro lado; esta verificación avisa que hace falta, no lo trae.",
    ]
    return "\n".join(lineas) + "\n"


def sincronizar(
    conexion: Connection,
    destino: AlmacenObjetos,
    origen: AlmacenObjetos | None = None,
) -> ReporteSincronizacion:
    """Copia al destino los objetos que la base referencia y los verifica allá.

    El contenedor es efímero: `var/objetos` desaparece con él y las capturas
    quedan sin bytes detrás. Esto lleva los originales a un almacén que
    sobreviva —un volumen montado, un bucket montado— y comprueba en el
    destino, leyendo de vuelta, que llegaron enteros. Copiar sin releer es
    confiar en que el `cp` no mintió.

    Solo copia lo que la base referencia. El almacén local acumula objetos de
    corridas que nadie citó; conservarlos fuera es pagar por guardar algo que
    ninguna afirmación necesita.
    """
    origen = origen or AlmacenObjetos()
    reporte = ReporteSincronizacion(origen=origen.base_uri, destino=destino.base_uri)

    shas = [
        fila.sha256_raw
        for fila in conexion.execute(
            text(
                "SELECT DISTINCT sha256_raw FROM capturas "
                " WHERE sha256_raw IS NOT NULL ORDER BY sha256_raw"
            )
        )
    ]
    reporte.referenciados = len(shas)

    for sha in shas:
        if destino.existe(sha):
            reporte.ya_estaban += 1
            continue
        try:
            datos = origen.leer(sha)
        except FileNotFoundError:
            reporte.sin_origen.append(sha)
            continue
        destino.guardar(datos)
        reporte.copiados += 1
        reporte.bytes_copiados += len(datos)

    # La verificación es del destino y se hace releyendo, no confiando en que
    # la copia salió bien.
    for sha in shas:
        try:
            if sha256_de(destino.leer(sha)) != sha:
                reporte.no_verificados.append(sha)
        except FileNotFoundError:
            if sha not in reporte.sin_origen:
                reporte.no_verificados.append(sha)

    return reporte


def formatear_sincronizacion(reporte: ReporteSincronizacion) -> str:
    lineas = [
        "# Originales conservados fuera del contenedor",
        "",
        f"Origen: `{reporte.origen}`",
        f"Destino: `{reporte.destino}`",
        "",
        f"- Objetos que la base referencia: {reporte.referenciados}",
        f"- Ya estaban en el destino: {reporte.ya_estaban}",
        f"- Copiados en esta corrida: {reporte.copiados} "
        f"({reporte.bytes_copiados / 1_048_576:.1f} MiB)",
    ]
    if reporte.sin_origen:
        lineas += [
            "",
            f"**{len(reporte.sin_origen)} objeto(s) no estaban en el origen.** No se pudieron "
            "copiar porque no hay de dónde: esas capturas ya estaban sin bytes antes de "
            "sincronizar. `bn objetos verificar` abre la incidencia que corresponde.",
        ]
    if reporte.no_verificados:
        lineas += [
            "",
            f"**{len(reporte.no_verificados)} objeto(s) no se pudieron releer del destino "
            "con el hash correcto.** La copia no quedó buena; el destino no sirve todavía "
            "como respaldo.",
        ]
    if reporte.completa:
        lineas += [
            "",
            "Cada objeto se releyó desde el destino y hashea a lo que la base declara. "
            "Si el contenedor se pierde, los originales siguen estando.",
            "",
            "## Qué no dice",
            "",
            "Que el destino sea durable. Un directorio montado en la misma máquina se "
            "pierde con la máquina; la retención y las copias del destino son del "
            "proveedor, y hay que declararlas aparte.",
        ]
    return "\n".join(lineas) + "\n"
