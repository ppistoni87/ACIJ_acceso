#!/usr/bin/env bash
# Corre el ciclo completo sobre las fuentes normativas del alcance inicial.
#
# Es idempotente: reejecutarlo revalida las capturas, no duplica versiones y
# solo reprocesa lo que cambió. Sirve tanto para poblar desde cero como para
# actualizar.
set -euo pipefail
cd "$(dirname "$0")/.."

BN=.venv/bin/bn

# Normas del alcance inicial: las seis relacionadas del anexo, la ficha HTML del
# decreto CABA 690/2006 y la Ley de Asignaciones Familiares.
NORMATIVAS=(D01 D02 D03 D04 D05 D06 D10 F33)

echo "== Catálogo =="
$BN catalogo cargar

echo
echo "== Captura =="
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

echo
echo "== Identidad normativa =="
$BN curacion identidad

echo
echo "== Relaciones normativas =="
$BN curacion relaciones

echo
echo "== Conciliación =="
$BN catalogo conciliar --salida docs/reportes/conciliacion_inventario.md
