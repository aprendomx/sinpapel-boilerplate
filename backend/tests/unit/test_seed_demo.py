"""El comando `seed_demo`, que es lo que consume `make seed`.

No son datos decorativos: de estas cuentas dependen el e2e y su preflight, así
que cuando el comando falla el síntoma aparece lejos —un timeout esperando una
pantalla que nunca llega—. Los casos que importan son la idempotencia y la
negativa a correr fuera de DEBUG.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.cuentas.models import Adscripcion, Dependencia

pytestmark = pytest.mark.django_db

CUENTAS = ["ana", "beto", "carla", "diana", "elena"]


@pytest.fixture
def en_debug(settings):
    """El comando exige DEBUG: crea cuentas con una contraseña conocida."""
    settings.DEBUG = True


def test_siembra_una_cuenta_por_rol_y_su_dependencia(en_debug):
    call_command("seed_demo", verbosity=0)

    Usuario = get_user_model()
    assert Dependencia.objects.filter(clave="DGA").count() == 1
    for username in CUENTAS:
        usuario = Usuario.objects.get(username=username)
        assert usuario.groups.count() == 1
        assert Adscripcion.objects.filter(usuario=usuario).exists()


def test_solo_la_cuenta_de_administracion_es_staff(en_debug):
    """De los cinco roles solo uno entra al admin de Django."""
    call_command("seed_demo", verbosity=0)

    Usuario = get_user_model()
    staff = set(Usuario.objects.filter(is_staff=True).values_list("username", flat=True))

    assert staff == {"elena"}


def test_correr_dos_veces_no_duplica_nada(en_debug):
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    Usuario = get_user_model()
    assert Usuario.objects.filter(username__in=CUENTAS).count() == len(CUENTAS)
    assert Dependencia.objects.filter(clave="DGA").count() == 1
    assert Adscripcion.objects.filter(usuario__username="ana").count() == 1


def test_repone_la_contrasena_de_una_cuenta_ya_existente(en_debug):
    """El caso que motivó el arreglo: `make seed` tiene que reparar, no solo crear.

    Si la contraseña solo se fijara al crear la cuenta, una cuenta con la clave
    cambiada quedaría rota para siempre y el consejo que da el preflight del
    e2e —«corre make seed»— no arreglaría nada.
    """
    call_command("seed_demo", verbosity=0)
    Usuario = get_user_model()
    ana = Usuario.objects.get(username="ana")
    ana.set_password("otra-cosa")
    ana.is_active = False
    ana.save()

    call_command("seed_demo", verbosity=0)

    ana.refresh_from_db()
    assert ana.check_password("demo12345")
    assert ana.is_active


def test_se_niega_fuera_de_debug(settings):
    """Contraseñas conocidas: en producción las cuentas se dan de alta a mano."""
    settings.DEBUG = False

    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_demo", verbosity=0)

    assert not get_user_model().objects.filter(username="ana").exists()


def test_con_solicitud_crea_un_borrador(en_debug):
    from apps.tramite_ejemplo.models import SolicitudConstancia

    call_command("seed_demo", "--con-solicitud", verbosity=0)

    solicitud = SolicitudConstancia.objects.get()
    assert solicitud.estado.nombre == "BORRADOR"
    assert solicitud.solicitante.username == "ana"
    assert solicitud.meta.curp == "AEAA010101HDFXXX09"
