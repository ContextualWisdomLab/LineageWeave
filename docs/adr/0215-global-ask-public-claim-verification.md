# ADR 0215: Global Ask verifies eligible public claims outside internal authority

## Status

Accepted

## Context

ADR 0047 lets normalized semantic and Knowledge Graph evidence nominate an
authorized source post. Nomination and an internal citation do not establish
that a real-world claim is publicly corroborated. Conversely, sending private
post bodies, people facts, measurement payloads, or source hints to a public
search service would cross the authorization boundary.

FEVER distinguishes supported, refuted, and not-enough-information judgments
and requires cited evidence for the first two. PROV-O requires internal source
evidence, external retrieval evidence, and the verification activity to remain
distinguishable. SearXNG's current Search API supports bounded JSON results from
`GET /search` when that output format is enabled.

## Decision

Public verification is explicit opt-in and defaults to false. The choice is
persisted on the asynchronous `global_ask_job`; the worker never reconstructs
consent from later state.

Only a source post whose persisted `visibility_code` is `public` receives the
`GlobalAskSourceDocument` egress capability. Eligible claims are limited to
project/ontology assertions and non-person Knowledge Graph relations already
carried by a cited public source. Private sources, Keyman/person facts, raw
source hints, source bodies, TEPP artifacts, fast-mlsirm artifacts, prompts,
credentials, and uncited facts never form a public query.

ADR 0275 strengthens admission: the production queue now requires a persisted,
PROV-O-bound public-claim envelope for an exact cited post. Question-token
overlap is retained only as legacy library compatibility and is not a runtime
egress decision.

SearXNG retrieves at most five bounded snippets for at most four claims. Result
URLs must be HTTP(S), must not be search pages, localhost, `.local`, or literal
non-global addresses, and are never fetched by LineageWeave. The untrusted
snippets cross contextual-orchestrator with `mode="verify"` and
`reasoning_effort="auto"`. A supported or refuted response without selected
evidence is downgraded to not enough information.

External URLs remain `external_claims[].evidence`; internal post identifiers
remain `cited_post_ids`. Verification never mutates ontology, Knowledge Graph,
Event Lineage, TEPP, or fast-mlsirm state. Unconfigured or failed retrieval is
an explicit unavailable state, not a negative judgment.

## Consequences

- Readers can request public corroboration without exporting private evidence.
- Conflicting evidence is visible without changing internal graph authority.
- Async HTTP responsiveness is retained; public retrieval runs in the worker.
- Search snippets remain evidence inputs, not trusted instructions or facts.

## References

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

SearXNG. (2026). *Search API*. https://docs.searxng.org/dev/search_api.html

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A
large-scale dataset for fact extraction and verification. In *Proceedings of
the 2018 Conference of the North American Chapter of the Association for
Computational Linguistics: Human Language Technologies* (Vol. 1, pp. 809–819).
Association for Computational Linguistics. https://doi.org/10.18653/v1/N18-1074
