"""Siembra datos de demostración: una dependencia y una cuenta por rol.

Es lo que consume `make seed` y lo que da al e2e sus actores. NO es una data
migration: son datos de conveniencia para desarrollo y pruebas, no parte de la
definición del sistema, y por eso se crean con un comando explícito que nunca
corre solo.

Se niega a ejecutarse fuera de DEBUG: crea cuentas con contraseñas conocidas.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from sinpapel.cache import get_estado_by_name

from apps.cuentas.models import (
    ROL_ADMIN,
    ROL_FIRMANTE,
    ROL_REVISOR,
    ROL_SOLICITANTE,
    ROL_VENTANILLA,
    Adscripcion,
    Dependencia,
)

# Contraseña única y evidente: estas cuentas solo existen en desarrollo.
CONTRASENA = "demo12345"

CUENTAS = [
    ("ana", "Ana", "Pérez", ROL_SOLICITANTE, False),
    ("beto", "Beto", "Ramírez", ROL_VENTANILLA, False),
    ("carla", "Carla", "Núñez", ROL_REVISOR, False),
    ("diana", "Diana", "Olvera", ROL_FIRMANTE, False),
    ("elena", "Elena", "Sandoval", ROL_ADMIN, True),
]

DEPENDENCIA = ("DGA", "Dirección General de Atención")


class Command(BaseCommand):
    help = "Crea una dependencia y una cuenta por rol para desarrollo y e2e."

    def add_arguments(self, parser):
        parser.add_argument(
            "--con-solicitud",
            action="store_true",
            help="Crea además una solicitud en BORRADOR para la cuenta solicitante.",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        from django.conf import settings

        if not settings.DEBUG:
            raise CommandError(
                "seed_demo crea cuentas con contraseñas conocidas y solo corre "
                "con DEBUG=True. En producción, da de alta las cuentas por el admin."
            )

        Usuario = get_user_model()

        dependencia, _ = Dependencia.objects.get_or_create(
            clave=DEPENDENCIA[0], defaults={"nombre": DEPENDENCIA[1]}
        )

        for username, nombre, apellido, rol, es_staff in CUENTAS:
            usuario, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": nombre,
                    "last_name": apellido,
                    "is_staff": es_staff,
                    # El rol `admin` necesita staff para los endpoints de
                    # administración, y superuser para entrar al admin de Django.
                    "is_superuser": es_staff,
                },
            )
            if creado:
                usuario.set_password(CONTRASENA)
                usuario.save()
            usuario.groups.add(Group.objects.get(name=rol))
            Adscripcion.objects.get_or_create(usuario=usuario, dependencia=dependencia)
            self.stdout.write(f"  {'creada ' if creado else 'existía'}  {username} ({rol})")

        if opciones["con_solicitud"]:
            self._crear_solicitud(Usuario.objects.get(username="ana"), dependencia)

        self.stdout.write(
            self.style.SUCCESS(f"\nCuentas listas. Contraseña de todas: {CONTRASENA}")
        )

    def _crear_solicitud(self, solicitante, dependencia):
        from apps.tramite_ejemplo.models import SolicitudConstancia

        solicitud = SolicitudConstancia(
            solicitante=solicitante,
            dependencia=dependencia,
            estado=get_estado_by_name("BORRADOR"),
        )
        solicitud.meta.curp = "AEAA010101HDFXXX09"
        solicitud.save()
        self.stdout.write(f"  solicitud {solicitud.folio} en BORRADOR")
