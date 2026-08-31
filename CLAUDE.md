# CLAUDE.md

Instrucciones para agentes que trabajen en este repositorio. Son reglas, no
sugerencias: romperlas produce sistemas que compilan y aun así están mal.

## Qué es este repo

Template ejecutable para construir sistemas de trámites sobre el framework
[sinpapel](https://github.com/aprendomx/sinpapel). No es un cookiecutter: no
hay `{{ variables }}` en el código. Todo compila y pasa los tests tal cual, y
la parametrización ocurre con `make rename NAME=<slug>`.

Un despliegue por cliente (single-tenant). **No** hay middleware de tenant ni
schemas dinámicos.

## Reglas duras

### La verdad de los flujos vive en `spec/flujos/*.json`

Los estados y las transiciones son **datos**, no código. Se describen en JSON
v0.2 y se siembran por data migration leyendo ese JSON. Nunca declares un
`Estado` ni una `ConfiguracionTransicion` directamente en Python fuera de esa
migración, y nunca uses `models.CharField(choices=...)` para el estado.

El gate `parity` exporta lo sembrado con la propia API de portabilidad del
framework y lo compara, en forma canónica, contra el archivo. Es lo que impide
que un agente derive del diseño acordado, y cubre todo lo que el schema v0.2
sabe representar sin enumerarlo campo por campo.

Editar un flujo es: descargar el JSON, editarlo (a mano o en el designer),
guardarlo en `spec/flujos/` y **aplicarlo con una data migration**. Guardar el
archivo no toca la base; `parity` falla mientras no coincidan.

### Nunca edites `.claude/skills/` a mano

Es contenido vendorizado desde
[aprendomx/sinpapel-skills](https://github.com/aprendomx/sinpapel-skills). Los
cambios van al repo canónico; aquí se regeneran con `make skills-sync`. El
commit de origen queda en `.claude/SKILLS_VERSION`.

### `WorkflowService` no existe

El motor es `WorkflowEngine`, en `sinpapel.services.workflow_engine`. Si ves
código que importa `WorkflowService`, está mal y hay que migrarlo.

### Un trámite nuevo se crea copiando `apps/tramite_ejemplo/` completa

No armes la estructura desde cero. La slice canónica ejercita todo el stack
(predicados, firma, side effects, SLA, metadatos, requisitos, webhooks,
reportes, frontend); reconstruirla a mano garantiza olvidar piezas.

### Los side effects se registran en `AppConfig.ready()`

Nunca a nivel de módulo ni en `__init__.py`: el orden de imports no está
garantizado fuera de `ready()`, y un handler no registrado se salta en
silencio.

### Ningún trabajo termina sin `make verify` en verde

No hay excepciones. Si un gate no pasa, se arregla o se explica por qué es
imposible — no se desactiva.

### Idioma

Español para nombres de dominio, modelos, campos y mensajes de usuario. Inglés
para nombres técnicos de infraestructura (`docker-compose`, `healthcheck`,
`settings`).

## Verifica las APIs contra el código real

Las skills son la mejor referencia disponible, pero el código manda. Antes de
usar una API que no hayas usado ya en este repo, ábrela en
`backend/.venv/lib/python3.12/site-packages/sinpapel*` y confirma la firma.

Si una skill contradice al código, gana el código: repórtalo para corregir la
skill upstream. **No inventes** nombres de clases, métodos, settings ni campos.
Si algo no existe, dilo y detente.

## Trampas verificadas del framework

Estas ya costaron tiempo. Están confirmadas contra `sinpapel 0.8.3`:

- **`AUTH_USER_MODEL` custom exige `sinpapel>=0.8.3`** y
  `sinpapel-webhooks>=0.2.4`. Antes, los FKs a usuario usaban el literal
  `"auth.User"` y Django abortaba con `fields.E301`.
- **`get_signature_backend` no se re-exporta** en `sinpapel.signing`: se
  importa de `sinpapel.signing.factory`.
- **`instance.meta` no es dict-like.** El acceso es por atributo
  (`instance.meta.rfc = "..."`); `meta["x"]` lanza `TypeError` y
  `meta.update()` lanza `AttributeError`. El JSONField subyacente se llama
  `datos_capturados`.
- **`MetaFormFactory.build_form()` recibe la lista `SCHEMA_METADATOS`**, no la
  clase del modelo.
- **Un modelo con `@workflow_enabled` debe heredar `Trazable`** (o declarar un
  `DateTimeField` llamado `actualizado`): el motor guarda con
  `save(update_fields=[state_field, "actualizado"])`.
- **`MetadatosCapturables.save()` llama a `clean()` en cada guardado.** Una
  instancia con metadatos requeridos vacíos no puede cambiar de estado, porque
  el `save()` del motor también valida.
- **`CondicionTransicion` y `SLAConfiguracion` no tienen `HistoricalRecords`.**
  Editar un predicado o un SLA no deja rastro histórico.
- **`RegistroFirma` solo protege `delete()`**, no `save()`. Solo
  `SeguimientoWorkflow` es append-only en ambos.
- **Los side effects corren post-commit** y el motor **no** les reenvía los
  kwargs de la transición (`comentarios`, `condiciones`, `ip_address`); si los
  necesitas, léelos del `SeguimientoWorkflow` más reciente.
- **JSON Logic solo ve** `instance.pk`, `meta.<key>`, `user.id` y
  `user.username`. Para condicionar sobre otros campos del modelo, usa el
  backend `django_orm`.
- **`deserialize_flujo` rechaza un `VersionFlujo` cuyo nombre ya existe.**
- **`transition()` casi nunca lanza `ValueError`.** La documentación lo mapea a
  400 para "estado destino inválido" o "arista inexistente", pero ambos casos
  pasan por `puede_cambiar_estado` y salen como `PermissionError` — es decir,
  403. Si escribes una vista propia, no esperes un `ValueError` que no llega.
- **El payload saliente de `workflow.transition.completed` es plano**
  (`estado_nuevo`, `target_object_id`, …). El envoltorio `data` es del formato
  *entrante*, no del emitido.
- **Los eventos salientes se encolan con `transaction.on_commit()`.** En un test
  envuelto en transacción nunca corren: usa la fixture
  `django_capture_on_commit_callbacks(execute=True)`.
- **El SLA mide tiempo-en-estado** desde el `SeguimientoWorkflow` más reciente.
  En un test, retrasar solo la última fila no vence nada: la referencia es el
  máximo `fecha_accion` de la instancia.

## Trampas del propio template

- **El proxy del dev server debe cubrir cada prefijo del backend.** Una ruta
  fuera de la lista de `vite.config.js` no da error: Vite devuelve el
  `index.html` con un 200 y el cliente recibe HTML donde esperaba JSON. El
  store valida la forma de la respuesta justo por esto.
- **`node_modules` del contenedor es un volumen con nombre**, y Docker solo lo
  puebla desde la imagen la primera vez. Tras añadir una dependencia, el
  volumen viejo shadowea el nuevo; el `frontend.Dockerfile` lo detecta
  comparando un marcador que vive DENTRO del volumen y reinstala solo.
- **`make up` reconstruye siempre** (`--build`): sin eso, compose reutiliza la
  imagen y los cambios del Dockerfile no llegan nunca al contenedor.
- **Los tests de pantalla montan dentro de un `QLayout`.** Un `q-page` fuera de
  un `QPageContainer` no renderiza, y un componente Quasar sin registrar
  descarta sus slots con nombre: en ambos casos el wrapper sale vacío sin un
  solo error. `tests/setup.js` registra los componentes a mano porque el
  transform del plugin de Vite no aplica en tests.
- **`main.js` registra los componentes Quasar globalmente**, y no es opcional:
  `@aprendomx/sinpapel-vue` viene precompilado y resuelve sus `q-form` /
  `q-dialog` por nombre en tiempo de ejecución. Sin registrarlos el panel se
  ve casi bien pero no hay `<form>` real, así que **ninguna transición ocurre**
  y no aparece un solo error en consola.
- **axios necesita los nombres de CSRF de Django** (`csrftoken` /
  `X-CSRFToken`); los suyos por defecto son de otro framework y todo POST
  responde 403. El health check lleva `@ensure_csrf_cookie` para que la cookie
  exista antes del primer envío.
- **`CSRF_TRUSTED_ORIGINS` es obligatorio con el proxy del dev server**, que
  reescribe el `Host`. Sin él ni siquiera se puede iniciar sesión.
- **El login de la aplicación está en `/cuentas/login/`**, no en el admin: el
  admin solo deja entrar a cuentas `is_staff`, y de los cinco roles solo uno
  lo es.
- **La librería humaniza los nombres de estado** al mostrarlos (`EN_REVISION`
  se pinta «EN REVISION»), y deja todas las pestañas en el DOM ocultas con
  `display:none`. En un e2e, selecciona por `value` y acota a lo visible.
- **`CampoMetadato` con `requerido=True` Y `default` rompía `/metadatos/`**
  (arreglado en sinpapel 0.8.4). Con default, `requerido` no aporta nada:
  `errores()` nunca ve el campo vacío.

## Los tres comandos

El flujo de trabajo del template son tres slash commands, en
`.claude/commands/sinpapel/`:

| Comando | Qué hace |
|---|---|
| `/sinpapel:especificar` | Descripción en lenguaje natural → `spec/`. **No escribe código.** |
| `/sinpapel:generar` | `spec/` → la app del trámite, copiando la slice canónica |
| `/sinpapel:verificar` | Corre los gates e interpreta lo que falle |

La separación es deliberada: especificar y generar son decisiones distintas, y
la primera se aprueba antes de que exista una línea de código.

## Comandos

```bash
make install   # venv del backend + npm ci del frontend
make up        # levanta db + backend + frontend
make db        # solo la base de datos (suficiente para make verify)
make seed      # una dependencia y una cuenta por rol (solo con DEBUG)
make verify    # todos los gates — la única puerta
make designer  # construye sinpapel-designer en designer/dist/
make e2e       # el trámite completo por la UI (necesita `up` + `seed`)
make down      # detiene el stack
```

`make verify` necesita una base de datos alcanzable en `DATABASE_URL`: corre
`make db` antes, o apunta la variable a la que uses.

## Estado del template

El Makefile crece por fases: un target existe cuando lo que verifica es real.
Nada de objetivos decorativos que pasan sin comprobar nada. Los gates activos
hoy son `lint`, `lockfile`, `migrations`, `deploy`, `test`, `parity`,
`roundtrip`, `api-roles`, `coverage` y `audit`.

Las dependencias del backend se instalan desde `backend/requirements.lock`, no
resolviendo el `pyproject.toml`. Al tocar una dependencia hay que correr
`make lock` y commitear el resultado: el gate `lockfile` falla si divergen,
igual que `migrations` con los modelos.

`e2e` y `rename-check` corren aparte: el primero necesita el stack levantado
(`make up` + `make seed`) y el segundo monta un entorno completo desde cero, así
que tardan minutos y en CI van como jobs propios.
