# ADR 0216: Global Ask uses retained revisions at a knowledge cutoff

## Status

Accepted

## Context

Global Ask previously answered only from live source bodies. Filtering posts by
their creation clock does not establish what body or derived semantic evidence
was available at an earlier instant. PROV-O distinguishes an entity from its
specializations and derivations, while OWL-Time defines instants and intervals;
therefore an as-of answer needs a recorded revision interval, not a rewritten
live body presented as historical evidence.

## Decision

`POST /api/ask` accepts an optional `knowledge_cutoff` instant no later than the
database clock. The async job persists that instant. Retrieval applies ABAC,
source eligibility, creation/event time, and the cutoff before its candidate
limit, then substitutes the `source_post_revision` whose half-open availability
interval contains the cutoff.

When no retained revision covers the instant, the response records
`historical_body_unavailable` and does not send the live body to
contextual-orchestrator. Current-only role, Keyman, graph-label, embedding,
image, and Event Lineage projections are excluded until their stores expose a
compatible system-time contract. Timestamped project and ontology-edge
evidence may nominate a post only when their recorded creation time is not
later than the cutoff; the answer still cites the retained source revision.

Responses expose the cutoff, full/partial grounding status, retained revision
identity and availability time, later-live-change status, and limitations.
Omitting the cutoff preserves the existing live request and response behavior.

## Consequences

- A historical answer cannot silently quote a later rewrite.
- Missing historical bodies and semantic channels remain explicit limitations.
- Historical graph/image projections stay unavailable instead of being
  reconstructed from current state.
- MCP parity remains a separate delivery requirement on the shared Ask contract.

## References

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Cox, S., & Little, C. (Eds.). (2020). *Time ontology in OWL*. World Wide Web
Consortium. https://www.w3.org/TR/owl-time/
