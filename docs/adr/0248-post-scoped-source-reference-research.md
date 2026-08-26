# ADR 0248: Post-scoped source-reference research

**Status:** Accepted
**Date:** 2026-08-26

## Context

Issue #611 decomposes closed PR #490. The remaining ADR 0133 criterion is
absent from protected `main`: a post-scoped lead from a source semantic unit or
image region, public search, retrieval of a cited public page, orchestrator
judgment, and a persisted research citation.

ADR 0005 verifies an already extracted ontology relation with a presence or
absence search signal. ADR 0215 verifies Global Ask public claims from SearXNG
snippets and **never fetches result URLs**. Those contracts stay unchanged.
Source-reference research needs the retrieved page itself because the reader
next action is to open the cited public resource and compare it with this
post's source unit or image region.

Private source content, people facts, TEPP artifacts, and fast-mlsirm artifacts
must not leave the authorization boundary. EgressWeave is an exact-host
allowlist and cannot retrieve arbitrary public pages. Retrieval therefore needs
its own public-target SSRF and redirect rejection.

## Decision

1. Only a source post whose persisted `visibility_code` is `public` may send
   lead text to SearXNG or retrieve a result URL. Private posts fail closed
   without egress.
2. Leads are existing `post_content_unit` rows (non-image kinds with non-empty
   `unit_text`) or `post_content_image_region` rows with caption or extracted
   text. The workflow does not invent a unit, region, claim, or score.
3. SearXNG search reuses the self-hosted `SEARXNG_BASE_URL` boundary already
   used by ADR 0005 and ADR 0215. The deployment must explicitly provide
   positive `SOURCE_RESEARCH_MAXIMUM_LEADS` and
   `SOURCE_RESEARCH_MAXIMUM_RESULTS` resource budgets. No undocumented default
   or evidence-free ranking threshold is inferred; without both budgets the
   channel is unavailable.
4. Result retrieval is a distinct public-target client: HTTP(S) only, no
   userinfo, no localhost or `.local` hosts, no non-global resolved addresses
   including IPv4-mapped forms, no search-engine hosts, redirects refused, and
   a bounded response body. DNS is resolved before connect; the client connects
   to a previously classified public address and sends the original Host header.
5. The retrieved excerpt crosses contextual-orchestrator with `mode="verify"`
   and `reasoning_effort="auto"`. Allowed judgments are
   `research_supported`, `research_refuted`,
   `research_not_enough_information`, and `research_unavailable`. Supported or
   refuted without a cited URL downgrades to not enough information.
6. Citations persist in 3NF `source_research_citation`. External URLs stay
   distinct from internal post identifiers. The workflow never mutates
   ontology, Knowledge Graph, Event Lineage, TEPP, or fast-mlsirm state.
7. Missing SearXNG, orchestrator, public target, or retrieved text is an
   explicit unavailable outcome, never a fabricated negative judgment.
8. A transient unavailable re-check is returned for the current attempt but
   does not erase a lead's last determinate persisted judgment or cited public
   resource. Citation reads use the persisted source-unit and image-region
   order as the deterministic tie-break within one transaction timestamp.
9. The bounded lead sequence alternates the two persisted source-kind streams,
   beginning with whichever kind occurs first in document order. This gives
   both a semantic-unit stream and an image-region stream a place whenever the
   supplied budget can contain both, without an inferred score, weight, or
   content-ranking heuristic. Each stream retains its persisted source order.
10. A settled Global Ask answer may attach only the determinate persisted
    references belonging to its already-authorized cited posts. Delivery
    rechecks current publication eligibility, limits historical answers to
    references checked by the requested cutoff, and returns the same reference
    fields through REST, UI, report, and MCP's shared durable answer. Missing
    references remain absent; no title or URL is synthesized.

## Consequences

- Readers can research a public post's own source unit or image region without
  mixing Global Ask snippet verification into the same table.
- A reader can move from an Ask citation to its event card, internal post, and
  persisted related public document without treating that document as Event
  Lineage or ontology state.
- Private posts remain inside the authorization boundary.
- Redirect-based SSRF and DNS rebinding are rejected at the retrieval client,
  not compensated later in UI copy.

## Related

Implements the remaining ADR 0133 delivery named in issue #611 on current
`main`. Distinct from [ADR 0005](0005-relation-verification-agent.md) and
[ADR 0215](0215-global-ask-public-claim-verification.md).

## References

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

SearXNG. (2026). *Search API*. https://docs.searxng.org/dev/search_api.html

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A
large-scale dataset for fact extraction and verification. In *Proceedings of
the 2018 Conference of the North American Chapter of the Association for
Computational Linguistics: Human Language Technologies* (Vol. 1, pp. 809–819).
Association for Computational Linguistics. https://doi.org/10.18653/v1/N18-1074
