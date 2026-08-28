# ADR 0269: Persist public-claim admission before external verification

## Status

Accepted

## Context

ADR 0215 defines opt-in public verification and keeps external evidence
separate from internal authority. Its first implementation nominated semantic
facts by token overlap with the question. Token overlap is neither provenance
nor a governed claim-admission decision, and it can change when wording changes.

The abandoned draft PR #679 proposed replacing that implementation wholesale.
The current Global Ask queue, cutoff behavior, authorization scope, SearXNG
validation, and contextual-orchestrator verifier have since evolved and remain
authoritative. Only the persisted admission boundary is still missing.

## Decision

`public_claim_envelope` stores one bounded claim kind, exact claim text, source
post, PROV-O `prov:wasDerivedFrom` assertion, and egress decision. The evidence
resource must bind to that same source post. Only organization presence, public
event, and public relationship kinds are admitted; person, Keyman, measurement,
prompt, and source-body payloads have no storage code.

Production Global Ask loads at most four envelopes whose source post is both
public and cited in the completed answer. The per-question opt-in remains the
durable consent boundary. A cutoff excludes envelopes or source posts created
after that cutoff. Changing a post from public revokes egress eligibility.

The persisted envelope supplies candidates to the existing ADR 0215 verifier.
It does not replace SearXNG URL validation, contextual-orchestrator adjudication,
or the distinction between external URLs and internal post citations. No claim
is inferred from question-token overlap in the production path. When no current,
authorized envelope exists, verification reports no public claims and performs
no external request.

## Consequences

- Public egress admission is stable, reviewable, and provenance-bearing.
- Existing verification transport and outcome contracts remain unchanged.
- A producer must persist a governed envelope before a claim becomes eligible;
  absence stays unavailable rather than being repaired heuristically.
- Draft PR #679 remains historical evidence for the missing boundary and is not
  merged wholesale over the current semantic stack.

## References

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A
large-scale dataset for fact extraction and verification. In *Proceedings of
NAACL-HLT 2018* (pp. 809–819). https://doi.org/10.18653/v1/N18-1074
