"""Dependencias, adscripciones y resolución de visibilidad por área."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.core.validators import validar_curp, validar_rfc
from apps.cuentas.models import Adscripcion, Dependencia

pytestmark = pytest.mark.django_db


def test_roles_sembrados_por_la_migracion():
    """Los cinco roles existen: son lo que consume `grupos_permitidos`."""
    from django.contrib.auth.models import Group

    assert set(Group.objects.values_list("name", flat=True)) == {
        "solicitante",
        "ventanilla",
        "revisor",
        "firmante",
        "admin",
    }


def test_una_dependencia_incluye_a_sus_subordinadas(dependencia):
    """Quien está adscrito a un área superior ve las que dependen de ella."""
    hija = Dependencia.objects.create(clave="DGA-1", nombre="Subdirección", superior=dependencia)
    nieta = Dependencia.objects.create(clave="DGA-1-A", nombre="Departamento", superior=hija)

    claves = {d.clave for d in dependencia.descendientes()}

    assert claves == {dependencia.clave, hija.clave, nieta.clave}
    # Hacia abajo, no hacia arriba.
    assert {d.clave for d in nieta.descendientes()} == {nieta.clave}


def test_visibilidad_por_adscripcion(solicitante, dependencia, otra_dependencia):
    hija = Dependencia.objects.create(clave="DGA-1", nombre="Subdirección", superior=dependencia)

    visibles = {d.clave for d in solicitante.dependencias_visibles()}

    assert visibles == {dependencia.clave, hija.clave}
    assert otra_dependencia.clave not in visibles


def test_una_adscripcion_vencida_deja_de_dar_visibilidad(solicitante, dependencia):
    """La vigencia es lo que permite explicar quién veía qué y cuándo."""
    ayer = timezone.now() - timedelta(days=1)
    Adscripcion.objects.filter(usuario=solicitante).update(hasta=ayer)

    assert solicitante.dependencias_visibles() == []


def test_no_se_duplica_una_adscripcion_activa(solicitante, dependencia):
    with pytest.raises(IntegrityError):
        Adscripcion.objects.create(usuario=solicitante, dependencia=dependencia)


def test_tiene_rol(solicitante):
    assert solicitante.tiene_rol("solicitante") is True
    assert solicitante.tiene_rol("revisor") is False
    assert solicitante.tiene_rol("revisor", "solicitante") is True


@pytest.mark.parametrize("valida", ["AEAA010101HDFXXX09", "BEBB020202MDFXXX07"])
def test_curp_valida(valida):
    validar_curp(valida)


@pytest.mark.parametrize("invalida", ["", "ABC", "AEAA010101XDFXXX09", "aeaa010101hdfxxx0"])
def test_curp_invalida(invalida):
    with pytest.raises(ValidationError):
        validar_curp(invalida)


@pytest.mark.parametrize("valido", ["AEAA010101AB1", "AAA010101AAA"])
def test_rfc_valido(valido):
    validar_rfc(valido)


@pytest.mark.parametrize("invalido", ["", "AE", "AEAA0101"])
def test_rfc_invalido(invalido):
    with pytest.raises(ValidationError):
        validar_rfc(invalido)
