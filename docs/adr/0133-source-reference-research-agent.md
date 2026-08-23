# ADR 0133: Evidence-bearing source-reference research agent

- Status: Accepted
- Date: 2026-08-23
- Related: [0004](0004-knowledge-graph-ontology.md), [0005](0005-relation-verification-agent.md), [0062](0062-semantic-unit-embedding.md), [0076](0076-paper-grounded-model-policy.md), [0084](0084-lineage-research-grounding.md)

## Context

A post can cite a URL, patent, publication, or address without explicitly
naming the organization that published or shared it. The existing relation
verification agent checks whether an already extracted organization has a web
footprint. It cannot discover the missing actor, follow the cited resource, or
decide whether retrieved evidence supports the post's claim. Treating a search
hit as proof would preserve the observed failure under a different label.

## Decision

Add a post-scoped source-reference research workflow with separate evidence
channels:

1. Discover URL and patent leads from persisted semantic units and completed
   image-region OCR. A lead retains its source unit or image-region identity;
   deterministic discovery is not an entity binding.
2. Retrieve candidates through the existing self-hosted SearXNG boundary.
   Fetch only public HTTP(S) result pages with redirect and private-network
   rejection. Store bounded extracted text, content digest, retrieval time,
   and final URL; never store credentials, cookies, or arbitrary binary files.
3. Ask contextual-orchestrator to judge each claim against the retrieved
   passages. The only outcomes are `supported`, `refuted`, and
   `not_enough_information`. A sharing actor is returned only when a cited
   passage explicitly identifies it. LineageWeave does not select a provider
   model or call one directly.
4. Persist leads, retrievals, and judgments in normalized tables. Project a
   supported actor/reference relation through the existing semantic and
   Knowledge Graph layers with PROV-O evidence; do not create a private edge
   alias for a W3C property.
5. LLM-as-a-Judge output remains a judgment, not a psychometric score. When a
   research judgment is used in calibrated evaluation, emit a provenance-
   bearing response event through `tepp_client`; TEPP owns calibration and a
   missing or unpersisted result remains Failed. TEPP has not yet published a
   response-event wire contract, so this release does not invent one: research
   judgments are excluded from calibrated evaluation until that contract is
   published and added to `tepp_client`.
6. The workflow is an explicit `post_admin` action because it performs external
   retrieval and writes derived evidence. Readers see persisted evidence,
   uncertainty, citations, and the next action; they never trigger hidden web
   calls by opening a post.

## Implementation status

The current worktree implements source-unit and described-image-region lead
discovery, bounded SearXNG retrieval with public-host and redirect rejection,
contextual-orchestrator judgment, normalized lead/retrieval/judgment/citation
persistence, migration replay, explicit admin execution, read-only retrieval,
and a reader panel. Cited supported actors are projected into the Knowledge
Graph as `dcterms:references` and `prov:wasAttributedTo` relations while
retaining the retrieval digest and judgment identity. Focused synthetic
source-research, migration-replay, graph, and panel tests cover those
boundaries; no live external or authenticated runtime validation is claimed.

The stored `evidence_url` is the SearXNG result URL because redirects are
rejected; canonical/final URL capture remains open. TEPP response-event
integration remains unavailable until TEPP publishes that contract. The
implemented actor guard requires a supported judgment, a citation, and literal
actor presence in the cited passage; whether that passage explicitly identifies
the actor as a publisher or sharer remains Judge-dependent until live evidence
validates it.

## Consequences

- An address alone remains a place. It cannot fill Who or become an
  organization without retrieved, cited evidence.
- Search, crawl, Judge, KG, ontology, and TEPP remain distinguishable signals;
  failure of one cannot be converted into confidence from another.
- Existing SearXNG, contextual-orchestrator, semantic-unit, PROV-O, KG, and
  `tepp_client` boundaries are reused. No provider SDK or second crawler
  dependency is added.

## References

- Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER:
  A large-scale dataset for fact extraction and verification. *Proceedings of
  NAACL-HLT 2018*, 809-819. https://aclanthology.org/N18-1074/
- World Intellectual Property Organization. (2024). *WIPO Standard ST.96:
  XML resources for IP data*. https://www.wipo.int/standards/en/st96/
- World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
  https://www.w3.org/TR/prov-o/
