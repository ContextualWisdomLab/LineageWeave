# ADR 0119: Publish a bounded LineageWeave provider contract

- Status: Accepted on this PR; not main-branch truth until merged
- Date: 2026-08-21
- Decision owners: LineageWeave maintainers

## Context

Naruon owns mailbox/provider access, canonical source identities, workspace
authorization, and provider mutations. LineageWeave owns reconstruction,
channel evidence, cutoff semantics, and inferred lineage. Sharing application
tables or copying LineageWeave internals into Naruon would create a second
authority and bypass the existing ABAC boundary.

## Decision

`lineageweave.lineage_contract` is the provider-side versioned boundary for a
bounded, store-agnostic analysis request. It uses immutable Python dataclasses
and canonical JSON (`lineage-analysis/v1`) so a future HTTP or generated SDK
adapter can be added without changing reconstruction.

- Requests carry an opaque caller-owned `evidence_ref`, an opaque
  `authorization_scope_ref`, separate occurred/available clocks, bounded text,
  optional separate RFC/provider email evidence, and non-authoritative project
  hints.
- A request is valid only when evidence references are unique, clocks are
  timezone-aware, payload budgets are bounded, and hints point to submitted
  evidence.
- `knowledge_cutoff` excludes evidence whose `available_at` is later. Excluded
  evidence is reported as a limitation and cannot appear in any edge.
- The implementation reuses `lineage_edge_specs()` and returns edges only in
  terms of submitted opaque evidence references, with channel scores and
  explicit `inferred` truth status.
- Missing contextual-orchestrator adjudication is an explicit limitation; it
  is not a zero score or a fabricated negative signal.
- The request digest is the idempotency identity. Persistence, retry, tenant
  authorization, and provider actions remain the consumer's responsibility.

LineageWeave does not read Naruon's database, receive Naruon credentials, or
claim authoritative project/task/calendar status. Naruon may adopt a proposed
projection only through its own policy.

## Consequences

The provider can be tested with synthetic Naruon-shaped evidence and shipped
independently. A service adapter can later expose the same JSON without
leaking database identifiers. The first version intentionally does not create
project projections or provider mutations; those require a separate reviewed
contract and evidence policy.

## Research and standards grounding

- World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
- Internet Engineering Task Force. (2008). *RFC 5322: Internet message format*.
- World Wide Web Consortium. (2017). *OWL-Time ontology*.

These standards support explicit provenance, separate message evidence, and
distinct event/availability clocks; they do not authorize a cross-service
database dependency.
