"""Modelo del trámite: folio, registro en el workflow y metadatos."""

import pytest
from django.core.exceptions import ValidationError
from sinpapel.registry import WorkflowRegistry

from apps.tramite_ejemplo.models import SolicitudConstancia

pytestmark = pytest.mark.django_db


def test_registrado_en_el_workflow_registry():
    config = WorkflowRegistry.get("solicitud_constancia")

    assert config.model is SolicitudConstancia
    assert config.state_field == "estado"
    assert config.expose_endpoints is True
    assert config.effective_slug == "solicitudes-constancia"


def test_metodos_inyectados_por_el_decorador(solicitud):
    for metodo in (
        "transition",
        "available_transitions",
        "can_transition_to",
        "preview_transition",
    ):
        assert callable(getattr(solicitud, metodo))


def test_el_folio_se_asigna_y_es_consecutivo(solicitante, dependencia, estados):
    primera = SolicitudConstancia(
        solicitante=solicitante, dependencia=dependencia, estado=estados["BORRADOR"]
    )
    primera.meta.curp = "AEAA010101HDFXXX09"
    primera.save()

    segunda = SolicitudConstancia(
        solicitante=solicitante, dependencia=dependencia, estado=estados["BORRADOR"]
    )
    segunda.meta.curp = "BEBB020202MDFXXX07"
    segunda.save()

    assert primera.folio.endswith("-000001")
    assert segunda.folio.endswith("-000002")
    assert primera.folio.startswith("SC-")


def test_el_folio_no_se_reasigna_al_guardar(solicitud):
    original = solicitud.folio

    solicitud.save()

    assert solicitud.folio == original


def test_no_se_guarda_sin_los_metadatos_requeridos(solicitante, dependencia, estados):
    """`MetadatosCapturables.save()` valida en cada guardado.

    Es la razón de que el motivo del rechazo no pueda declararse `requerido`:
    haría imposible crear la solicitud.
    """
    sin_curp = SolicitudConstancia(
        solicitante=solicitante, dependencia=dependencia, estado=estados["BORRADOR"]
    )

    with pytest.raises(ValidationError, match="curp"):
        sin_curp.save()


def test_el_tipo_de_constancia_tiene_default(solicitud):
    assert solicitud.meta.to_dict()["tipo_constancia"] == "ESTUDIOS"


def test_el_tipo_de_constancia_rechaza_un_valor_fuera_de_choices(solicitud):
    with pytest.raises(ValueError, match="solo acepta"):
        solicitud.meta.tipo_constancia = "INVENTADO"


def test_los_metadatos_rechazan_un_campo_fuera_del_schema(solicitud):
    with pytest.raises(AttributeError, match="no definido en el schema"):
        solicitud.meta.campo_inventado = "x"


def test_los_metadatos_rechazan_un_tipo_equivocado(solicitud):
    with pytest.raises(TypeError, match="espera str"):
        solicitud.meta.curp = 12345


def test_el_historial_registra_las_ediciones(solicitud):
    """`HistoricalRecords` audita cambios de fila; `SeguimientoWorkflow`, transiciones."""
    solicitud.meta.requisitos_confirmados = True
    solicitud.save()

    tipos = [h.history_type for h in solicitud.history.all().order_by("history_date")]

    assert tipos == ["+", "~"]


def test_representacion_legible(solicitud):
    assert str(solicitud) == f"{solicitud.folio} (BORRADOR)"
