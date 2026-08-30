"""Las URLConf de los paquetes del ecosistema están montadas.

Un `include` mal escrito no falla al importar: falla con 404 la primera vez que
alguien llama la API, ya en integración.
"""

from django.urls import resolve, reverse


def test_endpoints_de_portabilidad_de_flujos_montados():
    """Los usa el designer para exportar/importar (JSON v0.2)."""
    assert reverse("flujo-import") == "/sinpapel/api/flujos/import/"
    assert reverse("flujo-export", args=[1]) == "/sinpapel/api/flujos/1/export/"


def test_endpoint_inbound_de_webhooks_montado():
    ruta = reverse("sinpapel_webhooks:inbound", args=["proveedor"])

    assert ruta == "/sinpapel/api/webhooks/in/proveedor/"


def test_endpoints_de_reports_montados():
    """sinpapel-reports se monta aparte de sinpapel-drf."""
    match = resolve("/reports/field-catalog/")

    assert match.func.view_class.__name__ == "FieldCatalogView"
