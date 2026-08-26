# ADR 0224: Pin the canonical Compose project name

## Status

Accepted — 2026-08-26

## Context

Docker Compose otherwise derives its project name from the checkout directory.
Stacked PR worktrees therefore produced several production-looking
`lineageweave-*` projects with duplicated networks and stateful services. That
made the product preview ambiguous and could point operators at the wrong
PostgreSQL or identity service.

## Decision

The repository Compose file declares `name: lineageweave`. Normal `docker
compose` commands therefore converge on one canonical standalone stack,
regardless of the checkout directory name.

An isolated test or review environment may override the name explicitly with
`docker compose -p <test-project>`. Such an override is test infrastructure,
not another canonical deployment. After its declared objective succeeds, its
evidence and any required behavior are retained, then its containers and
network are removed with `docker compose -p <exact-project> down`. Named
volumes are never deleted as part of project-name consolidation without a
separate, explicit authorization.

The canonical standalone stack retains its synthetic local Keycloak fallback.
Organization-integrated deployments configure the central Keyverse issuer as
required by ADR 0028 and ADR 0156; the Compose project name does not change the
identity-provider trust boundary.

## Consequences

- `docker compose up` consistently creates the `lineageweave` project.
- Preview and operational instructions have one unambiguous project name.
- Parallel review stacks must opt into a distinct name and ports deliberately.
- Existing noncanonical volumes remain recoverable until separately retired.
