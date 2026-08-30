"""Lectura y escritura de `spec/flujos/*.json`.

Esos archivos son la verdad del flujo, no una copia: el gate `parity` compara
la base de datos contra ellos y falla si divergen. Por eso el designer escribe
aquí y no en la base: un flujo editado entra a git como cualquier otro cambio,
se revisa en un PR y se aplica con una data migration.

**En producción no se escribe.** El directorio se monta read-only y el guardado
queda deshabilitado: un cambio de flujo en caliente saltaría la revisión y
dejaría la base fuera de sincronía con el repositorio.
"""

import json
import re
from pathlib import Path

from django.conf import settings

from apps.spec_io.canonical import canonizar

# Un nombre de flujo se usa para construir una ruta: restringirlo evita que un
# `..` o una barra escapen del directorio.
NOMBRE_VALIDO = re.compile(r"^[a-z0-9_]+$")


class EscrituraDeshabilitada(RuntimeError):
    """Se intentó guardar un flujo fuera de desarrollo."""


class FlujoNoEncontrado(FileNotFoundError):
    """No existe `spec/flujos/<nombre>.json`."""


class NombreInvalido(ValueError):
    """El nombre no puede formar parte de una ruta de archivo."""


def directorio_flujos() -> Path:
    return Path(settings.SPEC_DIR) / "flujos"


def _ruta(nombre: str) -> Path:
    if not NOMBRE_VALIDO.match(nombre or ""):
        raise NombreInvalido(
            f"'{nombre}' no es un nombre de flujo válido (minúsculas, dígitos y _)."
        )
    ruta = (directorio_flujos() / f"{nombre}.json").resolve()
    # Cinturón y tirantes: aunque el patrón ya lo impide, se confirma que la
    # ruta resuelta sigue dentro del directorio.
    if not ruta.is_relative_to(directorio_flujos().resolve()):
        raise NombreInvalido(f"'{nombre}' resuelve fuera de spec/flujos/.")
    return ruta


def escritura_habilitada() -> bool:
    """El designer solo persiste a disco en desarrollo."""
    return bool(settings.DEBUG)


def listar_flujos() -> list[str]:
    """Nombres de los flujos declarados, sin extensión."""
    directorio = directorio_flujos()
    if not directorio.is_dir():
        return []
    return sorted(p.stem for p in directorio.glob("*.json"))


def leer_flujo(nombre: str) -> dict:
    ruta = _ruta(nombre)
    if not ruta.is_file():
        raise FlujoNoEncontrado(f"No existe spec/flujos/{nombre}.json")
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_flujo(nombre: str, datos: dict) -> bool:
    """Guarda el flujo. Devuelve si el archivo cambió.

    Compara en forma canónica antes de escribir: reordenar listas o reexportar
    no debe producir un commit vacío.
    """
    if not escritura_habilitada():
        raise EscrituraDeshabilitada(
            "El designer solo escribe a spec/flujos/ con DEBUG=True. "
            "En producción el directorio es de solo lectura."
        )

    ruta = _ruta(nombre)
    if ruta.is_file():
        actual = json.loads(ruta.read_text(encoding="utf-8"))
        if canonizar(actual) == canonizar(datos):
            return False

    ruta.parent.mkdir(parents=True, exist_ok=True)
    # `ensure_ascii=False` para que los acentos se lean en el diff de git, y
    # salto final para que el archivo termine como cualquier otro del repo.
    ruta.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return True


def exportar_desde_db(nombre: str) -> dict:
    """Serializa el flujo tal como está en la base, en JSON v0.2.

    Es la misma ruta que usa `manage.py sinpapel_export_flujo`, así que lo que
    sale de aquí es idéntico a lo que produciría el comando.
    """
    from sinpapel.models import VersionFlujo
    from sinpapel.schemas.flujo_export import serialize_flujo

    flujo = VersionFlujo.objects.filter(nombre=nombre).order_by("-activo", "-id").first()
    if flujo is None:
        raise FlujoNoEncontrado(f"No hay ningún VersionFlujo llamado '{nombre}'.")
    return serialize_flujo(flujo, inline_catalogs=True)
