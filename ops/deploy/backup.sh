#!/usr/bin/env bash
# Respaldo de la base de datos y del expediente documental.
#
# Un sistema de trámites custodia evidencia: la bitácora de transiciones y los
# registros de firma son append-only y no se pueden reconstruir, y los archivos
# subidos por las personas usuarias tampoco. Perderlos no es perder datos, es
# perder actos administrativos.
#
#   ./ops/deploy/backup.sh                    # respaldo completo
#   RETENCION_DIAS=30 ./ops/deploy/backup.sh  # ajusta la purga
set -euo pipefail

cd "$(dirname "$0")/../.."

COMPOSE="docker compose -f ops/deploy/docker-compose.prod.yml"
DESTINO="${BACKUP_DIR:-./backups}"
RETENCION_DIAS="${RETENCION_DIAS:-14}"
MARCA="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DESTINO"

echo "→ base de datos"
# `--format=custom` permite restaurar tablas sueltas y comprime de serie.
# Se escribe primero a un temporal: un respaldo truncado por un fallo a mitad
# es peor que no tenerlo, porque parece válido.
$COMPOSE exec -T db pg_dump \
  --username "${POSTGRES_USER:?falta POSTGRES_USER}" \
  --dbname "${POSTGRES_DB:?falta POSTGRES_DB}" \
  --format=custom \
  > "${DESTINO}/db-${MARCA}.dump.parcial"
mv "${DESTINO}/db-${MARCA}.dump.parcial" "${DESTINO}/db-${MARCA}.dump"
echo "  ${DESTINO}/db-${MARCA}.dump ($(du -h "${DESTINO}/db-${MARCA}.dump" | cut -f1))"

echo "→ expediente documental (media/)"
$COMPOSE run --rm --no-deps -T backend tar -cz -C /app media \
  > "${DESTINO}/media-${MARCA}.tar.gz.parcial"
mv "${DESTINO}/media-${MARCA}.tar.gz.parcial" "${DESTINO}/media-${MARCA}.tar.gz"
echo "  ${DESTINO}/media-${MARCA}.tar.gz ($(du -h "${DESTINO}/media-${MARCA}.tar.gz" | cut -f1))"

echo "→ purgando respaldos de más de ${RETENCION_DIAS} días"
find "$DESTINO" -name 'db-*.dump' -mtime "+${RETENCION_DIAS}" -print -delete
find "$DESTINO" -name 'media-*.tar.gz' -mtime "+${RETENCION_DIAS}" -print -delete

cat <<EOF

✓ respaldo ${MARCA} completo.

Un respaldo que nunca se ha restaurado es una hipótesis. Pruébalo:

  # base de datos, contra una base vacía
  $COMPOSE exec -T db pg_restore --username \$POSTGRES_USER \\
      --dbname <base_de_prueba> --clean --if-exists < ${DESTINO}/db-${MARCA}.dump

  # expediente
  tar -xz -C <destino> < ${DESTINO}/media-${MARCA}.tar.gz

Y llévatelos fuera de esta máquina: un respaldo en el mismo host no protege
del incidente que más lo destruye todo.
EOF
