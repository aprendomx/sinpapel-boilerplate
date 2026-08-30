"""Modelo de usuario del sistema.

`AUTH_USER_MODEL` apunta aquí desde la primera migración: Django no permite
cambiarlo después sin una migración de datos costosa, así que el modelo
existe desde el esqueleto aunque todavía no lleve campos de dominio.

La visibilidad por área (Dependencia / Adscripcion) y la resolución de
permisos por rol se modelan sobre este usuario en una fase posterior.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Usuario(AbstractUser):
    """Usuario del sistema.

    Hereda el contrato completo de `AbstractUser` (username, email, grupos,
    permisos). Los grupos de Django son la base de `grupos_permitidos` en las
    transiciones de sinpapel, así que no se sustituyen por un campo propio.
    """

    curp = models.CharField(
        _("CURP"),
        max_length=18,
        blank=True,
        help_text=_("Clave Única de Registro de Población, 18 caracteres."),
    )

    class Meta:
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")
        ordering = ["username"]

    def __str__(self) -> str:
        nombre = self.get_full_name()
        return f"{nombre} ({self.username})" if nombre else self.username
