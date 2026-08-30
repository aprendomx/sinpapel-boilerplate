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

El gate `parity` compara lo sembrado contra el JSON y falla si divergen. Es lo
que impide que un agente derive del diseño acordado.

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

## Comandos

```bash
make install   # venv del backend + npm ci del frontend
make up        # levanta db + backend + frontend
make db        # solo la base de datos (suficiente para make verify)
make verify    # todos los gates — la única puerta
make down      # detiene el stack
```

`make verify` necesita una base de datos alcanzable en `DATABASE_URL`: corre
`make db` antes, o apunta la variable a la que uses.

## Estado del template

El Makefile crece por fases: un target existe cuando lo que verifica es real.
Nada de objetivos decorativos que pasan sin comprobar nada. Los gates activos
hoy son `lint`, `migrations`, `test` y `audit`.
