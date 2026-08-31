# ADR-0005 — El designer escribe al archivo, y solo en desarrollo

- **Estado:** aceptada
- **Fecha:** 2026-08-29

## Contexto

`sinpapel-designer` es una SPA standalone que diseña flujos visualmente y hace
round-trip por JSON v0.2. Embeberlo plantea dos preguntas: qué escribe, y
cuándo.

Lo natural sería que guardara contra la base: el usuario edita y ve el cambio
aplicado. Pero eso contradice ADR-0003 —la verdad vive en `spec/flujos/`— y
convierte el designer en una vía para cambiar el comportamiento del sistema
saltándose la revisión.

## Decisión

El designer se sirve embebido bajo `/designer/`, protegido con
`staff_member_required`, y guarda **al archivo** `spec/flujos/<nombre>.json`,
nunca a la base de datos.

La escritura está restringida a `DEBUG=True`. En producción:

- El endpoint de guardado responde 403.
- `spec/` se monta read-only en el contenedor.

Son dos defensas independientes a propósito: la primera es una decisión de
código y la segunda del despliegue, y ninguna depende de que la otra esté bien.

Un flujo editado entra a git como cualquier otro cambio, se revisa en un PR y
se aplica con una data migration.

## Consecuencias

- Editar un flujo en producción es imposible por diseño. Cuando haga falta un
  cambio urgente, el camino es el mismo que para cualquier corrección: rama,
  revisión, despliegue.
- El designer no refleja lo sembrado hasta que alguien lo carga. Se mitiga con
  `GET /designer/api/flujos/<nombre>/?desde=db`, que exporta el estado real.
- Guardar compara en forma canónica antes de escribir, así que reexportar sin
  cambios no produce un commit vacío.
- El bundle del designer no se versiona: se construye con `make designer` desde
  el tag pineado. Un repositorio recién clonado no lo tiene y la ruta responde
  503 explicando cómo construirlo.
- El proyecto upstream construye con `publicPath "/"` porque está pensado como
  SPA standalone. Embebido bajo un subpath hay que fijarlo, o el index pide sus
  assets a la raíz y la página sale en blanco con un 200: el script de build lo
  ajusta y después lo verifica.
