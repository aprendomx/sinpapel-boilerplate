"""Settings de producción.

Todo lo sensible viene del entorno y falla ruidosamente si falta.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Entrega con reintentos y dead letter; exige correr el worker
# `sinpapel_webhooks_worker`.
SINPAPEL_WEBHOOKS_BACKEND = "outbox"

# ─── Firma electrónica ───────────────────────────────────────────────────────
# FIEL del SAT. La transición a APROBADA la exige (`requiere_firma=True` en el
# flujo), así que sin esto el trámite no se puede resolver favorablemente.
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.fiel.FielBackend"

# Modo B (server-side): el cliente sube .cer + .key + contraseña y el servidor
# firma. Da una UX simple a personas no técnicas, pero la clave privada existe
# en RAM del servidor durante la firma y eso traslada responsabilidad legal a
# quien opera el sistema. Exige la revisión del checklist de ADR-012 (ver la
# skill sinpapel-signing) antes de un despliegue real.
SINPAPEL_ALLOW_SERVER_SIGNING = True

# ACs de confianza del SAT. SIN ESTE BUNDLE una firma criptográficamente
# íntegra se persiste como VALIDA_SIN_CADENA: el certificado se verificó, pero
# NO que lo haya emitido el SAT. Nunca compares contra el string "VALIDA";
# compara contra `RegistroFirma.RESULTADOS_VALIDOS`.
SINPAPEL_FIEL_TRUSTED_CA_BUNDLE = env("SINPAPEL_FIEL_TRUSTED_CA_BUNDLE")
