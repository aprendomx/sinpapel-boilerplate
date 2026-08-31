"""La vista que sirve el bundle del designer.

Importa sobre todo el guardia contra escapes del directorio: la vista recibe la
ruta del recurso desde la URL y la resuelve contra `DIST`, así que sin esa
comprobación cualquiera con una cuenta staff podría leer archivos arbitrarios
del servidor pasando `../`.

El bundle no se versiona —se construye con `make designer`—, así que los tests
montan uno de mentira en un `tmp_path` y apuntan `DIST` ahí. De otro modo estos
casos dependerían de si alguien construyó el designer antes de correr la suite.
"""

import pytest
from django.test import Client

from apps.spec_io import views

pytestmark = pytest.mark.django_db


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    """Un `designer/dist/spa/` mínimo, con un recurso además del index."""
    dist = tmp_path / "spa"
    dist.mkdir()
    (dist / "index.html").write_text("<html>designer</html>", encoding="utf-8")
    (dist / "app.js").write_text("console.log('spa')", encoding="utf-8")
    monkeypatch.setattr(views, "DIST", dist)
    return dist


@pytest.fixture
def cliente_staff(administrador):
    cliente = Client()
    cliente.force_login(administrador)
    return cliente


def test_sirve_un_recurso_del_bundle(cliente_staff, bundle):
    respuesta = cliente_staff.get("/designer/app.js")

    assert respuesta.status_code == 200
    assert b"console.log" in b"".join(respuesta.streaming_content)


def test_una_ruta_desconocida_cae_en_el_index(cliente_staff, bundle):
    """La SPA resuelve su propio enrutado: todo lo que no es archivo es index."""
    respuesta = cliente_staff.get("/designer/flujos/solicitud_constancia")

    assert respuesta.status_code == 200
    assert b"designer" in b"".join(respuesta.streaming_content)


def test_no_sirve_archivos_fuera_del_dist(cliente_staff, bundle, tmp_path):
    """El caso que justifica el guardia: `../` no puede sacar nada del dist.

    El secreto se coloca en el padre del bundle, que es exactamente donde
    apuntaría un escape de un nivel. La vista no lo devuelve: cae en el index,
    igual que cualquier ruta desconocida.
    """
    secreto = tmp_path / "secreto.txt"
    secreto.write_text("SECRET_KEY=no-debe-salir", encoding="utf-8")

    respuesta = cliente_staff.get("/designer/../secreto.txt")
    cuerpo = b"".join(respuesta.streaming_content)

    assert b"no-debe-salir" not in cuerpo
    assert b"designer" in cuerpo


def test_el_guardia_rechaza_el_escape_directamente(bundle, tmp_path):
    """Sin pasar por el enrutador, que normaliza parte de las rutas.

    Django colapsa algunos `..` antes de llegar a la vista, así que el test por
    HTTP no basta para saber si el guardia funciona: podría estar pasando por
    la normalización y no por la comprobación. Aquí se llama a la función.
    """
    (tmp_path / "secreto.txt").write_text("x", encoding="utf-8")

    assert views._archivo_dentro_del_dist("../secreto.txt") is None
    assert views._archivo_dentro_del_dist("app.js") is not None


def test_un_directorio_no_es_un_recurso(bundle):
    """`is_file()` también descarta directorios, no solo lo inexistente."""
    (bundle / "assets").mkdir()

    assert views._archivo_dentro_del_dist("assets") is None


def test_sin_bundle_construido_responde_503(cliente_staff, tmp_path, monkeypatch):
    """Un 503 con instrucciones vale más que un 500: falta `make designer`."""
    monkeypatch.setattr(views, "DIST", tmp_path / "no-existe")

    respuesta = cliente_staff.get("/designer/")

    assert respuesta.status_code == 503
    assert "make designer" in respuesta.content.decode()


def test_bundle_sin_index_responde_404(cliente_staff, tmp_path, monkeypatch):
    """Un dist a medias no es lo mismo que un dist ausente."""
    dist = tmp_path / "spa"
    dist.mkdir()
    monkeypatch.setattr(views, "DIST", dist)

    assert cliente_staff.get("/designer/").status_code == 404


def test_exige_cuenta_staff(client, bundle, solicitante):
    """El designer edita la definición de los trámites: no basta con entrar."""
    client.force_login(solicitante)

    respuesta = client.get("/designer/")

    assert respuesta.status_code == 302
    assert "/admin/login/" in respuesta["Location"]
