"""Settings de desarrollo.

El designer escribe a disco solo con DEBUG=True (ver spec/decisiones/).
"""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# En dev basta el backend manual: no exige criptografía ni credenciales.
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.manual.ManualBackend"

# Entrega síncrona de webhooks: sin worker, útil para smoke local.
SINPAPEL_WEBHOOKS_BACKEND = "inline"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
