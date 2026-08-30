"""API de intercambio con el designer.

`sinpapel-designer` es una SPA standalone: guarda en `localStorage` y hace
round-trip por archivo (descarga / arrastra-y-suelta). Su integración con un
backend es manual por diseño — el embebido por `iframe` está en su roadmap, no
implementado.

Estos endpoints cubren ese hueco sin inventar un protocolo: exponen los
`spec/flujos/*.json` para alimentarlo y aceptan el JSON editado de vuelta. El
formato es el mismo v0.2 que el designer importa y exporta, así que el flujo de
trabajo es: descargar de aquí → editar en el designer → exportar → subir aquí.
"""

from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.spec_io import services


class GuardarFlujoSerializer(serializers.Serializer):
    """El payload es el JSON v0.2 completo, tal como lo exporta el designer."""

    schema_version = serializers.CharField()
    flujo = serializers.DictField()
    catalogos = serializers.DictField(required=False)
    exported_at = serializers.CharField(required=False, allow_blank=True)


class FlujosView(APIView):
    """Flujos declarados en `spec/flujos/`, y si se pueden editar."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {
                "flujos": services.listar_flujos(),
                # La UI necesita saberlo para no ofrecer un guardado que el
                # servidor va a rechazar.
                "escritura_habilitada": services.escritura_habilitada(),
            }
        )


class FlujoView(APIView):
    """Lectura y guardado de un flujo concreto."""

    permission_classes = [IsAdminUser]

    def get(self, request, nombre: str):
        """Devuelve el JSON de `spec/flujos/<nombre>.json`.

        Con `?desde=db` devuelve en cambio lo que hay sembrado en la base, que
        es lo que permite arrancar el designer desde el estado real del sistema.
        """
        origen = request.query_params.get("desde", "spec")
        try:
            if origen == "db":
                return Response(services.exportar_desde_db(nombre))
            return Response(services.leer_flujo(nombre))
        except services.NombreInvalido as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except services.FlujoNoEncontrado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, nombre: str):
        """Guarda el flujo editado en `spec/flujos/<nombre>.json`.

        Solo escribe con `DEBUG=True`. Lo que se guarda es el archivo, no la
        base: el cambio entra a git, se revisa y se aplica con una migración.
        """
        serializador = GuardarFlujoSerializer(data=request.data)
        serializador.is_valid(raise_exception=True)

        try:
            cambio = services.escribir_flujo(nombre, request.data)
        except services.EscrituraDeshabilitada as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except services.NombreInvalido as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "guardado": True,
                "cambio": cambio,
                "ruta": f"spec/flujos/{nombre}.json",
                "siguiente_paso": (
                    "Revisa el diff y aplica el cambio con una data migration; "
                    "el gate `parity` falla mientras la base no coincida."
                    if cambio
                    else "El archivo ya estaba al día."
                ),
            }
        )
