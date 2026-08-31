# Decisiones de arquitectura

Registro de las decisiones que no se deducen leyendo el código: por qué el
proyecto es así y qué se aceptó a cambio.

| ADR | Decisión |
|---|---|
| [0001](0001-usuario-custom-desde-el-esqueleto.md) | El usuario custom existe desde el esqueleto |
| [0002](0002-engine-postgresql-con-imagen-postgis.md) | Imagen PostGIS, engine PostgreSQL |
| [0003](0003-la-verdad-de-los-flujos-vive-en-spec.md) | La verdad de los flujos vive en `spec/flujos/` |
| [0004](0004-single-tenant-con-dependencias-y-adscripciones.md) | Single-tenant, con visibilidad por adscripción |
| [0005](0005-el-designer-escribe-al-archivo-solo-en-debug.md) | El designer escribe al archivo, y solo en desarrollo |
| [0006](0006-template-ejecutable-no-cookiecutter.md) | Template ejecutable, no cookiecutter |

Escribe uno cuando tomes una decisión que la siguiente persona —o el siguiente
agente— podría deshacer sin darse cuenta de lo que costó. Incluye siempre las
consecuencias, también las incómodas: un ADR que solo lista ventajas no está
registrando una decisión, está justificándola.
