"""Health check: es lo que consulta el orquestador para decidir si el
contenedor está listo."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_salud_reporta_ok_con_base_de_datos_disponible(client):
    respuesta = client.get(reverse("salud"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base_datos": "ok"}
