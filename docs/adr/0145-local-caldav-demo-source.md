# ADR 0145: Local demo CalDAV source for docker-compose

- Status: Accepted
- Date: 2026-08-24

## Context

ADR 0038 defines `GET /api/calendar`'s independent CalDAV consumer port:
`lineageweave.caldav_client` reads `{CALDAV_BASE_URL}/events` and fails
closed to an empty `events` list with a next action when unset. Naruon is
the intended long-term CalDAV provider, but per
`docs/product-technical-gap-baseline.md`'s "Calendar interoperability" entry
that provider-side endpoint has not shipped. Until then, every fresh
`docker compose up` shows the CalDAV panel as permanently disconnected --
including for demos and status reports, where an operator has no external
CalDAV account to point at either.

## Decision

Add a `caldav-demo` compose service (`docker/caldav-demo`): a
`python:3.13-alpine` image, pinned by digest, running as the image's
unprivileged `nobody` user, serving a static `events` fixture from
`python -m http.server`. It satisfies the exact same `GET {base}/events`
JSON contract `HttpCalDavClient` already expects -- no changes to
`lineageweave.caldav_client` or `GET /api/calendar`.

`backend`'s `CALDAV_BASE_URL` now defaults to
`http://caldav-demo:8080` instead of empty, and depends on
`caldav-demo`'s healthcheck. Setting `CALDAV_BASE_URL` to a real source
(the eventual Naruon endpoint, or any other CalDAV bridge) still overrides
the default, matching every other optional-channel variable in this file
(`TEPP_TRANSPORT_URL`, `ORCHESTRATOR_BASE_URL`).

## Consequences

- A fresh compose stack shows a connected Calendar workspace out of the
  box; no code changed in the consumer port or its tests
  (`tests/test_caldav_client.py` is unaffected).
- This is not the Naruon CalDAV provider integration. The
  product-technical-gap-baseline entry for that cross-repo contract
  remains open and unchanged by this ADR.
- The demo fixture's event dates are static and will read as stale after
  they pass; this is a known limitation shared with the existing seeded
  commitment fixtures (`lineageweave/fixtures.py`) and is not solved here.
