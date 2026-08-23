FROM python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d
# Local-only demo source for the independent CalDAV consumer port
# (lineageweave.caldav_client, ADR 0038). Serves the exact
# `GET {CALDAV_BASE_URL}/events` contract from a static file so
# docker-compose environments can exercise the connected-calendar path
# without a real external CalDAV account. Not the Naruon CalDAV provider
# (see docs/adr/0038-calendar-source-contract.md and the
# product-technical-gap-baseline "Calendar interoperability" entry) --
# swap CALDAV_BASE_URL to that provider once it ships.
WORKDIR /srv
COPY --chown=65534:65534 site /srv
EXPOSE 8080
# Official image's default unprivileged account (uid 65534, "nobody").
# Declared so the Dockerfile satisfies the explicit non-root USER
# convention used by docker/searxng and docker/keycloak.
USER 65534
CMD ["python3", "-m", "http.server", "8080", "--bind", "0.0.0.0"]
