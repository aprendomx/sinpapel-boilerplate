"""URLconf raíz del proyecto."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.api import router as router_dominio
from config.views import salud

urlpatterns = [
    path("admin/", admin.site.urls),
    path("salud/", salud, name="salud"),
    # API de dominio: CRUD del trámite y catálogos. Va en su propio prefijo
    # para no colisionar con el SinpapelRouter, que publica el mismo modelo
    # bajo /sinpapel/api/ con sus acciones de workflow.
    path("api/tramite/", include(router_dominio.urls)),
    # API de flujos: available-transitions, transition, history, metadatos,
    # documentos, requisitos, sla-status + CRUD admin y portabilidad.
    path("sinpapel/api/", include("sinpapel_drf.urls")),
    path("sinpapel/api/webhooks/", include("sinpapel_webhooks.urls")),
    path("reports/", include("sinpapel_reports.drf.urls")),
    # Designer embebido y el intercambio de spec/flujos/*.json. Protegido:
    # edita la definición de los trámites del sistema.
    path("designer/", include("apps.spec_io.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
