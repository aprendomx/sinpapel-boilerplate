#!/usr/bin/env bash
#
# Humo del despliegue de producción.
#
# `ops/deploy/docker-compose.prod.yml` estaba documentado y nunca se levantaba,
# así que sus fallos aparecían en el peor sitio posible. El primero que encontró
# esta prueba: el healthcheck del backend pedía `http://127.0.0.1:8000/salud/`,
# `SECURE_SSL_REDIRECT` respondía 301 a https, urllib seguía la redirección y
# terminaba intentando TLS contra un gunicorn en texto plano. El contenedor
# quedaba unhealthy para siempre.
#
# No pretende ser un despliegue real: monta valores de mentira y un bundle de
# ACs falso. Comprueba que el stack arranca, migra, queda sano y conserva sus
# propiedades de producción.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$RAIZ/ops/deploy/docker-compose.prod.yml"
PUERTO="${SMOKE_BACKEND_PORT:-8010}"
TRABAJO="$(mktemp -d)"

# Nombre de proyecto propio: sin esto compartiría contenedores y volúmenes con
# el stack de desarrollo y `down -v` se llevaría por delante la base de trabajo.
PROYECTO="sinpapel-boilerplate-smoke"

compose() {
  docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$TRABAJO/.env.prod" "$@"
}

limpiar() {
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$TRABAJO"
}
trap limpiar EXIT

fallar() {
  printf '\033[31m✗ %s\033[0m\n' "$1"
  echo "--- logs del backend ---"
  compose logs --tail 40 backend 2>&1 || true
  exit 1
}

printf -- "-----BEGIN CERTIFICATE-----\nsmoke\n-----END CERTIFICATE-----\n" \
  > "$TRABAJO/ca.pem"

cat > "$TRABAJO/.env.prod" <<EOF
PROJECT_NAME=$PROYECTO
DJANGO_SECRET_KEY=humo-no-es-una-llave-real-solo-para-esta-prueba-xxxxxxxxxxxx
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost
POSTGRES_DB=smoke
POSTGRES_USER=smoke
POSTGRES_PASSWORD=smoke
DATABASE_URL=postgres://smoke:smoke@db:5432/smoke
FIEL_CA_BUNDLE=$TRABAJO/ca.pem
BACKEND_PORT=$PUERTO
SLA_INTERVALO_SEGUNDOS=3600
EOF

echo "→ las variables obligatorias fallan ruidosamente si faltan"
# El compose las declara con `:?`. Se comprueba de verdad, porque un `:?` mal
# escrito no se nota hasta que alguien despliega sin esa variable.
: > "$TRABAJO/.env.vacio"
if docker compose -p "${PROYECTO}-vacio" -f "$COMPOSE_FILE" \
  --env-file "$TRABAJO/.env.vacio" config >/dev/null 2>&1; then
  fallar "el compose acepta un entorno vacío: los guardias \`:?\` no protegen"
fi
echo "  ✓ sin entorno, el compose se niega a resolver"

echo "→ levantando el stack de producción"
compose up -d --build --wait --wait-timeout 300 \
  || fallar "el stack no llegó a estar sano"

echo "→ el backend responde detrás de un proxy TLS"
codigo="$(curl -s -o /dev/null -w '%{http_code}' \
  -H 'X-Forwarded-Proto: https' "http://localhost:$PUERTO/salud/")"
[ "$codigo" = "200" ] || fallar "/salud/ respondió $codigo, se esperaba 200"
echo "  ✓ 200"

echo "→ y exige TLS cuando no lo hay"
# Propiedad de producción, no un detalle: si esto deja de redirigir es que
# SECURE_SSL_REDIRECT se apagó y el tráfico viajaría en claro.
codigo="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PUERTO/salud/")"
[ "$codigo" = "301" ] || fallar "sin TLS respondió $codigo, se esperaba 301"
echo "  ✓ 301 a https"

echo "→ las migraciones corrieron bajo el settings de producción"
# Incluye la data migration que siembra el flujo desde spec/flujos/: si el
# arranque no migra, el sistema queda sin estados y nada de esto es utilizable.
estados="$(compose exec -T backend python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()
from sinpapel.models import Estado
print(Estado.objects.count())
" 2>/dev/null | tr -d '\r\n ')"
[ "${estados:-0}" -ge 5 ] || fallar "solo hay ${estados:-0} estados sembrados, se esperaban 5"
echo "  ✓ $estados estados"

echo "→ el worker de webhooks y el cron de SLA siguen en pie"
# Sin el worker las entregas se acumulan en `pending` para siempre, y sin el
# cron ninguna solicitud vence nunca. Que arranquen y no mueran es lo mínimo.
for servicio in webhooks sla; do
  estado="$(compose ps --format '{{.State}}' "$servicio")"
  [ "$estado" = "running" ] || fallar "el servicio $servicio está en '$estado'"
done
echo "  ✓ webhooks y sla en marcha"

printf '\033[32m✓ humo del despliegue en verde\033[0m\n'
