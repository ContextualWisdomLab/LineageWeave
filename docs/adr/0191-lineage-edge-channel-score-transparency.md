# ADR 0191: Persist and surface each lineage edge's per-channel score breakdown

- Status: Accepted
- Date: 2026-08-24

## Context

A reader challenged Event Lineage's trustworthiness directly: two posts
get linked while showing only a single opaque `fused_score` number, with
no way to see *why* `reconstruct()` linked them -- was it because they
happened close in time, shared a project code, had similar text, or an
`llm` channel judged them related? The reader's underlying claim was
stronger still: a link should require the two posts' *overall meaning* to
be causally related, not merely statistically similar.

That stronger claim was assessed against the literature (discourse/causal
relation parsing -- Prasad et al., 2008; Mirza & Tonelli, 2014; Dunietz et
al., 2017; narrative/event-coherence modeling -- Chambers & Jurafsky, 2008,
2009; Barzilay & Lapata, 2008) and found to be *less* mature and reliable
than the record-linkage approach (Christen, 2012) this codebase already
uses deliberately (`lineageweave/reconstruct.py`'s own validation: naive
linking agreed with an independent grouping signal only 2.6% of the time,
which is why several weak channels are fused instead of trusting one).
Implicit causal inference -- the case that matters here, since internal
business posts rarely write "because" -- sits at roughly 20-30% F1 in the
CoNLL-2016 shared task on implicit discourse relations; bolting a causal
classifier onto this pipeline would replace a well-characterized weak-signal
error rate with a worse-characterized one, dressed up as more scientific.

The system already disclaims causality in two places
(`frontend/src/LineageDag.tsx`'s header description and its
"Inference boundary" note: "Edges explain reconstructed continuation only.
They are not causal or authoritative facts."), but that disclaimer sits at
tooltip/microcopy depth while the only structural evidence shown is one
undifferentiated number. The real gap is not the algorithm -- it is that
the algorithm's own reasoning (`Edge.channel_scores`, already computed by
`reconstruct._best_parent()`) was discarded before it ever reached the
database or the reader.

## Decision

- Add `post_lineage_edge_channel_score` (migration 0177): one row per
  `(parent_post_id, child_post_id, channel_code)`, cascade-deleted with its
  parent `post_lineage_edge` row. `channel_code` is constrained to the
  four channels `reconstruct()` actually produces (`temporal`,
  `secondary_key`, `text`, `llm`) rather than routed through
  `common_lookup_value`, matching how these names are already used as
  literal Python dict keys in `lineageweave/channels.py` and
  `DEFAULT_CHANNEL_WEIGHTS` -- they are an internal algorithm vocabulary,
  not reader-facing domain vocabulary.
- `backend/app/lineage_ingestion.py::persist_lineage_edges` writes each
  edge's `channel_scores` alongside its `fused_score`. A channel absent
  from `Edge.channel_scores` (e.g. `llm` when no `AdjudicationClient` was
  configured) is simply not written -- never a fabricated zero, matching
  ADR 0064's "a missing channel is dropped, never replaced with a
  fabricated score" rule.
- `visible_lineage_graph` fetches `post_lineage_edge_channel_score` and
  attaches each edge's breakdown as `channel_scores: Record<string,
  number>` in the `GET /api/lineage` response. `frontend/src/api.ts`'s
  `LineageGraphEdge` gains this field as required (not optional) -- the
  backend always includes it, even as `{}` for edges reconstructed before
  this ADR.
- `LineageDag.tsx`'s already-open (not hover-gated) Evidence trail table
  gains a fourth "Channel breakdown" column rendering each present
  channel's score in a fixed, documented order (`temporal`,
  `secondary_key`, `text`, `llm`), labeled with reader-facing names
  ("Temporal proximity", "Secondary key match", "Text similarity", "LLM
  judgment") translated across all five product locales. An unrecognized
  future channel code falls back to showing the raw code rather than
  silently dropping evidence the backend sent.
- No change to `reconstruct()`'s fusion logic, weights, or floor. This ADR
  is purely a transparency/evidence-surfacing decision, not an accuracy
  change.

## Consequences

- A reader can now see, for any edge, the exact per-channel evidence that
  produced its `fused_score` -- turning "trust the number" into "inspect
  the reasoning," directly answering the "why does this even connect"
  class of challenge without pretending the system computes causality it
  does not.
- Historical edges persisted before migration 0177 have no channel-score
  rows and render an empty breakdown cell; a corpus-wide `POST
  /api/lineage/rebuild` repopulates them, same as any other reconstruct-time
  evidence in this system.
- Does not address the separate, larger question (also raised, and
  correctly *not* solved here) of whether Knowledge-Graph-derived entity
  identity should ever veto a link (e.g. two posts with different primary
  counterparties). That is a genuine architecture decision changing what
  "linked" means and needs its own ADR, matching this repo's established
  pattern of not soloing grouping/architecture calls (ADR 0064's
  grouping-fallback question remains open for the same reason).

## References — APA 7th

Barzilay, R., & Lapata, M. (2008). Modeling local coherence: An
entity-based approach. *Computational Linguistics, 34*(1), 1-34.

Chambers, N., & Jurafsky, D. (2008). Unsupervised learning of narrative
event chains. In *Proceedings of ACL-08: HLT* (pp. 789-797). Association
for Computational Linguistics.

Chambers, N., & Jurafsky, D. (2009). Unsupervised learning of narrative
schemas and their participants. In *Proceedings of the Joint Conference of
the 47th Annual Meeting of the ACL and the 4th International Joint
Conference on Natural Language Processing of the AFNLP* (pp. 602-610).
Association for Computational Linguistics.

Christen, P. (2012). *Data matching: Concepts and techniques for record
linkage, entity resolution, and duplicate detection*. Springer.
https://doi.org/10.1007/978-3-642-31164-2

Dunietz, J., Levin, L., & Carbonell, J. (2017). The BECauSE corpus 2.0:
Annotating causality and overlapping relations. In *Proceedings of the
11th Linguistic Annotation Workshop* (pp. 95-104). Association for
Computational Linguistics.

Mirza, P., & Tonelli, S. (2014). An analysis of causality between events
and its relation to temporal information. In *Proceedings of COLING 2014,
the 25th International Conference on Computational Linguistics: Technical
Papers* (pp. 2097-2106). Dublin City University and Association for
Computational Linguistics.

Prasad, R., Dinesh, N., Lee, A., Miltsakaki, E., Robaldo, L., Joshi, A., &
Webber, B. (2008). The Penn Discourse TreeBank 2.0. In *Proceedings of the
Sixth International Conference on Language Resources and Evaluation
(LREC'08)* (pp. 2961-2968). European Language Resources Association.
