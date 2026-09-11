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
MARCA=""
SEGUNDAS_SOBRE_EXISTENTE=""
PRIMERAS_DE_DOCUMENTO_NUEVO=""
DETALLE_NO_IDEMPOTENTE=""
EVIDENCIA_NO_IDEMPOTENTE=""
TEXTOS_DIFERIDOS="${TEXTOS_DIFERIDOS:-docs/reportes/no_idempotencia}"
MARCA2=""
TRAS_TERCERA=""
TERCERA_SOBRE_EXISTENTE=""
TERCERA_PRIMERAS=""
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
    echo "## Qué agrega la segunda pasada"
    echo
    echo "El procedimiento se documenta como idempotente: reejecutarlo revalida las"
    echo "capturas, no duplica versiones y solo reprocesa lo que cambió. Acá se corre"
    echo "dos veces seguidas sobre la misma base y se cuenta lo que hay antes y después."
    echo "Una primera pasada nunca prueba la segunda, y la segunda es la que corre en"
    echo "producción todos los días."
    echo
    echo "El total solo no alcanza para juzgar: una versión nueva puede ser la **primera**"
    echo "de un documento que la primera pasada no alcanzó, o la **segunda** de uno que ya"
    echo "estaba. Únicamente la segunda rompe la idempotencia. Se cuentan por separado."
    echo
    if [ -n "${ANTES}" ] && [ -n "${DESPUES}" ]; then
      echo "| Momento | Versiones de documento |"
      echo "| --- | ---: |"
      echo "| Después de la primera pasada | ${ANTES} |"
      echo "| Después de la segunda | ${DESPUES} |"
      if [ -n "${TRAS_TERCERA}" ]; then
        echo "| Después de la tercera | ${TRAS_TERCERA} |"
      fi
      echo
      if [ "${SEGUNDAS_SOBRE_EXISTENTE:-0}" -gt 0 ] 2>/dev/null; then
        echo "> **El procedimiento no es idempotente.** La segunda pasada creó"
        echo "> ${SEGUNDAS_SOBRE_EXISTENTE} versión(es) sobre documentos que ya tenían una."
        echo "> Volver a pedir lo mismo no lo cambia, así que una segunda versión del"
        echo "> mismo documento es texto duplicado o extracción no determinista, y lo"
        echo "> que el procedimiento dice de sí mismo es falso. Por fuente:"
        echo "> ${DETALLE_NO_IDEMPOTENTE:-sin detalle}."
        echo
        if [ -n "${EVIDENCIA_NO_IDEMPOTENTE}" ]; then
          echo "Qué documento y cuánto cambió. Los textos completos de las dos versiones"
          echo "quedan en \`${TEXTOS_DIFERIDOS}/\` para poder diferenciarlos: la base se"
          echo "destruye al terminar la corrida y sin eso la evidencia se pierde con ella."
          echo
          echo "| Fuente | Documento | Versión | Caracteres |"
          echo "| --- | --- | ---: | --- |"
          echo "${EVIDENCIA_NO_IDEMPOTENTE}"
          echo
        fi
      elif [ "${PRIMERAS_DE_DOCUMENTO_NUEVO:-0}" -gt 0 ] 2>/dev/null; then
        echo "> **Ningún documento se duplicó**, y aun así el total subió de ${ANTES} a"
        echo "> ${DESPUES}: las ${PRIMERAS_DE_DOCUMENTO_NUEVO} versiones nuevas son todas la"
        echo "> primera de su documento. No son duplicados: son páginas que la primera"
        echo "> pasada nunca llegó a capturar, porque el descubrimiento de URLs corre"
        echo "> entremezclado con la captura y promueve hojas después de que su fuente ya"
        echo "> pasó. La segunda pasada no repite trabajo, lo termina."
        echo ">"
        echo "> Eso no es idempotencia rota, pero tampoco es un punto fijo: una pasada"
        echo "> sola no deja el corpus completo, y el procedimiento no debería decir que"
        echo "> sí. Lo que corresponde medir es si una tercera pasada agrega algo."
        echo
      else
        echo "La segunda pasada no agregó ninguna versión: ni un documento nuevo ni una"
        echo "versión sobre uno que ya estaba."
        echo
      fi
      if [ -n "${TRAS_TERCERA}" ]; then
        if [ "${TERCERA_SOBRE_EXISTENTE:-0}" -gt 0 ] 2>/dev/null; then
          echo "> **La tercera pasada volvió a versionar documentos existentes**"
          echo "> (${TERCERA_SOBRE_EXISTENTE}). No hay punto fijo: cada pasada reescribe lo"
          echo "> mismo, y eso es no determinismo o contenido que cambia solo."
          echo
        elif [ "${TERCERA_PRIMERAS:-0}" -gt 0 ] 2>/dev/null; then
          echo "> **La tercera pasada todavía encontró documentos nuevos**"
          echo "> (${TERCERA_PRIMERAS}). El recorrido no converge en dos pasadas: hay que"
          echo "> correrlo hasta que deje de crecer, y decir cuántas hacen falta."
          echo
        else
          echo "> **La tercera pasada no agregó nada.** Ahí está el punto fijo: el corpus"
          echo "> se completa en dos pasadas y a partir de la tercera reejecutar no cambia"
          echo "> nada. Eso es lo que la palabra idempotente tiene que significar acá."
          echo
        fi
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
# La marca separa lo que existía de lo que agregue la segunda pasada. Contar
# solo el total no alcanza: una versión nueva puede ser la primera de un
# documento que la primera pasada nunca alcanzó —porque el descubrimiento de
# URLs corre entremezclado con la captura y promueve hojas después de haber
# capturado su fuente— o la segunda de un documento que ya estaba. Solo la
# segunda es una violación de idempotencia; llamar duplicada a la primera es
# afirmar algo falso en un informe generado.
MARCA=$(sql "SELECT coalesce(max(creado_en), now())::text FROM documento_versiones" 2>/dev/null || echo "")
# shellcheck disable=SC2086
cronometrar "segunda pasada (idempotencia)" bash scripts/poblar_corpus.sh --sin-informes --sin-ampliar ${EXTRA}
DESPUES=$(sql "SELECT count(*) FROM documento_versiones" 2>/dev/null || echo "")
if [ -n "${MARCA}" ]; then
  SEGUNDAS_SOBRE_EXISTENTE=$(sql "SELECT count(*) FROM documento_versiones \
    WHERE creado_en > '${MARCA}' AND version > 1" 2>/dev/null || echo "")
  PRIMERAS_DE_DOCUMENTO_NUEVO=$(sql "SELECT count(*) FROM documento_versiones \
    WHERE creado_en > '${MARCA}' AND version = 1" 2>/dev/null || echo "")
  DETALLE_NO_IDEMPOTENTE=$(sql "SELECT string_agg(x.linea, ', ') FROM ( \
      SELECT d.source_id || ' (' || count(*) || ')' AS linea \
        FROM documento_versiones dv JOIN documentos d ON d.id = dv.documento_id \
       WHERE dv.creado_en > '${MARCA}' AND dv.version > 1 \
       GROUP BY d.source_id ORDER BY count(*) DESC) x" 2>/dev/null || echo "")
  # La base se destruye al terminar, así que la evidencia se junta ahora o no se
  # junta nunca. Sin esto, cada intento de explicar una versión de más empieza
  # por reconstruir a mano una base que ya no está, y se termina adivinando.
  EVIDENCIA_NO_IDEMPOTENTE=$(sql "SELECT string_agg(l, E'\n') FROM ( \
      SELECT '| ' || d.source_id || ' | ' || replace(coalesce(d.external_id,'?'),'|','/') \
             || ' | ' || nueva.version || ' | ' || length(previa.texto_extraido) \
             || ' → ' || length(nueva.texto_extraido) || ' |' AS l \
        FROM documento_versiones nueva \
        JOIN documentos d ON d.id = nueva.documento_id \
        JOIN LATERAL (SELECT * FROM documento_versiones p \
                       WHERE p.documento_id = nueva.documento_id \
                         AND p.version < nueva.version \
                       ORDER BY p.version DESC LIMIT 1) previa ON true \
       WHERE nueva.creado_en > '${MARCA}' AND nueva.version > 1 \
       ORDER BY d.source_id LIMIT 20) y" 2>/dev/null || echo "")
  # Y los textos completos a disco: comparar 7.978 caracteres a ojo dentro de una
  # celda de tabla no se puede, y el diff real es lo único que dice si cambió una
  # fecha, un teléfono o el orden de una lista.
  if [ -n "${EVIDENCIA_NO_IDEMPOTENTE}" ]; then
    mkdir -p "${TEXTOS_DIFERIDOS}"
    sql "COPY (SELECT d.source_id || '~' || nueva.version || '~' ||
                      translate(coalesce(d.external_id,'x'), '/:?&', '____')
                      || E'\t' || replace(nueva.texto_extraido, E'\n', '\\n')
                 FROM documento_versiones nueva
                 JOIN documentos d ON d.id = nueva.documento_id
                WHERE nueva.creado_en > '${MARCA}' AND nueva.version > 1)
          TO STDOUT" >"${TEXTOS_DIFERIDOS}/nuevas.tsv" 2>/dev/null || true
    sql "COPY (SELECT d.source_id || '~' || previa.version || '~' ||
                      translate(coalesce(d.external_id,'x'), '/:?&', '____')
                      || E'\t' || replace(previa.texto_extraido, E'\n', '\\n')
                 FROM documento_versiones nueva
                 JOIN documentos d ON d.id = nueva.documento_id
                 JOIN LATERAL (SELECT * FROM documento_versiones p
                                WHERE p.documento_id = nueva.documento_id
                                  AND p.version < nueva.version
                                ORDER BY p.version DESC LIMIT 1) previa ON true
                WHERE nueva.creado_en > '${MARCA}' AND nueva.version > 1)
          TO STDOUT" >"${TEXTOS_DIFERIDOS}/previas.tsv" 2>/dev/null || true
    echo "Evidencia de no idempotencia en ${TEXTOS_DIFERIDOS}" >&2
  fi
fi

# Si la segunda pasada solo terminó lo que la primera dejó a medias, la tercera
# tiene que no agregar nada: ese es el punto fijo. Correrla cuesta una pasada más
# y es la única forma de distinguir «la primera quedó corta» de «cada pasada
# encuentra algo nuevo», que serían dos diagnósticos opuestos con el mismo
# síntoma.
MARCA2=$(sql "SELECT coalesce(max(creado_en), now())::text FROM documento_versiones" 2>/dev/null || echo "")
# shellcheck disable=SC2086
cronometrar "tercera pasada (punto fijo)" bash scripts/poblar_corpus.sh --sin-informes --sin-ampliar ${EXTRA}
TRAS_TERCERA=$(sql "SELECT count(*) FROM documento_versiones" 2>/dev/null || echo "")
if [ -n "${MARCA2}" ]; then
  TERCERA_SOBRE_EXISTENTE=$(sql "SELECT count(*) FROM documento_versiones \
    WHERE creado_en > '${MARCA2}' AND version > 1" 2>/dev/null || echo "")
  TERCERA_PRIMERAS=$(sql "SELECT count(*) FROM documento_versiones \
    WHERE creado_en > '${MARCA2}' AND version = 1" 2>/dev/null || echo "")
fi

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
