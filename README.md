# sinpapel-boilerplate

Template ejecutable para construir sistemas de trámites sobre el framework
[sinpapel](https://github.com/aprendomx/sinpapel): workflow versionado,
auditoría inmutable, firma electrónica, predicados, SLAs y captura de
metadatos, con backend Django/DRF y frontend Vue 3 + Quasar.

No es un cookiecutter. No hay `{{ variables }}` en el código: el repo compila y
pasa sus tests tal cual se clona, y la parametrización ocurre con
`make rename NAME=<slug>`.

## Requisitos

- Python 3.12
- Node 22
- Docker con Compose v2
- [uv](https://docs.astral.sh/uv/) para gestionar el entorno de Python

## Arranque

```bash
cp .env.example .env    # ajusta POSTGRES_PORT si ya tienes un PostgreSQL local
make install            # venv del backend + npm ci del frontend
make up                 # db + backend + frontend
```

- Backend: <http://localhost:8000/salud/>
- Frontend: <http://localhost:5173>
- Admin: <http://localhost:8000/admin/>

Para trabajar sin levantar todo el stack basta la base de datos:

```bash
make db
make verify
```

## Gates

`make verify` es la única puerta del proyecto: ningún trabajo se considera
terminado sin que pase entera. Cada gate es una verificación real.

| Gate | Qué comprueba |
|---|---|
| `lint` | `ruff check` + `ruff format --check` en el backend, `eslint` en el frontend |
| `migrations` | `makemigrations --check --dry-run` limpio: no hay migraciones sin generar |
| `test` | `pytest` (backend) y `vitest` (frontend) |
| `audit` | `pip-audit`, `npm audit` y la integridad de los pines del ecosistema |

Los gates crecen con el proyecto: un target aparece en el Makefile cuando lo
que verifica existe. No hay objetivos decorativos que pasen sin comprobar nada.

## Estructura

```
├── .claude/skills/     Skills de sinpapel vendorizadas (make skills-sync)
├── spec/
│   ├── sistema.yaml    Identidad del sistema
│   ├── flujos/         Verdad de los flujos, en JSON v0.2
│   └── decisiones/     ADRs
├── backend/
│   ├── config/         settings (base/dev/prod/test), urls, wsgi, asgi
│   ├── apps/cuentas/   Usuario del sistema
│   └── tests/
├── frontend/           Vue 3 + Quasar + Vite + Pinia
├── e2e/                Playwright
└── ops/{docker,ci,deploy}/
```

## Versiones del ecosistema

Pineadas y verificadas. El gate `audit` falla si cambian sin actualizar
`ops/ci/check-pins.sh` y `spec/decisiones/`.

```
sinpapel~=0.8.3          Django>=5.2,<6.0
sinpapel-drf~=0.4.5      Python 3.12
sinpapel-webhooks~=0.2.4
sinpapel-reports~=0.2.4
```

`sinpapel>=0.8.3` no es opcional: las versiones anteriores son incompatibles
con un `AUTH_USER_MODEL` propio (ver
[ADR-0001](spec/decisiones/0001-usuario-custom-desde-el-esqueleto.md)).

## Base de datos

El contenedor corre PostgreSQL 16 con PostGIS, pero el engine de Django es el
de PostgreSQL a secas: `django.contrib.gis` exige GDAL y GEOS en cada máquina
y todavía no hay modelos con geometría. Ver
[ADR-0002](spec/decisiones/0002-engine-postgresql-con-imagen-postgis.md).

## Para agentes

Lee [CLAUDE.md](CLAUDE.md) antes de tocar código: reglas duras del repo y
trampas verificadas del framework. Las 20 skills de `sinpapel` están
vendorizadas en `.claude/skills/`; el commit de origen queda en
`.claude/SKILLS_VERSION` y se actualizan con `make skills-sync`.

## Licencia

GPL-3.0-or-later, igual que `sinpapel`.
