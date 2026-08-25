# ADR 0172: Persist and explain Event Lineage channel evidence

**Status:** Accepted
**Date:** 2026-08-21
**Issue:** [#274](https://github.com/ContextualWisdomLab/LineageWeave/issues/274)

## Context

`reconstruct()` already computes the winning edge's per-channel scores
(`temporal`, `secondary_key`, `text`, optional `llm`) and RankWeave
fuses them with a weighted convex combination. Production persistence
collapsed each edge to `(parent_post_id, child_post_id, fused_score)`,
so `/api/lineage` and the Event Lineage DAG exposed only the fused score.

A reader could see that two posts were linked but could not answer which
independent signals supported the edge, whether the optional LLM channel
participated, which signal dominated, or how to audit a later
reconstruction after model or weight changes. ADR 0064 already treats
every accepted edge as uncertainty-bearing evidence, not a proven
business fact; that contract was not visible in PostgreSQL or the UI.

This is distinct from typed Knowledge Graph path repair. Event Lineage
explains reconstructed post-to-post links. PostgreSQL remains
authoritative; PROV-O/RDF export is a projection.

## Decision

1. Persist a child table `post_lineage_edge_signal` with a composite
   foreign key to `post_lineage_edge` (`ON DELETE CASCADE`), one row per
   edge and active signal, and exact `numeric(8,6)` score, weight, and
   contribution. No JSONB for billable or auditable numeric facts.
2. Controlled lookup values are globally unique:
   `lineage_signal_temporal`, `lineage_signal_secondary_key`,
   `lineage_signal_text`, `lineage_signal_llm`. The LLM row is omitted
   when the adjudication client is unavailable; it is never fabricated.
3. Weights are the normalized active weights actually used
   (`reconstruct.active_weights`). Contribution is `weight * score` and
   must reconcile with `fused_score` within
   `CHANNEL_EVIDENCE_TOLERANCE` (`1e-6`).
4. Live Event Lineage is replaced atomically. A singleton
   `event_lineage_rebuild` stores reconstruction version, generated-at
   time, minimum fused score, and candidate window; 
   `event_lineage_rebuild_channel` stores the active weight profile.
   Analysis-run reconstruction (`analysis_run_lineage_edge`) stays a
   separate immutable run-scoped table.
   The administrator-triggered live rebuild and PostgreSQL import pass the
   configured contextual-orchestrator adjudication client through the same
   reconstruction boundary only when the exact candidate-pair count is at
   most 5,000. Larger snapshots drop the LLM channel before any provider call
   and renormalize the remaining weights. This is an operational work bound,
   not a model-quality or provider-ranking heuristic. One rebuild never mixes
   LLM and non-LLM weight profiles across edges.
5. `GET /api/lineage` returns an additive `channel_evidence` collection
   on each visible edge (`signal_code`, `signal_label`, `score`,
   `weight`, `contribution`, `rank`) ordered by contribution, then
   controlled signal order. The rebuild profile is returned in the same
   controlled order using `common_lookup_value.display_order`. ABAC never
   reveals evidence for an invisible endpoint.
6. The Event Lineage DAG provides an accessible edge-detail disclosure (not
   hover-only), labels the relation as inferred rather than causal, and
   states when no LLM channel participated only when at least one
   recorded channel exists. Print/export uses the same values.

## Consequences

- Readers can inspect why a connection was selected and distinguish
  inference from source evidence.
- A later rebuild rewrites live Event Lineage as a whole; historic
  meaning is not silently mutated in place.
- Completeness is lower when the LLM channel is unavailable, matching
  ADR 0064: missing channels are dropped and weights renormalize.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
rank fusion outperforms Condorcet and individual rank learning methods.
In *Proceedings of the 32nd International ACM SIGIR Conference on
Research and Development in Information Retrieval* (pp. 758–759). ACM.
https://doi.org/10.1145/1571941.1572114

Hearst, M. A. (1997). TextTiling: Segmenting text into multi-paragraph
subtopic passages. *Computational Linguistics, 23*(1), 33–64.

Jeon, J.-J., Kim, I., Vanli, N. D., & Choi, T. (2021). Logistic
structured interaction model for binary item response (arXiv:2007.08719).
https://arxiv.org/abs/2007.08719

Lebo, T., Sahoo, S., McGuinness, D., Belhajjame, K., Cheney, J.,
Corsar, D., Garijo, D., Soiland-Reyes, S., Zednik, S., & Zhao, J.
(2013). *PROV-O: The PROV ontology* (W3C Recommendation). World Wide
Web Consortium. https://www.w3.org/TR/2013/REC-prov-o-20130430/

Tong, H., Faloutsos, C., & Pan, J.-Y. (2006). Fast random walk with
restart and its applications. In *Proceedings of the Sixth International
Conference on Data Mining* (pp. 613–622). IEEE.
https://doi.org/10.1109/ICDM.2006.70

ADR 0064 (uncertainty-bearing lineage evidence)
ADR 0024 (RankWeave fusion fail-closed)
