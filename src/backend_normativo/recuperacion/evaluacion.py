"""Medir la recuperación contra un conjunto congelado, léxica contra híbrida.

P-012 criterio 3. Dos cosas se miden acá y son distintas.

**Recall@k**: de las preguntas que el corte puede responder, en cuántas el
fragmento que las responde aparece entre los primeros k. Se informa por
separado para la búsqueda léxica sola y para la híbrida, porque el criterio pide
la comparación y porque sin ella no se sabe si el índice semántico aportó algo o
si el resultado ya lo daba el texto.

**Que no se recupere lo que no está en el corte**: se busca a propósito texto
que existe en el corpus pero que no está publicado, y no tiene que aparecer.

Sobre «congelado». El conjunto lleva el hash de sus preguntas y esta evaluación
falla si no coincide. No es burocracia: quien mide y escribe las preguntas es la
misma persona, y sin una traba la tentación es corregir la pregunta que no salió
bien. Con el hash, cambiar una pregunta obliga a volver a congelar, y eso deja
un cambio visible en el repositorio en vez de una mejora silenciosa del número.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import uuid

from sqlalchemy import Connection, text

from backend_normativo.recuperacion.busqueda import buscar
from backend_normativo.recuperacion.embeddings import Embebedor, EmbebedorFastEmbed

CORTES = (1, 3, 5)
UMBRAL_RECALL_5 = 0.90


class ConjuntoAlterado(RuntimeError):
    """El conjunto cambió y su hash no."""


@dataclasses.dataclass
class Caso:
    id: str
    consulta: str
    responde: str
    por_que: str = ""
    puesto_lexico: int | None = None
    puesto_hibrido: int | None = None
    fuera_del_corte: bool = False


@dataclasses.dataclass
class Reporte:
    modelo: str = ""
    release_id: uuid.UUID | None = None
    fragmentos_indexados: int = 0
    casos: list[Caso] = dataclasses.field(default_factory=list)
    fugas: list[str] = dataclasses.field(default_factory=list)
    avisos: list[str] = dataclasses.field(default_factory=list)

    def _recall(self, atributo: str, corte: int) -> float:
        respondibles = [c for c in self.casos if not c.fuera_del_corte]
        if not respondibles:
            return 0.0
        aciertos = sum(
            1
            for c in respondibles
            if (puesto := getattr(c, atributo)) is not None and puesto <= corte
        )
        return aciertos / len(respondibles)

    def recall_lexico_en(self, corte: int) -> float:
        return self._recall("puesto_lexico", corte)

    def recall_hibrido_en(self, corte: int) -> float:
        return self._recall("puesto_hibrido", corte)

    @property
    def recall_hibrido(self) -> float:
        return self.recall_hibrido_en(5)

    @property
    def respondibles(self) -> int:
        return sum(1 for c in self.casos if not c.fuera_del_corte)

    @property
    def cumple(self) -> bool:
        return self.recall_hibrido >= UMBRAL_RECALL_5 and not self.fugas


def hash_de_preguntas(preguntas: list[dict]) -> str:
    """Huella de las preguntas, no del archivo.

    Se hashea solo lo que decide el resultado —id, consulta y respuesta
    esperada—, así una nota aclaratoria o un cambio de formato no obligan a
    volver a congelar, y cambiar lo que se pregunta sí.
    """
    canonico = json.dumps(
        [{"id": p["id"], "consulta": p["consulta"], "responde": p["responde"]} for p in preguntas],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def cargar(ruta: pathlib.Path) -> tuple[list[Caso], list[str]]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    preguntas = datos["preguntas"]
    esperado = datos.get("congelado", {}).get("hash", "")
    real = hash_de_preguntas(preguntas)
    if esperado != real:
        raise ConjuntoAlterado(
            f"El conjunto de evaluación cambió y su hash no.\n"
            f"  declarado: {esperado}\n"
            f"  real:      {real}\n"
            "Si el cambio es deliberado, actualizá `congelado.hash` en el mismo commit "
            "que cambia la pregunta, para que se vea qué se cambió y cuándo. Un conjunto "
            "que se edita después de ver el resultado no mide nada."
        )
    casos = [
        Caso(
            id=p["id"],
            consulta=p["consulta"],
            responde=p["responde"],
            por_que=p.get("por_que", ""),
            fuera_del_corte=bool(p.get("fuera_del_corte", False)),
        )
        for p in preguntas
    ]
    return casos, list(datos.get("fuera_del_corte", []))


def _puesto(fragmentos, ruta_esperada: str) -> int | None:
    for posicion, fragmento in enumerate(fragmentos, start=1):
        if fragmento.unidad == ruta_esperada:
            return posicion
    return None


def correr(
    conexion: Connection,
    ruta: pathlib.Path,
    *,
    embebedor: Embebedor | None = None,
    limite: int = max(CORTES),
) -> Reporte:
    casos, sondas_fuera = cargar(ruta)
    embebedor = embebedor or EmbebedorFastEmbed()
    reporte = Reporte(modelo=embebedor.modelo, casos=casos)

    release = conexion.execute(
        text(
            "SELECT id FROM releases WHERE estado = 'PUBLICADO' ORDER BY publicado_en DESC LIMIT 1"
        )
    ).scalar_one_or_none()
    if release is None:
        reporte.avisos.append("No hay corte publicado: no hay nada que evaluar.")
        return reporte
    reporte.release_id = release
    reporte.fragmentos_indexados = (
        conexion.execute(
            text(
                "SELECT coalesce(sum(fragmentos), 0) FROM indices_semanticos "
                " WHERE release_id = :r AND modelo = :m"
            ),
            {"r": release, "m": embebedor.modelo},
        ).scalar_one()
        or 0
    )

    for caso in casos:
        lexica = buscar(conexion, caso.consulta, release_id=release, embebedor=None, limite=limite)
        hibrida = buscar(
            conexion, caso.consulta, release_id=release, embebedor=embebedor, limite=limite
        )
        caso.puesto_lexico = _puesto(lexica.fragmentos, caso.responde)
        caso.puesto_hibrido = _puesto(hibrida.fragmentos, caso.responde)

    # Lo que el corte no publica no se recupera, por más que exista en el
    # corpus. Se prueba buscándolo a propósito.
    for sonda in sondas_fuera:
        resultado = buscar(conexion, sonda, release_id=release, embebedor=embebedor, limite=limite)
        if resultado.fragmentos:
            reporte.fugas.append(
                f"«{sonda}» devolvió {len(resultado.fragmentos)} fragmento(s) y no debía "
                "devolver ninguno: ese texto no está en el corte publicado."
            )
    return reporte


def formatear(reporte: Reporte) -> str:
    lineas = [
        "# Recuperación: léxica contra híbrida",
        "",
        f"- Corte evaluado: `{reporte.release_id or '—'}`",
        f"- Modelo: `{reporte.modelo}`",
        f"- Fragmentos indexados: **{reporte.fragmentos_indexados}**",
        f"- Preguntas respondibles: **{reporte.respondibles}** de {len(reporte.casos)}",
        "",
        "## Recall@k",
        "",
        "| k | Léxica sola | Híbrida | Diferencia |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for corte in CORTES:
        lexico = reporte.recall_lexico_en(corte)
        hibrido = reporte.recall_hibrido_en(corte)
        lineas.append(f"| {corte} | {lexico:.1%} | {hibrido:.1%} | {hibrido - lexico:+.1%} |")

    lineas += [
        "",
        f"El umbral del plan es Recall@5 ≥ {UMBRAL_RECALL_5:.0%} sobre preguntas respondibles. "
        f"Resultado: **{reporte.recall_hibrido:.1%}**"
        f" — {'cumple' if reporte.recall_hibrido >= UMBRAL_RECALL_5 else 'no cumple'}.",
        "",
        "## Qué encontró cada una",
        "",
        "| Caso | Consulta | Responde | Léxica | Híbrida |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for caso in reporte.casos:
        if caso.fuera_del_corte:
            continue
        lex = str(caso.puesto_lexico) if caso.puesto_lexico else "—"
        hib = str(caso.puesto_hibrido) if caso.puesto_hibrido else "—"
        lineas.append(f"| {caso.id} | {caso.consulta} | `{caso.responde}` | {lex} | {hib} |")

    lineas += ["", "## Que no se filtre lo que el corte no publica", ""]
    if reporte.fugas:
        lineas += [f"- {fuga}" for fuga in reporte.fugas]
    else:
        lineas.append(
            "Ninguna sonda devolvió fragmentos. Lo que no está en el corte no se recupera, "
            "y no porque la consulta se acuerde de filtrar: un vector cuelga de un índice y "
            "un índice cuelga de un corte, así que no hay dónde guardar lo que no pertenece."
        )
    for aviso in reporte.avisos:
        lineas += ["", aviso]
    return "\n".join(lineas)
