"""Servicio del designer embebido.

`sinpapel-designer` es una SPA: se construye con `make designer` a
`designer/dist/spa/` y se sirve desde aquí bajo una ruta protegida. No es una
app de Django ni se instala con pip.

La ruta exige staff porque el designer edita la definición de los trámites del
sistema, aunque el guardado a disco además esté restringido a DEBUG.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache

DIST = Path(settings.REPO_DIR) / "designer" / "dist" / "spa"

_AUSENTE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Designer no construido</title></head>
<body style="font-family: system-ui; max-width: 40rem; margin: 4rem auto; line-height: 1.6">
<h1>El designer no está construido</h1>
<p>La SPA se compila aparte y su salida no se versiona. Constrúyela con:</p>
<pre style="background:#f4f4f4;padding:1rem">make designer</pre>
<p>Después recarga esta página.</p>
</body></html>
"""


def _archivo_dentro_del_dist(ruta_relativa: str) -> Path | None:
    """Resuelve un recurso del bundle, rechazando cualquier escape del dist."""
    candidato = (DIST / ruta_relativa).resolve()
    if not candidato.is_relative_to(DIST.resolve()) or not candidato.is_file():
        return None
    return candidato


@never_cache
@staff_member_required
def designer(request: HttpRequest, recurso: str = "") -> HttpResponse:
    """Sirve el bundle del designer.

    Cualquier ruta que no corresponda a un archivo cae en `index.html`: la SPA
    resuelve su propio enrutado del lado del cliente.
    """
    if not DIST.is_dir():
        return HttpResponse(_AUSENTE, status=503)

    if recurso:
        archivo = _archivo_dentro_del_dist(recurso)
        if archivo is not None:
            return FileResponse(archivo.open("rb"))

    index = DIST / "index.html"
    if not index.is_file():
        raise Http404("El bundle del designer no contiene index.html")
    return FileResponse(index.open("rb"), content_type="text/html")
