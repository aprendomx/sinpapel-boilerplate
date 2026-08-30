"""El usuario custom y su acoplamiento con sinpapel.

sinpapel<0.8.3 declaraba sus FKs a usuario con el literal "auth.User": con un
AUTH_USER_MODEL propio, Django abortaba el system check con fields.E301 y el
proyecto no arrancaba. Estos tests fijan el contrato para que un bump del
framework que reintroduzca el defecto se detecte aquí y no en un despliegue.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from sinpapel.models import RegistroFirma, SeguimientoWorkflow, VersionFlujo
from sinpapel_webhooks.models import WebhookSubscription


def test_auth_user_model_es_el_del_proyecto():
    assert settings.AUTH_USER_MODEL == "cuentas.Usuario"


@pytest.mark.parametrize(
    ("modelo", "campo"),
    [
        (VersionFlujo, "creado_por"),
        (SeguimientoWorkflow, "usuario_accion"),
        (RegistroFirma, "signer"),
        (WebhookSubscription, "created_by"),
    ],
)
def test_fks_del_framework_apuntan_al_usuario_del_proyecto(modelo, campo):
    field = modelo._meta.get_field(campo)

    assert field.remote_field.model is get_user_model(), (
        f"{modelo.__name__}.{campo} no resuelve a {settings.AUTH_USER_MODEL}; "
        "revisa la versión de sinpapel / sinpapel-webhooks."
    )


@pytest.mark.django_db
def test_usuario_se_crea_y_se_representa_por_nombre():
    Usuario = get_user_model()

    usuario = Usuario.objects.create_user(username="jperez", first_name="Juana", last_name="Pérez")

    assert str(usuario) == "Juana Pérez (jperez)"


@pytest.mark.django_db
def test_usuario_sin_nombre_se_representa_por_username():
    Usuario = get_user_model()

    usuario = Usuario.objects.create_user(username="ventanilla")

    assert str(usuario) == "ventanilla"
