"""Gate `roundtrip`: exportar e importar un flujo no pierde nada.

Es la garantía que hace utilizable al designer. El ciclo real es
base → JSON → designer → JSON → base, y cada salto pasa por
`serialize_flujo` / `deserialize_flujo`. Si ese par pierde un campo, el flujo
editado vuelve mutilado y nadie se entera hasta que una transición se comporta
distinto en producción.

`requiere_firma` es el caso testigo: se añadió en 0.8.0 pero el serializador no
lo emitió hasta 0.8.2, así que durante dos versiones el round-trip apagaba en
silencio la exigencia de firma de cada transición que pasara por el designer.
"""

import json

import pytest
from sinpapel.models import VersionFlujo
from sinpapel.schemas.flujo_export import deserialize_flujo, serialize_flujo

from apps.spec_io.canonical import canonizar, describir, diferencias
from apps.spec_io.services import directorio_flujos, listar_flujos

pytestmark = pytest.mark.django_db

SUFIJO = "_roundtrip"


def _nombres() -> list[str]:
    nombres = listar_flujos()
    assert nombres, "No hay flujos en spec/flujos/; el gate no verificaría nada."
    return nombres


def _reimportar(datos: dict) -> VersionFlujo:
    """Importa el flujo bajo otro nombre y devuelve el resultado.

    Hay que renombrar porque `deserialize_flujo` rechaza un `VersionFlujo`
    cuyo nombre ya existe, y el original sigue sembrado.
    """
    copia = json.loads(json.dumps(datos))
    copia["flujo"]["nombre"] = copia["flujo"]["nombre"] + SUFIJO
    # `activo` no viaja en el payload: el importador usa su propio parámetro,
    # con default False. Se pasa explícito para que el ciclo lo conserve.
    return deserialize_flujo(copia, activo=copia["flujo"]["activo"])


@pytest.mark.parametrize("nombre", _nombres())
def test_el_ciclo_completo_preserva_el_flujo(nombre):
    """base → JSON → base → JSON produce el mismo flujo."""
    original = VersionFlujo.objects.get(nombre=nombre)
    exportado = serialize_flujo(original, inline_catalogs=True)

    # El original se desactiva antes de reimportar: la base solo admite una
    # versión activa por nombre, y sin esto el ciclo no podría conservar
    # `activo=True`.
    VersionFlujo.objects.filter(pk=original.pk).update(activo=False)
    reimportado = _reimportar(exportado)

    reexportado = serialize_flujo(reimportado, inline_catalogs=True)
    # Se devuelve el nombre para que la única diferencia esperada no cuente.
    reexportado["flujo"]["nombre"] = nombre

    problemas = diferencias(canonizar(exportado), canonizar(reexportado))

    assert not problemas, (
        f"El ciclo export→import perdió o alteró datos del flujo '{nombre}':\n"
        f"{describir(problemas)}"
    )


@pytest.mark.parametrize("nombre", _nombres())
def test_el_ciclo_preserva_requiere_firma(nombre):
    """Comprobación explícita del campo que ya se perdió una vez.

    El test anterior lo cubre, pero de forma difusa: si el serializador vuelve
    a dejar de emitirlo, `requiere_firma` desaparecería de AMBOS lados de la
    comparación y el ciclo parecería íntegro. Aquí se contrasta contra la base,
    que es la única fuente que no depende del serializador.
    """
    original = VersionFlujo.objects.get(nombre=nombre)
    esperado = {
        (t.estado_origen.nombre, t.estado_destino.nombre): t.requiere_firma
        for t in original.transiciones.select_related("estado_origen", "estado_destino")
    }

    exportado = serialize_flujo(original, inline_catalogs=True)
    VersionFlujo.objects.filter(pk=original.pk).update(activo=False)
    reimportado = _reimportar(exportado)

    obtenido = {
        (t.estado_origen.nombre, t.estado_destino.nombre): t.requiere_firma
        for t in reimportado.transiciones.select_related("estado_origen", "estado_destino")
    }

    assert obtenido == esperado
    assert any(esperado.values()), (
        f"El flujo '{nombre}' no exige firma en ninguna transición, así que "
        "este gate no está probando nada. Revisa el flujo o retira el test."
    )


@pytest.mark.parametrize("nombre", _nombres())
def test_el_json_del_repositorio_se_importa_sin_perdidas(nombre):
    """El archivo versionado es importable tal cual.

    Éste es el test que cierra el punto ciego de los dos anteriores. Comparar
    una exportación contra otra no detecta que el serializador DEJE de emitir
    un campo: desaparecería de ambos lados y el ciclo parecería íntegro. El
    JSON del repositorio es la única referencia que no pasa por el
    serializador, así que es la que acusa esa clase de regresión.
    """
    declarado = json.loads((directorio_flujos() / f"{nombre}.json").read_text(encoding="utf-8"))

    VersionFlujo.objects.filter(nombre=nombre).update(activo=False)
    importado = _reimportar(declarado)

    reexportado = serialize_flujo(importado, inline_catalogs=True)
    reexportado["flujo"]["nombre"] = nombre
    problemas = diferencias(canonizar(declarado), canonizar(reexportado))

    assert not problemas, (
        f"spec/flujos/{nombre}.json no sobrevive a su propia importación:\n{describir(problemas)}"
    )


@pytest.mark.parametrize("nombre", _nombres())
def test_dry_run_no_persiste(nombre):
    """`?dry_run=true` valida sin escribir.

    Es lo que permite comprobar un JSON del designer antes de aplicarlo.
    """
    declarado = json.loads((directorio_flujos() / f"{nombre}.json").read_text(encoding="utf-8"))
    copia = json.loads(json.dumps(declarado))
    copia["flujo"]["nombre"] = nombre + SUFIJO

    antes = VersionFlujo.objects.count()
    resultado = deserialize_flujo(copia, dry_run=True)

    assert resultado is None
    assert VersionFlujo.objects.count() == antes
