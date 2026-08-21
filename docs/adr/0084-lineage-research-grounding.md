# ADR 0084: Research-grounded lineage and ontology policy

- Status: Accepted
- Date: 2026-08-20
- Related: [0062](0062-semantic-unit-embedding.md), [0064](0064-lineage-evidence-and-tree-assembly.md), [0076](0076-paper-grounded-model-policy.md)

## Context

`docs/lineage-bi-research-notes.md` contains the literature and aggregate
validation evidence behind LineageWeave. Its decisions must not remain an
informal architecture source, and a short record must not be treated as a
proven fact merely because a heuristic or model produced a link.

## Decision

1. Treat every source record as a fallible mention. A lineage edge is an
   evidence-backed instance only after independent signals are fused and the
   minimum score floor is met; otherwise the record remains a root.
2. Preserve temporal, lexical, grouping, embedding, semantic, and optional
   LLM/VISION evidence as separate channels. Do not replace them with a
   nearest-neighbor or deterministic single-signal rule.
3. Keep mention detection, lineage instance construction, and calibrated
   measurement separate. TEPP remains a wire-contract boundary and is never
   reimplemented as local scoring or psychometrics.
4. Split posts into addressable semantic units such as paragraphs, sentences,
   DOM blocks, conversation turns, and image regions. Embed and persist each
   unit with its source order and provenance; do not use one opaque whole-post
   embedding as the ontology boundary.
5. Treat named people and organizations as unresolved mentions until evidence
   supports a catalog identity. Keyman side, affiliation, relationship,
   customer, project, and PU/sales-pool hints remain provenance-bearing
   evidence, not silently upgraded facts.
6. Use contextual-orchestrator for all model work, including VISION, with
   paper-grounded routing and capability negotiation. Missing channels remain
   unavailable; they are never replaced by fabricated scores, identities,
   summaries, or relationships.
7. Keep the complete bibliography and aggregate validation observations in
   `docs/lineage-bi-research-notes.md` as supporting evidence. Normative
   implementation decisions belong in this ADR and the channel-specific ADRs
   listed above.

## Considered alternatives

- A deterministic latest-record predecessor: rejected because scattered
  multi-topic histories make a single nearest predecessor unreliable.
- One whole-post semantic vector: rejected because it loses paragraph/DOM/image
  provenance and makes evidence navigation impossible.
- Local model ranking or a raw provider call: rejected because model policy,
  capability translation, cost attribution, and VISION boundary belong to
  contextual-orchestrator.

## Consequences

- Lineage and ontology results remain auditable and can abstain instead of
  manufacturing a relationship.
- Storage and ingestion retain more unit-level provenance and require stable
  third-normal-form projections.
- Multi-channel extraction costs more than a single heuristic, and incomplete
  provider capability or source context can leave evidence unavailable. That
  incompleteness is explicit rather than silently converted into confidence.

## Evidence and literature

The full APA bibliography, paper links, and aggregate validation statistic
are maintained in the supporting research notes. The policy is grounded in
the TDT/CHRONOS temporal record-linkage problem, ACE-style mention detection
and tracking, EDIN's unknown-entity discovery, DynamicER's evolving-mention
resolution, graph random-walk relatedness, RAG provenance discipline, and the
paper register required by ADR 0076. These papers are evidence for boundaries
and failure modes, not a license to claim that a particular model or heuristic
is universally correct.

The primary references used for this policy are:

- [CHRONOS: Facilitating History Discovery by Linking Temporal Records](https://doi.org/10.14778/2367502.2367559)
- [Identifying and Tracking Entity Mentions in a Maximum Entropy Framework](https://research.ibm.com/publications/identifying-and-tracking-entity-mentions-in-a-maximum-entropy-framework)
- [EDIN: An End-to-end Benchmark and Pipeline for Unknown Entity Discovery and Indexing](https://aclanthology.org/2022.emnlp-main.593/)
- [DynamicER: Resolving Emerging Mentions to Dynamic Entities for RAG](https://aclanthology.org/2024.emnlp-main.762/)
- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
