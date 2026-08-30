"""Siembra los roles del sistema como grupos de Django.

Son grupos y no un catálogo propio porque es lo que consume
`ConfiguracionTransicion.grupos_permitidos`: el motor de sinpapel valida la
pertenencia del usuario a esos grupos antes de permitir una transición.

El flujo también los declara en `catalogos.grupos`, así que su import los
crearía igual; se siembran aquí porque son parte de la definición del sistema
y deben existir aunque todavía no haya ningún flujo cargado.
"""

from django.db import migrations

ROLES = [
    "solicitante",
    "ventanilla",
    "revisor",
    "firmante",
    "admin",
]


def sembrar(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in ROLES:
        Group.objects.get_or_create(name=nombre)


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0002_alter_usuario_curp_dependencia_adscripcion"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Sin reverse: borrar los roles dejaría huérfanas las transiciones que
        # los referencian por `grupos_permitidos`.
        migrations.RunPython(sembrar, reverse_code=migrations.RunPython.noop),
    ]
