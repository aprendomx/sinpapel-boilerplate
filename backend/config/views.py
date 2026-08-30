"""Vistas de infraestructura del proyecto (no de dominio)."""

from django.db import connection
from django.http import HttpRequest, JsonResponse


def salud(_request: HttpRequest) -> JsonResponse:
    """Health check para el orquestador: verifica proceso y base de datos."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 — el health check reporta, no relanza
        return JsonResponse({"estado": "degradado", "base_datos": str(exc)}, status=503)
    return JsonResponse({"estado": "ok", "base_datos": "ok"})
