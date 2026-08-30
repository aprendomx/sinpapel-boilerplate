FROM node:22-alpine

WORKDIR /app

# Las dependencias se instalan en tiempo de build, no en cada arranque: un
# `npm ci` por `docker compose up` es lento y deja el servicio a merced de la
# red. Copiar solo los manifiestos primero conserva la capa de caché mientras
# no cambien.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci && cp package-lock.json node_modules/.lockfile-instalado.json

COPY frontend/ ./

EXPOSE 5173

# `node_modules` es un volumen con nombre, y Docker solo lo puebla desde la
# imagen la PRIMERA vez que lo crea. Tras añadir una dependencia, el volumen
# viejo shadowea el `node_modules` recién construido y la app arranca sin ella:
# falla en el navegador con un "Failed to resolve import" que no aparece en
# ningún test.
#
# El marcador va DENTRO de node_modules a propósito, para que viaje con el
# volumen: guardarlo en la imagen no serviría, porque ahí siempre estaría el
# lockfile actual y la comparación nunca detectaría el desfase.
CMD ["sh", "-c", "cmp -s package-lock.json node_modules/.lockfile-instalado.json || (echo 'Dependencias desfasadas en el volumen; reinstalando…' && npm ci && cp package-lock.json node_modules/.lockfile-instalado.json); npm run dev -- --host 0.0.0.0"]
