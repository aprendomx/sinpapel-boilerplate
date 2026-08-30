#!/usr/bin/env bash
# Construye sinpapel-designer y deja el bundle en designer/dist/spa/.
#
# El designer es una SPA standalone (Vue 3 + Quasar + Vue Flow): no es un
# paquete de Django ni se instala con pip. Su código fuente no se versiona aquí
# —se clona del repo canónico en el tag pineado— y su salida tampoco: es un
# artefacto de build, y el .gitignore lo excluye.
set -euo pipefail

cd "$(dirname "$0")/../.."

REPO="${SINPAPEL_DESIGNER_REPO:-https://github.com/aprendomx/sinpapel-designer}"
REF="${SINPAPEL_DESIGNER_REF:-v0.1.0}"
DESTINO="designer/dist"
# Debe coincidir con el prefijo donde config/urls.py monta apps.spec_io.urls.
PUBLIC_PATH="${SINPAPEL_DESIGNER_PUBLIC_PATH:-/designer/}"

CLONE="$(mktemp -d)"
trap 'rm -rf "$CLONE"' EXIT

echo "→ clonando ${REPO} (${REF})"
git clone --quiet --depth 1 --branch "$REF" "$REPO" "$CLONE"

# El designer está pensado como SPA standalone y construye con publicPath "/".
# Aquí se embebe bajo /designer/, así que sin ajustarlo el index pide sus
# assets a la raíz del dominio y la página sale en blanco (200 en el HTML,
# 404 en cada bundle). Se parchea la config del clon, no el repo upstream.
echo "→ fijando publicPath a ${PUBLIC_PATH}"
python3 - "$CLONE/quasar.config.js" "$PUBLIC_PATH" <<'PY'
import pathlib
import sys

ruta, publico = pathlib.Path(sys.argv[1]), sys.argv[2]
contenido = ruta.read_text(encoding="utf-8")

ancla = "  build: {"
if ancla not in contenido:
    sys.exit(
        "No se encontró el bloque `build:` en quasar.config.js; "
        "sinpapel-designer cambió su configuración."
    )
contenido = contenido.replace(ancla, f"{ancla}\n    publicPath: '{publico}',", 1)
ruta.write_text(contenido, encoding="utf-8")
PY

echo "→ instalando dependencias"
(cd "$CLONE" && npm ci --silent)

echo "→ construyendo"
(cd "$CLONE" && npm run build)

# Quasar publica en dist/spa; se comprueba en vez de asumirlo, para que un
# cambio de layout del proyecto upstream falle aquí y no al servir la ruta.
origen="$CLONE/dist/spa"
if [ ! -f "$origen/index.html" ]; then
  echo "✗ El build no produjo ${origen}/index.html." >&2
  echo "  Revisa si sinpapel-designer cambió su directorio de salida." >&2
  exit 1
fi

# Un index que pida sus assets a la raíz se sirve con 200 y se ve en blanco:
# el fallo es silencioso, así que se comprueba aquí.
if grep -qE '(src|href)="/assets/' "$origen/index.html"; then
  echo "✗ El bundle referencia /assets/ en vez de ${PUBLIC_PATH}assets/." >&2
  echo "  El publicPath no se aplicó; la página se serviría en blanco." >&2
  exit 1
fi

rm -rf "$DESTINO"
mkdir -p "$DESTINO"
cp -R "$origen" "$DESTINO/"

commit="$(git -C "$CLONE" rev-parse HEAD)"
cat > designer/DESIGNER_VERSION <<EOF
# Bundle construido por: make designer  (NO editar; no se versiona)
source_repo=${REPO}
source_ref=${REF}
source_commit=${commit}
EOF

echo "✓ designer construido en ${DESTINO}/spa (${REF}, ${commit:0:7})"
