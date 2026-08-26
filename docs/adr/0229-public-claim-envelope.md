# ADR 0229: Persisted public-claim envelope for Global Ask verification

**Status:** Accepted
**Date:** 2026-08-26

## Context

Issue #272 requires FEVER-style public verification of Global Ask claims
(Thorne, Vlachos, Christodoulopoulos, & Mittal, 2018). A closed stack
selected claims by question-token overlap and forced
`contextual-orchestrator` `mode="verify"`. That is heuristic admission and
it contradicts ADR 0076: orchestration policy belongs to the upstream
gateway, with `reasoning_effort="auto"`.

Until a typed, persisted, egress-eligible envelope exists, the honest
product state is **unavailable**, not a search query invented from the
question string.

## Decision

1. Persist `public_claim_envelope` in 3NF: one row names one claim kind,
   the exact public `source_post`, subject label, claim text, ontology
   truth status, optional event time, and `egress_eligible`.
2. Admitted claim kinds are a closed lookup: `claim_organization_presence`,
   `claim_public_event`, `claim_public_relationship`. Person, Keyman, TEPP,
   and fast-mlsirm kinds are not in the vocabulary and cannot be stored.
3. `egress_eligible` may be true only when the source post is `public`. A
   trigger fail-closes private or missing posts. Application code re-checks
   visibility and ABAC before any SearXNG dispatch.
4. Global Ask `verify_external` is opt-in and reuses the durable
   `global_ask_job.verify_external_requested` consent field from migration
   0218. Off omits the projection. On loads currently authorized
   egress-eligible envelopes and never nominates a claim from question tokens.
   For a knowledge-cutoff answer, both the source post and envelope must have
   existed no later than the cutoff; later live claims cannot enter an earlier
   evidence view.
5. SearXNG may retrieve a bounded list of public HTTP(S) URLs for the
   persisted claim text. Search pages, localhost, and literal
   private-network hosts are dropped. Those URLs are `external_evidence_urls`
   and must never enter `cited_post_ids`.
6. Classification:
   - search channel unavailable → `claim_unavailable`;
   - no usable URL → `claim_not_enough_information`;
   - `claim_organization_presence` with a distinctive-token footprint on a
     retrieved URL → `claim_supported` (the same FEVER presence subset
     ADR 0005 already ships);
   - `claim_refuted` and NLI polarity for other kinds stay unavailable
     until contextual-orchestrator classifies retrieved evidence. This
     repository does not force `mode="verify"`.
7. Private source text, raw source hints, credentials, PII, TEPP payloads,
   and fast-mlsirm respondent or item data never leave the trust boundary.

## Consequences

- After `make seed`, Ask Agent can opt into public-claim verification.
  The Demo public post envelope sits above the answer; a click opens that
  post. Web verification is unavailable when SearXNG is unset.
- A later orchestrator-owned polarity slice can fill `claim_refuted`
  without rewriting admission.
- Heuristic token-overlap claim selection remains forbidden.

## References

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018).
FEVER: A large-scale dataset for fact extraction and verification.
*Proceedings of NAACL-HLT 2018*, 809–819.
https://doi.org/10.18653/v1/N18-1074

World Wide Web Consortium. (2013, April 30). *PROV-O: The PROV ontology*
(W3C Recommendation). https://www.w3.org/TR/2013/REC-prov-o-20130430/
