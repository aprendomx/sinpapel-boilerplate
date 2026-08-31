# Despliegue

Un despliegue por cliente. No hay multi-tenancy: cada institución corre su
propia instancia con su propia base de datos.

```bash
cp .env.example .env.prod        # y ajústalo: en prod no hay valores por defecto
docker compose -f ops/deploy/docker-compose.prod.yml --env-file .env.prod up -d
```

El compose de producción falla al arrancar si falta cualquier variable
obligatoria, en vez de tomar un valor por defecto. Es deliberado: un
`DJANGO_SECRET_KEY` con el valor de ejemplo es peor que un despliegue que no
arranca.

## Servicios

| Servicio | Qué hace |
|---|---|
| `db` | PostgreSQL 16 + PostGIS |
| `backend` | migra, recolecta estáticos y sirve con gunicorn |
| `webhooks` | worker de la outbox |
| `sla` | evalúa los plazos cada hora |

`webhooks` y `sla` no son opcionales aunque el sistema arranque sin ellos:

- Con backend `outbox`, las entregas se acumulan en `pending` **para siempre**
  si nadie corre el worker. No hay error, no hay alerta: simplemente ningún
  consumidor externo se entera de nada.
- El motor de SLA **no es event-driven**. Si nadie evalúa los plazos, ninguna
  solicitud vence nunca y los escalamientos no ocurren.

## Custodia de llaves FIEL

La transición a `APROBADA` exige firma electrónica, y en producción el backend
es `FielBackend`. Dos piezas, con reglas distintas:

### Bundle de ACs del SAT — obligatorio

`SINPAPEL_FIEL_TRUSTED_CA_BUNDLE` apunta al PEM con las autoridades
certificadoras del SAT. **Sin él, una firma criptográficamente íntegra se
persiste como `VALIDA_SIN_CADENA`**: se verificó que la firma corresponde al
certificado, pero no que el certificado lo haya emitido el SAT. Cualquiera
podría firmar con un certificado autofirmado.

Se monta desde el host como read-only y nunca entra a la imagen ni al
repositorio:

```yaml
volumes:
  - /etc/sinpapel/sat-ca-bundle.pem:/etc/sinpapel/sat-ca-bundle.pem:ro
```

Al comprobar una firma en tu propio código, compara contra
`RegistroFirma.RESULTADOS_VALIDOS`, nunca contra el string `"VALIDA"`: dejarías
fuera las firmas legítimas y dentro ninguna, pero al revés —comparar con
`!= "INVALIDA"`— aceptarías las no verificadas.

### Llaves privadas de las personas firmantes — nunca en el servidor

El template configura **Modo B** (server-side): quien firma sube su `.cer`,
su `.key` y la contraseña, y el servidor firma en memoria.

Eso significa que **una clave privada de FIEL existe en la RAM del servidor
durante la firma**. El backend la descarta explícitamente al terminar y no la
escribe en disco, en la base ni en los logs, pero la responsabilidad legal
sobre ese manejo es de quien opera el sistema.

Antes de un despliegue real, revisa el checklist de ADR-012 (skill
`sinpapel-signing`). En particular:

- [ ] `SINPAPEL_ALLOW_SERVER_SIGNING` controlado por variable de entorno, no
      escrito en el código.
- [ ] HTTPS obligatorio: sin él, la clave privada viaja en claro.
- [ ] Revisión legal del uso de la FIEL del SAT para firma electrónica
      avanzada.
- [ ] Rate limiting en el endpoint de transición.

Si tu institución no puede asumir esa responsabilidad, cambia a **Modo A**
(client-side): pon `SINPAPEL_ALLOW_SERVER_SIGNING=False` y la clave privada
nunca sale del dispositivo de quien firma. Requiere que el cliente sepa firmar,
lo que complica el frontend, pero es la opción con mejor no repudio.

## Respaldos

```bash
./ops/deploy/backup.sh
```

Respalda la base y el expediente documental (`media/`), purga lo más viejo que
`RETENCION_DIAS` y te recuerda lo único que hace útil a un respaldo: probarlo
y sacarlo de la máquina.

Prográmalo en el cron del host, no dentro de un contenedor: si el contenedor no
arranca, quieres que el respaldo siga corriendo.

```cron
0 3 * * * cd /srv/tramites && ./ops/deploy/backup.sh >> /var/log/tramites-backup.log 2>&1
```

Lo que se respalda no es sustituible: `SeguimientoWorkflow` y `RegistroFirma`
son append-only por diseño y no se pueden reconstruir desde otra fuente. Los
archivos que subieron las personas usuarias, tampoco.

## Cambiar un flujo en producción

No se edita en caliente. El designer solo escribe con `DEBUG=True` y aquí
`spec/` está montado read-only.

El camino es: editar el JSON en desarrollo → revisar el diff en un PR →
aplicarlo con una data migration → desplegar. El gate `parity` falla mientras
la base y `spec/flujos/` no coincidan, que es exactamente lo que impide que el
sistema en ejecución deje de ser el declarado en el repositorio.
