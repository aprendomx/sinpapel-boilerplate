"""Fuente de datos para la generación de documentos por plantilla.

`sinpapel-reports` autodescubre este módulo (`autodiscover_modules("reports")`
sobre el nombre `reports`), así que el registro se hace explícito desde
`AppConfig.ready()` para no depender del nombre del archivo.

Dos plantillas, dos caminos distintos del motor:

- **Acuse (PDF)**: se estampa sobre una plantilla en coordenadas, según
  `Documento.configuracion_overlay`.
- **Oficio (DOCX)**: rellena marcadores Jinja de la plantilla; el overlay se
  ignora.
"""

from typing import Any

from sinpapel_reports.data_sources import CampoReporte, register_data_source

# Claves de `Documento.valor` con las que el side effect localiza cada plantilla.
DOCUMENTO_ACUSE = "ACUSE_SOLICITUD_CONSTANCIA"
DOCUMENTO_OFICIO = "OFICIO_RESOLUCION_CONSTANCIA"

FUENTE_DATOS = "solicitud_constancia"


@register_data_source
class SolicitudConstanciaDataSource:
    """Expone los datos de una `SolicitudConstancia` al motor de reportes."""

    name = FUENTE_DATOS

    def get_field_catalog(self) -> list[CampoReporte]:
        """Paleta de campos para el editor visual de overlays."""
        return [
            CampoReporte(key="folio", label="Folio"),
            CampoReporte(key="fecha", label="Fecha de emisión"),
            CampoReporte(key="estado", label="Estado"),
            CampoReporte(key="dependencia", label="Dependencia"),
            CampoReporte(key="solicitante", label="Solicitante", grupo="participantes"),
            CampoReporte(key="curp", label="CURP", grupo="participantes"),
            CampoReporte(key="tipo_constancia", label="Tipo de constancia"),
            CampoReporte(key="motivo_rechazo", label="Motivo del rechazo"),
        ]

    def build_context(self, target: Any) -> dict[str, Any]:
        """Datos a estampar o rellenar para esta solicitud.

        Todos los valores se devuelven como `str`: el renderer de overlay omite
        los valores falsy, así que un `0` o un `None` desaparecerían del
        documento sin avisar.
        """
        meta = target.meta.to_dict()
        return {
            "folio": target.folio,
            "fecha": target.creado.strftime("%d/%m/%Y") if target.creado else "",
            "estado": target.estado.nombre,
            "dependencia": target.dependencia.nombre,
            "solicitante": target.solicitante.get_full_name() or target.solicitante.username,
            "curp": str(meta.get("curp") or ""),
            "tipo_constancia": str(meta.get("tipo_constancia") or ""),
            "motivo_rechazo": str(meta.get("motivo_rechazo") or ""),
        }
