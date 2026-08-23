# ADR 0147 — TEPP topic-lineage evidence in Project History

**Decision status:** Accepted on this active product branch; not protected-main truth
**Implementation maturity:** active-PR
**Date:** 2026-08-23
**Depends on:** ADR 0022, ADR 0084, ADR 0113, ADR 0127, ADR 0136, and TEPP ADR 0012
**Figma File ID:** `SBpgot7uTvMxEaxUwvoc0S`
**Figma frames:** `308:2`, `309:2`, `309:50`, `310:2`

## Context

Project History already exposes one authorized, cutoff-safe timeline from a
post, post-scoped Ask, and Global Ask. Its `connected_post_count` and
`lineage_count` currently describe weak components in LineageWeave's fused
evidence DAG. Those values are useful navigation evidence, but they are not
topic-model lineages and cannot satisfy the TEPP TRSL-TM requirement.

TEPP now defines a bounded CPU `f64` reference estimator and the completed
`tepp.trsl_topic_lineage.v1` artifact. The artifact carries explicit fitted
predecessor/successor associations, artifact-local topic indices,
connectable-post and lineage counts, snapshot/cutoff binding, and the fixed
claim boundary `fitted_topic_association_not_causation`.

## Decision

1. LineageWeave requests topic lineage with TEPP model contract
   `trsl_tm_cpu_f64_v1` and output profile `trsl_topic_lineage_v1`. It does not
   fit, select, rename, or repair topics locally.
2. A completed transport response is accepted only when its `result` is an
   exact, bounded `tepp.trsl_topic_lineage.v1` object. Identifiers, RFC 3339
   cutoff, finite values, edge endpoints, topic indices, duplicate edges,
   top-level counts, and the non-causal inference status are revalidated before
   persistence and again before display.
3. Project History filters validated TEPP sequence edges to the already
   authorized, cutoff-safe project post IDs. It recomputes the displayed
   connectable-post count and lineage count from those filtered edges. Topic
   identity is the pair `(TEPP run id, artifact-local topic index)` so indices
   from different runs cannot collapse.
4. The existing fused `post_lineage_edge` remains the source for navigable
   prior-history paths. It does not supply fallback topic counts. When no
   validated, authorized artifact contributes an edge, topic counts are
   unavailable rather than zero or substituted with DAG components.
5. The shared `ProjectHistoryTimeline` remains the only reader component for
   dedicated Project History, each post, post-scoped Ask, and Global Ask. It
   labels validated numbers as fitted topic association, never causation, and
   renders an explicit unavailable state otherwise. No second timeline or DAG
   overlay is introduced in this increment.
6. CHRONOS/TDT prediction status, topic birth/split/merge, accelerated backend
   parity, production `K` selection, and causal claims remain outside this
   artifact and require their own upstream contract and ADR change.

## Consequences

The count shown beside a project history has one scientific source and one
authorization boundary. A missing TEPP transport, accepted-only receipt,
non-converged estimator, invalid artifact, stale cutoff, or unrelated snapshot
cannot silently become a topic result. Existing temporal history and source
navigation remain readable while topic evidence is unavailable.

## Verification

- strict artifact parser round-trip, tamper, size, count, and scope tests;
- analysis-run request and completed-envelope failure tests;
- PostgreSQL projection tests proving unauthorized and out-of-project endpoints
  do not affect counts;
- shared React component tests and Storybook scenes for validated and
  unavailable states at desktop and phone widths;
- backend and frontend full checks, then exact-head hosted checks and an
  independent review before protected merge.

## References

Blei, D. M., & Lafferty, J. D. (2006). Dynamic topic models. In *Proceedings
of the 23rd International Conference on Machine Learning* (pp. 113–120).
Association for Computing Machinery. https://doi.org/10.1145/1143844.1143859

Roberts, M. E., Stewart, B. M., & Tingley, D. (2019). stm: An R package for
structural topic models. *Journal of Statistical Software, 91*(2), 1–40.
https://doi.org/10.18637/jss.v091.i02

ContextualWisdomLab. (2026). *ADR 0012: Temporal relational shared-latent
topic measurement* [ADR].
https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/adr/0012-temporal-relational-shared-latent-topic-measurement.md
