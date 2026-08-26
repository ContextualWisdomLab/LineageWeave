# ADR 0132 — TEPP topic-lineage consumption boundary (TRSL-TM + CHRONOS/TDT)

**Decision status:** Accepted
**Implementation maturity:** boundary-accepted; evidence/inference/prediction
mark primitive implemented (`frontend/src/components/EvidenceStatusMark.tsx`,
below); DAG topic-thread wiring and runtime remain open
**Date:** 2026-08-22
**Depends on:** ADR 0022 (authorized TEPP start); ADR 0064 (lineage evidence
and tree assembly); ADR 0084 (research-grounded lineage and ontology policy)
**Refs:** TEPP ADR 0012 (Temporal Relational Shared-Latent Topic
Measurement); TEPP ADR 0016 (TDT, CHRONOS, and Event Ontology intelligence
boundary)

## Context

ADR 0084 already separates mention detection / lineage-instance
construction (LineageWeave's own evidence-fusion engine) from calibrated
measurement, which stays a TEPP wire-contract boundary that is never
reimplemented locally. That separation did not yet have a topic-identity
counterpart: `zcrht811_export_rows` board posts are scattered across time
with no thread connecting a post to the earlier/later posts that share its
underlying commercial topic (a competitor mention, a market trend, a sales
opportunity) the way a Git branch connects commits.

TEPP's own accepted-target architecture already defines this problem
precisely:

- TEPP ADR 0012 adopts **Temporal Relational Shared-Latent Topic
  Measurement (TRSL-TM)**: one global topic identity set per modeled
  period, where topics may be active, dormant, or reactivated over time
  without losing identity, and topic birth/split/merge/retirement is an
  explicit lineage extension — not an implicit side effect of fitting
  unrelated time slices.
- TEPP ADR 0016 separates Event Ontology, TDT-style detection/tracking, and
  CHRONOS-style reasoning (semantic/neural event-schema
  extraction/prediction plus symbolic temporal-consistency reasoning).
  Every output carries an evidence / inference / prediction status and
  provenance; a prediction is never silently converted into historical
  fact.

TEPP is currently a foundation-slice (`crates/tepp_api` exposes only
`AnalysisRunRequest` / `AnalysisRunAccepted`; a completed-result contract is
still open — TEPP issue #156). Standing up a local topic model or event
predictor to fill that gap would repeat exactly the "invented psychometric
substitute" ADR 0084 and the tepp-readiness discipline already forbid.

## Decision

1. LineageWeave does not compute topic identity, topic
   birth/split/merge/retirement, event-schema predictions, or temporal-
   consistency verdicts locally. These remain TEPP's TRSL-TM (ADR 0012) and
   CHRONOS/TDT (ADR 0016) computations, requested through `tepp_client` the
   same way `analysis_run_start.py` requests a measurement run (ADR 0022).
2. A new analysis-run kind, topic-lineage, is added alongside the existing
   lineage / TEPP / period-report kinds (ADR 0013 registry). Requesting it
   builds a TEPP request payload from the run's idempotency key, snapshot
   digest, knowledge cutoff, and corporate-entity workspace id — never post
   bodies or a fabricated topic label — and submits through `TeppClient`.
3. An empty `TEPP_TRANSPORT_URL`, or a TEPP response that omits the
   versioned topic-identity/CHRONOS-status envelope, appends Failed with a
   machine-readable reason (`tepp_not_available` /
   `tepp_topic_contract_unavailable`), mirroring ADR 0022. Failed is
   terminal; after the authority recovers, LineageWeave creates a new Pending
   current-snapshot run and submits it through the normal start/outbox path.
4. When TEPP does publish the topic-identity and CHRONOS-status envelope,
   LineageWeave persists it into a new topic-identity-thread projection
   (3NF, two-word snake_case, partitioned by corporate-entity + observed
   period to avoid a hot partition on the shared post table) that links
   existing posts to TEPP topic ids and carries each edge's evidence /
   inference / prediction status verbatim. This projection extends — it
   does not replace — the existing evidence-fusion lineage tree (ADR
   0064/0084); a post can appear in both the fusion-based lineage DAG and a
   TEPP topic thread, and the UI keeps the two visually distinct.
5. The frontend Event Lineage DAG gains a topic-thread overlay: nodes/edges
   sourced from TEPP render with a distinct visual channel (color/pattern
   token, not color alone, for accessibility) per evidence / inference /
   prediction status, and render nothing (not a placeholder guess) for a
   topic-lineage run that is Pending or Failed. Storybook stories cover
   Pending, Failed (`tepp_not_available`, `tepp_topic_contract_unavailable`),
   and each CHRONOS status; a Playwright e2e spec exercises the golden path
   once a topic-identity envelope exists and the fail-closed path when it
   does not.

```mermaid
sequenceDiagram
    participant Operator
    participant API
    participant TeppClient
    participant Registry
    Operator->>API: POST /api/analysis-runs (kind=topic_lineage)
    API-->>Operator: Pending topic-lineage request
    Operator->>API: POST /api/analysis-runs/{id}/start
    Registry->>Registry: Running
    API->>TeppClient: TopicLineageRequest v1 (TRSL-TM + CHRONOS/TDT)
    alt TeppNotAvailable
        Registry->>Registry: Failed tepp_not_available
    else envelope lacks topic-identity/CHRONOS contract
        Registry->>Registry: Failed tepp_topic_contract_unavailable
    else versioned envelope present
        Registry->>Registry: Succeeded; persist topic-identity threads + CHRONOS status
    end
    API-->>Operator: run status + evidence/inference/prediction detail
    Note over Operator,Registry: Failed stays terminal; Retry creates and starts a new run
```

### Implementation note: the status-mark primitive ships ahead of the wiring

Decision item 5's "distinct visual channel, not color alone" requirement is
implemented now as `EvidenceStatusMark` (`frontend/src/components/
EvidenceStatusMark.tsx`, i18n in `evidenceStatusI18n.ts`, tokens in
`styles/tokens.css`): a reusable badge distinguishing evidence / inference /
prediction by label text and glyph shape (`●` / `◆` / `△`) in addition to
color, satisfying WCAG 1.4.1 with redundant, testable channels (see its
Storybook stories and `EvidenceStatusMark.test.tsx`). It is presentational
only — every call site must supply `status` from a real TEPP-sourced
envelope; the component never infers or invents one. Wiring it into
`LineageDag`'s topic-thread overlay is the remaining step once TEPP issue 156
publishes the topic-identity/CHRONOS-status envelope this ADR's
decision 3-4 depend on; until then, no topic-lineage run reaches Succeeded,
so there is no envelope to source a `status` prop from.

No Figma frame exists yet for this primitive (cf. ADR 0002's precedent for
recording that gap rather than fabricating a frame reference); add the file
ID here when a designer produces one.

## Considered alternatives

1. **Fit a local LDA/BERTopic-style model over `zcrht811_export_rows` now,
   swap to TEPP later** — rejected: an ungrounded local topic model is
   exactly the invented substitute ADR 0084/CLAUDE.md forbid, and its
   outputs (unstable topic identity, no posterior uncertainty, no temporal-
   identity contract) would not be swap-compatible with TRSL-TM's
   logistic-normal, posterior-bearing topic coordinates.
2. **Treat the existing evidence-fusion lineage DAG (ADR 0064/0084) as
   sufficient and skip a topic-identity dimension** — rejected: fusion-based
   lineage links posts by lexical/embedding/temporal similarity, not by a
   calibrated, longitudinally stable topic identity; it cannot express
   topic birth/split/merge/retirement the way TRSL-TM can.
3. **Block all topic-lineage UI until TEPP ships the full contract** —
   rejected: the fail-closed Pending/Failed states are themselves a
   product (ADR 0022 precedent), and the UI/Storybook/e2e scaffolding can
   and should be built and reviewable now so the feature activates the
   moment TEPP's contract lands, instead of starting from zero then.

## Consequences

- LineageWeave's topic-lineage feature is fully specified and reviewable
  before TEPP exposes its topic-identity/CHRONOS envelope; only the
  transport needs to be connected once TEPP is ready (tracked in memory
  `tepp-readiness-watch` and TEPP issue #156).
- The evidence / inference / prediction distinction from TEPP ADR 0016
  propagates end to end — API response, DB row, and UI rendering — so a
  CHRONOS prediction can never be flattened into a fact anywhere in this
  product.
- Coordination cost: this ADR's runtime activation depends on a
  cross-repository contract change in TEPP; `docs/product-technical-gap-
  baseline.md` must track that dependency explicitly rather than mark this
  gap closed prematurely.

## References — APA 7th

ContextualWisdomLab. (2026). *TEPP* [Computer software]. GitHub.
https://github.com/ContextualWisdomLab/TEPP

ContextualWisdomLab. (2026). *ADR 0012: Temporal relational shared-latent
topic measurement* [ADR]. GitHub.
https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/adr/0012-temporal-relational-shared-latent-topic-measurement.md

ContextualWisdomLab. (2026). *ADR 0016: TDT, CHRONOS, and Event Ontology
intelligence boundary* [ADR]. GitHub.
https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/adr/0016-tdt-chronos-event-intelligence-boundary.md

Roberts, M. E., Stewart, B. M., & Tingley, D. (2019). stm: An R package for
structural topic models. *Journal of Statistical Software, 91*(2), 1–40.
https://doi.org/10.18637/jss.v091.i02

Mimno, D., Wallach, H. M., Naradowsky, J., Smith, D. A., & McCallum, A.
(2009). Polylingual topic models. In *Proceedings of the 2009 Conference on
Empirical Methods in Natural Language Processing* (pp. 880–889). Association
for Computational Linguistics. https://aclanthology.org/D09-1092/

Allan, J. (Ed.). (2002). *Topic detection and tracking: Event-based
information organization*. Springer. https://doi.org/10.1007/978-1-4615-0933-2

Kalashnikov, D. V., Chen, Z., Mehrotra, S., & Nuray-Turan, R. (2007). CHRONOS:
Facilitating history discovery by linking temporal records. *Proceedings of
the VLDB Endowment*. https://doi.org/10.14778/2367502.2367559
