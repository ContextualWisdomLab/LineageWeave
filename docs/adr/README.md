# Architecture Decision Records

ADRs are the normative source for architecture decisions. Research notes,
implementation matrices, schema references, runtime evidence, and Storybook
inventories remain supporting documents unless an ADR explicitly promotes a
decision from them.

## Supporting-document map

| Supporting document | Normative ADR |
|---|---|
| [`lineage-bi-research-notes.md`](../lineage-bi-research-notes.md) | [0084](0084-lineage-research-grounding.md), [0062](0062-semantic-unit-embedding.md), [0064](0064-lineage-evidence-and-tree-assembly.md) |
| [`PROV_O_IMPLEMENTATION.md`](../PROV_O_IMPLEMENTATION.md) | [0065](0065-prov-o-provenance-boundary.md) |
| [`PROV_O_IMPLEMENTATION_MATRIX.md`](../PROV_O_IMPLEMENTATION_MATRIX.md) | [0065](0065-prov-o-provenance-boundary.md) |
| [`image-content-schema.md`](../image-content-schema.md) | [0066](0066-position-preserving-image-content.md) |
| [`LINEAGE_EDGE_EVIDENCE_REFERENCES.md`](../doctoring/LINEAGE_EDGE_EVIDENCE_REFERENCES.md) | [0103](0103-event-lineage-channel-evidence.md) |

Runtime evidence under `docs/doctoring/` is not converted into an ADR: it
records observed results for already-decided behavior.
