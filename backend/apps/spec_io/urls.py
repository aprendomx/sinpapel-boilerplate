"""Rutas del designer y del intercambio de flujos."""

from django.urls import path, re_path

from apps.spec_io.api import FlujosView, FlujoView
from apps.spec_io.views import designer

urlpatterns = [
    path("api/flujos/", FlujosView.as_view(), name="spec-flujos"),
    path("api/flujos/<str:nombre>/", FlujoView.as_view(), name="spec-flujo"),
    # El catch-all va al final: la SPA resuelve su propio enrutado, así que
    # cualquier ruta que no sea un archivo del bundle devuelve el index.
    path("", designer, name="designer"),
    re_path(r"^(?P<recurso>.+)$", designer, name="designer-recurso"),
]
