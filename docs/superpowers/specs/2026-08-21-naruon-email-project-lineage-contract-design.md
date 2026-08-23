# Naruon Email and Project Lineage Contract Design

## Status

Accepted for implementation on 2026-08-21 through the user instruction to continue the cross-repository LineageWeave/Naruon integration work.

## Problem

Naruon owns customer mail, canonical message/thread identities, projects, tasks, commitments, provider credentials, authorization, and provider mutations. LineageWeave owns lineage reconstruction and the evidence explaining that reconstruction. A future integration needs a released, store-agnostic boundary between those products. Direct database access, copied source, and mutable submodules would collapse their authority boundaries.

## Decision

LineageWeave will publish a strict versioned Python contract that accepts bounded caller-authorized evidence and returns only opaque-reference lineage results. The first slice is an in-process, store-agnostic package boundary with no persistence or network access. Naruon can later consume the same schema through a package, service, or reviewed plugin adapter.

The contract has two layers:

1. `external_lineage_contract.py` strictly parses and serializes version `1.0.0` requests and results, enforces bounds, normalizes offset-aware timestamps, and computes deterministic content digests.
2. `external_lineage_analysis.py` adapts authorized records to the existing LineageWeave reconstruction kernel, preserves caller-observed parent relations ahead of inference, exposes per-channel evidence, enforces knowledge cutoffs using `available_at`, and emits project evidence groupings without promoting them to Naruon project truth.

## Authority and truth model

- Caller-supplied records are `observed` or `authoritative_in_caller` evidence.
- Caller-supplied explicit parent relations remain `observed`; they are not reclassified as semantic inference.
- LineageWeave reconstructed continuation edges are `inferred`.
- Project projections are `proposed` groupings from caller-supplied project references; they never claim authoritative Naruon project state.
- Missing LLM evidence is `unavailable`, never a numeric zero.
- Provider credentials, access tokens, mailbox access, and unrelated tenant data are outside the contract.

## Request contract

A request carries:

- immutable `analysis_id`;
- `analysis_scope_code` in `email_lineage`, `project_history`, or `generic_lineage`;
- optional offset-aware `knowledge_cutoff`;
- bounded reconstruction policy, including a maximum of 5,000 declared candidate-pair evaluations;
- one to 500 evidence records.

Each evidence record carries:

- opaque `evidence_ref` and `group_ref`;
- source kind and caller truth status;
- bounded label text;
- offset-aware `occurred_at` and `available_at`;
- optional single `secondary_key` used by the current reconstruction kernel;
- optional `project_ref` used only for proposed project grouping;
- optional explicit parent relation with a controlled relation code.

## Result contract

A result carries:

- deterministic `result_digest`;
- included and cutoff-excluded evidence references;
- LLM channel status;
- stable-sorted edges;
- per-channel score, normalized active weight, and contribution;
- proposed project groupings;
- explicit limitations.

## Temporal safety

Historical analysis is governed by:

```text
available_at <= knowledge_cutoff
```

`occurred_at` describes the event/message time; `available_at` describes when the caller could use the evidence. Evidence first available after the cutoff is excluded even if it describes an earlier event.

## Email safety

RFC reply/thread evidence and semantic lineage are separate:

- `rfc_reply`, `provider_reply`, and `manual_parent` are caller-observed explicit relations.
- `reconstructed_continuation` is a LineageWeave inference.
- Provider thread IDs or caller project keys can be supplied only as opaque secondary keys.
- The package never parses a mailbox, fetches a provider, or mutates mail state.

## Project safety

The result may group evidence under caller-supplied opaque `project_ref` values. This is a proposed evidence projection only. Naruon must apply its own deterministic or human approval policy before updating authoritative project/task/commitment state.

## Error handling

Unknown fields, duplicate references, unsafe or empty identifiers, naive timestamps, non-finite scores, invalid policy bounds, missing explicit parents, forward-inconsistent explicit parents, and unsupported vocabularies fail closed with `LineageContractError` and stable reason codes.

## Testing

The implementation uses TDD and must prove:

- strict parsing and canonical timestamp normalization;
- bounded payloads, duplicate rejection, and pre-provider candidate-pair budget enforcement;
- knowledge-cutoff exclusion by available time;
- observed explicit relations override inferred parent choices;
- RFC reply evidence remains distinct from semantic/project inference;
- absent LLM evidence is explicit;
- deterministic request/result digests;
- no omitted evidence reference can appear in output;
- proposed project groupings never claim caller authority;
- statement and branch coverage for the new production modules are 100%.

## Standards

- RFC 3339 for offset-aware timestamps.
- RFC 5322 and RFC 5256 for preserving email identity/thread evidence distinctions.
- W3C PROV-O for provenance and evidence authority.
- W3C OWL-Time for temporal interpretation boundaries.
