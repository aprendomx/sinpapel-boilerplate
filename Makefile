# Makefile del template. Los targets se añaden en la fase que los hace reales:
# nada de objetivos decorativos que "pasan" sin verificar nada.
# `--env-file` es explícito a propósito: compose busca el .env junto al archivo
# de compose (ops/docker/), no en la raíz del repo, y sin esto los overrides de
# puerto del .env se ignoran en silencio.
COMPOSE := docker compose --env-file .env -f ops/docker/docker-compose.yml
PIP     := uv pip install --python backend/.venv

.DEFAULT_GOAL := help
.PHONY: help install up down db seed logs verify lint test migrations parity \
        roundtrip api-roles coverage audit e2e rename rename-check \
        designer skills-sync clean

help: ## Muestra esta ayuda
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Crea el venv del backend e instala dependencias (backend + frontend)
	uv venv --python 3.12 backend/.venv
	$(PIP) -e "backend[dev]"
	cd frontend && npm ci

up: .env ## Levanta el stack completo (db + backend + frontend)
	# --build no es opcional: sin él, compose reutiliza la imagen existente y
	# los cambios en el Dockerfile o en las dependencias no llegan nunca al
	# contenedor. Con la caché de capas cuesta segundos.
	$(COMPOSE) up -d --build --wait
	@echo "backend  http://localhost:8000/salud/"
	@echo "frontend http://localhost:5173"

# El .env se crea solo si falta. `git clone && make up` tiene que funcionar:
# es la promesa del template, y hasta ahora el primer comando moría con el
# "couldn't find env file" de docker, que no dice qué hacer. No se sobrescribe
# uno existente, y no toca producción: ese despliegue usa su propio .env.prod
# explícito (ops/deploy/) y falla si le falta cualquier variable.
.env:
	@cp .env.example $@
	@printf '\033[33m→ .env creado desde .env.example (valores de desarrollo)\033[0m\n'

down: .env ## Detiene el stack y conserva los volúmenes
	$(COMPOSE) down

db: .env ## Levanta solo la base de datos (suficiente para `make verify`)
	$(COMPOSE) up -d --wait db

logs: .env ## Sigue los logs del stack
	$(COMPOSE) logs -f

# ─── Gates ───────────────────────────────────────────────────────────────────
# `verify` es la única puerta: ningún trabajo se considera terminado sin que
# pase entera. Cada gate es un check real, no un eco.

verify: lint migrations test parity roundtrip api-roles coverage audit ## Corre todos los gates
	@printf '\033[32m✓ make verify en verde\033[0m\n'

lint: ## ruff (backend) + eslint (frontend)
	backend/.venv/bin/ruff check backend
	backend/.venv/bin/ruff format --check backend
	cd frontend && npm run lint

migrations: ## Verifica que no haya migraciones sin generar
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.test \
		.venv/bin/python manage.py makemigrations --check --dry-run

test: ## Suite de tests (backend + frontend)
	cd backend && .venv/bin/python -m pytest
	cd frontend && npm run test

parity: ## La base coincide exactamente con spec/flujos/*.json
	cd backend && .venv/bin/python -m pytest tests/parity/test_parity.py \
		tests/parity/test_deteccion_deriva.py -q

roundtrip: ## Export -> import de cada flujo no pierde ningún campo
	cd backend && .venv/bin/python -m pytest tests/parity/test_roundtrip.py -q

api-roles: ## Cada endpoint responde 200/403 según el rol, para los cinco roles
	cd backend && .venv/bin/python -m pytest tests/api -q

coverage: ## Cobertura mínima del 85 % en la slice canónica
	cd backend && .venv/bin/python -m pytest -q \
		--cov=apps.tramite_ejemplo --cov-report=term-missing --cov-fail-under=85

audit: ## Vulnerabilidades conocidas + integridad de los pines del ecosistema
	# --skip-editable omite el propio backend, que se instala en modo editable
	# y no existe en PyPI; sus dependencias sí se auditan. No lleva --strict
	# porque ese flag falla precisamente por lo que --skip-editable omite; una
	# vulnerabilidad real sigue devolviendo código distinto de cero.
	backend/.venv/bin/pip-audit --skip-editable
	cd frontend && npm audit --audit-level=high
	./ops/ci/check-pins.sh

# ─── Utilidades ──────────────────────────────────────────────────────────────

seed: .env ## Datos de demostración: una dependencia y una cuenta por rol
	$(COMPOSE) exec backend python manage.py seed_demo

e2e: ## Playwright: el trámite completo, de captura a resolución firmada
	cd e2e && npm run test

rename: ## Renombra el proyecto: make rename NAME=<slug>
	./ops/ci/rename.py "$(NAME)"

rename-check: ## Gate `rename`: copia el repo, lo renombra y exige que siga verde
	./ops/ci/check-rename.sh

designer: ## Construye sinpapel-designer en designer/dist/spa/
	./ops/ci/build-designer.sh
	@echo "Disponible en http://localhost:8000/designer/ (requiere staff)"

skills-sync: ## Regenera .claude/skills/ desde aprendomx/sinpapel-skills
	./ops/ci/skills-sync.sh

clean: ## Borra artefactos de build y caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/htmlcov backend/.coverage
	rm -rf frontend/dist frontend/node_modules/.vite
	rm -rf designer/dist designer/DESIGNER_VERSION
