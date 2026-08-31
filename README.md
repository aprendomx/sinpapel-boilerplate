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

`parity` es el que impide la deriva: los flujos son datos, y su verdad vive en
`spec/flujos/`. Si alguien añade una transición por el admin, toca la migración
de siembra o edita el JSON sin volver a sembrar, el sistema en ejecución deja
de ser el declarado en el repositorio y nada más lo detectaría.

| Gate | Qué comprueba |
|---|---|
| `lint` | `ruff check` + `ruff format --check` en el backend, `eslint` en el frontend |
| `migrations` | `makemigrations --check --dry-run` limpio: no hay migraciones sin generar |
| `test` | `pytest` (backend) y `vitest` (frontend) |
| `parity` | La base de datos coincide exactamente con `spec/flujos/*.json` |
| `roundtrip` | Export → import de cada flujo no pierde ningún campo |
| `api-roles` | Cada endpoint expuesto responde 200/403 según el rol, para los cinco roles |
| `coverage` | Cobertura mínima del 85 % en `apps/tramite_ejemplo` |
| `audit` | `pip-audit`, `npm audit` y la integridad de los pines del ecosistema |

Dos gates corren aparte porque tardan minutos:

| Gate | Cómo |
|---|---|
| `e2e` | `make up && make seed && make e2e` — el trámite completo por la UI real |
| `rename` | `make rename-check` — copia el repo, lo renombra y exige que siga verde |

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
│   ├── config/                settings (base/dev/prod/test), urls, wsgi, asgi
│   ├── apps/core/             validadores y folios compartidos
│   ├── apps/cuentas/          usuario, dependencias, adscripciones, roles
│   ├── apps/tramite_ejemplo/  LA slice canónica
│   ├── apps/spec_io/          import/export de flujos para el designer
│   └── tests/{unit,api,parity}/
├── frontend/           Vue 3 + Quasar + Vite + Pinia + @aprendomx/sinpapel-vue
├── designer/           sinpapel-designer embebido (make designer)
├── e2e/                Playwright (trámite completo)
└── ops/{docker,ci,deploy}/
```

## Versiones del ecosistema

Pineadas y verificadas. El gate `audit` falla si cambian sin actualizar
`ops/ci/check-pins.sh` y `spec/decisiones/`.

```
sinpapel~=0.8.4          Django>=5.2,<6.0
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
