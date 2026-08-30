"""Fixtures compartidas por la suite.

El cache de sinpapel es process-wide (LocMemCache) mientras que la base de
datos hace rollback entre tests: sin limpiarlo, un test arrastra Estados y
VersionFlujo con IDs de filas ya revertidas.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from sinpapel.cache import clear_all
from sinpapel.models import Documento, Estado, InstanciaDocumento
from sinpapel.signing.factory import reset_backend_cache

from apps.cuentas.models import Adscripcion, Dependencia
from apps.tramite_ejemplo.models import SolicitudConstancia


@pytest.fixture(autouse=True)
def _limpiar_caches_sinpapel():
    clear_all()
    reset_backend_cache()
    yield
    clear_all()
    reset_backend_cache()


@pytest.fixture
def dependencia(db) -> Dependencia:
    return Dependencia.objects.create(clave="DGA", nombre="Dirección General de Atención")


@pytest.fixture
def otra_dependencia(db) -> Dependencia:
    return Dependencia.objects.create(clave="DGJ", nombre="Dirección General Jurídica")


@pytest.fixture
def crear_usuario(db, dependencia):
    """Crea un usuario con un rol y, salvo que se pida otra cosa, adscrito.

    Los roles son grupos de Django sembrados por la migración de `cuentas`, que
    es lo que consume `ConfiguracionTransicion.grupos_permitidos`.
    """

    def _crear(username: str, rol: str, *, adscrito_a: Dependencia | None = dependencia):
        usuario = get_user_model().objects.create_user(username=username, password="x")
        usuario.groups.add(Group.objects.get(name=rol))
        if adscrito_a is not None:
            Adscripcion.objects.create(usuario=usuario, dependencia=adscrito_a)
        return usuario

    return _crear


@pytest.fixture
def solicitante(crear_usuario):
    return crear_usuario("ana", "solicitante")


@pytest.fixture
def ventanilla(crear_usuario):
    return crear_usuario("beto", "ventanilla")


@pytest.fixture
def revisor(crear_usuario):
    return crear_usuario("carla", "revisor")


@pytest.fixture
def firmante(crear_usuario):
    return crear_usuario("diana", "firmante")


@pytest.fixture
def administrador(db, crear_usuario):
    usuario = crear_usuario("elena", "admin")
    usuario.is_staff = True
    usuario.save(update_fields=["is_staff"])
    return usuario


@pytest.fixture
def estados(db) -> dict[str, Estado]:
    """Los estados sembrados desde spec/flujos/solicitud_constancia.json."""
    return {e.nombre: e for e in Estado.objects.all()}


@pytest.fixture
def solicitud(db, solicitante, dependencia, estados) -> SolicitudConstancia:
    """Solicitud recién capturada, en BORRADOR.

    `curp` se asigna antes del primer guardado porque el schema la marca como
    requerida y `MetadatosCapturables.save()` valida en cada `save()`.
    """
    sol = SolicitudConstancia(
        solicitante=solicitante,
        dependencia=dependencia,
        estado=estados["BORRADOR"],
    )
    sol.meta.curp = "AEAA010101HDFXXX09"
    sol.save()
    return sol


@pytest.fixture
def adjuntar_documento(db):
    """Adjunta al expediente un documento del tipo indicado, al 100 %.

    Es lo que satisface un `RequisitoEstadoDocumento`: el motor busca
    `InstanciaDocumento` cuyo `documento.tipo_documento` sea el exigido.
    """

    def _adjuntar(instancia, nombre_tipo: str, porcentaje: int = 100) -> InstanciaDocumento:
        documento = Documento.objects.get(tipo_documento__nombre=nombre_tipo, plantilla="")
        return InstanciaDocumento.objects.create(
            documento=documento,
            target=instancia,
            porcentaje=porcentaje,
        )

    return _adjuntar


@pytest.fixture
def solicitud_recibida(solicitud, solicitante, estados, adjuntar_documento):
    """Solicitud en RECIBIDA con su expediente documental completo."""
    solicitud.transition("RECIBIDA", solicitante)
    adjuntar_documento(solicitud, "Identificación oficial")
    adjuntar_documento(solicitud, "Comprobante de domicilio")
    solicitud.refresh_from_db()
    return solicitud


@pytest.fixture
def solicitud_en_revision(solicitud_recibida, ventanilla):
    """Solicitud en EN_REVISION, con los requisitos ya cotejados por ventanilla."""
    solicitud_recibida.meta.requisitos_confirmados = True
    solicitud_recibida.save()
    solicitud_recibida.transition("EN_REVISION", ventanilla)
    solicitud_recibida.refresh_from_db()
    return solicitud_recibida


@pytest.fixture
def firma_payload():
    """Payload de firma para el backend de pruebas (`FakeBackend`).

    Modo A: el motor invoca al backend configurado con este contenido. En
    producción el backend es FIEL y el contenido es el payload canónico que
    firmó la persona.
    """
    return {"contenido": b"contenido-canonico-de-prueba"}
