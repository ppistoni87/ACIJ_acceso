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
# Uso: bash scripts/corrida_limpia.sh [base] [salida] [--sin-catalogo-nacional]
set -euo pipefail

BASE="${1:-backend_normativo_limpia}"
SALIDA="${2:-docs/reportes/corrida_limpia.md}"
EXTRA="${3:-}"

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
ANTES=""
DESPUES=""
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
  # Se cuentan los que tienen al menos una regla. `beneficios` a secas contaba
  # también los que una lectura fallida dejó escritos antes de rechazarse: un
  # beneficio sin ninguna condición no es un beneficio curado, y contarlo hacía
  # que el total tapara justamente las lecturas que no habían entrado.
  beneficios=$(sql "SELECT count(DISTINCT bv.beneficio_id) FROM beneficio_versiones bv
                      JOIN reglas r ON r.beneficio_version_id = bv.registro_version_id" \
                 2>/dev/null || echo "—")
  incidencias=$(sql "SELECT count(*) FROM incidencias_revision WHERE estado='ABIERTA'" \
    2>/dev/null || echo "—")

  mkdir -p "$(dirname "${SALIDA}")"
  {
    echo "# Corrida limpia: de una base vacía a un corpus servible"
    echo
    echo "Lo que esto demuestra es que la puesta en marcha es reproducible: las"
    echo "migraciones corren desde cero, el catálogo de las 83 fuentes entra, el"
    echo "planificador recorre la red de verdad, los importadores cargan el catálogo"
    echo "nacional, el padrón y los directorios, y la curación trabaja sobre lo"
    echo "capturado."
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
    echo "- Fuentes que el planificador deja pendientes al cerrar: \`${PENDIENTES_AL_CIERRE:-—}\`"
    echo
    echo "## Pasos"
    echo
    echo "El detalle paso por paso vive en \`scripts/poblar_corpus.sh\`, que es lo que"
    echo "corre acá. Lo que se mide es cuánto tarda entero y con qué queda."
    echo
    echo "| Paso | Duración | Última línea |"
    echo "| --- | ---: | --- |"
    cat "${TABLA}"
    echo
    if [ -s "${CONTROLES:-/dev/null}" ]; then
      echo "## Controles sobre el corpus recién construido"
      echo
      echo "Corren acá y no en la población porque es el único lugar donde el corpus"
      echo "se armó desde cero: un control sobre una base de desarrollo puede estar"
      echo "pasando por un resto de una corrida anterior."
      echo
      echo "| Control | Veredicto | Qué contó |"
      echo "| --- | --- | --- |"
      cat "${CONTROLES}"
      echo
    fi
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
    echo "escondiendo algo. La enorme mayoría viene del catálogo nacional, que se importa"
    echo "entero como metadatos: son normas cuyo tipo se numera por organismo y cuya"
    echo "clave (tipo, número, año) no las distingue. Quedan marcadas para que ninguna"
    echo "resuelva una cita por número, que es exactamente lo que la incidencia protege."
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
    echo "No todas las corridas en \`FALLIDA\` son iguales. Un tiempo de espera agotado o una"
    echo "conexión cortada es el portal de turno teniendo un mal momento: el cliente reintenta"
    echo "tres veces y a veces no alcanza, así que el número de capturas varía de una corrida a"
    echo "la siguiente. Eso no cambia lo que el sistema afirma —una fuente que no entregó no"
    echo "aporta nada, y se nota— pero explica por qué dos corridas del mismo día no dan"
    echo "exactamente el mismo total."
    echo
    echo "Las otras dos no son un error del sistema: son el"
    echo "sistema haciendo lo que tiene que hacer cuando el otro lado no deja pasar. Un"
    echo "certificado que no valida no se acepta igual, y un 403 no se contesta rotando"
    echo "identidad: la fuente queda pausada, con el motivo escrito en la fila de su"
    echo "corrida, y su cobertura se resuelve por fuente equivalente o carga manual"
    echo "trazada. Volverlas verdes relajando TLS o cambiando de identidad sería"
    echo "convertir un acceso bloqueado en un dato inventado."
    echo
    echo "## La segunda pasada no agrega nada"
    echo
    echo "El procedimiento se documenta como idempotente: reejecutarlo revalida las"
    echo "capturas, no duplica versiones y solo reprocesa lo que cambió. Acá se corre"
    echo "dos veces seguidas sobre la misma base y se cuenta lo que hay antes y después."
    echo "Una primera pasada nunca prueba la segunda, y la segunda es la que corre en"
    echo "producción todos los días."
    echo
    if [ -n "${ANTES}" ] && [ -n "${DESPUES}" ]; then
      echo "| Momento | Versiones de documento |"
      echo "| --- | ---: |"
      echo "| Después de la primera pasada | ${ANTES} |"
      echo "| Después de la segunda | ${DESPUES} |"
      echo
      if [ "${ANTES}" != "${DESPUES}" ]; then
        echo "> **La segunda pasada agregó versiones:** de ${ANTES} a ${DESPUES}. Volver a"
        echo "> pedir lo mismo no lo cambia, así que una versión nueva es una versión"
        echo "> duplicada: el procedimiento no es idempotente y lo que dice de sí mismo es"
        echo "> falso."
        echo
      fi
    else
      echo "La segunda pasada no llegó a correr: la corrida se interrumpió antes."
      echo
    fi
    echo "## Lecturas curadas que no se pudieron cargar"
    echo
    echo "Una lectura curada se apoya en el texto capturado de su norma: sin ese texto no"
    echo "hay nada que citar y el beneficio no entra. Que falte no es un error de la"
    echo "lectura, es que la fuente no entregó en esta corrida."
    echo
    faltantes=0
    esperados=""
    for archivo in docs/curaduria/*.json; do
      [ -e "${archivo}" ] || continue
      externo=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['norma']['external_id'])" "${archivo}")
      # No se llama `codigo`: `al_salir` guarda ahí el estado de salida de la
      # corrida y esto corre adentro de esa función, así que pisarlo hacía que
      # una corrida buena terminara con el código de un beneficio por número.
      codigo_beneficio=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['beneficio']['codigo'])" "${archivo}")
      existe=$(sql "SELECT count(*) FROM documentos WHERE external_id = '${externo}'")
      if [ "${existe}" = "0" ]; then
        faltantes=$((faltantes + 1))
        [ "${faltantes}" = 1 ] && { echo "| Lectura | Norma que le falta |"; echo "| --- | --- |"; }
        echo "| \`$(basename "${archivo}")\` | \`${externo}\` |"
      else
        esperados="${esperados}${codigo_beneficio}\n"
      fi
    done
    lecturas=$(ls docs/curaduria/*.json 2>/dev/null | wc -l)
    if [ "${faltantes}" = 0 ]; then
      echo "Ninguna: las ${lecturas} lecturas curadas encontraron su norma en el corpus."
    fi
    echo
    # Una lectura no es un beneficio: un mismo beneficio puede estar leído desde
    # la norma que lo crea y desde la que después le sustituye artículos. Lo que
    # tiene que cerrar es la cuenta de códigos distintos entre las lecturas cuya
    # norma sí está en el corpus. Si no da, el reporte se está contradiciendo y
    # lo dice: un informe que se desmiente a sí mismo sin avisar es peor que no
    # tenerlo.
    distintos=$(printf "%b" "${esperados}" | sort -u | grep -c . || true)
    if [ "${beneficios}" != "${distintos}" ]; then
      echo "> **El reporte no cierra:** ${lecturas} lecturas curadas, ${faltantes} sin su norma"
      echo "> en el corpus y ${distintos} código(s) de beneficio distinto(s) entre las que sí la"
      echo "> tienen, pero la base quedó con ${beneficios}. Hay un error en este informe o una"
      echo "> lectura que cargó a medias; no se puede leer como evidencia hasta resolverlo."
      echo
    fi
    # Que la norma esté en el corpus no quiere decir que la lectura haya
    # entrado: una cita que no encuentra su unidad detiene esa lectura y deja
    # las demás. Cada lectura cargada ata su beneficio a su norma, así que las
    # filas de ese vínculo son la cuenta de las que sí entraron.
    cargadas=$(sql "SELECT count(*) FROM beneficio_normas bn
                      WHERE EXISTS (SELECT 1 FROM reglas r
                                     WHERE r.beneficio_version_id = bn.beneficio_version_id)")
    if [ "${cargadas}" != "$((lecturas - faltantes))" ]; then
      echo "> **Faltan lecturas:** ${lecturas} lecturas curadas, ${faltantes} sin su norma en el"
      echo "> corpus, así que tendrían que haber entrado $((lecturas - faltantes)) y entraron"
      echo "> ${cargadas}. Las que faltan no son fuentes que no entregaron: son lecturas que la"
      echo "> carga rechazó, y el motivo está en la salida de \`bn curacion beneficios\`."
      echo
    fi
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

# La población no se redefine acá: se llama a `scripts/poblar_corpus.sh`, que es
# la única definición del procedimiento. Dos listas de pasos garantizan que una
# de las dos quede vieja, y la que quedaría vieja es siempre la que nadie corre
# todos los días.
# shellcheck disable=SC2086
cronometrar "población completa" bash scripts/poblar_corpus.sh --sin-informes ${EXTRA}

# Y otra vez, sobre la base que acaba de quedar poblada. El procedimiento dice
# de sí mismo que es idempotente y eso hay que ejercitarlo, no declararlo: la
# primera pasada nunca prueba la segunda. Cuatro importadores creaban una
# versión de documento por captura y la segunda pasada chocaba contra la
# restricción que impide duplicar una versión con el mismo contenido; no se veía
# porque la corrida limpia empieza de cero y la base de desarrollo nunca empieza
# de cero.
ANTES=$(sql "SELECT count(*) FROM documento_versiones" 2>/dev/null || echo "")
# shellcheck disable=SC2086
cronometrar "segunda pasada (idempotencia)" bash scripts/poblar_corpus.sh --sin-informes --sin-ampliar ${EXTRA}
DESPUES=$(sql "SELECT count(*) FROM documento_versiones" 2>/dev/null || echo "")

# Al cerrar, el planificador se vuelve a preguntar a quién le toca. Si el
# recorrido hizo lo que dice, ya no le toca a nadie: eso es lo que se mira.
cronometrar "planificación al cierre (en seco)" ${VENV}/bn monitoreo ciclo --en-seco
PENDIENTES_AL_CIERRE=$(grep -oP 'vuelven a la cola: \*\*\K\d+' "${BITACORA}" | head -1 || true)

# Los controles de calidad corren acá y no en la población: es el único lugar
# donde el corpus se construyó desde cero, y un control sobre una base de
# desarrollo puede estar pasando por un resto de una corrida anterior. No
# escriben en `docs/reportes/`: esos informes son del corpus real y esta base se
# destruye en un rato. Lo que dicen entra en este reporte.
CONTROLES=$(mktemp)
for control in "ingesta conciliar" "calidad grafo" "calidad plazos" "calidad fuentes"; do
  # shellcheck disable=SC2086
  if salida_control=$(${VENV}/bn ${control} 2>&1); then
    veredicto="pasa"
  else
    veredicto="**FALLA**"
    ESTADO_FINAL="con controles en rojo"
  fi
  resumen=$(printf '%s' "${salida_control}" | grep -E '^- ' | head -4 | tr '\n' ' ' | tr -s ' ')
  printf '| `bn %s` | %s | %s |\n' "${control}" "${veredicto}" "${resumen:0:220}" >> "${CONTROLES}"
done
