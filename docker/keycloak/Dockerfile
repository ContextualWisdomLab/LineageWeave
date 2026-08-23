FROM quay.io/keycloak/keycloak:26.0@sha256:09a381c715ab0b111835b70f2905955274843a219c6f27efb348e4d9f4086858
COPY realm-export.json /opt/keycloak/data/import/realm-export.json
COPY themes/lineageweave /opt/keycloak/themes/lineageweave
# Official image's default non-root account (uid 1000). Declared so the
# Dockerfile itself satisfies DS-0002 (explicit non-root USER).
USER 1000
