"""Settings de desarrollo.

El designer escribe a disco solo con DEBUG=True (ver spec/decisiones/).
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# El navegador habla con el dev server de Vite, que proxea al backend
# reescribiendo el Host. Sin declarar ese origen, todo POST se rechaza por CSRF.
CSRF_TRUSTED_ORIGINS = env.list(  # noqa: F405
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
)

# En dev basta el backend manual: no exige criptografía ni credenciales.
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.manual.ManualBackend"

# Entrega síncrona de webhooks: sin worker, útil para smoke local.
SINPAPEL_WEBHOOKS_BACKEND = "inline"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
