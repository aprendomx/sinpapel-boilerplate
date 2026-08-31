# sinpapel-boilerplate

Template ejecutable para construir sistemas de trámites sobre el framework
[sinpapel](https://github.com/aprendomx/sinpapel): workflow versionado,
auditoría inmutable, firma electrónica, predicados, SLAs y captura de
metadatos, con backend Django/DRF y frontend Vue 3 + Quasar.

**No es un cookiecutter.** No hay `{{ variables }}` en el código: el repositorio
se clona, se levanta y pasa sus propios gates tal cual. La parametrización
ocurre después, con `make rename`
([ADR-0006](spec/decisiones/0006-template-ejecutable-no-cookiecutter.md)).

Trae un trámite completo y funcionando —**Solicitud de Constancia**— que
ejercita todo el stack: predicados, firma exigible, side effects, SLA,
metadatos, requisitos documentales, webhooks y generación de documentos. No es
documentación: es código con sus tests y su cobertura. Un trámite nuevo se crea
copiándolo, no reconstruyéndolo.

## Cómo se usa

El template está pensado para trabajar con un agente de IA. Tres pasos:

```
/sinpapel:especificar   Descripción en lenguaje natural → spec/
/sinpapel:generar       spec/ → la app del trámite
/sinpapel:verificar     Corre los gates e interpreta lo que falle
```

El primero **no escribe código**: traduce lo que quieres a
`spec/flujos/<tramite>.json`, que es la fuente de verdad del flujo, y te lo
enseña en prosa para que lo apruebes. El segundo copia la slice canónica y la
adapta. El tercero verifica.

Los tres viven en `.claude/commands/sinpapel/` y puedes leerlos: son
instrucciones, no magia.

A mano, el camino es el mismo:

1. Edita `spec/flujos/<tramite>.json`, con el designer (`make designer`) o
   directamente.
2. Copia `apps/tramite_ejemplo/` completa y adáptala.
3. Siembra el flujo con una data migration que lea el JSON.
4. `make verify`.

## Arranque

Requisitos: Python 3.12, Node 22, Docker con Compose v2 y
[uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env    # ajusta POSTGRES_PORT si ya tienes un PostgreSQL local
make install            # venv del backend + npm ci del frontend
make up                 # db + backend + frontend
make seed               # una dependencia y una cuenta por rol
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000/salud/>
- Admin: <http://localhost:8000/admin/>
- Designer: <http://localhost:8000/designer/> (requiere `make designer` antes)

Las cuentas de `make seed` son `ana` (solicitante), `beto` (ventanilla),
`carla` (revisora), `diana` (firmante) y `elena` (administración), todas con
contraseña `demo12345`. El comando se niega a correr fuera de `DEBUG`.

Para trabajar sin levantar todo el stack basta la base de datos:

```bash
make db && make verify
```

## Gates

`make verify` es la única puerta del proyecto: ningún trabajo se considera
terminado sin que pase entera. Cada gate es una verificación real.

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

Dos gates corren aparte porque montan un entorno completo y tardan minutos:

| Gate | Cómo |
|---|---|
| `e2e` | `make up && make seed && make e2e` — el trámite completo por la UI real |
| `rename` | `make rename-check` — copia el repo, lo renombra y exige que siga verde |

**`parity` es el que impide la deriva.** Los flujos son datos, y su verdad vive
en `spec/flujos/`. Si alguien añade una transición por el admin, toca la
migración de siembra o edita el JSON sin volver a sembrar, el sistema en
ejecución deja de ser el declarado en el repositorio y nada más lo detectaría
([ADR-0003](spec/decisiones/0003-la-verdad-de-los-flujos-vive-en-spec.md)).

Los gates crecen con el proyecto: un target aparece en el Makefile cuando lo
que verifica existe. No hay objetivos decorativos que pasen sin comprobar nada.

## Renombrar el proyecto

```bash
make rename NAME=tramites-sep
```

Reemplaza el identificador del proyecto y el nombre de su base de datos, y deja
intacto el del framework —que aparece en imports, settings `SINPAPEL_*` y rutas
`/sinpapel/api/`—. `make rename-check` lo verifica sobre una copia.

## Estructura

```
├── .claude/
│   ├── commands/sinpapel/     Los tres comandos slash
│   └── skills/                Skills de sinpapel vendorizadas (make skills-sync)
├── spec/
│   ├── sistema.yaml           Identidad, roles y trámites
│   ├── flujos/                Verdad de los flujos, en JSON v0.2
│   └── decisiones/            ADRs
├── backend/
│   ├── config/                settings (base/dev/prod/test), urls, wsgi, asgi
│   ├── apps/core/             validadores y folios compartidos
│   ├── apps/cuentas/          usuario, dependencias, adscripciones, roles
│   ├── apps/spec_io/          import/export de flujos para el designer
│   ├── apps/tramite_ejemplo/  LA slice canónica
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
sinpapel~=0.8.4          @aprendomx/sinpapel-vue ^0.4.0
sinpapel-drf~=0.4.5      sinpapel-designer v0.1.0
sinpapel-webhooks~=0.2.4 Django>=5.2,<6.0 · Python 3.12
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

## Despliegue

Un despliegue por cliente, sin multi-tenancy
([ADR-0004](spec/decisiones/0004-single-tenant-con-dependencias-y-adscripciones.md)).
Ver [`ops/deploy/README.md`](ops/deploy/README.md) para el compose de
producción, el cron de SLA, los respaldos y la custodia de llaves FIEL.

## Para agentes

Lee [CLAUDE.md](CLAUDE.md) antes de tocar código: las reglas duras del
repositorio y las trampas verificadas del framework, varias de las cuales no
producen ningún error visible cuando se incumplen.

Las 20 skills de `sinpapel` están vendorizadas en `.claude/skills/`; el commit
de origen queda en `.claude/SKILLS_VERSION` y se actualizan con
`make skills-sync`. **Nunca se editan a mano.**

## Licencia

GPL-3.0-or-later, igual que `sinpapel`.
