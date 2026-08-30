"""Usuario, áreas y adscripciones.

La visibilidad por área se modela con FKs normales (`Dependencia`,
`Adscripcion`), no con un middleware de tenant ni schemas dinámicos: el
despliegue es uno por cliente.

Los permisos se resuelven por **rol + adscripción**: el rol (grupo de Django)
dice *qué* acciones puede ejecutar una persona, y la adscripción dice *sobre
qué expedientes*. El motor de sinpapel valida el rol a través de
`ConfiguracionTransicion.grupos_permitidos`; la parte de adscripción la aporta
este módulo.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validar_curp

# Roles del sistema. Son grupos de Django porque es lo que consume
# `ConfiguracionTransicion.grupos_permitidos`; declararlos aquí evita que los
# nombres se escriban a mano en cada sitio.
ROL_SOLICITANTE = "solicitante"
ROL_VENTANILLA = "ventanilla"
ROL_REVISOR = "revisor"
ROL_FIRMANTE = "firmante"
ROL_ADMIN = "admin"

ROLES = (
    (ROL_SOLICITANTE, _("Presenta y da seguimiento a sus propias solicitudes.")),
    (ROL_VENTANILLA, _("Recibe solicitudes y coteja requisitos documentales.")),
    (ROL_REVISOR, _("Analiza y resuelve solicitudes de su dependencia.")),
    (ROL_FIRMANTE, _("Firma electrónicamente las resoluciones favorables.")),
    (ROL_ADMIN, _("Administra catálogos, flujos y configuración.")),
)


class Dependencia(models.Model):
    """Área administrativa que atiende trámites.

    Es un árbol: una dependencia puede tener una superior, y quien está
    adscrito a la superior ve también los expedientes de las subordinadas.
    """

    clave = models.CharField(_("Clave"), max_length=20, unique=True)
    nombre = models.CharField(_("Nombre"), max_length=250)
    superior = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="subordinadas",
        verbose_name=_("Dependencia superior"),
    )
    activa = models.BooleanField(_("Activa"), default=True)

    class Meta:
        verbose_name = _("Dependencia")
        verbose_name_plural = _("Dependencias")
        ordering = ["clave"]

    def __str__(self) -> str:
        return f"{self.clave} — {self.nombre}"

    def descendientes(self) -> list["Dependencia"]:
        """Esta dependencia y todas las que cuelgan de ella.

        Recorre el árbol en memoria: el catálogo de áreas de una institución es
        de decenas de filas, no de miles, y así se evita una consulta recursiva.
        """
        resultado: list[Dependencia] = [self]
        pendientes: list[Dependencia] = [self]
        vistas = {self.pk}
        while pendientes:
            actual = pendientes.pop()
            for hija in actual.subordinadas.all():
                if hija.pk not in vistas:
                    vistas.add(hija.pk)
                    resultado.append(hija)
                    pendientes.append(hija)
        return resultado


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
        validators=[validar_curp],
        help_text=_("Clave Única de Registro de Población, 18 caracteres."),
    )

    class Meta:
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")
        ordering = ["username"]

    def __str__(self) -> str:
        nombre = self.get_full_name()
        return f"{nombre} ({self.username})" if nombre else self.username

    def tiene_rol(self, *roles: str) -> bool:
        """¿Pertenece a alguno de los roles indicados?"""
        return self.groups.filter(name__in=roles).exists()

    def dependencias_visibles(self) -> list[Dependencia]:
        """Dependencias sobre las que puede actuar, según sus adscripciones vigentes.

        Incluye las subordinadas de cada adscripción: quien está adscrito a un
        área superior ve los expedientes de las que dependen de ella.
        """
        visibles: dict[int, Dependencia] = {}
        for adscripcion in self.adscripciones.vigentes().select_related("dependencia"):
            for dependencia in adscripcion.dependencia.descendientes():
                visibles[dependencia.pk] = dependencia
        return list(visibles.values())


class AdscripcionQuerySet(QuerySet):
    def vigentes(self, momento=None) -> "AdscripcionQuerySet":
        """Adscripciones activas en `momento` (por omisión, ahora)."""
        momento = momento or timezone.now()
        return self.filter(
            Q(desde__lte=momento),
            Q(hasta__isnull=True) | Q(hasta__gte=momento),
            activa=True,
        )


class Adscripcion(models.Model):
    """Vínculo vigente entre una persona y una dependencia.

    Se modela con vigencia (`desde`/`hasta`) en vez de un simple FK en el
    usuario porque las adscripciones cambian y el expediente tiene que poder
    explicar quién podía ver qué en cada momento.
    """

    usuario = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.CASCADE,
        related_name="adscripciones",
        verbose_name=_("Usuario"),
    )
    dependencia = models.ForeignKey(
        Dependencia,
        on_delete=models.PROTECT,
        related_name="adscripciones",
        verbose_name=_("Dependencia"),
    )
    desde = models.DateTimeField(_("Vigente desde"), default=timezone.now)
    hasta = models.DateTimeField(_("Vigente hasta"), null=True, blank=True)
    activa = models.BooleanField(_("Activa"), default=True)

    objects = AdscripcionQuerySet.as_manager()

    class Meta:
        verbose_name = _("Adscripción")
        verbose_name_plural = _("Adscripciones")
        ordering = ["-desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "dependencia"],
                condition=Q(activa=True),
                name="cuentas_adscripcion_activa_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.usuario} → {self.dependencia.clave}"
