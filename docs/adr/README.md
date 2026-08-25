# Architecture Decision Records

ADRs are the normative source for architecture decisions. Research notes,
implementation matrices, schema references, runtime evidence, and Storybook
inventories remain supporting documents unless an ADR explicitly promotes a
decision from them.

## Supporting-document map

| Supporting document | Normative ADR |
|---|---|
| [`product-technical-gap-baseline.md`](../product-technical-gap-baseline.md) | Product/technical traceability projection across the ADR set; ADRs remain normative |
| [`lineage-bi-research-notes.md`](../lineage-bi-research-notes.md) | [0084](0084-lineage-research-grounding.md), [0062](0062-semantic-unit-embedding.md), [0064](0064-lineage-evidence-and-tree-assembly.md), [0024](0024-rankweave-fusion-fail-closed.md), [0165](0165-quantity-script-display.md), [0167](0167-rankweave-ranking-channel-evidence.md), [0172](0172-event-lineage-channel-evidence.md) |
| [`PROV_O_IMPLEMENTATION.md`](../PROV_O_IMPLEMENTATION.md) | [0065](0065-prov-o-provenance-boundary.md) |
| [`PROV_O_IMPLEMENTATION_MATRIX.md`](../PROV_O_IMPLEMENTATION_MATRIX.md) | [0065](0065-prov-o-provenance-boundary.md) |
| [`ONTOLOGY_NAMESPACE_INVENTORY.md`](../doctoring/ONTOLOGY_NAMESPACE_INVENTORY.md) | [0157](0157-public-ontology-namespace-identity.md) |
| [`image-content-schema.md`](../image-content-schema.md) | [0066](0066-position-preserving-image-content.md) |
| [`storybook-inventory.md`](../storybook-inventory.md) | [0118](0118-uiux-standard-guide-v3-design-overhaul.md), [0184](0184-ontology-provenance-explorer.md) |

Files under `docs/doctoring/` remain non-normative supporting evidence even
when this map links them to an ADR. Runtime-evidence files record observed
results for already-decided behavior.
