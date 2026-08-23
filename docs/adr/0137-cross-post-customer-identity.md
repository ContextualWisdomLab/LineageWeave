# ADR 0137: Cross-post customer identity judgment and name history

- Status: Accepted
- Date: 2026-08-23
- Numbering: this decision was drafted as a second ADR 0135; analysis-result
  next actions keep [0135](0135-analysis-result-kind-exact-next-actions.md)
  and this record is 0137.
- Extends: [ADR 0003](0003-fast-mlsirm-report-integration.md),
  [ADR 0004](0004-knowledge-graph-ontology.md),
  [ADR 0009](0009-cross-post-actor-identity.md),
  [ADR 0010](0010-corporate-hierarchy-auto-creation.md),
  [ADR 0026](0026-tied-organization-similarity.md), and
  [ADR 0042](0042-source-hints-before-customer-binding.md)

## Context

Customer hints are currently grouped by `source_customer_code` alone. The same
opaque code can belong to different source systems, and the resolver reads a
bounded set of posts but does not retain which posts supported its decision,
an LLM-as-a-Judge response, or an IRT-ready measurement row. A corroborated
name can therefore be written to `corporate_entity` without proving that it was
repeated across distinct posts. `corporate_entity.entity_name` also overwrites
the only stored label when wording changes, so an alias and a formal rename are
indistinguishable.

The product needs a collective identity decision, not another per-post
classifier. Bhattacharya and Getoor (2007) show why relational evidence across
records matters for entity resolution. Zheng et al. (2023) also document that
LLM judges have position and other biases; a judge score alone is not a safe
master-data write authority.

## Decision

1. The source identity key is `(source_system_code, source_customer_code)`.
   `source_system_code` remains nullable because older authorized imports may
   not provide it, but null is one explicit key value (`NULLS NOT DISTINCT`),
   never a wildcard spanning named systems.
2. A customer identity judgment requires at least two distinct eligible,
   authorized posts carrying that exact key. The evidence fingerprint covers
   post ids, source timestamps, source customer names, and normalized excerpt
   hashes. An unchanged fingerprint reuses the persisted decision and avoids a
   second paid model call.
3. Candidate-name extraction continues through contextual-orchestrator. A
   second, versioned `fast_mlsirm.ContextualOrchestratorJudge` rubric evaluates
   cross-post recurrence, same-organization consistency, and candidate-name
   support. Its result is persisted through `LLMJudgeResult.to_irt_row()` in
   `customer_identity_judgment_response`; LineageWeave does not invent a
   parallel judge-to-IRT conversion.
4. Promotion requires all of the following: two or more distinct posts, the
   judge's accepted decision and minimum rubric category, external search
   corroboration, and a unique catalog resolution. A miss enters ADR 0010's
   verified hierarchy-creation path under ADR 0012's advisory lock. A tie stays
   unbound under ADR 0026. Missing contextual-orchestrator, search, TEPP, or
   hierarchy channels never produce substitute evidence.
5. TEPP's temporal-context contract may order the observation events. Its
   `association_not_causal` result is stored only as the ordering source. If
   TEPP is unavailable, source `created_at`/`updated_at` facts retain their
   deterministic order; no TEPP score or causal claim is fabricated.
6. `customer_identity_binding` is the stable Customer Master link. Evidence
   posts project through `post_customer_identity_mention` into the Knowledge
   Graph as `edge_customer_identity_observation`, distinct from an R&R
   organization mention. The edge's support remains post-scoped and ABAC
   filtered.
7. `corporate_entity_name_history` stores preferred, former, and alternate
   labels. This follows SKOS preferred/alternate-label semantics. A differing
   candidate becomes an alternate label by default. It replaces the preferred
   label only after a separate strict rename rubric proves the same legal
   identity, an explicit name-change assertion, and temporal succession. The
   prior preferred label then becomes former; the observation times are not
   presented as a legal effective date.
8. The judgment, its criterion responses, supporting posts, binding, name
   history, and graph mention remain normalized records with foreign keys. The
   judgment-to-post table is application audit evidence, not a new PROV-O
   predicate; `knowledge_graph_edge` remains only the navigation projection.
9. The PostgreSQL source importer collects only customer keys changed in that
   run and reconciles them after content and lineage persistence. Missing
   channels or a provider outage leave aggregate `unavailable` evidence and do
   not roll back authorized source records; a failure for one key does not stop
   the remaining keys. The admin endpoint remains an explicit retry path.

## Runtime sequence

```mermaid
sequenceDiagram
    participant Importer as PostgreSQL importer
    participant Store as LineageWeave PostgreSQL
    participant Orch as contextual-orchestrator
    participant Search as SearXNG
    participant TEPP

    Importer->>Store: Upsert authorized source posts
    Importer->>Store: Load repeated exact customer key
    Store-->>Importer: At least two eligible post records
    Importer->>TEPP: Order opaque observation events (optional)
    Importer->>Orch: Resolve candidate and run fast-mlsirm Judge
    Importer->>Search: Corroborate candidate organization
    alt all promotion gates pass
        Importer->>Store: Persist judgment, IRT rows, binding, names, post mentions
        Importer->>Store: Project customer-observation KG edges
    else evidence is missing, tied, or weak
        Importer->>Store: Preserve abstention evidence; do not bind
    end
```

## Consequences

- One plausible post cannot promote a customer master record.
- Source-system code collisions and same-name catalog ties fail closed.
- A reader can trace a promoted customer to every supporting post and the exact
  judge rubric version without storing source text again.
- Judge categories are audit measurements, not calibrated probability or
  theta. Population calibration remains a later `fast-mlsirm` report concern.
- Formal renames are intentionally rarer than aliases. An operator can review
  ambiguous labels without losing the current preferred name; former and
  alternate names are visible when the Customer Master entity is expanded.

## References (APA 7th)

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in
relational data. *ACM Transactions on Knowledge Discovery from Data, 1*(1),
Article 5. https://doi.org/10.1145/1217299.1217304

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-O: The PROV ontology*.
World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Reynolds, D. (Ed.). (2014). *The organization ontology*. World Wide Web
Consortium. https://www.w3.org/TR/vocab-org/

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z.,
Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023).
Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *Advances in Neural
Information Processing Systems, 36*. https://arxiv.org/abs/2306.05685
