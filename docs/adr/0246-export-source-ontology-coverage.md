# ADR 0246: Export-source ontology coverage

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0004](0004-knowledge-graph-ontology.md), [ADR
0207](0207-repository-case-ontology-namespace-canonical.md), and
[ADR 0242](0242-private-content-semantic-coverage-audit.md)

## Context

An authorized real PostgreSQL source (`public.zcrht811_export_rows`, a
single-table extract of short timestamped records exported from an ERP
customer-relationship program) was made available at an aggregate-only
analysis boundary. Repository artifacts must not retain any source value,
identifier, organization name, or artifact path (ADR 0001). The question the
audit must answer: is the published Ontology and Semantic Layer sufficient to
express the export's content, and where it is not, does the gap belong to
(a) a missing derived-semantic term, (b) a raw source code that must remain
instance data until its code system is governed, or (c) a column that carries
no semantic meaning of its own?

The export is a set of business-document rows with a governed source-type
field (VOC / VOCC / VOCO / VOM / VOP), raw ERP lifecycle and classification
codes, an authored document title/body containing the actual site/business
content, a user-attribution and record-timestamp trail, and a caller-owning
geographic country/region field.

## Decision
1. **Governed document type is the only value now promoted to the SKOS
   scheme layer.** The five-value source type field maps 1:1 onto the
   governed five-value `voc_type` post-type scheme (ADR 0207, seeded by
   migrations/0042): a source `VOC` record is a `:VoiceOfCustomerType` post,
   `VOCC` a `:VoiceOfCustomerCustomerType`, and so on. No new document-type
   concepts are minted.
2. **All other source lifecycle and classification codes stay instance
   literals.** `grade`, `stage`, `detail-state`, reply and deletion flags,
   and the product-unit codes are raw ERP codes whose code system a caller
   or an upstream project governs; this ontology neither renames nor
   interprets them (the documented `sourceStageCode` / `sourceDetailStateCode`
   raw projections already exist for the analogous application rows). A code
   with no governed system remains instance data, never a fabricated term nor
   a local psychometric meaning (ADR 0145 boundaries apply).
3. **Derived semantic content is now locatable.** The audit surfaced that the
   semantic layer expressed *that* a post concerns a place yet had no way to
   carry the place name or its region. Two derived-semantic datatype
   properties, `:locationName` and `:countryCode`, are added to the
   `:Location` node with a SHACL node shape. They are properties of the
   *derived semantic location node* -- like `:semanticConfidence` on
   `:ProjectMention` -- not column projections of the relational tables, so
   the ADR 0207 column-only discipline does not apply.
4. **Aggregate coverage reporting only.** All coverage facts in the ADR and
   its supporting document are counts and distinct-code-set membership
   statements over the export's code sets; no title, person, project number,
   or artifact name is narrated. Reproduction uses the caller-supplied
   read-only DSN and aggregate-only queries, matching ADR 0242 decision 5.

## Consequences

- Posters can name the plant site and country/region a record came from on a
  buyer-facing post view without exposing internal source codes.
- Existing round-trip tests (lookup-code coverage) are untouched: the new
  terms carry no `:lookupCode`, so there is nothing new for the relational
  schema to seed.
- The raw ERP codes remain internal instance data; buying them into a
  governed SKOS scheme is a future decision only when a caller governs the
  underlying code authority (ADR 0145 measurement boundaries apply).