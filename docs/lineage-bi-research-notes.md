# Research notes: what this design is grounded in

**Status:** living document -- update when the channel set or fusion method changes.

## The problem this is answering

Given a pile of short, timestamped records that are only loosely grouped
(by an account id, a project code, a customer id -- something coarse), and
no explicit "this follows from that" link between them, reconstruct the
implicit thread structure: which record is a continuation of which, so the
whole pile can be browsed as a set of branching histories instead of a flat
list.

This is deliberately **not** the same question
[TEPP](https://github.com/ContextualWisdomLab/TEPP) (Temporal Event
Psychometrics Platform) answers. TEPP estimates calibrated latent-construct
scores and trajectories from evidence-grounded text under an explicit
multilevel/multiple-membership model (its own literature register,
`docs/research/standards-and-literature.md`, is built on Raudenbush and
Bryk (2002) and Browne et al. (2001) -- see below). LineageWeave's channel
scores are a much weaker claim: "this pair of records plausibly continues
one another," produced by fast, cheap heuristics plus an optional LLM
judgment, with no calibration or uncertainty quantification. TEPP's own
published integration contract for external consumers
(`docs/connectors/naruon-artifact-consumer.md`) is explicit that a
consumer "must not treat lexical heuristics as TEPP topic inference" --
this repo takes that instruction at face value: it never presents its
lineage-graph output as TEPP's kind of measurement, and it consumes TEPP
(when TEPP's HTTP layer exists) only as a request for TEPP's own analysis,
never by reading TEPP's tables or reimplementing TEPP's model.

## Why no single signal is trusted

Grouping records by a coarse key and simply linking each one to its most
recent predecessor is the obvious first idea. It does not work well in
practice: a bounded validation run against a real ~44,000-row dataset of
short business records grouped by customer found that this naive
predecessor-linking heuristic agreed with an independent, coarser grouping
signal (a project code) only 2.6% of the time. Most of a customer's next
record is *not* about the same named project as the one right before it --
scattered, multi-topic histories are the normal case, not the exception,
which is exactly the premise this project exists to address.

Topic Detection and Tracking research reached the same conclusion for news
story linking two decades earlier: single-signal nearest-neighbor linking
between short text items is unreliable, and TDT systems fuse multiple
detectors and report calibrated, probabilistic link/no-link decisions
rather than a single deterministic answer (Allan, 2002). LineageWeave
follows the same shape at much smaller scale: several independent,
individually weak channels (`lineageweave/channels.py`), fused into one
score per candidate edge, with a minimum-score floor below which a record
is left as its own root rather than force-attached to the least-bad
available candidate (`reconstruct.DEFAULT_MIN_FUSED_SCORE`).

## The ADR-0016 three-layer boundary

TEPP's [ADR 0016](https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/adr/0016-tdt-chronos-event-intelligence-boundary.md)
separates event intelligence into three layers so that a prediction, a
topical link, and a proven fact never get silently collapsed into one
undifferentiated "event model." LineageWeave's own pipeline
(`reconstruct.py`) follows the same three-way separation, at the smaller
scale of record-to-record lineage rather than event ontology:

1. **Mention/instance separation** (Doddington et al., 2004 -- the ACE
   program's distinction between a surface detection and a resolved event
   structure). Every `Record` fed into `reconstruct()` is a fallible
   mention; an `Edge` is only an accepted lineage *instance* once its fused
   score clears `DEFAULT_MIN_FUSED_SCORE` -- below that floor, a record
   stays its own root (`Tree.roots`) rather than being silently attached as
   if the link were established fact.
2. **Calibrated detection/tracking** (Allan, 2002 -- TDT). Every `Edge`
   keeps its `channel_scores` breakdown, win or lose, so a fused decision
   can be audited and re-evaluated rather than trusted as a bare boolean.
3. **Temporal-consistency reasoning** (Anagnostopoulos et al., 2013 --
   CHRONOS; grounded in Allen's, 1983, interval algebra). A candidate
   parent is only ever drawn from records that occurred at or before the
   record being linked (`reconstruct.py`'s candidate window is built from
   `sorted(..., key=lambda r: r.occurred_at)` and only looks backward) --
   the "before-or-equal" relation is enforced structurally, not just hoped
   for, so no promoted edge can ever point forward in time.

This is also why LineageWeave never presents its own output as TEPP-grade
measurement (see "The problem this is answering," above): TEPP's ADR 0016
requires every event/relation to carry an explicit evidence/inference/
prediction status, and treats TDT/CHRONOS-style outputs as "probabilistic
measurement/detection evidence" that "can feed psychometric and
longitudinal models only through versioned, uncertainty-bearing
contracts" -- LineageWeave's fused scores are exactly that kind of
uncertainty-bearing, non-authoritative evidence, never promoted to fact
outside this repo's own DAG view.

## Channels and their grounding

| Channel | What it does | Grounded in |
|---|---|---|
| `temporal` | Prefers a candidate parent closer in time | Standard recency prior in event/story linking (Allan, 2002) |
| `secondary_key` | Rewards a shared finer-grained key (e.g. project code) | Coarse blocking key, the standard first step in record-linkage pipelines (Fellegi & Sunter, 1969; Christen, 2012) |
| `text` | String-similarity between record labels | A dependency-free stand-in for an embedding-cosine channel (`lineageweave.embedding_client`); same role, cheaper, swappable without touching the fusion code |
| `llm` | An LLM's judged confidence that one record follows from another | Optional, highest-weighted when available -- see "LLM adjudication" below |

Channel scores are fused with a **weighted convex combination**
(`rankweave.weighted_convex_fuse`), the simpler of RankWeave's two fusion
strategies (its other, reciprocal-rank fusion, is grounded in Cormack et
al., 2009) -- convex combination was chosen here because every channel
already produces a comparable `[0, 1]` score rather than only a ranking,
so combining raw scores loses less information than converting everything
to ranks first.

## Tree assembly

Once each record has (at most) one chosen parent, the edges are threaded
into trees with [ThreadWeave](https://github.com/ContextualWisdomLab/ThreadWeave),
an implementation of the JWZ message-threading algorithm (Zawinski, 1997;
formalized for IMAP as RFC 5256, Crispin & Murchison, 2008). JWZ threading
is normally applied to email `References`/`In-Reply-To` headers; the
headers here are supplied by LineageWeave's own fusion step instead of a
mail client, which the algorithm does not care about -- it only needs a
message id and a reference list per item.

## LLM adjudication

When configured (`lineageweave.adjudication_client.ContextualOrchestratorAdjudicationClient`),
the `llm` channel calls a running
[contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)
instance with `mode="verify"` and `reasoning_effort="high"` -- one worker
call plus one checked verifier judgment, rather than either a bare
unverified guess or the full four-step thinker/worker/verifier/synthesizer
workflow. This follows the test-time-compute allocation argument
contextual-orchestrator is built around: allocate more reasoning effort to
the low-volume, judgment-heavy calls (adjudicating one candidate edge) and
none to the high-volume, cheap ones (the `text`/`temporal`/`secondary_key`
channels), rather than spending a fixed budget on every call regardless of
how much judgment it actually needs.

## References (APA 7th)

Allan, J. (Ed.). (2002). *Topic detection and tracking: Event-based information organization*. Kluwer Academic Publishers.

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM*, *26*(11), 832-843. https://doi.org/10.1145/182.358434

Anagnostopoulos, E., Batsakis, S., & Petrakis, E. G. M. (2013). CHRONOS: A reasoning engine for qualitative temporal information in OWL. *Procedia Computer Science*, *22*, 70-77. https://doi.org/10.1016/j.procs.2013.09.082

Browne, W. J., Goldstein, H., & Rasbash, J. (2001). Multiple membership multiple classification (MMMC) models. *Statistical Modelling*, *1*(2), 103-124. https://doi.org/10.1177/1471082X0100100202

Chang, J., & Blei, D. M. (2009). Relational topic models for document networks. In D. van Dyk & M. Welling (Eds.), *Proceedings of the 12th International Conference on Artificial Intelligence and Statistics* (pp. 81-88). PMLR.

Christen, P. (2012). *Data matching: Concepts and techniques for record linkage, entity resolution, and duplicate detection*. Springer. https://doi.org/10.1007/978-3-642-31164-2

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval* (pp. 758-759). ACM. https://doi.org/10.1145/1571941.1572114

Crispin, M., & Murchison, K. (2008). *Internet Message Access Protocol (IMAP) - THREAD and SORT extensions* (RFC 5256). IETF. https://doi.org/10.17487/RFC5256

Doddington, G., Mitchell, A., Przybocki, M., Ramshaw, L., Strassel, S., & Weischedel, R. (2004). The Automatic Content Extraction (ACE) program -- Tasks, data, and evaluation. In *Proceedings of the Fourth International Conference on Language Resources and Evaluation (LREC 2004)* (pp. 837-840). European Language Resources Association.

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal of the American Statistical Association*, *64*(328), 1183-1210. https://doi.org/10.2307/2286061

Raudenbush, S. W., & Bryk, A. S. (2002). *Hierarchical linear models: Applications and data analysis methods* (2nd ed.). Sage Publications.

Zawinski, J. (1997). *Message threading* [Design note]. jwz.org. https://www.jwz.org/doc/threading.html

Additional context on the Fugu / Conductor / TRINITY test-time-compute-allocation research the `llm` channel's design follows is maintained in
[contextual-orchestrator's own literature register](https://github.com/ContextualWisdomLab/contextual-orchestrator/blob/main/docs/architecture.md)
rather than duplicated here, so the two repos do not drift out of sync.
