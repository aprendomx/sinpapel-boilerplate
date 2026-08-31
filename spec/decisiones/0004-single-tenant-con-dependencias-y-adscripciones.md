# ADR-0004 — Single-tenant, con visibilidad por adscripción

- **Estado:** aceptada
- **Fecha:** 2026-08-28

## Contexto

Un sistema de trámites tiene que responder dos preguntas distintas: *qué* puede
hacer una persona y *sobre qué expedientes*. Las instituciones que lo operan
tienen áreas, y una persona de una dirección no debe ver los expedientes de
otra.

La tentación es resolverlo con multi-tenancy: un middleware que fije el tenant,
o schemas de base de datos por cliente.

## Decisión

**Un despliegue por cliente.** Cada institución corre su propia instancia con su
propia base de datos. No hay middleware de tenant ni schemas dinámicos.

Dentro de un despliegue, la visibilidad por área se modela con FKs normales:

- `Dependencia`, un árbol de áreas administrativas.
- `Adscripcion`, el vínculo con vigencia entre una persona y una dependencia.

Los permisos se resuelven por **rol + adscripción**: el rol —un grupo de
Django— dice qué acciones puede ejecutar, y lo valida el motor a través de
`ConfiguracionTransicion.grupos_permitidos`; la adscripción dice sobre qué
expedientes, y lo acota el queryset de la API de dominio.

## Consecuencias

- El modelo de datos es Django corriente: sin magia, sin middleware que pueda
  fallar abierto.
- La adscripción tiene vigencia (`desde`/`hasta`) en vez de ser un simple FK en
  el usuario: el expediente puede explicar quién podía ver qué en cada momento,
  que es lo que pide una auditoría.
- Quien está adscrito a un área superior ve las subordinadas. Es una decisión de
  dominio, no una limitación: así funcionan las jerarquías administrativas.
- Operar N clientes son N despliegues. Es más infraestructura, a cambio de
  aislamiento real: un error de filtrado no puede exponer datos de otro cliente
  porque no están en la misma base.
- **El filtrado por adscripción vive en el queryset de la API de dominio, no en
  el motor.** Las acciones que genera `sinpapel-drf` usan `IsAuthenticated`, así
  que un endpoint de workflow nuevo hereda la validación de rol pero no la de
  área: acótalo tú.
