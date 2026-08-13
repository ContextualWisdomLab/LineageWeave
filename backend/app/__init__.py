"""LineageWeave product backend: FastAPI over a direct PostgreSQL connection,
OIDC-validated login (Keycloak), and RBAC + ABAC-enforced post access.

See ARCHITECTURE.md's "Product schema" section and
docs/adr/0001-demo-identity-and-data-boundary.md for the scope this
implements against.
"""
