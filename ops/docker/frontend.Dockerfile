FROM node:22-alpine

WORKDIR /app

# Las dependencias se instalan en tiempo de build, no en cada arranque: un
# `npm ci` por `docker compose up` es lento y deja el servicio a merced de la
# red. Copiar solo los manifiestos primero conserva la capa de caché mientras
# no cambien.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
