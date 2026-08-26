# Local Compose project consolidation evidence

On 2026-08-26 KST, container labels were read before any cleanup. Three
non-canonical Compose projects were identified by exact project name and
configuration path: `lw-cancelled-visualk5c5lp`, `lw-k6-agent`, and `lwrepro`.
Their service definitions were compared with the Dashboard candidate. The only
still-supported environment contract absent from that candidate was
`TEPP_API_KEY`; it is now part of the canonical backend service.

Before cleanup, `lineageweave-dashboard-metrics` ran PostgreSQL plus its
successful one-shot migration, Valkey, SearXNG, Keycloak,
contextual-orchestrator, backend, and frontend. Live OIDC/JWKS verification
passed. An authenticated 2-VU, 20-second k6 run completed 162 requests with
zero failures across posts, Event Lineage, Dashboard, and Ask polling; all
seven observed Ask jobs in the synthetic database were `succeeded`.
This local run left `KEYVERSE_ISSUER` unset and therefore proved the synthetic
Keycloak fallback only. A Keyverse-configured deployment is a separate,
fail-closed issuer and claim-binding acceptance boundary under ADR 0028/0156.

Each identified Compose project was retired with its exact `-p` project name
and `docker compose down`, without `-v`. Six named volumes remain: one
PostgreSQL and one Valkey volume for each retired project. The independently
created `lw-orch-hostport` container has no Compose project/configuration
labels, so it was not guessed into a project or deleted. A one-off container
still labeled `lw-k6-agent` is likewise retained because the approved cleanup
mechanism is project-scoped `docker compose down`, not direct container
deletion.

This is local, synthetic runtime evidence. It is neither production capacity
evidence nor protected-main delivery evidence.
