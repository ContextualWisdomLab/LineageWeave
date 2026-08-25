# ADR 0205 — TEPP criterion-validity anchor for lineage channel weights

**Decision status:** Accepted
**Date:** 2026-08-25
**Amends:** [ADR 0003](0003-fast-mlsirm-report-integration.md),
[ADR 0145](0145-psychometric-channel-weight-estimation.md), and
[ADR 0200](0200-channel-weight-reconciliation.md)

## Context

ADR 0145 correctly required an independent outcome before a fast-mlsirm
channel vector could represent Event Lineage. ADR 0200 temporarily activated
an internally anchored vector. That internal covariance is not criterion
validity and is no longer an activation anchor.

TEPP owns calibrated temporal/event measurement. Its accepted transport
envelope is not itself a result; only a completed, persisted, versioned TEPP
result can anchor another model.

## Decision

The sole production anchor method is `tepp_lineage_criterion_v1`. LineageWeave
requests TEPP model contract `tepp-lineage-criterion-v1` and output profile
`lineage_pair_criterion_anchor`, and accepts only result schema
`tepp.lineage_criterion_anchor.v1`. A weight
vector activates only when one normalized `lineage_weight_tepp_anchor` row:

1. references a persisted `analysis_run_tepp_result` and an
   `analysis_run_tepp` run;
2. carries anchor kind `lineage_pair_criterion`, contract version 1, and TEPP
   validity status `accepted`;
3. names the same estimation run, immutable snapshot SHA-256, knowledge
   cutoff, and validated pair count as every weight in the vector; and
4. matches the TEPP analysis run's immutable snapshot and cutoff exactly.

The RFC 3339 request preserves the database cutoff's fractional-second
precision; truncating it would make an otherwise valid exact anchor
permanently unavailable.

The loader also continues to require the exact active-channel set, one
fast-mlsirm run, expected-information method, official estimator version,
finite positive weights summing to one, and complete provenance. Any missing
or mismatched value disables the entire vector; nothing is repaired,
renormalized, inferred, or substituted.

The normative artifact schema is owned by TEPP as
`schemas/lineage_criterion_anchor_v1.json`; LineageWeave only mirrors that
consumer boundary (TEPP PR #237). TEPP decides criterion validity under its versioned contract. LineageWeave
does not calculate a local theta, choose a correlation threshold, or translate
a TEPP statistic into an acceptance rule. Persisting the normalized anchor is
only a foreign-result integrity projection; the authoritative result JSON and
digest remain in `analysis_run_tepp_result`.

## Consequences

- `unanchored_internal_structure` is no longer an authorized product anchor.
- A completed TEPP result without the exact anchor projection cannot activate
  fast-mlsirm weights.
- RankWeave receives a weighted lineage channel only after this gate passes;
  its parameter-free RRF behavior remains unchanged.
