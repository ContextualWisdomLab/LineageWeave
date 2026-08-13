FROM node:24-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Vite bakes VITE_* vars in at build time, not runtime -- build args let
# docker-compose pass through its own (possibly operator-overridden) ports.
ARG VITE_KEYCLOAK_ISSUER
ARG VITE_KEYCLOAK_CLIENT_ID
ARG VITE_BACKEND_BASE_URL
ENV VITE_KEYCLOAK_ISSUER=${VITE_KEYCLOAK_ISSUER} \
    VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID} \
    VITE_BACKEND_BASE_URL=${VITE_BACKEND_BASE_URL}
RUN pnpm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
