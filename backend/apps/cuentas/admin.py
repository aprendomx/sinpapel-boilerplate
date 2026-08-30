from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.cuentas.models import Adscripcion, Dependencia, Usuario


class AdscripcionInline(admin.TabularInline):
    model = Adscripcion
    extra = 0
    autocomplete_fields = ["dependencia"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        ("Identificación", {"fields": ("curp",)}),
    )
    list_display = ("username", "first_name", "last_name", "email", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    inlines = [AdscripcionInline]


@admin.register(Dependencia)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "superior", "activa")
    list_filter = ("activa",)
    search_fields = ("clave", "nombre")
    autocomplete_fields = ["superior"]


@admin.register(Adscripcion)
class AdscripcionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "dependencia", "desde", "hasta", "activa")
    list_filter = ("activa", "dependencia")
    autocomplete_fields = ["usuario", "dependencia"]
