from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.tramite_ejemplo.models import SolicitudConstancia


@admin.register(SolicitudConstancia)
class SolicitudConstanciaAdmin(SimpleHistoryAdmin):
    list_display = ("folio", "solicitante", "dependencia", "estado", "alerta_sla", "creado")
    list_filter = ("estado", "dependencia", "alerta_sla")
    search_fields = ("folio", "solicitante__username")
    autocomplete_fields = ["solicitante", "dependencia"]
    readonly_fields = ("folio", "creado", "actualizado")
