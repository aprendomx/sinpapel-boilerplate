"""Webhooks del trámite: emisión al aprobar y recepción idempotente."""

import hashlib
import hmac
import json
import time
import uuid

import pytest
from django.urls import reverse
from sinpapel_webhooks.models import (
    InboundWebhookEvent,
    WebhookDelivery,
    WebhookEvent,
    WebhookSubscription,
)

from apps.tramite_ejemplo.webhooks import EVENTO_CURP_VALIDADA, FUENTE_RENAPO

pytestmark = pytest.mark.django_db

SECRETO = "a" * 64


@pytest.fixture
def suscripcion(db) -> WebhookSubscription:
    return WebhookSubscription.objects.create(
        name="consumidor-de-pruebas",
        url="https://consumidor.example.com/hook",
        events=["workflow.transition.completed"],
        secret=SECRETO,
        active=True,
    )


def test_aprobar_emite_el_evento_de_transicion(
    solicitud_en_revision,
    firmante,
    firma_payload,
    suscripcion,
    settings,
    django_capture_on_commit_callbacks,
):
    """`sinpapel-webhooks` emite el evento por su cuenta al crearse el seguimiento.

    Con backend `outbox` la entrega queda encolada como `WebhookDelivery`
    pendiente y la despacha el worker; el trámite no tiene que hacer nada.

    El paquete encola con `transaction.on_commit()` para no emitir eventos de
    transacciones que luego hacen rollback. Un test envuelto en transacción
    nunca commitea, así que hay que ejecutar esos callbacks explícitamente.
    """
    settings.SINPAPEL_WEBHOOKS_BACKEND = "outbox"

    with django_capture_on_commit_callbacks(execute=True):
        solicitud_en_revision.transition("APROBADA", firmante, firma_payload=firma_payload)

    evento = WebhookEvent.objects.filter(event_type="workflow.transition.completed").latest(
        "occurred_at"
    )
    # El payload saliente es plano (el envoltorio `data` es del formato
    # entrante, no de éste).
    assert evento.payload["estado_anterior"] == "EN_REVISION"
    assert evento.payload["estado_nuevo"] == "APROBADA"
    assert evento.payload["target_object_id"] == solicitud_en_revision.pk
    assert evento.payload["user_id"] == firmante.pk

    entrega = WebhookDelivery.objects.get(event=evento, subscription=suscripcion)
    assert entrega.status == "pending"


def _firmar(cuerpo: bytes, secreto: str = SECRETO) -> str:
    """Cabecera `X-Sinpapel-Signature` tal como la construye el emisor."""
    marca = int(time.time())
    mac = hmac.new(secreto.encode(), f"{marca}.".encode() + cuerpo, hashlib.sha256)
    return f"t={marca},v1={mac.hexdigest()}"


def _enviar(client, solicitud, *, event_id: str, curp: str, settings):
    settings.SINPAPEL_WEBHOOKS_INBOUND_SECRETS = {FUENTE_RENAPO: SECRETO}
    cuerpo = json.dumps(
        {
            "event_id": event_id,
            "event_type": EVENTO_CURP_VALIDADA,
            "data": {"folio": solicitud.folio, "curp": curp},
        }
    ).encode()
    return client.post(
        reverse("sinpapel_webhooks:inbound", args=[FUENTE_RENAPO]),
        data=cuerpo,
        content_type="application/json",
        headers={
            "x-sinpapel-signature": _firmar(cuerpo),
            "x-sinpapel-event-id": event_id,
            "x-sinpapel-event-type": EVENTO_CURP_VALIDADA,
        },
    )


def test_inbound_aplica_la_curp_validada(client, solicitud, settings):
    nueva = "BEBB020202HDFXXX07"

    respuesta = _enviar(
        client, solicitud, event_id=str(uuid.uuid4()), curp=nueva, settings=settings
    )

    assert respuesta.status_code == 200
    solicitud.refresh_from_db()
    assert solicitud.meta.to_dict()["curp"] == nueva


def test_inbound_descarta_el_evento_repetido(client, solicitud, settings):
    """El dispatcher deduplica por `(source, event_id)`.

    Un reenvío del mismo evento responde 200 sin volver a ejecutar el handler:
    el consumidor no debe reintentar, y el expediente no se toca dos veces.
    """
    event_id = str(uuid.uuid4())
    primera = _enviar(
        client, solicitud, event_id=event_id, curp="BEBB020202HDFXXX07", settings=settings
    )
    segunda = _enviar(
        client, solicitud, event_id=event_id, curp="CECC030303HDFXXX05", settings=settings
    )

    assert (primera.status_code, segunda.status_code) == (200, 200)
    assert InboundWebhookEvent.objects.filter(source=FUENTE_RENAPO, event_id=event_id).count() == 1

    solicitud.refresh_from_db()
    # Ganó el primero: el segundo nunca llegó al handler.
    assert solicitud.meta.to_dict()["curp"] == "BEBB020202HDFXXX07"


def test_inbound_rechaza_una_firma_invalida(client, solicitud, settings):
    """Sin HMAC válido el handler jamás se invoca."""
    settings.SINPAPEL_WEBHOOKS_INBOUND_SECRETS = {FUENTE_RENAPO: SECRETO}
    cuerpo = json.dumps(
        {
            "event_id": str(uuid.uuid4()),
            "event_type": EVENTO_CURP_VALIDADA,
            "data": {"folio": solicitud.folio, "curp": "BEBB020202HDFXXX07"},
        }
    ).encode()

    respuesta = client.post(
        reverse("sinpapel_webhooks:inbound", args=[FUENTE_RENAPO]),
        data=cuerpo,
        content_type="application/json",
        headers={
            "x-sinpapel-signature": _firmar(cuerpo, secreto="b" * 64),
            "x-sinpapel-event-id": str(uuid.uuid4()),
            "x-sinpapel-event-type": EVENTO_CURP_VALIDADA,
        },
    )

    assert respuesta.status_code == 401
    solicitud.refresh_from_db()
    assert solicitud.meta.to_dict()["curp"] == "AEAA010101HDFXXX09"


def test_inbound_con_folio_desconocido_no_falla(client, solicitud, settings):
    """Un folio inexistente se reporta, no revienta: el emisor no debe reintentar."""
    settings.SINPAPEL_WEBHOOKS_INBOUND_SECRETS = {FUENTE_RENAPO: SECRETO}
    cuerpo = json.dumps(
        {
            "event_id": str(uuid.uuid4()),
            "event_type": EVENTO_CURP_VALIDADA,
            "data": {"folio": "SC-2000-999999", "curp": "BEBB020202HDFXXX07"},
        }
    ).encode()
    event_id = str(uuid.uuid4())

    respuesta = client.post(
        reverse("sinpapel_webhooks:inbound", args=[FUENTE_RENAPO]),
        data=cuerpo,
        content_type="application/json",
        headers={
            "x-sinpapel-signature": _firmar(cuerpo),
            "x-sinpapel-event-id": event_id,
            "x-sinpapel-event-type": EVENTO_CURP_VALIDADA,
        },
    )

    assert respuesta.status_code == 200


def test_inbound_con_payload_incompleto_se_reporta(client, solicitud, settings):
    """Falta la CURP: se responde 200 y se explica, sin tocar el expediente."""
    settings.SINPAPEL_WEBHOOKS_INBOUND_SECRETS = {FUENTE_RENAPO: SECRETO}
    cuerpo = json.dumps(
        {
            "event_id": str(uuid.uuid4()),
            "event_type": EVENTO_CURP_VALIDADA,
            "data": {"folio": solicitud.folio},
        }
    ).encode()

    respuesta = client.post(
        reverse("sinpapel_webhooks:inbound", args=[FUENTE_RENAPO]),
        data=cuerpo,
        content_type="application/json",
        headers={
            "x-sinpapel-signature": _firmar(cuerpo),
            "x-sinpapel-event-id": str(uuid.uuid4()),
            "x-sinpapel-event-type": EVENTO_CURP_VALIDADA,
        },
    )

    assert respuesta.status_code == 200
    solicitud.refresh_from_db()
    assert solicitud.meta.to_dict()["curp"] == "AEAA010101HDFXXX09"


def test_inbound_reenviado_con_otro_id_no_corrompe(client, solicitud, settings):
    """El handler es idempotente por su cuenta, no solo por la deduplicación.

    Un reintento del proveedor tras un timeout llega con otro `event_id` y
    esquiva el dedup; escribir el mismo valor otra vez no debe cambiar nada.
    """
    curp = "BEBB020202HDFXXX07"
    _enviar(client, solicitud, event_id=str(uuid.uuid4()), curp=curp, settings=settings)
    _enviar(client, solicitud, event_id=str(uuid.uuid4()), curp=curp, settings=settings)

    solicitud.refresh_from_db()
    assert solicitud.meta.to_dict()["curp"] == curp
    assert solicitud.history.count() == 2
