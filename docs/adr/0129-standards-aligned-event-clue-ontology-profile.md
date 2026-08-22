# ADR 0129: Standards-aligned event and clue ontology profile

- Status: Accepted
- Date: 2026-08-21

## Context

The product must answer questions such as `왜?` from a connected graph, not
from a body-text keyword hit. A key event therefore needs explicit, searchable
clues for its actors, action, time, place, cause, goal, object, result,
condition, quantity, and next step. A clue must retain the source evidence and
the assertion state; a guessed relationship must never look like an observed
fact.

The existing `knowledge_graph_edge` table is a compact navigation projection.
It cannot represent the qualified evidence, literal values, selectors, or
inference provenance required by this use case. The semantic assertions and
event clues remain normalized source projections and can be joined into KG
rendering without pretending that every semantic row is already a polymorphic
KG node.

## Decision

Publish a standards-aligned ontology profile in
`docs/ontology/lineageweave-kg.ttl` and a validation profile in
`docs/ontology/lineageweave-shapes.ttl`.

### Standard mappings

- W3C PROV-O is the provenance backbone. Extracted assertions use
  `prov:Entity`; extraction is a `prov:Activity`; qualified influence,
  derivation, attribution, usage, association, delegation, and time remain
  available through the existing `lineageweave.prov_o` registry.
- W3C Organization Ontology supplies organization, organizational-unit,
  membership, role, reporting, and sub-organization patterns. A generic
  `사업부` is not bound to a concrete unit without source evidence.
- OWL 2/RDFS supply class inheritance, inverse properties, property chains,
  equivalence/disjointness, and restrictions. These are ontology axioms, not
  rows in `knowledge_graph_edge`.
- OWL-Time supplies instant/interval and before/after/during relations. A
  normalized date is retained with precision and normalization evidence.
- SOSA/SSN supplies the observation/result distinction. A
  `QuantitativeObservation` or `EventObservation` in this product is an
  extracted source assertion, not an asserted physical sensor act; it is
  therefore aligned through `rdfs:seeAlso` and does not claim `sosa:Observation`
  without an actual procedure, feature of interest, phenomenon time, and
  result.
- Web Annotation supplies the evidence-target and selector pattern. A clue
  may target an event, an assertion, or a source content unit. Exact source
  text and position remain private runtime evidence and are not copied into
  repository fixtures.
- SHACL supplies the machine-readable graph contract. It validates minimum
  evidence, value types, and the distinction between extracted and inferred
  assertions; it is also usable for UI generation and data integration.
- ODRL supplies normative rule vocabulary. A source condition such as “not
  commercial” is a fact/condition only. It becomes a prohibition, permission,
  or duty only when the source expresses a normative modality and action.
- QUDT is the external quantity/unit reference vocabulary. Local measurement
  codes remain the application-controlled vocabulary and use conservative
  `rdfs:seeAlso`/mapping annotations until an exact unit identity is verified.
- DCMI Terms supplies general metadata relations such as provenance,
  references, and conformance for export-facing metadata.
- ISO/IEC 21838 BFO, ISO/IEC 19510 BPMN, and ISO 21127 CIDOC CRM are mapping
  references for upper-level entity, process/event, and actor/event patterns.
  ISO 14224, ISA-95/IEC 62264, OPC UA Events/Alarms, and ISO 31000 extend the
  industrial asset, process, condition, maintenance, and risk vocabulary.
  They are not imported as runtime axioms because their domain commitments are
  broader than this product's evidence contract.

### Profile extensions for meanings no single standard covers

The profile may add a local term when no adopted vocabulary has the exact
meaning needed for source-grounded business correspondence. Every extension
must have:

1. a precise definition and domain/range;
2. source evidence and assertion status requirements;
3. a nearest standard mapping (`rdfs:seeAlso`, `skos:closeMatch`, or a
   qualified PROV relation), without overstating equivalence;
4. a declared inference policy; and
5. a decision on whether it is only a semantic-layer resource or is hydrated
   into the compact KG projection.

The first such extensions cover the whole source-to-question path:
`ObservationRecord`, `EventObservation`, `EvidenceClue`, `TemporalClaim`,
`OrganizationContext`, `IndustrialAsset`, `IndustrialProcess`,
`NormativeStatement`, `QualityAssessment`, `RiskStatement`,
`clueSupports`, `clueFor`, `hasCause`, `hasGoal`, `hasConsequence`,
`hasNextStep`, `assertionStatus`, and `inferenceRule`. They are not aliases
for W3C PROV properties: provenance uses the canonical PROV direction, while
these terms express the product's evidence and question-answering semantics.

The source-facing dimensions are deliberately explicit: time, place, actor,
cause, purpose/goal, result, next step, quantity, condition, quality, risk,
and source segment. Organization and industrial context are modeled as
separate entities so a plant, team, equipment item, process, and company are
not collapsed into one actor label. Normative statements are separate from
descriptive conditions.

### Assertion and inference boundary

The graph renderer may show asserted, derived, and inferred paths, but must
label them separately. A standard inverse, subclass, subproperty, or property
chain is deterministic entailment. A business conclusion such as “this event
was caused by X” is not entailed merely because X appears nearby; it needs a
source clue or a qualified inference record. No local heuristic may silently
upgrade a clue into a fact.

### Hydration rule

Declaring a class or relation in the profile does not create a database node.
New `knowledge_graph_edge` node/edge lookup codes require a relational source,
authorization-aware hydration, evidence rows, and a graph regression test.
Until then, the semantic layer exposes the resource and the Ask retriever may
join it as a provenance-bearing fact.

## Consequences

- Event-centered retrieval can traverse `event -> clue -> source unit ->
  post -> KG neighbor`, then answer `why` with a visible evidence path.
- Numeric, temporal, conditional, and role clues remain independently
  searchable without copying private source values into repository artifacts.
- The profile is broad enough for future event/entity classes while refusing
  false certainty where a standard does not define the business meaning.
- Shapes are a contract and regression guard; they do not replace the
  orchestrator's source-grounded extraction or database authorization.

## References

- W3C PROV-O: https://www.w3.org/TR/prov-o/
- W3C Organization Ontology: https://www.w3.org/TR/vocab-org/
- W3C OWL-Time: https://www.w3.org/TR/owl-time/
- W3C SOSA/SSN 2023: https://www.w3.org/TR/vocab-ssn-2023/
- W3C Web Annotation Data Model: https://www.w3.org/TR/annotation-model/
- W3C SHACL: https://www.w3.org/TR/shacl/
- W3C ODRL Information Model: https://www.w3.org/TR/odrl-model/
- QUDT Schema: https://www.qudt.org/doc/2025/03/DOC_SCHEMA-QUDT.html
- ISO/IEC 21838-2:2021 BFO: https://www.iso.org/standard/74572.html
- OMG BPMN 2.0: https://www.omg.org/spec/BPMN/2.0
- CIDOC CRM / ISO 21127:2023: https://cidoc-crm.org/Event/iso-211272023-has-been-released
- DCMI Metadata Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- ISO 14224: https://www.iso.org/standard/64076.html
- ISA-95 / IEC 62264: https://www.isa.org/standards-and-publications/isa-standards/isa-95-standard
- OPC UA Event Model: https://reference.opcfoundation.org/specs/OPC-10000-3/4.7
- OPC UA Alarms and Conditions: https://reference.opcfoundation.org/Core/Part9/v105/docs/4.1
- ISO 31000: https://committee.iso.org/sites/tc262/home/projects/published/iso-31000-2009-risk-management.html
