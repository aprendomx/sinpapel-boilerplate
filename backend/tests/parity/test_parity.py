"""Gate `parity`: la base de datos coincide con `spec/flujos/*.json`.

Este es el gate que impide la deriva. Los estados y las transiciones son datos,
no código, y su verdad vive en `spec/flujos/`. Un agente (o una persona) puede
añadir una transición por el admin, tocar la migración de siembra o editar el
JSON sin volver a sembrar: en los tres casos el sistema en ejecución deja de
ser el que está declarado en el repositorio, y nada más lo detectaría.

La comparación es exhaustiva a propósito: se exporta el flujo sembrado con la
misma API de portabilidad del framework y se compara, en forma canónica, contra
el archivo. Así el gate cubre todo lo que el schema v0.2 sabe representar
—estados, etapas, grupos, tipos de documento, transiciones, grupos permitidos,
`requiere_firma`, condiciones, requisitos y SLAs— sin enumerarlo campo por
campo, que es como se olvida uno.
"""

import json

import pytest
from sinpapel.models import VersionFlujo
from sinpapel.schemas.flujo_export import serialize_flujo

from apps.spec_io.canonical import canonizar, describir, diferencias
from apps.spec_io.services import directorio_flujos, listar_flujos

pytestmark = pytest.mark.django_db


def _archivos() -> list[str]:
    nombres = listar_flujos()
    assert nombres, (
        "No hay ningún flujo en spec/flujos/. El gate `parity` no verifica nada "
        "si el directorio está vacío, así que un descuido ahí lo dejaría pasar "
        "en falso."
    )
    return nombres


@pytest.mark.parametrize("nombre", _archivos())
def test_lo_sembrado_coincide_con_el_json(nombre):
    """Lo que hay en la base exporta exactamente al archivo declarado."""
    declarado = json.loads((directorio_flujos() / f"{nombre}.json").read_text(encoding="utf-8"))

    flujo = VersionFlujo.objects.filter(nombre=nombre).first()
    assert flujo is not None, (
        f"spec/flujos/{nombre}.json declara el flujo '{nombre}' pero no está "
        "sembrado. Falta la data migration que lo importe."
    )

    exportado = serialize_flujo(flujo, inline_catalogs=True)
    problemas = diferencias(canonizar(declarado), canonizar(exportado))

    assert not problemas, (
        f"La base de datos y spec/flujos/{nombre}.json han divergido:\n"
        f"{describir(problemas)}\n\n"
        "Si el cambio es intencional, actualiza el JSON y siembra la nueva "
        "versión con una data migration. Nunca al revés."
    )


@pytest.mark.parametrize("nombre", _archivos())
def test_el_flujo_declarado_activo_esta_activo(nombre):
    """Un flujo inactivo no resuelve transiciones aunque exista.

    `deserialize_flujo` ignora la clave `activo` del JSON y usa su propio
    parámetro, con default `False`. Es fácil sembrar un flujo que existe pero
    no se aplica a nada.
    """
    declarado = json.loads((directorio_flujos() / f"{nombre}.json").read_text(encoding="utf-8"))
    if not declarado["flujo"].get("activo"):
        pytest.skip(f"El flujo '{nombre}' no se declara activo.")

    activos = VersionFlujo.objects.filter(nombre=nombre, activo=True).count()

    assert activos == 1, (
        f"spec/flujos/{nombre}.json se declara activo, pero hay {activos} "
        "versiones activas con ese nombre en la base."
    )


@pytest.mark.parametrize("nombre", _archivos())
def test_cada_flujo_tiene_un_modelo_que_lo_use(nombre):
    """El `nombre` del flujo es la clave con la que el modelo lo resuelve.

    Sin un modelo decorado que use esa key, el flujo está sembrado pero muerto:
    ninguna instancia lo consultaría nunca.
    """
    from sinpapel.registry import WorkflowRegistry

    assert nombre in WorkflowRegistry.list_keys(), (
        f"Ningún modelo declara `workflow_key='{nombre}'`. El flujo está "
        "sembrado pero no lo usa nadie."
    )


def test_no_hay_flujos_sembrados_sin_declarar():
    """Todo flujo en la base tiene su archivo en `spec/flujos/`.

    Cubre la deriva en el otro sentido: alguien importó un flujo por la API de
    administración y nunca lo bajó al repositorio.
    """
    declarados = set(listar_flujos())
    sembrados = set(VersionFlujo.objects.values_list("nombre", flat=True))

    huerfanos = sembrados - declarados

    assert not huerfanos, (
        f"Hay flujos en la base que no están declarados en spec/flujos/: "
        f"{sorted(huerfanos)}. Expórtalos con "
        "`GET /designer/api/flujos/<nombre>/?desde=db` y commitea el archivo."
    )
