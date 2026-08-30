# ADR-0001 — El usuario custom existe desde el esqueleto

- **Estado:** aceptada
- **Fecha:** 2026-08-28

## Contexto

`AUTH_USER_MODEL` no se puede cambiar después de aplicar la primera migración
sin una migración de datos costosa y propensa a errores. El modelado de
visibilidad por área (`Dependencia`, `Adscripcion`) y la resolución de permisos
por rol llegan en una fase posterior a la del esqueleto.

Además, `sinpapel<=0.8.2` era incompatible con cualquier `AUTH_USER_MODEL`
propio: declaraba los FKs a usuario con el literal `"auth.User"`, y Django
abortaba el system check con cinco errores `fields.E301`. Ni `check` ni
`migrate` corrían.

## Decisión

`apps/cuentas` con un `Usuario(AbstractUser)` mínimo entra desde el esqueleto,
antes que cualquier otro modelo de dominio, y `AUTH_USER_MODEL` apunta a él
desde la migración `0001`.

El template exige `sinpapel>=0.8.3` y `sinpapel-webhooks>=0.2.4`, versiones que
declaran esos FKs con `settings.AUTH_USER_MODEL`. El fix se hizo upstream a
raíz de este trabajo; no conlleva cambio de esquema.

## Consecuencias

- El esqueleto arrastra un modelo que todavía no tiene campos de dominio. Es
  deliberado: el costo de tenerlo vacío un rato es mucho menor que el de
  migrarlo después.
- `tests/unit/test_usuario.py` fija el contrato: si un bump del framework
  reintroduce el FK fijo, la suite falla aquí y no en un despliegue.
- Un downgrade a `sinpapel<0.8.3` rompe el arranque. El gate `audit` verifica
  que los pines sigan intactos.
