"""Vistas de infraestructura del proyecto (no de dominio)."""

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def salud(_request: HttpRequest) -> JsonResponse:
    """Health check para el orquestador: verifica proceso y base de datos.

    Además siembra la cookie CSRF. El frontend consulta este endpoint al
    montar, así que para cuando alguien pueda pulsar un botón la cookie ya
    existe; sin ella el primer POST fallaría con 403 aunque la sesión sea
    válida.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 — el health check reporta, no relanza
        return JsonResponse({"estado": "degradado", "base_datos": str(exc)}, status=503)
    return JsonResponse({"estado": "ok", "base_datos": "ok"})
