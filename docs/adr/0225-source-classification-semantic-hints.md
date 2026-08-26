# ADR 0225: Source classification semantic hints

**Status:** Accepted  
**Date:** 2026-08-26  
**Extends:** [ADR 0004](0004-knowledge-graph-ontology.md),
[ADR 0117](0117-catalog-backed-semantic-hints.md),
[ADR 0159](0159-published-ontology-pages.md),
[ADR 0207](0207-repository-case-ontology-namespace-canonical.md), and
[ADR 0222](0222-project-nodes-in-ontology-neighborhood.md)

## Context

The importer preserves a governed VOC type plus caller-mapped source stage and
detail-state codes, but semantic extraction received neither classification.
An authorized source reference catalog currently provides examples, not a
complete code list or authoritative definitions for every observed value.
Dropping the fields loses source evidence; minting ontology concepts from
partial examples invents semantics.

## Decision

1. Pass `voc_type_code`, `source_stage_code`, and
   `source_detail_state_code` to contextual-orchestrator as labeled raw source
   hints with exact `source_post` column provenance.
2. Raw codes are context only. They do not assert a lifecycle transition,
   inspection outcome, quality grade, entity relationship, or classified
   ontology concept. An RDF source-code literal asserts only the observed raw
   value and its predicate, not the value's business meaning.
3. RDF projects the governed five-value VOC type as `:hasPostType` to its
   published SKOS concept. Stage and detail-state remain literal properties;
   projecting a raw literal preserves evidence without minting a concept.
4. Promoting stage/detail values to ontology concepts requires a complete
   source-owned code catalog, stable definitions, mapping provenance, and
   SHACL fixtures. Partial screen examples are insufficient.
5. Missing codes remain `none`; no default classification is inferred. Every
   RDF post projector therefore requires an explicit governed VOC type.

## Consequences

Semantic extraction can consider classifications already preserved by the
import boundary without silently losing them or overclaiming their meaning.
The ontology remains intentionally incomplete for source-specific grades and
inspection states until their authority is available.
