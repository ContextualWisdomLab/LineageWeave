# ADR 0047: Global Ask retrieves semantic and source evidence

## Context

Global Ask previously selected candidates only from post titles and normalized
post bodies. A project may exist only in a persisted semantic mention, and a
source record may be identifiable only by its raw customer, PU, sales-pool,
author, or source-record key fields. In those cases the Buyer search could
find a post while Ask Agent could not.

## Decision

Global Ask candidate retrieval searches the same authorized source context as
the board: raw source hints, source record identity, project mentions, stored
roles, cataloged Keyman mentions, title, and normalized body. The retrieved
posts carry their raw source fields and persisted project/role/Keyman facts
into the contextual-orchestrator prompt with column/table provenance.

Raw source fields remain `hint_only`; the prompt explicitly distinguishes them
from resolved ontology assertions. The existing ABAC filter is applied before
semantic evidence is loaded, and the bounded source limit remains in place.

## Consequences

- Ask Agent can answer evidence-grounded questions when the relevant project
  or identity is not repeated in the body.
- A source hint can retrieve a post but cannot silently bind a customer,
  project, PU, or Keyman.
- The orchestrator receives more useful evidence while still receiving only
  authorized, bounded source documents.
