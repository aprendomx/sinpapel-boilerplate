"""Router de la API de dominio.

Separado del `SinpapelRouter`, que auto-publica las acciones de workflow de
cada modelo decorado. Aquí van los endpoints propios del proyecto.
"""

from rest_framework.routers import DefaultRouter

from apps.cuentas.api import DependenciaViewSet
from apps.tramite_ejemplo.api import SolicitudConstanciaViewSet

router = DefaultRouter()
# Sin sufijos de formato: registrarlos colisiona con el converter global que ya
# declara cualquier otro DefaultRouter del proceso (Django >= 5.1 falla al
# re-registrar un nombre existente).
router.include_format_suffixes = False
router.register("solicitudes-constancia", SolicitudConstanciaViewSet, basename="solicitud")
router.register("dependencias", DependenciaViewSet, basename="dependencia")
