"""Gate `api-roles`: cada endpoint expuesto responde según el rol.

La autoridad sobre quién puede transicionar son los `grupos_permitidos` de la
`ConfiguracionTransicion`, no el frontend. Estos tests fijan ese contrato desde
fuera, por HTTP, para los cinco roles del sistema.

Ojo con el mapeo de códigos: `sinpapel-drf` traduce `PermissionError` a 403 y
`ValueError` a 400, pero el motor lanza `PermissionError` también cuando la
arista no existe. En la práctica, casi todo bloqueo llega como 403.
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

BASE = "/sinpapel/api/solicitudes-constancia"

ROLES = ["solicitante", "ventanilla", "revisor", "firmante", "admin"]


@pytest.fixture
def usuarios_por_rol(crear_usuario):
    """Un usuario por cada rol del sistema, todos adscritos a la dependencia."""
    return {rol: crear_usuario(f"u_{rol}", rol) for rol in ROLES}


def _cliente(usuario) -> APIClient:
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


# ─── Lectura ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rol", ROLES)
def test_lectura_abierta_a_cualquier_rol_autenticado(rol, usuarios_por_rol, solicitud):
    """Los endpoints de consulta exigen sesión, no un rol concreto.

    Filtrar por adscripción es responsabilidad del viewset de dominio; estas
    acciones las genera `sinpapel-drf` con `IsAuthenticated`.
    """
    cliente = _cliente(usuarios_por_rol[rol])

    for ruta in ["available-transitions", "requisitos", "documentos", "metadatos"]:
        respuesta = cliente.get(f"{BASE}/{solicitud.pk}/{ruta}/")
        assert respuesta.status_code == 200, f"{rol} → {ruta}: {respuesta.status_code}"


def test_sin_autenticar_no_se_lee_nada(solicitud):
    respuesta = APIClient().get(f"{BASE}/{solicitud.pk}/available-transitions/")

    assert respuesta.status_code == 403


# ─── Transiciones ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("solicitante", 201),
        ("ventanilla", 403),
        ("revisor", 403),
        ("firmante", 403),
        ("admin", 403),
    ],
)
def test_presentar_solicitud_solo_el_solicitante(rol, esperado, usuarios_por_rol, solicitud):
    respuesta = _cliente(usuarios_por_rol[rol]).post(
        f"{BASE}/{solicitud.pk}/transition/",
        {"target_state": "RECIBIDA", "comentarios": "Presento mi solicitud."},
        format="json",
    )

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("ventanilla", 201),
        ("solicitante", 403),
        ("revisor", 403),
        ("firmante", 403),
        ("admin", 403),
    ],
)
def test_enviar_a_revision_solo_ventanilla(rol, esperado, usuarios_por_rol, solicitud_recibida):
    solicitud_recibida.meta.requisitos_confirmados = True
    solicitud_recibida.save()

    respuesta = _cliente(usuarios_por_rol[rol]).post(
        f"{BASE}/{solicitud_recibida.pk}/transition/",
        {"target_state": "EN_REVISION"},
        format="json",
    )

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("firmante", 201),
        ("solicitante", 403),
        ("ventanilla", 403),
        ("revisor", 403),
        ("admin", 403),
    ],
)
def test_aprobar_solo_el_firmante(rol, esperado, usuarios_por_rol, solicitud_en_revision):
    respuesta = _cliente(usuarios_por_rol[rol]).post(
        f"{BASE}/{solicitud_en_revision.pk}/transition/",
        {"target_state": "APROBADA", "signature": {"backend": "fake"}},
        format="json",
    )

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("revisor", 201),
        ("solicitante", 403),
        ("ventanilla", 403),
        ("firmante", 403),
        ("admin", 403),
    ],
)
def test_rechazar_solo_el_revisor(rol, esperado, usuarios_por_rol, solicitud_en_revision):
    solicitud_en_revision.meta.motivo_rechazo = "Documentación inconsistente."
    solicitud_en_revision.save()

    respuesta = _cliente(usuarios_por_rol[rol]).post(
        f"{BASE}/{solicitud_en_revision.pk}/transition/",
        {"target_state": "RECHAZADA"},
        format="json",
    )

    assert respuesta.status_code == esperado


def test_aprobar_sin_firma_da_403(usuarios_por_rol, solicitud_en_revision):
    """`requiere_firma=True` se enforca en el motor, no en el cliente."""
    respuesta = _cliente(usuarios_por_rol["firmante"]).post(
        f"{BASE}/{solicitud_en_revision.pk}/transition/",
        {"target_state": "APROBADA"},
        format="json",
    )

    assert respuesta.status_code == 403


def test_el_preview_anuncia_que_hace_falta_firma(usuarios_por_rol, solicitud_en_revision):
    respuesta = _cliente(usuarios_por_rol["firmante"]).post(
        f"{BASE}/{solicitud_en_revision.pk}/preview-transition/",
        {"target_state": "APROBADA"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["firma_requerida"] is True


# ─── Endpoints de administración ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("admin", 200),
        ("solicitante", 403),
        ("ventanilla", 403),
        ("revisor", 403),
        ("firmante", 403),
    ],
)
def test_catalogo_de_slas_solo_para_administracion(rol, esperado, usuarios_por_rol):
    """`sinpapel-drf` protege el CRUD admin con `IsAdminUser`.

    Se apoya en el flag `is_staff` de Django, no en el grupo `admin`: tener el
    rol no basta si la cuenta no es de staff.
    """
    usuario = usuarios_por_rol[rol]
    if rol == "admin":
        usuario.is_staff = True
        usuario.save(update_fields=["is_staff"])

    respuesta = _cliente(usuario).get("/sinpapel/api/slas/")

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [
        ("admin", 200),
        ("solicitante", 403),
        ("ventanilla", 403),
        ("revisor", 403),
        ("firmante", 403),
    ],
)
def test_exportar_el_flujo_solo_para_administracion(rol, esperado, usuarios_por_rol):
    from sinpapel.models import VersionFlujo

    usuario = usuarios_por_rol[rol]
    if rol == "admin":
        usuario.is_staff = True
        usuario.save(update_fields=["is_staff"])
    flujo = VersionFlujo.objects.get(nombre="solicitud_constancia")

    respuesta = _cliente(usuario).get(f"/sinpapel/api/flujos/{flujo.pk}/export/")

    assert respuesta.status_code == esperado
