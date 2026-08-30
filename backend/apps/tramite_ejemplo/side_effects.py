"""Efectos posteriores a una transición.

El motor invoca estos handlers **después** de que la transacción de la
transición commiteó. Implicaciones que condicionan cómo están escritos:

- Un fallo aquí **no** revierte la transición: ya persistió. El motor logea la
  excepción y devuelve `{"error": True, ...}` en el resultado. Lo que deba
  bloquear va en un predicado, no aquí.
- Por lo mismo tienen que ser idempotentes: el reintento llega por fuera
  (reejecución manual, cola) y puede encontrar el trabajo a medias.
- El motor **no** reenvía los kwargs de la transición (`comentarios`,
  `condiciones`, `ip_address`). Si hacen falta, se leen del
  `SeguimientoWorkflow` más reciente de la instancia.
"""

import logging

from sinpapel.models import Documento, InstanciaDocumento
from sinpapel.services.side_effects import register_side_effect

from apps.tramite_ejemplo.reportes import DOCUMENTO_ACUSE, DOCUMENTO_OFICIO

logger = logging.getLogger(__name__)


def _ya_generado(instancia, documento: Documento) -> InstanciaDocumento | None:
    """Devuelve la generación previa de `documento` para `instancia`, si existe.

    Es lo que hace idempotentes a los handlers: reejecutar no duplica el
    archivo en el expediente.
    """
    from django.contrib.contenttypes.models import ContentType

    tipo = ContentType.objects.get_for_model(type(instancia))
    return (
        InstanciaDocumento.objects.filter(
            target_content_type=tipo,
            target_object_id=instancia.pk,
            documento=documento,
        )
        .exclude(archivo_generado="")
        .first()
    )


def _generar(instancia, valor_documento: str, usuario) -> dict:
    """Genera por plantilla el documento de clave `valor_documento`."""
    from sinpapel_reports.services.report_engine import ReportEngine

    documento = Documento.objects.filter(valor=valor_documento).first()
    if documento is None:
        logger.error(
            "No existe el Documento '%s'; no se generó nada para %s",
            valor_documento,
            instancia.folio,
        )
        return {"documento_generado": False, "motivo": "plantilla_ausente"}

    previa = _ya_generado(instancia, documento)
    if previa is not None:
        return {"documento_generado": True, "instancia_documento_id": previa.pk}

    resultado = ReportEngine.generar(documento, instancia, actor=usuario)
    return {
        "documento_generado": True,
        "instancia_documento_id": resultado.instancia_id,
    }


@register_side_effect("RECIBIDA", workflow_key="solicitud_constancia")
def emitir_acuse(instance, user, **kwargs):
    """Emite el acuse de recepción en PDF al entrar a RECIBIDA.

    El acuse está declarado como requisito documental de RECIBIDA con
    `auto_carga=True`: lo produce el sistema, así que no bloquea a la persona
    solicitante aunque forme parte del expediente exigido.
    """
    return _generar(instance, DOCUMENTO_ACUSE, user)


@register_side_effect("APROBADA", workflow_key="solicitud_constancia")
def emitir_oficio_resolucion(instance, user, **kwargs):
    """Emite el oficio de resolución en DOCX al aprobar.

    El webhook `workflow.transition.completed` lo emite `sinpapel-webhooks` por
    su cuenta al crearse el `SeguimientoWorkflow`; aquí no hay que hacer nada
    para que salga.
    """
    return _generar(instance, DOCUMENTO_OFICIO, user)
