# Analysis-run lineage outbox standards and research traceability

**Status:** Active PR evidence; not protected-main truth until merge.
**Scope:** Migration 0019, ADR 0018, rollback, and cutoff-reconstruction tests.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| Hohpe & Woolf (2003) transactional outbox | Durable work stays in PostgreSQL; a queue may signal but cannot be the authority for Succeeded. | `analysis_run_outbox` lease/completion columns; Valkey is optional. |
| Bernstein & Newcomer (2009) | Request identity and derivation commit separately so a retry cannot invent a second run. | ADR 0017 create stays Pending; ADR 0018 delivery claims one outbox row. |
| W3C PROV-DM / PROV-O | Keep the activity that reconstructed edges identifiable and scoped to one run. | `analysis_run_lineage_edge.analysis_run_id` plus append-only status events. |
| W3C Time Ontology in OWL / ISO 8601-1:2019 | Reconstruct only posts known at the run cutoff. | Worker filter `created_at <= knowledge_cutoff` before `lineage_edge_specs`. |
| AERA/APA/NCME (2014) | Do not fabricate a measurement when the measurement service is absent. | TEPP reconstruct is 422; no theta column or local psychometric substitute. |

## Accuracy claim

`fixtures.sample_records()` designs an A-100 fork: the pricing-renegotiation
follow-up (`rec-002`) has two children (revised quote `rec-003`, delivery
question `rec-004`). `reconstruct_cutoff_edges` must recover that shape.
`rec-006` remains its own root. That is a true-structure test, not a
placeholder score.

## APA 7th references

American Educational Research Association, American Psychological
Association, & National Council on Measurement in Education. (2014).
*Standards for educational and psychological testing*. American
Educational Research Association.

Bernstein, P. A., & Newcomer, E. (2009). *Principles of transaction
processing* (2nd ed.). Morgan Kaufmann.

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns: Designing,
building, and deploying messaging solutions*. Addison-Wesley.

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology* (W3C
Recommendation). https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
