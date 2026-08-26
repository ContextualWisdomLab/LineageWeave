# ADR 0231: External lineage arithmetic authority

**Status:** Accepted  
**Date:** 2026-08-26

## Context

LineageWeave is the authorization, provenance, orchestration, persistence, and
evidence-navigation product. It is not the owner of mathematical or
psychometric computation. The current reconstruction path still calculates
temporal, secondary-key, and text scores, renormalizes channel weights, applies
a fixed candidate window of 50, and applies a fixed fused-score floor of 0.3.
Those local defaults are neither an estimator result nor an owning-library
contract, so they cannot remain a production authority.

## Decision

LineageWeave will retain source admission, knowledge-cutoff enforcement,
opaque evidence references, run orchestration, provenance persistence, and UI.
It will consume versioned, provenance-bearing results from these owners:

- TEPP owns temporal-event and psychometric measurement in Rust.
- fast-mlsirm owns multilevel psychometric estimation and estimated weights in
  Rust.
- RankWeave owns retrieval fusion, contribution evidence, evaluation, and
  policy selection; its calculation core must satisfy the ecosystem Rust-core
  requirement before it becomes the production lineage arithmetic boundary.
- ThreadWeave owns deterministic reference-thread assembly.

The external result contract must carry the immutable implementation revision,
model or policy revision, input-evidence digest, availability/knowledge cutoff,
active channels, estimated parameters, and limitations. LineageWeave validates
and persists that envelope; it does not recompute it. Missing or incompatible
owners make reconstruction unavailable. There is no Python, heuristic, fixed
threshold, fixed window, or hand-authored-weight fallback.

## Migration

1. Publish the owning Rust calculation contracts and synthetic consumer
   fixtures without database or provider access.
2. Add a fail-closed LineageWeave adapter and exact-envelope persistence.
3. Run parity tests only as migration evidence; do not retain a second engine.
4. Remove local scoring, weight renormalization, thresholding, and candidate
   window arithmetic after the released owner is pinned.

Until step 4, the existing local path is legacy demo behavior and not
production calculation evidence.

## Consequences

- LineageWeave remains independently useful for governed evidence navigation,
  while calculation authorities remain independently releasable modules.
- A provider outage is visible as unavailable rather than an invented score.
- The previously merged external-lineage contract from stack PR #343 must not
  be resurrected unchanged because it imports local reconstruction arithmetic.

## References

ContextualWisdomLab. (2026a). *fast-mlsirm product requirements* [Software
documentation]. https://github.com/ContextualWisdomLab/fast-mlsirm

ContextualWisdomLab. (2026b). *RankWeave architecture* [Software
documentation]. https://github.com/ContextualWisdomLab/RankWeave

ContextualWisdomLab. (2026c). *TEPP product requirements* [Software
documentation]. https://github.com/ContextualWisdomLab/TEPP
