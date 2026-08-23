# ADR 0114: Preserve buyer continuity for stale summaries

**Decision status:** Accepted on active PR
**Date:** 2026-08-20
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`
**Figma File URL:** https://www.figma.com/design/1Su3lDRmiZdcUs47t1QwIX

## Context

Summary extraction contracts evolve. A persisted summary written by an older
contract can coexist with an imported source body and source-grounded semantic
rows. Treating that row as current would hide a compatibility gap; discarding
it and returning only an error makes the buyer lose a readable summary even
though the source post remains authorized and available.

## Decision

1. `fetch_persisted_summary()` continues to return only the current contract
   by default. Callers must explicitly request a stale projection.
2. The post-summary endpoint first attempts a current summary. If the
   orchestrator is unavailable or the refresh returns an incomplete provider
   response, it returns the last persisted summary with
   `summary_status: "stale"` and its stored contract version. This continuity
   applies immediately to text-only posts. An image-bearing stale summary is
   withheld until its persisted parent and region descriptions are complete,
   then regenerated unless its persisted normalized summary-input SHA-256
   matches the exact current ordered image-evidence text. Legacy rows with no
   input binding are never current. For text-only posts, a normalized-input
   mismatch downgrades a current-contract row to explicit stale continuity.
3. The buyer popup labels the stale state and offers a retry action. Stale
   content is never labelled current and is never used to create new catalog
   identities or semantic rows.
4. A successful contextual-orchestrator refresh remains the only path that
   atomically replaces the stale projection. Failed refreshes never delete the
   prior summary or source body.
5. After provider work and before replacing any summary-owned semantic or
   shared catalog projection, persistence locks and rechecks the current
   source-body SHA-256. For image-bearing input it also requires the exact
   current succeeded content job and re-reads the ordered persisted image
   evidence; that evidence must match the normalized summary input byte for
   byte. Catalog-writing resolution, summary-owned projection replacement,
   and current-payload fetch then complete in that same transaction while the
   source/evidence lock remains held. This deliberately accepts bounded
   enrichment latency under the source lock so stale provider output cannot
   mutate a shared catalog before its evidence is rejected. A source or
   evidence change during provider work therefore leaves both the shared
   catalog and prior summary projection intact and cannot return the
   superseded result as current.

## Consequences

- Buyers can read source-grounded prior context while the semantic gateway is
  unavailable instead of seeing a fail-closed summary panel. Image-bearing
  posts remain fail-closed at the VISION evidence boundary without delaying
  source-post open or source rendering.
- The UI makes the refresh boundary visible, so an old contract cannot be
  mistaken for current ontology evidence.
- A durable background refresh remains useful for large-scale regeneration;
  this decision only fixes the read-path continuity failure.

## Related

- [ADR 0052](0052-plain-orchestrator-semantic-evidence.md)
- [ADR 0100](0100-major-event-requester-processor.md)
- [ADR 0101](0101-enrichment-timeout-does-not-block-summary.md)
- [ADR 0076](0076-paper-grounded-model-policy.md)
