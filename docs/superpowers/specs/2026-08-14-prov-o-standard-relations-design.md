# PROV-O standard relations design

## Goal

Extend PR #74 from three actor categories to complete, interoperable W3C PROV-O relation support while preserving the current product navigation graph.

## Considered approaches

### A. Widen `knowledge_graph_edge`

Rejected. It has one UUID object and cannot represent RDF literals, qualified influence resources, or multiple classes per resource.

### B. Store opaque RDF only

Rejected. It would support interchange but provide no fail-closed domain/range, datatype, or relational-integrity contract.

### C. Standards layer plus explicit product projection — selected

A complete PROV-O registry, validator, inference engine, normalized relational store, RDF serializer, and support profile sit beside the compact product graph. Existing nodes may be bound to standard resources, and only an explicit projector creates navigation edges.

## Invariants

1. Exact W3C namespace and local names are preserved.
2. The registry count is exactly 30 classes and 50 properties for this Recommendation version.
3. A property is object or datatype, never both.
4. Qualified forms imply unqualified forms.
5. Reserved inverse names never create ad hoc vocabulary.
6. Existing product data is not silently retyped or projected.
7. SQL and Python reject invalid assertion shape/domain/range.
8. Definitions and observations remain normalized and independently versionable.
