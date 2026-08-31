# ADR 0224: Canonical local Compose project

- Status: Accepted
- Date: 2026-08-26

## Context

Running the same Compose file from temporary worktrees created multiple `lw*`
and branch-named projects. Operators could no longer tell which stack owned the
current synthetic database, migrations, frontend, backend, identity provider,
search, queue, and contextual-orchestrator boundary. One observed project also
carried `TEPP_API_KEY` into the backend while the Dashboard candidate omitted
that already-supported runtime setting.

## Decision

`docker-compose.yml` declares the default project name `lineageweave` and keeps
all product services in that project: PostgreSQL, the one-shot migration,
Valkey, SearXNG, Keycloak, contextual-orchestrator, the dedicated durable-queue
worker, backend, and frontend.
An isolated test may still override the name explicitly with Compose `-p`; it
must use a disposable name and must not mutate the canonical project.

The backend receives only its TEPP transport URL and TEPP API credential. The
provider gateway credentials remain confined to contextual-orchestrator through
the existing `${HOME}/.env` boundary. Compose cleanup uses `docker compose down`
for an exactly identified project and never deletes named volumes by default.

Identity selection remains ADR 0028/0156's exclusive choice. With a non-empty
`KEYVERSE_ISSUER`, backend and frontend use central Keyverse and malformed or
unbound Keyverse scope claims fail closed; the local Keycloak service is not a
second trusted issuer. With no Keyverse issuer, standalone/local/dev/test uses
only the synthetic `lineageweave-demo` Keycloak realm.

The API process never owns a queue consumer. Instead, `backend` has a required
`service_healthy` dependency on `backend-worker`, whose progress-based health
probe observes its event loop. The probe reads the worker's monotonic heartbeat
with the image's POSIX shell rather than starting and importing a Python
process on every interval. This preserves progress detection while preventing
concurrent health probes from amplifying container-runtime and filesystem load.
The worker removes both the heartbeat and the probe's prior baseline before it
publishes the first heartbeat of a process. Those files may survive a process
or VM restart in the container writable layer while the operating system's
monotonic clock restarts from a smaller value; monotonic samples are therefore
compared only within one worker-process epoch and never across boots.
When a runtime prerequisite closes readiness, the worker removes both files
again. A successful validation, including an unchanged prepared identity,
opens a new readiness epoch and resumes the heartbeat.
Consequently, targeted canonical startup such
as `docker compose up backend` also starts the worker and does not expose an API
that can accept durable jobs while no consumer exists. Non-Compose deployments
must express the same co-deployment and readiness dependency in their service
manager; process liveness alone is not durable-job readiness.

Backend, worker, and frontend images carry the
`org.opencontainers.image.revision` label supplied by the explicit
`LINEAGEWEAVE_SOURCE_REVISION` build argument. Its default is `unknown`, so an
acceptance runner cannot mistake an ordinary local build for exact-head
evidence. Exact-head evidence requires a full commit SHA supplied at build time
and verified on every participating product container before the run.

## Consequences

- `make up`, `make ps`, `make logs`, and `make down` address the same project
  from the repository or a worktree unless an isolated test explicitly uses
  `-p`.
- A complete synthetic acceptance run can exercise OIDC, migrations, search,
  Valkey, contextual-orchestrator, backend, frontend, Dashboard, and Ask without
  mixing services from different working directories.
- Starting the canonical backend target alone still starts and health-gates the
  dedicated worker; queue ownership remains outside the HTTP process.
- Historical `lw*` projects may be removed only after comparing their Compose
  source and validating the canonical stack; their named volumes remain
  recoverable.
