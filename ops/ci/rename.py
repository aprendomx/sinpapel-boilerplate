#!/usr/bin/env python3
"""Reemplaza la identidad del proyecto: `make rename NAME=<slug>`.

El template es un repo ejecutable, no un cookiecutter: no hay `{{ variables }}`
que sustituir, así que renombrar es reemplazar dos literales concretos.

    sinpapel-boilerplate  → <slug>         (kebab: paquetes, compose, README)
    sinpapel_boilerplate  → <slug con _>   (snake: base de datos, usuario)

Es deliberadamente quirúrgico. El framework se llama `sinpapel` a secas y ese
nombre aparece por todas partes —imports, settings `SINPAPEL_*`, rutas
`/sinpapel/api/`—: un reemplazo sobre "sinpapel" destruiría el proyecto.

Está en Python y no en bash porque este script se reescribe a sí mismo: bash
lee los scripts de forma incremental y, al cambiar sus bytes a mitad de la
ejecución, pasa a interpretar basura. Python carga el archivo entero antes de
ejecutarlo, así que la automodificación es inocua.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

KEBAB_ACTUAL = "sinpapel-boilerplate"
SNAKE_ACTUAL = "sinpapel_boilerplate"

# Kebab-case: se usa como nombre de paquete npm, proyecto de compose e
# identificador en spec/sistema.yaml.
SLUG_VALIDO = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# Contenido vendorizado y artefactos que se regeneran: no se editan a mano.
EXCLUIDOS = (".claude/skills/",)
REGENERADOS = ("package-lock.json",)


def archivos_versionados() -> list[Path]:
    salida = subprocess.run(
        ["git", "ls-files"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rutas = []
    for linea in salida.splitlines():
        if linea.startswith(EXCLUIDOS) or linea.endswith(REGENERADOS):
            continue
        ruta = RAIZ / linea
        if ruta.is_file():
            rutas.append(ruta)
    return rutas


def es_binario(ruta: Path) -> bool:
    """Las plantillas PDF/DOCX del trámite, por ejemplo."""
    try:
        ruta.read_text(encoding="utf-8")
    except (UnicodeDecodeError, ValueError):
        return True
    return False


def renombrar(nuevo_kebab: str) -> int:
    nuevo_snake = nuevo_kebab.replace("-", "_")

    print(f"→ {KEBAB_ACTUAL} → {nuevo_kebab}")
    print(f"→ {SNAKE_ACTUAL} → {nuevo_snake}")

    cambiados = 0
    for ruta in archivos_versionados():
        if es_binario(ruta):
            continue
        texto = ruta.read_text(encoding="utf-8")
        if KEBAB_ACTUAL not in texto and SNAKE_ACTUAL not in texto:
            continue
        # El snake primero: ninguno es subcadena del otro, pero el orden
        # explícito deja la intención clara si algún día se parecen.
        texto = texto.replace(SNAKE_ACTUAL, nuevo_snake)
        texto = texto.replace(KEBAB_ACTUAL, nuevo_kebab)
        ruta.write_text(texto, encoding="utf-8")
        print(f"  · {ruta.relative_to(RAIZ)}")
        cambiados += 1
    return cambiados


# Paquetes npm del repositorio: cada uno lleva su nombre dentro del lockfile.
PAQUETES_NPM = ("frontend", "e2e")


def regenerar_lockfiles() -> None:
    """Regenera los lockfiles para que recojan el nombre nuevo.

    Se regeneran en vez de editarlos a mano: npm es la autoridad sobre su
    propio formato. Va DESPUÉS del renombrado, porque npm copia el nombre desde
    `package.json`: hacerlo antes reescribiría el lockfile con el nombre viejo.
    """
    for paquete in PAQUETES_NPM:
        lockfile = RAIZ / paquete / "package-lock.json"
        if not lockfile.is_file():
            continue
        print(f"→ regenerando {paquete}/package-lock.json")
        subprocess.run(
            ["npm", "install", "--package-lock-only", "--silent"],
            cwd=RAIZ / paquete,
            check=True,
        )


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1]:
        print("Uso: make rename NAME=<slug>", file=sys.stderr)
        return 2

    nuevo = sys.argv[1]
    if not SLUG_VALIDO.match(nuevo):
        print(f"✗ '{nuevo}' no es un slug válido.", file=sys.stderr)
        print(
            "  Minúsculas, dígitos y guiones; debe empezar por letra "
            "(ej. tramites-sep).",
            file=sys.stderr,
        )
        return 2

    cambiados = renombrar(nuevo)
    if cambiados:
        regenerar_lockfiles()

    if cambiados == 0:
        print("\nNo se encontró la identidad del template en ningún archivo.")
        print("¿Ya se renombró este repositorio?")
        return 1

    print(f"\n✓ {cambiados} archivo(s) actualizados.\n")
    print("Siguiente paso: 'make verify'. Y si ya tenías el stack levantado,")
    print("'make down' antes de 'make up': cambian el nombre del proyecto de")
    print("compose y el de la base de datos, así que los contenedores viejos")
    print("quedan huérfanos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
