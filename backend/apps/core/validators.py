"""Validadores de identificadores oficiales mexicanos.

Viven en `core` y no en la app que los usa porque los comparten el usuario del
sistema y los metadatos de los trámites.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# RENAPO: 4 letras, 6 dígitos de fecha, H/M, 5 letras de entidad y consonantes,
# 1 alfanumérico (homoclave o dígito para nacidos desde 2000) y 1 dígito.
_CURP = re.compile(r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[0-9A-Z]\d$")

# SAT: 3 letras (moral) o 4 (física), 6 dígitos de fecha y 3 de homoclave.
_RFC = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[0-9A-Z]{3}$")


def validar_curp(valor: str) -> None:
    """Valida la forma de una CURP.

    Comprueba la estructura, no la existencia en el registro: para eso hace
    falta consultar a RENAPO.
    """
    if not _CURP.match((valor or "").upper()):
        raise ValidationError(
            _("'%(valor)s' no tiene la forma de una CURP (18 caracteres)."),
            code="curp_invalida",
            params={"valor": valor},
        )


def validar_rfc(valor: str) -> None:
    """Valida la forma de un RFC con homoclave."""
    if not _RFC.match((valor or "").upper()):
        raise ValidationError(
            _("'%(valor)s' no tiene la forma de un RFC con homoclave."),
            code="rfc_invalido",
            params={"valor": valor},
        )
