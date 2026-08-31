"""Solicitud de Constancia — la vertical slice canónica del template.

Un trámite nuevo se crea copiando esta app completa y renombrando, no armando
la estructura desde cero: aquí están conectadas todas las piezas del framework
(predicados, firma exigible, side effects, SLA, metadatos, requisitos
documentales, webhooks y reportes) y reconstruirlas a mano garantiza olvidar
alguna.

Los estados y las transiciones NO se declaran aquí: viven en
`spec/flujos/solicitud_constancia.json` y se siembran por data migration.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from sinpapel import workflow_enabled
from sinpapel.mixins import CampoMetadato, MetadatosCapturables, Trazable

from apps.core.folios import generar_folio

TIPO_ESTUDIOS = "ESTUDIOS"
TIPO_RESIDENCIA = "RESIDENCIA"
TIPO_INGRESOS = "INGRESOS"
TIPOS_CONSTANCIA = [TIPO_ESTUDIOS, TIPO_RESIDENCIA, TIPO_INGRESOS]


@workflow_enabled(
    state_field="estado",
    workflow_key="solicitud_constancia",
    expose_endpoints=True,
    endpoint_slug="solicitudes-constancia",
)
class SolicitudConstancia(MetadatosCapturables, Trazable):
    """Solicitud de una constancia ante una dependencia.

    Hereda `Trazable` porque `@workflow_enabled` lo exige: el motor persiste
    cada transición con `save(update_fields=[state_field, "actualizado"])` y
    valida el contrato en tiempo de decoración.
    """

    # Ojo con `requerido=True`: `MetadatosCapturables.save()` llama a `clean()`
    # en CADA guardado, incluido el que hace el motor al transicionar. Un campo
    # requerido que solo se conoce al final del trámite (el motivo del rechazo)
    # haría imposible guardar la instancia desde el principio, así que su
    # obligatoriedad se enforca con un predicado sobre la transición y no aquí.
    SCHEMA_METADATOS = [
        CampoMetadato(
            nombre="curp",
            tipo=str,
            requerido=True,
            etiqueta=_("CURP"),
            ayuda=_("18 caracteres, como aparece en el documento oficial."),
        ),
        # Sin `requerido=True` a propósito, aunque el valor sea obligatorio en
        # la práctica: con `default`, `MetadatosProxy.errores()` nunca lo ve
        # vacío, así que la marca no aporta nada — y `MetaFormFactory
        # .build_serializer()` pasa ambos a DRF, que rechaza la combinación con
        # "May not set both `required` and `default`". El resultado sería un 500
        # en GET/PATCH de /metadatos/ para TODO el trámite.
        CampoMetadato(
            nombre="tipo_constancia",
            tipo=str,
            choices=TIPOS_CONSTANCIA,
            default=TIPO_ESTUDIOS,
            etiqueta=_("Tipo de constancia"),
        ),
        CampoMetadato(
            nombre="requisitos_confirmados",
            tipo=bool,
            default=False,
            etiqueta=_("Requisitos cotejados"),
            ayuda=_("Lo marca ventanilla tras cotejar los documentos físicos."),
        ),
        CampoMetadato(
            nombre="motivo_rechazo",
            tipo=str,
            etiqueta=_("Motivo del rechazo"),
            ayuda=_("Obligatorio para resolver desfavorablemente."),
        ),
    ]

    folio = models.CharField(_("Folio"), max_length=50, unique=True, editable=False)
    solicitante = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        related_name="solicitudes_constancia",
        verbose_name=_("Solicitante"),
    )
    dependencia = models.ForeignKey(
        "cuentas.Dependencia",
        on_delete=models.PROTECT,
        related_name="solicitudes_constancia",
        verbose_name=_("Dependencia que atiende"),
    )
    estado = models.ForeignKey(
        "sinpapel.Estado",
        # PROTECT: jamás borres expedientes porque alguien depure el catálogo
        # de estados.
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("Estado"),
    )
    alerta_sla = models.BooleanField(
        _("Vencida por SLA"),
        default=False,
        help_text=_("La activa el SLAEngine cuando la solicitud excede el plazo."),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Solicitud de constancia")
        verbose_name_plural = _("Solicitudes de constancia")
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["dependencia", "estado"]),
            models.Index(fields=["solicitante", "-creado"]),
        ]

    def __str__(self) -> str:
        return f"{self.folio} ({self.estado.nombre})"

    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = generar_folio(type(self), "SC")
        super().save(*args, **kwargs)

    def resolve_workflow_version(self):
        """Resuelve el flujo activo de este trámite.

        `@workflow_enabled` no declara `version_field`, así que el motor
        invoca este método. Sin él, las consultas a `ConfiguracionTransicion`
        no filtrarían por flujo y un sistema con varias versiones daría
        transiciones ambiguas.
        """
        from sinpapel.cache import get_active_version_flujo

        return get_active_version_flujo("solicitud_constancia")
