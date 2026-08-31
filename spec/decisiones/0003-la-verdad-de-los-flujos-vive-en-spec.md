# ADR-0003 — La verdad de los flujos vive en `spec/flujos/`

- **Estado:** aceptada
- **Fecha:** 2026-08-28

## Contexto

En `sinpapel` los estados y las transiciones son **datos**: filas de `Estado`,
`ConfiguracionTransicion`, `CondicionTransicion`, `RequisitoEstadoDocumento` y
`SLAConfiguracion`. Eso los hace editables en caliente desde el admin, desde la
API de administración o desde el designer.

Pero esos datos **definen el comportamiento del sistema**. Quién puede aprobar,
qué documentos se exigen, qué transición requiere firma electrónica: cambiarlos
cambia los actos administrativos que la institución puede emitir. Tratarlos
como configuración operativa significa que el sistema en ejecución puede dejar
de ser el que está declarado en el repositorio sin que nadie lo note.

Este template además está pensado para que un agente de IA lo use como base. Un
agente que puede modificar el flujo directamente en la base no deja rastro
revisable de lo que cambió.

## Decisión

La fuente de verdad de cada flujo es un archivo JSON v0.2 en `spec/flujos/`.

- Los flujos se siembran por data migration leyendo ese JSON, con
  `deserialize_flujo` — la misma API que usan el comando `sinpapel_import_flujo`
  y el endpoint `POST /flujos/import/`.
- Nunca se declara un `Estado` ni una `ConfiguracionTransicion` en Python fuera
  de esa migración.
- El designer escribe al archivo, no a la base (ver ADR-0005).
- El gate `parity` exporta lo sembrado con la propia API de portabilidad del
  framework y lo compara, en forma canónica, contra el archivo. Si divergen,
  falla.

## Consecuencias

- Cambiar un flujo es un cambio de código: se revisa en un PR, se versiona y se
  aplica con una migración. Más lento a propósito.
- El gate `parity` cubre todo lo que el schema v0.2 sabe representar sin
  enumerarlo campo por campo, que es como se queda corta una lista.
- Un cambio hecho por el admin en producción rompe el siguiente `make verify`.
  Es el comportamiento buscado: obliga a bajarlo al repositorio.
- El schema v0.2 acota lo que se puede expresar. Algo que no viaje en el JSON
  —por ejemplo, un estado sin ninguna transición— queda fuera del gate.
