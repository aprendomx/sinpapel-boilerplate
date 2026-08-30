"""Generación de folios de trámite."""

from datetime import date

from django.db import models


def generar_folio(modelo: type[models.Model], prefijo: str, hoy: date | None = None) -> str:
    """Devuelve el siguiente folio del año para `modelo`, con formato PREFIJO-AAAA-NNNNNN.

    El consecutivo se calcula contando los folios ya emitidos ese año. No es
    resistente a concurrencia por sí solo: el campo `folio` debe ser único a
    nivel de base de datos para que un choque falle en vez de duplicar.
    """
    hoy = hoy or date.today()
    raiz = f"{prefijo}-{hoy.year}-"
    consecutivo = modelo.objects.filter(folio__startswith=raiz).count() + 1
    return f"{raiz}{consecutivo:06d}"
