# ADR 0124: Evidence-bounded external lineage integration contract

- Status: Proposed
- Date: 2026-08-21

## Context

LineageWeave reconstructs branching lineage from temporal, secondary-key, text, and optional contextual-orchestrator evidence. Naruon and other CWL products may need this capability for selected email, thread, task, commitment, and project evidence, but they must not import LineageWeave application tables, copy its implementation, or disclose provider credentials and unrelated tenant data.

The existing generic `Record` and `reconstruct()` kernel are store-agnostic, but they do not define a stable external trust, serialization, work-budget, historical-cutoff, or truth-status contract.

## Decision

Publish a versioned external analysis contract and pure execution adapter.

The caller supplies only bounded evidence it has already authorized. Each record carries an opaque caller-owned `evidence_ref`, caller grouping, source/truth classification, event/document time, availability time, bounded label, and optional secondary key, project reference, or explicit parent evidence.

The execution boundary:

1. rejects unknown fields and vocabularies;
2. validates offset-aware timestamps and opaque references;
3. enforces record, text, candidate-window, and pair-evaluation bounds;
4. admits historical evidence only when `available_at <= knowledge_cutoff`;
5. keeps explicit caller-observed parent relations separate from reconstructed inferred relations;
6. exposes normalized channel score, weight, and contribution for inferred edges;
7. represents absent optional LLM work as `not_requested` or `unavailable`, never zero;
8. returns project groupings only as `proposed` projections;
9. emits canonical request/result digests; and
10. performs no database access, persistence, provider mutation, or credential handling.

The first public artifact is a Python package contract plus JSON Schema Draft 2020-12. A future separately deployed service or Naruon plugin may wrap the same contract after its own identity, authorization, rate, durability, and operability review.

## Authority boundary

LineageWeave owns its reconstruction algorithm, channel evidence, run semantics, limitations, provenance, and artifact version.

The caller remains authoritative for source access, tenant/workspace authorization, canonical email/thread/project/task identities, provider state, and any decision to accept or reject a proposed relation. An inferred LineageWeave edge does not become provider truth merely because the caller trusts the LineageWeave service.

## Consequences

- Naruon can later consume LineageWeave without direct SQL or mutable source coupling.
- RFC reply/thread observations remain distinguishable from semantic/project lineage.
- Historical runs cannot use evidence first available after the requested cutoff.
- Consumers can retain content-minimized evidence and opaque references.
- The contract does not itself provide remote authentication, persistence, asynchronous jobs, plugin lifecycle, or buyer UI; those remain later consumer/service slices.

## References

See `docs/doctoring/EXTERNAL_LINEAGE_CONTRACT_REFERENCES.md`.
