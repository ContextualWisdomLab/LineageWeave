# ADR 0101 — Enrichment timeout does not block source-grounded summary

**Decision status:** Accepted on active PR
**Date:** 2026-08-20
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`
**Figma File URL:** https://www.figma.com/design/1Su3lDRmiZdcUs47t1QwIX

## Context

Post summary persistence enriches organization actors through the shared
corporate-hierarchy resolver. A contextual-orchestrator inference timeout was
previously allowed to escape that resolver, so a source-grounded summary
could fail with HTTP 500 before its events, roles, and requester/processor
actions were stored.

## Decision

`get_or_create_corporate_entity` catches provider transport and timeout
failures from hierarchy inference and returns `None`. Summary persistence
continues with the actor row unbound. The source-derived event, R&R, action,
and evidence rows are still committed; no catalog row, placeholder actor, or
guessed organization is created.

This is not a silent success for enrichment: the missing catalog binding
remains visible as an unresolved/unbound identity and can be retried by a
later explicit extraction. Only the enrichment channel is unavailable; the
source summary is not discarded.

## Rationale

The existing ADR 0010/0026 boundary distinguishes a catalog miss or tie from
a verified identity. A transient orchestrator failure is neither a miss nor a
negative identity claim. Keeping it unbound preserves evidence while avoiding
the fail-closed screen behavior that prevents a buyer from reading the source
post.

## Consequences

- Buyer summary requests no longer lose source-grounded content because
  organization enrichment timed out.
- A timeout still produces no catalog identity and therefore no fabricated KG
  edge or organization binding.
- A retry path remains necessary for eventual catalog enrichment; this ADR
  does not turn a failed inference into a successful one.

## Related

- [ADR 0010](0010-corporate-hierarchy-auto-creation.md)
- [ADR 0026](0026-tied-organization-similarity.md)
- [ADR 0102](0102-major-event-requester-processor.md)
