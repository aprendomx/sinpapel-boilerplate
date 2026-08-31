#!/usr/bin/env bash
# Gate `rename`: el template sigue verde después de renombrarlo.
#
# Copia el repositorio a un directorio temporal, lo renombra y corre allí los
# gates. Es la única forma de comprobar que la parametrización no rompe nada:
# hacerlo sobre el repo real lo dejaría renombrado.
#
# Se ejecuta aparte de `make verify` porque monta un entorno completo desde
# cero (venv + node_modules) y tarda minutos. En CI corre como job propio.
set -euo pipefail

cd "$(dirname "$0")/../.."
ORIGEN="$(pwd)"

NOMBRE_PRUEBA="${RENAME_TEST_NAME:-demo-xyz}"
DESTINO="$(mktemp -d)"
trap 'rm -rf "$DESTINO"' EXIT

echo "→ copiando el repositorio a $DESTINO"
# Se copia lo que *se commitearía*: versionado más lo nuevo que no está
# ignorado. Usar `git archive HEAD` limitaría el gate al último commit, y en
# local se estaría comprobando una versión anterior del template sin avisar.
# Se filtran las rutas que ya no existen: el índice de git puede listar un
# archivo borrado pero todavía no commiteado, y tar abortaría por él.
git ls-files --cached --others --exclude-standard \
  | while IFS= read -r ruta; do [ -f "$ruta" ] && printf '%s\n' "$ruta"; done \
  | tar -T - -c -f - \
  | tar -x -C "$DESTINO"

cd "$DESTINO"
# Los scripts leen `git ls-files`, así que la copia necesita ser un repo.
git init -q -b main
git add -A
git -c user.email=gate@local -c user.name=gate commit -qm "copia para el gate rename"

echo "→ renombrando a '${NOMBRE_PRUEBA}'"
./ops/ci/rename.py "$NOMBRE_PRUEBA"

echo "→ comprobando que no quedó rastro de la identidad anterior"
residuo="$(
  git ls-files \
    | grep -v '^\.claude/skills/' \
    | xargs grep -lF -e 'sinpapel-boilerplate' -e 'sinpapel_boilerplate' 2>/dev/null || true
)"
if [ -n "$residuo" ]; then
  echo "✗ Quedaron referencias al nombre original en:" >&2
  echo "$residuo" | sed 's/^/    /' >&2
  exit 1
fi

echo "→ comprobando que el framework NO se renombró"
# Un reemplazo demasiado amplio se llevaría por delante el nombre del propio
# framework, y el proyecto dejaría de arrancar de formas difíciles de leer.
for esperado in 'from sinpapel import' 'SINPAPEL_SIGNATURE_BACKEND' 'sinpapel/api/'; do
  if ! git ls-files | xargs grep -qF "$esperado" 2>/dev/null; then
    echo "✗ Desapareció '$esperado': el rename tocó el nombre del framework." >&2
    exit 1
  fi
done

echo "→ instalando el proyecto renombrado"
make install >/dev/null

echo "→ corriendo los gates sobre la copia"
# La copia renombrada apunta por defecto a una base que no existe, así que se
# reutiliza la conexión de quien corre el gate: en CI viene del entorno, y en
# local del .env del repositorio original. Los tests crean su propia base
# `test_*`, de modo que no tocan los datos de desarrollo.
if [ -z "${DATABASE_URL:-}" ] && [ -f "$ORIGEN/.env" ]; then
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ORIGEN/.env" | tail -1 | cut -d= -f2-)"
fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "✗ Sin DATABASE_URL: el gate necesita una base alcanzable." >&2
  echo "  Expórtala, o crea un .env (make db la levanta)." >&2
  exit 1
fi
export DATABASE_URL

make lint migrations test parity roundtrip

echo
echo "✓ el template sigue verde tras renombrarse a '${NOMBRE_PRUEBA}'"
