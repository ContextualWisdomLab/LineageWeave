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
vectors must have the same configured embedding model and dimension. No token
extraction, keyword matching, lexical weighting, similarity threshold, or
locally invented channel weight participates in candidate selection.

The retrieved posts carry their raw source fields and persisted
project/role/Keyman facts into the contextual-orchestrator prompt with
column/table provenance. These facts enrich grounded answering; they do not
become keyword retrieval signals. If the embedding channel or a complete
matching-model vector is unavailable, retrieval returns no evidence rather
than falling back to lexical search.

Raw source fields remain `hint_only`; the prompt explicitly distinguishes them
from resolved ontology assertions. The existing ABAC filter is applied before
semantic evidence is loaded, and the bounded source limit remains in place.

## Consequences

- Ask Agent retrieves by semantic-unit meaning without a keyword rule.
- A source hint can retrieve a post but cannot silently bind a customer,
  project, PU, or Keyman.
- The orchestrator receives more useful evidence while still receiving only
  authorized, bounded source documents.
- Missing semantic measurement fails closed and cannot silently change the
  retrieval method.
