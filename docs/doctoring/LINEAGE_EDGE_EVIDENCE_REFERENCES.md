# Event Lineage edge-evidence research and standards traceability

**Status:** Supporting doctoring for proposed ADR 0101. It does not promote an
active-PR implementation to protected-main truth.

## Traceability matrix

| Evidence source | Product implication | Owning artifact | Executable evidence |
|---|---|---|---|
| Topic Detection and Tracking treats story links as uncertain detection evidence assembled from multiple signals rather than unquestioned fact. | Preserve each participating score, the normalized weight actually used, its contribution to the selected fused score, and deterministic contribution rank. | ADR 0064; ADR 0101; `lineageweave.lineage_persistence` | `tests/test_lineage_persistence.py`; `tests/test_lineage_channel_evidence.py`; `frontend/src/LineageDag.test.tsx` |
| Record linkage begins with fallible blocking and comparison evidence rather than a self-authenticating identity relation. | Secondary-key agreement remains one explicit channel and never becomes identity or authority by itself. | `lineageweave/channels.py`; ADR 0101 | no-LLM/LLM profile tests and exact Buyer disclosure |
| A reproducible derived result requires its generating activity/configuration to remain identifiable. | Persist one reconstruction-run version, generated-at time, and normalized active weight profile; do not recompute historic meaning at read time. | `lineage_reconstruction_run`; `lineage_reconstruction_run_channel`; ADR 0101 | real migration rehearsal; run/profile persistence tests |
| W3C PROV-O separates entities, activities, agents, derivations, and attribution. | Keep reconstructed edge evidence distinct from source facts, external verification, and TEPP/fast-mlsirm measurement artifacts. PostgreSQL remains authority; any RDF is a projection. | ADR 0065; ADR 0101 | normalized schema, ABAC projection tests, API/UI type contract |
| Accessible disclosure must not depend on pointer hover or color. | Repeat exact edge evidence in a semantic table and open disclosure, retain SVG text parity, keyboard/screen-reader semantics, responsive overflow, and print preservation. | `frontend/src/LineageDag.tsx`; `LineageDag.css`; Storybook inventory | `LineageDag.test.tsx`; `LineageDag.stories.tsx`; frontend build/Storybook gates |

## Numerical contract

- Every active score is finite and within `[0, 1]`.
- Every active normalized weight is finite and within `(0, 1]`.
- Active weights sum to 1 within absolute tolerance `1e-9`.
- `channel_contribution = channel_score × channel_weight`.
- Contributions sum to `post_lineage_edge.fused_score` within absolute
  tolerance `1e-9` before persistence and on read.
- Missing rows mean unavailable. They are never synthesized as zero.

These values are product-level reconstruction evidence. They are not calibrated
probabilities, causal effects, TEPP temporal estimates, or fast-mlsirm latent
parameters.

## APA 7th references

Allan, J. (Ed.). (2002). *Topic detection and tracking: Event-based information
organization*. Springer. https://doi.org/10.1007/978-1-4615-0933-2

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal
of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.1080/01621459.1969.10501049

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/
