"""Webhooks entrantes del trámite.

`sinpapel-webhooks` autodescubre este módulo por nombre desde su
`AppConfig.ready()`.

El **saliente** no se declara aquí: el paquete emite
`workflow.transition.completed` por sí solo al crearse cada
`SeguimientoWorkflow`, firma el POST con HMAC-SHA256 y lo entrega por el
backend configurado (`outbox` en producción, con su worker). Lo único que hace
falta es una `WebhookSubscription` suscrita a ese evento.
"""

import logging

from sinpapel_webhooks import webhook_receiver

logger = logging.getLogger(__name__)

FUENTE_RENAPO = "renapo"
EVENTO_CURP_VALIDADA = "curp.validada"


@webhook_receiver(source=FUENTE_RENAPO, event=EVENTO_CURP_VALIDADA)
def registrar_curp_validada(payload, request):  # noqa: ARG001 — firma del framework
    """Marca la CURP de una solicitud como validada por el servicio externo.

    El dispatcher ya verifica el HMAC y descarta duplicados por
    `(source, event_id)` antes de llegar aquí, así que un reenvío del mismo
    evento nunca ejecuta esta función dos veces. Aun así el handler es
    idempotente por su cuenta: escribir el mismo valor otra vez no cambia nada,
    de modo que un reenvío con otro `event_id` (un reintento del proveedor tras
    un timeout, por ejemplo) tampoco corrompe el expediente.
    """
    from apps.tramite_ejemplo.models import SolicitudConstancia

    datos = payload.get("data") or {}
    folio = datos.get("folio")
    curp = datos.get("curp")

    if not folio or not curp:
        logger.warning("Evento %s sin folio o curp: %s", EVENTO_CURP_VALIDADA, datos)
        return {"aplicado": False, "motivo": "payload_incompleto"}

    solicitud = SolicitudConstancia.objects.filter(folio=folio).first()
    if solicitud is None:
        logger.warning("Evento %s para un folio inexistente: %s", EVENTO_CURP_VALIDADA, folio)
        return {"aplicado": False, "motivo": "folio_desconocido"}

    if solicitud.meta.to_dict().get("curp") == curp:
        return {"aplicado": True, "folio": folio, "sin_cambios": True}

    solicitud.meta.curp = curp
    solicitud.save()
    return {"aplicado": True, "folio": folio, "sin_cambios": False}
