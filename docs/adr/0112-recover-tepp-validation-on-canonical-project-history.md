# ADR 0112: Recover TEPP validation on the canonical project history

- Status: Proposed
- Date: 2026-08-21
- Depends on: LineageWeave Project history stack; `ContextualWisdomLab/TEPP#159`
- Supersedes: the duplicate project-history implementation carried by LineageWeave #281/#282

## Context

A Buyer project-history timeline was implemented on a canonical, authorization-first
LineageWeave read model. An earlier TEPP integration was then left behind in a closed
parent PR and an open child PR whose branch reimplemented the project query, event
classification, and timeline. The user-supplied product screen requires one project
lifecycle timeline and an optional TEPP-linked answer, not two competing histories.

The TEPP contract in PR #159 accepts only an exact project identity, a knowledge cutoff,
a focus event, and explicit source-grounded events. It may order those events and return
coded temporal-association findings. It does not accept or return a latent score, a
probability of causation, or an authoritative assignment record.

## Decision

1. LineageWeave remains authoritative for RBAC/ABAC, source eligibility, exact project
   identity, event classification, visible responsibility evidence, and the Buyer
   timeline.
2. The TEPP request is derived from that already-authorized canonical projection. No
   second database query or second timeline component is allowed.
3. Source-post creation time is sent as both `occurred_at` and `available_at` only because
   the canonical timeline explicitly declares it as the current fallback clock. The UI
   continues to disclose that limitation.
4. Actor names and local actor keys do not cross the service boundary. TEPP receives a
   deterministic opaque SHA-256 reference scoped to the authorized workspace. This is a
   data-minimizing pseudonymous reference, not a claim of irreversible anonymization.
5. Evidence text is bounded and composed from the event title and persisted source-state
   fields. Post bodies, browser tokens, review credentials, provider keys, and
   `TEPP_API_KEY` are not forwarded.
6. The client requires the exact versioned field set, exact event cardinality and content,
   deterministic chronological ordering, unchanged project/focus/cutoff identity, and
   evidence-derived participant counts. Unknown fields, changed evidence, or a response above
   TEPP's published 256 KiB contract limit fail closed before JSON decoding.
7. Accepted findings are limited to the six published TEPP #159 finding codes. Duplicate
   event or evidence references are rejected. Buyer UI copy is owned by LineageWeave and
   keyed by those codes; provider-authored summary prose is retained for contract
   validation but is not rendered as the interpretation.
8. `temporal_association_only` is the only accepted inference status. Buyer copy states
   that the result does not identify a cause.
9. A transport outage is distinct from an invalid response. `not_configured`,
   `unavailable`, and `invalid_evidence` states leave the canonical timeline readable and
   tell the operator or Buyer what to do next.
10. Global Ask and post-scoped Ask are a subsequent stacked slice and must reuse this same
    canonical projection and TEPP envelope.

## Consequences

- The previously implemented capability is recovered without reviving the orphaned
  duplicate stack.
- A TEPP outage cannot remove or alter authorized LineageWeave evidence.
- TEPP findings remain inspectable through exact source-post references.
- An unrecognized finding vocabulary cannot introduce provider-authored Buyer claims.
- The product does not answer “what caused the VOC?” as a causal claim. It answers which
  explicit prior records are temporally associated and provides evidence for human review.
- A future distinct event-time or available-time source can replace the current fallback
  only through a versioned contract and migration.

## Rejected alternatives

- **Merge the old #282 branch as-is.** It is based on a closed parent and carries a second
  project-history implementation with a large unrelated ancestry.
- **Let TEPP query the LineageWeave database.** This breaks authorization ownership and
  modular deployment.
- **Send full post bodies or actor names.** These are unnecessary for the published
  temporal contract and expand the privacy boundary.
- **Render a separate TEPP timeline.** Duplicate timelines can disagree and obscure which
  system owns evidence selection.
- **Render arbitrary TEPP summary prose.** The provider may validate time, but it does not
  own Buyer-facing interpretation or an open-ended claim vocabulary.
- **Describe preceding events as causes.** Event order alone does not identify causality.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of
the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2017). *Time ontology in OWL*.
https://www.w3.org/TR/owl-time/
