"""API de dominio: bandeja acotada por adscripción y alta de solicitudes."""

import pytest
from rest_framework.test import APIClient

from apps.cuentas.models import Dependencia
from apps.tramite_ejemplo.models import SolicitudConstancia

pytestmark = pytest.mark.django_db

BASE = "/api/tramite/solicitudes-constancia"


def _cliente(usuario) -> APIClient:
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


@pytest.fixture
def solicitud_de_otra_dependencia(db, crear_usuario, otra_dependencia, estados):
    """Solicitud fuera del área de las personas adscritas a la dependencia base."""
    ajena = crear_usuario("zoe", "solicitante", adscrito_a=otra_dependencia)
    solicitud = SolicitudConstancia(
        solicitante=ajena,
        dependencia=otra_dependencia,
        estado=estados["BORRADOR"],
    )
    solicitud.meta.curp = "CECC030303HDFXXX05"
    solicitud.save()
    return solicitud


def test_el_solicitante_solo_ve_lo_suyo(
    solicitante, crear_usuario, solicitud, dependencia, estados
):
    """Estar adscrito a un área no le da acceso al expediente de otras personas."""
    otro = crear_usuario("otro_solicitante", "solicitante")
    ajena = SolicitudConstancia(
        solicitante=otro, dependencia=dependencia, estado=estados["BORRADOR"]
    )
    ajena.meta.curp = "BEBB020202MDFXXX07"
    ajena.save()

    respuesta = _cliente(solicitante).get(f"{BASE}/")
    folios = {s["folio"] for s in respuesta.json()["results"]}

    assert respuesta.status_code == 200
    assert folios == {solicitud.folio}


def test_ventanilla_ve_las_de_su_dependencia(ventanilla, solicitud, solicitud_de_otra_dependencia):
    respuesta = _cliente(ventanilla).get(f"{BASE}/")
    folios = {s["folio"] for s in respuesta.json()["results"]}

    assert folios == {solicitud.folio}
    assert solicitud_de_otra_dependencia.folio not in folios


def test_la_adscripcion_alcanza_a_las_subordinadas(ventanilla, dependencia, crear_usuario, estados):
    hija = Dependencia.objects.create(clave="DGA-1", nombre="Subdirección", superior=dependencia)
    solicitante_hija = crear_usuario("hijo", "solicitante", adscrito_a=hija)
    en_la_hija = SolicitudConstancia(
        solicitante=solicitante_hija, dependencia=hija, estado=estados["BORRADOR"]
    )
    en_la_hija.meta.curp = "DEDD040404HDFXXX03"
    en_la_hija.save()

    respuesta = _cliente(ventanilla).get(f"{BASE}/")
    folios = {s["folio"] for s in respuesta.json()["results"]}

    assert en_la_hija.folio in folios


def test_administracion_ve_todo(administrador, solicitud, solicitud_de_otra_dependencia):
    respuesta = _cliente(administrador).get(f"{BASE}/")
    folios = {s["folio"] for s in respuesta.json()["results"]}

    assert folios == {solicitud.folio, solicitud_de_otra_dependencia.folio}


def test_no_se_puede_leer_una_solicitud_fuera_del_area(ventanilla, solicitud_de_otra_dependencia):
    """El queryset acota también el detalle: fuera del área es 404, no 403."""
    respuesta = _cliente(ventanilla).get(f"{BASE}/{solicitud_de_otra_dependencia.pk}/")

    assert respuesta.status_code == 404


def test_alta_de_solicitud(solicitante, dependencia):
    respuesta = _cliente(solicitante).post(
        f"{BASE}/",
        {
            "dependencia": dependencia.pk,
            "metadatos": {"curp": "AEAA010101HDFXXX09", "tipo_constancia": "RESIDENCIA"},
        },
        format="json",
    )

    assert respuesta.status_code == 201
    creada = SolicitudConstancia.objects.get(pk=respuesta.json()["id"])
    assert creada.solicitante == solicitante
    assert creada.estado.nombre == "BORRADOR"
    assert creada.folio.startswith("SC-")
    assert creada.meta.to_dict()["tipo_constancia"] == "RESIDENCIA"


@pytest.mark.parametrize(
    ("metadatos", "campo"),
    [
        ({"tipo_constancia": "ESTUDIOS"}, "curp"),
        ({"curp": "AEAA010101HDFXXX09", "tipo_constancia": "INVENTADO"}, "tipo_constancia"),
        ({"curp": 12345, "tipo_constancia": "ESTUDIOS"}, "curp"),
        ({"curp": "AEAA010101HDFXXX09", "inventado": "x"}, "inventado"),
    ],
)
def test_alta_rechaza_metadatos_invalidos(solicitante, dependencia, metadatos, campo):
    """El schema valida en el alta, no al primer intento de transición."""
    respuesta = _cliente(solicitante).post(
        f"{BASE}/",
        {"dependencia": dependencia.pk, "metadatos": metadatos},
        format="json",
    )

    assert respuesta.status_code == 400
    assert campo in str(respuesta.json()).lower()


def test_la_bandeja_expone_lo_que_la_ui_necesita(solicitante, solicitud):
    item = _cliente(solicitante).get(f"{BASE}/").json()["results"][0]

    assert item["estado"]["nombre"] == "BORRADOR"
    assert item["estado"]["color"]
    assert item["metadatos"]["curp"] == "AEAA010101HDFXXX09"
    assert item["dependencia_nombre"]


def test_catalogo_de_dependencias(solicitante, dependencia):
    respuesta = _cliente(solicitante).get("/api/tramite/dependencias/")

    assert respuesta.status_code == 200
    assert {d["clave"] for d in respuesta.json()["results"]} == {dependencia.clave}


def test_sin_autenticar_no_hay_bandeja():
    assert APIClient().get(f"{BASE}/").status_code == 403


@pytest.mark.parametrize(
    ("fixture_usuario", "esperado"),
    [("administrador", True), ("solicitante", False), ("ventanilla", False)],
)
def test_la_pestana_de_sla_solo_se_ofrece_a_administracion(
    request, fixture_usuario, esperado, solicitud
):
    """El endpoint `sla-status` exige IsAdminUser: ofrecerlo a otros da 403."""
    usuario = request.getfixturevalue(fixture_usuario)

    detalle = _cliente(usuario).get(f"{BASE}/{solicitud.pk}/").json()

    assert detalle["puede_evaluar_sla"] is esperado
