#!/usr/bin/env bash
# Regenera .claude/skills/ desde el repo canónico de skills.
#
# .claude/skills/ es contenido vendorizado: NUNCA se edita a mano. Los cambios
# van a aprendomx/sinpapel-skills (fuente en skills/<nombre>/SKILL.md), se
# regeneran con build_skills.py y se traen aquí con este script.
set -euo pipefail

cd "$(dirname "$0")/../.."

REPO="${SINPAPEL_SKILLS_REPO:-https://github.com/aprendomx/sinpapel-skills}"
REF="${SINPAPEL_SKILLS_REF:-main}"
CLONE="$(mktemp -d)"
trap 'rm -rf "$CLONE"' EXIT

echo "→ clonando ${REPO} (${REF})"
git clone --quiet --depth 1 --branch "$REF" "$REPO" "$CLONE"

commit="$(git -C "$CLONE" rev-parse HEAD)"
fecha="$(git -C "$CLONE" log -1 --format=%cI)"
origen="$CLONE/dist/claude/skills"

if [ ! -d "$origen" ]; then
  echo "✗ el repo de skills no trae dist/claude/skills; ¿falta correr build_skills.py?" >&2
  exit 1
fi

total="$(find "$origen" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
if [ "$total" -eq 0 ]; then
  echo "✗ dist/claude/skills está vacío" >&2
  exit 1
fi

echo "→ reemplazando .claude/skills/ (${total} skills)"
rm -rf .claude/skills
mkdir -p .claude/skills
cp -R "$origen"/* .claude/skills/

cat > .claude/SKILLS_VERSION <<EOF
# Skills vendorizadas desde aprendomx/sinpapel-skills
# Regenerar con: make skills-sync  (NUNCA editar .claude/skills/ a mano)
source_repo=${REPO}
source_commit=${commit}
source_commit_date=${fecha}
source_path=dist/claude/skills
skills_count=${total}
EOF

echo "✓ ${total} skills sincronizadas desde ${commit:0:7}"
