#!/usr/bin/env bash
# Regenera .claude/skills/ y .claude/commands/ desde el repo canónico.
#
# Ambos son contenido vendorizado: NUNCA se editan a mano. Los cambios van a
# aprendomx/sinpapel-skills —las skills en skills/<nombre>/SKILL.md, los slash
# commands en commands/<espacio>/<nombre>.md—, se regeneran con build_skills.py
# y se traen aquí con este script.
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
origen_comandos="$CLONE/dist/claude/commands"

if [ ! -d "$origen" ]; then
  echo "✗ el repo de skills no trae dist/claude/skills; ¿falta correr build_skills.py?" >&2
  exit 1
fi

total="$(find "$origen" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
if [ "$total" -eq 0 ]; then
  echo "✗ dist/claude/skills está vacío" >&2
  exit 1
fi

if [ ! -d "$origen_comandos" ]; then
  echo "✗ el repo de skills no trae dist/claude/commands; ¿versión anterior a 7639bd7?" >&2
  exit 1
fi

comandos="$(find "$origen_comandos" -type f -name '*.md' | wc -l | tr -d ' ')"
if [ "$comandos" -eq 0 ]; then
  echo "✗ dist/claude/commands está vacío" >&2
  exit 1
fi

echo "→ reemplazando .claude/skills/ (${total} skills)"
rm -rf .claude/skills
mkdir -p .claude/skills
cp -R "$origen"/* .claude/skills/

echo "→ reemplazando .claude/commands/ (${comandos} comandos)"
rm -rf .claude/commands
mkdir -p .claude/commands
cp -R "$origen_comandos"/* .claude/commands/

cat > .claude/SKILLS_VERSION <<EOF
# Skills y comandos vendorizados desde aprendomx/sinpapel-skills
# Regenerar con: make skills-sync
# NUNCA editar .claude/skills/ ni .claude/commands/ a mano
source_repo=${REPO}
source_commit=${commit}
source_commit_date=${fecha}
source_path=dist/claude
skills_count=${total}
commands_count=${comandos}
EOF

echo "✓ ${total} skills y ${comandos} comandos sincronizados desde ${commit:0:7}"
