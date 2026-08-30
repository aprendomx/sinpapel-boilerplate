# ADR-0002 — Imagen PostGIS, engine PostgreSQL

- **Estado:** aceptada
- **Fecha:** 2026-08-28

## Contexto

El stack objetivo declara PostgreSQL 16 + PostGIS. Usar el engine
`django.contrib.gis.db.backends.postgis` obliga a tener GDAL y GEOS instalados
en **toda** máquina que ejecute el backend: desarrollo, CI y contenedor. En
macOS y en imágenes slim eso es una cadena de dependencias nativas pesada.

Hoy ningún modelo del template tiene campos de geometría.

## Decisión

El contenedor de base de datos corre `postgis/postgis:16-3.4`, así que la
extensión está disponible. El engine de Django, en cambio, es el de PostgreSQL
a secas (`postgres://` en `DATABASE_URL`).

## Consecuencias

- El arranque no requiere GDAL ni GEOS en ninguna máquina.
- Cuando un modelo necesite geometría: cambia el esquema de `DATABASE_URL` a
  `postgis://`, añade GDAL y GEOS a `ops/docker/backend.Dockerfile`, y
  documenta el requisito en el README. Es una línea de settings más la
  toolchain.
- La extensión PostGIS ya está en la imagen, así que ese cambio no obliga a
  recrear la base de datos.
