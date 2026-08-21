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
  bounded email reference collections, and bounded non-authoritative project
  hints.
- A request is valid only when evidence references are unique, clocks are
  timezone-aware, payload budgets are bounded, and hints point to submitted
  evidence.
- `knowledge_cutoff` excludes evidence whose `available_at` is later. Excluded
  evidence is reported as a limitation and cannot appear in any edge.
- The implementation reuses the existing `reconstruct()` pipeline and returns edges only in
  terms of submitted opaque evidence references, with channel scores and
  explicit `inferred` truth status.
- Missing contextual-orchestrator adjudication is an explicit limitation; it
  is not a zero score or a fabricated negative signal.
- Provider exceptions and non-finite or out-of-range provider scores are
  converted to stable contract errors at this boundary. Raw provider response
  bodies and exception text never cross the public contract.
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
- National Institute of Standards and Technology. (2020). *Security and
  privacy controls for information systems and organizations: NIST SP
  800-53 Rev. 5*. https://doi.org/10.6028/NIST.SP.800-53r5
- OWASP Foundation. (2024). *Application Security Verification Standard
  5.0.0*. https://github.com/OWASP/ASVS
- MITRE. (n.d.). *CWE-209: Generation of error message containing sensitive
  information*. https://cwe.mitre.org/data/definitions/209.html

These standards support explicit provenance, separate message evidence,
distinct event/availability clocks, and prevention of sensitive information in
error messages; they do not authorize a cross-service database dependency.
