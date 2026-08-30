"""API de dominio del trámite.

`sinpapel-drf` genera las acciones del *workflow* (transiciones, historial,
documentos, requisitos…) pero no un CRUD: su `WorkflowViewSet` es un
`GenericViewSet` sin `list` ni `create`. Este módulo aporta lo que falta para
operar el trámite desde el frontend.

Se monta bajo un prefijo propio (`/api/tramite/`) y con un `basename` distinto
para no colisionar con el `SinpapelRouter`, que ya publica el mismo modelo en
`/sinpapel/api/solicitudes-constancia/`.

Aquí es donde la visibilidad por adscripción se vuelve efectiva: el motor
valida el **rol** (vía `grupos_permitidos`), y este queryset acota **sobre qué
expedientes**.
"""

from django.core.exceptions import ValidationError as ValidationErrorDjango
from django.db.models import QuerySet
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from sinpapel.cache import get_estado_by_name

from apps.cuentas.models import ROL_SOLICITANTE
from apps.tramite_ejemplo.models import SolicitudConstancia

ESTADO_INICIAL = "BORRADOR"


class EstadoSerializer(serializers.Serializer):
    """Proyección mínima del estado para pintar la bandeja."""

    nombre = serializers.CharField()
    color = serializers.CharField()
    icono = serializers.CharField()


class SolicitudConstanciaSerializer(serializers.ModelSerializer):
    estado = EstadoSerializer(read_only=True)
    solicitante = serializers.StringRelatedField(read_only=True)
    dependencia_nombre = serializers.CharField(source="dependencia.nombre", read_only=True)
    metadatos = serializers.SerializerMethodField()
    puede_evaluar_sla = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudConstancia
        fields = [
            "id",
            "folio",
            "estado",
            "solicitante",
            "dependencia",
            "dependencia_nombre",
            "alerta_sla",
            "puede_evaluar_sla",
            "metadatos",
            "creado",
            "actualizado",
        ]
        read_only_fields = ["id", "folio", "estado", "solicitante", "alerta_sla"]

    def get_metadatos(self, obj) -> dict:
        return obj.meta.to_dict()

    def get_puede_evaluar_sla(self, obj) -> bool:
        """¿La UI debe ofrecer la pestaña de SLA?

        El endpoint `sla-status` de sinpapel-drf exige `IsAdminUser`, así que
        mostrarla a quien no es staff solo produciría un 403 al abrirla.
        """
        usuario = getattr(self.context.get("request"), "user", None)
        return bool(usuario and usuario.is_staff)


class SolicitudConstanciaCrearSerializer(serializers.ModelSerializer):
    """Alta de una solicitud.

    Los metadatos se reciben como bloque y se asignan campo por campo: el proxy
    `.meta` no es dict-like y valida cada asignación contra `SCHEMA_METADATOS`.
    """

    metadatos = serializers.DictField(write_only=True)

    class Meta:
        model = SolicitudConstancia
        fields = ["id", "dependencia", "metadatos"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        metadatos = validated_data.pop("metadatos", {})
        solicitud = SolicitudConstancia(
            solicitante=self.context["request"].user,
            estado=get_estado_by_name(ESTADO_INICIAL),
            **validated_data,
        )
        for nombre, valor in metadatos.items():
            # El proxy valida cada asignación: campo fuera del schema
            # (AttributeError), tipo equivocado (TypeError) o valor fuera de
            # `choices` (ValueError).
            try:
                setattr(solicitud.meta, nombre, valor)
            except (AttributeError, TypeError, ValueError) as exc:
                raise serializers.ValidationError({nombre: str(exc)}) from exc

        # `MetadatosCapturables.save()` llama a `clean()`, que levanta el
        # ValidationError de Django si falta un metadato requerido. DRF no lo
        # reconoce, así que sin traducirlo el alta respondería 500 en vez de
        # 400.
        try:
            solicitud.save()
        except ValidationErrorDjango as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return solicitud


class SolicitudConstanciaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Bandeja y alta de solicitudes, acotadas por rol y adscripción."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return SolicitudConstanciaCrearSerializer
        return SolicitudConstanciaSerializer

    def get_queryset(self) -> QuerySet[SolicitudConstancia]:
        """Acota el expediente visible.

        - Administración (`is_staff`) ve todo.
        - Quien solo es solicitante ve exclusivamente lo suyo, sin importar a
          qué dependencia esté adscrito.
        - El resto del personal ve lo de las dependencias donde tiene
          adscripción vigente, incluidas las subordinadas.
        """
        base = SolicitudConstancia.objects.select_related("estado", "solicitante", "dependencia")
        usuario = self.request.user

        if usuario.is_staff:
            return base

        if usuario.tiene_rol(ROL_SOLICITANTE) and not usuario.tiene_rol(
            "ventanilla", "revisor", "firmante"
        ):
            return base.filter(solicitante=usuario)

        return base.filter(dependencia__in=usuario.dependencias_visibles())
