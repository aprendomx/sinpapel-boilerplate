FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libpq para psycopg. GDAL/GEOS no se instalan: el engine es `postgresql`
# a secas mientras ningún modelo tenga campos de geometría.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# La fuente se copia ANTES de instalar: `pip install -e` resuelve los paquetes
# declarados en [tool.setuptools] (apps, config) en disco, y con solo el
# pyproject.toml presente falla con "package directory 'apps' does not exist".
COPY backend/ ./

# Desde el lock, igual que `make install`: si el contenedor resolviera por su
# cuenta, podría correr con versiones distintas de las que pasaron los gates.
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir -e . --no-deps

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
