"""Guardas sobre la configuración del proyecto.

Cada test de este módulo protege una trampa documentada del framework: son
errores que no revientan al importar, sino en runtime y de forma difusa
(auditoría vacía, arranque roto tras cambiar el usuario, etc.).
"""

from django.conf import settings


def test_simple_history_va_antes_que_sinpapel():
    """`sinpapel` define modelos con HistoricalRecords y depende del registro
    previo de simple_history."""
    apps = settings.INSTALLED_APPS

    assert apps.index("simple_history") < apps.index("sinpapel")


def test_apps_de_dominio_van_despues_de_sinpapel():
    """Las apps de dominio referencian sinpapel.Estado por FK string."""
    apps = settings.INSTALLED_APPS

    assert apps.index("sinpapel") < apps.index("apps.cuentas")


def test_history_middleware_va_despues_de_authentication():
    """HistoryRequestMiddleware puebla history_user desde request.user; antes
    de AuthenticationMiddleware la auditoría queda siempre en None."""
    mw = settings.MIDDLEWARE

    assert mw.index("django.contrib.auth.middleware.AuthenticationMiddleware") < mw.index(
        "simple_history.middleware.HistoryRequestMiddleware"
    )


def test_predicate_modules_es_una_whitelist_explicita():
    """Con SINPAPEL_PREDICATE_MODULES en None el backend python_path rechaza
    todo; debe ser una lista, aunque esté vacía."""
    assert isinstance(settings.SINPAPEL_PREDICATE_MODULES, list)


def test_server_side_signing_desactivado():
    """Modo B del FIEL exige revisión legal: nunca por defecto."""
    assert settings.SINPAPEL_ALLOW_SERVER_SIGNING is False
