"""URLconf raíz del proyecto."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import salud

urlpatterns = [
    path("admin/", admin.site.urls),
    path("salud/", salud, name="salud"),
    # API de flujos: available-transitions, transition, history, metadatos,
    # documentos, requisitos, sla-status + CRUD admin y portabilidad.
    path("sinpapel/api/", include("sinpapel_drf.urls")),
    path("sinpapel/api/webhooks/", include("sinpapel_webhooks.urls")),
    path("reports/", include("sinpapel_reports.drf.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
