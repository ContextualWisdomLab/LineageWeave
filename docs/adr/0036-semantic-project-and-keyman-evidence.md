# ADR 0036: Semantic project and Keyman evidence

- Status: Accepted
- Date: 2026-08-18

## Context

`source_post.secondary_grouping_key` is useful when an importer has a
project field, but many records describe a project only in the title or body.
The same record can also carry useful hints in its sales-pool/process-unit,
customer, and author-account affiliations. A customer represented as `기타`,
미등록, unknown, or an equivalent placeholder is not reliable identity
evidence.

Keyman side classification has the same boundary. The post author's account
and its corporate affiliations are strong prior context for identifying an
our-side person, but they do not prove that an arbitrary name in the body is a
Keyman.

## Decision

1. Keep imported project fields as explicit evidence, not as the only source
   of project identity.
2. Send project field, sales-pool, customer, author display name, and author
   affiliation hints to `contextual-orchestrator` together with normalized
   title/body text. Hints are priors, never proof.
3. Treat generic or unregistered customer values as weak hints. They cannot
   raise an unsupported project or Keyman assertion to a confirmed result.
4. Extract semantic project mentions through the existing post-summary
   orchestrator path. Persist canonical key, display name, evidence phrase,
   confidence, ontology IRI, and extraction method in `post_project_mention`.
5. Project period reports union non-empty imported project keys with semantic
   project mentions whose confidence is at least `0.7`. A post may belong to
   multiple project groups. Lower-confidence candidates remain visible as
   uncertainty but are excluded from calibrated grouping.
6. Keyman extraction uses the same author/account context, while the text's
   stated role or affiliation remains required for the extracted result.
7. No project, customer, organization, or person is fabricated when the
   semantic channel is unavailable or its response is malformed.

## Consequences

The project grouping is no longer limited to rows with an imported project
field, while reports retain a deterministic threshold and multi-membership
behavior. Reviewers can inspect the evidence and confidence instead of
mistaking an inferred label for a source fact. Generic customer metadata is
prevented from becoming an accidental identity anchor.

This is evidence-backed semantic linking, not a full probabilistic ontology
reasoner or random-effects multilevel estimator. Those require a separate
calibrated model and evaluation dataset.
