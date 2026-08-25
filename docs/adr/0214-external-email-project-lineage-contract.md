# ADR 0214: Publish a bounded external email/project lineage contract

- Status: Accepted
- Date: 2026-08-21

## Context

Naruon owns customer mail/calendar/file access, canonical message/thread identities, projects, tasks, commitments, provider credentials, authorization, and provider mutations. LineageWeave owns evidence-fused lineage reconstruction and the provenance explaining that reconstruction. Future integration must not give either product direct SQL access to the other's application database, duplicate source authority, or depend on a mutable branch/submodule.

Email thread facts also have different truth semantics from reconstructed semantic continuation. RFC `Message-ID`, `References`, and `In-Reply-To` evidence may establish a caller-observed reply relation, while LineageWeave text/temporal/project signals produce an inferred relation. Flattening both into one unexplained score would make buyer correction and audit impossible.

## Decision

LineageWeave publishes contract version `1.0.0` through:

- `lineageweave.external_lineage_contract` for strict immutable request/result shapes, canonical serialization, bounds, and deterministic digests;
- `lineageweave.external_lineage_analysis` for adapting caller-authorized evidence to the existing reconstruction kernel.

The initial implementation is a store-agnostic Python package boundary. It performs no database, mailbox, provider, or network operation. A later service or Naruon plugin adapter must preserve the same JSON Schema and truth boundaries.

Execution requires an explicit calibrated convex channel-weight vector. The
adapter validates but never estimates, repairs, or invents that vector. The
three core channels are mandatory; the optional LLM channel is admitted only
when both a calibrated LLM weight and an available orchestrator client exist.
The calibrated vector must exactly match the channels executed for the request;
an inactive LLM channel makes a four-channel vector invalid rather than causing
the core weights to be silently renormalized.
Weight estimation and provenance remain governed by ADR 0200 and the owning
product loader.

The caller supplies opaque evidence references, bounded text labels, occurrence and availability clocks, an optional secondary key, an optional project reference, and an optional caller-observed parent relation. Explicit observed parent relations replace an inferred parent for the same child and must form an acyclic graph. Reconstructed continuation remains `inferred`. Project groupings remain `proposed`.

An admitted child with an explicit observed parent is not rescored for an alternative inferred parent and consumes no optional LLM/provider call or inferred-pair budget. The record remains in temporal history and may still be an eligible candidate parent for a later record. This preserves observed authority without weakening downstream lineage reconstruction.

The caller also supplies `maximum_pair_evaluations` in the bounded policy. The package computes the exact inferred candidate-parent pair count after knowledge-cutoff filtering, excluding children whose parent is already caller-observed, and rejects work above the declared budget before any optional LLM/provider call. Contract v1 caps the declared budget at 5,000 pairs.

Historical requests include evidence only when:

```text
available_at <= knowledge_cutoff
```

Evidence becoming available after the cutoff is excluded even when it describes an earlier occurrence.

## Consequences

- Naruon can eventually consume a released artifact without exposing credentials or application tables.
- RFC reply/thread evidence stays distinguishable from semantic lineage.
- Caller-observed children are never disclosed to an optional model merely to calculate an inferred edge that would be discarded.
- The optional LLM channel is explicit as `not_requested`, `unavailable`,
  `not_used`, or `completed`; admission without a provider call is never
  reported as completion, and missing output is never zero.
- A missing or malformed calibrated weight vector fails closed before scoring.
- A calibrated vector containing an inactive channel fails closed instead of
  being repaired or renormalized into a different measurement.
- Canonical serialization and SHA-256 digesting are deterministic for a given request or result. Repeatability of model-backed scores additionally requires a pinned LineageWeave release, adjudicator implementation, provider/model revision, and model-side determinism policy.
- Explicit parent cycles and analysis work above the caller-approved pair budget fail closed before inference.
- Project evidence can inform Naruon without mutating authoritative project/task/provider state.
- The single generic secondary key reflects the current core kernel. Multiple independent typed secondary-key channels remain a future contract revision rather than being silently flattened.

## References

See `docs/doctoring/EXTERNAL_LINEAGE_CONTRACT_REFERENCES.md`.
