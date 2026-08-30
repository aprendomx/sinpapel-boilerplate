"""Recorrido del trámite y todo lo que lo bloquea.

Cubre los elementos de la slice que viven en la máquina de estados: permisos
por rol, predicado `json_logic`, requisitos documentales y firma exigible.
"""

import pytest
from sinpapel.models import SeguimientoWorkflow

pytestmark = pytest.mark.django_db


def test_camino_feliz_hasta_aprobada(
    solicitud, solicitante, ventanilla, firmante, adjuntar_documento, firma_payload
):
    resultado = solicitud.transition("RECIBIDA", solicitante)
    assert resultado["estado_nuevo"] == "RECIBIDA"

    adjuntar_documento(solicitud, "Identificación oficial")
    adjuntar_documento(solicitud, "Comprobante de domicilio")
    solicitud.meta.requisitos_confirmados = True
    solicitud.save()

    solicitud.transition("EN_REVISION", ventanilla)
    resultado = solicitud.transition("APROBADA", firmante, firma_payload=firma_payload)

    solicitud.refresh_from_db()
    assert solicitud.estado.nombre == "APROBADA"
    assert resultado["estado_anterior"] == "EN_REVISION"
    # Una fila de bitácora por transición ejecutada.
    assert SeguimientoWorkflow.objects.filter(target_object_id=solicitud.pk).count() == 3


def test_rol_equivocado_no_puede_transicionar(solicitud, revisor):
    """Los grupos permitidos son la autoridad: revisor no presenta solicitudes."""
    with pytest.raises(PermissionError):
        solicitud.transition("RECIBIDA", revisor)

    solicitud.refresh_from_db()
    assert solicitud.estado.nombre == "BORRADOR"


def test_requisitos_documentales_faltantes_bloquean(solicitud, solicitante, ventanilla):
    """Sin identificación ni comprobante, RECIBIDA no avanza."""
    solicitud.transition("RECIBIDA", solicitante)
    solicitud.meta.requisitos_confirmados = True
    solicitud.save()

    reporte = solicitud.preview_transition("EN_REVISION", ventanilla)
    faltantes = {
        d["tipo_documento"]
        for d in reporte["documentos_faltantes"]
        if d["tipo"] == "requisito_documento"
    }

    assert reporte["permitido"] is False
    assert faltantes == {"Identificación oficial", "Comprobante de domicilio"}
    with pytest.raises(PermissionError):
        solicitud.transition("EN_REVISION", ventanilla)


def test_acuse_autocarga_no_bloquea(solicitud, solicitante, ventanilla, adjuntar_documento):
    """El acuse es requisito de RECIBIDA pero lo genera el sistema.

    Está sembrado con `auto_carga=True`, así que el motor lo da por satisfecho
    y no aparece entre los faltantes aunque nadie lo suba.
    """
    solicitud.transition("RECIBIDA", solicitante)
    adjuntar_documento(solicitud, "Identificación oficial")
    adjuntar_documento(solicitud, "Comprobante de domicilio")
    solicitud.meta.requisitos_confirmados = True
    solicitud.save()

    reporte = solicitud.preview_transition("EN_REVISION", ventanilla)

    assert reporte["permitido"] is True
    assert reporte["documentos_faltantes"] == []


def test_documento_incompleto_no_satisface_el_requisito(
    solicitud, solicitante, ventanilla, adjuntar_documento
):
    """El requisito exige 100 %; un documento al 50 % sigue faltando."""
    solicitud.transition("RECIBIDA", solicitante)
    adjuntar_documento(solicitud, "Identificación oficial", porcentaje=50)
    adjuntar_documento(solicitud, "Comprobante de domicilio")

    reporte = solicitud.preview_transition("EN_REVISION", ventanilla)
    faltante = next(
        d for d in reporte["documentos_faltantes"] if d["tipo"] == "requisito_documento"
    )

    assert faltante["tipo_documento"] == "Identificación oficial"
    assert faltante["porcentaje_actual"] == 50
    assert faltante["porcentaje_requerido"] == 100


def test_predicado_bloquea_sin_cotejo_de_ventanilla(solicitud_recibida, ventanilla):
    """El `json_logic` exige que ventanilla confirme los requisitos."""
    reporte = solicitud_recibida.preview_transition("EN_REVISION", ventanilla)

    assert reporte["permitido"] is False
    assert any("cotejar" in p["mensaje"] for p in reporte["predicados_fallidos"])
    with pytest.raises(PermissionError, match="cotejar"):
        solicitud_recibida.transition("EN_REVISION", ventanilla)


def test_aprobar_exige_firma(solicitud_en_revision, firmante):
    """`requiere_firma=True` vive en la configuración de la transición.

    El motor rechaza la transición sin `firma_payload`, sin depender de que el
    llamador se acuerde de firmar.
    """
    reporte = solicitud_en_revision.preview_transition("APROBADA", firmante)
    assert reporte["firma_requerida"] is True

    with pytest.raises(PermissionError, match="firma"):
        solicitud_en_revision.transition("APROBADA", firmante)


def test_la_firma_queda_ligada_al_seguimiento(solicitud_en_revision, firmante, firma_payload):
    resultado = solicitud_en_revision.transition("APROBADA", firmante, firma_payload=firma_payload)

    seguimiento = SeguimientoWorkflow.objects.get(pk=resultado["seguimiento_id"])
    assert seguimiento.firma_registro is not None
    assert seguimiento.firma_registro.signer == firmante
    assert seguimiento.firma_registro.backend_name == "fake"


def test_rechazar_exige_motivo(solicitud_en_revision, revisor):
    """El motivo no puede ser `requerido=True` en el schema.

    `MetadatosCapturables.save()` valida en cada guardado, así que un motivo
    requerido impediría crear la solicitud. Su obligatoriedad se enforca con un
    predicado sobre la transición a RECHAZADA.
    """
    with pytest.raises(PermissionError, match="motivo"):
        solicitud_en_revision.transition("RECHAZADA", revisor)

    solicitud_en_revision.meta.motivo_rechazo = "La CURP no corresponde a la identificación."
    solicitud_en_revision.save()
    solicitud_en_revision.transition("RECHAZADA", revisor)

    solicitud_en_revision.refresh_from_db()
    assert solicitud_en_revision.estado.nombre == "RECHAZADA"


@pytest.mark.parametrize(
    ("destino", "mensaje"),
    [
        ("APROBADA", "No se puede cambiar de 'BORRADOR' a 'APROBADA'"),
        ("NO_EXISTE", "Estado destino 'NO_EXISTE' no existe"),
    ],
)
def test_destino_invalido_lanza_permission_error(
    solicitud, firmante, firma_payload, destino, mensaje
):
    """Tanto una arista inexistente como un estado inexistente dan PermissionError.

    Ojo: la documentación del framework mapea `ValueError` a 400 para estos
    casos, pero `transition()` no lo lanza. Ambas validaciones pasan por
    `puede_cambiar_estado`, que devuelve `(False, mensaje)`, y `cambiar_estado`
    convierte eso en `PermissionError` — es decir, 403. Verificado contra
    sinpapel 0.8.3; si escribes una vista propia, no esperes un `ValueError`
    que no llega.
    """
    with pytest.raises(PermissionError, match=mensaje):
        solicitud.transition(destino, firmante, firma_payload=firma_payload)


def test_transiciones_disponibles_filtran_por_flujo(solicitud, solicitante):
    """`resolve_workflow_version` acota las aristas al flujo activo."""
    destinos = {e.nombre for e in solicitud.available_transitions(solicitante)}

    assert destinos == {"RECIBIDA"}
