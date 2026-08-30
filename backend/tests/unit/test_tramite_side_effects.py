"""Side effects, SLA y generación de documentos por plantilla."""

import pytest
from django.contrib.contenttypes.models import ContentType
from sinpapel.models import InstanciaDocumento
from sinpapel.services.side_effects import resolver_handler

pytestmark = pytest.mark.django_db


def _generados(instancia) -> list[InstanciaDocumento]:
    """Documentos que produjo el sistema para esta instancia."""
    tipo = ContentType.objects.get_for_model(type(instancia))
    return list(
        InstanciaDocumento.objects.filter(
            target_content_type=tipo, target_object_id=instancia.pk
        ).exclude(archivo_generado="")
    )


def test_handlers_registrados_para_el_flujo():
    """`AppConfig.ready()` los importó; sin eso el motor los saltaría en silencio."""
    assert resolver_handler("RECIBIDA", "solicitud_constancia") is not None
    assert resolver_handler("APROBADA", "solicitud_constancia") is not None


def test_acuse_pdf_se_emite_al_recibir(solicitud, solicitante):
    resultado = solicitud.transition("RECIBIDA", solicitante)

    assert resultado["documento_generado"] is True
    generados = _generados(solicitud)
    assert len(generados) == 1
    assert generados[0].archivo_generado.name.endswith(".pdf")
    assert generados[0].documento.valor == "ACUSE_SOLICITUD_CONSTANCIA"


def test_oficio_docx_se_emite_al_aprobar(solicitud_en_revision, firmante, firma_payload):
    resultado = solicitud_en_revision.transition("APROBADA", firmante, firma_payload=firma_payload)

    assert resultado["documento_generado"] is True
    valores = {g.documento.valor for g in _generados(solicitud_en_revision)}
    assert valores == {"ACUSE_SOLICITUD_CONSTANCIA", "OFICIO_RESOLUCION_CONSTANCIA"}


def test_el_handler_es_idempotente(solicitud, solicitante):
    """Reejecutarlo no duplica el archivo en el expediente.

    Importa porque el handler corre post-commit: si falla a medias, el
    reintento llega por fuera y puede encontrarse el trabajo ya hecho.
    """
    from apps.tramite_ejemplo.side_effects import emitir_acuse

    solicitud.transition("RECIBIDA", solicitante)
    primero = _generados(solicitud)

    emitir_acuse(solicitud, solicitante)

    assert len(_generados(solicitud)) == len(primero) == 1


def test_el_contenido_del_acuse_lleva_los_datos_de_la_solicitud(solicitud, solicitante):
    """El overlay estampa el contexto de la fuente de datos sobre la plantilla."""
    from pypdf import PdfReader

    solicitud.transition("RECIBIDA", solicitante)
    generado = _generados(solicitud)[0]

    with generado.archivo_generado.open("rb") as fh:
        texto = PdfReader(fh).pages[0].extract_text()

    assert solicitud.folio in texto
    assert "AEAA010101HDFXXX09" in texto
    assert "ACUSE DE RECEPCIÓN" in texto


def test_un_side_effect_fallido_no_revierte_la_transicion(solicitud, solicitante, monkeypatch):
    """El handler corre después del commit: la transición ya persistió.

    El motor logea la excepción y devuelve `{"error": True}` en vez de
    relanzarla. Lo que deba bloquear va en un predicado, no aquí.
    """
    from apps.tramite_ejemplo import side_effects

    def explota(*args, **kwargs):
        raise RuntimeError("plantilla corrupta")

    monkeypatch.setattr(side_effects, "_generar", explota)

    resultado = solicitud.transition("RECIBIDA", solicitante)

    solicitud.refresh_from_db()
    assert solicitud.estado.nombre == "RECIBIDA"
    assert resultado["error"] is True


def test_sla_marca_la_solicitud_vencida(solicitud_en_revision):
    """El SLA de EN_REVISION activa la bandera al superar los 5 días.

    El plazo se mide como tiempo-en-estado: la referencia es la fecha del
    último `SeguimientoWorkflow`, no la de creación de la solicitud.
    """
    from datetime import timedelta

    from django.utils import timezone
    from sinpapel.models import SeguimientoWorkflow
    from sinpapel.services.sla_engine import SLAEngine

    # Hay que retrasar TODAS las filas de la bitácora, no solo la última: la
    # referencia es el máximo `fecha_accion`, así que dejar una reciente
    # mantendría el plazo vivo.
    SeguimientoWorkflow.objects.filter(target_object_id=solicitud_en_revision.pk).update(
        fecha_accion=timezone.now() - timedelta(days=6)
    )

    acciones = SLAEngine.evaluar_instancia(solicitud_en_revision)

    solicitud_en_revision.refresh_from_db()
    assert solicitud_en_revision.alerta_sla is True
    assert acciones == [
        {"accion": "alertar", "campo": "alerta_sla", "valor": True, "persistido": True}
    ]


def test_sla_no_dispara_dentro_del_plazo(solicitud_en_revision):
    from sinpapel.services.sla_engine import SLAEngine

    SLAEngine.evaluar_instancia(solicitud_en_revision)

    solicitud_en_revision.refresh_from_db()
    assert solicitud_en_revision.alerta_sla is False


def test_sin_plantilla_registrada_no_revienta(solicitud, solicitante, monkeypatch):
    """Si falta la fila `Documento`, se reporta y se sigue.

    El acuse es deseable, no bloqueante: quedarse sin plantilla no puede
    impedir que una solicitud se reciba.
    """
    from sinpapel.models import Documento

    Documento.objects.filter(valor="ACUSE_SOLICITUD_CONSTANCIA").delete()

    resultado = solicitud.transition("RECIBIDA", solicitante)

    solicitud.refresh_from_db()
    assert solicitud.estado.nombre == "RECIBIDA"
    assert resultado["documento_generado"] is False
    assert resultado["motivo"] == "plantilla_ausente"


def test_el_catalogo_de_campos_alimenta_el_editor_de_overlays():
    """La paleta que consume el editor visual sale de la fuente de datos."""
    from apps.tramite_ejemplo.reportes import SolicitudConstanciaDataSource

    campos = SolicitudConstanciaDataSource().get_field_catalog()
    claves = {c.key for c in campos}

    assert {"folio", "curp", "dependencia", "motivo_rechazo"} <= claves
    assert {c.grupo for c in campos if c.key == "curp"} == {"participantes"}
