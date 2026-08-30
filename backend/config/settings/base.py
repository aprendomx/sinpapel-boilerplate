"""Settings compartidos por todos los entornos.

Los valores sensibles y los que cambian por despliegue se leen del entorno
(ver `.env.example` en la raíz del repo). Este módulo no debe contener
secretos ni rutas absolutas de una máquina concreta.
"""

from pathlib import Path

import environ

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# raíz del repo (donde viven spec/, ops/, frontend/)
REPO_DIR = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(REPO_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-inseguro-cambiar-en-produccion")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ─── Apps ────────────────────────────────────────────────────────────────────
# El orden importa (ver skill sinpapel-project-setup):
#   simple_history antes de sinpapel  — registra los modelos históricos.
#   sinpapel antes de las apps de dominio — éstas referencian sinpapel.Estado
#   por FK string.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Dependencias del framework
    "simple_history",
    "rest_framework",
    # sinpapel
    "sinpapel",
    "sinpapel_drf",
    "sinpapel_webhooks",
    "sinpapel_reports",
    # Apps de dominio
    "apps.cuentas",
    "apps.tramite_ejemplo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Puebla history_user en cada HistoricalRecords. Va DESPUÉS de
    # AuthenticationMiddleware porque depende de request.user.
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# El contenedor de base de datos corre PostgreSQL 16 con PostGIS, así que la
# extensión está disponible. El engine, en cambio, es el de PostgreSQL a secas:
# `django.contrib.gis` exige GDAL y GEOS instalados en cada máquina que corra
# el backend, y hoy ningún modelo tiene campos de geometría. Cuando alguno lo
# necesite, cambia el esquema de DATABASE_URL a `postgis://` y añade GDAL al
# Dockerfile y a la documentación de arranque.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://sinpapel:sinpapel@localhost:5432/sinpapel",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Usuario custom. Debe estar definido ANTES del primer migrate: cambiarlo
# después es costoso. Requiere sinpapel>=0.8.3 / sinpapel-webhooks>=0.2.4,
# que declaran sus FKs con settings.AUTH_USER_MODEL.
AUTH_USER_MODEL = "cuentas.Usuario"

LANGUAGE_CODE = "es-mx"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="America/Mexico_City")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# ─── sinpapel ────────────────────────────────────────────────────────────────
# La fuente de verdad de los flujos vive en spec/flujos/*.json y se siembra
# por data migration. Nunca definas estados ni transiciones en código.
SPEC_DIR = REPO_DIR / "spec"

SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.manual.ManualBackend"
SINPAPEL_ALLOW_SERVER_SIGNING = False
SINPAPEL_CACHE_ALIAS = "default"
SINPAPEL_CACHE_TIMEOUT = 3600
# Whitelist de módulos para predicados `python_path`. Sin ella ese backend
# rechaza todo. Vacía a propósito: las condiciones del trámite de ejemplo son
# `json_logic`, que no importa código del proyecto. Amplíala solo si añades
# predicados en Python, y apunta a módulos concretos, nunca a un paquete raíz.
SINPAPEL_PREDICATE_MODULES: list[str] = []

SINPAPEL_WEBHOOKS_BACKEND = env("SINPAPEL_WEBHOOKS_BACKEND", default="outbox")
SINPAPEL_WEBHOOKS_INBOUND_SECRETS = env.dict("SINPAPEL_WEBHOOKS_INBOUND_SECRETS", default={})

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
}
