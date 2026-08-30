"""Catálogos de cuentas expuestos al frontend."""

from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.cuentas.models import Dependencia


class DependenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependencia
        fields = ["id", "clave", "nombre"]


class DependenciaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Solo lectura: el alta de dependencias es tarea del admin de Django."""

    permission_classes = [IsAuthenticated]
    serializer_class = DependenciaSerializer
    queryset = Dependencia.objects.filter(activa=True)
