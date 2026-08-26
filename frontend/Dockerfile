FROM node:24-slim@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03 AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
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

FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Official nginx binds :80 as root and writes its pid file to /run/nginx.pid
# (nginx.conf's real path -- NOT /var/run/nginx.pid, which does not
# appear in this image's config and made an earlier sed here a silent
# no-op, leaving the master process unable to start as non-root at all).
# Move both so the declared non-root USER can actually start the master
# process (DS-0002). Compose publishes this 8080, not 80.
RUN sed -i 's,/run/nginx.pid,/tmp/nginx.pid,' /etc/nginx/nginx.conf \
    && sed -i '/^user /d' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx
USER nginx
EXPOSE 8080
