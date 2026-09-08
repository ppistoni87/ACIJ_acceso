"""DQ18: evaluación conversacional sobre el corpus publicado.

La gate pide un conjunto experto de al menos 60 consultas, con ambiguas e
históricas, y que pasen el 100% de los casos críticos de no exclusión, cita,
monto, fecha, identidad y revocación.

Lo que se verifica acá no es la redacción de una respuesta —eso lo hace el
sistema conversacional, no el backend— sino lo que el backend le entrega: si
para cada consulta devuelve un dato con evidencia localizable, se abstiene con
un motivo, pide los datos que faltan o falla con un error tipado. Ese es el
insumo con el que se responde, y es donde se decide si la respuesta va a poder
ser honesta.

Una abstención esperada que se cumple **es** un caso que pasa. La mayoría de las
consultas del conjunto preguntan por datos que el corpus todavía no tiene: que
el backend lo diga, en vez de devolver algo parecido, es exactamente lo que hay
que comprobar.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

RUTA_CONSULTAS = pathlib.Path("docs/calidad/consultas_conversacionales.json")

COMPORTAMIENTOS = ("RESPONDE_CON_EVIDENCIA", "SE_ABSTIENE", "PIDE_DATOS", "ERROR_TIPADO")

# Familias críticas de la gate: acá no se admite un caso que no pase.
CRITICAS = frozenset({"no_exclusion", "cita", "monto", "fecha", "identidad", "revocacion"})


class ConjuntoInsuficiente(Exception):
    """El conjunto no llega al mínimo o declara algo fuera del contrato."""


@dataclass
class ResultadoConsulta:
    id: str
    consulta: str
    familia: str
    operacion: str
    espera: str
    observado: str = ""
    detalle: str = ""
    at: str | None = None

    @property
    def pasa(self) -> bool:
        return self.observado == self.espera


@dataclass
class ReporteConversacional:
    total: int = 0
    pasan: int = 0
    fallan: int = 0
    criticas: int = 0
    criticas_que_pasan: int = 0
    release_id: str | None = None
    resultados: list[ResultadoConsulta] = field(default_factory=list)

    @property
    def cumple_la_gate(self) -> bool:
        return self.total >= 60 and self.criticas > 0 and self.criticas_que_pasan == self.criticas


def correr(
    conexion: Connection, cliente, *, raiz: pathlib.Path | None = None
) -> ReporteConversacional:
    base = raiz or pathlib.Path.cwd()
    documento = json.loads((base / RUTA_CONSULTAS).read_text())
    consultas = documento["consultas"]
    if len(consultas) < 60:
        raise ConjuntoInsuficiente(
            f"El conjunto tiene {len(consultas)} consultas y la gate pide 60 como mínimo."
        )
    fuera = sorted({c["espera"] for c in consultas} - set(COMPORTAMIENTOS))
    if fuera:
        raise ConjuntoInsuficiente(f"Comportamientos esperados fuera del contrato: {fuera}.")

    norma_id = _norma_publicada(conexion)
    reporte = ReporteConversacional(total=len(consultas))
    for consulta in consultas:
        resultado = ResultadoConsulta(
            id=consulta["id"],
            consulta=consulta["consulta"],
            familia=consulta["familia"],
            operacion=consulta["operacion"],
            espera=consulta["espera"],
            at=consulta.get("at"),
        )
        resultado.observado, resultado.detalle = _ejecutar(cliente, consulta, norma_id)
        reporte.resultados.append(resultado)
        if resultado.pasa:
            reporte.pasan += 1
        else:
            reporte.fallan += 1
        if consulta["familia"] in CRITICAS:
            reporte.criticas += 1
            if resultado.pasa:
                reporte.criticas_que_pasan += 1

    if norma_id is not None:
        cuerpo = cliente.get(f"/v1/normas/{norma_id}").json()
        reporte.release_id = cuerpo.get("release_id")
    return reporte


def _norma_publicada(conexion: Connection) -> uuid.UUID | None:
    return conexion.execute(
        text(
            "SELECT nv.norma_id FROM norma_versiones nv "
            "  JOIN registro_versiones rv ON rv.id = nv.registro_version_id "
            " WHERE rv.release_id IS NOT NULL ORDER BY rv.known_desde LIMIT 1"
        )
    ).scalar_one_or_none()


def _ejecutar(cliente, consulta: dict, norma_id: uuid.UUID | None) -> tuple[str, str]:
    operacion = consulta["operacion"]
    argumento = consulta.get("argumento")

    if operacion == "norma_inexistente":
        respuesta = cliente.get(f"/v1/normas/{uuid.uuid4()}")
        codigo = respuesta.json().get("detail", {}).get("codigo")
        return (
            "ERROR_TIPADO" if codigo else "SIN_CLASIFICAR",
            f"HTTP {respuesta.status_code} · {codigo}",
        )

    if operacion in ("ficha", "campo"):
        if norma_id is None:
            return ("SE_ABSTIENE", "No hay ninguna norma publicada.")
        cuerpo = cliente.get(f"/v1/normas/{norma_id}").json()
        if operacion == "ficha":
            return _clasificar_ficha(cuerpo)
        return _clasificar_campo(cuerpo, argumento)

    if operacion == "buscar":
        cuerpo = cliente.get("/v1/normas", params={"q": argumento}).json()
        return _clasificar_envoltura(cuerpo, len(cuerpo["data"]["items"]))

    if operacion == "recuperar":
        cuerpo = cliente.post("/v1/recuperacion", json={"consulta": argumento, "limite": 3}).json()
        fragmentos = cuerpo["data"].get("fragmentos", [])
        if fragmentos and all(f.get("cita") or f.get("ruta") for f in fragmentos):
            return ("RESPONDE_CON_EVIDENCIA", f"{len(fragmentos)} fragmento(s) con cita.")
        return _clasificar_envoltura(cuerpo, len(fragmentos))

    if operacion == "beneficios":
        cuerpo = cliente.get("/v1/beneficios").json()
        return _clasificar_envoltura(cuerpo, len(cuerpo["data"]["items"]))

    if operacion == "puntos_atencion":
        cuerpo = cliente.get("/v1/puntos-atencion").json()
        return _clasificar_envoltura(cuerpo, len(cuerpo["data"]))

    if operacion == "valores":
        respuesta = cliente.get("/v1/valores", params={"concepto": argumento})
        if respuesta.status_code >= 400:
            detalle = respuesta.json().get("detail", {})
            codigo = detalle.get("codigo") if isinstance(detalle, dict) else None
            return ("ERROR_TIPADO" if codigo else "SIN_CLASIFICAR", f"HTTP {respuesta.status_code}")
        cuerpo = respuesta.json()
        return _clasificar_envoltura(cuerpo, len(cuerpo["data"]))

    if operacion == "plazos":
        respuesta = cliente.get(
            "/v1/plazos", params={"beneficio_id": argumento} if argumento else None
        )
        detalle = respuesta.json().get("detail", {}) if respuesta.status_code >= 400 else {}
        if respuesta.status_code >= 400:
            codigo = detalle.get("codigo") if isinstance(detalle, dict) else None
            return (
                "PIDE_DATOS" if codigo == "INVALID_REQUEST" else "SIN_CLASIFICAR",
                f"HTTP {respuesta.status_code} · {codigo}",
            )
        cuerpo = respuesta.json()
        return _clasificar_envoltura(cuerpo, len(cuerpo["data"]))

    if operacion == "cobertura":
        cuerpo = cliente.get("/v1/cobertura").json()
        return ("RESPONDE_CON_EVIDENCIA", f"Métricas: {', '.join(sorted(cuerpo['data']))}.")

    raise ConjuntoInsuficiente(f"Operación desconocida en el conjunto: {operacion!r}.")


def _clasificar_ficha(cuerpo: dict) -> tuple[str, str]:
    versiones = cuerpo["data"].get("versiones", [])
    servibles = [v for v in versiones if v["servible"]]
    if servibles and cuerpo["evidence"]:
        return (
            "RESPONDE_CON_EVIDENCIA",
            f"{len(servibles)} versión(es) servible(s) y {len(cuerpo['evidence'])} evidencia(s).",
        )
    motivos = [m for v in versiones for m in v["motivos_no_servible"]]
    if motivos or cuerpo["warnings"]:
        return ("SE_ABSTIENE", "; ".join(motivos[:2]) or cuerpo["warnings"][0]["detalle"])
    return ("SIN_CLASIFICAR", f"data_status {cuerpo['data_status']} sin motivo declarado.")


def _clasificar_campo(cuerpo: dict, campo: str) -> tuple[str, str]:
    ficha = cuerpo["data"]["campos"].get(campo)
    if ficha is None:
        return ("SIN_CLASIFICAR", f"El campo {campo} no viaja en la ficha.")
    estado = ficha.get("estado")
    valores = ficha.get("valores", [])
    if estado == "INFORMADO" and valores:
        return ("RESPONDE_CON_EVIDENCIA", f"{len(valores)} valor(es) con estado {estado}.")
    if campo in cuerpo["missing_fields"] or estado in (
        "NO_INFORMADO_EN_FUENTES_REVISADAS",
        "EN_CONFLICTO",
        "PENDIENTE",
    ):
        return ("SE_ABSTIENE", f"Estado {estado}; el campo figura como faltante.")
    return ("SIN_CLASIFICAR", f"Estado {estado} con {len(valores)} valor(es).")


def _clasificar_envoltura(cuerpo: dict, cuantos: int) -> tuple[str, str]:
    if cuantos and cuerpo["data_status"] == "PUBLICADO":
        return ("RESPONDE_CON_EVIDENCIA", f"{cuantos} resultado(s) sobre el release publicado.")
    if cuerpo["warnings"]:
        return ("SE_ABSTIENE", cuerpo["warnings"][0]["detalle"])
    if cuerpo["data_status"] in ("SIN_RESULTADOS", "NO_PUBLICABLE"):
        return ("SE_ABSTIENE", f"data_status {cuerpo['data_status']}, sin resultados.")
    return ("SIN_CLASIFICAR", f"data_status {cuerpo['data_status']} con {cuantos} resultado(s).")


def formatear(reporte: ReporteConversacional) -> str:
    lineas = [
        "# Evaluación conversacional",
        "",
        f"- Consultas del conjunto: **{reporte.total}** (la gate pide 60 como mínimo)",
        f"- Pasan: **{reporte.pasan}** · fallan: **{reporte.fallan}**",
        f"- Casos críticos: **{reporte.criticas}**, de los cuales pasan "
        f"**{reporte.criticas_que_pasan}**",
        f"- Release evaluado: `{reporte.release_id}`",
        f"- Gate DQ18: **{'cumple' if reporte.cumple_la_gate else 'no cumple'}**",
        "",
        "Lo que se comprueba no es cómo se redacta la respuesta —eso es del sistema",
        "conversacional— sino lo que el backend entrega: un dato con evidencia localizable,",
        "una abstención con motivo, un pedido de datos o un error tipado.",
        "",
        "**Una abstención esperada que se cumple es un caso que pasa.** La mayoría de estas",
        "consultas preguntan por datos que el corpus todavía no tiene; que el backend lo diga,",
        "en vez de devolver algo parecido, es justamente lo que hay que comprobar.",
        "",
        "| ID | AT | Familia | Consulta | Espera | Observado | Detalle |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in reporte.resultados:
        marca = "" if r.pasa else " ❌"
        lineas.append(
            f"| {r.id} | {r.at or '—'} | {r.familia} | {r.consulta} | {r.espera} "
            f"| {r.observado}{marca} | {r.detalle} |"
        )
    if reporte.fallan:
        lineas += [
            "",
            "## Consultas que no se comportaron como se esperaba",
            "",
        ]
        for r in reporte.resultados:
            if not r.pasa:
                lineas.append(
                    f"- **{r.id}** ({r.familia}): esperaba {r.espera}, "
                    f"dio {r.observado}. {r.detalle}"
                )
    return "\n".join(lineas)
