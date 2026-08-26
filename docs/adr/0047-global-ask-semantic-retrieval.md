# ADR 0047: Global Ask retrieves semantic and source evidence

## Context

Global Ask previously selected candidates only from post titles and normalized
post bodies. A project may exist only in a persisted semantic mention, and a
source record may be identifiable only by its raw customer, PU, sales-pool,
author, or source-record key fields. In those cases the Buyer search could
find a post while Ask Agent could not.

## Decision

Global Ask embeds the complete natural-language question once through
contextual-orchestrator and ranks authorized posts by the maximum raw cosine
similarity against their persisted semantic-unit embeddings. Query and unit
vectors must have the same configured embedding model and dimension.

Persisted project, role/responsibility/affiliation, Keyman, Knowledge Graph
edge/endpoint-label, and ontology-IRI evidence is a second candidate-nomination
channel. PostgreSQL `websearch_to_tsquery('simple', ...)` runs against GIN
expression indexes on the normalized owning tables; it does not copy evidence
into a denormalized search table. A complete canonical ontology IRI in the
question maps through the published lookup-code annotation. A Knowledge Graph
match nominates only `knowledge_graph_edge_evidence.evidence_post_id`, never an
endpoint post merely because that post labels a node.

Both owned rank lists are bounded independently after the same SQL
visibility, corporate/process scope, source-eligibility, and event-time
predicates. RankWeave combines them with Cormack, Clarke, and Buettcher's
(2009) parameter-free reciprocal rank fusion. No token extractor, similarity
threshold, hand-authored channel preference, or locally invented weight is
allowed. The existing final source-row query and `can_see_post` callback remain
a second authorization check. If RankWeave cannot combine two present
channels, the new evidence channel is dropped and the embedding ranking
remains; a sole available channel needs no fusion.

The retrieved posts carry their raw source fields and persisted semantic/KG
facts into the contextual-orchestrator prompt with column/table provenance.
Candidate nomination does not make a fact authoritative and does not bypass
the evidence-post mapping. If the embedding channel or a complete
matching-model vector is unavailable, retrieval may use only the persisted
evidence channel; it never falls back to title/body lexical search.

Raw source fields remain `hint_only`; the prompt explicitly distinguishes them
from resolved ontology assertions. The existing ABAC filter is applied before
semantic evidence is loaded, and the bounded source limit remains in place.

## Consequences

- Ask Agent retrieves by semantic-unit meaning without a keyword rule.
- A term present only in normalized semantic, Knowledge Graph, endpoint-label,
  or ontology evidence can nominate its authorized evidence post.
- A source hint can retrieve a post but cannot silently bind a customer,
  project, PU, or Keyman.
- The orchestrator receives more useful evidence while still receiving only
  authorized, bounded source documents.
- Missing semantic measurement fails closed and cannot silently change the
  retrieval method.

## References

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank
fusion outperforms Condorcet and individual rank learning methods. In
*Proceedings of the 32nd International ACM SIGIR Conference on Research and
Development in Information Retrieval* (pp. 758–759). Association for
Computing Machinery. https://doi.org/10.1145/1571941.1572114
