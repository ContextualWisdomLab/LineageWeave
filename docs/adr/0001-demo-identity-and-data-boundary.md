# ADR 0001 — Demo-grade identity and data boundary for LineageWeave's product features

**Decision status:** Accepted
**Date:** 2026-08-13

## Context

LineageWeave is growing from a synthetic-data DAG-reconstruction prototype
into a fuller product surface: corporate/PU-code login, ABAC/RBAC, a
Keyman (key-contact) extraction and Knowledge Graph feature, a corporate
hierarchy tree, and a real PostgreSQL-backed React frontend, wired to a
real identity provider (Keyverse) and a real event queue (Valkey).

Two of these features are qualitatively different from anything built so
far in this repository:

1. **Keyman extraction** derives and persists the *names, roles, and
   inter-organizational relationships of real individuals* -- including
   people at counterparty organizations who never consented to being
   catalogued in a Knowledge Graph -- from free-text record content.
2. **Keyverse login** would wire this repository to the organization's
   real production identity provider and real employee accounts.

Every prior milestone in this repository kept a strict boundary: real
data analysis happens locally only, is never committed, and the public
repository ships synthetic data and pluggable clients only. A working
product feature that logs in with real accounts and displays real
extracted people is a different shape of risk than an optionally-real-
provider-gated test -- it is the shipped, running behavior of a public,
company-name-scrubbed repository, not an opt-in test path.

## Decision

LineageWeave's product features are built and demonstrated against a
**real, working, but synthetic-identity stack**, not the organization's
real production tenant or real record content:

1. **Identity**: a real OIDC-compatible auth flow, stood up via Docker
   Compose (not a "recorded HTTP-shaped adapter" stub -- the login flow
   genuinely works end to end), seeded with synthetic demo accounts,
   corporate codes, and PU codes. Not the organization's real Keyverse
   tenant.
2. **Content**: Keyman extraction, Knowledge Graph traversal, corporate
   hierarchy AI, and lineage popups are demonstrated against synthetic
   fixture records (fabricated organizations, fabricated people) --
   never real extracted third-party names or real record content.
3. **Real data analysis** (embeddings, LLM adjudication, chunking, image
   OCR against the actual real dataset) continues exactly as established
   in milestones 1-3: runs locally only, results never committed to any
   repository, and only aggregate/non-identifying findings are ever
   referenced anywhere else. This ADR does not change that boundary --
   it clarifies that the *product's shipped, running behavior* is a
   separate concern from the *private local analysis*, and only the
   latter touches real content.

## Rationale

- Cataloguing real, named individuals -- especially non-consenting
  external counterparties -- into a persistent, queryable graph is a
  substantial privacy/consent question a development-process instruction
  cannot resolve on those individuals' behalf. Building the *mechanism*
  against synthetic people demonstrates the same capability without that
  question being open.
- A real login flow wired to the organization's actual identity
  provider and real employee accounts, inside a repository whose whole
  point is to never identify the source organization in its files, would
  re-introduce that identification through a different channel (account
  structure, real corporate/PU codes) even with zero literal company-name
  strings in the code.
- This still fully satisfies "no recorded/mocked adapters" -- the auth
  flow, the database, the event queue, and the frontend are all real and
  working; only the *identities and content* flowing through them are
  synthetic, exactly like `lineageweave/fixtures.py` already establishes
  for the DAG-reconstruction pipeline.

## Consequences

- Docker Compose must stand up a genuinely functional OIDC provider (not
  a stub), PostgreSQL, and Valkey -- "it works with fake data" is the bar,
  not "it works."
- If a real deployment against the organization's actual Keyverse tenant
  and real record content is wanted later, that is a distinct, explicit
  decision for a private, non-public deployment -- not something this
  public repository's default configuration does.

## Related

Builds on the data-handling discipline established across this
repository's prior milestones (see `docs/lineage-bi-research-notes.md`
and `AGENTS.md`'s "no real data, ever" rule).
