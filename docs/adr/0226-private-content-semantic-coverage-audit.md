# ADR 0226: Private content semantic-coverage audit

**Status:** Accepted  
**Date:** 2026-08-26  
**Extends:** [ADR 0001](0001-demo-identity-and-data-boundary.md),
[ADR 0004](0004-knowledge-graph-ontology.md), and
[ADR 0089](0089-private-real-data-runtime-boundary.md)

## Context

Schema availability does not prove that the ontology expresses the material
meaning of source content. A first runtime request submitted 100 private titles
but returned a claimed sample size of 60. The transport had succeeded, yet the
semantic result was unusable because neither the model nor the caller enforced
cardinality. Repository artifacts must not retain the private titles.

## Decision

1. `scripts/audit_source_content_semantics.py` reads a caller-owned query that
   returns exactly one `content_text` column and exactly the declared sample.
2. Content crosses only the configured contextual-orchestrator boundary in
   `conduct` mode. Every accepted batch requires a multi-step trace.
3. The caller accepts a batch only when JSON, input count, item count, ordered
   indexes, booleans, and governed missing-dimension codes all validate.
4. No retry repairs, lexical rules, inferred categories, source values,
   identifiers, or row-level outputs are persisted or printed. Any malformed,
   incomplete, single-agent, or unavailable result fails the run.
5. Only complete non-identifying aggregates may enter repository documents.
   A sample audit describes the sample, never the full corpus.
6. Missing-dimension counts do not themselves authorize new private ontology
   terms. Event/activity candidates must first reconcile with PROV-O;
   temporal candidates with OWL-Time; and observed property, asset, system,
   or feature-of-interest candidates with the current SOSA/SSN edition. A
   source-grounded normalized fact and qualified provenance remain mandatory.

## Consequences

An HTTP 200 can no longer turn a partial classification into coverage evidence.
The audit remains unavailable when contextual-orchestrator cannot complete all
batches, preserving failures in the denominator instead of silently shrinking
the sample.

## References

Cox, S., & Little, C. (Eds.). (2022). *Time ontology in OWL*. World Wide Web
Consortium. https://www.w3.org/TR/owl-time/

Cox, S. J. D., Lefrançois, M., Warren, R., Atkinson, R., Moreira de Sousa, L.,
Schleidt, K., Grellet, S., & Janowicz, K. (Eds.). (2026). *Semantic Sensor
Network Ontology—2023 edition* (Working Draft). World Wide Web Consortium &
Open Geospatial Consortium. https://www.w3.org/TR/vocab-ssn-2023/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/
