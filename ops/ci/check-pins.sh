#!/usr/bin/env bash
# Gate `audit`: verifica que los pines del ecosistema sinpapel sigan intactos.
#
# El template está verificado contra un conjunto exacto de versiones. Un bump
# accidental (o un `uv pip install` que resuelva otra cosa) rompe supuestos que
# los tests no siempre cubren, así que se comprueba tanto lo declarado en
# pyproject.toml/package.json como lo instalado en el venv.
set -euo pipefail

cd "$(dirname "$0")/../.."

fallos=0

esperado_py=(
  'sinpapel~=0.8.4'
  'sinpapel-drf~=0.4.6'
  'sinpapel-webhooks~=0.2.4'
  'sinpapel-reports~=0.2.4'
  'Django>=5.2,<6.0'
)

echo "→ pines declarados en backend/pyproject.toml"
for pin in "${esperado_py[@]}"; do
  if grep -qF "\"${pin}\"" backend/pyproject.toml; then
    echo "  ✓ ${pin}"
  else
    echo "  ✗ falta o cambió: ${pin}"
    fallos=$((fallos + 1))
  fi
done

echo "→ pin declarado en frontend/package.json"
if grep -q '"@aprendomx/sinpapel-vue": "\^0\.4\.' frontend/package.json; then
  echo "  ✓ @aprendomx/sinpapel-vue ^0.4.x"
else
  echo "  ✗ @aprendomx/sinpapel-vue ausente o fuera del rango ^0.4.x"
  fallos=$((fallos + 1))
fi

echo "→ versión realmente instalada en frontend/node_modules"
instalada_vue="$(node -p "require('./frontend/node_modules/@aprendomx/sinpapel-vue/package.json').version" 2>/dev/null || echo "")"
case "$instalada_vue" in
  0.4.*) echo "  ✓ @aprendomx/sinpapel-vue ${instalada_vue}" ;;
  "")    echo "  ✗ @aprendomx/sinpapel-vue no está instalado; corre 'make install'"
         fallos=$((fallos + 1)) ;;
  *)     echo "  ✗ @aprendomx/sinpapel-vue ${instalada_vue} — se esperaba la serie 0.4.x"
         fallos=$((fallos + 1)) ;;
esac

echo "→ pin de sinpapel-designer"
# El designer no es una dependencia declarada: se clona de un tag y se
# construye. El pin vive en el script de build, así que sin comprobarlo aquí un
# cambio de tag pasaría inadvertido — y lo que se sirve bajo /designer/ dejaría
# de ser la versión verificada.
DESIGNER_ESPERADO="v0.1.0"
if grep -qF "SINPAPEL_DESIGNER_REF:-${DESIGNER_ESPERADO}" ops/ci/build-designer.sh; then
  echo "  ✓ sinpapel-designer ${DESIGNER_ESPERADO}"
else
  echo "  ✗ ops/ci/build-designer.sh no pinea ${DESIGNER_ESPERADO}"
  fallos=$((fallos + 1))
fi

# Si alguien ya lo construyó, el bundle tiene que ser de ese mismo tag: un
# `make designer` con SINPAPEL_DESIGNER_REF apuntando a otra cosa deja servido
# algo distinto de lo declarado.
if [ -f designer/DESIGNER_VERSION ]; then
  ref_construida="$(grep -E '^source_ref=' designer/DESIGNER_VERSION | cut -d= -f2-)"
  if [ "$ref_construida" = "$DESIGNER_ESPERADO" ]; then
    echo "  ✓ bundle construido desde ${ref_construida}"
  else
    echo "  ✗ el bundle es de '${ref_construida}', no de ${DESIGNER_ESPERADO}"
    echo "    Reconstruye con: make designer"
    fallos=$((fallos + 1))
  fi
else
  echo "  · sin construir (make designer)"
fi

echo "→ versiones realmente instaladas en backend/.venv"
if [ -x backend/.venv/bin/python ]; then
  backend/.venv/bin/python - <<'PY' || fallos=$((fallos + 1))
import sys
from importlib.metadata import PackageNotFoundError, version

# (paquete, major.minor exigido)
esperado = {
    "sinpapel": "0.8",
    "sinpapel-drf": "0.4",
    "sinpapel-webhooks": "0.2",
    "sinpapel-reports": "0.2",
    "Django": "5.2",
}
fallos = 0
for paquete, serie in esperado.items():
    try:
        instalada = version(paquete)
    except PackageNotFoundError:
        print(f"  ✗ {paquete} no está instalado")
        fallos += 1
        continue
    if instalada.startswith(f"{serie}."):
        print(f"  ✓ {paquete} {instalada}")
    else:
        print(f"  ✗ {paquete} {instalada} — se esperaba la serie {serie}.x")
        fallos += 1
sys.exit(1 if fallos else 0)
PY
else
  echo "  ✗ backend/.venv no existe; corre 'make install'"
  fallos=$((fallos + 1))
fi

if [ "$fallos" -gt 0 ]; then
  echo
  echo "✗ ${fallos} problema(s) con los pines. Si el cambio es intencional,"
  echo "  actualiza backend/pyproject.toml, este script y spec/decisiones/."
  exit 1
fi

echo "✓ pines intactos"
