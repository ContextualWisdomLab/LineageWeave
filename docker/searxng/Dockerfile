FROM searxng/searxng@sha256:c2dc2d9e6b910653e8628361c23443222490e4cabbb9e02667b7847143db843b
COPY settings.yml /etc/searxng/settings.yml
# Official image's default non-root account (uid 977). Declared so the
# Dockerfile itself satisfies DS-0002 (explicit non-root USER), matching
# docker/keycloak/Dockerfile's own USER declaration.
USER searxng
# Same readiness probe as docker-compose.yml's searxng healthcheck.
HEALTHCHECK --interval=5s --timeout=5s --retries=10 \
    CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
