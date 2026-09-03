# Architecture Decision Records

ADRs are the normative source for architecture decisions. Research notes,
implementation matrices, schema references, runtime evidence, and Storybook
inventories remain supporting documents unless an ADR explicitly promotes a
decision from them.

## Supporting-document map

| Supporting document | Normative ADR |
|---|---|
| [`product-requirements.md`](../product-requirements.md) | Product requirements projection across the ADR set; ADRs remain normative, including [0252](0252-temporal-primary-voice-history.md) |
| [`product-technical-gap-baseline.md`](../product-technical-gap-baseline.md) | Product/technical traceability projection across the ADR set; ADRs remain normative |
| [`release.md`](../release.md) | [0358](0358-immutable-release-supply-chain-boundary.md) |
| [`lineage-bi-research-notes.md`](../lineage-bi-research-notes.md) | [0084](0084-lineage-research-grounding.md), [0062](0062-semantic-unit-embedding.md), [0064](0064-lineage-evidence-and-tree-assembly.md), [0024](0024-rankweave-fusion-fail-closed.md), [0165](0165-quantity-script-display.md), [0167](0167-rankweave-ranking-channel-evidence.md), [0169](0169-ask-batched-lineage-graph.md), [0172](0172-event-lineage-channel-evidence.md), [0202](0202-ask-event-time-filter.md), [0223](0223-explicit-semantic-content-unit-kinds.md), [0238](0238-source-conversation-turn-import-contract.md) |
| [`voice-combination-technical-requirements.md`](../voice-combination-technical-requirements.md) | [0246](0246-expanded-voice-of-x-post-taxonomy.md), [0251](0256-evidence-bearing-voice-combinations.md), [0252](0252-temporal-primary-voice-history.md) |
| [`lineage-bi-research-notes.md`](../lineage-bi-research-notes.md) | [0084](0084-lineage-research-grounding.md), [0062](0062-semantic-unit-embedding.md), [0064](0064-lineage-evidence-and-tree-assembly.md), [0024](0024-rankweave-fusion-fail-closed.md), [0165](0165-quantity-script-display.md), [0167](0167-rankweave-ranking-channel-evidence.md), [0169](0169-ask-batched-lineage-graph.md), [0172](0172-event-lineage-channel-evidence.md), [0202](0202-ask-event-time-filter.md), [0223](0223-explicit-semantic-content-unit-kinds.md) |
| [`PROV_O_IMPLEMENTATION.md`](../PROV_O_IMPLEMENTATION.md) | [0065](0065-prov-o-provenance-boundary.md) |
| [`PROV_O_IMPLEMENTATION_MATRIX.md`](../PROV_O_IMPLEMENTATION_MATRIX.md) | [0065](0065-prov-o-provenance-boundary.md) |
| [`ONTOLOGY_NAMESPACE_INVENTORY.md`](../doctoring/ONTOLOGY_NAMESPACE_INVENTORY.md) | [0207](0207-repository-case-ontology-namespace-canonical.md), [0157](0157-public-ontology-namespace-identity.md) |
| [`image-content-schema.md`](../image-content-schema.md) | [0066](0066-position-preserving-image-content.md) |
| [`storybook-inventory.md`](../storybook-inventory.md) | [0118](0118-uiux-standard-guide-v3-design-overhaul.md), [0184](0184-ontology-provenance-explorer.md), [0222](0222-project-nodes-in-ontology-neighborhood.md), [0256](0256-evidence-bearing-voice-combinations.md) |
| [`POSTGRESQL_CONCURRENCY_REFERENCES.md`](../doctoring/POSTGRESQL_CONCURRENCY_REFERENCES.md) | [0204](0204-analysis-run-short-transaction-delivery.md), [0213](0213-global-ask-embedding-pool-release.md) |
| [`GLOBAL_ASK_PUBLIC_VERIFICATION_REFERENCES.md`](../doctoring/GLOBAL_ASK_PUBLIC_VERIFICATION_REFERENCES.md) | [0215](0215-global-ask-public-claim-verification.md) |
| [`GLOBAL_ASK_KNOWLEDGE_CUTOFF_REFERENCES.md`](../doctoring/GLOBAL_ASK_KNOWLEDGE_CUTOFF_REFERENCES.md) | [0216](0216-global-ask-knowledge-cutoff.md) |
| [`GLOBAL_ASK_QUERY_REWRITE_REFERENCES.md`](../doctoring/GLOBAL_ASK_QUERY_REWRITE_REFERENCES.md) | [0217](0217-evidence-constrained-semantic-query-rewrite.md) |
| [`MCP_GLOBAL_ASK_REFERENCES.md`](../doctoring/MCP_GLOBAL_ASK_REFERENCES.md) | [0218](0218-current-contract-mcp-global-ask.md) |
| [`operability/http-concurrency-evidence.md`](../operability/http-concurrency-evidence.md) | [0204](0204-analysis-run-short-transaction-delivery.md), [0212](0212-single-query-authorized-post-filter-options.md), [0213](0213-global-ask-embedding-pool-release.md) |
| [`operability/mcp-concurrency-evidence.md`](../operability/mcp-concurrency-evidence.md) | [0218](0218-current-contract-mcp-global-ask.md) |
| Evidence operations Dashboard (`/`) | [0206](0206-evidence-operations-dashboard.md) |
| [`temporal-topic-context-influence-research.md`](../temporal-topic-context-influence-research.md) | [0210](0210-temporal-topic-context-influence-dashboard.md) |
| [`python-mathematical-compute-boundary-audit.md`](../doctoring/python-mathematical-compute-boundary-audit.md) | [0208](0208-externalize-local-mathematical-compute.md) |
| [`WORKER_FUNCTION_TAXONOMY_REFERENCES.md`](../doctoring/WORKER_FUNCTION_TAXONOMY_REFERENCES.md) | [0232](0232-worker-function-taxonomy-in-the-published-ontology.md) |
| [`OCCUPATIONAL_CONSTRUCT_REFERENCES.md`](../doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md) | [0248](0248-occupational-construct-evidence-boundary.md), [0250](0250-official-occupational-construct-catalog-sync.md), [0253](0253-catalog-bound-occupational-construct-extraction.md), [0255](0255-occupational-construct-ontology-navigation.md), [0265](0265-occupational-construct-catalog-search.md) |
| [`IOPSY_TAXONOMY_REFERENCES.md`](../doctoring/IOPSY_TAXONOMY_REFERENCES.md) | [0251](0251-fja-iopsy-cognitive-affective-behavioral-ontology.md) |

| [`IO_OCCUPATIONAL_TAXONOMY_REFERENCES.md`](../doctoring/IO_OCCUPATIONAL_TAXONOMY_REFERENCES.md) | [0245](0245-io-occupational-taxonomy-in-the-published-ontology.md) |

| [`ANALYSIS_RUN_REGISTRY_REFERENCES.md`](../doctoring/ANALYSIS_RUN_REGISTRY_REFERENCES.md) | [0013](0013-normalized-analysis-run-registry.md)-[0022](0022-authorized-tepp-start.md) registry family, [0017](0017-authorized-analysis-run-create.md), [0020](0020-analysis-run-retention-purge.md), [0021](0021-authorized-analysis-run-start.md) |
| [`DESIGN_TOKEN_REFERENCES.md`](../doctoring/DESIGN_TOKEN_REFERENCES.md) | [0099](0099-badge-and-accent-color-tokens.md), [0118](0118-uiux-standard-guide-v3-design-overhaul.md) |
| [`EXTERNAL_LINEAGE_CONTRACT_REFERENCES.md`](../doctoring/EXTERNAL_LINEAGE_CONTRACT_REFERENCES.md) | [0239](0239-external-email-project-lineage-contract.md) |
| [`EXTERNAL_LINEAGE_CONTRACT_TRACEABILITY.md`](../doctoring/EXTERNAL_LINEAGE_CONTRACT_TRACEABILITY.md) | [0239](0239-external-email-project-lineage-contract.md) |
| [`JOB_ARCHITECTURE_REFERENCES.md`](../doctoring/JOB_ARCHITECTURE_REFERENCES.md) | [0263](0263-authorized-job-architecture-import.md) |
| [`NARUON_CALENDAR_PROJECTION_REFERENCES.md`](../doctoring/NARUON_CALENDAR_PROJECTION_REFERENCES.md) | [0038](0038-calendar-source-contract.md), [0203](0203-naruon-calendar-projection-boundary.md) |
| [`ONET_RATING_STORE_REFERENCES.md`](../doctoring/ONET_RATING_STORE_REFERENCES.md) | [0257](0257-onet-occupation-rating-observation-store.md) |
| [`ONTOLOGY_EXPLORER_REFERENCES.md`](../doctoring/ONTOLOGY_EXPLORER_REFERENCES.md) | [0184](0184-ontology-provenance-explorer.md) |
| [`OPENTELEMETRY_REFERENCES.md`](../doctoring/OPENTELEMETRY_REFERENCES.md) | [0009](0009-cross-post-actor-identity.md), [0071](0071-post-scoped-llm-session-metadata.md) |
| [`PROV_O_REFERENCES.md`](../doctoring/PROV_O_REFERENCES.md) | [0011](0011-prov-o-standard-relations.md), [0065](0065-prov-o-provenance-boundary.md) |
| [`RELATED_NODE_TEAM_ORG_REFERENCES.md`](../doctoring/RELATED_NODE_TEAM_ORG_REFERENCES.md) | [0018](0018-related-nodes-team-org-walk.md) |
| [`ROLE_CATALOG_IDENTITY_REFERENCES.md`](../doctoring/ROLE_CATALOG_IDENTITY_REFERENCES.md) | [0019](0019-role-catalog-identity.md), [0027](0027-role-person-catalog-identity.md) |
| [`SOURCE_POST_REVISION_REFERENCES.md`](../doctoring/SOURCE_POST_REVISION_REFERENCES.md) | [0024](0024-rankweave-fusion-fail-closed.md), [0025](0025-source-post-revision.md) |

[0011](0011-prov-o-standard-relations.md) and [0065](0065-prov-o-provenance-boundary.md) cite the dated W3C PROV-O and PROV-DM Recommendations (https://www.w3.org/TR/2013/REC-prov-o-20130430/ and https://www.w3.org/TR/2013/REC-prov-dm-20130430/).

Files under `docs/doctoring/` remain non-normative supporting evidence even
when this map links them to an ADR. Runtime-evidence files record observed
results for already-decided behavior.
