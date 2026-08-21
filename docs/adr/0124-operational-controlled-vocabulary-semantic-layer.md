# ADR 0124: Model operational controlled vocabularies as SKOS concepts

## Status

Accepted

## Context

`common_lookup_value` already centralizes configuration-like values used by
post visibility, VOC type, permissions, and issue-ticket state. The existing
OWL/RDFS vocabulary modeled the knowledge-graph predicates and actor types,
but left these operational codes as untyped strings. That weakened the
semantic layer exactly where the product exposes public/private access,
VOC/VOM/VOP classification, RBAC permissions, and ticket/calendar workflow.

## Decision

Represent these four lookup categories as SKOS concept schemes in
`docs/ontology/lineageweave-kg.ttl`:

- `post_visibility`: public and private post visibility concepts;
- `voc_type`: VOC, VOCC, VOCO, VOM, and VOP concepts;
- `permission`: post-read and post-admin concepts;
- `ticket_status`: open, in-progress, and closed concepts.

The relational lookup code remains the stable `:lookupCode` annotation and
PostgreSQL remains the source of record. OWL object properties describe the
semantic use of a concept (`Post -> hasPostVisibility`, `Post -> hasVocType`,
`AccessRole -> hasPermission`, and `IssueTicket -> hasTicketStatus`) without
turning workflow state into a knowledge-graph edge predicate.

The ontology round-trip test now includes these categories. A code is not
considered semantically available merely because it exists in the database;
it must resolve to a SKOS concept with a scheme and label.

## Options considered

1. Keep operational values as database-only strings. Rejected: this leaves
   authorization, filtering, and workflow semantics outside the governed
   ontology.
2. Add a second runtime taxonomy database. Rejected: it duplicates the
   existing normalized lookup source and creates synchronization risk.
3. Publish the existing lookup values as SKOS concepts over the current
   relational source. Selected: it adds machine-readable semantics without a
   second store or a change to the API wire codes.

## Consequences

Positive:

- public/private, VOC classification, RBAC permissions, and ticket state have
  stable IRIs, labels, schemes, and domain/range semantics;
- drift between seeded lookup values and the published ontology fails tests;
- consumers can use SKOS alongside the existing OWL/RDFS and PROV-O profile.

Negative:

- adding a new operational lookup value now requires an ontology term and a
  round-trip test update;
- the current profile still does not model every analysis-run and content
  processing status as a semantic concept, so those remain explicitly tracked
  gaps rather than being silently treated as complete.

## References (APA 7th)

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS Simple Knowledge
Organization System reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

World Wide Web Consortium. (2017). *Shapes Constraint Language (SHACL)*.
https://www.w3.org/TR/shacl/
