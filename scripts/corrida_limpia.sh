#!/usr/bin/env bash
# HU-039: el ciclo completo sobre una base que empieza vacía.
#
# Lo que esto demuestra es la reproducibilidad de la puesta en marcha: que las
# migraciones corran desde cero, que el catálogo de las 83 fuentes entre, que la
# captura recorra las fuentes activas contra la red de verdad y que la curación
# cargue sobre lo capturado.
#
# Lo que NO demuestra es que corra igual en otra máquina o desde otra red: eso
# necesita otra máquina y otra red. Lo que sí hace es dejar el procedimiento
# escrito, cronometrado y con el resultado fuente por fuente, para que la
# diferencia se pueda medir cuando alguien lo corra allá.
#
# Uso: bash scripts/corrida_limpia.sh [base] [salida] [fuentes|TODAS]
set -euo pipefail

BASE="${1:-backend_normativo_limpia}"
SALIDA="${2:-docs/reportes/corrida_limpia.md}"
FUENTES="${3:-TODAS}"

# El nombre de la base entra en un DROP DATABASE. Que sea un identificador simple
# no es cosmética: es lo único que separa un argumento de un comando.
if ! [[ "${BASE}" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
  echo "Nombre de base inválido: ${BASE}" >&2
  exit 2
fi

VENV=".venv/bin"
BASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/${BASE}"

sql() { PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d "${BASE}" -tAF'|' -c "$1"; }
admin() { PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d postgres -q "$@"; }

TABLA=$(mktemp)
BITACORA=$(mktemp)
ARRANQUE=$(date -Iseconds)
ESTADO_FINAL="completa"
PENDIENTES_AL_CIERRE=""

cronometrar() {
  local etiqueta="$1"; shift
  local inicio fin detalle
  inicio=$(date +%s.%N)
  if ! "$@" >"${BITACORA}" 2>&1; then
    fin=$(date +%s.%N)
    printf '| %s | %.1f s | **falló** — %s |\n' "${etiqueta}" \
      "$(echo "${fin} - ${inicio}" | bc)" "$(recortar "$(tail -1 "${BITACORA}")")" >>"${TABLA}"
    echo "FALLÓ: ${etiqueta}" >&2
    tail -15 "${BITACORA}" >&2
    ESTADO_FINAL="interrumpida en «${etiqueta}»"
    return 1
  fi
  fin=$(date +%s.%N)
  detalle=$(recortar "$(tail -1 "${BITACORA}")")
  printf '| %s | %.1f s | %s |\n' "${etiqueta}" "$(echo "${fin} - ${inicio}" | bc)" "${detalle}" \
    >>"${TABLA}"
}

recortar() {
  local texto="${1//|/ }"
  if [ "${#texto}" -gt 88 ]; then echo "${texto:0:88}…"; else echo "${texto}"; fi
}

escribir_reporte() {
  local fuentes_cargadas capturas unidades beneficios incidencias
  fuentes_cargadas=$(sql "SELECT count(*) FROM fuentes" 2>/dev/null || echo "—")
  capturas=$(sql "SELECT count(*) FROM capturas" 2>/dev/null || echo "—")
  unidades=$(sql "SELECT count(*) FROM unidades_documentales" 2>/dev/null || echo "—")
  beneficios=$(sql "SELECT count(*) FROM beneficios" 2>/dev/null || echo "—")
  incidencias=$(sql "SELECT count(*) FROM incidencias_revision WHERE estado='ABIERTA'" \
    2>/dev/null || echo "—")

  mkdir -p "$(dirname "${SALIDA}")"
  {
    echo "# Corrida limpia: de una base vacía a un corpus servible"
    echo
    echo "Lo que esto demuestra es que la puesta en marcha es reproducible: las"
    echo "migraciones corren desde cero, el catálogo de las 83 fuentes entra, la captura"
    echo "recorre las fuentes activas contra la red de verdad y la curación carga sobre"
    echo "lo capturado."
    echo
    echo "Lo que **no** demuestra es que corra igual en otra máquina o desde otra red."
    echo "Para eso hace falta otra máquina y otra red; lo que queda acá es el"
    echo "procedimiento escrito, cronometrado y con el resultado fuente por fuente, para"
    echo "que la diferencia se pueda medir cuando alguien lo corra allá."
    echo
    echo "Generado por \`scripts/corrida_limpia.sh\`. La base se crea y se destruye en la"
    echo "misma corrida: si algo de acá se pudiera explicar por estado previo, no habría"
    echo "estado previo del que agarrarse."
    echo
    echo "- Arranque: \`${ARRANQUE}\`"
    echo "- Cierre: \`$(date -Iseconds)\`"
    echo "- Resultado: **${ESTADO_FINAL}**"
    echo "- Base: \`${BASE}\`"
    echo "- Fuentes pedidas a la captura: \`${FUENTES}\`"
    echo "- Fuentes que el planificador deja pendientes al cerrar: \`${PENDIENTES_AL_CIERRE:-—}\`"
    echo
    echo "## Pasos"
    echo
    echo "| Paso | Duración | Última línea |"
    echo "| --- | ---: | --- |"
    cat "${TABLA}"
    echo
    echo "## Con qué quedó la base"
    echo
    echo "| Qué | Cuántos |"
    echo "| --- | ---: |"
    echo "| Fuentes en el catálogo | ${fuentes_cargadas} |"
    echo "| Capturas | ${capturas} |"
    echo "| Unidades documentales | ${unidades} |"
    echo "| Beneficios curados | ${beneficios} |"
    echo "| Incidencias abiertas | ${incidencias} |"
    echo
    echo "Las incidencias abiertas no son un fallo de la corrida: son lo que el sistema"
    echo "encontró y no resolvió solo. Una corrida limpia que no abriera ninguna estaría"
    echo "escondiendo algo."
    echo
    echo "## Qué pasó fuente por fuente"
    echo
    echo "Una fuente que no entrega no es una fuente vacía. Acá está el estado con el que"
    echo "cerró cada corrida de ingesta, con lo que el servidor contestó cuando contestó"
    echo "algo distinto de los datos."
    echo
    echo "| Fuente | Estado | Solicitadas | Descargadas | Rechazadas | Detalle |"
    echo "| --- | --- | ---: | ---: | ---: | --- |"
    sql "SELECT ci.source_id, ci.estado, ci.solicitadas, ci.descargadas, ci.rechazadas,
                coalesce(replace(left(ci.detalle_error, 110), '|', ' '), '')
         FROM corridas_ingesta ci ORDER BY
           CASE ci.estado WHEN 'FALLIDA' THEN 0 WHEN 'PARCIAL' THEN 1 ELSE 2 END, ci.source_id" \
      2>/dev/null | awk -F'|' '{printf "| %s | %s | %s | %s | %s | %s |\n",$1,$2,$3,$4,$5,$6}'
    echo
    echo "Las corridas en \`FALLIDA\` de esta lista no son un error del sistema: son el"
    echo "sistema haciendo lo que tiene que hacer cuando el otro lado no deja pasar. Un"
    echo "certificado que no valida no se acepta igual, y un 403 no se contesta rotando"
    echo "identidad: la fuente queda pausada, con el motivo escrito en la fila de su"
    echo "corrida, y su cobertura se resuelve por fuente equivalente o carga manual"
    echo "trazada. Volverlas verdes relajando TLS o cambiando de identidad sería"
    echo "convertir un acceso bloqueado en un dato inventado."
    echo
    echo "## Incidencias que abrió la corrida"
    echo
    echo "| Tipo | Cuántas |"
    echo "| --- | ---: |"
    sql "SELECT tipo, count(*) FROM incidencias_revision WHERE estado='ABIERTA'
         GROUP BY tipo ORDER BY 2 DESC, 1" 2>/dev/null \
      | awk -F'|' '{printf "| %s | %s |\n",$1,$2}'
  } >"${SALIDA}"
  echo "Reporte escrito en ${SALIDA}" >&2
}

al_salir() {
  local codigo=$?
  escribir_reporte
  if [ "${codigo}" -eq 0 ]; then
    admin -c "DROP DATABASE IF EXISTS \"${BASE}\" WITH (FORCE)"
  else
    echo "La base ${BASE} queda en pie para inspeccionar el fallo." >&2
  fi
  rm -f "${TABLA}" "${BITACORA}"
  return "${codigo}"
}

echo "Creando ${BASE} desde cero…" >&2
admin -c "DROP DATABASE IF EXISTS \"${BASE}\" WITH (FORCE)" -c "CREATE DATABASE \"${BASE}\""
trap al_salir EXIT

export BN_DATABASE_URL="${BASE_URL}"

cronometrar "migraciones" ${VENV}/alembic upgrade head
cronometrar "catálogo de fuentes" ${VENV}/bn catalogo cargar
cronometrar "conciliación del inventario" ${VENV}/bn catalogo conciliar

# El recorrido no se hace con una lista escrita a mano: se hace con el mismo
# planificador que corre en producción. Una lista a mano prueba que anda la lista;
# el ciclo prueba que anda la regla que decide a quién le toca —y que las fuentes
# que la política no habilita a automatizar, o que no tienen URL, quedan afuera
# solas en vez de que las saque el script.
if [ "${FUENTES}" = "TODAS" ]; then
  cronometrar "recorrido de fuentes (ciclo real)" ${VENV}/bn monitoreo ciclo
else
  # shellcheck disable=SC2086
  cronometrar "captura de red" ${VENV}/bn ingesta capturar ${FUENTES}
fi
cronometrar "extracción" ${VENV}/bn ingesta extraer
cronometrar "identidad de normas" ${VENV}/bn curacion identidad
cronometrar "relaciones normativas" ${VENV}/bn curacion relaciones
cronometrar "siete campos" ${VENV}/bn curacion campos
cronometrar "beneficios curados" ${VENV}/bn curacion beneficios
# Al cerrar, el planificador se vuelve a preguntar a quién le toca. Si el
# recorrido hizo lo que dice, ya no le toca a nadie: eso es lo que se mira.
cronometrar "planificación al cierre (en seco)" ${VENV}/bn monitoreo ciclo --en-seco
PENDIENTES_AL_CIERRE=$(grep -oP 'vuelven a la cola: \*\*\K\d+' "${BITACORA}" | head -1 || true)
