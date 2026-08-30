# AGENTS.md

Este repositorio dirige a los agentes desde **[CLAUDE.md](CLAUDE.md)**. Léelo
completo antes de tocar código: contiene las reglas duras del proyecto y las
trampas verificadas del framework `sinpapel`.

Resumen de lo que más se rompe:

- La verdad de los flujos vive en `spec/flujos/*.json`, no en código.
- `.claude/skills/` es contenido vendorizado: se regenera con `make skills-sync`.
- `WorkflowService` no existe; el motor es `WorkflowEngine`.
- Ningún trabajo termina sin `make verify` en verde.
- Verifica cada API contra `site-packages/sinpapel*` antes de usarla.

Las skills del framework están en `.claude/skills/` (formato Agent Skills, 20
skills). Si tu herramienta no las carga sola, empieza por
`.claude/skills/sinpapel-overview/SKILL.md`, que enruta al resto.
