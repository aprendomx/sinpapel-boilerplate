"""Intercambio de flujos con el designer y su ruta protegida."""

import json

import pytest
from rest_framework.test import APIClient

from apps.spec_io import services

pytestmark = pytest.mark.django_db

BASE = "/designer/api/flujos"
FLUJO = "solicitud_constancia"


def _cliente(usuario) -> APIClient:
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente


@pytest.fixture
def spec_temporal(tmp_path, settings):
    """Aísla `spec/` en un directorio temporal.

    Sin esto, un test de guardado reescribiría los flujos reales del repo.
    """
    flujos = tmp_path / "flujos"
    flujos.mkdir(parents=True)
    settings.SPEC_DIR = tmp_path
    return flujos


# ─── Permisos ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("fixture_usuario", ["solicitante", "ventanilla", "revisor", "firmante"])
def test_solo_administracion_lista_flujos(request, fixture_usuario):
    """El designer edita la definición de los trámites: no es para operarlos."""
    usuario = request.getfixturevalue(fixture_usuario)

    assert _cliente(usuario).get(f"{BASE}/").status_code == 403


def test_administracion_lista_los_flujos(administrador):
    respuesta = _cliente(administrador).get(f"{BASE}/")

    assert respuesta.status_code == 200
    assert FLUJO in respuesta.json()["flujos"]


# ─── Lectura ────────────────────────────────────────────────────────────────


def test_lee_el_json_del_repositorio(administrador):
    respuesta = _cliente(administrador).get(f"{BASE}/{FLUJO}/")

    datos = respuesta.json()
    assert respuesta.status_code == 200
    assert datos["schema_version"] == "0.2"
    assert datos["flujo"]["nombre"] == FLUJO


def test_exporta_desde_la_base(administrador):
    """`?desde=db` arranca el designer con el estado real del sistema."""
    respuesta = _cliente(administrador).get(f"{BASE}/{FLUJO}/?desde=db")

    datos = respuesta.json()
    assert respuesta.status_code == 200
    aristas = {
        (t["estado_origen"], t["estado_destino"]): t["requiere_firma"]
        for t in datos["flujo"]["transiciones"]
    }
    assert aristas[("EN_REVISION", "APROBADA")] is True


def test_un_flujo_inexistente_da_404(administrador):
    assert _cliente(administrador).get(f"{BASE}/no_existe/").status_code == 404


@pytest.mark.parametrize("nombre", ["MAYUSCULAS", "con espacio", "con-guion", "punto.json"])
def test_un_nombre_invalido_se_rechaza(administrador, nombre):
    """El nombre se usa para construir una ruta: no puede ser arbitrario."""
    respuesta = _cliente(administrador).get(f"{BASE}/{nombre}/")

    assert respuesta.status_code == 400


@pytest.mark.parametrize("intento", ["../secretos", "../../config/settings/base.py"])
def test_un_intento_de_traversal_no_filtra_nada(administrador, intento):
    """Estas rutas ni siquiera alcanzan la API: las absorbe el catch-all del
    designer, que resuelve el recurso y descarta cualquiera fuera de su `dist`.

    Se comprueba el resultado observable —que no salga contenido del servidor—
    en vez del código concreto, que depende de qué ruta lo atienda.
    """
    respuesta = _cliente(administrador).get(f"{BASE}/{intento}/")

    assert respuesta.status_code in (302, 400, 404, 503)
    assert b"SECRET_KEY" not in respuesta.content
    assert b"schema_version" not in respuesta.content


def test_leer_un_nombre_invalido_falla_en_el_servicio():
    """Defensa en profundidad: el servicio valida aunque la vista ya filtre."""
    with pytest.raises(services.NombreInvalido):
        services.leer_flujo("../../etc/passwd")


# ─── Escritura ──────────────────────────────────────────────────────────────


def test_guarda_el_flujo_editado(administrador, spec_temporal, settings):
    settings.DEBUG = True
    (spec_temporal / f"{FLUJO}.json").write_text(
        json.dumps({"schema_version": "0.2", "flujo": {"nombre": FLUJO, "transiciones": []}}),
        encoding="utf-8",
    )
    editado = {
        "schema_version": "0.2",
        "flujo": {"nombre": FLUJO, "transiciones": [], "descripcion": "editado"},
    }

    respuesta = _cliente(administrador).put(f"{BASE}/{FLUJO}/", editado, format="json")

    assert respuesta.status_code == 200
    assert respuesta.json()["cambio"] is True
    guardado = json.loads((spec_temporal / f"{FLUJO}.json").read_text(encoding="utf-8"))
    assert guardado["flujo"]["descripcion"] == "editado"


def test_guardar_lo_mismo_no_toca_el_archivo(administrador, spec_temporal, settings):
    """Reexportar sin cambios no debe producir un commit vacío."""
    settings.DEBUG = True
    contenido = {
        "schema_version": "0.2",
        "flujo": {"nombre": FLUJO, "transiciones": [], "requisitos": []},
    }
    (spec_temporal / f"{FLUJO}.json").write_text(json.dumps(contenido), encoding="utf-8")

    # Mismo flujo, listas en otro orden y con `exported_at`: sigue siendo igual.
    respuesta = _cliente(administrador).put(
        f"{BASE}/{FLUJO}/",
        {**contenido, "exported_at": "2026-01-01T00:00:00+00:00"},
        format="json",
    )

    assert respuesta.json()["cambio"] is False


def test_en_produccion_no_se_escribe(administrador, spec_temporal, settings):
    """El directorio se monta read-only: un cambio en caliente saltaría la revisión."""
    settings.DEBUG = False

    respuesta = _cliente(administrador).put(
        f"{BASE}/{FLUJO}/",
        {"schema_version": "0.2", "flujo": {"nombre": FLUJO, "transiciones": []}},
        format="json",
    )

    assert respuesta.status_code == 403
    assert not (spec_temporal / f"{FLUJO}.json").exists()


def test_el_listado_anuncia_si_se_puede_escribir(administrador, settings):
    """La UI lo necesita para no ofrecer un guardado que el servidor rechaza."""
    settings.DEBUG = False
    assert _cliente(administrador).get(f"{BASE}/").json()["escritura_habilitada"] is False

    settings.DEBUG = True
    assert _cliente(administrador).get(f"{BASE}/").json()["escritura_habilitada"] is True


def test_un_payload_que_no_es_un_flujo_se_rechaza(administrador, spec_temporal, settings):
    settings.DEBUG = True

    respuesta = _cliente(administrador).put(
        f"{BASE}/{FLUJO}/", {"cualquier": "cosa"}, format="json"
    )

    assert respuesta.status_code == 400


def test_escribir_fuera_del_directorio_es_imposible(settings, spec_temporal):
    """Defensa en profundidad: el servicio valida aunque la vista ya filtre."""
    settings.DEBUG = True

    with pytest.raises(services.NombreInvalido):
        services.escribir_flujo("../fuera", {"schema_version": "0.2"})


# ─── Ruta del designer ──────────────────────────────────────────────────────


def test_el_designer_exige_staff(client, solicitante):
    """Sin staff, la ruta redirige al login del admin en vez de servir la SPA."""
    client.force_login(solicitante)

    respuesta = client.get("/designer/")

    assert respuesta.status_code == 302
    assert "/admin/login/" in respuesta["Location"]


def test_el_designer_explica_como_construirse_si_falta(client, administrador):
    """Su salida no se versiona: sin `make designer` no hay bundle que servir."""
    client.force_login(administrador)

    respuesta = client.get("/designer/")

    # 503 si no está construido; 200 si alguien ya corrió `make designer`.
    assert respuesta.status_code in (200, 503)
    if respuesta.status_code == 503:
        assert b"make designer" in respuesta.content
