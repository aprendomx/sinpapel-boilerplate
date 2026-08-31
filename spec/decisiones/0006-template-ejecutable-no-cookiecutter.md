# ADR-0006 — Template ejecutable, no cookiecutter

- **Estado:** aceptada
- **Fecha:** 2026-08-28

## Contexto

Un template de proyecto suele distribuirse como plantilla con marcadores
(`{{ project_name }}`) que una herramienta sustituye al generar. El problema es
que **la plantilla no compila**: no se puede ejecutar, ni testear, ni verificar
que sigue funcionando. Se comprueba generando un proyecto y probando ése, lo
que deja al template sin garantías propias.

Para un template pensado como base de trabajo de un agente de IA, eso es peor
todavía: el agente no puede correr los tests del template antes de modificarlo,
así que no tiene un punto de partida verde contra el que comparar.

## Decisión

El repositorio es **ejecutable**: no hay `{{ variables }}` en ningún archivo.
Se clona, se levanta y pasa sus propios gates tal cual.

La parametrización ocurre después, con `make rename NAME=<slug>`, que
reemplaza dos literales concretos —el identificador del proyecto en kebab-case
y su variante snake para la base de datos— y deja intacto todo lo demás.

Un trámite nuevo se crea **copiando `apps/tramite_ejemplo/` completa**, no
armando la estructura desde cero.

## Consecuencias

- El template se verifica a sí mismo. `make verify` corre sobre el repositorio
  real, no sobre una instancia generada.
- El gate `rename` cierra el hueco: copia el repositorio, lo renombra y exige
  que siga verde. Además comprueba que el renombrado **no** tocó el nombre del
  framework, que es la forma en que un reemplazo demasiado amplio destruiría el
  proyecto.
- La slice canónica no es documentación: es código en producción del propio
  repositorio, con sus tests y su cobertura. Si se rompe, el template está roto.
- El precio es que el template arrastra un trámite de ejemplo que hay que
  sustituir. Es deliberado: reconstruir esa estructura a mano garantiza olvidar
  piezas —los side effects registrados en `ready()`, el predicado, la firma
  exigible, los requisitos documentales—, y ninguna de esas omisiones falla de
  forma visible.
