"""Settings de la suite de tests.

Nunca toca FIEL real ni la red: firma con FakeBackend y entrega los webhooks
en proceso.
"""

from .base import *  # noqa: F403

DEBUG = False

SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.fake.FakeBackend"
SINPAPEL_ALLOW_SERVER_SIGNING = False
SINPAPEL_WEBHOOKS_BACKEND = "inline"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
