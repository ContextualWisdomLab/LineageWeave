# Research notes: what this design is grounded in

**Status:** supporting research notes. Normative design decisions are recorded
in [ADR 0064](adr/0064-lineage-evidence-and-tree-assembly.md), [ADR 0062](adr/0062-semantic-unit-embedding.md),
and the existing channel-specific ADRs; update this file as literature and
validation evidence changes, not as an untracked architecture decision.

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

## Chunking: embedding at meaning-identifiable units, not whole documents

Embedding a whole flattened document as one vector dilutes a short
relevant unit with everything else in the same document -- the vector
averages over content that has nothing to do with the match being sought.
`lineageweave/chunking.py` splits a document into meaning-identifiable
units first. ADR 0208 removed the unused local Python cosine/max-pooling
experiment; a versioned Rust retrieval-owner envelope must perform any future
unit scoring. Four unit types remain, each grounded in a real boundary concept:

- **paragraph** -- subtopic-passage boundaries (Hearst, 1997, TextTiling).
- **sentence** -- the finer unit inside a paragraph.
- **dom** -- sectioning/flow block-element boundaries (WHATWG HTML Living
  Standard).
- **conversation_turn** -- sender/receiver boundaries (RFC 5322), reusing
  the same one-message-one-party shape ThreadWeave's JWZ threading already
  models across records, just applied within a single record's body.

**Honest scope note for this project's real dataset**: the real dataset
validated against in milestone 2 (43,814 short business records) has only
one real free-text field, and it is short (~28 characters average) with no
paragraph, DOM, or conversation structure to chunk, so unit persistence does
not imply or fabricate a local similarity score.
This module exists for when a richer content source is embedded --
concretely, the raw MHTML source artifacts this dataset's records were
derived from (tracked only as opaque content-addressed references in this
project's real dataset, not fetchable from this repository) are HTML
documents with real DOM and sender/receiver structure, which is exactly
the shape `chunk_by_dom` and `chunk_by_conversation_turn` are for.

## Embedded images: OCR and object recognition, position-preserved

The same DOM content that motivates `chunk_by_dom` can carry embedded
base64 images -- `chunk_by_dom` extracts these as `"image"` chunks
interleaved with the surrounding text chunks in true document order (see
`Chunk.index`), and `lineageweave.image_content` turns image bytes into
searchable content via a pluggable vision-capable client, following the
same never-fake-a-missing-channel discipline as the embedding and
adjudication clients:

- **OCR (text recognition)**: grounded in Li et al. (2023) -- TrOCR, the
  transformer encoder-decoder architecture family modern OCR (including
  vision-capable chat models) descends from.
- **Object recognition / captioning / tagging**: grounded in Radford et
  al. (2021) -- CLIP, contrastive language-image pretraining, the basis
  most current zero-shot image tagging and captioning builds on.

Proven for real during development: a real PNG generated with real
rendered text (`draw.text(...)`, not a canned fixture file) was sent
through `OpenAiCompatibleVisionClient` against the live gateway, and the
text was read back correctly -- genuine OCR, not a mocked response.

`docs/image-content-schema.md` proposes the DB design for storing and
searching this content so a match on extracted text or a tag can still be
traced back to which document, and which position in that document, the
picture came from -- an extracted caption is not useful for review if
nobody can tell which paragraph it illustrated.

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
instance with `mode="auto"` and `reasoning_effort="high"`; the orchestrator
selects the supported route and records any verification metadata -- one worker
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

Cai, D., Yu, S., Wen, J.-R., & Ma, W.-Y. (2003). *VIPS: A vision-based page segmentation algorithm* (Microsoft Research Technical Report MSR-TR-2003-79). Microsoft Research.

Chang, J., & Blei, D. M. (2009). Relational topic models for document networks. In D. van Dyk & M. Welling (Eds.), *Proceedings of the 12th International Conference on Artificial Intelligence and Statistics* (pp. 81-88). PMLR.

Christen, P. (2012). *Data matching: Concepts and techniques for record linkage, entity resolution, and duplicate detection*. Springer. https://doi.org/10.1007/978-3-642-31164-2

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval* (pp. 758-759). ACM. https://doi.org/10.1145/1571941.1572114

Crispin, M., & Murchison, K. (2008). *Internet Message Access Protocol (IMAP) - THREAD and SORT extensions* (RFC 5256). IETF. https://doi.org/10.17487/RFC5256

Doddington, G., Mitchell, A., Przybocki, M., Ramshaw, L., Strassel, S., & Weischedel, R. (2004). The Automatic Content Extraction (ACE) program -- Tasks, data, and evaluation. In *Proceedings of the Fourth International Conference on Language Resources and Evaluation (LREC 2004)* (pp. 837-840). European Language Resources Association.

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data*, *1*(1), 5-es. https://doi.org/10.1145/1217299.1217304

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal of the American Statistical Association*, *64*(328), 1183-1210. https://doi.org/10.2307/2286061

Gildea, D., & Jurafsky, D. (2002). Automatic labeling of semantic roles. *Computational Linguistics*, *28*(3), 245-288. https://doi.org/10.1162/089120102760275983

Hearst, M. A. (1997). TextTiling: Segmenting text into multi-paragraph subtopic passages. *Computational Linguistics*, *23*(1), 33-64.

International Organization for Standardization. (2022). *Quantities and units — Part 1: General* (ISO 80000-1:2022).

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In H. Larochelle, M. Ranzato, R. Hadsell, M. F. Balcan, & H. Lin (Eds.), *Advances in Neural Information Processing Systems* (Vol. 33, pp. 9459-9474). Curran Associates.

Li, M., Lv, T., Chen, J., Cui, L., Lu, Y., Florencio, D., Zhang, C., Li, Z., & Wei, F. (2023). TrOCR: Transformer-based optical character recognition with pre-trained models. *Proceedings of the AAAI Conference on Artificial Intelligence*, *37*(11), 13094-13102. https://doi.org/10.1609/aaai.v37i11.26538

Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., Sastry, G., Askell, A., Mishkin, P., Clark, J., Krueger, G., & Sutskever, I. (2021). Learning transferable visual models from natural language supervision. *Proceedings of the 38th International Conference on Machine Learning*, *139*, 8748-8763.

Raudenbush, S. W., & Bryk, A. S. (2002). *Hierarchical linear models: Applications and data analysis methods* (2nd ed.). Sage Publications.

Resnick, P. (2008). *Internet Message Format* (RFC 5322). IETF. https://doi.org/10.17487/RFC5322

See, A., Liu, P. J., & Manning, C. D. (2017). Get to the point: Summarization with pointer-generator networks. In *Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics* (Vol. 1, pp. 1073-1083). Association for Computational Linguistics. https://doi.org/10.18653/v1/P17-1099

Sun, Q., Yuan, J., He, S., Guan, X., Yuan, H., Fu, X., Li, J., & Yu, P. S. (2025). *DyG-RAG: Dynamic graph retrieval-augmented generation with event-centric reasoning*. arXiv. https://arxiv.org/abs/2507.13396

Tong, H., Faloutsos, C., & Pan, J.-Y. (2006). Fast random walk with restart and its applications. *Proceedings of the Sixth International Conference on Data Mining (ICDM'06)*, 613-622. https://doi.org/10.1109/ICDM.2006.70

The Unicode Consortium. (2024). *The Unicode Standard* (Version 16.0.0). https://www.unicode.org/versions/Unicode16.0.0/

Wang, Q., Fu, Y., Cao, Y., Wang, S., Tian, Z., & Ding, L. (2023). *Recursively summarizing enables long-term dialogue memory in large language models*. arXiv. https://arxiv.org/abs/2308.15022

WHATWG. (2026). *HTML Living Standard — sections 4.3 (sectioning content) and 4.4 (grouping content)*. https://html.spec.whatwg.org/

Zawinski, J. (1997). *Message threading* [Design note]. jwz.org. https://www.jwz.org/doc/threading.html

Zelenko, D., Aone, C., & Richardella, A. (2003). Kernel methods for relation extraction. *Journal of Machine Learning Research*, *3*, 1083-1106.

Additional context on the Fugu / Conductor / TRINITY test-time-compute-allocation research the `llm` channel's design follows is maintained in
[contextual-orchestrator's own literature register](https://github.com/ContextualWisdomLab/contextual-orchestrator/blob/main/docs/architecture.md)
rather than duplicated here, so the two repos do not drift out of sync.

## Keyman extraction (Phase 2)

`lineageweave/keyman_extraction.py` treats a named person in a post as an
ACE-style entity mention (Doddington et al., 2004): the surface string is
not yet a resolved person node, and a mention whose side cannot be
classified into the closed `{our_side, counterparty}` set is dropped
rather than guessed. N:N organization attachments are slot-filling on
that mention (a person may have zero, one, or several affiliations in
the same post), not a second independent NER pass. The live client
calls contextual-orchestrator (`mode="auto"`) rather than a raw LLM
API so adaptive reasoning-effort allocation stays centralized with the
adjudication channel. Proven for real during development against
`fixtures.ambiguous_keyman_post` when orchestrator credentials are set;
the default suite asserts the parser and the never-fake null client.

## Knowledge Graph traversal (Phase 2)

`lineageweave/knowledge_graph.py`'s `random_walk_with_restart` implements
Tong et al. (2006)'s eq. 2 by power iteration: from a starting node (a
selected Keyman), every other node in the graph gets a continuous
relevance score shaped by the graph's real connectivity, rather than a
single fixed hop count. `select_related_nodes` turns that into a per-node
adaptive cutoff (a relevance-ratio threshold against the top score) --
`tests/test_knowledge_graph.py` proves this concretely: the same ratio
threshold yields a five-node related-set from a well-connected "hub" node
and a one-node related-set from a sparsely-connected node, with no hop-count
constant anywhere in the algorithm or the test.

## Entity-relationship classification and corporate hierarchy resolution (Phase 3)

`lineageweave/entity_relationship_classification.py` treats "is this named
organization a customer, competitor, partner, ...?" as relation
extraction (Zelenko, Aone, & Richardella, 2003): the relationship between
the post author's own organization and each named entity, not a property
of the string alone -- the same organization can be classified differently
across two different posts (or, per the fixture used in its real-provider
test, could plausibly be read either way within one post, e.g. a current
customer whose new division has started competing). The org's own
`voc`/`vom`/`vop`/`vocc`/`voco`/`vos` vocabulary maps directly onto this as
the classifier's closed output set; an unrecognized code from the model is
dropped rather than guessed, same discipline as Keyman extraction.

`lineageweave/corporate_hierarchy_resolution.py` implements the candidate-
generation and similarity-scoring stage of collective entity resolution
(Bhattacharya & Getoor, 2007) -- resolving "Acme Electronics Korea Ltd." or
"Acme Elec Korea" mentioned in free text to the existing `corporate_entity`
row a human would recognize it as, via normalized string similarity, with
an explicit `None` (not a guess) when nothing clears the similarity
threshold. This is honestly the *first* stage of what Bhattacharya &
Getoor call collective resolution, not the full joint-inference version:
a genuinely collective resolver would also weigh which other entities are
co-mentioned in the same post against each candidate's own known
affiliates, and could resolve two different ambiguous mentions in one post
jointly. That joint step is a documented upgrade path, not yet needed --
nothing in this product's real usage so far has shown single-mention
similarity scoring under- or over-resolving.

## Affiliate tree and VOC evidence (Phase 6)

The affiliate tree is the already-resolved corporate hierarchy (the
self-referencing `corporate_entity` table, same Bhattacharya & Getoor,
2007 candidate-generation stage `corporate_hierarchy_resolution`
implements) rendered as the ancestor forest of the organizations a
post's Keymen actually name. Walking `parent_entity_id` from those
leaves is enough: a sibling the post never mentions is not a related
node, and an unresolved free-text affiliation is left as its own root
rather than attached to the nearest name.

VOC evidence is extractive, not abstractive. The post already carries a
closed `voc_type_code`; the buyer-felt gap was the missing span that
justifies that label. `sentence_excerpts` returns the sentences that
contain a classified organization name -- the ACE mention extent
(Doddington et al., 2004) already used for Keyman -- and returns
nothing when the name is absent. A second LLM pass would be a guessed
quote, which this channel is not allowed to invent.

## Post summary, key events, R&R, and the in-popup chat (Phase 4)

`lineageweave/post_summary.py` treats the popup's summary panel as three
distinct extraction tasks rather than one "summarize this" prompt:
abstractive summarization (See, Liu, & Manning, 2017 -- a summary is a
genuinely re-generated, condensed account, not an extracted span),
ACE-style key-event extraction (Doddington et al., 2004, the same
grounding `keyman_extraction` uses), and semantic role labeling (Gildea &
Jurafsky, 2002) for R&R -- who did what, per person named in the post.

`lineageweave/post_chat.py` implements the in-popup chat as retrieval-
augmented generation (Lewis et al., 2020): an explicit *retrieve* step
(`backend/app/post_chat_ingestion.py` assembles the post's own content
plus its Event-Lineage-linked posts, direct and Knowledge-Graph-indirect,
as numbered source documents) followed by a *reason-and-cite* step (the
model answers using only those sources and reports which ones it actually
drew from). This is the Agentic retrieve-reason-cite shape the product
brief asks for without adding a full agent-framework dependency for what
two functions and a structured prompt already do.

## Global Ask timeline expansion and conversation continuity (Phase 5)

`gather_global_chat_sources` (`backend/app/post_chat_ingestion.py`) had a
retrieve step with no lineage expansion at all: it ranked keyword-matched
posts by match specificity, but never pulled in a matched post's own
Event-Lineage neighbors. A relevance-correct top match is still a single
snapshot, not the connected sequence of records around it -- a live
question about one event returned an accurate answer about that one post
alone when the account actually wanted to know what led up to it and what
happened next. This is exactly the event-centric temporal retrieval
problem DyG-RAG frames: retrieving one temporally-anchored record and
stopping there answers "what does this record say" but not "what actually
happened," which needs the surrounding event sequence (Sun et al., 2025).
The fix expands the single top-ranked match through its direct
`post_lineage_edge` neighbors (the same relation `reconstruct.py` already
persists, reused rather than re-derived) so the source set can speak to a
connected timeline, still ABAC-filtered and still bounded by the existing
source limit -- expanding every keyword hit instead of only the top one
was rejected because a loosely related term would otherwise drag in an
unrelated lineage chain into the model's context.

Global Ask's chat turns are not yet persisted as a running conversation --
each question is answered independently, so there is no multi-turn
context to compress. Recursive dialogue summarization (Wang et al., 2023)
is the grounding this repository would use if/when Global Ask grows a
persisted conversation thread that can exceed a bounded context window:
summarize-and-replace older turns instead of an unbounded transcript or a
hard truncation that silently drops earlier decisions. This is recorded
here as the citation this feature would build on, not as a claim that
conversation-level compression is implemented today.

## Quantity scripts in source units (ADR 0165)

Board exports write cubic metres as HTML `<sup>` or as `m^3`. Flattening
those tags concatenates `m3`, which is a different quantity, and leaving
the caret in the buyer view hides the exponent. Derived units map a short
HTML/caret exponent onto Unicode Super/Subscript characters (The Unicode
Consortium, 2024, §22.4) so embeddings keep the unit (Cai, Yu, Wen, & Ma,
2003) while the post view renders React `<sup>`/`<sub>` instead of
`innerHTML`. ISO 80000-1 treats the exponent on a unit symbol as part of
the quantity, not decoration. Comparison operators and a leading footnote
caret stay literal. Full formula ontology is still open.
