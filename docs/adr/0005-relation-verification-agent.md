# ADR 0005 — External search verification for Ontology relation inferences

**Decision status:** Accepted
**Date:** 2026-08-13

## Context

The product brief is explicit: "Ontology 컨텐츠 중 관계 추론 결과의 진위 확인을
위해 외부 웹/내부 검색 Agent가 필요할 것임. 반드시 구현 바람. (Searxng 사용
가능)" -- the Ontology's relation-inference outputs need their truthfulness
checked by an external web/internal search agent, and Searxng is named as
an acceptable implementation.

`entity_relationship_classification.py` is the concrete inference target:
an LLM reads a post and names a `rel_voc`/`rel_vom`/`rel_vop`/`rel_vocc`/
`rel_voco`/`rel_vos` relationship for an organization it also names --
both the organization's existence and the specific relationship are the
model's inference, persisted to `post_counterparty_entity` and, via
[ADR 0004](0004-knowledge-graph-ontology.md), backed by a real
`hasVocRelationship`/etc. Ontology predicate. Nothing previously checked
whether the named organization has any real-world footprint at all --
an LLM hallucinating an organization name would sit in the Knowledge
Graph indistinguishable from a genuine one.

## Decision

Add a pluggable `RelationVerificationClient`
(`lineageweave/relation_verification.py`), grounded in FEVER-style
open-domain claim verification (Thorne, Vlachos, Christodoulopoulos, &
Mittal, 2018): retrieve external evidence for a claim, then classify it
against what was retrieved. This module implements the practical subset
that fits a same-request check -- retrieval plus a presence/absence
signal (`verify_corroborated` / `verify_uncorroborated`), not full
NLI-based entailment scoring against retrieved passages. The
presence/absence signal is deliberately coarse: it catches "this
organization has zero web footprint" (the failure mode actually
observed from LLM classification), not "this specific relationship
claim is definitely true" -- a genuinely false relationship between two
REAL organizations still returns results about each organization
separately, so this is an existence/plausibility check, not a full
relationship-truth adjudicator. That is a real upgrade path once real
usage shows the coarser signal under- or over-trusting results in
practice, not implemented here because nothing yet demonstrates the
need for it over this cheaper stage.

The real implementation, `SearxngRelationVerificationClient`, queries a
**self-hosted** Searxng instance (`docker/searxng/`), never a
third-party hosted search API requiring its own key -- consistent with
this repo's "solve it yourself via Docker Compose rather than report a
channel unavailable" discipline (see `docker-compose.yml`'s `searxng`
service, published on a non-default host port like every other service
here, so both the backend container and host-process integration tests
can reach it). `NullRelationVerificationClient`
keeps the channel unavailable (never fabricates a verification result)
when `SEARXNG_BASE_URL` is unset, same discipline as every other
pluggable client in this repo.

Persistence: `post_counterparty_entity` gains
`verification_status_code` (`common_lookup_value` category
`relation_verification_status`: `verify_pending` / `verify_corroborated`
/ `verify_uncorroborated`), `verification_evidence_url`, and
`verification_checked_at` (`migrations/0001_initial_schema.sql`, with
`migrations/0004_relation_verification.sql` as the idempotent upgrade
path for an already-running deployment, matching 0002/0003's pattern).
A re-classification (`entity_relationship_ingestion.py`, on a repeat
`extract-keymen` call) resets these three columns back to
`verify_pending` -- a prior verification was checked against the OLD
relationship label, so it does not carry over to a changed
classification.

Trigger: a separate, explicitly-invoked action
(`POST /api/posts/{id}/verify-relations`), not run automatically inside
`extract-keymen` -- the same pattern this repo already uses for summary/
commitment-derivation/chat (separate real-cost actions the user
triggers, not a hidden side effect of extraction). The post-detail
popup's VOC evidence section (`GET /api/posts/{id}/voc-evidence`) now
also returns `verification_status_code` / `verification_evidence_url`
per counterparty so the UI can render a status badge without a second
round trip, with a "Verify" action next to any still-`verify_pending`
row.

## Consequences

- New Docker Compose service (`searxng`) and a new backend dependency
  edge (`backend` -> `searxng`, healthcheck-gated in `depends_on`) --
  a genuine new moving part in the stack, not a stub.
- The coarse presence/absence signal is an honestly-scoped first stage,
  documented as such in the module docstring, not claimed as full
  relationship-truth adjudication.
- `post_counterparty_entity` inserts must supply (or accept the default
  for) three new columns; existing callers using `INSERT ... VALUES`
  with an explicit column list are unaffected since the new columns all
  have defaults.

## Related

Builds on [ADR 0004](0004-knowledge-graph-ontology.md)'s Ontology/
Semantic-Layer grounding and `entity_relationship_classification.py`'s
existing relation-extraction citation (Zelenko, Aone, & Richardella,
2003).

## References (APA 7th)

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: a large-scale dataset for fact extraction and VERification. In *Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1 (Long Papers)* (pp. 809–819). Association for Computational Linguistics. https://aclanthology.org/N18-1074/
