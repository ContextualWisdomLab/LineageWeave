FROM quay.io/keycloak/keycloak:26.0@sha256:09a381c715ab0b111835b70f2905955274843a219c6f27efb348e4d9f4086858
COPY realm-export.json /opt/keycloak/data/import/realm-export.json
COPY entrypoint.sh /opt/keycloak/lineageweave-entrypoint.sh
# Render the realm audience at startup so MCP_PORT and exact audience
# validation cannot drift. Only this import directory is made writable by
# Keycloak's existing non-root uid.
USER root
RUN chown -R 1000:0 /opt/keycloak/data/import \
    && chmod 0755 /opt/keycloak/lineageweave-entrypoint.sh
# Official image's default non-root account (uid 1000). Declared so the
# Dockerfile itself satisfies DS-0002 (explicit non-root USER).
USER 1000
ENTRYPOINT ["/opt/keycloak/lineageweave-entrypoint.sh"]
