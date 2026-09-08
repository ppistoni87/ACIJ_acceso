#!/usr/bin/env bash
# El ciclo completo de población, de punta a punta.
#
# Es la única definición del procedimiento: `scripts/corrida_limpia.sh` lo llama
# sobre una base que se crea vacía, y acá se corre sobre la base de desarrollo.
# Tener dos listas de pasos garantiza que una de las dos quede vieja.
#
# Es idempotente: reejecutarlo revalida las capturas, no duplica versiones y solo
# reprocesa lo que cambió. Sirve tanto para poblar desde cero como para
# actualizar.
#
# Uso: bash scripts/poblar_corpus.sh [--sin-catalogo-nacional] [--sin-informes]
set -euo pipefail
cd "$(dirname "$0")/.."

BN=.venv/bin/bn
CATALOGO_NACIONAL=1
INFORMES=1
for opcion in "$@"; do
  case "${opcion}" in
    --sin-catalogo-nacional) CATALOGO_NACIONAL=0 ;;
    --sin-informes) INFORMES=0 ;;
    *) echo "Opción desconocida: ${opcion}" >&2; exit 2 ;;
  esac
done

# La última captura de una fuente, que es sobre la que trabajan los importadores.
# Trabajan sobre bytes ya guardados, nunca sobre la red: leen el objeto por su
# SHA-256, así que correrlos de nuevo no vuelve a pedirle nada a nadie.
ultima_captura() {
  psql -h 127.0.0.1 -U postgres -d "${1}" -tAc \
    "SELECT c.id FROM capturas c JOIN fuente_urls fu ON fu.id = c.source_url_id
      WHERE fu.source_id = '${2}' ORDER BY c.capturado_en DESC LIMIT 1"
}

BASE=$(python3 - <<'PY'
import os, urllib.parse
url = os.environ.get("BN_DATABASE_URL", "")
print(urllib.parse.urlparse(url).path.lstrip("/") or "backend_normativo")
PY
)
export PGPASSWORD="${PGPASSWORD:-postgres}"

# Normas del alcance inicial: las seis relacionadas del anexo, la ficha HTML del
# decreto CABA 690/2006 y la Ley de Asignaciones Familiares.
NORMATIVAS=(D01 D02 D03 D04 D05 D06 D10 F33)

echo "== Catálogo =="
$BN catalogo validar >/dev/null
$BN catalogo cargar

echo
echo "== Captura del alcance inicial =="
$BN ingesta capturar "${NORMATIVAS[@]}"

echo
echo "== Extracción =="
$BN ingesta extraer

echo
echo "== Descubrimiento de vistas de texto =="
for fuente in "${NORMATIVAS[@]}"; do
  $BN ingesta descubrir "$fuente" >/dev/null
done

echo
echo "== Captura y extracción de los textos descubiertos =="
$BN ingesta capturar "${NORMATIVAS[@]}"
$BN ingesta extraer

# El resto del catálogo lo recorre el mismo planificador que corre en
# producción, no una lista escrita a mano: así se prueba la regla que decide a
# quién le toca, y las fuentes que la política no habilita a automatizar quedan
# afuera solas.
echo
echo "== Resto de las fuentes, por el planificador =="
$BN monitoreo ciclo | sed -n '1,8p'

echo
echo "== Identidad normativa =="
$BN curacion identidad

echo
echo "== Relaciones normativas =="
$BN curacion relaciones


echo
echo "== Trámites =="
$BN curacion tramites

# Anexos y equivalencias trabajan norma por norma, no de corrido: la primera
# busca remisiones en el cuerpo de una norma que aprueba anexos, la segunda
# compara dos versiones del texto de la misma norma. Las normas se sacan de la
# base —las que tienen texto extraído— en vez de escribirlas a mano: una lista
# fija se queda corta en cuanto entra una norma nueva al corpus.
echo
echo "== Anexos y equivalencias =="
NORMAS_CON_TEXTO=$(psql -h 127.0.0.1 -U postgres -d "${BASE}" -tAc \
  "SELECT DISTINCT n.id FROM normas n JOIN norma_versiones nv ON nv.norma_id = n.id")
for norma in ${NORMAS_CON_TEXTO}; do
  # Solo se informa la norma que remite a un anexo: una línea «0 remisiones» por
  # cada norma del corpus tapa la única que sí importa.
  $BN curacion anexos "${norma}" 2>/dev/null | grep -E 'Remisiones a anexo: [1-9]' || true
done
NORMAS_CON_DOS_VERSIONES=$(psql -h 127.0.0.1 -U postgres -d "${BASE}" -tAc \
  "SELECT n.id FROM normas n JOIN norma_versiones nv ON nv.norma_id = n.id
    GROUP BY n.id HAVING count(DISTINCT nv.registro_version_id) > 1")
for norma in ${NORMAS_CON_DOS_VERSIONES}; do
  $BN curacion equivalencias "${norma}" 2>/dev/null | tail -3 || true
done

echo
echo "== Directorios de atención =="
for fuente in F20 F60; do
  captura=$(ultima_captura "${BASE}" "${fuente}")
  if [ -n "${captura}" ]; then
    echo "-- ${fuente}"
    $BN ingesta importar-directorio "${captura}" | tail -3
  fi
done
captura=$(ultima_captura "${BASE}" F44)
if [ -n "${captura}" ]; then
  echo "-- F44 (Defensoría del Pueblo de la Nación)"
  $BN ingesta importar-dpn "${captura}" | tail -3
fi
# El padrón no viaja en el HTML de la página: se lee de una planilla publicada
# cuyo identificador declara el script de la propia página. Descubrirla, pedirla
# y recién después importarla. El importador trabaja sobre la planilla, no sobre
# la página, así que se elige la captura por su tipo y no por ser la más nueva.
captura=$(ultima_captura "${BASE}" F39)
if [ -n "${captura}" ]; then
  echo "-- F39 (RENABAP)"
  $BN ingesta descubrir-renabap "${captura}" | tail -2 || true
  $BN ingesta capturar F39 | tail -1
  planilla=$(psql -h 127.0.0.1 -U postgres -d "${BASE}" -tAc \
    "SELECT c.id FROM capturas c JOIN fuente_urls fu ON fu.id = c.source_url_id
      WHERE fu.source_id = 'F39' AND fu.url LIKE '%out:csv%'
      ORDER BY c.capturado_en DESC LIMIT 1")
  if [ -n "${planilla}" ]; then
    $BN ingesta importar-renabap "${planilla}" | tail -3
  else
    echo "F39: la planilla no se pudo capturar; el padrón queda sin importar." >&2
  fi
fi

if [ "${CATALOGO_NACIONAL}" = 1 ]; then
  echo
  echo "== Catálogo nacional (F01), como metadatos =="
  captura=$(ultima_captura "${BASE}" F01)
  if [ -n "${captura}" ]; then
    $BN ingesta importar-infoleg "${captura}" | tail -4
  else
    echo "F01 no tiene captura: se omite." >&2
  fi
fi

echo
echo "== Calendario de feriados =="
$BN plazos calendario "$(date +%Y)" | tail -2

echo
echo "== Beneficios curados =="
$BN curacion beneficios | grep -E '^(Beneficio|Poblaciones|Cuantías|Campos)' || true

# Los siete campos se evalúan al final, después de la curación: varios de ellos
# —población destinataria, criterios, beneficio otorgado— salen de la lectura
# curada del beneficio. Evaluarlos antes los deja en PENDIENTE y esconde el
# trabajo que sí está hecho.
echo
echo "== Siete campos =="
$BN curacion campos

echo
echo "== Vigencia =="
$BN curacion vigencia | tail -3

if [ "${INFORMES}" = 1 ]; then
  echo
  echo "== Informes =="
  $BN catalogo conciliar --salida docs/reportes/conciliacion_inventario.md
  $BN calidad cobertura --salida docs/reportes/cobertura.md
fi
