# Designer

`sinpapel-designer` embebido: la SPA para diseñar flujos visualmente.

No es una app de Django ni se instala con pip. Se clona del repo canónico en el
tag pineado, se construye y se sirve desde `/designer/` con `staff_member_required`.
Ni el código fuente ni el bundle se versionan aquí — `dist/` está en
`.gitignore` y `DESIGNER_VERSION` deja constancia del commit construido.

```bash
make designer     # clona v0.1.0, construye y deja el bundle en dist/spa/
```

El tag lo comprueba el gate `audit`: verifica que `build-designer.sh` siga
pineando la versión verificada y que, si el bundle está construido, sea de ese
mismo tag. Un `make designer` con `SINPAPEL_DESIGNER_REF` apuntando a otra cosa
deja servido algo distinto de lo declarado, y sin el gate no se notaría.

Después está en <http://localhost:8000/designer/> (requiere una cuenta staff).

## Cómo editar un flujo

El designer guarda en `localStorage` y hace round-trip por archivo: no se
sincroniza solo con el backend, y su embebido por `iframe` está en el roadmap
del proyecto, no implementado. El intercambio es por JSON v0.2, que es el mismo
formato en los dos extremos.

1. **Descarga el flujo.** Desde el estado real del sistema:

   ```
   GET /designer/api/flujos/solicitud_constancia/?desde=db
   ```

   O el archivo tal como está en el repositorio, quitando `?desde=db`.

2. **Impórtalo** en el designer: `Workflows` → `Importar`, arrastrando el JSON.

3. **Edita** en el canvas. El toggle *Firma electrónica* de una transición es
   `ConfiguracionTransicion.requiere_firma`.

4. **Exporta** el JSON editado desde el designer.

5. **Súbelo** de vuelta:

   ```
   PUT /designer/api/flujos/solicitud_constancia/
   ```

   Escribe `spec/flujos/solicitud_constancia.json`. **Solo con `DEBUG=True`**:
   en producción el directorio se monta read-only y el guardado responde 403.

6. **Aplica el cambio con una data migration.** Guardar el archivo no toca la
   base de datos, y es deliberado: un cambio de flujo en caliente saltaría la
   revisión y dejaría el sistema fuera de sincronía con el repositorio.

   Mientras la base no coincida con el JSON, el gate `parity` falla — que es
   exactamente su trabajo.

## Por qué el archivo y no la base

Los estados y las transiciones son datos, pero son datos que definen el
comportamiento del sistema. Tratarlos como código —revisables en un PR,
versionados, aplicados por migración— es lo que impide que el sistema en
ejecución deje de ser el que está declarado en el repositorio.
