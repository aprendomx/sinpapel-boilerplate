"""Fixtures compartidas por la suite.

El cache de sinpapel es process-wide (LocMemCache) mientras que la base de
datos hace rollback entre tests: sin limpiarlo, un test arrastra Estados y
VersionFlujo con IDs de filas ya revertidas.
"""

import pytest
from sinpapel.cache import clear_all
from sinpapel.signing.factory import reset_backend_cache


@pytest.fixture(autouse=True)
def _limpiar_caches_sinpapel():
    clear_all()
    reset_backend_cache()
    yield
    clear_all()
    reset_backend_cache()
