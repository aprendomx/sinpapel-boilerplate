from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.cuentas.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        ("Identificación", {"fields": ("curp",)}),
    )
    list_display = ("username", "first_name", "last_name", "email", "is_staff")
