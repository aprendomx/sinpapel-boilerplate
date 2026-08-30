"""Comprueba que el gate `parity` falla ante cada tipo de deriva.

Un gate que solo se ve pasar no prueba nada: hay que verlo fallar por las
razones correctas.
"""

import pytest
from django.contrib.auth.models import Group
from sinpapel.models import ConfiguracionTransicion, Estado, SLAConfiguracion, VersionFlujo

pytestmark = pytest.mark.django_db

from tests.parity.test_parity import (  # noqa: E402
    test_lo_sembrado_coincide_con_el_json as comprobar,
)

NOMBRE = "solicitud_constancia"


def _falla(mensaje_esperado: str):
    with pytest.raises(AssertionError) as exc:
        comprobar(NOMBRE)
    assert mensaje_esperado in str(exc.value), str(exc.value)[:400]


def test_detecta_una_transicion_extra():
    flujo = VersionFlujo.objects.get(nombre=NOMBRE)
    ConfiguracionTransicion.objects.create(
        flujo=flujo,
        estado_origen=Estado.objects.get(nombre="BORRADOR"),
        estado_destino=Estado.objects.get(nombre="APROBADA"),
    )
    _falla("flujo.transiciones")


def test_detecta_que_se_apago_requiere_firma():
    ConfiguracionTransicion.objects.filter(
        flujo__nombre=NOMBRE,
        estado_origen__nombre="EN_REVISION",
        estado_destino__nombre="APROBADA",
    ).update(requiere_firma=False)
    _falla("requiere_firma")


def test_detecta_un_grupo_permitido_cambiado():
    t = ConfiguracionTransicion.objects.get(
        flujo__nombre=NOMBRE,
        estado_origen__nombre="BORRADOR",
        estado_destino__nombre="RECIBIDA",
    )
    t.grupos_permitidos.add(Group.objects.get(name="admin"))
    _falla("grupos_permitidos")


def test_detecta_un_color_de_estado_cambiado():
    Estado.objects.filter(nombre="APROBADA").update(color="#000000")
    _falla("color")


def test_detecta_un_sla_modificado():
    SLAConfiguracion.objects.filter(estado__nombre="EN_REVISION").update(dias_maximos=99)
    _falla("dias_maximos")


def test_detecta_una_condicion_borrada():
    from sinpapel.models import CondicionTransicion

    CondicionTransicion.objects.filter(transicion__estado_origen__nombre="RECIBIDA").delete()
    _falla("condiciones")


def test_detecta_un_requisito_documental_relajado():
    from sinpapel.models import RequisitoEstadoDocumento

    RequisitoEstadoDocumento.objects.filter(tipo_documento__nombre="Identificación oficial").update(
        porcentaje=50
    )
    _falla("porcentaje")


# ─── Gate `roundtrip` ────────────────────────────────────────────────────────


def test_roundtrip_detecta_que_el_serializador_deja_de_emitir_requiere_firma(monkeypatch):
    """Reproduce el bug real de sinpapel 0.8.0–0.8.1.

    `requiere_firma` existía en el modelo pero `serialize_flujo` no lo emitía,
    así que cada paso por el designer apagaba en silencio la exigencia de firma.
    Se simula recortando la clave del payload exportado, que es exactamente lo
    que producía aquel serializador.
    """
    import json as _json

    from sinpapel.schemas import flujo_export

    original = flujo_export.serialize_flujo

    def serializar_sin_requiere_firma(flujo, **kwargs):
        datos = _json.loads(_json.dumps(original(flujo, **kwargs)))
        for transicion in datos["flujo"]["transiciones"]:
            transicion.pop("requiere_firma", None)
        return datos

    monkeypatch.setattr(
        "tests.parity.test_roundtrip.serialize_flujo", serializar_sin_requiere_firma
    )

    from tests.parity.test_roundtrip import test_el_ciclo_preserva_requiere_firma

    with pytest.raises(AssertionError):
        test_el_ciclo_preserva_requiere_firma(NOMBRE)


def test_roundtrip_detecta_un_requisito_que_no_sobrevive(monkeypatch):
    """Un requisito documental perdido en el ciclo tiene que romper el gate.

    Se ejercita contra el test que compara con el JSON del repositorio, no con
    el que compara exportación contra exportación: ése tiene un punto ciego
    para esta clase de fallo (ver la nota en `test_roundtrip`).
    """
    import json as _json

    from sinpapel.schemas import flujo_export

    original = flujo_export.serialize_flujo

    def serializar_sin_requisitos(flujo, **kwargs):
        datos = _json.loads(_json.dumps(original(flujo, **kwargs)))
        datos["flujo"]["requisitos"] = []
        return datos

    monkeypatch.setattr("tests.parity.test_roundtrip.serialize_flujo", serializar_sin_requisitos)

    from tests.parity.test_roundtrip import (
        test_el_json_del_repositorio_se_importa_sin_perdidas,
    )

    with pytest.raises(AssertionError, match="requisitos"):
        test_el_json_del_repositorio_se_importa_sin_perdidas(NOMBRE)
