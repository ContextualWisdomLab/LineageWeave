# ADR 0106 — Global Ask public claim verification

- Status: Proposed
- Date: 2026-08-20
- Owners: LineageWeave Buyer surface / Knowledge Graph / Semantic evidence
- Depends on: ADR 0004, ADR 0005, ADR 0036, ADR 0070, ADR 0090

## Context

Global Ask can retrieve authorized posts and render persisted Knowledge Graph,
ontology, project, role, and Keyman evidence. That is not the same as checking
whether a public-world Knowledge Graph or semantic assertion is corroborated by
external evidence.

The existing relation-verification path uses SearXNG for a narrower inferred
counterparty relationship write. Global Ask needs a read-only verification lane
that preserves four distinctions:

1. an authorized internal post citation is not an external web citation;
2. a persisted graph/ontology assertion is not automatically authoritative;
3. a failed or empty web search is not evidence that a claim is false;
4. TEPP and fast-mlsirm outputs are measurement evidence, not public-world facts
   that web search may truth-promote.

## Decision

Global Ask SHALL support an explicit `verify_external` opt-in. Normal answers
remain grounded in authorized LineageWeave posts. When verification is enabled:

1. lexical retrieval and persisted semantic/KG candidate nomination run before
   final source selection;
2. the ordinary source visibility/ABAC predicate is re-run before body or
   evidence material enters an LLM prompt;
3. only facts attached to public sources are eligible for public egress;
4. Keyman/person/actor facts, source hints, credentials, PII, TEPP artifacts,
   fast-mlsirm respondent/item/latent data, and any private source evidence are
   ineligible for SearXNG queries;
5. a graph relation is eligible only if every persisted evidence-post identifier
   carried by the relation is public in the authorized source set;
6. SearXNG returns bounded snippets and URLs. LineageWeave does not server-side
   fetch the returned target URL as part of verification;
7. contextual-orchestrator adjudicates the claim from only those numbered web
   snippets in `mode="auto"` with a strict JSON schema; its model, protocol, and
   reasoning policy remain owned by the orchestrator;
8. the result is one of `claim_supported`, `claim_refuted`, or
   `claim_not_enough_information`;
9. `claim_supported` and `claim_refuted` require at least one cited external
   evidence item. A verdict without cited evidence is downgraded to
   `claim_not_enough_information`;
10. external URLs remain separate from internal `cited_post_ids`; and
11. no external verdict mutates or authority-promotes a Knowledge Graph edge,
    ontology mapping, TEPP result, or fast-mlsirm score.

## Retrieval decision

Global Ask SHALL not require the query term to occur in the raw post body before
semantic evidence can nominate the post. Candidate nomination covers persisted
project mentions, roles/responsibilities/affiliations, Keyman catalog evidence,
organization/team mentions, graph edge/type vocabulary, and ontology lookup
codes. Nomination returns post identifiers only and therefore does not grant
access.

Current title/body/source-field weighting and direct Event-Lineage expansion
remain intact. A strong persisted semantic/KG match may outrank a weak body hit.
A non-empty query with no lexical, semantic, graph, or ontology candidates fails
closed to no source instead of returning unrelated recent posts.

## SearXNG boundary

Only HTTP(S) result URLs are eligible for display evidence. Localhost, `.local`,
non-global literal IP addresses, and search-engine/result-page hosts are
rejected. Title, URL, and snippet lengths are bounded before the adjudication
prompt is constructed.

SearXNG's Search API supports GET/POST search and JSON output when the instance
has that output format enabled. A configured instance that disables JSON output
is therefore an unavailable verification provider, not a refutation.

## Provenance and authority

Internal source posts, persisted semantic facts, external retrieval snippets,
and the adjudication activity remain distinguishable provenance entities and
activities. The public-verification payload is additional evidence that a
Buyer can inspect; it is not a new system of record.

## Measurement boundary

TEPP accepted receipts prove transport acceptance only. Completed TEPP results
remain versioned temporal measurement evidence. fast-mlsirm reports remain
versioned psychometric/latent-measurement evidence. Neither may be placed in
`external_claim_facts`, sent to SearXNG, or relabeled `web_verified`.

## Buyer next action

The response SHALL tell the Buyer what to do next:

- skipped → explicitly enable public verification when appropriate;
- unavailable → configure/recover SearXNG and contextual-orchestrator, then retry;
- no public claim → inspect the internal cited posts;
- refuted → inspect the conflicting public evidence before accepting the graph claim;
- not enough information → collect stronger authoritative evidence;
- supported → inspect the cited public evidence before any governed graph review.

## Verification requirements

Regression coverage must prove:

- semantic-only/KG-only retrieval;
- no unrelated-recency fallback;
- final ABAC re-check after nomination;
- private/Keyman/person/source-hint/measurement non-egress;
- all-evidence-public requirement for graph claims;
- internal post IDs and external URLs never share a citation field;
- SearXNG/provider failure cannot become `claim_refuted`;
- evidence-free support/refute verdicts downgrade to not-enough-information;
- API opt-in remains backward compatible; and
- changed production modules retain repository-required statement and branch
  coverage.

## References

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

SearXNG contributors. (2026). *Search API*. SearXNG documentation.
https://docs.searxng.org/dev/search_api.html

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A
large-scale dataset for fact extraction and verification. In *Proceedings of
the 2018 Conference of the North American Chapter of the Association for
Computational Linguistics: Human Language Technologies, Volume 1 (Long
Papers)* (pp. 809–819). Association for Computational Linguistics.
https://doi.org/10.18653/v1/N18-1074
