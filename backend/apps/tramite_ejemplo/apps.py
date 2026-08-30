from django.apps import AppConfig


class TramiteEjemploConfig(AppConfig):
    name = "apps.tramite_ejemplo"
    label = "tramite_ejemplo"
    verbose_name = "Solicitud de Constancia"

    def ready(self):
        # Importar registra los handlers vía decorador. Va en ready() y no a
        # nivel de módulo porque fuera de aquí el orden de imports no está
        # garantizado y un handler sin registrar se salta EN SILENCIO: la
        # transición ocurre igual, solo que sin su efecto.
        from apps.tramite_ejemplo import reportes, side_effects  # noqa: F401
