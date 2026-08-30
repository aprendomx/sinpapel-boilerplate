"""Siembra el flujo del trámite leyendo `spec/flujos/solicitud_constancia.json`.

La verdad de los estados y las transiciones vive en ese JSON, no aquí: esta
migración solo lo carga. Editar el flujo significa editar el JSON (a mano o con
el designer) y volver a importarlo, nunca tocar Python.

Se usa `deserialize_flujo`, la API canónica de portabilidad de sinpapel, en vez
de crear los objetos a mano: es la misma ruta que usan el comando
`sinpapel_import_flujo` y el endpoint `POST /flujos/import/`, así que lo que
esta migración produce es idéntico a lo que produciría el designer.

Excepción consciente a `apps.get_model`: `deserialize_flujo` importa los
modelos reales de sinpapel. Es lo que documenta el framework para este caso;
a cambio, la migración depende de que el esquema de sinpapel no cambie bajo
sus pies, que es justo lo que fija el pin `sinpapel~=0.8.3`.
"""

import json
from pathlib import Path

from django.core.files import File
from django.db import migrations

# backend/apps/tramite_ejemplo/migrations/ -> raíz del repo
REPO_DIR = Path(__file__).resolve().parents[4]
FLUJO_JSON = REPO_DIR / "spec" / "flujos" / "solicitud_constancia.json"
PLANTILLAS = Path(__file__).resolve().parents[1] / "plantillas"

NOMBRE_FLUJO = "solicitud_constancia"

# Coordenadas del acuse. La `y` se mide desde el borde SUPERIOR de la página
# (el renderer dibuja en `alto_pagina - y`), no desde el inferior como haría
# un PDF nativo.
OVERLAY_ACUSE = {
    "data_source": "solicitud_constancia",
    "campos_solicitud": {
        "folio": {"visible": True, "label": "Folio", "x": 90, "y": 160},
        "fecha": {"visible": True, "label": "Fecha", "x": 350, "y": 160},
        "dependencia": {"visible": True, "label": "Dependencia", "x": 90, "y": 195},
        "estado": {"visible": True, "label": "Estado", "x": 350, "y": 195},
    },
    "campos_participantes": {
        "solicitante": {"visible": True, "label": "Solicitante", "x": 90, "y": 235},
        "curp": {"visible": True, "label": "CURP", "x": 350, "y": 235},
    },
    "posicion_base": {"x_left": 90, "y_top_offset": 160, "line_height": 18},
    "fuente": {"nombre": "Helvetica", "tamaño": 10},
}


def sembrar(apps, schema_editor):
    from sinpapel.schemas.flujo_export import deserialize_flujo

    VersionFlujo = apps.get_model("sinpapel", "VersionFlujo")
    if VersionFlujo.objects.filter(nombre=NOMBRE_FLUJO).exists():
        # `deserialize_flujo` rechaza un flujo cuyo nombre ya existe. Salir
        # aquí hace la migración segura ante una reejecución manual.
        return

    datos = json.loads(FLUJO_JSON.read_text(encoding="utf-8"))
    # El JSON declara `activo: true`, pero el importador ignora esa clave y usa
    # su propio parámetro, con default False por seguridad. Se pasa explícito
    # para que lo sembrado coincida con lo declarado.
    deserialize_flujo(datos, activo=datos["flujo"]["activo"])

    _sembrar_documentos_del_usuario(apps)
    _sembrar_plantillas(apps)


def _sembrar_documentos_del_usuario(apps):
    """Registra los `Documento` que la persona solicitante sube al expediente.

    El flujo declara los *tipos* exigidos (`RequisitoEstadoDocumento`), pero el
    expediente se llena con `InstanciaDocumento`, que apunta a un `Documento`
    concreto. Sin estas filas no habría forma de satisfacer un requisito, y el
    endpoint de carga tampoco podría resolver el documento a partir del tipo.

    No llevan plantilla: el archivo lo aporta quien tramita.
    """
    TipoDocumento = apps.get_model("sinpapel", "TipoDocumento")
    Documento = apps.get_model("sinpapel", "Documento")

    for nombre_tipo, valor in [
        ("Identificación oficial", "IDENTIFICACION_OFICIAL"),
        ("Comprobante de domicilio", "COMPROBANTE_DOMICILIO"),
    ]:
        if Documento.objects.filter(valor=valor).exists():
            continue
        tipo = TipoDocumento.objects.filter(nombre=nombre_tipo).first()
        Documento.objects.create(
            nombre=nombre_tipo,
            valor=valor,
            tipo_documento=tipo,
            activo=True,
        )


def _sembrar_plantillas(apps):
    """Registra las dos plantillas del trámite como `Documento`.

    `Documento.valor` es la clave con la que los side effects localizan cada
    plantilla; el archivo se copia a MEDIA_ROOT a través del FileField.
    """
    TipoDocumento = apps.get_model("sinpapel", "TipoDocumento")
    Documento = apps.get_model("sinpapel", "Documento")

    # El oficio no es requisito de ningún estado, así que su tipo no viaja en
    # el JSON del flujo y se crea aquí.
    tipo_oficio, _ = TipoDocumento.objects.get_or_create(
        nombre="Oficio de resolución",
        defaults={"activo": True, "orden": 4},
    )

    especificaciones = [
        {
            "valor": "ACUSE_SOLICITUD_CONSTANCIA",
            "nombre": "Acuse de recepción de solicitud",
            "tipo_documento": "Acuse de recepción",
            "tipo_plantilla": "PDF",
            "archivo": PLANTILLAS / "acuse_recepcion.pdf",
            "configuracion_overlay": OVERLAY_ACUSE,
        },
        {
            "valor": "OFICIO_RESOLUCION_CONSTANCIA",
            "nombre": "Oficio de resolución",
            "tipo_documento": tipo_oficio.nombre,
            "tipo_plantilla": "DOCX",
            "archivo": PLANTILLAS / "oficio_resolucion.docx",
            # DOCX no usa overlay: docxtpl recibe el contexto completo y
            # rellena los marcadores Jinja de la plantilla.
            "configuracion_overlay": {"data_source": "solicitud_constancia"},
        },
    ]

    for espec in especificaciones:
        if Documento.objects.filter(valor=espec["valor"]).exists():
            continue
        tipo = TipoDocumento.objects.filter(nombre=espec["tipo_documento"]).first()
        documento = Documento.objects.create(
            nombre=espec["nombre"],
            valor=espec["valor"],
            tipo_documento=tipo,
            tipo_plantilla=espec["tipo_plantilla"],
            configuracion_overlay=espec["configuracion_overlay"],
            activo=True,
        )
        ruta = espec["archivo"]
        with ruta.open("rb") as fh:
            documento.plantilla.save(ruta.name, File(fh), save=True)


class Migration(migrations.Migration):
    dependencies = [
        ("tramite_ejemplo", "0001_initial"),
        ("sinpapel", "0009_alter_historicalregistrofirma_verification_result_and_more"),
        ("cuentas", "0003_seed_roles"),
    ]

    operations = [
        # Sin reverse: revertir borraría el flujo y con él las transiciones que
        # referencian los expedientes ya tramitados.
        migrations.RunPython(sembrar, reverse_code=migrations.RunPython.noop),
    ]
