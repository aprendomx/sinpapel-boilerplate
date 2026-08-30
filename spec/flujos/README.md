# Flujos

La verdad de los flujos vive aquí, en JSON v0.2 (el formato de export/import de
`sinpapel` y del designer). Un archivo por flujo.

Estos JSON **no** son documentación: se siembran por data migration, y el gate
`parity` compara lo que hay en la base de datos contra ellos. Si divergen, el
gate falla.

Para editarlos visualmente usa el designer; con `DEBUG=True` escribe
directamente en este directorio, de modo que los cambios entren a git como
cualquier otro cambio de código.

Todavía no hay ningún flujo declarado: el trámite de ejemplo llega con la
vertical slice.
