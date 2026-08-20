# Event Lineage edge-evidence research and standards traceability

**Status:** Supporting doctoring for proposed ADR 0100. It does not promote an
active-PR implementation to protected-main truth.

| Evidence source | Product implication | Owning artifact | Executable evidence |
|---|---|---|---|
| Topic Detection and Tracking treats story links as uncertain detection evidence assembled from multiple signals rather than unquestioned fact. | Preserve independent channel scores and show them beside the fused selection value. | ADR 0064; ADR 0100 | `tests/test_lineage_channel_evidence.py`; `frontend/src/LineageDag.test.tsx` |
| Record linkage begins with fallible blocking and comparison evidence rather than a self-authenticating identity relation. | Secondary-key agreement remains one explicit channel and never becomes authority by itself. | `lineageweave/channels.py`; ADR 0100 | true-channel persistence and exact-value UI tests |
| W3C PROV-O separates entities, activities, agents, derivations, and attribution. | Keep reconstructed edge evidence distinct from source facts, external verification, and TEPP/fast-mlsirm measurement artifacts. | ADR 0065; ADR 0100 | normalized schema, ABAC projection tests, API/UI type contract |

## APA 7th references

Allan, J. (Ed.). (2002). *Topic detection and tracking: Event-based information
organization*. Springer. https://doi.org/10.1007/978-1-4615-0933-2

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal
of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.1080/01621459.1969.10501049

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/
