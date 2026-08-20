# ADR 0107 — Disclose corroborated organization labels on Global Ask

- Status: Accepted
- Date: 2026-08-20
- Owners: LineageWeave Buyer surface / Organization identity
- Depends on: [0008](0008-organization-abbreviation-resolution.md), [0106](0106-global-ask-public-claim-verification.md)

## Context

Global Ask may nominate authorized posts from search-corroborated
raw/canonical organization-name pairs (ADR 0008). Nomination returns
post identifiers only. Without a buyer-visible evidence fact, a query
for a synthetic alias such as `DC` can surface a Demo Corp post while
leaving the matched SKOS altLabel → prefLabel pair hidden. The buyer
then cannot tell why that post was nominated or what to open next.

Pending and uncorroborated aliases must stay invisible. A guessed
translation or an unverified LLM expansion is not evidence.

## Decision

After the ordinary source-visibility/ABAC predicate has selected
visible posts, Global Ask SHALL load corroborated
`organization_name_resolution` rows whose raw or resolved label matches
the bounded query terms and whose canonical name joins a
`corporate_entity` already mentioned on, or affiliated to a person on,
those visible posts.

Each match is disclosed as cited-post evidence of kind
`verified_organization_label` with the raw label and canonical label
kept separate (`DC → Demo Corp`). The fact is internal SKOS evidence. It
is not a public-search claim, is not placed in `external_claim_facts`,
and does not authority-promote a Knowledge Graph edge.

Pending (`verify_pending`) and uncorroborated (`verify_uncorroborated`)
rows remain excluded from both nomination and disclosure. The query
uses one indexable `ILIKE` predicate per label column.

When at least one cited post carries a verified organization label, the
response next action SHALL name opening that cited post to read Event
Lineage. Public-verification next actions remain for answers that have
no such label.

## Buyer next action

- corroborated label match → open a cited post to read Event Lineage
- no corroborated label match → keep the ADR 0106 public-verification
  next action

## Consequences

- The buyer can inspect the exact raw→canonical pair that nominated the
  post without inventing a translation at query time.
- Disclosure cannot precede ABAC: only already-visible post identifiers
  are joined.
- Synthetic fixtures only; Demo Corp / DC and Aurora Grid Power / AGP
  are the documented examples.

## References

De Cao, N., Wu, L., Popat, K., Artetxe, M., Goyal, N., Plekhanov, M.,
Zettlemoyer, L., & Riedel, S. (2022). Multilingual autoregressive
entity linking. *Transactions of the Association for Computational
Linguistics, 10*, 274–290. https://doi.org/10.1162/tacl_a_00460

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/
